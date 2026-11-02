// Personajes low-poly. Los humanos en tonos CÁLIDOS; la cosa siempre más FRÍA y pálida (regla de la ficha).
import React from 'react';
import {SPEC} from './spec';
import {V3} from '../anim';

const C = SPEC.color;
const M: React.FC<{c: string; e?: string; ei?: number}> = ({c, e, ei}) => (
  <meshStandardMaterial color={c} flatShading roughness={0.85} emissive={e ?? '#000000'} emissiveIntensity={ei ?? 0} />
);
const Caja: React.FC<{p: V3; s: V3; c: string; r?: V3}> = ({p, s, c, r}) => (
  <mesh position={p} rotation={r} castShadow><boxGeometry args={s} /><M c={c} /></mesh>
);
const Bola: React.FC<{p: V3; s: V3; c: string; d?: number}> = ({p, s, c, d = 1}) => (
  <mesh position={p} scale={s} castShadow><icosahedronGeometry args={[1, d]} /><M c={c} /></mesh>
);
/** brazo: pivote en el hombro, cuelga hacia -y */
const Brazo: React.FC<{p: V3; largo: number; grosor: number; c: string; mano: string; rx: number; rz: number}> = ({p, largo, grosor, c, mano, rx, rz}) => (
  <group position={p} rotation={[rx, 0, rz]}>
    <mesh position={[0, -largo / 2, 0]} castShadow><cylinderGeometry args={[grosor, grosor * 0.8, largo, 5]} /><M c={c} /></mesh>
    <Bola p={[0, -largo - grosor, 0]} s={[grosor * 1.3, grosor * 1.6, grosor * 1.1]} c={mano} d={0} />
  </group>
);

/** Tomás, 12 años. `sentado` 0..1, `mano` 0..1 (hacia el cerrojo), `boca` tapada, `miedo` abre los ojos */
export const Tomas: React.FC<{pos: V3; yaw: number; sentado: number; paso: number; mano: number; miedo: number}> = ({pos, yaw, sentado, paso, mano, miedo}) => {
  const baja = sentado * 0.32;
  const piernas = Math.sin(paso) * 0.5;
  return (
    <group position={pos} rotation={[0, yaw, 0]}>
      <group position={[0, -baja, 0]}>
        {/* piernas */}
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.09, 0.62, 0]} rotation={[sentado * -1.4 + s * piernas, 0, 0]}>
            <mesh position={[0, -0.3, 0]} castShadow><cylinderGeometry args={[0.065, 0.055, 0.6, 5]} /><M c="#2c3550" /></mesh>
          </group>
        ))}
        {/* torso con suéter */}
        <mesh position={[0, 0.86, 0]} castShadow><cylinderGeometry args={[0.15, 0.17, 0.48, 6]} /><M c={C.ropa} /></mesh>
        <Brazo p={[-0.2, 1.06, 0]} largo={0.4} grosor={0.05} c={C.ropa} mano={C.piel} rx={0.15} rz={0.12} />
        <Brazo p={[0.2, 1.06, 0]} largo={0.4} grosor={0.05} c={C.ropa} mano={C.piel} rx={-mano * 1.5 + 0.1} rz={-0.12 + mano * 0.25} />
        {/* cabeza */}
        <group position={[0, 1.25, 0]}>
          <Bola p={[0, 0, 0]} s={[0.13, 0.15, 0.13]} c={C.piel} />
          <Bola p={[0, 0.07, -0.02]} s={[0.14, 0.1, 0.14]} c="#2a1a12" />
          {[-1, 1].map((s) => (
            <group key={s} position={[s * 0.05, 0.01, 0.115]}>
              <mesh scale={[0.026 + miedo * 0.008, 0.026 + miedo * 0.01, 0.01]}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#f4efe6" /></mesh>
              <mesh position={[0, 0, 0.008]} scale={0.012}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#1a0f08" /></mesh>
            </group>
          ))}
          <mesh position={[0, -0.075, 0.12]} scale={[0.03, 0.012 + miedo * 0.012, 0.01]}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#5a2418" /></mesh>
        </group>
      </group>
    </group>
  );
};

/** la madre: camisón cálido; `mano` 0..1 tapa la boca de Tomás */
export const Madre: React.FC<{pos: V3; mano: number}> = ({pos, mano}) => (
  <group position={pos}>
    <mesh position={[0, 0.62, 0]} castShadow><coneGeometry args={[0.3, 1.25, 7]} /><M c={C.madre} /></mesh>
    <mesh position={[0, 1.2, 0]} castShadow><cylinderGeometry args={[0.13, 0.16, 0.36, 6]} /><M c={C.madre} /></mesh>
    <Brazo p={[0.17, 1.33, 0.02]} largo={0.46} grosor={0.045} c={C.madre} mano={C.piel} rx={-mano * 1.2} rz={0.5 * mano} />
    <Brazo p={[-0.17, 1.33, 0.02]} largo={0.46} grosor={0.045} c={C.madre} mano={C.piel} rx={-mano * 0.9} rz={-0.2} />
    <group position={[0, 1.55, 0]}>
      <Bola p={[0, 0, 0]} s={[0.12, 0.14, 0.12]} c={C.piel} />
      <Bola p={[0, 0.05, -0.07]} s={[0.135, 0.17, 0.11]} c="#3a2216" />
      <Bola p={[0, -0.12, -0.09]} s={[0.12, 0.16, 0.06]} c="#3a2216" />
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.045, 0.01, 0.105]}>
          <mesh scale={[0.022, 0.016, 0.01]}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#efe8dc" /></mesh>
          <mesh position={[0, 0, 0.007]} scale={0.009}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#20120a" /></mesh>
        </group>
      ))}
      <mesh position={[0, -0.07, 0.11]} scale={[0.025, 0.006, 0.01]}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color="#6a2c26" /></mesh>
    </group>
  </group>
);

const INCLINA = 1.12;
/** dónde queda la cabeza de la cosa (para apuntar la cámara) */
/** al agacharse baja la cadera abriendo las piernas como una araña (así la cara llega a la ventana) */
const cadera = (agacha: number) => 1.55 - 0.62 * agacha;
const abre = (agacha: number) => Math.acos(cadera(agacha) / 1.55);
export const cabezaCosa = (pos: V3, yaw: number, agacha: number): V3 => {
  const inc = agacha * INCLINA, r = 1.62;
  const fw = Math.sin(inc) * r, dir = yaw === 0 ? 1 : -1;
  return [pos[0], cadera(agacha) + Math.cos(inc) * r, pos[2] + dir * fw];
};
/** LA COSA: 3,4 m, flaca, pálida y fría, brazos hasta las rodillas, ojos huecos con brillo frío.
 * `agacha` 0..1 dobla el torso para mirar por la ventana; `golpe` 0..1 levanta el brazo para golpear;
 * `sonrisa` 0..1 abre una boca demasiado ancha. */
export const Cosa: React.FC<{pos: V3; yaw: number; agacha: number; golpe: number; sonrisa: number; respira: number}> = ({pos, yaw, agacha, golpe, sonrisa, respira}) => {
  const piel = C.monstruo, sombra = '#8d9db3';
  const inclina = agacha * INCLINA;
  return (
    <group position={pos} rotation={[0, yaw, 0]}>
      {/* piernas largas */}
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.16, cadera(agacha), 0]} rotation={[0, 0, s * abre(agacha)]}>
          <mesh position={[0, -0.78, 0]} castShadow><cylinderGeometry args={[0.07, 0.05, 1.56, 5]} /><M c={sombra} /></mesh>
          <Caja p={[0, -1.55, 0.08]} s={[0.12, 0.05, 0.3]} c={sombra} r={[0, 0, -s * abre(agacha)]} />
        </group>
      ))}
      {/* torso: pivote en la cadera */}
      <group position={[0, cadera(agacha), 0]} rotation={[inclina, 0, 0]}>
        <mesh position={[0, 0.55, 0]} castShadow><cylinderGeometry args={[0.24, 0.14, 1.1, 6]} /><M c={piel} /></mesh>
        {/* costillas */}
        {[0.42, 0.56, 0.7].map((y) => (
          <mesh key={y} position={[0, y, 0.15]} rotation={[0, 0, Math.PI / 2]} scale={[1, 1, 0.5]}><torusGeometry args={[0.13, 0.012, 3, 8, Math.PI]} /><M c={sombra} /></mesh>
        ))}
        <Brazo p={[-0.3, 1.04, 0]} largo={1.45} grosor={0.05} c={piel} mano={sombra} rx={-inclina * 0.8 + 0.05 * respira} rz={-0.08} />
        <Brazo p={[0.3, 1.04, 0]} largo={1.45} grosor={0.05} c={piel} mano={sombra} rx={-inclina * 0.8 - golpe * 0.95} rz={0.08 - golpe * 0.2} />
        {/* cuello y cabeza alargada */}
        <group position={[0, 1.15, 0.02]} rotation={[-inclina * 0.6, 0, 0.12 * Math.sin(respira * 0.5)]}>
          <mesh position={[0, 0.12, 0]}><cylinderGeometry args={[0.05, 0.07, 0.26, 5]} /><M c={piel} /></mesh>
          <group position={[0, 0.42, 0.02]}>
            <mesh scale={[0.17, 0.27, 0.17]} castShadow><icosahedronGeometry args={[1, 0]} /><M c={piel} e="#3a5068" ei={0.25} /></mesh>
            {/* ojos huecos con brillo frío */}
            {[-1, 1].map((s) => (
              <group key={s} position={[s * 0.065, 0.05, 0.13]}>
                <mesh scale={[0.045, 0.06, 0.02]}><sphereGeometry args={[1, 8, 6]} /><meshBasicMaterial color="#04070c" /></mesh>
                <mesh position={[0, 0, 0.012]} scale={0.013}><sphereGeometry args={[1, 6, 4]} /><meshBasicMaterial color={C.ojosMonstruo} /></mesh>
              </group>
            ))}
            {/* boca: una raya que se abre en sonrisa demasiado ancha */}
            <mesh position={[0, -0.12, 0.13]} scale={[0.07 + sonrisa * 0.07, 0.008 + sonrisa * 0.035, 0.02]}><sphereGeometry args={[1, 10, 6]} /><meshBasicMaterial color="#05070a" /></mesh>
            {sonrisa > 0.2 && Array.from({length: 9}, (_, k) => (
              <mesh key={k} position={[(k - 4) * 0.016, -0.12 + 0.016 * sonrisa, 0.148]} rotation={[0, 0, Math.PI]} scale={[0.006, 0.014 * sonrisa, 0.004]}><coneGeometry args={[1, 1, 3]} /><meshBasicMaterial color="#e8eef2" /></mesh>
            ))}
          </group>
        </group>
      </group>
    </group>
  );
};
