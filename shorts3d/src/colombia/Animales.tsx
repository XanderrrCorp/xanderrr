// Animales 3D low-poly del Short de los departamentos (código propio). Todos miran hacia +x.
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {V3} from '../anim';

const M: React.FC<{c: string; r?: number; m?: number; e?: string; ei?: number}> = ({c, r = 0.45, m = 0.05, e = '#000', ei = 0}) => (
  <meshStandardMaterial color={c} flatShading roughness={r} metalness={m} emissive={e} emissiveIntensity={ei} />
);
const Bola: React.FC<{p: V3; s: V3; c: string; r?: V3; d?: number; rough?: number}> = ({p, s, c, r = [0, 0, 0], d = 1, rough}) => (
  <mesh position={p} scale={s} rotation={r} castShadow>
    <icosahedronGeometry args={[1, d]} />
    <M c={c} r={rough} />
  </mesh>
);

/** Rana dorada (Phyllobates terribilis): amarilla brillante, ojos negros grandes. Mide ~1,6 de largo. */
export const Rana: React.FC<{f: number; hop?: number}> = ({f, hop = 0}) => {
  const C = '#ffcc1f', D = '#e0a400';
  const breathe = 1 + 0.03 * Math.sin(f / 5);
  return (
    <group position={[0, hop, 0]}>
      <Bola p={[0, 0.42, 0]} s={[0.62, 0.36 * breathe, 0.5]} c={C} rough={0.25} />
      <Bola p={[0.45, 0.55, 0]} s={[0.4, 0.28, 0.42]} c={C} rough={0.25} />
      {[1, -1].map((sd) => (
        <group key={sd}>
          <Bola p={[0.56, 0.74, sd * 0.25]} s={[0.13, 0.11, 0.12]} c={C} rough={0.25} />
          <mesh position={[0.63, 0.76, sd * 0.3]} scale={0.095} castShadow>
            <icosahedronGeometry args={[1, 1]} />
            <meshStandardMaterial color="#0a0a0a" roughness={0.1} metalness={0.3} flatShading />
          </mesh>
          <mesh position={[0.69, 0.8, sd * 0.33]} scale={0.03}>
            <icosahedronGeometry args={[1, 0]} />
            <meshBasicMaterial color="#ffffff" />
          </mesh>
          {/* patas de adelante */}
          <Bola p={[0.55, 0.18, sd * 0.36]} s={[0.1, 0.22, 0.1]} r={[sd * 0.4, 0, -0.3]} c={D} />
          <Bola p={[0.66, 0.04, sd * 0.42]} s={[0.12, 0.04, 0.1]} c={D} />
          {/* patas de atrás, dobladas */}
          <Bola p={[-0.35, 0.25, sd * 0.42]} s={[0.36, 0.18, 0.16]} r={[0, sd * 0.4, 0.4]} c={C} />
          <Bola p={[-0.05, 0.08, sd * 0.52]} s={[0.28, 0.06, 0.1]} r={[0, sd * -0.5, 0]} c={D} />
        </group>
      ))}
      <mesh position={[0.84, 0.47, 0]} scale={[0.02, 0.02, 0.18]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshBasicMaterial color="#5a3a00" />
      </mesh>
    </group>
  );
};

/** Mapaná / talla X (Bothrops asper): enrollada, cabeza triangular levantada, manchas en X. */
export const Serpiente: React.FC<{f: number; strike?: number}> = ({f, strike = 0}) => {
  const segs = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 120; i++) {
      const t = i / 120;
      const turns = 2.3, a = t * turns * Math.PI * 2;
      const r = 1.1 - t * 0.55;
      const lift = t < 0.82 ? 0.16 + t * 0.05 : 0.2 + (t - 0.82) * 4.2;
      pts.push(new THREE.Vector3(Math.cos(a) * r * (t < 0.82 ? 1 : 1 - (t - 0.82) * 3), lift, Math.sin(a) * r * (t < 0.82 ? 1 : 1 - (t - 0.82) * 3)));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const N = 26;
    return Array.from({length: N}, (_, k) => {
      const a = k / N, b = (k + 1) / N;
      const sub = Array.from({length: 8}, (_, j) => curve.getPointAt(a + ((b - a) * j) / 7));
      const rad = 0.17 * (1 - a * 0.45);
      return {geo: new THREE.TubeGeometry(new THREE.CatmullRomCurve3(sub), 6, rad, 7, false), dark: k % 2 === 1};
    }).concat([]);
  }, []);
  const tipCurve = useMemo(() => segs, [segs]);
  const sway = 0.08 * Math.sin(f / 7);
  return (
    <group>
      {tipCurve.map((s, i) => (
        <mesh key={i} geometry={s.geo} castShadow>
          <M c={s.dark ? '#3a2a18' : '#8a7448'} r={0.5} />
        </mesh>
      ))}
      {/* cabeza triangular */}
      <group position={[0.02 + strike * 0.9, 1.0 + sway, 0.05]} rotation={[0, 0, -0.35 + strike * 0.3]}>
        <Bola p={[0.1, 0, 0]} s={[0.3, 0.13, 0.24]} c="#6e5a36" />
        <Bola p={[0.33, -0.01, 0]} s={[0.15, 0.09, 0.15]} c="#7c6640" />
        <Bola p={[0.1, 0.06, 0]} s={[0.24, 0.07, 0.17]} c="#3a2a18" />
        {[1, -1].map((sd) => (
          <mesh key={sd} position={[0.26, 0.06, sd * 0.13]} scale={0.04}>
            <icosahedronGeometry args={[1, 0]} />
            <meshBasicMaterial color="#d8b000" />
          </mesh>
        ))}
        {Math.sin(f / 4) > 0.2 && (
          <mesh position={[0.56, -0.03, 0]} scale={[0.22, 0.012, 0.03]}>
            <boxGeometry args={[1, 1, 1]} />
            <meshBasicMaterial color="#d0202a" />
          </mesh>
        )}
      </group>
    </group>
  );
};

/** Escorpión (Tityus): cuerpo segmentado, pinzas y cola curvada con aguijón. */
export const Escorpion: React.FC<{f: number}> = ({f}) => {
  const C = '#3b2414', D = '#24150b', P = '#5a3a20';
  const tail = Array.from({length: 6}, (_, i) => i);
  const wag = 0.08 * Math.sin(f / 6);
  return (
    <group>
      <Bola p={[0.45, 0.22, 0]} s={[0.36, 0.13, 0.3]} c={C} rough={0.3} />
      {[0, 1, 2, 3, 4].map((i) => (
        <Bola key={i} p={[0.1 - i * 0.2, 0.22, 0]} s={[0.13, 0.12, 0.3 - i * 0.02]} c={i % 2 ? D : C} rough={0.3} />
      ))}
      {/* cola que sube y se curva hacia adelante, con el aguijón al final */}
      {(() => {
        const els: React.ReactNode[] = [];
        let x = -0.78, y = 0.24, a = 0.25;
        for (let i = 0; i < 6; i++) {
          a += 0.48 + wag;
          x -= Math.cos(a) * 0.19;
          y += Math.sin(a) * 0.19;
          els.push(<Bola key={i} p={[x, y, 0]} s={[0.1, 0.09, 0.09]} c={i % 2 ? D : C} rough={0.3} />);
        }
        a += 0.5;
        const tx = x - Math.cos(a) * 0.17, ty = y + Math.sin(a) * 0.17;
        els.push(<Bola key="b" p={[tx, ty, 0]} s={[0.13, 0.1, 0.1]} c="#7a4a20" />);
        els.push(
          <mesh key="ag" position={[tx - Math.cos(a + 0.6) * 0.14, ty + Math.sin(a + 0.6) * 0.14, 0]} rotation={[0, 0, Math.PI / 2 - (a + 0.6)]}>
            <coneGeometry args={[0.04, 0.2, 5]} />
            <M c="#140a04" />
          </mesh>,
        );
        return els;
      })()}
      {/* pinzas */}
      {[1, -1].map((sd) => (
        <group key={sd} position={[0.7, 0.22, sd * 0.2]} rotation={[0, sd * -0.5, 0]}>
          <mesh position={[0.25, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.05, 0.05, 0.5, 5]} />
            <M c={P} />
          </mesh>
          <Bola p={[0.6, 0.02, 0]} s={[0.24, 0.11, 0.13]} c={P} rough={0.3} />
          <mesh position={[0.86, 0.02, 0.04 * sd]} rotation={[0, sd * 0.3, -Math.PI / 2]}>
            <coneGeometry args={[0.05, 0.22, 5]} />
            <M c={D} />
          </mesh>
        </group>
      ))}
      {/* 8 patas */}
      {[0, 1, 2, 3].map((i) => [1, -1].map((sd) => (
        <group key={i + '_' + sd} position={[0.35 - i * 0.2, 0.2, sd * 0.25]} rotation={[sd * -0.9, 0, 0.2 * Math.sin(f / 5 + i)]}>
          <mesh position={[0, -0.18, 0]}>
            <cylinderGeometry args={[0.022, 0.016, 0.4, 4]} />
            <M c={P} />
          </mesh>
        </group>
      )))}
    </group>
  );
};
