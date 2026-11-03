// Una toma 3D: mundo (mundo.ts) + cadena de post de la skill (tinta → desenfoque de lente → bloom → tone map NEUTRAL →
// gradación). El plan da el Estado de cada cuadro; las medidas en píxeles escalan con el lado corto / 1080.
import React, { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { AbsoluteFill, continueRender, delayRender, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { EffectComposer } from "@react-three/postprocessing";
import { BlendFunction, BloomEffect, ToneMappingEffect, ToneMappingMode } from "postprocessing";
import { InkPass, noInkFallback } from "./ink";
import { LensBlur } from "./lensblur";
import { GradeEffect, GRADES } from "./grade";
import { Mundo, Estado } from "./mundo";
import { NombreEscenario } from "./escenarios";
import { NombreLuz } from "./luces";
import { serpientePrueba } from "./animalPrueba";

export type Desenfoque = { foco?: [number, number, number]; cInf: number };
export type Plan = (f: number) => Estado & { dof?: Desenfoque };

const makeBloom = (corto: number) => {
  const b = new BloomEffect({ blendFunction: BlendFunction.ADD, intensity: 0.5, luminanceThreshold: 1.0, luminanceSmoothing: 0.2, mipmapBlur: true, levels: 6, radius: 0.6 });
  const mip = b.mipmapBlurPass, setSize = mip.setSize.bind(mip);
  mip.setSize = (w: number, h: number) => { const k = 1080 / Math.max(1, Math.min(w, h)); setSize(Math.round(w * k), Math.round(h * k)); };
  void corto;
  return b;
};

/** carga la imagen del animal (URL) o la serpiente de prueba */
export const useAnimal = (src?: string | null) => {
  const [img, setImg] = useState<HTMLImageElement | HTMLCanvasElement | null>(null);
  const [h] = useState(() => delayRender("animal"));
  useEffect(() => {
    if (!src || src === "prueba") { setImg(serpientePrueba()); continueRender(h); return; }
    const im = new Image(); im.crossOrigin = "anonymous";
    im.onload = () => { setImg(im); continueRender(h); };
    im.onerror = () => { setImg(serpientePrueba()); continueRender(h); };
    im.src = src;
  }, [src, h]);
  return img;
};

const Inner: React.FC<{ escenario: NombreEscenario; luz: NombreLuz; plan: Plan; animal: HTMLImageElement | HTMLCanvasElement | null }> = ({ escenario, luz, plan, animal }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const { camera, scene } = useThree();
  const mundo = useMemo(() => new Mundo(escenario, luz, animal), [escenario, luz, animal]);
  const fx = useMemo(() => {
    const g = new GradeEffect(GRADES[luz === "amanecer" ? "golden" : "day"], luz === "noche" ? 0.5 : luz === "amanecer" ? 0.6 : 0.8);
    return { ink: new InkPass(scene, camera as THREE.PerspectiveCamera, { strength: 0.32, widthNear: 2.6, widthFar: 1.6, creaseScale: 0.5, angleLo: 55, angleHi: 70 }) /* mundo casi sin tinta, como la muestra; el personaje lleva la suya */, lens: new LensBlur({ maxCoC: 24, nearScale: 1.2 }), bloom: makeBloom(Math.min(width, height)),
      tone: new ToneMappingEffect({ mode: ToneMappingMode.NEUTRAL }), grade: g };
  }, [camera, scene, luz, width, height]);
  useEffect(() => () => fx.ink.dispose(), [fx]);
  const post = useMemo(() => (
    <EffectComposer multisampling={4}>
      <primitive object={fx.ink} dispose={null} />
      <primitive object={fx.lens.pre} dispose={null} />
      <primitive object={fx.lens.main} dispose={null} />
      <primitive object={fx.bloom} dispose={null} />
      <primitive object={fx.tone} dispose={null} />
      <primitive object={fx.grade} dispose={null} />
    </EffectComposer>
  ), [fx]);
  const cam = camera as THREE.PerspectiveCamera;
  const s = plan(f);
  const look = mundo.update(s, cam, scene, Math.min(width, height));
  noInkFallback(mundo.root);
  const fwd = new THREE.Vector3(); cam.getWorldDirection(fwd);
  const foco = s.dof?.foco ? new THREE.Vector3(...s.dof.foco) : look;
  fx.lens.focus = Math.max(0.3, foco.clone().sub(cam.position).dot(fwd));
  fx.lens.cInf = s.dof?.cInf ?? 0;
  return (<><primitive object={mundo.root} dispose={null} />{post}</>);
};

export const Toma: React.FC<{ escenario: NombreEscenario; luz: NombreLuz; plan: Plan; animal?: string | null }> = ({ escenario, luz, plan, animal }) => {
  const { width, height } = useVideoConfig();
  const img = useAnimal(animal);
  if (!img) return null;
  return (
    <AbsoluteFill>
      <ThreeCanvas width={width} height={height} shadows gl={{ antialias: false, stencil: false, powerPreference: "high-performance" }} camera={{ fov: 40, near: 0.1, far: 2000 }}>
        <Inner escenario={escenario} luz={luz} plan={plan} animal={img} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
