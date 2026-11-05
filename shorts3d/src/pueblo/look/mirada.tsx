// LA MIRADA DE LA SKILL «cartoon-3d-short» (MIT, ver src/skill_cartoon/LICENSE) aplicada al pueblo: sombreado de dos
// tonos en todo el mundo, sol relativo a la cámara y fijo por plano, cielo pintado por elevación, nubes pintadas,
// niebla = color del horizonte, y la cadena de posproceso de la skill: tinta → desenfoque de lente → brillo →
// tono NEUTRAL → gradación. Se reutilizan sus archivos tal cual (src/skill_cartoon/bridge/*); aquí solo se conectan.
// Añadido nuestro: un ajuste de NOCHE (la skill solo trae día y atardecer): azul oscuro, nunca negro.
import React, {useEffect, useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import {EffectComposer} from '@react-three/postprocessing';
import {BlendFunction, BloomEffect, ToneMappingEffect, ToneMappingMode} from 'postprocessing';
import * as THREE from 'three';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {InkPass, noInkFallback, NOINK} from '../../skill_cartoon/bridge/ink';
import {LensBlur} from '../../skill_cartoon/bridge/lensblur';
import {GradeEffect, GRADES} from '../../skill_cartoon/bridge/grade';
import {LIGHTS, LOOK, LightPreset, WorldLook} from '../../skill_cartoon/bridge/lights';
import {TONE, CHAR, twoTone, untone} from '../../skill_cartoon/bridge/shade';
import {cloudHD} from '../../skill_cartoon/bridge/paint';
import type {Cam, V3} from '../tipos';

export {NOINK};
// ---------- ajuste de noche (nuestro) ----------
export const LUZ_NOCHE: LightPreset = {
  ...LIGHTS.day, az: 60, el: 38,
  lit: [0.62, 0.72, 1.18], shade: [0.2, 0.22, 0.42], lift: [0.06, 0.08, 0.2], lambert: 0.35, sideK: 0.84, term: 0.25,
  charTint: [0.8, 0.86, 1.1], charShade: 0.86, charGrad: 0.08, bodyGrad: 0.2, sideTint: [0.85, 0.88, 1.0],
  top: '#16204a', hor: '#3b5a9a', fog: '#2d4580', fogNear: 25, fogFar: 140, sunCol: '#b8c8ff', sunI: 1.3, sky: '#5a76c0', ground: '#1e2440', hemiI: 0.6,
};
export const MIRA_NOCHE: WorldLook = {
  ...LOOK.day,
  sky: {c: ['#3b5a9a', '#33508f', '#283f7c', '#1f3166', '#16234e'], e: [0, 4, 10, 20, 45]},
  cloud: {lit: '#8fa3d6', mid: '#6a7fb8', shade: '#4a5c96'},
  sat: 1.05,
};
const GRADE_NOCHE = {...GRADES.day, vig: [0.18, 0.4] as [number, number]};

// ---------- materiales del mundo: Lambert de dos tonos (cacheados por color) ----------
const cache = new Map<string, THREE.MeshLambertMaterial>();
export const matMundo = (c: string, o: {e?: string; ei?: number; map?: THREE.Texture} = {}) => {
  const k = `${c}|${o.e ?? ''}|${o.ei ?? 0}|${o.map?.uuid ?? ''}`;
  let m = cache.get(k);
  if (!m) {
    m = twoTone(new THREE.MeshLambertMaterial({color: c, map: o.map ?? null, emissive: o.e ?? '#000000', emissiveIntensity: o.ei ?? 0}));
    cache.set(k, m);
  }
  return m;
};

// ---------- cielo, sol, nubes ----------
const skyMat = new THREE.ShaderMaterial({
  uniforms: {c0: {value: new THREE.Color()}, c1: {value: new THREE.Color()}, c2: {value: new THREE.Color()}, c3: {value: new THREE.Color()}, c4: {value: new THREE.Color()}, e: {value: new THREE.Vector4()}},
  vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `uniform vec3 c0, c1, c2, c3, c4; uniform vec4 e; varying vec3 vP;
    void main(){ float el = asin(clamp(normalize(vP).y, -1.0, 1.0));
      vec3 c = mix(c0, c1, smoothstep(0.0, e.x, el)); c = mix(c, c2, smoothstep(e.x, e.y, el));
      c = mix(c, c3, smoothstep(e.y, e.z, el)); c = mix(c, c4, smoothstep(e.z, e.w, el)); gl_FragColor = vec4(c, 1.0); }`,
  side: THREE.BackSide, depthWrite: false, fog: false,
});

/** desenfoque por tipo de plano (la skill: primeros planos 12–14 px, planos medios 10–12, generales 0) */
export const dofDe = (cam: Cam) => cam.dof ?? ((cam.fov ?? 40) <= 34 ? 13 : (cam.fov ?? 40) <= 42 ? 10 : 0);

type Props = {cam: Cam; noche?: boolean; interior?: boolean};
export const Mirada: React.FC<Props> = ({cam, noche, interior}) => {
  const f = useCurrentFrame();
  const {camera, scene, gl} = useThree();
  const L = noche ? LUZ_NOCHE : LIGHTS.day, K = noche ? MIRA_NOCHE : LOOK.day;
  const rig = useMemo(() => {
    const root = new THREE.Group();
    const sky = new THREE.Mesh(new THREE.SphereGeometry(400, 48, 24), skyMat);
    sky.renderOrder = -1; sky.frustumCulled = false; sky.layers.set(NOINK); root.add(sky);
    const sun = new THREE.DirectionalLight('#fff3e0', 2.8); sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
    const hemi = new THREE.HemisphereLight('#dcecff', '#b49a78', 0.55);
    // relleno desde la cámara: el mundo de dos tonos lo ignora (solo usa el sol), así que solo ilumina a los
    // personajes de plástico, que si no quedan con la cara en sombra
    const relleno = new THREE.DirectionalLight('#fff4e8', 1.6);
    root.add(sun, sun.target, hemi, relleno, relleno.target);
    const nubes = [0, 1, 2, 3, 4, 5].map((i) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({map: cloudHD(i % 4), transparent: true, depthWrite: false, fog: false}));
      const a = (i / 6) * Math.PI * 2 + 0.4, d = 150 + (i % 3) * 25, w = 60 + (i % 3) * 18;
      m.position.set(Math.cos(a) * d, 38 + (i % 2) * 12, Math.sin(a) * d - 20); m.scale.set(w, w / 2, 1);
      m.layers.set(NOINK); root.add(m);
      return m;
    });
    const fog = new THREE.Fog('#b8d0ec', 25, 300);
    return {root, sky, sun, hemi, relleno, nubes, fog};
  }, []);
  // reflejos para el plástico brillante de los personajes de bloques (sin bajar ningún HDRI)
  useEffect(() => {
    const pm = new THREE.PMREMGenerator(gl);
    const env = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    return () => { env.dispose(); pm.dispose(); };
  }, [gl, scene]);
  // ---- cámara del plano ----
  const c = camera as THREE.PerspectiveCamera;
  c.position.set(...cam.pos); c.up.set(0, 1, 0); c.lookAt(...cam.look); c.fov = cam.fov ?? 40;
  c.near = 0.05; c.far = 800; c.updateProjectionMatrix(); c.updateMatrixWorld(); c.layers.enable(NOINK);
  // ---- sol relativo a la cámara (fijo por plano: depende solo de la cámara, que es fija) ----
  const fx0 = cam.look[0] - cam.pos[0], fz0 = cam.look[2] - cam.pos[2], n = Math.hypot(fx0, fz0) || 1, fx = fx0 / n, fz = fz0 / n;
  const az = THREE.MathUtils.degToRad(L.az), el = THREE.MathUtils.degToRad(L.el);
  const hx = fx * Math.cos(az) - fz * Math.sin(az), hz = fz * Math.cos(az) + fx * Math.sin(az);
  const sunDir = new THREE.Vector3(hx * Math.cos(el), Math.sin(el), hz * Math.cos(el)).normalize();
  const focus = new THREE.Vector3(...cam.look), dist = c.position.distanceTo(focus);
  const Rr = THREE.MathUtils.clamp(dist * 1.15 + 7, 10, 60);
  rig.sun.position.copy(focus).addScaledVector(sunDir, 150); rig.sun.target.position.copy(focus);
  const sc = rig.sun.shadow.camera; sc.left = -Rr; sc.right = Rr; sc.top = Rr; sc.bottom = -Rr; sc.near = 20; sc.far = 320; sc.updateProjectionMatrix();
  rig.sun.shadow.bias = L.bias; rig.sun.shadow.normalBias = L.normalBias * (Rr / 12);
  rig.sun.color.set(L.sunCol); rig.sun.intensity = L.sunI;
  rig.relleno.position.copy(c.position).add(new THREE.Vector3(-1.5, 2.5, 0)); rig.relleno.target.position.copy(focus);
  rig.relleno.intensity = noche ? 1.1 : 1.7; rig.relleno.color.set(noche ? '#c8d4ff' : '#fff4e8');
  rig.hemi.color.set(L.sky); rig.hemi.groundColor.set(L.ground); rig.hemi.intensity = (noche ? 0.9 : 1.1) * (interior ? 1.2 : 1);
  TONE.uLitCol.value.set(...L.lit); TONE.uShadeCol.value.set(...L.shade); TONE.uShadeLift.value.set(...L.lift);
  TONE.uLambert.value = L.lambert; TONE.uSideK.value = L.sideK; TONE.uTerm.value = L.term; TONE.uBounce.value.set(...K.bounce); TONE.uSat.value = K.sat;
  CHAR.uCharTint.value.set(...L.charTint); CHAR.uCharShade.value = L.charShade; CHAR.uGrad.value = L.charGrad;
  CHAR.uBodyGrad.value = L.bodyGrad; CHAR.uSideTint.value.set(...L.sideTint);
  const su = skyMat.uniforms;
  K.sky.c.forEach((h, i) => untone(h, su['c' + i].value));
  const e = K.sky.e.map((d) => THREE.MathUtils.degToRad(d)); su.e.value.set(e[1], e[2], e[3], e[4]);
  rig.sky.position.copy(c.position);
  untone(L.fog, rig.fog.color); rig.fog.near = L.fogNear; rig.fog.far = noche ? L.fogFar : 220;
  scene.fog = rig.fog; scene.background = null;
  rig.nubes.forEach((m, i) => { m.visible = !interior; (m.material as THREE.MeshBasicMaterial).map = cloudHD(i % 4, K.cloud); m.lookAt(c.position); m.position.x += Math.sin(f / 300 + i) * 0.02; });
  // ---- posproceso de la skill ----
  const fxs = useMemo(() => ({
    ink: new InkPass(scene, c),
    lens: new LensBlur({maxCoC: 24, nearScale: 1.2}),
    bloom: (() => {
      const b = new BloomEffect({blendFunction: BlendFunction.ADD, intensity: 0.5, luminanceThreshold: 1.0, luminanceSmoothing: 0.2, mipmapBlur: true, levels: 6, radius: 0.6});
      const mip = b.mipmapBlurPass, setSize = mip.setSize.bind(mip);
      mip.setSize = (w: number, h: number) => setSize(Math.round((1920 * w) / Math.max(h, 1)), 1920);
      return b;
    })(),
    tone: new ToneMappingEffect({mode: ToneMappingMode.NEUTRAL}),
    grade: new GradeEffect(GRADES.day, 1),
  }), [scene, c]);
  useEffect(() => () => fxs.ink.dispose(), [fxs]);
  fxs.grade.set(noche ? GRADE_NOCHE : GRADES.day);
  fxs.grade.amount = noche ? 0.7 : 1;
  const fwd = new THREE.Vector3(); c.getWorldDirection(fwd);
  fxs.lens.focus = Math.max(0.3, new THREE.Vector3(...(cam.foco ?? cam.look)).sub(c.position).dot(fwd));
  fxs.lens.cInf = dofDe(cam);
  noInkFallback(scene);
  return (
    <>
      <primitive object={rig.root} dispose={null} />
      <EffectComposer multisampling={4}>
        <primitive object={fxs.ink} dispose={null} />
        <primitive object={fxs.lens.pre} dispose={null} />
        <primitive object={fxs.lens.main} dispose={null} />
        <primitive object={fxs.bloom} dispose={null} />
        <primitive object={fxs.tone} dispose={null} />
        <primitive object={fxs.grade} dispose={null} />
      </EffectComposer>
    </>
  );
};
export type {V3};
