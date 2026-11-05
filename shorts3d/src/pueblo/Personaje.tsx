// PERSONAJES DE BLOQUES (estilo juguete de plástico): torso y extremidades rectangulares, cabeza cilíndrica, cara
// 2D simple. Las expresiones son pocas a propósito (feliz, triste, miedo, enojo, sorpresa, llora, dormido) y las
// poses cubren lo que piden los 6 guiones. Don Bruno y los niños salen de aquí (personajes.ts).
import React from 'react';
import * as THREE from 'three';
import type {V3} from './tipos';
import {Cartel} from './Pueblo';

export type Cara = 'feliz' | 'neutral' | 'triste' | 'miedo' | 'enojo' | 'sorpresa' | 'llora' | 'dormido' | 'guino';
export type Pose = 'quieto' | 'camina' | 'corre' | 'saluda' | 'sentado' | 'acostado' | 'llora' | 'abraza' | 'senala' | 'cose' | 'brazos_arriba' | 'agachado' | 'carga';
export type Ropa = {
  piel: string; camisa: string; pantalon: string; zapatos?: string; pelo?: string;
  sombrero?: {tipo: 'gorro' | 'boina' | 'copa' | 'gorra' | 'panadero'; color: string; cinta?: string};
  bufanda?: string; mochila?: string; delantal?: string; banda?: string; bigote?: string; barriga?: boolean;
  falda?: string; coletas?: boolean; lentes?: boolean; corbata?: string; pijama?: boolean;
};
/** SILUETA (episodio 3): el mismo personaje pintado de sombra oscura, para las sombras que actúan solas */
export const SiluetaCtx = React.createContext(false);
const COLOR_SOMBRA = '#0e0b1e';
/** plástico brillante de juguete: barniz (clearcoat) con reflejos del entorno */
const Mate: React.FC<{c: string; o?: number}> = ({c, o = 1}) => React.useContext(SiluetaCtx)
  ? <meshBasicMaterial color={COLOR_SOMBRA} transparent opacity={0.9} depthWrite={false} toneMapped={false} />
  : (
  <meshPhysicalMaterial color={c} roughness={0.32} metalness={0} clearcoat={1} clearcoatRoughness={0.12} envMapIntensity={0.9} transparent={o < 1} opacity={o} depthWrite={o > 0.5} />
);
const Caja: React.FC<{p: V3; s: V3; c: string; o?: number; r?: V3}> = ({p, s, c, o, r}) => (
  <mesh position={p} rotation={r} castShadow={o === undefined || o > 0.5}>
    <boxGeometry args={s} /><Mate c={c} o={o} />
  </mesh>
);
const Negro: React.FC<{o?: number}> = ({o = 1}) => React.useContext(SiluetaCtx)
  ? <meshBasicMaterial color={COLOR_SOMBRA} transparent opacity={0} depthWrite={false} />
  : <meshBasicMaterial color="#111" transparent={o < 1} opacity={o} />;

/** la cara va pegada al frente del cilindro de la cabeza */
const CaraPlana: React.FC<{cara: Cara; f: number; o: number}> = ({cara, f, o}) => {
  const z = 0.243, ojoY = 0.05;
  const parpadeo = cara !== 'dormido' && f % 97 < 3; // parpadeo de vez en cuando
  const ojos = cara === 'dormido' || parpadeo || cara === 'guino'
    ? [-1, 1].map((s) => (cara === 'guino' && s === -1 && !parpadeo
      ? <mesh key={s} position={[s * 0.09, ojoY, z]} scale={[0.038, 0.05, 0.01]}><sphereGeometry args={[1, 12, 8]} /><Negro o={o} /></mesh>
      : <mesh key={s} position={[s * 0.09, ojoY, z]}><boxGeometry args={[0.07, 0.014, 0.01]} /><Negro o={o} /></mesh>))
    : [-1, 1].map((s) => {
      const grande = cara === 'miedo' || cara === 'sorpresa';
      return <mesh key={s} position={[s * 0.09, ojoY, z]} scale={[grande ? 0.05 : 0.036, grande ? 0.065 : 0.05, 0.01]}><sphereGeometry args={[1, 14, 10]} /><Negro o={o} /></mesh>;
    });
  let boca: React.ReactNode;
  if (cara === 'feliz' || cara === 'guino') boca = <mesh position={[0, -0.06, z]} rotation={[0, 0, Math.PI]}><torusGeometry args={[0.07, 0.012, 6, 16, Math.PI]} /><Negro o={o} /></mesh>;
  else if (cara === 'triste' || cara === 'llora') boca = <mesh position={[0, -0.11, z]}><torusGeometry args={[0.06, 0.012, 6, 16, Math.PI]} /><Negro o={o} /></mesh>;
  else if (cara === 'miedo' || cara === 'sorpresa') boca = <mesh position={[0, -0.09, z]}><torusGeometry args={[0.035, 0.012, 6, 16]} /><Negro o={o} /></mesh>;
  else boca = <mesh position={[0, -0.08, z]}><boxGeometry args={[0.1, 0.013, 0.01]} /><Negro o={o} /></mesh>;
  const cejas = cara === 'enojo' || cara === 'triste' || cara === 'llora' || cara === 'miedo';
  return (
    <group>
      {ojos}
      {boca}
      {cejas && [-1, 1].map((s) => <mesh key={s} position={[s * 0.09, ojoY + 0.075, z]} rotation={[0, 0, cara === 'enojo' ? s * 0.45 : -s * 0.35]}><boxGeometry args={[0.08, 0.014, 0.01]} /><Negro o={o} /></mesh>)}
      {cara === 'llora' && [-1, 1].map((s) => {
        const y = ojoY - 0.06 - ((f * 0.012 + (s > 0 ? 0.5 : 0)) % 1) * 0.22;
        return <mesh key={s} position={[s * 0.1, y, z + 0.01]} scale={[0.018, 0.028, 0.012]}><sphereGeometry args={[1, 10, 8]} /><meshStandardMaterial color="#5fc8ff" roughness={0.1} transparent opacity={0.9 * o} /></mesh>;
      })}
    </group>
  );
};

/** brazo con pivote en el hombro */
const Brazo: React.FC<{x: number; rx: number; rz: number; c: string; piel: string; o: number}> = ({x, rx, rz, c, piel, o}) => (
  <group position={[x, 1.36, 0]} rotation={[rx, 0, rz]}>
    <Caja p={[0, -0.27, 0]} s={[0.19, 0.5, 0.2]} c={c} o={o} />
    <Caja p={[0, -0.58, 0]} s={[0.17, 0.14, 0.18]} c={piel} o={o} />
  </group>
);

export type PropsPersonaje = {pos?: V3; rotY?: number; escala?: number; ropa: Ropa; cara?: Cara; pose?: Pose; f?: number; opacidad?: number; mira?: number; nombre?: string};
export const Personaje: React.FC<PropsPersonaje> = ({pos = [0, 0, 0], rotY = 0, escala = 1, ropa, cara = 'neutral', pose = 'quieto', f = 0, opacidad = 1, mira = 0, nombre}) => {
  const o = opacidad;
  const fase = f * (pose === 'corre' ? 0.55 : 0.32);
  const paso = pose === 'camina' ? Math.sin(fase) * 0.55 : pose === 'corre' ? Math.sin(fase) * 0.95 : 0;
  const bob = pose === 'camina' || pose === 'corre' ? Math.abs(Math.sin(fase)) * 0.05 : Math.sin(f / 18) * 0.008;
  let bi = {rx: -paso * 0.8, rz: 0.08}, bd = {rx: paso * 0.8, rz: -0.08};
  let pierna = {i: paso, d: -paso}, bajar = 0, cuerpoRx = pose === 'corre' ? 0.15 : 0;
  if (pose === 'saluda') bd = {rx: 0, rz: -2.6 + Math.sin(f * 0.5) * 0.35};
  if (pose === 'brazos_arriba') { bi = {rx: 0, rz: 2.7 + Math.sin(f * 0.4) * 0.15}; bd = {rx: 0, rz: -2.7 - Math.sin(f * 0.4) * 0.15}; }
  if (pose === 'llora') { bi = {rx: -2.5, rz: -0.35}; bd = {rx: -2.5, rz: 0.35}; }
  if (pose === 'abraza') { bi = {rx: -1.35, rz: -0.5}; bd = {rx: -1.35, rz: 0.5}; }
  if (pose === 'carga') { bi = {rx: -1.1, rz: -0.25}; bd = {rx: -1.1, rz: 0.25}; }
  if (pose === 'senala') bd = {rx: -1.55, rz: 0};
  if (pose === 'cose') { bi = {rx: -1.2, rz: -0.3}; bd = {rx: -1.0 + Math.sin(f * 0.35) * 0.25, rz: 0.3}; }
  if (pose === 'sentado') { pierna = {i: -1.5, d: -1.5}; bajar = 0.42; }
  if (pose === 'agachado') { pierna = {i: -1.2, d: -1.2}; bajar = 0.3; cuerpoRx = 0.3; }
  const acostado = pose === 'acostado';
  const piel = ropa.piel, camisa = ropa.camisa;
  const ancho = ropa.barriga ? 0.66 : 0.52, fondo = ropa.barriga ? 0.42 : 0.28;
  const s = ropa.sombrero;
  return (
    <group position={pos} rotation={[0, rotY, 0]} scale={escala}>
      <group rotation={acostado ? [-Math.PI / 2, 0, 0] : [0, 0, 0]} position={acostado ? [0, 0.15, 0.9] : [0, bob - bajar, 0]}>
        {/* piernas con pivote en la cadera */}
        {[-1, 1].map((l) => (
          <group key={l} position={[l * 0.13, 0.7, 0]} rotation={[l < 0 ? pierna.i : pierna.d, 0, 0]}>
            <Caja p={[0, -0.32, 0]} s={[0.22, 0.6, 0.24]} c={ropa.pijama ? camisa : ropa.pantalon} o={o} />
            <Caja p={[0, -0.64, 0.04]} s={[0.23, 0.1, 0.3]} c={ropa.zapatos ?? '#3a2a20'} o={o} />
          </group>
        ))}
        <group rotation={[cuerpoRx, mira * 0.3, 0]} position={[0, 0.7, 0]}>
          <group position={[0, -0.7, 0]}>
            {/* torso */}
            <Caja p={[0, 1.05, 0]} s={[ancho, 0.7, fondo]} c={camisa} o={o} />
            {ropa.falda && <Caja p={[0, 0.72, 0]} s={[ancho + 0.08, 0.22, fondo + 0.08]} c={ropa.falda} o={o} />}
            {nombre && o > 0.4 && <Cartel p={[0, 1.08, fondo / 2 + 0.02]} w={ancho * 0.9} texto={nombre} fondo={camisa} color="#ffffff" />}
            {ropa.delantal && <Caja p={[0, 0.92, fondo / 2 + 0.01]} s={[ancho * 0.85, 0.62, 0.02]} c={ropa.delantal} o={o} />}
            {ropa.banda && <Caja p={[0, 1.08, fondo / 2 + 0.012]} s={[0.09, 0.85, 0.02]} c={ropa.banda} o={o} r={[0, 0, 0.75]} />}
            {ropa.corbata && <Caja p={[0, 1.15, fondo / 2 + 0.012]} s={[0.07, 0.36, 0.02]} c={ropa.corbata} o={o} />}
            {ropa.mochila && <Caja p={[0, 1.08, -fondo / 2 - 0.1]} s={[0.4, 0.5, 0.2]} c={ropa.mochila} o={o} />}
            <Brazo x={-(ancho / 2 + 0.1)} rx={bi.rx} rz={bi.rz} c={camisa} piel={piel} o={o} />
            <Brazo x={ancho / 2 + 0.1} rx={bd.rx} rz={bd.rz} c={camisa} piel={piel} o={o} />
            {/* cabeza cilíndrica */}
            <group position={[0, 1.62, 0]} rotation={[0, mira, 0]}>
              <mesh castShadow={o > 0.5}><cylinderGeometry args={[0.24, 0.24, 0.42, 28]} /><Mate c={piel} o={o} /></mesh>
              <mesh position={[0, 0.215, 0]}><cylinderGeometry args={[0.2, 0.24, 0.04, 28]} /><Mate c={piel} o={o} /></mesh>
              <CaraPlana cara={cara} f={f} o={o} />
              {ropa.pelo && !s && <mesh position={[0, 0.2, -0.03]}><cylinderGeometry args={[0.25, 0.25, 0.1, 28]} /><Mate c={ropa.pelo} o={o} /></mesh>}
              {ropa.pelo && !s && <Caja p={[0, 0.08, -0.17]} s={[0.46, 0.26, 0.14]} c={ropa.pelo} o={o} />}
              {ropa.coletas && [-1, 1].map((l) => <Caja key={l} p={[l * 0.3, 0.02, -0.05]} s={[0.12, 0.26, 0.12]} c={ropa.pelo ?? '#3a2412'} o={o} />)}
              {ropa.lentes && [-1, 1].map((l) => <mesh key={l} position={[l * 0.09, 0.05, 0.25]}><torusGeometry args={[0.06, 0.012, 6, 18]} /><Negro o={o} /></mesh>)}
              {ropa.bigote && <Caja p={[0, -0.02, 0.255]} s={[0.3, 0.06, 0.04]} c={ropa.bigote} o={o} />}
              {ropa.bigote && [-1, 1].map((l) => <Caja key={l} p={[l * 0.17, 0.0, 0.255]} s={[0.1, 0.05, 0.04]} c={ropa.bigote!} o={o} r={[0, 0, l * 0.5]} />)}
              {s?.tipo === 'copa' && (<>
                <mesh position={[0, 0.24, 0]} castShadow><cylinderGeometry args={[0.36, 0.36, 0.04, 28]} /><Mate c={s.color} o={o} /></mesh>
                <mesh position={[0, 0.47, 0]} castShadow><cylinderGeometry args={[0.22, 0.22, 0.44, 28]} /><Mate c={s.color} o={o} /></mesh>
                <mesh position={[0, 0.31, 0]}><cylinderGeometry args={[0.225, 0.225, 0.08, 28]} /><Mate c={s.cinta ?? '#c0392b'} o={o} /></mesh>
              </>)}
              {s?.tipo === 'gorro' && (<>
                <mesh position={[0, 0.27, 0]} castShadow><cylinderGeometry args={[0.2, 0.26, 0.2, 28]} /><Mate c={s.color} o={o} /></mesh>
                <mesh position={[0, 0.42, 0]}><sphereGeometry args={[0.08, 12, 8]} /><Mate c={s.cinta ?? '#fff'} o={o} /></mesh>
              </>)}
              {s?.tipo === 'boina' && <mesh position={[0.03, 0.25, 0]} scale={[1, 0.3, 1]} castShadow><sphereGeometry args={[0.3, 20, 12]} /><Mate c={s.color} o={o} /></mesh>}
              {s?.tipo === 'gorra' && (<>
                <mesh position={[0, 0.24, 0]}><cylinderGeometry args={[0.25, 0.25, 0.1, 28]} /><Mate c={s.color} o={o} /></mesh>
                <Caja p={[0, 0.2, 0.3]} s={[0.36, 0.03, 0.22]} c={s.color} o={o} />
              </>)}
              {s?.tipo === 'panadero' && <mesh position={[0, 0.36, 0]} castShadow><cylinderGeometry args={[0.28, 0.24, 0.32, 28]} /><Mate c={s.color} o={o} /></mesh>}
            </group>
            {ropa.bufanda && <mesh position={[0, 1.41, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.22, 0.06, 8, 20]} /><Mate c={ropa.bufanda} o={o} /></mesh>}
          </group>
        </group>
      </group>
    </group>
  );
};
/** LA SOMBRA QUE ACTÚA: silueta plana del personaje tendida en el suelo detrás de él (hacia `dir`), con su
 *  propia pose. `levanta` 0..1 la pone de pie (se despega del piso), como en el baile del episodio 3. */
export const Sombra: React.FC<PropsPersonaje & {dir?: number; levanta?: number; largo?: number}> = ({pos = [0, 0, 0], dir = 0, levanta = 0, largo = 1.25, ...p}) => (
  <SiluetaCtx.Provider value={true}>
    <group position={[pos[0], pos[1] + 0.035, pos[2]]} rotation={[0, dir, 0]}>
      <group rotation={[-Math.PI / 2 * (1 - levanta), 0, 0]} scale={[1, largo * (1 - 0.15 * (1 - levanta)), 1]}>
        <group scale={[1, 1, 0.03 + 0.97 * levanta]}>
          <Personaje {...p} pos={[0, 0, 0]} rotY={Math.PI} />
        </group>
      </group>
    </group>
  </SiluetaCtx.Provider>
);
/** altura de la cabeza (para los globos de diálogo) */
export const alturaCabeza = (escala = 1, pose: Pose = 'quieto') => (pose === 'sentado' ? 1.45 : pose === 'acostado' ? 0.5 : 2.0) * escala;
export const _three = THREE;
