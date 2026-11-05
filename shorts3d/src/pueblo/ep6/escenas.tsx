// Episodio 6 — «SI ROMPES ALGO, APARECE EN TU CAMA!» (personajes 2D de la skill). Guion del dueño tal cual.
import React, {useMemo} from 'react';
import type {Escena, V3, Cam} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Camion, Caja, Aula, AULA} from '../Pueblo';
import {Carta2D, cabeza2D} from '../Carta2D';
import {BRUNO_2D, NINOS_2D, EXTRAS_2D} from '../personajes2d';
import {lerp, clamp, rnd} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p), enA = (p: V3) => add(AULA, p);
const cam = (pos: V3, look: V3, fov = 42, dof?: number): Cam => ({pos, look, fov, dof});
const LEO = NINOS_2D.leo, DANI = NINOS_2D.dani;
const CAMA: V3 = [-2.2, 0.58, -2.2];
const PIE: V3 = [-2.2, 0.58, -0.9]; // al pie de la cama, sentado mirando a la cámara
const Cobija: React.FC<{alto?: number}> = ({alto = 0.55}) => <Caja p={[-2.2, 0.6, -1.55]} s={[1.5, alto, 0.25]} c="#4ea8de" />;
const camsCuarto = {
  abierto: cam(enC([0.4, 2.4, 4.4]), enC([-0.8, 1.2, -1.8]), 50, 0),
  cama: cam(enC([-0.9, 1.5, 0.9]), enC([-2.2, 1.1, -2.0]), 42),
  cara: cam(enC([-1.7, 1.55, -0.2]), enC([-2.2, 1.4, -2.2]), 34, 13),
};
/** montón de cosas sobre la cama (trozos, dulces, tierra…) */
const Monton: React.FC<{n: number; col: string[]; s?: number; y?: number; seed?: number; esfera?: boolean; vidrio?: boolean}> = ({n, col, s = 0.12, y = 0.9, seed = 1, esfera, vidrio}) => {
  const ps = useMemo(() => Array.from({length: n}, (_, i) => ({x: -2.2 + (rnd(i, seed) - 0.5) * 1.2, z: -1.5 + (rnd(i, seed + 1) - 0.5) * 0.5, r: rnd(i, seed + 2) * 3, k: 0.6 + rnd(i, seed + 3) * 0.8})), [n, seed]);
  return (<>{ps.map((q, i) => (
    <mesh key={i} position={[q.x, y + rnd(i, seed + 4) * 0.12, q.z]} rotation={[q.r, q.r * 2, q.r * 0.5]} scale={s * q.k} castShadow>
      {esfera ? <sphereGeometry args={[1, 10, 8]} /> : <tetrahedronGeometry args={[1.2, 0]} />}
      {vidrio ? <meshPhysicalMaterial color="#bfe7ff" roughness={0.05} transparent opacity={0.7} clearcoat={1} /> : <meshLambertMaterial color={col[i % col.length]} />}
    </mesh>
  ))}</>);
};
const Cama2D: React.FC<{c: {f: number}; quien: typeof LEO; expr: Parameters<typeof Carta2D>[0]['expr']; pared?: string; noche?: boolean; children?: React.ReactNode}> = ({c, quien, expr, pared = '#fde2e4', noche, children}) => (
  <Cuarto noche={noche} pared={pared}>
    <Carta2D pos={CAMA} ropa={quien} expr={expr} modo="sit" f={c.f} seed={quien === LEO ? 2 : 9} />
    <Cobija />
    {children}
  </Cuarto>
);
const Carrito: React.FC<{p: V3}> = ({p}) => (
  <group position={p} rotation={[0.1, 0.4, 0.05]}>
    <Caja p={[0, 0.25, 0]} s={[1.4, 0.35, 0.7]} c="#e63946" />
    <Caja p={[0, 0.55, 0]} s={[0.8, 0.3, 0.6]} c="#e63946" />
    <Caja p={[0, 0.56, 0.31]} s={[0.7, 0.22, 0.02]} c="#a8dadc" />
    {[[-0.45, 0.36], [0.45, 0.36], [-0.45, -0.36], [0.45, -0.36]].map(([x, z], i) => <mesh key={i} position={[x, 0.1, z]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.14, 0.14, 0.1, 14]} /><meshLambertMaterial color="#222" /></mesh>)}
  </group>
);
// la casa de Don Bruno: la de [-6, 0, 15] (mira hacia la plaza, -z). El montón de cosas rotas, delante.
const CASA: V3 = [-6, 0, 12.4];
const MontonCasa: React.FC<{k: number; f: number}> = ({k, f}) => {
  const ps = useMemo(() => Array.from({length: 26}, (_, i) => ({x: (rnd(i, 7) - 0.5) * 3.6, h: rnd(i, 8), z: (rnd(i, 9) - 0.5) * 1.2, c: ['#8d99ae', '#c08552', '#e9c46a', '#a3b18a', '#e76f51', '#ffffff'][i % 6], s: 0.3 + rnd(i, 10) * 0.5, r: rnd(i, 11) * 2})), []);
  return (<>{ps.map((q, i) => {
    const vivo = clamp(k * 26 - i);
    if (vivo <= 0) return null;
    return <Caja key={i} p={[CASA[0] + q.x, q.s / 2 + q.h * 3.6 * (1 - Math.abs(q.x) / 2.2), CASA[2] + q.z]} s={[q.s * vivo, q.s * vivo, q.s * vivo]} c={q.c} r={[q.r, q.r, 0.3 * Math.sin(f / 30 + i)]} />;
  })}</>);
};

export const ESCENAS: Record<string, Escena> = {
  // [Amanecer. Un niño despierta y hay un plato roto en su almohada.]
  plato: {
    interior: true,
    camaras: [camsCuarto.cama, cam(enC([-1.6, 1.4, -1.4]), enC([-2.2, 1.0, -2.6]), 34, 13)],
    render: (c) => <Cama2D c={c} quien={NINOS_2D.nino} expr="shock" pared="#ffe5b4"><Monton n={5} col={['#ffffff', '#dfe7ef']} s={0.13} y={0.82} seed={3} /></Cama2D>,
  },
  // Un señor rompió una ventana y amaneció lleno de vidrios.
  vidrios: {
    interior: true,
    camaras: [camsCuarto.cama, camsCuarto.abierto],
    render: (c) => <Cama2D c={c} quien={EXTRAS_2D.papa} expr="pained" pared="#d8e2dc"><Monton n={22} col={['#fff']} s={0.09} y={0.95} seed={5} vidrio /></Cama2D>,
  },
  // El que chocó el carro amaneció con el carro encima.
  carro: {
    interior: true,
    camaras: [camsCuarto.abierto, camsCuarto.cama],
    render: (c) => <Cama2D c={c} quien={EXTRAS_2D.vecino} expr="dazed" pared="#cdb4db"><Carrito p={[-2.2, 0.85, -1.6]} /></Cama2D>,
  },
  // El que rompió la piñata, lleno de dulces. A ese le fue bien.
  pinata: {
    interior: true,
    camaras: [camsCuarto.cama, camsCuarto.cara],
    render: (c) => <Cama2D c={c} quien={NINOS_2D.ana} expr={c.u > 0.5 ? 'laugh' : 'grin'} pared="#ffc8dd"><Monton n={40} col={['#ef476f', '#ffd166', '#06d6a0', '#118ab2', '#f78c6b']} s={0.07} y={0.9} seed={8} esfera /></Cama2D>,
  },
  // Por eso aquí todos caminan despacito.
  despacito: {
    pueblo: true,
    camaras: [cam([0, 2.0, 12.5], [0, 1.2, 5.6], 44, 0), cam([2.8, 1.2, 8.6], [1.4, 1.0, 5.6], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={9.5} />
        {[[-2.4, EXTRAS_2D.vecina], [-0.4, EXTRAS_2D.vecino], [1.6, EXTRAS_2D.papa], [3.2, EXTRAS_2D.mama]].map(([x, r], i) => (
          <Carta2D key={i} pos={[(x as number) + ((c.f * 0.004) % 0.6), 0, 5.6 + (i % 2) * 0.6]} ropa={r as typeof LEO} expr="nervous" f={Math.floor(c.f / 3)} caminar seed={40 + i} />
        ))}
      </group>
    ),
  },
  // Y nadie juega fútbol cerca de las casas.
  futbol: {
    pueblo: true,
    camaras: [cam([10, 2.4, 25], [6, 1.0, 30], 44, 0), cam([7.5, 1.1, 27.5], [6.5, 0.9, 30.5], 34)],
    render: (c) => {
      const t = (c.f % 50) / 50;
      return (
        <group>
          <Pueblo f={c.f} hora={16} />
          <Carta2D pos={[5, 0, 30]} ropa={NINOS_2D.nino} expr="grin" f={c.f} seed={41} />
          <Carta2D pos={[8, 0, 31]} ropa={DANI} expr="laugh" f={c.f} seed={9} />
          <mesh position={[lerp(5.4, 7.6, Math.abs(1 - 2 * t)), 0.2 + Math.sin(Math.abs(1 - 2 * t) * Math.PI) * 1.0, 30.5]} castShadow><icosahedronGeometry args={[0.2, 1]} /><meshLambertMaterial color="#ffffff" /></mesh>
        </group>
      );
    },
  },
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46, 0), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (<group><Pueblo f={c.f} hora={8.1} /><Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} /></group>),
  },
  // Me llamo Leo. El primer día rompí el florero de mamá.
  florero: {
    interior: true,
    camaras: [cam(enC([0.6, 1.6, 3.0]), enC([0.4, 1.0, -0.6]), 42), cam(enC([0.9, 0.7, 0.9]), enC([0.6, 0.3, -0.2]), 34, 12)],
    render: (c) => {
      const roto = c.f > c.W('l08', 'rompí');
      return (
        <Cuarto pared="#fde2e4" vacio>
          <Carta2D pos={[0, 0, -0.8]} ropa={LEO} expr={roto ? 'shock' : 'smile'} f={c.f} seed={2} />
          {!roto && <group position={[0.7, 0, -0.4]}><mesh position={[0, 0.25, 0]} castShadow><cylinderGeometry args={[0.14, 0.1, 0.5, 14]} /><meshLambertMaterial color="#4895ef" /></mesh>{[-0.08, 0, 0.08].map((x) => <mesh key={x} position={[x, 0.62, 0]}><sphereGeometry args={[0.07, 8, 6]} /><meshLambertMaterial color="#ff70a6" /></mesh>)}</group>}
          {roto && [0, 1, 2, 3, 4].map((i) => <mesh key={i} position={[0.6 + (rnd(i, 1) - 0.5) * 0.6, 0.04, -0.3 + (rnd(i, 2) - 0.5) * 0.5]} rotation={[rnd(i, 3) * 3, rnd(i, 4) * 3, 0]} scale={0.08} castShadow><tetrahedronGeometry args={[1, 0]} /><meshLambertMaterial color="#4895ef" /></mesh>)}
          {roto && <mesh position={[0.7, 0.03, -0.35]} scale={[0.4, 0.05, 0.3]}><sphereGeometry args={[1, 10, 6]} /><meshLambertMaterial color="#6f4518" /></mesh>}
        </Cuarto>
      );
    },
  },
  // [Leo despierta con el florero y la tierra en la cama.]
  tierra: {
    interior: true,
    camaras: [camsCuarto.cama, camsCuarto.cara],
    render: (c) => (
      <Cama2D c={c} quien={LEO} expr="dazed">
        <Monton n={16} col={['#6f4518', '#7f5539']} s={0.12} y={0.85} seed={12} esfera />
        <Monton n={5} col={['#4895ef']} s={0.1} y={0.95} seed={14} />
        {[-2.5, -2.0].map((x) => <mesh key={x} position={[x, 1.05, -1.5]}><sphereGeometry args={[0.07, 8, 6]} /><meshLambertMaterial color="#ff70a6" /></mesh>)}
      </Cama2D>
    ),
  },
  // [Escuela. Leo conoce a Dani. Juegan, se ríen.]
  amigos: {
    pueblo: true,
    camaras: [cam([-6.4, 1.6, 8.6], [-9.6, 1.1, 5.8], 42), cam([-8.0, 1.2, 7.2], [-9.4, 1.0, 5.6], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Carta2D pos={[-9.8, 0, 6.2]} ropa={LEO} expr={c.u > 0.4 ? 'laugh' : 'smile'} f={c.f} seed={2} saluda={c.u < 0.4} />
        <Carta2D pos={[-8.9, 0, 5.4]} ropa={DANI} expr={c.u > 0.4 ? 'laugh' : 'grin'} f={c.f} seed={9} />
      </group>
    ),
  },
  // [Recreo. Leo le cuenta un secreto de Dani a otros niños. Todos se ríen. Dani se va.]
  secreto: {
    interior: true,
    camaras: [cam(enA([2.4, 1.7, 5.2]), enA([0, 1.0, 1.2]), 46, 0), cam(enA([0.9, 1.2, 3.4]), enA([0.2, 1.1, 1.6]), 34, 12)],
    render: (c) => (
      <Aula>
        <Carta2D pos={[0.2, 0, 1.6]} ropa={LEO} expr="grin" f={c.f} seed={2} />
        <Carta2D pos={[-1.6, 0, 1.0]} ropa={NINOS_2D.ana} expr="laugh" f={c.f} seed={21} />
        <Carta2D pos={[1.8, 0, 1.0]} ropa={NINOS_2D.nino} expr="laugh" f={c.f} seed={22} />
        <Carta2D pos={[-0.8, 0, 0.2]} ropa={NINOS_2D.sofi} expr="laugh" f={c.f} seed={23} />
        <Carta2D pos={[3.2, 0, 2.6]} ropa={DANI} expr="sad" f={c.f} seed={9} />
      </Aula>
    ),
  },
  // Dani dejó de hablarme.
  seva: {
    pueblo: true,
    camaras: [cam([-6.4, 1.6, 8.6], [-9.6, 1.1, 5.8], 42), cam([-7.6, 1.3, 7.0], [-9.0, 1.1, 5.8], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={15} />
        <Carta2D pos={[-8.2, 0, 7.2]} ropa={LEO} expr="sad" f={c.f} seed={2} />
        <Carta2D pos={[lerp(-9.4, -11.6, c.u), 0, lerp(5.6, 3.6, c.u)]} ropa={DANI} expr="sad" f={c.f} caminar seed={9} />
      </group>
    ),
  },
  // [Noche. Leo se duerme.]
  dormir: {
    noche: true, interior: true,
    camaras: [camsCuarto.abierto, camsCuarto.cara],
    render: (c) => <Cama2D c={c} quien={LEO} expr="sleep" noche />,
  },
  // [Amanecer. Leo despierta. A los pies de la cama está Dani, sentado y triste.] + diálogo
  pie: {
    interior: true,
    camaras: [cam(enC([0.6, 1.7, 2.6]), enC([-1.8, 1.0, -1.6]), 42), camsCuarto.cara, cam(enC([-1.4, 1.1, 1.2]), enC([-2.2, 1.0, -0.9]), 34, 12)],
    cabezas: {leo: enC(cabeza2D(CAMA, 1, true)), dani: enC(cabeza2D(PIE, 1, true))},
    render: (c) => (
      <Cama2D c={c} quien={LEO} expr={c.f > c.W('l15') ? 'nervous' : 'shock'} pared="#fde2e4">
        <Carta2D pos={PIE} ropa={DANI} expr="sad" modo="sit" f={c.f} seed={9} />
      </Cama2D>
    ),
  },
  // [Leo entiende.] Entonces entendí: había roto algo. Nuestra amistad.
  entiende: {
    interior: true,
    camaras: [camsCuarto.cara, cam(enC([-1.4, 1.1, 1.2]), enC([-2.2, 1.0, -0.9]), 34, 12)],
    render: (c) => <Cama2D c={c} quien={LEO} expr="sad"><Carta2D pos={PIE} ropa={DANI} expr="sad" modo="sit" f={c.f} seed={9} /></Cama2D>,
  },
  // [Montaje: Leo intenta arreglarlo con pegamento, cinta, una carta.]
  arreglar: {
    interior: true,
    camaras: [cam(enC([0.4, 1.4, 2.6]), enC([0, 1.0, -0.6]), 40), cam(enC([0.6, 1.2, 1.2]), enC([0.1, 1.0, -0.6]), 32, 12)],
    render: (c) => {
      const k = c.f < c.W('l18', 'cinta,') ? 0 : c.f < c.W('l18', 'carta.') ? 1 : 2;
      return (
        <Cuarto pared="#fde2e4" vacio>
          <Carta2D pos={[0, 0, -0.8]} ropa={LEO} expr={c.f > c.W('l18', 'Nada.') ? 'sad' : 'nervous'} f={c.f} seed={2} />
          <group position={[0.5, 1.05, -0.55]}>
            {k === 0 && <><mesh castShadow><cylinderGeometry args={[0.07, 0.07, 0.22, 12]} /><meshLambertMaterial color="#f8f9fa" /></mesh><mesh position={[0, 0.15, 0]}><coneGeometry args={[0.05, 0.1, 10]} /><meshLambertMaterial color="#e63946" /></mesh></>}
            {k === 1 && <mesh rotation={[Math.PI / 2, 0, 0]} castShadow><torusGeometry args={[0.1, 0.04, 8, 20]} /><meshLambertMaterial color="#e9ecef" /></mesh>}
            {k === 2 && <Caja p={[0, 0, 0]} s={[0.3, 0.2, 0.02]} c="#fffaf0" />}
          </group>
        </Cuarto>
      );
    },
  },
  // Cada mañana, Dani aparecía otra vez al pie de mi cama.
  pie2: {
    interior: true,
    camaras: [cam(enC([0.6, 1.7, 2.6]), enC([-1.8, 1.0, -1.6]), 42), cam(enC([-1.4, 1.1, 1.2]), enC([-2.2, 1.0, -0.9]), 34, 12)],
    render: (c) => {
      const k = Math.floor(c.u * 3);
      return <Cama2D c={c} quien={LEO} expr="sad" pared={['#fde2e4', '#e9edc9', '#cdb4db'][k]}><Carta2D pos={PIE} ropa={DANI} expr={k === 2 ? 'stern' : 'sad'} modo="sit" f={c.f} seed={9} /></Cama2D>;
    },
  },
  // [Calle. Una casa enorme llena de cosas rotas apiladas hasta el techo: la de Don Bruno.]
  brunoCasa: {
    pueblo: true,
    camaras: [cam([-3.0, 2.6, 4.2], [-6.0, 2.4, 13.0], 46, 0), cam([-4.6, 1.4, 9.0], [-6.0, 1.4, 12.4], 36)],
    render: (c) => <group><Pueblo f={c.f} hora={11} /><MontonCasa k={1} f={c.f} /><Carta2D pos={[-3.6, 0, 9.6]} ropa={LEO} expr="shock" f={c.f} seed={2} /></group>,
  },
  // Y en su cama dormía su hermano, que no le hablaba desde hacía 30 años.
  hermano: {
    interior: true,
    camaras: [camsCuarto.abierto, camsCuarto.cama],
    render: (c) => (
      <Cuarto pared="#adb5bd">
        <Carta2D pos={CAMA} ropa={EXTRAS_2D.hermano} expr="sleep" modo="sit" f={c.f} seed={50} />
        <Cobija />
        <Carta2D pos={[0.2, 0, -0.8]} ropa={BRUNO_2D} expr="sad" f={c.f} seed={7} />
        <Monton n={14} col={['#8d99ae', '#c08552', '#e9c46a']} s={0.18} y={0.15} seed={21} />
      </Cuarto>
    ),
  },
  // [Leo frente a Dani, en la plaza, con todo el pueblo mirando.]
  plaza: {
    pueblo: true,
    camaras: [cam([0, 2.6, 12.5], [0, 1.1, 5.0], 46, 0), cam([2.2, 1.3, 8.4], [0.6, 1.1, 5.2], 36), cam([-1.6, 1.2, 7.8], [-0.6, 1.0, 5.2], 34, 12)],
    cabezas: {leo: cabeza2D([-0.6, 0, 5.2], 1, true)},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={12} />
        <Carta2D pos={[-0.6, 0, 5.2]} ropa={LEO} expr={c.f > c.W('l23') ? 'sad' : 'nervous'} f={c.f} seed={2} />
        <Carta2D pos={[0.8, 0, 5.0]} ropa={DANI} expr={c.f > c.W('l23', 'ti.') ? 'relief' : 'stern'} f={c.f} seed={9} />
        {[[-3, 3.6, EXTRAS_2D.vecina], [-2, 2.6, EXTRAS_2D.papa], [2.4, 2.8, EXTRAS_2D.mama], [3.4, 3.8, EXTRAS_2D.vecino], [0.2, 2.2, BRUNO_2D]].map(([x, z, r], i) => (
          <Carta2D key={i} pos={[x as number, 0, z as number]} ropa={r as typeof LEO} expr="neutral" f={c.f} seed={60 + i} />
        ))}
      </group>
    ),
  },
  // [POP. Brillo. Dani sonríe.] …Dani estaba en la puerta, con un balón.
  puerta: {
    interior: true,
    camaras: [cam(enC([0.4, 1.8, 3.6]), enC([-0.2, 1.0, -0.8]), 52, 0), cam(enC([1.0, 1.2, 1.6]), enC([2.8, 1.1, 0.8]), 34, 12)],
    render: (c) => (
      <Cama2D c={c} quien={LEO} expr={c.u > 0.4 ? 'grin' : 'shock'}>
        {c.u > 0.4 && <><Carta2D pos={[2.8, 0, 0.8]} ropa={DANI} expr="grin" f={c.f} seed={9} saluda /><mesh position={[2.4, 0.2, 1.2]} castShadow><icosahedronGeometry args={[0.2, 1]} /><meshLambertMaterial color="#ffffff" /></mesh></>}
      </Cama2D>
    ),
  },
  // [Don Bruno, viéndolo todo, va a su casa y abraza a su hermano.]
  perdon: {
    pueblo: true,
    camaras: [cam([-4.4, 1.6, 7.6], [-6.0, 1.2, 11.0], 40), cam([-5.4, 1.4, 8.8], [-6.2, 1.5, 11.0], 32, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={17.5} />
        <MontonCasa k={1} f={c.f} />
        <Carta2D pos={[-6.5, 0, 11.0]} ropa={BRUNO_2D} expr={c.u > 0.6 ? 'relief' : 'sad'} f={c.f} seed={7} />
        <Carta2D pos={[-5.6, 0, 11.1]} ropa={EXTRAS_2D.hermano} expr={c.u > 0.6 ? 'relief' : 'stern'} f={c.f} seed={50} />
      </group>
    ),
  },
  // Y su casa se vació en un segundo.
  vacia: {
    pueblo: true,
    camaras: [cam([-3.0, 2.6, 4.2], [-6.0, 2.4, 13.0], 46, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={17.8} />
        <MontonCasa k={1 - c.desde('l26', 'vació', 20)} f={c.f} />
        <Carta2D pos={[-6.5, 0, 11.0]} ropa={BRUNO_2D} expr="grin" f={c.f} seed={7} />
        <Carta2D pos={[-5.6, 0, 11.1]} ropa={EXTRAS_2D.hermano} expr="grin" f={c.f} seed={50} />
      </group>
    ),
  },
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.0, 13.5], [0, 1.2, 6.8], 46, 0), cam([3.0, 1.8, 12.5], [0, 1.1, 6.8], 42, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Carta2D pos={[1.4, 0, 6.6]} ropa={BRUNO_2D} expr="grin" f={c.f} saluda seed={7} />
        <Carta2D pos={[-0.4, 0, 7.1]} ropa={LEO} expr="grin" f={c.f + 9} saluda seed={2} />
        <Carta2D pos={[0.5, 0, 7.4]} ropa={DANI} expr="grin" f={c.f + 4} saluda seed={9} />
        <Carta2D pos={[2.6, 0, 6.2]} ropa={EXTRAS_2D.hermano} expr="smile" f={c.f + 12} saluda seed={50} />
      </group>
    ),
  },
};
