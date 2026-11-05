// Episodio 3 — «AQUÍ TU SOMBRA HACE LO QUE REALMENTE QUIERES!» (bloques 3D brillantes). Guion del dueño tal cual.
// Las sombras son siluetas planas del mismo personaje (Personaje.Sombra) con su PROPIA pose: así «hacen lo que de
// verdad quieren» mientras el personaje sonríe.
import React from 'react';
import type {Escena, V3, Cam} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Camion, Caja, Banca, Estacion, Cartel} from '../Pueblo';
import {Personaje, Sombra, Pose} from '../Personaje';
import {DON_BRUNO, NINOS, EXTRAS} from '../personajes';
import {lerp, clamp} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p);
const cam = (pos: V3, look: V3, fov = 42, dof?: number): Cam => ({pos, look, fov, dof});
const LUCAS = NINOS.lucas, PAPA = EXTRAS.papa, NINO = 0.72, IZQ = Math.PI - 0.5, DER = Math.PI + 0.5; // sombras hacia la cámara, en diagonal: en vertical caben en el cuadro
const baile = (f: number): Pose => (['brazos_arriba', 'saluda', 'corre', 'brazos_arriba'] as Pose[])[Math.floor(f / 8) % 4];

export const ESCENAS: Record<string, Escena> = {
  // [Plaza de día. Un señor sonríe, pero su sombra le pega una patada a una lata.]
  lata: {
    pueblo: true,
    camaras: [cam([3.4, 3.2, 10.0], [1.0, 0.4, 5.4], 44, 0), cam([2.4, 1.8, 7.8], [0.6, 0.3, 5.4], 36)],
    render: (c) => {
      const pat = c.desde('l01', 'realmente', 14);
      return (
        <group>
          <Pueblo f={c.f} hora={10} />
          <Personaje pos={[0, 0, 5.2]} ropa={EXTRAS.vecino} cara="feliz" pose="quieto" f={c.f} rotY={0.3} />
          <Sombra pos={[0, 0, 5.2]} dir={IZQ - 0.3} ropa={EXTRAS.vecino} pose={pat > 0 && pat < 1 ? 'corre' : 'quieto'} f={c.f * 2} />
          <mesh position={[lerp(-1.9, -4.5, pat), 0.08 + Math.sin(pat * Math.PI) * 1.2, lerp(5.3, 4.6, pat)]} rotation={[pat * 8, 0, Math.PI / 2]} castShadow><cylinderGeometry args={[0.07, 0.07, 0.16, 12]} /><meshPhysicalMaterial color="#c0c0c8" metalness={0.8} roughness={0.3} /></mesh>
        </group>
      );
    },
  },
  // El señor dice: "Qué rico tu pastel"… y su sombra lo escupe.
  pastel: {
    pueblo: true,
    camaras: [cam([10.4, 2.6, 0.6], [9.0, 0.6, -3.0], 42, 0), cam([9.8, 1.6, -1.0], [9.0, 1.2, -3.0], 34)],
    render: (c) => {
      const esc = c.desde('l02', 'escupe.', 10);
      return (
        <group>
          <Pueblo f={c.f} hora={11} />
          <Personaje pos={[9.0, 0, -3.0]} ropa={EXTRAS.vecino} cara="feliz" pose="carga" f={c.f} rotY={0.3} />
          <mesh position={[9.15, 1.05, -2.6]} castShadow><cylinderGeometry args={[0.22, 0.22, 0.18, 20]} /><meshPhysicalMaterial color="#ff8fab" roughness={0.4} clearcoat={0.6} /></mesh>
          <Sombra pos={[9.0, 0, -3.0]} dir={IZQ - 0.4} ropa={EXTRAS.vecino} pose={esc > 0 ? 'agachado' : 'quieto'} f={c.f} />
          {esc > 0 && esc < 1 && <mesh position={[lerp(7.4, 6.4, esc), 0.03, lerp(-3.6, -4.0, esc)]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.18, 12]} /><meshBasicMaterial color="#1b1830" transparent opacity={0.6} /></mesh>}
        </group>
      );
    },
  },
  // La profe dice: "Qué buen dibujo"… y su sombra lo tira a la basura.
  dibujo: {
    pueblo: true,
    camaras: [cam([-8.4, 2.8, 9.4], [-10.6, 0.6, 5.6], 42, 0), cam([-8.4, 2.0, 8.8], [-10.8, 0.9, 5.8], 38)],
    render: (c) => {
      const tira = c.desde('l03', 'tira', 12);
      return (
        <group>
          <Pueblo f={c.f} hora={9.5} />
          <Personaje pos={[-10.6, 0, 5.8]} ropa={EXTRAS.profe} cara="feliz" pose="carga" f={c.f} rotY={0.6} />
          <Caja p={[-10.35, 1.05, 6.25]} s={[0.4, 0.3, 0.02]} c="#fffaf0" />
          <Sombra pos={[-10.6, 0, 5.8]} dir={IZQ} ropa={EXTRAS.profe} pose={tira > 0 ? 'senala' : 'carga'} f={c.f} />
          <Caja p={[-12.9, 0.35, 5.9]} s={[0.5, 0.7, 0.5]} c="#6c757d" />
          {tira > 0 && <mesh position={[lerp(-11.6, -12.9, tira), 0.03, 5.9]} rotation={[-Math.PI / 2, 0, tira * 3]}><planeGeometry args={[0.3, 0.2]} /><meshBasicMaterial color="#1b1830" transparent opacity={0.6} /></mesh>}
        </group>
      );
    },
  },
  // Las parejas se toman de la mano, pero sus sombras miran a otro lado.
  parejas: {
    pueblo: true,
    camaras: [cam([0, 3.4, 11.4], [0, 0.5, 6.2], 44, 0), cam([1.6, 1.6, 9.2], [0, 1.2, 6.2], 36)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={16} />
        <Personaje pos={[-0.45, 0, 6.2]} ropa={EXTRAS.mama} cara="feliz" pose="quieto" f={c.f} rotY={0.4} />
        <Personaje pos={[0.45, 0, 6.2]} ropa={EXTRAS.papa} cara="feliz" pose="quieto" f={c.f} rotY={-0.4} />
        <Sombra pos={[-0.45, 0, 6.2]} dir={IZQ} ropa={EXTRAS.mama} pose="quieto" f={c.f} />
        <Sombra pos={[0.45, 0, 6.2]} dir={DER} ropa={EXTRAS.papa} pose="quieto" f={c.f} />
      </group>
    ),
  },
  // Por eso todos caminan a mediodía, cuando la sombra es más pequeñita.
  mediodia: {
    pueblo: true,
    camaras: [cam([0, 2.6, 13.0], [0, 1.0, 5.0], 44, 0), cam([0, 9.5, -2], [0, 7.4, -12.5], 36, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={12} />
        {[[-2.4, EXTRAS.mama], [-0.6, EXTRAS.cartero], [1.4, EXTRAS.panadero], [3.0, EXTRAS.vecino]].map(([x, r], i) => {
          const p: V3 = [(x as number) + ((c.f * 0.02 + i) % 2) - 1, 0, 5.4 + (i % 2) * 0.8];
          return <group key={i}><Personaje pos={p} ropa={r as typeof PAPA} cara="feliz" pose="camina" f={c.f + i * 9} rotY={Math.PI / 2} /><Sombra pos={p} dir={IZQ} ropa={r as typeof PAPA} pose="camina" f={c.f + i * 9} largo={0.28} /></group>;
        })}
      </group>
    ),
  },
  // [Plano abierto de la plaza, sombras peleando entre ellas.]
  pelea: {
    pueblo: true,
    camaras: [cam([0, 4.6, 12.0], [0, 0.2, 5.6], 46, 0), cam([1.8, 2.0, 8.4], [0.4, 0.2, 5.8], 36)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={17.6} />
        <Personaje pos={[-1.2, 0, 5.0]} ropa={EXTRAS.vecino} cara="neutral" pose="quieto" f={c.f} />
        <Personaje pos={[1.2, 0, 5.0]} ropa={EXTRAS.cartero} cara="neutral" pose="quieto" f={c.f} />
        <Sombra pos={[-1.2, 0, 5.0]} dir={-0.8 + Math.sin(c.f / 5) * 0.2} ropa={EXTRAS.vecino} pose={Math.floor(c.f / 6) % 2 ? 'corre' : 'abraza'} f={c.f * 2} largo={1.5} />
        <Sombra pos={[1.2, 0, 5.0]} dir={0.8 - Math.sin(c.f / 5) * 0.2} ropa={EXTRAS.cartero} pose={Math.floor(c.f / 6) % 2 ? 'abraza' : 'corre'} f={c.f * 2} largo={1.5} />
      </group>
    ),
  },
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46, 0), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (<group><Pueblo f={c.f} hora={8.1} /><Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} /></group>),
  },
  // Yo me llamo Lucas, y nunca digo lo que siento.
  lucas: {
    pueblo: true,
    camaras: [cam([0.6, 1.6, 6.6], [2.4, 1.0, 11.0], 42), cam([1.8, 1.15, 8.8], [2.2, 1.0, 11.0], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.4} />
        <Camion p={[3.6, 0, 13.6]} rotY={Math.PI} f={c.f} />
        <Personaje pos={[2.2, 0, 11]} escala={NINO} ropa={LUCAS} cara="feliz" pose={c.u < 0.5 ? 'saluda' : 'quieto'} f={c.f} rotY={Math.PI - 0.25} />
        <Sombra pos={[2.2, 0, 11]} dir={IZQ + 0.3} escala={NINO} ropa={LUCAS} pose="quieto" f={c.f} />
      </group>
    ),
  },
  // [Casa. Papá pregunta, Lucas sonríe…] yo decía "sí"…
  casa: {
    interior: true,
    camaras: [cam(enC([0.8, 1.7, 3.6]), enC([-0.4, 1.0, -1.0]), 46, 0), cam(enC([0.2, 1.1, 1.4]), enC([-0.6, 0.95, -0.6]), 32, 12)],
    render: (c) => (
      <Cuarto pared="#ffe5b4" vacio>
        <Personaje pos={[0.9, 0, -0.9]} ropa={PAPA} cara="feliz" pose="senala" f={c.f} rotY={-1.2} />
        <Personaje pos={[-0.6, 0, -0.6]} escala={NINO} ropa={LUCAS} cara="feliz" pose="quieto" f={c.f} rotY={0.6} />
        <Sombra pos={[-0.6, 0, -0.6]} dir={IZQ} escala={NINO} ropa={LUCAS} pose="quieto" f={c.f} />
      </Cuarto>
    ),
  },
  // …y mi sombra se sentaba en una esquina, abrazando sus rodillas.
  rincon: {
    interior: true,
    camaras: [cam(enC([0.2, 1.4, 1.8]), enC([-3.2, 0.7, -2.9]), 40), cam(enC([0.8, 1.7, 3.6]), enC([-1.4, 0.8, -1.6]), 46, 0)],
    render: (c) => (
      <Cuarto pared="#ffe5b4" vacio>
        <Personaje pos={[-0.6, 0, -0.6]} escala={NINO} ropa={LUCAS} cara="feliz" pose="quieto" f={c.f} rotY={0.6} />
        <Sombra pos={[-3.4, 0, -3.1]} dir={0} levanta={1} escala={NINO} ropa={LUCAS} pose="abraza" f={c.f} />
        <Sombra pos={[-3.4, 0, -3.1]} dir={0} levanta={1} escala={NINO * 0.9} ropa={LUCAS} pose="sentado" f={c.f} />
      </Cuarto>
    ),
  },
  // [Escuela. Unos niños se burlan de él. Lucas se ríe. Su sombra llora.]
  burla: {
    pueblo: true,
    camaras: [cam([-6.8, 2.8, 8.6], [-9.6, 0.5, 5.2], 44, 0), cam([-8.4, 1.4, 7.0], [-9.6, 0.9, 5.4], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10.5} />
        <Personaje pos={[-9.6, 0, 5.4]} escala={NINO} ropa={LUCAS} cara="feliz" pose="quieto" f={c.f} rotY={0.8} />
        <Sombra pos={[-9.6, 0, 5.4]} dir={IZQ + 0.6} escala={NINO} ropa={LUCAS} pose="llora" f={c.f} />
        <Personaje pos={[-10.8, 0, 6.8]} escala={NINO} ropa={NINOS.teo} cara="feliz" pose="senala" f={c.f} rotY={2.4} />
        <Personaje pos={[-11.4, 0, 5.0]} escala={NINO} ropa={NINOS.sofi} cara="guino" pose="senala" f={c.f} rotY={1.7} />
      </group>
    ),
  },
  // [Plaza. Don Bruno da un discurso sonriendo.]
  discurso: {
    pueblo: true,
    camaras: [cam([0, 2.6, 12.0], [0, 1.6, 4.4], 44, 0), cam([1.6, 2.0, 8.2], [0, 2.0, 4.4], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={11} />
        <Caja p={[0, 0.25, 4.4]} s={[2.0, 0.5, 1.2]} c="#e63946" />
        <Personaje pos={[0, 0.5, 4.4]} ropa={DON_BRUNO} cara="feliz" pose={Math.floor(c.f / 30) % 2 ? 'saluda' : 'senala'} f={c.f} />
        <mesh position={[0.5, 1.2, 4.7]}><cylinderGeometry args={[0.02, 0.02, 1.4, 8]} /><meshLambertMaterial color="#333" /></mesh>
        {[-1.8, -0.6, 0.8, 2.0].map((x, i) => <Personaje key={i} pos={[x, 0, 7.0 + (i % 2) * 0.6]} ropa={[EXTRAS.mama, EXTRAS.vecino, EXTRAS.panadero, EXTRAS.cartero][i]} cara="neutral" pose="quieto" f={c.f} rotY={Math.PI} />)}
      </group>
    ),
  },
  // [Zoom al piso: la sombra de Don Bruno llorando a moco tendido.]
  brunoSombra: {
    pueblo: true,
    camaras: [cam([1.4, 2.6, 6.8], [-1.0, 0.3, 4.4], 38), cam([0.6, 1.8, 6.0], [-0.8, 0.5, 4.6], 32, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={11} />
        <Caja p={[0, 0.25, 4.4]} s={[2.0, 0.5, 1.2]} c="#e63946" />
        <Personaje pos={[0, 0.5, 4.4]} ropa={DON_BRUNO} cara="feliz" pose="saluda" f={c.f} />
        <Sombra pos={[-0.9, 0.0, 4.4]} dir={IZQ + 0.2} ropa={DON_BRUNO} pose="llora" f={c.f} largo={1.2} />
      </group>
    ),
  },
  // [Noche. Lucas sigue a la sombra de Don Bruno.] …hasta la estación del tren.
  estacion: {
    noche: true, pueblo: true,
    camaras: [cam([1.6, 2.2, -18.0], [0, 1.4, -30.0], 44, 0), cam([-1.4, 1.4, -21.0], [0, 1.2, -26.0], 36)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={22} />
        <Estacion noche />
        <Sombra pos={[lerp(0.4, 0.2, c.u), 0, lerp(-24, -30.5, c.u)]} dir={Math.PI} levanta={1} ropa={DON_BRUNO} pose="camina" f={c.f} />
        <Personaje pos={[lerp(0.8, 0.6, c.u), 0, lerp(-20, -26, c.u)]} escala={NINO} ropa={LUCAS} cara="miedo" pose="camina" f={c.f} rotY={Math.PI} />
      </group>
    ),
  },
  // Se quedó mirando un cartel viejo: "SE BUSCA PANADERO — CIUDAD GRANDE".
  cartel: {
    noche: true, pueblo: true,
    camaras: [cam([1.8, 1.9, -28.0], [-1.2, 2.0, -32.4], 38), cam([-1.2, 2.2, -29.4], [-2.6, 2.3, -32.4], 30, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={22.2} />
        <Estacion noche />
        <group position={[-2.6, 0, -32.5]}>
          <mesh position={[0, 1.1, 0]}><cylinderGeometry args={[0.05, 0.05, 2.2, 8]} /><meshLambertMaterial color="#5a3b2a" /></mesh>
          <Cartel p={[0, 2.5, 0.06]} w={1.7} texto="SE BUSCA PANADERO" fondo="#f1e3c6" color="#5a2d0c" />
          <Cartel p={[0, 2.05, 0.06]} w={1.5} texto="CIUDAD GRANDE" fondo="#f1e3c6" color="#8b4a2b" />
        </group>
        <Sombra pos={[-0.6, 0, -31.0]} dir={Math.PI + 0.5} levanta={1} ropa={DON_BRUNO} pose="quieto" f={c.f} />
        <Personaje pos={[1.0, 0, -29.8]} escala={NINO} ropa={LUCAS} cara="sorpresa" pose="quieto" f={c.f} rotY={-2.6} />
      </group>
    ),
  },
  // [Flashback simple: Don Bruno joven, con delantal de panadero.]
  joven: {
    pueblo: true,
    camaras: [cam([7.6, 1.6, -1.2], [9.2, 1.2, -4.0], 40), cam([8.2, 1.4, -2.2], [9.2, 1.5, -4.0], 32, 12)],
    render: (c) => {
      const obliga = c.f > c.W('l16', 'obligó.') - 4;
      return (
        <group>
          <Pueblo f={c.f} hora={16.5} />
          <Personaje pos={[9.2, 0, -4.0]} ropa={{...DON_BRUNO, bigote: undefined, barriga: false, banda: undefined, delantal: '#ffffff', sombrero: {tipo: 'panadero', color: '#ffffff'}, camisa: '#e9c46a'}} cara={obliga ? 'triste' : 'feliz'} pose={obliga ? 'quieto' : 'carga'} f={c.f} rotY={0.4} />
          {!obliga && <mesh position={[9.3, 1.0, -3.6]} rotation={[0, 0, Math.PI / 2]} castShadow><capsuleGeometry args={[0.13, 0.36, 6, 12]} /><meshPhysicalMaterial color="#d4a04c" roughness={0.6} /></mesh>}
          {obliga && <Personaje pos={[7.9, 0, -3.4]} ropa={{...DON_BRUNO, bigote: '#9a9a9a', camisa: '#3b3b3b'}} cara="enojo" pose="senala" f={c.f} rotY={2.0} />}
        </group>
      );
    },
  },
  // [Día. Lucas se acerca a Don Bruno en la plaza.] —Señor, su sombra quiere hacer pan.
  acerca: {
    pueblo: true,
    camaras: [cam([3.6, 1.7, 8.6], [0.6, 1.2, 5.0], 42), cam([1.6, 1.2, 7.2], [1.1, 1.0, 5.6], 32, 12)],
    cabezas: {lucas: [1.1, 1.45, 5.6]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={11.5} />
        <Personaje pos={[0, 0, 4.8]} ropa={DON_BRUNO} cara="feliz" pose="quieto" f={c.f} rotY={0.6} />
        <Sombra pos={[0, 0, 4.8]} dir={IZQ} ropa={DON_BRUNO} pose="llora" f={c.f} />
        <Personaje pos={[1.1, 0, 5.6]} escala={NINO} ropa={LUCAS} cara="neutral" pose="senala" f={c.f} rotY={-2.2} />
      </group>
    ),
  },
  // [Don Bruno se pone rojo. Silencio. Plano abierto: todo el pueblo mira.] … —Odio ser alcalde.
  callado: {
    pueblo: true,
    camaras: [cam([0, 3.0, 13.0], [0, 1.2, 5.0], 46, 0), cam([0.8, 1.9, 7.2], [0, 1.9, 4.8], 32, 12)],
    cabezas: {bruno: [0, 2.15, 4.8]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={11.6} />
        <Personaje pos={[0, 0, 4.8]} ropa={{...DON_BRUNO, piel: '#f08a7a'}} cara={c.f > c.W('l19') ? 'enojo' : 'sorpresa'} pose="quieto" f={c.f} />
        <Personaje pos={[1.1, 0, 5.6]} escala={NINO} ropa={LUCAS} cara="sorpresa" pose="quieto" f={c.f} rotY={-2.2} />
        {[[-2.6, 7.4, EXTRAS.mama], [-1.2, 8.0, EXTRAS.vecino], [2.4, 7.6, EXTRAS.panadero], [3.4, 6.8, EXTRAS.cartero], [-3.4, 6.4, EXTRAS.abuela]].map(([x, z, r], i) => (
          <Personaje key={i} pos={[x as number, 0, z as number]} ropa={r as typeof PAPA} cara="sorpresa" pose="quieto" f={c.f} rotY={Math.PI + (x as number) * 0.08} />
        ))}
      </group>
    ),
  },
  // [POP: su sombra se pone de pie y baila.]
  baila: {
    pueblo: true,
    camaras: [cam([2.6, 2.0, 9.6], [-0.6, 1.2, 4.6], 44, 0), cam([0.4, 1.6, 7.6], [-1.0, 1.3, 4.2], 36)],
    render: (c) => {
      const lev = c.desde('l20', 'levantó', 14);
      return (
        <group>
          <Pueblo f={c.f} hora={11.8} />
          <Personaje pos={[0, 0, 4.8]} ropa={DON_BRUNO} cara="sorpresa" pose="quieto" f={c.f} />
          <Sombra pos={[-1.2, 0, 4.4]} dir={IZQ * (1 - lev) + Math.sin(c.f / 6) * 0.5 * lev} levanta={lev} ropa={DON_BRUNO} pose={lev >= 1 ? baile(c.f) : 'quieto'} f={c.f} />
        </group>
      );
    },
  },
  // [Lucas mira a su papá.] Así que yo también lo dije: —Papá… extraño mi casa.
  papa: {
    pueblo: true,
    camaras: [cam([3.4, 1.6, 9.6], [1.6, 1.1, 6.8], 40), cam([2.8, 1.1, 8.6], [2.2, 1.0, 7.2], 32, 12)],
    cabezas: {lucas: [2.2, 1.45, 7.2]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={12} />
        <Personaje pos={[1.0, 0, 6.6]} ropa={PAPA} cara={c.f > c.W('l22') ? 'triste' : 'neutral'} pose="quieto" f={c.f} rotY={1.0} />
        <Personaje pos={[2.2, 0, 7.2]} escala={NINO} ropa={LUCAS} cara="triste" pose="quieto" f={c.f} rotY={-1.9} />
        <Sombra pos={[2.2, 0, 7.2]} dir={DER} escala={NINO} ropa={LUCAS} pose="llora" f={c.f} />
      </group>
    ),
  },
  // [Papá abraza a Lucas. Las dos sombras se abrazan.]
  abrazo: {
    pueblo: true,
    camaras: [cam([1.6, 3.0, 10.4], [1.6, 0.6, 6.6], 42, 0), cam([3.4, 1.4, 8.6], [1.7, 1.0, 6.8], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={12.2} />
        <Personaje pos={[1.4, 0, 6.6]} ropa={PAPA} cara="feliz" pose="abraza" f={c.f} rotY={1.2} />
        <Personaje pos={[2.0, 0, 6.8]} escala={NINO} ropa={LUCAS} cara="feliz" pose="abraza" f={c.f} rotY={-1.9} />
        <Sombra pos={[1.4, 0, 6.6]} dir={IZQ - 0.6} ropa={PAPA} pose="abraza" f={c.f} />
        <Sombra pos={[2.0, 0, 6.8]} dir={IZQ - 0.2} escala={NINO} ropa={LUCAS} pose="abraza" f={c.f} />
      </group>
    ),
  },
  // [Panadería con el cartel "PAN DE DON BRUNO".]
  panaderia: {
    pueblo: true,
    camaras: [cam([7.0, 1.9, -0.6], [10.4, 2.0, -5.4], 42, 0), cam([8.4, 1.5, -2.4], [9.4, 1.4, -4.2], 32, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9} panaderia="PAN DE DON BRUNO" />
        <Personaje pos={[9.2, 0, -4.0]} ropa={{...DON_BRUNO, delantal: '#ffffff', sombrero: {tipo: 'panadero', color: '#ffffff'}}} cara="feliz" pose="carga" f={c.f} rotY={0.5} />
        <mesh position={[9.35, 1.0, -3.55]} rotation={[0, 0.5, Math.PI / 2]} castShadow><capsuleGeometry args={[0.14, 0.4, 6, 12]} /><meshPhysicalMaterial color="#d4a04c" roughness={0.6} clearcoat={0.4} /></mesh>
        <Sombra pos={[9.2, 0, -4.0]} dir={IZQ} ropa={DON_BRUNO} pose={baile(c.f)} f={c.f} />
      </group>
    ),
  },
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.6, 13.5], [0, 1.0, 6.8], 46, 0), cam([3.0, 2.2, 12.5], [0, 1.0, 6.8], 42, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} panaderia="PAN DE DON BRUNO" />
        <Personaje pos={[1.3, 0, 6.6]} ropa={DON_BRUNO} cara="feliz" pose="saluda" f={c.f} />
        <Personaje pos={[-0.4, 0, 7.1]} escala={NINO} ropa={LUCAS} cara="feliz" pose="saluda" f={c.f + 9} />
        <Personaje pos={[-2.1, 0, 6.4]} ropa={PAPA} cara="feliz" pose="saluda" f={c.f + 4} />
        <Sombra pos={[1.3, 0, 6.6]} dir={DER} ropa={DON_BRUNO} pose="saluda" f={c.f} />
        <Sombra pos={[-0.4, 0, 7.1]} dir={IZQ} escala={NINO} ropa={LUCAS} pose="saluda" f={c.f + 9} />
      </group>
    ),
  },
};
export const _b = Banca;
