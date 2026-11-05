// PERSONAJES 2D DE LA SKILL (episodios 2, 6 y 4): el dibujante de la skill (look/toon.ts, bodyFront) pinta al
// personaje en un lienzo de 600x1000 unidades (suela en y = 975) y la tarjeta se pone en el mundo mirando a la
// cámara, iluminada por la escena (cardShade de la skill), sin contorno del mundo (capa NOINK: llevan su propia tinta
// morada) y con una sombra de contacto en el suelo. Igual que en el corto del puente de la skill.
import React, {useMemo} from 'react';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {Pen, bodyFront, Outfit, Expr, FrontOpts} from './look/toon';
import {cardShade, CARD_K} from '../skill_cartoon/bridge/cardshade';
import {NOINK} from '../skill_cartoon/bridge/ink';
import type {V3} from './tipos';

const SU = 0.00216; // metros por unidad de diseño (como la skill: 1000 unidades = 2,16 m)
const K = 1.4;      // resolución del lienzo (600x1000 → 840x1400): nítido en primeros planos
const GEO = (() => { const g = new THREE.PlaneGeometry(600 * SU, 1000 * SU); g.translate(0, (975 - 500) * SU, 0); return g; })();

// caché acotado de dibujos (cada pose/expresión distinta es un lienzo; se reciclan los más viejos)
type Ent = {tex: THREE.CanvasTexture; mat: THREE.MeshLambertMaterial; t: number};
const CACHE = new Map<string, Ent>();
let reloj = 0;
const dibujo = (key: string, draw: (p: Pen) => void) => {
  reloj++;
  const e = CACHE.get(key);
  if (e) { e.t = reloj; return e.mat; }
  if (CACHE.size > 90) { // tira el más viejo
    let viejo: string | null = null, tv = Infinity;
    for (const [k, v] of CACHE) if (v.t < tv) { tv = v.t; viejo = k; }
    if (viejo) { const v = CACHE.get(viejo)!; v.tex.dispose(); v.mat.dispose(); CACHE.delete(viejo); }
  }
  const cv = document.createElement('canvas'); cv.width = Math.round(600 * K); cv.height = Math.round(1000 * K);
  const g = cv.getContext('2d')!; g.setTransform(K, 0, 0, K, 0, 0);
  draw(new Pen(g));
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const mat = cardShade(new THREE.MeshLambertMaterial({map: tex, alphaTest: 0.5, side: THREE.DoubleSide}));
  CACHE.set(key, {tex, mat, t: reloj});
  return mat;
};
const blobTex = (() => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d')!, gr = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  gr.addColorStop(0, 'rgba(40,30,60,0.55)'); gr.addColorStop(1, 'rgba(40,30,60,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();

/** gira la tarjeta hacia la cámara usando su posición EN EL MUNDO (los sets están desplazados a x=200, etc.) */
const _wp = new THREE.Vector3(), _cp = new THREE.Vector3();
const mirar = (m: THREE.Mesh, cam: THREE.Camera) => {
  if (!m.parent) return;
  m.parent.updateWorldMatrix(true, false);
  _wp.copy(m.position).applyMatrix4(m.parent.matrixWorld); cam.getWorldPosition(_cp);
  m.rotation.y = Math.atan2(_cp.x - _wp.x, _cp.z - _wp.z);
  m.updateMatrixWorld(true);
  m.modelViewMatrix.multiplyMatrices(cam.matrixWorldInverse, m.matrixWorld);
  m.normalMatrix.getNormalMatrix(m.modelViewMatrix);
};
export type Props2D = {
  pos: V3; ropa: Outfit; expr?: Expr; f?: number; escala?: number;
  modo?: FrontOpts['mode']; caminar?: boolean; saluda?: boolean; mira?: number; facing?: -1 | 0 | 1; seed?: number;
  /** transparencia (0..1) para efectos; las tarjetas usan recorte, así que < 0.5 = invisible */
  visible?: boolean; inclina?: number;
};
/** un personaje 2D en el mundo, siempre de frente a la cámara (gira solo en vertical) */
export const Carta2D: React.FC<Props2D> = ({pos, ropa, expr = 'neutral', f = 0, escala = 1, modo, caminar, saluda, mira = 0, facing = 0, seed = 1, visible = true, inclina = 0}) => {
  const {camera} = useThree();
  // parpadeo cada 0,5–2,3 s, 4 cuadros (la skill)
  const ciclo = 30 + (seed * 37) % 40, blink = f % ciclo < 4 && expr !== 'sleep';
  const fase = caminar ? Math.round(((f * 0.035) % 1) * 16) / 16 : 0;
  const ola = saluda ? Math.round(Math.sin(f * 0.45) * 4) / 4 : undefined;
  const opts: FrontOpts = {phase: fase, expr, mode: modo ?? (caminar ? 'stroll' : 'stand'), look: mira, blink, facing, seed, wave: ola, tilt: inclina};
  const key = JSON.stringify([ropa, opts]);
  const mat = dibujo(key, (p) => bodyFront(p, ropa, opts));
  const yaw = Math.atan2(camera.position.x - pos[0], camera.position.z - pos[2]);
  const mesh = useMemo(() => {
    const m = new THREE.Mesh(GEO, mat);
    m.layers.set(NOINK); m.receiveShadow = true; m.castShadow = false; m.renderOrder = 1;
    m.onBeforeRender = (r, _s, cam) => { const rt = r.getRenderTarget(); CARD_K.uPx.value = (rt ? rt.height : r.domElement.height) / 1920; mirar(m, cam); };
    return m;
  }, []);
  mesh.material = mat;
  mesh.position.set(...pos); mesh.rotation.set(0, yaw, 0); mesh.scale.setScalar(escala); mesh.visible = visible;
  return (
    <group>
      <primitive object={mesh} dispose={null} />
      {visible && blobTex && (
        <mesh position={[pos[0], pos[1] + 0.015, pos[2]]} rotation={[-Math.PI / 2, 0, 0]} scale={[0.75 * escala, 0.42 * escala, 1]} layers={NOINK} renderOrder={0.5}>
          <planeGeometry args={[1, 1]} /><meshBasicMaterial map={blobTex} transparent depthWrite={false} />
        </mesh>
      )}
    </group>
  );
};
/** tarjeta con un dibujo propio (criaturas, objetos): mismo lienzo de 600x1000 y la misma luz que los personajes */
export const CartaLibre: React.FC<{pos: V3; clave: string; draw: (p: Pen) => void; escala?: number | [number, number]; sombra?: boolean; rotY?: number}> = ({pos, clave, draw, escala = 1, sombra = true, rotY}) => {
  const {camera} = useThree();
  const mat = dibujo('libre|' + clave, draw);
  const mesh = useMemo(() => {
    const m = new THREE.Mesh(GEO, mat);
    m.layers.set(NOINK); m.receiveShadow = true; m.renderOrder = 1;
    m.onBeforeRender = (r, _s, cam) => { const rt = r.getRenderTarget(); CARD_K.uPx.value = (rt ? rt.height : r.domElement.height) / 1920; if (!m.userData.fijo) mirar(m, cam); };
    return m;
  }, []);
  mesh.material = mat; mesh.userData.fijo = rotY !== undefined;
  const [sx, sy] = Array.isArray(escala) ? escala : [escala, escala];
  mesh.position.set(...pos); mesh.rotation.set(0, rotY ?? Math.atan2(camera.position.x - pos[0], camera.position.z - pos[2]), 0); mesh.scale.set(sx, sy, 1);
  return (
    <group>
      <primitive object={mesh} dispose={null} />
      {sombra && blobTex && (
        <mesh position={[pos[0], pos[1] + 0.015, pos[2]]} rotation={[-Math.PI / 2, 0, 0]} scale={[0.8 * sx, 0.45 * sx, 1]} layers={NOINK} renderOrder={0.5}>
          <planeGeometry args={[1, 1]} /><meshBasicMaterial map={blobTex} transparent depthWrite={false} />
        </mesh>
      )}
    </group>
  );
};
export {Pen};
/** altura de la cabeza de una tarjeta (para los globos) */
export const cabeza2D = (pos: V3, escala = 1, nino = false): V3 => [pos[0], pos[1] + (nino ? 1.45 : 1.85) * escala, pos[2]];
