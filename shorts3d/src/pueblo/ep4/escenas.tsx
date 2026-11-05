// Episodio 4 — «SI MIENTES, TODO EL PUEBLO LO ESCUCHA!» (personajes 2D de la skill). Guion del dueño tal cual.
import React from 'react';
import type {Escena, V3, Cam} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Camion, Caja, Aula, AULA, Cartel} from '../Pueblo';
import {Carta2D, cabeza2D} from '../Carta2D';
import {BRUNO_2D, NINOS_2D, EXTRAS_2D} from '../personajes2d';
import {lerp, clamp, rnd} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p), enA = (p: V3) => add(AULA, p);
const cam = (pos: V3, look: V3, fov = 42, dof?: number): Cam => ({pos, look, fov, dof});
const SOFI = NINOS_2D.sofi, ANA = NINOS_2D.ana;
/** poste con dos altavoces de bocina; `apagado` 0..1 los descuelga y apaga */
const Altavoz: React.FC<{p: V3; apagado?: number; vibra?: number; f?: number}> = ({p, apagado = 0, vibra = 0, f = 0}) => {
  const v = vibra * Math.sin(f * 2.1) * 0.03;
  return (
    <group position={p}>
      <mesh position={[0, 2.0, 0]} castShadow><cylinderGeometry args={[0.07, 0.09, 4.0, 8]} /><meshLambertMaterial color="#5c677d" /></mesh>
      {[-1, 1].map((s) => (
        <group key={s} position={[s * 0.25, 3.8 + v, 0]} rotation={[apagado * 0.9, 0, s * (0.5 + apagado * 0.6)]}>
          <mesh rotation={[0, 0, -s * Math.PI / 2]} castShadow><coneGeometry args={[0.28, 0.55, 14, 1, true]} /><meshLambertMaterial color={apagado > 0.5 ? '#6c757d' : '#adb5bd'} side={2} /></mesh>
        </group>
      ))}
    </group>
  );
};
/** «MENTIRA» que salta del altavoz (rebota al entrar) */
const Mentira: React.FC<{p: V3; t: number}> = ({p, t}) => {
  if (t <= 0) return null;
  const s = clamp(t * 1.6) * (1 + 0.15 * Math.sin(Math.min(1, t * 1.6) * Math.PI));
  return <group position={p} scale={s}><Cartel p={[0, 0, 0]} w={1.5} texto="¡MENTIRA!" fondo="#d62828" color="#ffffff" /></group>;
};
const Bici: React.FC<{p: V3; rot?: number; caida?: number}> = ({p, rot = 0, caida = 0}) => (
  <group position={p} rotation={[0, rot, caida * 1.3]}>
    {[-0.45, 0.45].map((x) => <mesh key={x} position={[x, 0.33, 0]}><torusGeometry args={[0.3, 0.035, 8, 24]} /><meshLambertMaterial color="#222" /></mesh>)}
    <Caja p={[0, 0.55, 0]} s={[0.9, 0.05, 0.05]} c="#e63946" r={[0, 0, -0.25]} />
    <Caja p={[-0.1, 0.65, 0]} s={[0.05, 0.6, 0.05]} c="#e63946" r={[0, 0, 0.3]} />
    <Caja p={[0.4, 0.85, 0]} s={[0.05, 0.12, 0.4]} c="#333" />
  </group>
);
// plaza: altavoces en tres puntos fijos
const POSTES: V3[] = [[-3.2, 0, 3.6], [3.6, 0, 3.2], [-6.5, 0, -2.5]];
const Plaza: React.FC<{f: number; hora?: number; noche?: boolean; apagados?: number[]; vibra?: number}> = ({f, hora = 10, noche, apagados = [0, 0, 0], vibra = 0}) => (
  <group>
    <Pueblo f={f} hora={hora} noche={noche} />
    {POSTES.map((p, i) => <Altavoz key={i} p={p} apagado={apagados[i]} vibra={vibra} f={f} />)}
  </group>
);

export const ESCENAS: Record<string, Escena> = {
  // [Postes con altavoces. Un niño dice "yo no fui" y se escucha por todo el pueblo: "MENTIRA".]
  postes: {
    pueblo: true,
    camaras: [cam([-1.0, 2.4, 9.0], [-2.6, 2.4, 3.6], 44, 0), cam([-1.6, 1.3, 7.0], [-2.0, 1.0, 5.0], 34, 12)],
    render: (c) => {
      const t = c.desde('l01', 'altavoces.', 14);
      return <group><Plaza f={c.f} vibra={t > 0 ? 1 : 0} /><Carta2D pos={[-2.0, 0, 5.0]} ropa={NINOS_2D.nino} expr={t > 0 ? 'shock' : 'nervous'} f={c.f} seed={41} /><Mentira p={[-2.0, 2.15, 5.3]} t={t} /></group>;
    },
  },
  // "Ya hice la tarea." → MENTIRA.
  tarea: {
    interior: true,
    camaras: [cam(enA([1.6, 1.6, 4.4]), enA([0, 1.2, 1.4]), 44, 0), cam(enA([0.5, 1.2, 3.2]), enA([0, 1.1, 1.6]), 32, 12)],
    render: (c) => {
      const t = c.desde('l02', 'MENTIRA.', 12);
      return (
        <Aula>
          <Carta2D pos={[0, 0, 1.7]} ropa={NINOS_2D.dani} expr={t > 0 ? 'shock' : 'smile'} f={c.f} seed={9} />
          <Carta2D pos={[-2.0, 0, 0.4]} ropa={EXTRAS_2D.vecina} expr={t > 0 ? 'stern' : 'neutral'} f={c.f} seed={44} />
          <Mentira p={[0, 2.05, 2.0]} t={t} />
        </Aula>
      );
    },
  },
  // "Me encanta tu suéter, abuela." → MENTIRA.
  sueter: {
    pueblo: true,
    camaras: [cam([5.0, 1.6, 9.0], [6.4, 1.2, 5.6], 42), cam([5.8, 1.3, 7.6], [6.8, 1.2, 5.6], 32, 12)],
    render: (c) => {
      const t = c.desde('l03', 'MENTIRA.', 12);
      return (
        <group>
          <Plaza f={c.f} hora={11} vibra={t > 0 ? 1 : 0} />
          <Carta2D pos={[6.0, 0, 5.8]} ropa={NINOS_2D.leo} expr={t > 0 ? 'shock' : 'grin'} f={c.f} seed={2} />
          <Carta2D pos={[7.0, 0, 5.4]} ropa={{...EXTRAS_2D.vecina, jacket: '#ff9f1c', dress: '#ff9f1c'}} expr={t > 0 ? 'pained' : 'smile'} f={c.f} seed={45} />
          <Mentira p={[6.1, 2.15, 6.1]} t={t} />
        </group>
      );
    },
  },
  // "Solo me comí una galleta." → MENTIRA.
  galleta: {
    interior: true,
    camaras: [cam(enC([-0.4, 1.4, 2.2]), enC([0.2, 1.0, -0.6]), 42), cam(enC([0.6, 1.15, 1.0]), enC([0.2, 1.0, -0.6]), 32, 12)],
    render: (c) => {
      const t = c.desde('l04', 'MENTIRA.', 12);
      return (
        <Cuarto pared="#ffe5b4" vacio>
          <Carta2D pos={[0.2, 0, -0.6]} ropa={NINOS_2D.nino} expr={t > 0 ? 'shock' : 'smile'} f={c.f} seed={41} />
          <Caja p={[1.4, 0.4, -0.9]} s={[0.8, 0.8, 0.5]} c="#a0522d" />
          {[0, 1, 2, 3, 4, 5].map((i) => <mesh key={i} position={[1.2 + (i % 3) * 0.2, 0.84, -0.9 + Math.floor(i / 3) * 0.18]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.07, 12]} /><meshLambertMaterial color="#8b5e34" /></mesh>)}
          <Mentira p={[0.2, 2.1, -0.3]} t={t} />
        </Cuarto>
      );
    },
  },
  // Por eso aquí la gente responde "mmm" a todo.
  mmm: {
    pueblo: true,
    camaras: [cam([0, 2.0, 11.5], [0, 1.2, 5.6], 44, 0), cam([1.2, 1.3, 8.2], [0.6, 1.2, 5.6], 32, 12)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={12} />
        <Carta2D pos={[-0.6, 0, 5.6]} ropa={EXTRAS_2D.papa} expr="whistle" f={c.f} seed={46} />
        <Carta2D pos={[0.7, 0, 5.4]} ropa={EXTRAS_2D.mama} expr="whistle" f={c.f} seed={47} />
      </group>
    ),
  },
  // Y nadie pregunta "¿me veo bien?".
  espejo: {
    interior: true,
    camaras: [cam(enC([-0.6, 1.5, 1.8]), enC([0.6, 1.2, -2.6]), 42), cam(enC([0.3, 1.4, 0.6]), enC([0.6, 1.3, -3.3]), 34, 12)],
    render: (c) => (
      <Cuarto pared="#cdb4db" vacio>
        <group position={[0.6, 0, -3.3]}>
          <Caja p={[0, 1.15, 0]} s={[1.3, 1.9, 0.08]} c="#c9a227" />
          <mesh position={[0, 1.15, 0.05]}><planeGeometry args={[1.1, 1.7]} /><meshPhysicalMaterial color="#cfe7ff" roughness={0.05} metalness={0.6} /></mesh>
        </group>
        <Carta2D pos={[0.6, 0, -2.0]} ropa={EXTRAS_2D.vecina} expr="nervous" f={c.f} seed={44} />
      </Cuarto>
    ),
  },
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46, 0), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (<group><Plaza f={c.f} hora={8.1} /><Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} /></group>),
  },
  // Me llamo Sofi. Mi mejor amiga aquí era Ana.
  sofi: {
    pueblo: true,
    camaras: [cam([-6.4, 1.6, 8.8], [-9.6, 1.1, 5.8], 42), cam([-7.0, 1.5, 8.6], [-9.2, 1.1, 5.8], 38, 12)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={8.6} />
        <Carta2D pos={[-9.0, 0, 6.2]} ropa={SOFI} expr="smile" f={c.f} seed={3} saluda={c.u < 0.4} />
        {c.u > 0.45 && <Carta2D pos={[-10.0, 0, 5.4]} ropa={ANA} expr="grin" f={c.f} seed={5} saluda />}
      </group>
    ),
  },
  // [Ana en la escuela, sonriendo, con un yeso en el brazo.] + —Me caí de la bici.
  ana: {
    pueblo: true,
    camaras: [cam([-7.2, 1.6, 8.4], [-9.6, 1.1, 5.6], 38, 12), cam([-6.4, 1.8, 9.0], [-9.4, 1.0, 5.6], 44)],
    cabezas: {ana: cabeza2D([-9.8, 0, 5.4], 1, true)},
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={9} />
        <Carta2D pos={[-9.8, 0, 5.4]} ropa={ANA} expr="smile_closed" f={c.f} seed={5} />
        <Caja p={[-9.45, 0.95, 5.55]} s={[0.12, 0.3, 0.12]} c="#ffffff" />
        <Carta2D pos={[-8.8, 0, 6.2]} ropa={SOFI} expr="nervous" f={c.f} seed={3} />
      </group>
    ),
  },
  // [Silencio. Ningún altavoz suena.]
  silencio: {
    pueblo: true,
    camaras: [cam([-1.0, 2.4, 9.0], [-3.2, 3.6, 3.6], 40, 0), cam([-6.0, 2.2, 1.6], [-6.5, 3.6, -2.5], 38)],
    render: (c) => <Plaza f={c.f} hora={9.2} />,
  },
  // [Sofi, confundida.] Era verdad… pero se caía de la bici todos los días.
  confusa: {
    pueblo: true,
    camaras: [cam([-7.0, 1.5, 8.8], [-8.8, 1.1, 6.2], 38, 12), cam([-6.4, 1.8, 9.0], [-9.4, 1.0, 5.6], 44)],
    render: (c) => <group><Plaza f={c.f} hora={9.4} /><Carta2D pos={[-8.8, 0, 6.2]} ropa={SOFI} expr="dazed" f={c.f} seed={3} /></group>,
  },
  // [Noche. Sofi espía la casa de Ana: Ana practica sola en la bici, se cae, se levanta.]
  noche: {
    noche: true, pueblo: true,
    camaras: [cam([10.0, 1.9, 13.0], [13.0, 0.9, 9.0], 44, 0), cam([12.0, 1.0, 11.0], [13.4, 0.7, 9.2], 34, 12)],
    render: (c) => {
      const ciclo = (c.f % 60) / 60, cae = ciclo > 0.6 ? clamp((ciclo - 0.6) / 0.15) : 0;
      return (
        <group>
          <Plaza f={c.f} noche hora={22} />
          <Bici p={[lerp(11.6, 14.4, Math.min(ciclo / 0.6, 1)), 0, 9.2]} caida={cae} />
          <Carta2D pos={[lerp(11.6, 14.4, Math.min(ciclo / 0.6, 1)), 0.15 - cae * 0.15, 9.0]} ropa={ANA} expr={cae > 0.5 ? 'pained' : 'stern'} modo={cae > 0.5 ? 'fall' : 'stand'} f={c.f} seed={5} />
          <Carta2D pos={[10.6, 0, 11.6]} ropa={SOFI} expr="shock" f={c.f} seed={3} />
        </group>
      );
    },
  },
  // Diálogo de noche
  charla: {
    noche: true, pueblo: true,
    camaras: [cam([11.4, 1.6, 13.4], [12.4, 1.1, 10.2], 42), cam([13.4, 1.35, 12.9], [12.0, 1.1, 10.6], 38, 12), cam([10.6, 1.35, 12.9], [13.0, 1.1, 10.0], 38, 12)],
    cabezas: {ana: cabeza2D([13.0, 0, 10.0], 1, true), sofi: cabeza2D([11.9, 0, 10.6], 1, true)},
    render: (c) => (
      <group>
        <Plaza f={c.f} noche hora={22.2} />
        <Bici p={[13.8, 0, 9.6]} rot={0.6} />
        <Carta2D pos={[13.0, 0, 10.0]} ropa={ANA} expr={c.f > c.W('l17') ? 'stern' : 'smile'} f={c.f} seed={5} />
        <Carta2D pos={[11.9, 0, 10.6]} ropa={SOFI} expr={c.f > c.W('l17') ? 'shock' : 'nervous'} f={c.f} seed={3} />
      </group>
    ),
  },
  // [Flashback: Ana pequeña diciendo "Mi papá vuelve pronto". Altavoz: MENTIRA. Todo el pueblo la mira.]
  flashback: {
    pueblo: true,
    camaras: [cam([-1.0, 2.6, 9.4], [-2.6, 1.6, 4.4], 44, 0), cam([-1.8, 1.0, 6.6], [-2.2, 0.8, 5.0], 32, 12)],
    render: (c) => {
      const t = c.desde('l18', 'MENTIRA.', 12);
      return (
        <group>
          <Plaza f={c.f} hora={16.5} vibra={t > 0 ? 1 : 0} />
          <Carta2D pos={[-2.2, 0, 5.0]} ropa={ANA} expr={t > 0 ? 'cry' : 'smile'} escala={0.8} f={c.f} seed={5} />
          {[[-4.4, 6.8, EXTRAS_2D.vecina], [-0.4, 7.2, EXTRAS_2D.vecino], [0.8, 5.6, EXTRAS_2D.papa], [-5.0, 4.6, EXTRAS_2D.panadero]].map(([x, z, r], i) => (
            <Carta2D key={i} pos={[x as number, 0, z as number]} ropa={r as typeof ANA} expr={t > 0 ? 'stern' : 'neutral'} f={c.f} seed={70 + i} />
          ))}
          <Mentira p={[-2.2, 1.85, 5.3]} t={t} />
        </group>
      );
    },
  },
  // [Sábado. Carrera en la plaza. Ana va ganando, pero se cae en la última curva.]
  carrera: {
    pueblo: true,
    camaras: [cam([0, 4.0, 14.0], [0, 0.8, 6.0], 46, 0), cam([5.6, 1.4, 9.0], [4.2, 0.8, 6.8], 34, 12)],
    render: (c) => {
      const cae = c.desde('l19', 'cayó', 10);
      const ang = (k: number) => lerp(-1.2, 0.9, clamp(c.u * 1.2 - k * 0.08)) + (k ? 0 : 0);
      const enAro = (a: number, r = 6.6): V3 => [Math.sin(a) * r, 0, Math.cos(a) * r];
      return (
        <group>
          <Plaza f={c.f} hora={10.5} />
          {[ANA, NINOS_2D.dani, NINOS_2D.nino, NINOS_2D.leo].map((r, k) => {
            const a = k === 0 && cae > 0 ? lerp(ang(0), ang(0) - 0.05, cae) : ang(k);
            const p = enAro(a);
            return <group key={k}><Bici p={p} rot={a + Math.PI / 2} caida={k === 0 ? cae : 0} /><Carta2D pos={[p[0], 0.2 - (k === 0 ? cae * 0.2 : 0), p[2] + 0.05]} ropa={r} expr={k === 0 ? (cae > 0.5 ? 'pained' : 'grin') : 'stern'} modo={k === 0 && cae > 0.5 ? 'fall' : 'stand'} f={c.f} seed={5 + k * 3} /></group>;
          })}
        </group>
      );
    },
  },
  // [Don Bruno entrega la copa a otro niño.]
  copa: {
    pueblo: true,
    camaras: [cam([0.4, 2.0, 10.0], [0, 1.6, 4.6], 42), cam([1.0, 1.6, 7.0], [0.4, 1.5, 4.8], 32, 12)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={11} />
        <Caja p={[0, 0.25, 4.6]} s={[3.0, 0.5, 1.4]} c="#e63946" />
        <Carta2D pos={[-0.5, 0.5, 4.6]} ropa={BRUNO_2D} expr="grin" f={c.f} seed={7} />
        <Carta2D pos={[0.6, 0.5, 4.7]} ropa={NINOS_2D.dani} expr="laugh" f={c.f} seed={9} />
        <group position={[0.15, 1.45, 4.9]}>
          <mesh><cylinderGeometry args={[0.18, 0.06, 0.3, 16]} /><meshPhysicalMaterial color="#e9c46a" metalness={1} roughness={0.25} /></mesh>
          <mesh position={[0, -0.2, 0]}><cylinderGeometry args={[0.1, 0.12, 0.08, 14]} /><meshPhysicalMaterial color="#e9c46a" metalness={1} roughness={0.25} /></mesh>
        </group>
        <Carta2D pos={[2.6, 0, 6.4]} ropa={ANA} expr="sad" f={c.f} seed={5} />
      </group>
    ),
  },
  // [Sofi sube al escenario y agarra el micrófono.] —¡Ana ganó!
  escenario: {
    pueblo: true,
    camaras: [cam([0.4, 2.0, 10.0], [0, 1.6, 4.6], 42), cam([1.6, 1.7, 8.4], [0.9, 1.5, 4.8], 38, 12)],
    cabezas: {sofi: cabeza2D([0.9, 0.5, 4.7], 1, true)},
    render: (c) => {
      const sube = clamp((c.f - c.W('l21', 'subí')) / 14);
      return (
        <group>
          <Plaza f={c.f} hora={11.1} />
          <Caja p={[0, 0.25, 4.6]} s={[3.0, 0.5, 1.4]} c="#e63946" />
          <Carta2D pos={[-0.5, 0.5, 4.6]} ropa={BRUNO_2D} expr="shock" f={c.f} seed={7} />
          <Carta2D pos={[lerp(2.4, 0.9, sube), lerp(0, 0.5, sube), lerp(6.2, 4.7, sube)]} ropa={SOFI} expr={c.f > c.W('l22') ? 'stern' : 'nervous'} f={c.f} seed={3} caminar={sube > 0 && sube < 1} />
          <mesh position={[1.2, 1.2, 4.9]}><cylinderGeometry args={[0.02, 0.02, 1.4, 8]} /><meshLambertMaterial color="#333" /></mesh>
          <mesh position={[1.2, 1.95, 4.9]}><sphereGeometry args={[0.07, 10, 8]} /><meshLambertMaterial color="#222" /></mesh>
        </group>
      );
    },
  },
  // [Todos miran los altavoces. Silencio total.]
  callados: {
    pueblo: true,
    camaras: [cam([0, 3.0, 13.0], [0, 2.0, 4.0], 46, 0), cam([-1.0, 2.0, 8.6], [-3.2, 3.6, 3.6], 38)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={11.2} />
        <Caja p={[0, 0.25, 4.6]} s={[3.0, 0.5, 1.4]} c="#e63946" />
        <Carta2D pos={[-0.5, 0.5, 4.6]} ropa={BRUNO_2D} expr="nervous" f={c.f} seed={7} />
        <Carta2D pos={[0.9, 0.5, 4.7]} ropa={SOFI} expr="stern" f={c.f} seed={3} />
        {[[-2.6, 7.4, EXTRAS_2D.vecina], [-1.2, 8.0, EXTRAS_2D.vecino], [2.4, 7.6, EXTRAS_2D.panadero], [3.4, 6.8, EXTRAS_2D.papa], [1.2, 8.4, ANA]].map(([x, z, r], i) => (
          <Carta2D key={i} pos={[x as number, 0, z as number]} ropa={r as typeof ANA} expr="nervous" f={c.f} seed={80 + i} mira={-1} />
        ))}
      </group>
    ),
  },
  // [Primer plano de Don Bruno sudando.] —Esa niña… dice la verdad.
  bruno: {
    pueblo: true,
    camaras: [cam([-0.3, 1.95, 7.0], [-0.5, 1.95, 4.6], 30, 13), cam([0.4, 2.0, 10.0], [0, 1.6, 4.6], 42)],
    cabezas: {bruno: cabeza2D([-0.5, 0.5, 4.6])},
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={11.3} />
        <Caja p={[0, 0.25, 4.6]} s={[3.0, 0.5, 1.4]} c="#e63946" />
        <Carta2D pos={[-0.5, 0.5, 4.6]} ropa={BRUNO_2D} expr="nervous" f={c.f} seed={7} />
        <Carta2D pos={[0.9, 0.5, 4.7]} ropa={SOFI} expr="stern" f={c.f} seed={3} />
      </group>
    ),
  },
  // [Sofi señala a Don Bruno.] —¡Porque ganar no es llegar primero!…
  senala: {
    pueblo: true,
    camaras: [cam([1.6, 1.7, 8.4], [0.9, 1.5, 4.8], 38, 12), cam([0.4, 2.0, 10.0], [0, 1.6, 4.6], 42)],
    cabezas: {sofi: cabeza2D([0.9, 0.5, 4.7], 1, true)},
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={11.4} />
        <Caja p={[0, 0.25, 4.6]} s={[3.0, 0.5, 1.4]} c="#e63946" />
        <Carta2D pos={[-0.5, 0.5, 4.6]} ropa={BRUNO_2D} expr="nervous" f={c.f} seed={7} />
        <Carta2D pos={[0.9, 0.5, 4.7]} ropa={SOFI} expr="grin" f={c.f} seed={3} saluda />
      </group>
    ),
  },
  // [Altavoces: chispas, se apagan uno por uno. SFX "pssst".]
  chispas: {
    pueblo: true,
    camaras: [cam([-1.2, 2.8, 8.4], [-3.2, 3.4, 3.6], 44, 0), cam([1.6, 3.0, 7.4], [3.6, 3.6, 3.2], 38, 12)],
    render: (c) => {
      const marcas = [c.W('l26', 'apagaron'), c.W('l26', 'uno'), c.W('l26', 'uno.')];
      const ap = marcas.map((m) => clamp((c.f - m) / 8));
      return (
        <group>
          <Plaza f={c.f} hora={11.5} apagados={ap} />
          {POSTES.map((p, i) => ap[i] > 0 && ap[i] < 1 && Array.from({length: 8}, (_, k) => (
            <mesh key={i + '-' + k} position={[p[0] + (rnd(k + i * 9, 1) - 0.5) * ap[i] * 1.4, 3.8 + (rnd(k, 2) - 0.3) * ap[i] * 1.2, p[2] + (rnd(k, 3) - 0.5) * 0.6]}>
              <sphereGeometry args={[0.05, 6, 4]} /><meshBasicMaterial color="#ffd60a" toneMapped={false} />
            </mesh>
          )))}
        </group>
      );
    },
  },
  // [Ana y Sofi abrazadas en la plaza.]
  abrazo: {
    pueblo: true,
    camaras: [cam([0.4, 1.5, 9.0], [0.2, 1.0, 5.6], 38, 12), cam([0, 2.2, 12.0], [0, 1.1, 5.6], 44, 0)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={16} apagados={[1, 1, 1]} />
        <Carta2D pos={[-0.25, 0, 5.6]} ropa={ANA} expr="relief" f={c.f} seed={5} inclina={6} />
        <Carta2D pos={[0.55, 0, 5.62]} ropa={SOFI} expr="relief" f={c.f} seed={3} inclina={-6} />
      </group>
    ),
  },
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.0, 13.5], [0, 1.2, 6.8], 46, 0), cam([3.0, 1.8, 12.5], [0, 1.1, 6.8], 42, 0)],
    render: (c) => (
      <group>
        <Plaza f={c.f} hora={10} apagados={[1, 1, 1]} />
        <Carta2D pos={[1.4, 0, 6.6]} ropa={BRUNO_2D} expr="grin" f={c.f} saluda seed={7} />
        <Carta2D pos={[-0.4, 0, 7.1]} ropa={SOFI} expr="grin" f={c.f + 9} saluda seed={3} />
        <Carta2D pos={[0.5, 0, 7.4]} ropa={ANA} expr="grin" f={c.f + 4} saluda seed={5} />
      </group>
    ),
  },
};
