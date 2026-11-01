// Vista previa SIN VOZ del Short «El animal más peligroso de cada departamento»: mapa 3D de Colombia por
// departamentos (Natural Earth, dominio público) + animales 3D. Sirve para ver cómo se ve antes de gastar.
import React, {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import DEP from './departamentos.json';
import {Rana, Serpiente, Escorpion} from './Animales';
import {clamp, E, EaseName, lerp, prog, sp, V3} from '../anim';

type Dep = {nombre: string; rings: number[][][]; centro: [number, number]};
export const DEPS = DEP as unknown as Dep[];
export const toXZ = (lon: number, lat: number): [number, number] => [lon + 73, -(lat - 4)];
export const cen = (n: string): V3 => {
  const d = DEPS.find((x) => x.nombre === n)!;
  const [x, z] = toXZ(...d.centro);
  return [x, 0, z];
};
export const ALTO = 0.3;

// guion visual de la vista previa (12 s)
export const PASOS: {dep: string; from: number; to: number; animal: 'rana' | 'serpiente' | 'escorpion'; nombre: string}[] = [
  {dep: 'Cauca', from: 90, to: 180, animal: 'rana', nombre: 'CAUCA'},
  {dep: 'Antioquia', from: 180, to: 270, animal: 'serpiente', nombre: 'ANTIOQUIA'},
  {dep: 'Tolima', from: 270, to: 360, animal: 'escorpion', nombre: 'TOLIMA'},
];
export const TOTAL_COL = 360;

type Pose = {t: V3; d: number; az: number; el: number};
const o = (t: V3, d: number, az: number, el: number): Pose => ({t, d, az, el});
const up = (p: V3, y: number): V3 => [p[0], p[1] + y, p[2]];
const KEYS: {f: number; p: Pose; e: EaseName}[] = [
  {f: 0, p: o([0, 0, 0.3], 50, 0, 74), e: 'linear'},
  {f: 80, p: o([0, 0, 0.6], 43, 6, 64), e: 'soft'},
  {f: 100, p: o(up(cen('Cauca'), 1.6), 8.5, 35, 24), e: 'inOut'},
  {f: 175, p: o(up(cen('Cauca'), 1.6), 7.2, 60, 20), e: 'soft'},
  {f: 192, p: o(up(cen('Antioquia'), 1.9), 9, -30, 22), e: 'inOut'},
  {f: 265, p: o(up(cen('Antioquia'), 1.9), 7.6, -5, 18), e: 'soft'},
  {f: 282, p: o(up(cen('Tolima'), 1.6), 11, 25, 28), e: 'inOut'},
  {f: 360, p: o(up(cen('Tolima'), 1.6), 9.6, 45, 24), e: 'soft'},
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
const project = (f: number, pt: V3) => {
  apply(cam, f);
  const v = new THREE.Vector3(...pt).project(cam);
  return {x: (v.x * 0.5 + 0.5) * 1080, y: (-v.y * 0.5 + 0.5) * 1920};
};

const CamRig: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => apply(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};

export const VERDES = ['#3f9a52', '#4dab5e', '#5cb86a', '#378a49', '#68c275', '#46a057'];
const activo = (f: number) => PASOS.find((p) => f >= p.from - 10 && f < p.to);

const Departamentos: React.FC<{f: number}> = ({f}) => {
  const geos = useMemo(() => DEPS.map((d) => {
    const shapes = d.rings.map((r) => new THREE.Shape(r.map(([lon, lat]) => new THREE.Vector2(...toXZ(lon, lat).map((v, i) => (i ? -v : v)) as [number, number]))));
    const g = new THREE.ExtrudeGeometry(shapes, {depth: ALTO, bevelEnabled: false});
    g.rotateX(-Math.PI / 2);
    return {g, edges: new THREE.EdgesGeometry(g, 25)};
  }), []);
  const act = activo(f);
  return (
    <>
      {DEPS.map((d, i) => {
        const on = act && act.dep === d.nombre;
        const rise = on ? sp(f, act!.from - 8, 11) * 1.0 : 0;
        const col = on ? '#ffd23f' : act ? '#2f6e3d' : VERDES[i % VERDES.length];
        return (
          <group key={d.nombre} position={[0, rise, 0]}>
            <mesh geometry={geos[i].g} castShadow receiveShadow>
              <meshStandardMaterial color={col} flatShading roughness={0.7} emissive={on ? '#ffb000' : '#000'} emissiveIntensity={on ? 0.25 : 0} />
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
      const st = 12 + i * 2;
      if (f < st) return null;
      const s = sp(f, st, 10);
      const [x, z] = toXZ(...d.centro);
      const act = activo(f);
      const hide = act ? 1 - prog(f, act.from - 10, act.from) : 1;
      if (hide <= 0.01) return null;
      return (
        <group key={i} position={[x, ALTO + lerp(5, 0, clamp(s, 0, 1)), z]} scale={0.6 * Math.min(1.15, s) * hide}>
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

const AnimalEn: React.FC<{f: number}> = ({f}) => {
  const act = activo(f);
  if (!act) return null;
  const p = cen(act.dep);
  const s = clamp(sp(f, act.from + 2, 10), 0, 1.2);
  const A = act.animal === 'rana' ? <Rana f={f} /> : act.animal === 'serpiente' ? <Serpiente f={f} /> : <Escorpion f={f} />;
  const sc = act.animal === 'serpiente' ? 1.0 : act.animal === 'rana' ? 1.15 : 1.3;
  return (
    <group position={[p[0], ALTO + 1.0, p[2]]} rotation={[0, act.animal === 'escorpion' ? -0.75 : 0.6, 0]} scale={sc * s}>
      {A}
    </group>
  );
};

const World: React.FC = () => {
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
      <AnimalEn f={f} />
    </>
  );
};

const FONT = 'Inter, sans-serif';
export const MapaColombia: React.FC = () => {
  const f = useCurrentFrame();
  const act = activo(f);
  const lab = act ? project(f, up(cen(act.dep), 1.0 + 0.3 - 0.9)) : null;
  const titulo = f < 90 ? sp(f, 6, 12) : 0;
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg, #4f8fc8 0%, #173a5e 100%)'}}>
      <ThreeCanvas width={1080} height={1920} shadows flat gl={{antialias: true, alpha: true}} camera={{fov: 32, position: [0, 30, 20]}}>
        <World />
      </ThreeCanvas>
      {titulo > 0 && (
        <div style={{position: 'absolute', top: 250, width: 1080, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 74, color: '#fff',
          WebkitTextStroke: '12px #0b0b0b', paintOrder: 'stroke fill', transform: `scale(${clamp(titulo, 0, 1.15)})`, lineHeight: 1.1}}>
          ¿CUÁL ES EL<br /><span style={{color: '#ffd23f'}}>DE TU DEPARTAMENTO?</span>
        </div>
      )}
      {act && lab && f >= act.from && (
        <div style={{position: 'absolute', left: lab.x, top: lab.y + 40, transform: `translate(-50%, 0) scale(${clamp(sp(f, act.from + 4, 11), 0, 1.15)})`,
          fontFamily: FONT, fontWeight: 900, fontSize: 64, color: '#1a1200', background: '#ffd23f', padding: '10px 30px', borderRadius: 18, boxShadow: '0 10px 30px rgba(0,0,0,0.4)', whiteSpace: 'nowrap'}}>
          {act.nombre}
        </div>
      )}
    </AbsoluteFill>
  );
};
