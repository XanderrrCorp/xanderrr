// Juguetes de bloques (episodio 5, y reutilizables): osito, dinosaurio, muñeca, soldadito y EL TUERTO, el conejo
// viejo sin un ojo, con una oreja rota y la costura roja que le hace Max.
import React from 'react';
import {Caja} from './Pueblo';
import type {V3} from './tipos';

const Ojo: React.FC<{p: V3; abierto: number; s?: number}> = ({p, abierto, s = 1}) => (
  abierto > 0.15
    ? <mesh position={p} scale={[0.035 * s, 0.045 * s * abierto, 0.01]}><sphereGeometry args={[1, 12, 8]} /><meshBasicMaterial color="#111" /></mesh>
    : <mesh position={p}><boxGeometry args={[0.07 * s, 0.012, 0.01]} /><meshBasicMaterial color="#111" /></mesh>
);
export const Osito: React.FC<{p: V3; rotY?: number; ojos?: number; s?: number}> = ({p, rotY = 0, ojos = 0, s = 1}) => (
  <group position={p} rotation={[0, rotY, 0]} scale={s}>
    <Caja p={[0, 0.2, 0]} s={[0.36, 0.4, 0.28]} c="#b5835a" />
    <Caja p={[0, 0.55, 0]} s={[0.34, 0.3, 0.3]} c="#b5835a" />
    {[-1, 1].map((l) => <Caja key={l} p={[l * 0.14, 0.73, 0]} s={[0.1, 0.1, 0.08]} c="#8a5a3b" />)}
    <Caja p={[0, 0.5, 0.16]} s={[0.14, 0.1, 0.04]} c="#e8c9a7" />
    {[-1, 1].map((l) => <Ojo key={l} p={[l * 0.08, 0.6, 0.155]} abierto={ojos} />)}
    {[-1, 1].map((l) => <Caja key={l} p={[l * 0.22, 0.25, 0]} s={[0.1, 0.25, 0.12]} c="#a27148" />)}
  </group>
);
export const Dino: React.FC<{p: V3; rotY?: number; f: number; color?: string}> = ({p, rotY = 0, f, color = '#52b788'}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    <Caja p={[0, 0.22, 0]} s={[0.24, 0.22, 0.5]} c={color} />
    <Caja p={[0, 0.4, 0.3]} s={[0.18, 0.18, 0.24]} c={color} />
    <Caja p={[0, 0.2, -0.36]} s={[0.1, 0.1, 0.3]} c={color} r={[0.3, 0, 0]} />
    {[0.12, -0.12].map((z) => [-1, 1].map((l) => <Caja key={l + '' + z} p={[l * 0.1, 0.06 + (Math.sin(f * 0.5 + l + z * 10) > 0 ? 0.02 : 0), z]} s={[0.07, 0.12, 0.08]} c={color} />))}
    {[-1, 1].map((l) => <mesh key={l} position={[l * 0.05, 0.45, 0.425]} scale={[0.02, 0.025, 0.01]}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#111" /></mesh>)}
    {[0, 1, 2].map((k) => <Caja key={k} p={[0, 0.36, 0.1 - k * 0.14]} s={[0.03, 0.08, 0.06]} c="#ffd166" />)}
  </group>
);
export const Muneca: React.FC<{p: V3; rotY?: number; vestido?: string; brazos?: number}> = ({p, rotY = 0, vestido = '#ff70a6', brazos = 0}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    <Caja p={[0, 0.18, 0]} s={[0.26, 0.3, 0.2]} c={vestido} />
    <mesh position={[0, 0.45, 0]}><cylinderGeometry args={[0.1, 0.1, 0.2, 16]} /><meshStandardMaterial color="#f7d9c4" roughness={0.6} /></mesh>
    <Caja p={[0, 0.55, -0.02]} s={[0.22, 0.08, 0.22]} c="#ffd60a" />
    {[-1, 1].map((l) => <mesh key={l} position={[l * 0.04, 0.47, 0.1]} scale={[0.015, 0.02, 0.01]}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#111" /></mesh>)}
    {[-1, 1].map((l) => <group key={l} position={[l * 0.16, 0.3, 0]} rotation={[-brazos * 1.4, 0, 0]}><Caja p={[0, -0.08, 0]} s={[0.06, 0.18, 0.06]} c="#f7d9c4" /></group>)}
  </group>
);
export const Soldadito: React.FC<{p: V3; rotY?: number}> = ({p, rotY = 0}) => (
  <group position={p} rotation={[0, rotY, 0]}>
    {[-1, 1].map((l) => <Caja key={l} p={[l * 0.05, 0.09, 0]} s={[0.07, 0.18, 0.08]} c="#1d3557" />)}
    <Caja p={[0, 0.26, 0]} s={[0.18, 0.18, 0.12]} c="#e63946" />
    <mesh position={[0, 0.41, 0]}><cylinderGeometry args={[0.06, 0.06, 0.12, 12]} /><meshStandardMaterial color="#f1c8a0" /></mesh>
    <mesh position={[0, 0.52, 0]}><cylinderGeometry args={[0.065, 0.065, 0.14, 12]} /><meshStandardMaterial color="#111" /></mesh>
    <Caja p={[0.11, 0.3, 0.02]} s={[0.03, 0.34, 0.03]} c="#6c757d" />
  </group>
);
/** EL TUERTO: le falta el ojo izquierdo (una X cosida), la oreja derecha está doblada y rota; `cosido` = costura roja */
export const Conejo: React.FC<{p: V3; rotY?: number; ojo?: number; cosido?: boolean; sucio?: boolean; de_pie?: number; s?: number}> = ({p, rotY = 0, ojo = 0, cosido = false, sucio = false, de_pie = 0, s = 1}) => {
  const pelo = sucio ? '#b9b3a6' : '#e9e3d6';
  return (
    <group position={p} rotation={[-(1 - de_pie) * 0.25, rotY, 0]} scale={s}>
      <Caja p={[0, 0.2, 0]} s={[0.34, 0.38, 0.26]} c={pelo} />
      <Caja p={[0, 0.2, 0.135]} s={[0.2, 0.24, 0.01]} c="#f8c8d2" />
      <Caja p={[0, 0.54, 0]} s={[0.32, 0.3, 0.28]} c={pelo} />
      {/* orejas: la izquierda entera, la derecha rota y doblada */}
      <Caja p={[-0.08, 0.86, 0]} s={[0.08, 0.36, 0.06]} c={pelo} />
      <group position={[0.08, 0.7, 0]} rotation={[0, 0, -1.2]}><Caja p={[0, 0.1, 0]} s={[0.08, 0.2, 0.06]} c={pelo} /></group>
      {cosido && <Caja p={[0.12, 0.73, 0.035]} s={[0.1, 0.02, 0.01]} c="#d62828" r={[0, 0, -1.2]} />}
      {cosido && [0, 1, 2].map((k) => <Caja key={k} p={[0.09 + k * 0.03, 0.71 + k * 0.025, 0.04]} s={[0.012, 0.05, 0.01]} c="#d62828" r={[0, 0, 0.3]} />)}
      {/* ojo que queda (se abre cuando un niño llora) y la X donde faltaba el otro */}
      <Ojo p={[0.07, 0.58, 0.145]} abierto={ojo} />
      {[-1, 1].map((l) => <Caja key={l} p={[-0.07, 0.58, 0.145]} s={[0.07, 0.014, 0.01]} c={cosido ? '#d62828' : '#555'} r={[0, 0, l * 0.8]} />)}
      <Caja p={[0, 0.5, 0.145]} s={[0.05, 0.035, 0.01]} c="#ff8fab" />
      {[-1, 1].map((l) => <Caja key={l} p={[l * 0.21, 0.25 + de_pie * 0.05, 0.02]} s={[0.08, 0.22, 0.08]} c={pelo} />)}
      {[-1, 1].map((l) => <Caja key={l} p={[l * 0.1, 0.03, 0.08]} s={[0.12, 0.06, 0.2]} c={pelo} />)}
    </group>
  );
};
