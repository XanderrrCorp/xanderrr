// Episodio 2 — «A LAS 3:33 TODOS DEBEN ESTAR DORMIDOS!» (personajes 2D de la skill). Guion del dueño tal cual.
import React from 'react';
import type {Escena, V3, Cam} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Armario, Camion, CajaCarton, Caja, Aula, AULA, RelojMesa, Casa} from '../Pueblo';
import {Carta2D, CartaLibre, cabeza2D} from '../Carta2D';
import {BRUNO_2D, NINOS_2D, EXTRAS_2D} from '../personajes2d';
import {Osito} from '../Juguetes';
import {dibujaCriatura} from './criatura';
import {lerp, clamp} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p), enA = (p: V3) => add(AULA, p);
const cam = (pos: V3, look: V3, fov = 42, dof?: number): Cam => ({pos, look, fov, dof});
const MIA = NINOS_2D.mia, NINO = 0.62;
const H = 3.55; // 3:33 en la torre
// Mía sentada en su cama con la cobija hasta la cintura (la cobija tapa las piernas de la tarjeta)
const CAMA_MIA: V3 = [-2.2, 0.58, -2.2];
const Cobija: React.FC<{alto?: number}> = ({alto = 0.55}) => <Caja p={[-2.2, 0.6, -1.55]} s={[1.5, alto, 0.25]} c="#4ea8de" />;
const Criatura: React.FC<{p: V3; f: number; bufanda?: boolean; ojos?: 'abiertos' | 'mira' | 'cerrados'; brazos?: number; agacha?: number; esc?: number}> = ({p, f, bufanda = true, ojos = 'abiertos', brazos = 0, agacha = 0, esc = 1.55}) => {
  const o = {bufanda, ojos, brazos: Math.round(brazos * 8) / 8, agacha: Math.round(agacha * 8) / 8};
  return <CartaLibre pos={[p[0], p[1] + Math.sin(f / 20) * 0.02, p[2]]} clave={'criatura' + JSON.stringify(o)} draw={(pen) => dibujaCriatura(pen, o)} escala={esc} />;
};
const camsCuarto = {
  abierto: cam(enC([0.4, 2.4, 4.4]), enC([-0.8, 1.2, -1.8]), 50, 0),
  cama: cam(enC([-1.0, 1.4, 0.4]), enC([-2.2, 1.1, -2.2]), 40),
  cara: cam(enC([-1.75, 1.6, -0.3]), enC([-2.2, 1.45, -2.2]), 34, 13),
  puerta: cam(enC([-2.0, 1.4, -0.6]), enC([2.6, 1.6, 1.8]), 46),
};
// la puerta del cuarto (pared derecha, cerca del frente)
const Puerta: React.FC<{abre: number}> = ({abre}) => (
  <group position={[3.9, 0, 1.6]}>
    <Caja p={[0, 1.15, 0]} s={[0.12, 2.3, 1.2]} c="#1a2244" sombra={false} />
    <group position={[-0.02, 0, -0.6]} rotation={[0, -abre * 1.3, 0]}><Caja p={[0, 1.15, 0.6]} s={[0.08, 2.3, 1.2]} c="#a0522d" /></group>
  </group>
);

export const ESCENAS: Record<string, Escena> = {
  // [Torre del reloj de noche, marcando 3:33. Campanada.]
  reloj: {
    noche: true, pueblo: true,
    camaras: [cam([0, 4.5, 2], [0, 7.4, -12.5], 40, 0), cam([2.5, 7.0, -7.5], [0, 7.4, -11.5], 32, 0)],
    render: (c) => <Pueblo f={c.f} noche hora={H} />,
  },
  // Porque a esa hora algo pasa casa por casa, abriendo las puertas…
  casas: {
    noche: true, pueblo: true,
    camaras: [cam([-1, 2.2, 6], [-12, 2.4, 9], 44, 0), cam([-9, 1.6, 4], [-15, 2.6, 10], 40)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Criatura p={[lerp(-8, -15, c.u), 0, lerp(8.5, 10.5, c.u)]} f={c.f} agacha={0.2} />
      </group>
    ),
  },
  // Por eso aquí la gente se acuesta a las 8.
  acuesta: {
    pueblo: true,
    camaras: [cam([4, 3, 9], [8, 4.5, -2], 44, 0), cam([-2, 9, -4], [0, 7.4, -12.5], 38, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={8} />
        <Carta2D pos={[7.5, 0, 2]} ropa={EXTRAS_2D.vecino} expr="sleep" f={c.f} caminar seed={3} />
        <Carta2D pos={[9, 0, 1]} ropa={EXTRAS_2D.vecina} expr="sleep" f={c.f + 7} caminar seed={4} />
      </group>
    ),
  },
  // Los guardias de noche duermen parados, como caballos.
  guardias: {
    noche: true, pueblo: true,
    camaras: [cam([-6.5, 1.8, 3.6], [-9.6, 1.3, -3.4], 40), cam([-8.5, 1.2, -0.6], [-9.6, 1.6, -3.4], 32)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        {[-10.6, -8.6].map((x, i) => <Carta2D key={x} pos={[x, 0, -3.2 + i * 0.4]} ropa={{jacket: '#1d3557', pants: '#22223b', boots: '#241726', hat: 'shako', belt: '#f1efe6', buttons: '#e8c45a'}} expr="sleep" f={c.f} seed={11 + i} inclina={Math.sin(c.f / 18 + i) * 3} />)}
      </group>
    ),
  },
  // El panadero amasa sonámbulo.
  panadero: {
    noche: true, pueblo: true,
    camaras: [cam([7.0, 1.5, 0.6], [8.6, 1.2, -3.0], 38), cam([5.6, 2.2, 1.6], [8.6, 1.3, -3.0], 46)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Caja p={[8.6, 0.45, -2.7]} s={[1.6, 0.9, 0.8]} c="#c1793f" />
        <mesh position={[8.6 + Math.sin(c.f * 0.3) * 0.1, 0.98, -2.7]} scale={[0.35, 0.12 + 0.03 * Math.sin(c.f * 0.6), 0.25]} castShadow><sphereGeometry args={[1, 16, 10]} /><meshLambertMaterial color="#f5deb3" /></mesh>
        <Carta2D pos={[8.6, 0, -3.4]} ropa={EXTRAS_2D.panadero} expr="sleep" f={c.f} seed={5} inclina={Math.sin(c.f * 0.3) * 4} />
      </group>
    ),
  },
  // Y los bebés no lloran, porque ya aprendieron.
  bebes: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.4, 1.2, 0.6]), enC([-0.8, 0.7, -1.4]), 36), camsCuarto.abierto],
    render: (c) => (
      <Cuarto noche vacio pared="#fde2e4">
        <Caja p={[-0.8, 0.35, -1.6]} s={[1.0, 0.3, 0.6]} c="#f4a261" />
        {[-1.25, -0.35].map((x) => <Caja key={x} p={[x, 0.55, -1.6]} s={[0.06, 0.7, 0.6]} c="#e76f51" />)}
        <Carta2D pos={[-0.8, 0.45, -1.62]} ropa={{...NINOS_2D.nino, hat: 'hair', hair: '#e0c08a'}} expr="nervous" escala={0.32} f={c.f} seed={9} />
        <Caja p={[-0.8, 0.52, -1.35]} s={[0.95, 0.12, 0.08]} c="#ffffff" />
      </Cuarto>
    ),
  },
  // [Huellas enormes en el pasto al amanecer.] …y las cobijas… bien estiraditas.
  huellas: {
    pueblo: true,
    camaras: [cam([4, 3.6, 11], [6, 0, 5], 42, 0), cam([5.4, 1.2, 7.8], [6.2, 0.2, 5.5], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={6.5} />
        {Array.from({length: 7}, (_, i) => (
          <mesh key={i} position={[4 + i * 0.9, 0.03, 8.5 - i * 0.9 + (i % 2) * 0.5]} rotation={[-Math.PI / 2, 0, 0.8]} scale={[0.35, 0.75, 1]}>
            <circleGeometry args={[1, 20]} /><meshLambertMaterial color="#2f6b2f" />
          </mesh>
        ))}
      </group>
    ),
  },
  // [Camión de mudanza]
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46, 0), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (<group><Pueblo f={c.f} hora={8.1} /><Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} /></group>),
  },
  // Yo me llamo Mía, y siempre me cuesta dormir.
  mia: {
    pueblo: true,
    camaras: [cam([0.6, 1.6, 7.2], [2.4, 1.0, 11.4], 42), cam([1.8, 1.1, 9.0], [2.2, 1.0, 11.0], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.4} />
        <Camion p={[3.6, 0, 13.6]} rotY={Math.PI} f={c.f} />
        <Carta2D pos={[2.2, 0, 11]} ropa={MIA} expr={c.u < 0.5 ? 'smile' : 'nervous'} f={c.f} escala={NINO / 0.62} saluda={c.u < 0.45} seed={2} />
        <CajaCarton p={[1.2, 0, 11.6]} /><CajaCarton p={[0.6, 0, 12.1]} s={0.8} r={0.4} />
      </group>
    ),
  },
  // [Cuarto de noche. Mía con los ojos muy abiertos y el reloj marcando 3:30.]
  cuarto330: {
    noche: true, interior: true,
    camaras: [camsCuarto.cama, cam(enC([-0.2, 1.05, -2.0]), enC([-0.65, 0.82, -2.85]), 30, 14), camsCuarto.cara],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={CAMA_MIA} ropa={MIA} expr="shock" modo="sit" f={c.f} seed={2} />
        <Cobija />
        <RelojMesa p={[-0.68, 0.7, -2.82]} hora="3:30" />
        <Puerta abre={0} />
      </Cuarto>
    ),
  },
  // [3:33. Campanada. La puerta cruje.]
  puerta: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.2, 1.05, -2.0]), enC([-0.65, 0.82, -2.85]), 30, 14), camsCuarto.puerta],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={CAMA_MIA} ropa={MIA} expr="shock" modo="sit" f={c.f} seed={2} />
        <Cobija />
        <RelojMesa p={[-0.68, 0.7, -2.82]} hora="3:33" />
        <Puerta abre={c.desde('l11', 'abrió', 30)} />
      </Cuarto>
    ),
  },
  // [Silueta altísima en la puerta, con brazos largos.]
  silueta: {
    noche: true, interior: true,
    camaras: [camsCuarto.puerta, cam(enC([0.6, 0.6, -0.4]), enC([3.2, 2.2, 1.6]), 44)],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={CAMA_MIA} ropa={MIA} expr="fear" modo="sit" f={c.f} seed={2} />
        <Cobija />
        <Puerta abre={1} />
        <Criatura p={enC([3.0, 0, 1.6]).map((v, i) => (i === 0 ? v - 200 : v)) as V3} f={c.f} agacha={c.u < 0.5 ? 0.6 : 0} esc={1.45} />
      </Cuarto>
    ),
  },
  // Cerré los ojos y me hice la dormida.
  dormida: {
    noche: true, interior: true,
    camaras: [camsCuarto.cara, camsCuarto.cama],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={CAMA_MIA} ropa={MIA} expr="sleep" modo="sit" f={c.f} seed={2} />
        <Cobija />
        <Criatura p={[1.2, 0, 0.2]} f={c.f} agacha={0.4} esc={1.45} />
      </Cuarto>
    ),
  },
  // [Primer plano de la cara de Mía, temblando.]
  temblando: {
    noche: true, interior: true,
    camaras: [cam(enC([-2.05, 1.3, -1.3]), enC([-2.2, 1.25, -2.2]), 28, 14), cam(enC([-0.4, 1.3, -0.2]), enC([-1.6, 1.0, -1.6]), 40)],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={[CAMA_MIA[0] + Math.sin(c.f * 1.7) * 0.01, CAMA_MIA[1], CAMA_MIA[2]]} ropa={MIA} expr="cry" modo="sit" f={c.f} seed={2} />
        <Cobija />
        <Criatura p={[-0.75, 0, -1.75]} f={c.f} agacha={1} brazos={c.desde('l14', 'pies.', 10)} esc={1.45} />
      </Cuarto>
    ),
  },
  // [Corte: la criatura le acomoda la cobija y le arropa los pies.]
  tapa: {
    noche: true, interior: true,
    camaras: [camsCuarto.cama, camsCuarto.abierto],
    render: (c) => (
      <Cuarto noche pared="#cdb4db">
        <Carta2D pos={CAMA_MIA} ropa={MIA} expr="sleep" modo="sit" f={c.f} seed={2} />
        <Cobija alto={lerp(0.55, 0.75, c.desde('l15', 'tapó', 12))} />
        <Criatura p={[-0.75, 0, -1.75]} f={c.f} agacha={1} brazos={0.5} esc={1.45} />
      </Cuarto>
    ),
  },
  // [La criatura sale. Mía abre un ojo.] La noche siguiente lo seguí.
  sigue: {
    noche: true, pueblo: true,
    camaras: [cam([3, 1.3, 9], [6, 1.4, 13], 42), cam([1.5, 2.4, 5.5], [6.5, 1.5, 12.5], 46, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Criatura p={[lerp(6.5, 9.5, c.u), 0, 11.6]} f={c.f} />
        <Carta2D pos={[lerp(4.2, 6.0, c.u), 0, 10.2]} ropa={MIA} expr="fear" f={c.f} caminar seed={2} />
      </group>
    ),
  },
  // [Mía espía por las ventanas. La criatura arropa a un niño, levanta un peluche del piso.]
  ventanas: {
    noche: true, interior: true,
    camaras: [camsCuarto.abierto, cam(enC([-0.5, 1.2, 0.6]), enC([-1.6, 0.9, -1.8]), 40)],
    render: (c) => {
      const k = Math.floor(c.u * 3);
      return (
        <Cuarto noche pared={['#a9def9', '#e9edc9', '#ffc8dd'][k]}>
          <Carta2D pos={CAMA_MIA} ropa={[NINOS_2D.nino, NINOS_2D.dani, NINOS_2D.ana][k]} expr="sleep" modo="sit" f={c.f} seed={20 + k} />
          <Cobija alto={0.7} />
          {k === 1 && <Osito p={[-1.4, 0.73, -1.6]} ojos={0} />}
          <Criatura p={[-0.6, 0, -0.7]} f={c.f} agacha={0.8} brazos={k === 2 ? 0.8 : 0.4} esc={1.45} />
        </Cuarto>
      );
    },
  },
  // [La criatura llega a una casa oscura. Un niño duerme solo, sin cobija.]
  ultima: {
    noche: true, interior: true,
    camaras: [camsCuarto.abierto, camsCuarto.cama],
    render: (c) => (
      <Cuarto noche pared="#adb5bd" luzLampara={false}>
        <Carta2D pos={CAMA_MIA} ropa={NINOS_2D.leo} expr="sad" modo="sit" f={c.f} seed={30} />
        <Criatura p={[0.4, 0, -0.4]} f={c.f} agacha={0.5} esc={1.45} />
      </Cuarto>
    ),
  },
  // La criatura se quitó su propia bufanda y se la puso encima.
  bufanda: {
    noche: true, interior: true,
    camaras: [camsCuarto.cama, cam(enC([-1.4, 1.2, -0.6]), enC([-2.2, 0.95, -1.9]), 34, 13)],
    render: (c) => {
      const puesta = c.f > c.W('l19', 'encima.') - 2;
      return (
        <Cuarto noche pared="#adb5bd" luzLampara={false}>
          <Carta2D pos={CAMA_MIA} ropa={NINOS_2D.leo} expr={puesta ? 'sleep' : 'sad'} modo="sit" f={c.f} seed={30} />
          {puesta && <Caja p={[-2.2, 0.75, -1.85]} s={[1.3, 0.12, 0.9]} c="#e63946" />}
          <Criatura p={[-0.75, 0, -1.75]} f={c.f} agacha={1} brazos={puesta ? 0.3 : 0.7} bufanda={!puesta} esc={1.45} />
        </Cuarto>
      );
    },
  },
  // [La criatura ve a Mía. Silencio.]
  mevio: {
    noche: true, pueblo: true,
    camaras: [cam([4.8, 1.6, 9.2], [6.8, 2.6, 12.2], 34, 12), cam([7.2, 1.0, 11.0], [5.0, 0.9, 9.6], 34, 12)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Criatura p={[6.8, 0, 12.4]} f={c.f} ojos="mira" bufanda={false} />
        <Carta2D pos={[5.0, 0, 9.6]} ropa={MIA} expr="fear" f={c.f} seed={2} />
      </group>
    ),
  },
  // —¿Por qué nadie puede verte? / —Porque si me ven… dejo de existir.
  dialogo: {
    noche: true, pueblo: true,
    camaras: [cam([3.2, 1.8, 7.2], [6.0, 1.8, 11.0], 44), cam([5.4, 1.4, 8.2], [6.6, 2.4, 12.2], 36)],
    cabezas: {mia: cabeza2D([5.0, 0, 9.6], 1, true), criatura: [6.8, 3.2, 12.4]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Criatura p={[6.8, 0, 12.4]} f={c.f} ojos={c.f > c.W('l22') ? 'abiertos' : 'mira'} bufanda={false} agacha={0.3} />
        <Carta2D pos={[5.0, 0, 9.6]} ropa={MIA} expr={c.f > c.W('l22') ? 'sad' : 'nervous'} f={c.f} seed={2} />
      </group>
    ),
  },
  // [Ruido: Don Bruno con una linterna y una red.]
  bruno: {
    noche: true, pueblo: true,
    camaras: [cam([1.5, 1.8, 6.5], [3.0, 1.4, 10.5], 44), cam([2.4, 1.6, 9.0], [2.8, 1.8, 11.4], 34, 12)],
    cabezas: {bruno: cabeza2D([2.8, 0, 11.4])},
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={H} />
        <Carta2D pos={[2.8, 0, 11.4]} ropa={BRUNO_2D} expr={c.f > c.W('l24') ? 'grin' : 'stern'} f={c.f} seed={7} />
        {/* linterna con su haz y la red */}
        <group position={[3.45, 1.15, 11.5]} rotation={[0, 0, -0.5]}>
          <mesh castShadow><cylinderGeometry args={[0.06, 0.08, 0.35, 12]} /><meshLambertMaterial color="#555" /></mesh>
          <mesh position={[0, 0.75, 0]}><coneGeometry args={[0.35, 1.2, 20, 1, true]} /><meshBasicMaterial color="#fff3b0" transparent opacity={0.22} depthWrite={false} /></mesh>
        </group>
        <group position={[2.0, 1.3, 11.5]} rotation={[0, 0, 0.4]}>
          <mesh><cylinderGeometry args={[0.025, 0.025, 1.4, 8]} /><meshLambertMaterial color="#8b5e34" /></mesh>
          <mesh position={[0, 0.85, 0]} rotation={[Math.PI / 2, 0, 0]}><torusGeometry args={[0.3, 0.03, 8, 20]} /><meshLambertMaterial color="#8b5e34" /></mesh>
        </group>
        <Criatura p={[6.8, 0, 12.4]} f={c.f} bufanda={false} ojos="abiertos" />
        <Carta2D pos={[5.0, 0, 9.6]} ropa={MIA} expr="shock" f={c.f} seed={2} />
      </group>
    ),
  },
  // [Mía apaga la linterna de un manotazo.] Le apagué la linterna. Nadie lo vio. Se fue.
  apaga: {
    noche: true, pueblo: true,
    camaras: [cam([1.5, 1.8, 6.5], [3.6, 1.4, 10.8], 44), cam([4.0, 1.6, 8.0], [7.5, 2.0, 13.0], 40)],
    render: (c) => {
      const off = c.f > c.W('l25', 'apagué');
      const se = c.desde('l25', 'fue.', 30);
      return (
        <group>
          <Pueblo f={c.f} noche hora={H} />
          <Carta2D pos={[2.8, 0, 11.4]} ropa={BRUNO_2D} expr={off ? 'shock' : 'grin'} f={c.f} seed={7} />
          {!off && <mesh position={[3.45, 2.1, 11.5]}><coneGeometry args={[0.35, 1.2, 20, 1, true]} /><meshBasicMaterial color="#fff3b0" transparent opacity={0.22} depthWrite={false} /></mesh>}
          <Carta2D pos={[3.6, 0, 10.9]} ropa={MIA} expr={off ? 'grin' : 'stern'} f={c.f} seed={2} />
          {se < 1 && <Criatura p={[6.8 + se * 6, 0, 12.4 + se * 4]} f={c.f} bufanda={false} />}
        </group>
      );
    },
  },
  // [Día. Mía dormida en clase, sonriendo.]
  clase: {
    interior: true,
    camaras: [cam(enA([1.8, 1.6, 4.2]), enA([0, 0.9, 1.4]), 44), cam(enA([0.6, 1.15, 2.7]), enA([0, 1.0, 1.4]), 32, 12)],
    render: (c) => (
      <Aula>
        <Carta2D pos={[0, 0, 1.75]} ropa={MIA} expr="sleep" modo="sit" f={c.f} seed={2} />
        <Carta2D pos={[-2.2, 0, 1.75]} ropa={NINOS_2D.dani} expr="smile" modo="sit" f={c.f} seed={21} />
        <Carta2D pos={[2.2, 0, 1.75]} ropa={NINOS_2D.leo} expr="neutral" modo="sit" f={c.f} seed={22} />
      </Aula>
    ),
  },
  // [CTA] la plaza, todos saludan
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.0, 13.5], [0, 1.2, 6.8], 46, 0), cam([3.0, 1.8, 12.5], [0, 1.1, 6.8], 42, 0)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Carta2D pos={[1.4, 0, 6.6]} ropa={BRUNO_2D} expr="grin" f={c.f} saluda seed={7} />
        <Carta2D pos={[-0.4, 0, 7.1]} ropa={MIA} expr="grin" f={c.f + 9} saluda seed={2} />
        <Carta2D pos={[-2.2, 0, 6.3]} ropa={NINOS_2D.leo} expr="smile" f={c.f + 4} saluda seed={30} />
        <Criatura p={[3.6, 0, 5.4]} f={c.f} brazos={0.6} esc={1.3} />
      </group>
    ),
  },
};
export const _casa = Casa; export const _arm = Armario;
