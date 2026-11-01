// Short «El animal más peligroso de cada departamento»: estado y mundo 3D amarrados a la voz real.
import React, {useLayoutEffect, useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {DEPS, cen, ALTO, VERDES, toXZ} from './Mapa';
import {Rana, Serpiente, Escorpion} from './Animales';
import {SCENES, W, TOTAL} from './timing';
import {clamp, E, EaseName, lerp, prog, rnd, sp, V3} from '../anim';

const S = (i: number) => SCENES[i];
const r = Math.round;
export type Animal = 'rana' | 'serpiente' | 'escorpion';
type Act = {dep: string; animal: Animal; from: number; to: number; instant?: boolean};
// quién está arriba en cada momento (la víbora del cuadro 0 es la misma del final: loop)
export const LOOP = r(W(7, 9)) - 2;
export const ACTS: Act[] = [
  {dep: 'Antioquia', animal: 'serpiente', from: 0, to: r(W(0, 3)) + 4, instant: true},
  {dep: 'Cauca', animal: 'rana', from: S(2).from + 4, to: S(3).from},
  {dep: 'Tolima', animal: 'escorpion', from: S(3).from + 4, to: S(4).from},
  {dep: 'Antioquia', animal: 'serpiente', from: S(5).from + 4, to: S(6).from},
  {dep: 'Antioquia', animal: 'serpiente', from: LOOP, to: TOTAL + 1, instant: true},
];
export const actAt = (f: number) => ACTS.find((a) => f >= a.from && f < a.to) || null;

type Pose = {t: V3; d: number; az: number; el: number};
const o = (t: V3, d: number, az: number, el: number): Pose => ({t, d, az, el});
const up = (p: V3, y: number): V3 => [p[0], p[1] + y, p[2]];
const ANT = cen('Antioquia'), CAU = cen('Cauca'), TOL = cen('Tolima');
const CERCA_VIBORA = o(up(ANT, 1.95), 4.4, 24, 9);
const ANCHO = o([0, 0, 0.4], 46, 0, 72);
const KEYS: {f: number; p: Pose; e: EaseName}[] = [
  {f: 0, p: CERCA_VIBORA, e: 'linear'},
  {f: r(W(0, 1)), p: o(up(ANT, 2.0), 5.4, 24, 12), e: 'linear'},
  {f: r(W(0, 4)), p: ANCHO, e: 'inOut'},
  {f: S(1).from, p: o([0, 0, 0.6], 42, 6, 64), e: 'soft'},
  {f: S(1).from + 6, p: o([0.5, 0, 1.5], 30, -14, 40), e: 'inOut'},
  {f: S(2).from, p: o([0.5, 0, 1.0], 28, -6, 44), e: 'soft'},
  {f: S(2).from + 14, p: o(up(CAU, 1.6), 8.5, 35, 24), e: 'inOut'},
  {f: r(W(2, 7)) - 2, p: o(up(CAU, 1.7), 8.0, 45, 22), e: 'soft'},
  {f: r(W(2, 7)), p: o(up(CAU, 1.85), 4.4, 72, 10), e: 'inOut'},
  {f: r(W(2, 14)) - 2, p: o(up(CAU, 1.85), 4.1, 80, 9), e: 'soft'},
  {f: r(W(2, 15)), p: o(up(CAU, 1.7), 7.0, 40, 20), e: 'inOut'},
  {f: S(3).from, p: o(up(CAU, 1.7), 6.6, 30, 22), e: 'soft'},
  {f: S(3).from + 14, p: o(up(TOL, 1.6), 11, 25, 28), e: 'inOut'},
  {f: r(W(3, 10)) - 2, p: o(up(TOL, 1.6), 10, 40, 26), e: 'soft'},
  {f: r(W(3, 10)) + 4, p: o(up(TOL, 2.6), 5.2, 12, 22), e: 'inOut'},
  {f: S(4).from, p: o(up(TOL, 2.4), 4.8, 0, 22), e: 'soft'},
  {f: S(4).from + 12, p: o([0, 0, 0.6], 40, -8, 58), e: 'inOut'},
  {f: S(5).from, p: o([0, 0, 0.6], 38, 8, 56), e: 'soft'},
  {f: S(5).from + 14, p: o(up(ANT, 1.9), 9.2, -30, 22), e: 'inOut'},
  {f: r(W(5, 9)) - 2, p: o(up(ANT, 1.9), 8.4, -20, 20), e: 'soft'},
  {f: r(W(5, 9)) + 3, p: o(up(ANT, 1.6), 6.8, -2, 9), e: 'inOut'},
  {f: r(W(5, 16)), p: o(up(ANT, 1.6), 6.4, 8, 9), e: 'soft'},
  {f: r(W(5, 17)) + 2, p: o(up(ANT, 2.0), 3.9, 18, 8), e: 'inOut'},
  {f: S(6).from, p: o(up(ANT, 2.0), 3.7, 22, 8), e: 'soft'},
  {f: S(6).from + 14, p: o([0, 0, 1.0], 36, 10, 52), e: 'inOut'},
  {f: S(7).from, p: o([0, 0, 1.0], 34, -8, 54), e: 'soft'},
  {f: LOOP - 1, p: o([0, 0, 0.6], 44, -4, 66), e: 'soft'},
  {f: LOOP, p: CERCA_VIBORA, e: 'linear'},
  {f: TOTAL, p: CERCA_VIBORA, e: 'linear'},
];
export const poseAt = (f: number): Pose => {
  let k = 0;
  while (k < KEYS.length - 1 && f >= KEYS[k + 1].f) k++;
  const a = KEYS[k], b = KEYS[Math.min(k + 1, KEYS.length - 1)];
  const t = a === b ? 0 : E[b.e](clamp((f - a.f) / Math.max(1, b.f - a.f)));
  return {t: [lerp(a.p.t[0], b.p.t[0], t), lerp(a.p.t[1], b.p.t[1], t), lerp(a.p.t[2], b.p.t[2], t)], d: Math.exp(lerp(Math.log(a.p.d), Math.log(b.p.d), t)), az: lerp(a.p.az, b.p.az, t), el: lerp(a.p.el, b.p.el, t)};
};
const camPos = (p: Pose): V3 => {
  const az = (p.az * Math.PI) / 180, el = (p.el * Math.PI) / 180;
  return [p.t[0] + p.d * Math.sin(az) * Math.cos(el), p.t[1] + p.d * Math.sin(el), p.t[2] + p.d * Math.cos(az) * Math.cos(el)];
};
const apply = (c: THREE.PerspectiveCamera, f: number) => {
  const p = poseAt(f);
  c.position.set(...camPos(p));
  c.lookAt(...p.t);
  c.fov = 32; c.aspect = 1080 / 1920; c.near = 0.1; c.far = 400;
  c.updateProjectionMatrix(); c.updateMatrixWorld();
};
const cam = new THREE.PerspectiveCamera(32, 1080 / 1920, 0.1, 400);
export const project = (f: number, pt: V3) => {
  apply(cam, f);
  const v = new THREE.Vector3(...pt).project(cam);
  return {x: (v.x * 0.5 + 0.5) * 1080, y: (-v.y * 0.5 + 0.5) * 1920, behind: v.z > 1};
};
const CamRig: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => apply(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};

const riseOf = (f: number, a: Act | null) => (a ? (a.instant ? 1 : clamp(sp(f, a.from - 6, 11), 0, 1.15)) : 0);
// en «¿De qué departamento eres?» los departamentos se prenden uno por uno
const ola = (f: number, i: number) => {
  const st = S(6).from + 6 + (i % 32) * 2;
  return f >= st && f < S(7).from ? Math.exp(-((f - st) / 10)) : 0;
};

const Departamentos: React.FC<{f: number}> = ({f}) => {
  const geos = useMemo(() => DEPS.map((d) => {
    const shapes = d.rings.map((rr) => new THREE.Shape(rr.map(([lon, lat]) => new THREE.Vector2(lon + 73, lat - 4))));
    const g = new THREE.ExtrudeGeometry(shapes, {depth: ALTO, bevelEnabled: false});
    g.rotateX(-Math.PI / 2);
    return {g, edges: new THREE.EdgesGeometry(g, 25)};
  }), []);
  const act = actAt(f);
  const dim = f >= S(4).from && f < S(5).from ? 0.45 : 1; // el botón de suscribirse manda
  return (
    <>
      {DEPS.map((d, i) => {
        const on = act && act.dep === d.nombre;
        const rise = on ? riseOf(f, act) : 0;
        const w = ola(f, i);
        const base = new THREE.Color(on ? '#ffd23f' : act ? '#2f6e3d' : VERDES[i % VERDES.length]).multiplyScalar(dim).lerp(new THREE.Color('#ffd23f'), w);
        return (
          <group key={d.nombre} position={[0, rise * 1.0 + w * 0.35, 0]}>
            <mesh geometry={geos[i].g} castShadow receiveShadow>
              <meshStandardMaterial color={base} flatShading roughness={0.7} emissive={on ? '#ffb000' : '#000'} emissiveIntensity={on ? 0.25 : 0} />
            </mesh>
            <lineSegments geometry={geos[i].edges}>
              <lineBasicMaterial color="#123018" />
            </lineSegments>
          </group>
        );
      })}
    </>
  );
};

const Pines: React.FC<{f: number}> = ({f}) => (
  <>
    {DEPS.map((d, i) => {
      const st = r(W(0, 3)) + (i % 32) * 1.5;
      if (f < st) return null;
      const s = sp(f, st, 10);
      const [x, z] = toXZ(...d.centro);
      const act = actAt(f);
      const hide = act ? 0 : 1; // en los planos cerrados no tapan al animal
      if (!hide) return null;
      const pulse = 1 + 0.08 * Math.sin(f / 5 + i);
      return (
        <group key={i} position={[x, ALTO + lerp(6, 0, clamp(s, 0, 1)), z]} scale={0.6 * Math.min(1.15, s) * pulse}>
          <mesh position={[0, 0.5, 0]} rotation={[Math.PI, 0, 0]} castShadow>
            <coneGeometry args={[0.22, 1, 8]} />
            <meshStandardMaterial color="#e5341c" flatShading />
          </mesh>
          <mesh position={[0, 1.05, 0]} castShadow>
            <icosahedronGeometry args={[0.32, 1]} />
            <meshStandardMaterial color="#ff4a2e" flatShading emissive="#ff2a10" emissiveIntensity={0.25} />
          </mesh>
        </group>
      );
    })}
  </>
);

const Hojas: React.FC<{f: number}> = ({f}) => {
  const a = actAt(f);
  const st = r(W(5, 9)) - 4;
  if (!a || a.dep !== 'Antioquia' || f < st) return null;
  return (
    <group position={[ANT[0], ALTO + 1.02, ANT[2]]}>
      {Array.from({length: 26}, (_, i) => {
        const ang = rnd(i, 31) * Math.PI * 2, d = 0.6 + rnd(i, 32) * 1.5;
        const fall = clamp(sp(f, st + i, 12), 0, 1);
        return (
          <mesh key={i} position={[Math.cos(ang) * d, lerp(3, 0.03, fall), Math.sin(ang) * d]} rotation={[-Math.PI / 2 + 0.2 * rnd(i, 33), 0, rnd(i, 34) * 6]} scale={[0.22, 0.1, 1]}>
            <circleGeometry args={[1, 6]} />
            <meshStandardMaterial color={i % 3 ? '#8a5a2a' : '#b07a3a'} side={THREE.DoubleSide} flatShading />
          </mesh>
        );
      })}
    </group>
  );
};

const AnimalArriba: React.FC<{f: number}> = ({f}) => {
  const a = actAt(f);
  if (!a) return null;
  const p = cen(a.dep);
  const s = a.instant ? 1 : clamp(sp(f, a.from + 2, 10), 0, 1.2);
  const strike = a.animal === 'serpiente' && f >= r(W(5, 17)) - 3 && f < S(6).from ? Math.sin(clamp((f - (r(W(5, 17)) - 3)) / 12) * Math.PI) : 0;
  const A = a.animal === 'rana' ? <Rana f={f} /> : a.animal === 'serpiente' ? <Serpiente f={f} strike={strike} /> : <Escorpion f={f} />;
  const sc = a.animal === 'serpiente' ? 1.0 : a.animal === 'rana' ? 1.15 : 1.3;
  const rot = a.animal === 'escorpion' ? -0.75 : a.animal === 'serpiente' ? 0.35 : 0.6;
  // veneno: la rana brilla en «veneno»
  const glow = a.animal === 'rana' && f >= r(W(2, 15)) ? 0.5 + 0.5 * Math.sin((f - W(2, 15)) / 3) : 0;
  return (
    <group position={[p[0], ALTO + 1.0, p[2]]} rotation={[0, rot, 0]} scale={sc * s}>
      {A}
      {glow > 0 && <pointLight position={[0.3, 0.6, 0]} intensity={4 * glow} distance={3} color="#7dff4a" />}
    </group>
  );
};

export const Mundo: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <CamRig />
      <hemisphereLight args={['#dff0ff', '#2a3a2a', 1.0]} />
      <directionalLight position={[8, 18, 10]} intensity={2.3} castShadow shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-14} shadow-camera-right={14} shadow-camera-top={14} shadow-camera-bottom={-14} />
      <directionalLight position={[-8, 6, -10]} intensity={0.7} color="#9fd0ff" />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <circleGeometry args={[120, 32]} />
        <meshStandardMaterial color="#1f5b8c" flatShading />
      </mesh>
      <Departamentos f={f} />
      <Pines f={f} />
      <Hojas f={f} />
      <AnimalArriba f={f} />
    </>
  );
};
export {TOTAL};
