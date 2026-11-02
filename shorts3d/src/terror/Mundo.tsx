// El pueblo de noche en low-poly: calle con niebla, la casa de Tomás (con su cuarto por dentro), las casas
// de enfrente con ventanas naranjas, faroles, la casa de los vecinos y el cementerio al fondo de la calle.
import React, {useLayoutEffect, useMemo} from 'react';
import {useCurrentFrame} from 'remotion';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {aplicarPose} from './planos';
import {estado, L} from './estado';
import {Tomas, Madre, Cosa} from './Personajes';
import {SPEC} from './spec';
import {V3, rnd, lerp} from '../anim';

const C = SPEC.color;
const Cam: React.FC = () => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => aplicarPose(camera as THREE.PerspectiveCamera, f), [f, camera]);
  return null;
};
const Mat: React.FC<{c: string; e?: string; ei?: number; t?: number}> = ({c, e, ei, t}) => (
  <meshStandardMaterial color={c} flatShading roughness={0.9} emissive={e ?? '#000'} emissiveIntensity={ei ?? 0} transparent={t !== undefined} opacity={t ?? 1} />
);
const Caja: React.FC<{p: V3; s: V3; c: string; r?: V3; e?: string; ei?: number}> = ({p, s, c, r, e, ei}) => (
  <mesh position={p} rotation={r} castShadow receiveShadow><boxGeometry args={s} /><Mat c={c} e={e} ei={ei} /></mesh>
);
const Techo: React.FC<{p: V3; w: number; d: number; h: number; c: string}> = ({p, w, d, h, c}) => (
  <mesh position={p} rotation={[0, Math.PI / 4, 0]} scale={[w / Math.SQRT2, h, d / Math.SQRT2]} castShadow>
    <coneGeometry args={[1, 1, 4]} /><Mat c={c} />
  </mesh>
);

/** casa con una ventana de verdad (hueco en la pared delantera, z = +d/2) para poder mirar dentro y fuera */
const CasaHueca: React.FC<{p: V3; w: number; d: number; h: number; pared: string; dentro: string; hueco: [number, number, number, number]; abierta?: number; vidrio?: boolean}> = ({p, w, d, h, pared, dentro, hueco, abierta = 0, vidrio = true}) => {
  const [x0, x1, y0, y1] = hueco, g = 0.15, z = d / 2;
  return (
    <group position={p}>
      {/* pared delantera en 4 piezas alrededor del hueco */}
      <Caja p={[(-w / 2 + x0) / 2, h / 2, z]} s={[x0 + w / 2, h, g]} c={pared} />
      <Caja p={[(x1 + w / 2) / 2, h / 2, z]} s={[w / 2 - x1, h, g]} c={pared} />
      <Caja p={[(x0 + x1) / 2, y0 / 2, z]} s={[x1 - x0, y0, g]} c={pared} />
      <Caja p={[(x0 + x1) / 2, (y1 + h) / 2, z]} s={[x1 - x0, h - y1, g]} c={pared} />
      {/* resto de la casa */}
      <Caja p={[0, h / 2, -d / 2]} s={[w, h, g]} c={pared} />
      <Caja p={[-w / 2, h / 2, 0]} s={[g, h, d]} c={pared} />
      <Caja p={[w / 2, h / 2, 0]} s={[g, h, d]} c={pared} />
      <Caja p={[0, h + 0.02, 0]} s={[w + 0.3, 0.08, d + 0.3]} c="#2b2a33" />
      <Techo p={[0, h + 0.7, 0]} w={w + 0.6} d={d + 0.6} h={1.4} c="#3b2d34" />
      {/* forro interior cálido */}
      <Caja p={[0, h / 2, -d / 2 + 0.09]} s={[w - 0.3, h, 0.02]} c={dentro} />
      <Caja p={[-w / 2 + 0.09, h / 2, 0]} s={[0.02, h, d - 0.3]} c={dentro} />
      <Caja p={[w / 2 - 0.09, h / 2, 0]} s={[0.02, h, d - 0.3]} c={dentro} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]} receiveShadow><planeGeometry args={[w - 0.2, d - 0.2]} /><Mat c="#5a3a26" /></mesh>
      {/* marco, cruz y vidrio (el vidrio se abre hacia fuera si `abierta`) */}
      <Caja p={[(x0 + x1) / 2, y0 - 0.04, z + 0.1]} s={[x1 - x0 + 0.2, 0.08, 0.16]} c="#e6dccb" />
      <group position={[x0, 0, z + 0.04]} rotation={[0, -abierta * 1.6, 0]}>
        <Caja p={[(x1 - x0) / 2, (y0 + y1) / 2, 0]} s={[0.05, y1 - y0, 0.05]} c="#e6dccb" />
        <Caja p={[(x1 - x0) / 2, (y0 + y1) / 2, 0]} s={[x1 - x0, 0.05, 0.05]} c="#e6dccb" />
        {[0, x1 - x0].map((x) => <Caja key={x} p={[x, (y0 + y1) / 2, 0]} s={[0.06, y1 - y0, 0.06]} c="#e6dccb" />)}
        {vidrio && (
          <mesh position={[(x1 - x0) / 2, (y0 + y1) / 2, 0]}>
            <planeGeometry args={[x1 - x0, y1 - y0]} />
            <meshStandardMaterial color="#9db3c9" transparent opacity={0.14} roughness={0.1} side={THREE.DoubleSide} />
          </mesh>
        )}
      </group>
    </group>
  );
};

const CasaSimple: React.FC<{p: V3; w: number; h: number; c: string; yaw: number; luz: number}> = ({p, w, h, c, yaw, luz}) => (
  <group position={p} rotation={[0, yaw, 0]}>
    <Caja p={[0, h / 2, 0]} s={[w, h, 4]} c={c} />
    <Techo p={[0, h + 0.75, 0]} w={w + 0.5} d={4.5} h={1.5} c="#3a2c33" />
    {[-w / 4, w / 4].map((x, i) => (
      <mesh key={x} position={[x, h * 0.55, 2.01]}>
        <planeGeometry args={[0.9, 0.9]} />
        <meshBasicMaterial color={rnd(i + p[0], 3) > 0.25 * (1 - luz) ? C.ventana : '#1a1f2a'} toneMapped={false} />
      </mesh>
    ))}
    <Caja p={[0, 0.9, 2.02]} s={[0.8, 1.8, 0.05]} c="#3a2418" />
  </group>
);

const Farol: React.FC<{p: V3; luz: boolean; f: number}> = ({p, luz, f}) => {
  const parpadeo = 0.85 + 0.15 * Math.sin(f / 3 + p[0]) * Math.sin(f / 7);
  return (
    <group position={p}>
      <mesh position={[0, 1.4, 0]} castShadow><cylinderGeometry args={[0.05, 0.07, 2.8, 5]} /><Mat c="#1d1d24" /></mesh>
      <mesh position={[0, 2.9, 0]}><boxGeometry args={[0.28, 0.36, 0.28]} /><meshBasicMaterial color={C.linterna} toneMapped={false} /></mesh>
      {luz && <pointLight position={[0, 2.75, 0]} intensity={9 * parpadeo} distance={9} decay={1.6} color={C.linterna} />}
    </group>
  );
};

const Cementerio: React.FC = () => {
  const tumbas = useMemo(() => Array.from({length: 16}, (_, i) => ({x: -3.5 + (i % 4) * 2.1 + rnd(i, 1) * 0.5, z: -3 + Math.floor(i / 4) * 1.9, r: (rnd(i, 2) - 0.5) * 0.25, cruz: rnd(i, 3) > 0.6, h: 0.6 + rnd(i, 4) * 0.4})), []);
  return (
    <group position={L.cementerio}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow><circleGeometry args={[6.5, 9]} /><Mat c="#2a3328" /></mesh>
      {tumbas.map((t, i) => (
        <group key={i} position={[t.x, 0, t.z]} rotation={[0, 0, t.r]}>
          {t.cruz ? (
            <>
              <Caja p={[0, t.h / 2 + 0.1, 0]} s={[0.1, t.h + 0.2, 0.1]} c="#8a8f99" />
              <Caja p={[0, t.h * 0.85, 0]} s={[0.45, 0.1, 0.1]} c="#8a8f99" />
            </>
          ) : (
            <Caja p={[0, t.h / 2, 0]} s={[0.55, t.h, 0.16]} c="#7c8290" />
          )}
        </group>
      ))}
      {Array.from({length: 22}, (_, i) => <Caja key={i} p={[-6 + i * 0.57, 0.5, 4]} s={[0.05, 1, 0.05]} c="#15151a" />)}
      <Caja p={[0.3, 0.95, 4]} s={[12.5, 0.05, 0.05]} c="#15151a" />
      {/* árbol muerto */}
      <group position={[3.8, 0, -2.5]}>
        <mesh position={[0, 1.8, 0]}><cylinderGeometry args={[0.1, 0.25, 3.6, 5]} /><Mat c="#1b1612" /></mesh>
        {[[-0.6, 3, 0.9], [0.7, 2.6, -0.8], [0.2, 3.4, 0.4]].map(([x, y, r], i) => (
          <mesh key={i} position={[x / 2, y, 0]} rotation={[0, 0, r]}><cylinderGeometry args={[0.03, 0.07, 1.6, 4]} /><Mat c="#1b1612" /></mesh>
        ))}
      </group>
    </group>
  );
};

export const Mundo: React.FC = () => {
  const f = useCurrentFrame();
  const s = estado(f);
  const dia = s.dia, rayo = s.rayo;
  const niebla = new THREE.Color(C.niebla).lerp(new THREE.Color('#8592a6'), dia * 0.6);
  return (
    <>
      <Cam />
      <fog attach="fog" args={[niebla.getStyle(), 7, lerp(34, 48, dia)]} />
      <hemisphereLight args={['#7f97c9', '#20242e', 0.75 + dia * 0.6 + rayo * 3]} />
      <directionalLight position={[-12, 18, 14]} intensity={1.1 + dia * 0.8} color="#9db7ff" castShadow shadow-mapSize={[1024, 1024]} shadow-camera-left={-20} shadow-camera-right={20} shadow-camera-top={20} shadow-camera-bottom={-20} />
      {rayo > 0.01 && <directionalLight position={[6, 20, 18]} intensity={6 * rayo} color="#eef4ff" />}
      {/* luna */}
      <mesh position={[-30, 26, -40]}><icosahedronGeometry args={[3.2, 1]} /><meshBasicMaterial color="#e9eefc" fog={false} /></mesh>
      {/* suelo y calle */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow><planeGeometry args={[120, 120]} /><Mat c="#28302d" /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 7.5]} receiveShadow><planeGeometry args={[60, 5.5]} /><Mat c="#3a3d46" /></mesh>
      {Array.from({length: 30}, (_, i) => (
        <mesh key={i} position={[-29 + i * 2 + rnd(i, 1), 0.02, 5 + rnd(i, 2) * 5]} rotation={[-Math.PI / 2, 0, rnd(i, 3) * 3]}><circleGeometry args={[0.12 + rnd(i, 4) * 0.2, 5]} /><Mat c="#30333b" /></mesh>
      ))}
      {/* casa de Tomás, con el cuarto por dentro */}
      <CasaHueca p={[0, 0, -0.25]} w={5} d={4.5} h={2.8} pared="#6d7c92" dentro="#b98a64" hueco={[-0.65, 0.65, 1.0, 2.0]} />
      {/* resplandor naranja de la ventana visto desde la calle (de dentro no se ve: cara trasera) */}
      <mesh position={[0, 1.5, 1.86]}><planeGeometry args={[1.3, 1.0]} /><meshBasicMaterial color={C.ventana} transparent opacity={0.55} blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} /></mesh>
      <pointLight position={[-1.9, 1.3, -1.6]} intensity={5.5} distance={7} decay={1.5} color="#ffb060" />
      {/* lámpara de la mesa de noche, cama y reloj de las 3:00 */}
      <Caja p={[-1.95, 0.3, -1.65]} s={[0.45, 0.6, 0.45]} c="#5c3b26" />
      <mesh position={[-1.95, 0.82, -1.65]}><coneGeometry args={[0.16, 0.24, 6]} /><meshBasicMaterial color="#ffc27a" toneMapped={false} /></mesh>
      <Caja p={[L.cama[0], 0.24, L.cama[2] - 0.4]} s={[1.1, 0.48, 2]} c="#6b4a33" />
      <Caja p={[L.cama[0], 0.52, L.cama[2] - 0.35]} s={[1.05, 0.12, 1.9]} c="#5e6f9a" />
      <Caja p={[L.cama[0], 0.62, L.cama[2] - 1.15]} s={[0.6, 0.12, 0.3]} c="#e8e2d4" />
      <group position={L.reloj} rotation={[0, Math.PI / 2, 0]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.24, 0.24, 0.05, 12]} /><Mat c="#efe6d2" /></mesh>
        <Caja p={[0, 0.08, 0.035]} s={[0.025, 0.17, 0.01]} c="#151515" />
        <Caja p={[0.06, 0, 0.04]} s={[0.12, 0.03, 0.01]} c="#151515" />
      </group>
      {/* casas de enfrente (ventanas naranjas) y de los lados */}
      {[-11, -5.5, 5.5, 11].map((x, i) => <CasaSimple key={x} p={[x, 0, 13]} w={4.4} h={2.6 + (i % 2) * 0.5} c={i % 2 ? '#56607a' : '#4b5a6e'} yaw={Math.PI} luz={1} />)}
      <CasaSimple p={[-8, 0, -0.2]} w={4.6} h={2.8} c="#506078" yaw={0} luz={1} />
      {/* casa de los vecinos: de noche luz naranja; al amanecer, ventana abierta y nadie dentro */}
      <CasaHueca p={[L.vecinos[0], 0, -0.25]} w={4.6} d={4.5} h={2.8} pared="#5d6a80" dentro="#4a4038" hueco={[-0.6, 0.6, 1.0, 2.0]} abierta={s.vecinosAbierta ? 1 : 0} />
      {!s.vecinosAbierta && <pointLight position={[L.vecinos[0], 1.4, -1]} intensity={4} distance={5} decay={1.6} color="#ffa04a" />}
      {s.vecinosAbierta && <Caja p={[L.vecinos[0] + 0.6, 0.25, -0.6]} s={[0.45, 0.5, 0.45]} c="#5a3a26" r={[0, 0.4, 1.4]} />}
      {/* faroles (luz cálida) */}
      <Farol p={[-3.2, 0, 4.6]} luz f={f} />
      <Farol p={[3.6, 0, 10.2]} luz f={f} />
      <Farol p={[-9, 0, 10.2]} luz={false} f={f} />
      <Cementerio />
      {/* personajes */}
      <Tomas pos={s.tomas.pos} yaw={s.tomas.yaw} sentado={s.tomas.sentado} paso={s.tomas.paso} mano={s.tomas.mano} miedo={s.tomas.miedo} />
      {s.madre.visible && <Madre pos={s.madre.pos} mano={s.madre.mano} />}
      {s.monstruo.visible && <Cosa pos={s.monstruo.pos} yaw={s.monstruo.yaw} agacha={s.monstruo.agacha} golpe={s.monstruo.golpe} sonrisa={s.monstruo.sonrisa} respira={s.monstruo.respira} />}
      {/* luz fría que baña a la cosa (siempre más fría que los humanos) */}
      {s.monstruo.visible && <pointLight position={[s.monstruo.pos[0] + 1.2, 3.4, s.monstruo.pos[2] + (s.monstruo.yaw === 0 ? 2 : -0.4)]} intensity={4} distance={5} decay={1.4} color="#a8c8ff" />}
    </>
  );
};
