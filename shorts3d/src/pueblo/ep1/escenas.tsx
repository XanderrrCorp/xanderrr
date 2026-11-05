// Episodio 1 — «SI NADIE DICE TU NOMBRE, TE VUELVES INVISIBLE…» (bloques 3D brillantes). Guion del dueño tal cual.
// Volverse invisible = el plástico se vuelve transparente (opacidad del personaje).
import React from 'react';
import type {Escena, V3, Cam} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Camion, CajaCarton, Caja, Banca} from '../Pueblo';
import {Personaje} from '../Personaje';
import {DON_BRUNO, NINOS, EXTRAS} from '../personajes';
import {lerp, clamp} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p);
const cam = (pos: V3, look: V3, fov = 42, dof?: number): Cam => ({pos, look, fov, dof});
const TEO = NINOS.teo, ROSA = EXTRAS.abuela, NINO = 0.72;
const ROSA_FUENTE: V3 = [0.2, 0.68, 2.3]; // Doña Rosa sentada en el borde de la fuente
/** sombrero de copa solo, flotando (Don Bruno invisible) */
const Copa: React.FC<{p: V3}> = ({p}) => (
  <group position={p}>
    <mesh castShadow><cylinderGeometry args={[0.36, 0.36, 0.04, 28]} /><meshPhysicalMaterial color="#1a1a1a" roughness={0.3} clearcoat={1} /></mesh>
    <mesh position={[0, 0.23, 0]} castShadow><cylinderGeometry args={[0.22, 0.22, 0.44, 28]} /><meshPhysicalMaterial color="#1a1a1a" roughness={0.3} clearcoat={1} /></mesh>
    <mesh position={[0, 0.07, 0]}><cylinderGeometry args={[0.225, 0.225, 0.08, 28]} /><meshPhysicalMaterial color="#d62828" roughness={0.3} clearcoat={1} /></mesh>
  </group>
);
const Bolsa: React.FC<{p: V3; f: number; k: number}> = ({p, f, k}) => (
  <group position={[p[0], p[1] + Math.sin(f / 9 + k) * 0.08, p[2]]} rotation={[0, Math.sin(f / 20 + k) * 0.4, 0]}>
    <Caja p={[0, 0, 0]} s={[0.4, 0.45, 0.22]} c={['#f4a261', '#e9c46a', '#a8dadc'][k % 3]} />
    <mesh position={[0, 0.3, 0]}><torusGeometry args={[0.1, 0.02, 6, 14, Math.PI]} /><meshLambertMaterial color="#6c584c" /></mesh>
    {k % 2 === 0 && <mesh position={[0.05, 0.3, 0]}><sphereGeometry args={[0.1, 10, 8]} /><meshLambertMaterial color="#e63946" /></mesh>}
  </group>
);

export const ESCENAS: Record<string, Escena> = {
  // [Plaza de día. Un señor saca la basura y se va poniendo transparente.]
  basura: {
    pueblo: true,
    camaras: [cam([-2.5, 1.9, 9.5], [-5.0, 1.0, 13.0], 42), cam([-4.2, 1.4, 10.6], [-5.6, 1.1, 12.7], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8} />
        <Personaje pos={[lerp(-6.4, -5.2, c.u), 0, 12.6]} ropa={EXTRAS.vecino} cara={c.u > 0.5 ? 'sorpresa' : 'neutral'} pose="carga" f={c.f} rotY={0.4} opacidad={lerp(1, 0.18, clamp(c.u * 1.3))} />
        <Caja p={[lerp(-6.0, -4.8, c.u), 0.9, 13.0]} s={[0.45, 0.5, 0.4]} c="#2b2d42" />
      </group>
    ),
  },
  // "¡Buenos días, Marta!" "¡Buenos días, Pedro!"
  saludo: {
    pueblo: true,
    camaras: [cam([0, 1.9, 11.5], [0, 1.3, 6.4], 44, 0), cam([2.2, 1.6, 9.2], [0.9, 1.4, 6.4], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.5} />
        <Personaje pos={[-0.9, 0, 6.4]} ropa={EXTRAS.mama} cara="feliz" pose="saluda" f={c.f} rotY={0.9} />
        <Personaje pos={[0.9, 0, 6.4]} ropa={EXTRAS.papa} cara="feliz" pose="saluda" f={c.f + 7} rotY={-0.9} />
      </group>
    ),
  },
  // Los papás le ponen a sus hijos nombres cortitos…
  nombres: {
    pueblo: true,
    camaras: [cam([4.0, 1.6, 7.4], [6.4, 1.0, 3.6], 40), cam([5.0, 1.1, 5.4], [6.2, 0.9, 3.4], 32, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Personaje pos={[6.9, 0, 3.2]} ropa={EXTRAS.papa} cara="feliz" pose="senala" f={c.f} rotY={-0.9} />
        <Personaje pos={[6.0, 0, 3.6]} escala={0.6} ropa={{...EXTRAS.nino, camisa: '#ff70a6'}} cara="feliz" pose="quieto" f={c.f} rotY={0.3} nombre="LU" />
      </group>
    ),
  },
  // Hay quien se escribe su nombre en la camiseta, por si acaso.
  camiseta: {
    pueblo: true,
    camaras: [cam([6.6, 1.5, 4.4], [8.6, 1.3, 1.6], 34), cam([5.0, 2.0, 6.0], [8.6, 1.2, 1.6], 44)],
    render: (c) => <group><Pueblo f={c.f} hora={10.5} /><Personaje pos={[8.6, 0, 1.6]} ropa={{...EXTRAS.vecino, camisa: '#2a9d8f'}} cara="guino" pose="senala" f={c.f} rotY={-0.62} nombre="RAÚL" /></group>,
  },
  // Y el cartero reparte las cartas leyendo los sobres en voz alta, uno por uno.
  cartero: {
    pueblo: true,
    camaras: [cam([-2.0, 1.7, 7.2], [-4.8, 1.2, 11.0], 42), cam([-4.0, 1.4, 9.2], [-5.0, 1.4, 11.2], 32)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.5} />
        <Personaje pos={[lerp(-4.0, -5.6, c.u), 0, 11.2]} ropa={EXTRAS.cartero} cara="sorpresa" pose={c.u < 0.5 ? 'camina' : 'senala'} f={c.f} rotY={-0.6} />
        <Caja p={[lerp(-3.75, -5.35, c.u), 1.3, 10.85]} s={[0.3, 0.2, 0.02]} c="#fffaf0" />
      </group>
    ),
  },
  // [Bolsas de la compra flotando por la calle, solas.]
  bolsas: {
    pueblo: true,
    camaras: [cam([3.2, 1.5, 8.0], [5.5, 0.9, 12.0], 42), cam([7.4, 1.1, 9.4], [5.0, 0.9, 12.0], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={11} />
        {[0, 1, 2].map((k) => <Bolsa key={k} p={[lerp(8 - k * 1.5, 2 - k * 1.5, c.u), 0.7, 11.6 + (k % 2) * 0.9]} f={c.f} k={k} />)}
      </group>
    ),
  },
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46, 0), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (<group><Pueblo f={c.f} hora={8.1} /><Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} /></group>),
  },
  // Yo me llamo Teo. En la escuela nueva nadie me conocía.
  teo: {
    pueblo: true,
    camaras: [cam([-6.6, 1.6, 7.6], [-10.0, 1.4, 6.0], 44), cam([-8.6, 1.1, 6.9], [-10.0, 1.0, 6.0], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.6} />
        <Personaje pos={[-10.0, 0, 6.0]} escala={NINO} ropa={TEO} cara={c.u < 0.4 ? 'feliz' : 'triste'} pose={c.u < 0.4 ? 'saluda' : 'quieto'} f={c.f} rotY={1.1} />
        <Personaje pos={[-11.2, 0, 4.2]} escala={NINO} ropa={NINOS.lucas} cara="neutral" pose="camina" f={c.f} rotY={2.6} />
        <Personaje pos={[-11.6, 0, 7.6]} escala={NINO} ropa={NINOS.sofi} cara="neutral" pose="quieto" f={c.f} rotY={2.2} />
      </group>
    ),
  },
  // [Recreo. Teo solo en una banca. Sus manos se vuelven medio transparentes.]
  recreo: {
    pueblo: true,
    camaras: [cam([-6.8, 1.5, 2.6], [-8.8, 0.9, 1.0], 40), cam([-7.9, 1.0, 1.7], [-8.8, 0.85, 1.0], 30, 14)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10.5} />
        <Banca p={[-8.8, 0, 0.7]} rotY={0.9} />
        <Personaje pos={[-8.8, 0.08, 0.8]} escala={NINO} ropa={TEO} cara={c.u > 0.6 ? 'miedo' : 'triste'} pose={c.u > 0.4 ? 'carga' : 'sentado'} f={c.f} rotY={0.9} opacidad={lerp(1, 0.45, c.u)} />
      </group>
    ),
  },
  // [Noche, cuarto oscuro. Teo frente al espejo, casi invisible.]
  espejo: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.9, 1.25, 1.6]), enC([0.6, 1.0, -2.6]), 42), cam(enC([0.2, 1.1, 0.4]), enC([0.6, 1.0, -3.3]), 34)],
    render: (c) => (
      <Cuarto noche pared="#a0c4ff">
        <group position={[0.6, 0, -3.3]}>
          <Caja p={[0, 1.15, 0]} s={[1.3, 1.9, 0.08]} c="#c9a227" />
          <mesh position={[0, 1.15, 0.05]}><planeGeometry args={[1.1, 1.7]} /><meshPhysicalMaterial color="#cfe7ff" roughness={0.05} metalness={0.6} transparent opacity={0.85} /></mesh>
        </group>
        <Personaje pos={[0.6, 0, -2.1]} escala={NINO} ropa={{...TEO, mochila: undefined}} cara="miedo" pose="quieto" f={c.f} rotY={Math.PI} opacidad={0.2} />
        <Personaje pos={[0.6, 0, -4.2]} escala={NINO} ropa={{...TEO, mochila: undefined}} cara="miedo" pose="quieto" f={c.f} rotY={0} opacidad={0.12} />
      </Cuarto>
    ),
  },
  // [Día. Una abuelita en la plaza, saludando a todos.]
  rosa: {
    pueblo: true,
    camaras: [cam([0.4, 1.9, 8.6], [0.2, 1.1, 2.6], 44, 0), cam([1.6, 1.3, 4.6], [0.2, 1.3, 2.4], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara="feliz" pose={Math.floor(c.f / 40) % 2 ? 'saluda' : 'sentado'} f={c.f} />
        <Personaje pos={[lerp(-4, 3, (c.f % 160) / 160), 0, 4.6]} ropa={EXTRAS.panadero} cara="neutral" pose="camina" f={c.f} rotY={Math.PI / 2} />
        <Personaje pos={[lerp(4, -3, ((c.f + 60) % 180) / 180), 0, 5.6]} ropa={EXTRAS.cartero} cara="neutral" pose="camina" f={c.f} rotY={-Math.PI / 2} />
      </group>
    ),
  },
  // Y a ella… nadie la saludaba.
  rosaSola: {
    pueblo: true,
    camaras: [cam([1.3, 1.6, 6.0], [0.2, 1.3, 2.4], 34, 12), cam([-3.0, 2.4, 9.0], [0.2, 1.0, 2.6], 46, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.2} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara="triste" pose="sentado" f={c.f} />
        <Personaje pos={[lerp(3, -4, c.u), 0, -2.8]} ropa={EXTRAS.vecino} cara="neutral" pose="camina" f={c.f} rotY={-Math.PI / 2} />
      </group>
    ),
  },
  // [Teo se acerca, casi transparente.] diálogo con Doña Rosa
  acerca: {
    pueblo: true,
    camaras: [cam([4.4, 1.6, 5.6], [0.6, 1.1, 2.9], 42), cam([1.3, 1.65, 4.3], [0.2, 1.45, 2.3], 34, 12), cam([2.2, 1.2, 2.0], [1.0, 1.0, 3.4], 32, 12)],
    cabezas: {rosa: [0.2, 2.05, 2.3], teo: [1.0, 1.45, 3.4]},
    render: (c) => {
      const vuelve = c.f > c.W('l16', 'Teo!');
      return (
        <group>
          <Pueblo f={c.f} hora={9.4} />
          <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara="feliz" pose={vuelve ? 'saluda' : 'sentado'} f={c.f} rotY={0.5} />
          <Personaje pos={[1.0, 0, 3.4]} escala={NINO} ropa={TEO} cara="triste" pose="quieto" f={c.f} rotY={-2.51} opacidad={0.22} />
        </group>
      );
    },
  },
  // [POP. Teo vuelve a ser sólido.]
  pop: {
    pueblo: true,
    camaras: [cam([-0.3, 1.35, 2.0], [1.0, 1.0, 3.4], 34, 12), cam([4.4, 1.6, 5.6], [0.6, 1.1, 2.9], 42)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.5} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara="feliz" pose="sentado" f={c.f} rotY={0.5} />
        <Personaje pos={[1.0, Math.max(0, Math.sin(c.desde('l17', 'Pop.', 10) * Math.PI)) * 0.25, 3.4]} escala={NINO} ropa={TEO} cara="feliz" pose="brazos_arriba" f={c.f} rotY={-2.51} opacidad={c.f > c.W('l17', 'Pop.') ? 1 : 0.22} />
      </group>
    ),
  },
  // [Teo mira la alcaldía. Ventana vacía, un sombrero de copa flotando.]
  alcaldia: {
    pueblo: true,
    camaras: [cam([-4.6, 1.5, 0.2], [-9.4, 2.4, -6.0], 44, 0), cam([-6.0, 1.3, -1.4], [-4.8, 1.0, 0.4], 40)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Personaje pos={[-4.6, 0, -1.0]} escala={NINO} ropa={TEO} cara="sorpresa" pose="quieto" f={c.f} rotY={-2.4} />
      </group>
    ),
  },
  // Solo se veía su sombrero de copa paseándose por la alcaldía.
  sombrero: {
    pueblo: true,
    camaras: [cam([-7.0, 1.6, -2.4], [-9.6, 1.6, -5.2], 40), cam([-6.0, 2.4, -0.4], [-9.6, 1.5, -5.0], 46, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10.2} />
        <Copa p={[lerp(-10.6, -8.6, 0.5 + 0.5 * Math.sin(c.f / 25)), 1.9 + Math.abs(Math.sin(c.f * 0.3)) * 0.05, -4.7]} />
      </group>
    ),
  },
  // —¿Y Don Bruno? / —Uy, nadie le dice el nombre…
  pregunta: {
    pueblo: true,
    camaras: [cam([4.4, 1.6, 5.6], [0.6, 1.1, 2.9], 42), cam([1.3, 1.65, 4.3], [0.2, 1.45, 2.3], 34, 12), cam([2.2, 1.2, 2.0], [1.0, 1.0, 3.4], 32, 12)],
    cabezas: {rosa: [0.2, 2.05, 2.3], teo: [1.0, 1.45, 3.4]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10.5} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara={c.f > c.W('l21') ? 'guino' : 'neutral'} pose="sentado" f={c.f} rotY={0.5} />
        <Personaje pos={[1.0, 0, 3.4]} escala={NINO} ropa={TEO} cara="sorpresa" pose="quieto" f={c.f} rotY={-2.51} />
      </group>
    ),
  },
  // [Teo corre a la plaza y se sube a la fuente.]
  fuente: {
    pueblo: true,
    camaras: [cam([0, 2.6, 9.5], [0, 1.6, 0], 46, 0), cam([2.4, 1.2, 4.4], [0.6, 1.5, 1.2], 38)],
    render: (c) => {
      const s = clamp((c.f - c.W('l22', 'subí')) / 12);
      return (
        <group>
          <Pueblo f={c.f} hora={9} />
          <Personaje pos={[lerp(0.8, 0.6, s), lerp(0, 0.7, s) + Math.sin(s * Math.PI) * 0.4, lerp(4.5, 1.7, s)]} escala={NINO} ropa={TEO} cara="feliz" pose={s < 1 ? 'corre' : 'quieto'} f={c.f} rotY={Math.PI} />
        </group>
      );
    },
  },
  // —¡BUENOS DÍAS, DON BRUNO!
  grito: {
    pueblo: true,
    camaras: [cam([0.6, 1.4, 4.4], [0.6, 1.7, 1.7], 34, 12), cam([-2.6, 3.2, 8.0], [0, 1.8, 0], 46, 0)],
    cabezas: {teo: [0.6, 2.2, 1.7]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.1} />
        <Personaje pos={[0.6, 0.7, 1.7]} escala={NINO} ropa={TEO} cara="sorpresa" pose="brazos_arriba" f={c.f} rotY={0} />
      </group>
    ),
  },
  // [Don Bruno aparece de golpe con un pan en la mano, avergonzado.]
  aparece: {
    pueblo: true,
    camaras: [cam([-1.6, 1.8, 7.6], [-1.2, 1.3, 4.2], 38), cam([-0.4, 1.7, 6.0], [-1.2, 1.7, 4.2], 32, 12)],
    render: (c) => {
      const ya = c.f >= c.W('l24', 'apareció.') - 1;
      return (
        <group>
          <Pueblo f={c.f} hora={9.2} />
          {ya ? <Personaje pos={[-1.2, 0, 4.2]} ropa={DON_BRUNO} cara={c.f > c.W('l24', 'pan') ? 'triste' : 'sorpresa'} pose="carga" f={c.f} rotY={0.2} /> : <Copa p={[-1.2, 2.05, 4.2]} />}
          {ya && <mesh position={[-1.2, 1.0, 4.65]} rotation={[0, 0, Math.PI / 2]} scale={[1, 1, 0.8]} castShadow><capsuleGeometry args={[0.14, 0.4, 6, 12]} /><meshPhysicalMaterial color="#d4a04c" roughness={0.6} clearcoat={0.3} /></mesh>}
          <Personaje pos={[0.6, 0.7, 1.7]} escala={NINO} ropa={TEO} cara="feliz" pose="quieto" f={c.f} rotY={-0.6} />
        </group>
      );
    },
  },
  // [Doña Rosa sonríe. Corte a Doña Rosa empezando a ponerse transparente.]
  rosaBorra: {
    pueblo: true,
    camaras: [cam([1.3, 1.6, 6.0], [0.2, 1.3, 2.4], 34, 12), cam([0.4, 1.9, 8.6], [0.2, 1.1, 2.6], 44, 0)],
    render: (c) => <group><Pueblo f={c.f} hora={9.4} /><Personaje pos={ROSA_FUENTE} ropa={ROSA} cara={c.u < 0.25 ? 'feliz' : 'triste'} pose="sentado" f={c.f} opacidad={lerp(1, 0.25, clamp(c.u * 1.4 - 0.2))} /></group>,
  },
  // [Teo se lo dice al oído al alcalde. Plano abierto: todo el pueblo en la plaza.]
  pueblo: {
    pueblo: true,
    camaras: [cam([0, 3.4, 13.5], [0, 1.2, 3], 50, 0), cam([2.4, 1.6, 7.6], [0.2, 1.2, 2.6], 40)],
    cabezas: {pueblo: [0.6, 2.4, 5.6]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.6} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara={c.f > c.W('l26', 'ROSA!') ? 'llora' : 'sorpresa'} pose="sentado" f={c.f} opacidad={c.f > c.W('l26', 'ROSA!') ? 1 : 0.3} />
        <Personaje pos={[1.6, 0, 5.4]} ropa={DON_BRUNO} cara="feliz" pose="brazos_arriba" f={c.f} rotY={Math.PI} />
        <Personaje pos={[0.6, 0, 5.9]} escala={NINO} ropa={TEO} cara="feliz" pose="brazos_arriba" f={c.f + 5} rotY={Math.PI} />
        {[[-1.6, 6.2, EXTRAS.mama], [-0.4, 6.8, EXTRAS.papa], [2.8, 6.4, EXTRAS.panadero], [-2.8, 5.6, EXTRAS.cartero], [3.6, 5.2, EXTRAS.vecino], [1.2, 7.2, EXTRAS.profe]].map(([x, z, r], i) => (
          <Personaje key={i} pos={[x as number, 0, z as number]} ropa={r as typeof ROSA} cara="feliz" pose="brazos_arriba" f={c.f + i * 6} rotY={Math.PI} />
        ))}
      </group>
    ),
  },
  // [Doña Rosa vuelve a ser sólida y llora de felicidad.] Ahora, cada mañana, es ella la que se sienta a escuchar.
  final: {
    pueblo: true,
    camaras: [cam([1.3, 1.6, 6.0], [0.2, 1.3, 2.4], 34, 12), cam([0.4, 1.9, 8.6], [0.2, 1.1, 2.6], 44, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9} />
        <Personaje pos={ROSA_FUENTE} ropa={ROSA} cara={c.u < 0.4 ? 'llora' : 'feliz'} pose="sentado" f={c.f} />
        <Personaje pos={[-1.4, 0, 4.2]} ropa={EXTRAS.mama} cara="feliz" pose="saluda" f={c.f} rotY={2.4} />
        <Personaje pos={[1.8, 0, 4.4]} escala={NINO} ropa={TEO} cara="feliz" pose="saluda" f={c.f + 8} rotY={-2.4} />
      </group>
    ),
  },
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.0, 13.5], [0, 1.2, 6.8], 46, 0), cam([3.0, 1.8, 12.5], [0, 1.1, 6.8], 42, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Personaje pos={[1.3, 0, 6.6]} ropa={DON_BRUNO} cara="feliz" pose="saluda" f={c.f} />
        <Personaje pos={[-0.4, 0, 7.1]} escala={NINO} ropa={TEO} cara="feliz" pose="saluda" f={c.f + 9} />
        <Personaje pos={[-2.3, 0, 6.3]} ropa={ROSA} cara="feliz" pose="saluda" f={c.f + 4} rotY={0.3} />
      </group>
    ),
  },
};
export const _cc = CajaCarton;
