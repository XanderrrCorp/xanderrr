// Escenarios 3D del Short de la pantera. Solo se monta el escenario del plano actual (cortes secos).
import React, {useLayoutEffect, useMemo, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {Felino} from './Felino';
import {applyPose, planoAt, SET, PLANOS} from './planos';
import {W} from './timing';
import {clamp, lerp, prog, rnd, sp, V3, E} from '../anim';

const CamRig: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => applyPose(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};
const pl = (id: string) => PLANOS.find((p) => p.id.startsWith(id))!;
const NEGRO = '#2a231d', MANCHA_NEGRA = '#030303';
const mixc = (a: string, b: string, t: number) => '#' + new THREE.Color(a).lerp(new THREE.Color(b), clamp(t)).getHexString();

// ---------------- noche ----------------
export const panteraNoche = (f: number) => {
  const p = planoAt(f);
  let x = 0, walk = 0, walkAmt = 0, yaw = 0, light = 0.8, reveal = 0, sweepX: number | null = null, eyes = 1;
  const id = p.id;
  if (id.startsWith('P1-') || id.startsWith('P16')) { yaw = -0.25; light = 1.25; }
  if (id.startsWith('P2')) light = 0.03;
  if (id.startsWith('P3')) light = 0.25;
  if (id.startsWith('P8') || id.startsWith('P9')) {
    const a = pl('P8').from, b = pl('P9').to;
    x = lerp(0, 3.4, (f - a) / (b - a));
    walk = (f - a) * 0.32;
    walkAmt = 1;
    light = id.startsWith('P8') ? lerp(0.8, 0.12, prog(f, a, pl('P8').to, 'inOut')) : 1.0;
  }
  if (id.startsWith('P11')) {
    light = 0.28;
    sweepX = lerp(2.6, -3.0, prog(f, W(4, 3), W(4, 8), 'inOut'));
  }
  if (id.startsWith('P12')) { light = 0.9; reveal = 1; }
  if (id.startsWith('P13')) { light = 1.35; reveal = 1; }
  if (id.startsWith('P14')) { light = 0.9; reveal = 0.7; yaw = lerp(-0.2, -0.85, prog(f, p.from, p.from + 12, 'out')); }
  return {x, walk, walkAmt, yaw, light, reveal, sweepX, eyes};
};

const Noche: React.FC<{f: number}> = ({f}) => {
  const s = panteraNoche(f);
  const trees = useMemo(() => Array.from({length: 22}, (_, i) => {
    const a = -Math.PI * 0.95 + rnd(i, 3) * Math.PI * 0.9, d = 9 + rnd(i, 4) * 22;
    return {x: Math.cos(a) * d, z: Math.sin(a) * d, h: 9 + rnd(i, 5) * 9, r: 2.2 + rnd(i, 6) * 2.5};
  }), []);
  const leaves: [V3, V3, number][] = [[[7.2, 1.0, 2.6], [1.3, 0.12, 0.6], 0.4], [[7.6, 2.5, 1.5], [1.2, 0.1, 0.55], -0.5], [[6.6, 3.2, 3.3], [1.0, 0.1, 0.5], 0.9], [[-3, 0.5, 3.5], [1.6, 0.12, 0.7], 0.2], [[5.0, 0.4, -1.8], [1.4, 0.12, 0.6], 1.2]];
  const L = s.light;
  return (
    <group>
      <fog attach="fog" args={['#07101e', 10, 42]} />
      <hemisphereLight args={['#5a78b8', '#0a0f08', 0.55 * L]} />
      <directionalLight position={[-10, 12, -9]} intensity={1.6 * Math.max(L, 0.35)} color="#aac4ff" castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[8, 6, 10]} intensity={0.9 * L} color="#ffdcae" />
      {s.sweepX !== null && <pointLight position={[s.sweepX, 2.7, 2.3]} intensity={30} distance={4.2} decay={1.6} color="#fff1d6" />}
      <mesh position={[-28, 12, -50]}>
        <icosahedronGeometry args={[4, 2]} />
        <meshBasicMaterial color="#eef3ff" fog={false} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[80, 24]} />
        <meshStandardMaterial color="#13241a" flatShading />
      </mesh>
      {trees.map((t, i) => (
        <group key={i} position={[t.x, 0, t.z]}>
          <mesh position={[0, t.h / 2, 0]}>
            <cylinderGeometry args={[0.35, 0.6, t.h, 6]} />
            <meshStandardMaterial color="#1c140e" flatShading />
          </mesh>
          <mesh position={[0, t.h, 0]} scale={[t.r, t.r * 0.75, t.r]}>
            <icosahedronGeometry args={[1, 0]} />
            <meshStandardMaterial color="#0f2a1c" flatShading />
          </mesh>
        </group>
      ))}
      {leaves.map(([p, sc, r], i) => (
        <mesh key={i} position={p} scale={sc} rotation={[0.2, r, 0.35]}>
          <icosahedronGeometry args={[1, 0]} />
          <meshStandardMaterial color={i % 2 ? '#1d4a2c' : '#26603a'} flatShading />
        </mesh>
      ))}
      {/* rama en el suelo (la pisa sin romperla) */}
      <mesh position={[3.75, 0.07, 0.3]} rotation={[Math.PI / 2, 0, 0.35]} castShadow>
        <cylinderGeometry args={[0.05, 0.07, 1.6, 5]} />
        <meshStandardMaterial color="#5a3d24" flatShading />
      </mesh>
      {Array.from({length: 40}, (_, i) => {
        const p: V3 = [(rnd(i, 7) - 0.5) * 18, 0.4 + rnd(i, 8) * 4 + Math.sin(f / 30 + i) * 0.3, (rnd(i, 9) - 0.5) * 12];
        const on = 0.5 + 0.5 * Math.sin(f / 9 + i * 1.7);
        return (
          <mesh key={i} position={p} scale={0.035}>
            <icosahedronGeometry args={[1, 0]} />
            <meshBasicMaterial color="#d8ff7a" transparent opacity={0.3 + on * 0.6} />
          </mesh>
        );
      })}
      <group position={[s.x, 0, 0]}>
        <Felino coat={NEGRO} spots="jaguar" spotBase={MANCHA_NEGRA} reveal={s.reveal} sweepX={s.sweepX === null ? null : s.sweepX - s.x}
          walk={s.walk} walkAmt={s.walkAmt} yaw={s.yaw} eyes={s.eyes} tail={Math.sin(f / 18)} />
      </group>
    </group>
  );
};

// ---------------- pedestales ----------------
const Pedestales: React.FC<{f: number}> = ({f}) => {
  const P = SET.pedestales;
  const p7 = pl('P7');
  const toBlack = f >= p7.from ? prog(f, p7.from + 4, p7.from + 26, 'inOut') : 0;
  const cats: [number, 'jaguar' | 'leopardo', string, string][] = [[-3.5, 'jaguar', '#c98f35', '#24160a'], [3.5, 'leopardo', '#dcaa50', '#2a1a0c']];
  return (
    <group position={P}>
      <fog attach="fog" args={['#0d1626', 14, 40]} />
      <hemisphereLight args={['#b8cdf0', '#1a1410', 0.9]} />
      <directionalLight position={[4, 12, 9]} intensity={2.2} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-6, 5, -8]} intensity={0.8} color="#9fc0ff" />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[40, 24]} />
        <meshStandardMaterial color="#1b2030" flatShading />
      </mesh>
      {cats.map(([x, sp_, coat, spot], i) => {
        const pop = sp(f, i === 0 ? pl('P4').from : pl('P5').from - 6, 12);
        return (
          <group key={i} position={[x, 0, 0]}>
            <mesh position={[0, 0.3, 0]} receiveShadow castShadow>
              <cylinderGeometry args={[2.1, 2.3, 0.6, 6]} />
              <meshStandardMaterial color="#2c3448" flatShading />
            </mesh>
            <group position={[0, 0.6, 0]} rotation={[0, -0.75 * (x < 0 ? 1 : 1.25), 0]} scale={0.95 * clamp(pop, 0, 1.15)}>
              <group position={[-0.3, 0, 0]}>
                <Felino coat={mixc(coat, NEGRO, toBlack)} spots={sp_} spotBase={mixc(spot, MANCHA_NEGRA, toBlack)} reveal={1} yaw={-0.35} eyes={0.5} tail={Math.sin(f / 20 + i)} />
              </group>
            </group>
          </group>
        );
      })}
    </group>
  );
};

// ---------------- pelo con pigmento ----------------
const NG = 260;
const gran = Array.from({length: NG}, (_, i) => {
  const a = rnd(i, 11) * Math.PI * 2, r = Math.sqrt(rnd(i, 12)) * 0.72;
  return {p: [Math.cos(a) * r, -1.6 + rnd(i, 13) * 6.0, Math.sin(a) * r] as V3, s: 0.07 + rnd(i, 14) * 0.06};
});
const Pelo: React.FC<{f: number}> = ({f}) => {
  const H = SET.pelo, p6 = pl('P6');
  const fill = prog(f, p6.from + 3, p6.to - 2, 'inOut');
  const ref = useRef<THREE.InstancedMesh>(null!);
  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    gran.forEach((g, i) => {
      const t = clamp((fill * 1.25 - i / NG) * 6);
      const from: V3 = [g.p[0] * 0.3, -2.8, g.p[2] * 0.3];
      const pos: V3 = [lerp(from[0], g.p[0], E.out(t)), lerp(from[1], g.p[1], E.out(t)), lerp(from[2], g.p[2], E.out(t))];
      const s = g.s * (t > 0 ? 1 : 0);
      m.makeScale(s, s, s).setPosition(...pos);
      ref.current.setMatrixAt(i, m);
    });
    ref.current.instanceMatrix.needsUpdate = true;
  }, [fill]);
  return (
    <group position={H}>
      <hemisphereLight args={['#cfe0ff', '#202020', 1.0]} />
      <directionalLight position={[5, 8, 8]} intensity={2.0} />
      <pointLight position={[0, 1, 3]} intensity={6} distance={10} color="#ffe2b8" />
      <mesh position={[0, 1.4, 0]}>
        <cylinderGeometry args={[0.85, 0.9, 7, 14, 1, true]} />
        <meshStandardMaterial color={mixc('#d8b07a', '#3a2412', fill)} transparent opacity={0.32} side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh position={[0, -2.7, 0]} scale={[1.35, 1.0, 1.35]}>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color="#c9846c" flatShading transparent opacity={0.85} />
      </mesh>
      <instancedMesh ref={ref} args={[undefined, undefined, NG]}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color="#1a0e06" flatShading />
      </instancedMesh>
    </group>
  );
};

// ---------------- mordida a la tortuga ----------------
const Tortuga: React.FC<{f: number}> = ({f}) => {
  const T = SET.tortuga, p10 = pl('P10');
  const bite = W(3, 17);
  const open = prog(f, p10.from, p10.from + 10, 'out');
  const close = prog(f, bite - 3, bite + 2, 'in');
  const jaw = open * (1 - close);
  const lunge = prog(f, bite - 8, bite + 1, 'in') * 0.35;
  const crack = prog(f, bite, bite + 10, 'out');
  return (
    <group position={T}>
      <fog attach="fog" args={['#07101e', 8, 30]} />
      <hemisphereLight args={['#6f8cc8', '#0a0f08', 0.7]} />
      <directionalLight position={[6, 9, 8]} intensity={1.8} color="#ffe2c0" castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-8, 6, -6]} intensity={1.2} color="#9fc0ff" />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[40, 20]} />
        <meshStandardMaterial color="#1a2a1c" flatShading />
      </mesh>
      <group position={[lunge, 0, 0]}>
        <Felino coat={NEGRO} spots="jaguar" spotBase={MANCHA_NEGRA} reveal={0.15} pitch={-0.5} jaw={jaw} yaw={0} tail={Math.sin(f / 15)} />
      </group>
      <mesh position={[2.55, 0.4, 0]} scale={[0.7, 0.5, 0.6]} castShadow receiveShadow>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color="#4a4a48" flatShading />
      </mesh>
      <group position={[2.5, 0.92, 0]} scale={0.75}>
        {[0, 1].map((h) => (
          <group key={h} position={[0, 0, (h ? 1 : -1) * crack * 0.22]} rotation={[(h ? 1 : -1) * crack * 0.35, 0, 0]}>
            <mesh scale={[0.62, 0.4, 0.52]} castShadow>
              <sphereGeometry args={[1, 9, 5, h ? 0 : Math.PI, Math.PI, 0, Math.PI / 2]} />
              <meshStandardMaterial color="#6a7a34" flatShading side={THREE.DoubleSide} />
            </mesh>
            {[0, 1, 2].map((k) => (
              <mesh key={k} position={[-0.3 + k * 0.3, 0.37, (h ? 1 : -1) * 0.12]} rotation={[-Math.PI / 2 + (h ? -0.5 : 0.5), 0, 0]} scale={[0.15, 0.13, 1]}>
                <circleGeometry args={[1, 6]} />
                <meshStandardMaterial color="#4a5520" flatShading side={THREE.DoubleSide} />
              </mesh>
            ))}
          </group>
        ))}
        <mesh position={[0.62, -0.02, 0]} scale={[0.16, 0.12, 0.13]}>
          <icosahedronGeometry args={[1, 1]} />
          <meshStandardMaterial color="#8a9a56" flatShading />
        </mesh>
        {crack > 0 && crack < 1 && Array.from({length: 10}, (_, i) => {
          const a = (i / 10) * Math.PI * 2;
          const pp: V3 = [Math.cos(a) * 0.3 * (1 + crack * 2), 0.3 + crack * 0.8 - crack * crack * 0.9, Math.sin(a) * 0.3 * (1 + crack * 2)];
          return (
            <mesh key={i} position={pp} scale={0.07 * (1 - crack)} rotation={[i, crack * 6, 0]}>
              <tetrahedronGeometry args={[1, 0]} />
              <meshStandardMaterial color="#56642a" flatShading />
            </mesh>
          );
        })}
      </group>
    </group>
  );
};

// ---------------- vacío del llamado final ----------------
const Vacio: React.FC<{f: number}> = ({f}) => (
  <group position={SET.vacio}>
    <ambientLight intensity={0.2} />
    {Array.from({length: 50}, (_, i) => (
      <mesh key={i} position={[(rnd(i, 21) - 0.5) * 10, -3 + rnd(i, 22) * 9 + Math.sin(f / 25 + i) * 0.2, (rnd(i, 23) - 0.5) * 6]} scale={0.03}>
        <icosahedronGeometry args={[1, 0]} />
        <meshBasicMaterial color="#8fa8d8" transparent opacity={0.4} />
      </mesh>
    ))}
  </group>
);

export const World: React.FC = () => {
  const f = useCurrentFrame();
  const set = planoAt(f).set;
  return (
    <>
      <CamRig />
      {set === 'noche' && <Noche f={f} />}
      {set === 'pedestales' && <Pedestales f={f} />}
      {set === 'pelo' && <Pelo f={f} />}
      {set === 'tortuga' && <Tortuga f={f} />}
      {set === 'vacio' && <Vacio f={f} />}
    </>
  );
};
