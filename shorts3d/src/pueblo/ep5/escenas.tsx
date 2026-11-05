// Episodio 5 — «SI UN NIÑO LLORA, LOS JUGUETES DESPIERTAN…». Una escena por cada [toma] del guion. Las cámaras
// son FIJAS: cada escena trae 2–3 encuadres (abierto / medio / reacción) que el montaje va turnando.
import React from 'react';
import type {Escena, V3, Cam, Ctx} from '../tipos';
import {Pueblo, Cuarto, CUARTO, Armario, Basurero, BASURERO, Oficina, OFICINA, Camion, CajaCarton, Caja, Casa} from '../Pueblo';
import {Personaje} from '../Personaje';
import {DON_BRUNO, NINOS, EXTRAS} from '../personajes';
import {Osito, Dino, Muneca, Soldadito, Conejo} from '../Juguetes';
import {lerp, clamp} from '../../anim';

const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const enC = (p: V3) => add(CUARTO, p), enB = (p: V3) => add(BASURERO, p), enO = (p: V3) => add(OFICINA, p);
const cam = (pos: V3, look: V3, fov = 42): Cam => ({pos, look, fov});
const NINO = 0.72, MAX = NINOS.max;
// lugares fijos del cuarto (relativos)
const CAMA_SENTADO: V3 = [-2.2, 0.72, -2.3];
const ARMARIO: V3 = [3.05, 0, -2.9];
const camsCuarto = {
  abierto: cam(enC([0.4, 2.4, 4.4]), enC([-0.4, 1.0, -1.8]), 50),
  cama: cam(enC([-0.9, 1.35, 0.3]), enC([-2.2, 1.0, -2.3]), 42),
  armario: cam(enC([0.9, 1.4, 0.9]), enC([2.9, 1.2, -2.6]), 44),
};

export const ESCENAS: Record<string, Escena> = {
  // [Cuarto de noche. Un niño llora y su osito de peluche abre los ojos.]
  llora: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.2, 1.7, 1.6]), enC([-1.9, 0.9, -2.0]), 44), cam(enC([-0.3, 1.0, 0.0]), enC([-1.3, 0.85, -1.7]), 40), camsCuarto.cama],
    render: (c) => (
      <Cuarto noche pared="#a9def9">
        <Personaje pos={[CAMA_SENTADO[0] - 200 + 200, CAMA_SENTADO[1], CAMA_SENTADO[2]]} escala={NINO} ropa={{...EXTRAS.nino, pijama: true, camisa: '#90e0ef'}} cara="llora" pose="sentado" f={c.f} />
        <Osito p={[-1.3, 0.73, -1.7]} rotY={-0.5} ojos={c.desde('l01', 'despiertan.', 5)} s={1.1} />
        <Armario p={ARMARIO} f={c.f} />
      </Cuarto>
    ),
  },
  // Los dinosaurios patrullan debajo de la cama.
  dinos: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.4, 0.7, 1.6]), enC([-2.0, 0.35, -1.0]), 44), cam(enC([-3.2, 0.9, 1.6]), enC([-2.0, 0.3, -0.6]), 46)],
    render: (c) => (
      <Cuarto noche pared="#a9def9">
        <Personaje pos={[-2.2, 0.75, -2.14]} escala={NINO} ropa={{...EXTRAS.nino, pijama: true, camisa: '#90e0ef'}} cara="dormido" pose="acostado" f={c.f} />
        {[0, 1, 2].map((k) => {
          const x = -3.2 + ((c.f * 0.025 + k * 0.55) % 1.7);
          return <Dino key={k} p={[x, 0, -0.4 - k * 0.05]} rotY={Math.PI / 2} f={c.f + k * 7} color={['#52b788', '#f4a261', '#4895ef'][k]} />;
        })}
      </Cuarto>
    ),
  },
  // Las muñecas cierran el armario con cinta.
  munecas: {
    noche: true, interior: true,
    camaras: [camsCuarto.armario, cam(enC([2.4, 0.7, -0.6]), enC([3.0, 0.8, -2.4]), 40)],
    render: (c) => (
      <Cuarto noche pared="#a9def9">
        <Armario p={ARMARIO} f={c.f} cinta={c.f > c.W('l03', 'cinta.')} />
        {[-0.55, 0, 0.55].map((x, k) => <Muneca key={k} p={[3.05 + x, 0, -2.25]} rotY={Math.PI} brazos={0.6 + 0.4 * Math.sin(c.f * 0.4 + k)} vestido={['#ff70a6', '#9b5de5', '#f15bb5'][k]} />)}
      </Cuarto>
    ),
  },
  // Los soldaditos hacen guardia en la ventana.
  soldaditos: {
    noche: true, interior: true,
    camaras: [cam(enC([1.3, 1.45, -1.6]), enC([1.6, 1.25, -3.25]), 40), cam(enC([0.2, 1.8, -0.5]), enC([1.6, 1.3, -3.2]), 46)],
    render: () => (
      <Cuarto noche pared="#a9def9">
        {[0.9, 1.3, 1.7, 2.1].map((x) => <Soldadito key={x} p={[x, 1.14, -3.18]} />)}
      </Cuarto>
    ),
  },
  // Por eso aquí los papás lloran a escondidas… (de noche, en la plaza, bajo los faroles)
  papas: {
    noche: true, pueblo: true,
    camaras: [cam([1.5, 2.0, 6.5], [5.2, 1.0, 0.6], 44), cam([3.2, 1.3, 2.6], [5.4, 1.0, 0.2], 40)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} noche hora={23.5} />
        <Personaje pos={[5.3, 0, 0.1]} ropa={EXTRAS.papa} cara="llora" pose="sentado" f={c.f} rotY={-Math.PI / 2} />
        <Personaje pos={[4.6, 0, -2.4]} ropa={EXTRAS.mama} cara="llora" pose="llora" f={c.f} rotY={-0.4} />
      </group>
    ),
  },
  // [Camión de mudanza]
  mudanza: {
    pueblo: true,
    camaras: [cam([-6, 2.4, 3], [2.5, 1.2, 16], 46), cam([7.5, 1.6, 6], [3, 1.4, 14], 40)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.1} />
        <Camion p={[3, 0, lerp(26, 13, clamp(c.u * 1.6))]} rotY={Math.PI} f={c.f} avanza={c.u < 0.62 ? 1 : 0} />
      </group>
    ),
  },
  // Me llamo Max. En la mudanza perdí todos mis juguetes.
  max: {
    pueblo: true,
    camaras: [cam([0.6, 1.7, 6.6], [2.4, 1.2, 11.5], 44), cam([1.7, 1.15, 8.6], [2.2, 1.0, 11.0], 34)],
    cabezas: {max: [2.2, 1.4, 11]},
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={8.3} />
        <Camion p={[3.6, 0, 13.6]} rotY={Math.PI} f={c.f} />
        <Personaje pos={[2.2, 0, 11]} escala={NINO} ropa={MAX} cara={c.f < c.W('l07', 'perdí') ? 'feliz' : 'triste'} pose={c.f < c.W('l07', 'perdí') ? 'saluda' : 'quieto'} f={c.f} rotY={Math.PI - 0.25} />
        <CajaCarton p={[1.2, 0, 11.6]} /><CajaCarton p={[0.6, 0, 12.1]} s={0.8} r={0.4} /><CajaCarton p={[1.2, 0.6, 11.6]} s={0.7} r={0.2} />
      </group>
    ),
  },
  // [Cuarto vacío de Max. Solo una caja.] Mi cuarto estaba vacío. Y la primera noche, lloré.
  vacio: {
    noche: true, interior: true,
    camaras: [camsCuarto.abierto, cam(enC([-0.3, 1.05, 1.5]), enC([0.0, 0.55, -0.7]), 40), cam(enC([2.2, 1.6, 2.2]), enC([0.0, 0.6, -0.8]), 46)],
    render: (c) => (
      <Cuarto noche vacio pared="#e9edc9">
        <Personaje pos={[0, 0.0, -0.7]} escala={NINO} ropa={{...MAX, sombrero: undefined, pelo: MAX.pelo}} cara={c.f > c.W('l08', 'lloré.') - 4 ? 'llora' : 'triste'} pose="sentado" f={c.f} rotY={0.2} />
        <CajaCarton p={[-1.2, 0, -1.4]} />
        <Armario p={ARMARIO} f={c.f} />
      </Cuarto>
    ),
  },
  // Y en el armario, algo se movió.
  armario: {
    noche: true, interior: true,
    camaras: [camsCuarto.armario, cam(enC([-0.4, 1.0, 0.6]), enC([2.6, 1.3, -2.6]), 40)],
    render: (c) => (
      <Cuarto noche vacio pared="#e9edc9">
        <Personaje pos={[0, 0.0, -0.7]} escala={NINO} ropa={{...MAX, sombrero: undefined}} cara="miedo" pose="sentado" f={c.f} rotY={0.9} />
        <Armario p={ARMARIO} f={c.f} temblor={c.desde('l10', 'movió.', 4)} ojos={c.desde('l10', 'movió.', 6)} abierto={0.3 * c.desde('l10', 'movió.', 6)} />
      </Cuarto>
    ),
  },
  // [PROPUESTA] Las pelotas ruedan solas hasta la puerta…
  pelotas: {
    noche: true, interior: true,
    camaras: [cam(enC([0.6, 0.6, 2.4]), enC([-0.6, 0.3, 0.6]), 46), cam(enC([-3.0, 0.5, 2.6]), enC([-1.0, 0.3, 1.6]), 44)],
    render: (c) => (
      <Cuarto noche pared="#a9def9">
        {[0, 1, 2].map((k) => {
          const t = clamp(c.u * 1.3 - k * 0.15);
          return <mesh key={k} position={enC([lerp(-1.6 + k * 0.4, 1.2 + k * 0.3, t), 0.18, lerp(-1.2, 2.6, t)]).map((v, q) => (q === 0 ? v - 200 : v)) as V3} rotation={[t * 12, 0, 0]} castShadow>
            <sphereGeometry args={[0.18, 16, 12]} /><meshStandardMaterial color={['#ef476f', '#ffd166', '#06d6a0'][k]} roughness={0.5} />
          </mesh>;
        })}
      </Cuarto>
    ),
  },
  // [PROPUESTA] Los robots de cuerda revisan que la ventana esté bien cerrada.
  robots: {
    noche: true, interior: true,
    camaras: [cam(enC([1.0, 1.6, -1.0]), enC([1.6, 1.3, -3.2]), 44), cam(enC([2.8, 1.5, -1.4]), enC([1.6, 1.25, -3.2]), 42)],
    render: (c) => (
      <Cuarto noche pared="#a9def9">
        {[1.1, 2.0].map((x, k) => (
          <group key={x} position={[x + Math.sin(c.f * 0.15 + k) * 0.15, 1.14, -3.15]} rotation={[0, Math.sin(c.f * 0.1 + k) * 0.6, 0]}>
            <Caja p={[0, 0.12, 0]} s={[0.2, 0.2, 0.16]} c="#adb5bd" />
            <Caja p={[0, 0.3, 0]} s={[0.16, 0.14, 0.14]} c="#ced4da" />
            {[-1, 1].map((l) => <mesh key={l} position={[l * 0.04, 0.31, 0.075]}><sphereGeometry args={[0.02, 8, 6]} /><meshBasicMaterial color="#ffd60a" /></mesh>)}
            <group position={[0, 0.14, -0.1]} rotation={[0, 0, c.f * 0.3]}><Caja p={[0, 0, 0]} s={[0.16, 0.03, 0.02]} c="#ffd166" /></group>
          </group>
        ))}
      </Cuarto>
    ),
  },
  // [PROPUESTA] Y los peluches más viejos se turnan para no quedarse dormidos.
  turnos: {
    noche: true, interior: true,
    camaras: [cam(enC([-1.0, 1.25, -0.4]), enC([-1.9, 0.85, -2.2]), 38), camsCuarto.cama],
    render: (c) => {
      const turno = Math.floor(c.u * 3) % 2;
      return (
        <Cuarto noche pared="#a9def9">
          <Personaje pos={[-2.2, 0.75, -2.14]} escala={NINO} ropa={{...EXTRAS.nino, pijama: true, camisa: '#90e0ef'}} cara="dormido" pose="acostado" f={c.f} />
          <Osito p={[-1.6, 0.73, -1.3]} rotY={0.3} ojos={turno ? 0 : 1} s={1.1} />
          <Osito p={[-2.8, 0.73, -1.2]} rotY={-0.3} ojos={turno ? 1 : 0} s={1.0} />
        </Cuarto>
      );
    },
  },
  // [PROPUESTA] En la escuela, el que llora en clase sale con un dinosaurio asomado en la mochila.
  mochila: {
    pueblo: true,
    camaras: [cam([-8.2, 1.4, 6.6], [-10.2, 1.0, 5.6], 40), cam([-7.0, 2.2, 3.5], [-10.4, 1.4, 6.2], 46)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={13} />
        <Personaje pos={[lerp(-10.6, -9.6, c.u), 0, 5.4]} escala={NINO} ropa={{...EXTRAS.nino, mochila: '#ff9f1c'}} cara="triste" pose="camina" f={c.f} rotY={Math.PI / 2 + 0.6} />
        <group position={[lerp(-10.6, -9.6, c.u) - 0.12, 0.92 + Math.max(0, Math.sin(c.f * 0.3)) * 0.05, 5.32]} rotation={[0, Math.PI / 2 + 0.6 + Math.PI, 0]} scale={0.8}><Dino p={[0, 0, 0]} f={c.f} rotY={0} color="#52b788" /></group>
      </group>
    ),
  },
  // [PROPUESTA] Esa noche no dormí. El armario rascaba la puerta…
  rasca: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.2, 1.0, 0.9]), enC([0.0, 0.6, -0.8]), 38), camsCuarto.armario],
    render: (c) => (
      <Cuarto noche vacio pared="#e9edc9">
        <Personaje pos={[0, 0.0, -0.7]} escala={NINO} ropa={{...MAX, sombrero: undefined}} cara="miedo" pose="sentado" f={c.f} rotY={0.6} />
        <Armario p={ARMARIO} f={c.f} temblor={0.5 + 0.5 * Math.abs(Math.sin(c.f * 0.2))} ojos={1} abierto={0.15} />
      </Cuarto>
    ),
  },
  // [Max corre al basurero del pueblo.]
  basurero: {
    camaras: [cam(enB([4, 2.4, 9]), enB([0, 0.8, -2]), 48), cam(enB([-2.5, 1.2, 3.5]), enB([0, 0.9, 0]), 40)],
    render: (c) => (
      <Basurero>
        <Personaje pos={[lerp(-1.5, 0.6, c.u), 0, lerp(4, 0, c.u)]} escala={NINO} ropa={MAX} cara="neutral" pose="camina" f={c.f} rotY={2.8} />
      </Basurero>
    ),
  },
  // [Entre la basura: un conejo de peluche viejo, sin un ojo, con una oreja rota.]
  conejo: {
    camaras: [cam(enB([0.6, 1.0, 1.7]), enB([0.1, 0.6, -0.3]), 38), cam(enB([2.4, 1.6, 3.0]), enB([0.4, 0.7, -0.4]), 44)],
    render: (c) => (
      <Basurero>
        <Caja p={[0, 0.2, -0.5]} s={[1.2, 0.4, 0.9]} c="#adb5bd" />
        <Conejo p={[0, 0.4, -0.3]} sucio rotY={0.2} />
        <Personaje pos={[0.9, 0, 0.3]} escala={NINO} ropa={MAX} cara="sorpresa" pose="agachado" f={c.f} rotY={-2.4} />
      </Basurero>
    ),
  },
  // [Max lo cose con hilo rojo.]
  coser: {
    interior: true,
    camaras: [cam(enC([1.3, 1.2, 1.2]), enC([0.0, 0.5, -0.7]), 40), camsCuarto.abierto],
    render: (c) => (
      <Cuarto vacio pared="#e9edc9">
        <Personaje pos={[0, 0, -1.0]} escala={NINO} ropa={MAX} cara="feliz" pose="cose" f={c.f} />
        <Conejo p={[0.05, 0.02, -0.45]} cosido={c.u > 0.4} rotY={0.5} s={0.9} />
        <CajaCarton p={[-1.2, 0, -1.4]} />
        <Armario p={ARMARIO} f={c.f} />
      </Cuarto>
    ),
  },
  // [Noche. Max llora. El conejo abre su único ojo.]
  ojo: {
    noche: true, interior: true,
    camaras: [cam(enC([-0.3, 1.1, 1.5]), enC([0.1, 0.55, -0.6]), 42), cam(enC([0.9, 0.6, 1.0]), enC([0.45, 0.45, -0.3]), 32)],
    render: (c) => (
      <Cuarto noche vacio pared="#e9edc9">
        <Personaje pos={[-0.2, 0, -0.9]} escala={NINO} ropa={{...MAX, sombrero: undefined}} cara="llora" pose="sentado" f={c.f} />
        <Conejo p={[0.45, 0, -0.3]} cosido ojo={c.desde('l14', 'ojo.', 5)} rotY={-0.3} />
        <Armario p={ARMARIO} f={c.f} temblor={0.6} ojos={0.6} />
      </Cuarto>
    ),
  },
  // [El conejo salta y se pone frente al armario.]
  guardia: {
    noche: true, interior: true,
    camaras: [cam(enC([1.3, 0.8, 0.6]), enC([2.9, 0.7, -2.2]), 42), camsCuarto.abierto],
    render: (c) => {
      const salto = clamp((c.f - c.W('l15', 'paró')) / 14);
      const calma = c.desde('l15', 'calmó.', 10);
      return (
        <Cuarto noche vacio pared="#e9edc9">
          <Personaje pos={[-0.2, 0, -0.9]} escala={NINO} ropa={{...MAX, sombrero: undefined}} cara={calma > 0.5 ? 'feliz' : 'sorpresa'} pose="sentado" f={c.f} />
          <Conejo p={[lerp(0.45, 2.95, salto), Math.sin(salto * Math.PI) * 0.6, lerp(-0.3, -1.9, salto)]} cosido ojo={1} de_pie={salto} rotY={salto > 0.5 ? Math.PI : -0.3} />
          <Armario p={ARMARIO} f={c.f} temblor={1 - calma} ojos={1 - calma} />
        </Cuarto>
      );
    },
  },
  // [Día. Los juguetes del pueblo, reunidos en la fuente, hablando de «el Tuerto».]
  leyenda: {
    pueblo: true,
    camaras: [cam([0.4, 1.35, 4.4], [0, 0.95, 2.0], 40), cam([-2.6, 1.6, 4.6], [-0.2, 0.9, 2.0], 44)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={17.5} />
        <Osito p={[-0.7, 0.7, 2.05]} rotY={0.5 + 0.15 * Math.sin(c.f / 6)} ojos={1} s={1.0} />
        <Muneca p={[0.1, 0.7, 2.1]} rotY={-0.2} brazos={0.5 + 0.5 * Math.sin(c.f / 4)} />
        <Dino p={[0.8, 0.7, 2.0]} rotY={-0.9} f={c.f} color="#f4a261" />
        <Soldadito p={[-0.25, 0.7, 2.15]} rotY={0.2} />
        <Conejo p={[1.5, 0.7, 1.9]} cosido ojo={1} rotY={-1.1} s={0.6} />
      </group>
    ),
  },
  // …había cuidado a cientos de niños… y a uno más que a todos.
  cientos: {
    noche: true, interior: true,
    camaras: [camsCuarto.cama, cam(enC([-0.4, 1.7, 0.6]), enC([-2.2, 0.8, -2.1]), 46)],
    render: (c) => {
      const k = Math.floor(c.u * 4) % 4;
      const ropas = [EXTRAS.nino, NINOS.mia, NINOS.lucas, {...DON_BRUNO, sombrero: undefined, bigote: undefined, pelo: '#4a2c17'}];
      const paredes = ['#cdb4db', '#ffc8dd', '#bde0fe', '#fde2e4'];
      return (
        <Cuarto noche pared={paredes[k]}>
          <Personaje pos={[-2.2, 0.75, -2.14]} escala={NINO} ropa={{...ropas[k], pijama: true}} cara="dormido" pose="acostado" f={c.f} />
          <Conejo p={[-1.3, 0.73, -1.6]} ojo={1} rotY={-0.8} sucio={false} />
        </Cuarto>
      );
    },
  },
  // [Alcaldía. En el escritorio de Don Bruno, una foto de él de niño abrazando al conejo.]
  foto: {
    interior: true,
    camaras: [cam(enO([1.6, 1.7, 1.8]), enO([0.2, 0.9, -1.3]), 44), cam(enO([0.6, 1.15, -0.5]), enO([0.55, 1.08, -1.5]), 32)],
    render: (c) => (
      <Oficina>
        <group position={[0.55, 0.85, -1.5]} rotation={[-0.15, 0, 0]}>
          <Caja p={[0, 0.25, 0]} s={[0.46, 0.56, 0.04]} c="#c9a227" />
          <Caja p={[0, 0.25, 0.022]} s={[0.38, 0.48, 0.01]} c="#f0d9b5" />
          <group position={[0, 0.03, 0.05]} scale={0.16}>
            <Personaje pos={[0, 0, 0]} escala={NINO} ropa={{...DON_BRUNO, sombrero: undefined, bigote: undefined, pelo: '#4a2c17'}} cara="feliz" pose="abraza" f={0} />
            <Conejo p={[0, 0.55, 0.3]} ojo={1} s={1.2} />
          </group>
          <Caja p={[0, 0.0, -0.08]} s={[0.05, 0.3, 0.16]} c="#c9a227" r={[0.5, 0, 0]} />
        </group>
        <Personaje pos={[-1.6, 0, 0.2]} escala={NINO} ropa={MAX} cara="sorpresa" pose="carga" f={c.f} rotY={0.6} />
        <Conejo p={[-1.48, 0.58, 0.44]} cosido ojo={1} s={0.85} rotY={0.6} />
      </Oficina>
    ),
  },
  // —Lo tiré cuando crecí. Me dio vergüenza.
  bruno: {
    interior: true,
    camaras: [cam(enO([0.6, 1.9, 3.2]), enO([-0.4, 1.2, -0.6]), 46), cam(enO([-1.0, 1.55, 1.6]), enO([0.4, 1.7, -0.6]), 36)],
    cabezas: {bruno: enO([0.4, 2.05, -0.6])},
    render: (c) => (
      <Oficina>
        <Personaje pos={[0.4, 0, -0.6]} ropa={DON_BRUNO} cara="triste" pose="quieto" f={c.f} rotY={-0.5} />
        <Personaje pos={[-1.4, 0, 0.6]} escala={NINO} ropa={MAX} cara="neutral" pose="carga" f={c.f} rotY={1.6} />
        <Conejo p={[-1.13, 0.58, 0.64]} cosido ojo={0} s={0.85} rotY={1.6} />
      </Oficina>
    ),
  },
  // [Don Bruno empieza a llorar. El conejo abre su ojo.]
  brunoLlora: {
    interior: true,
    camaras: [cam(enO([0.0, 1.8, 1.8]), enO([0.4, 1.7, -0.6]), 34), cam(enO([-0.6, 1.0, 2.6]), enO([-1.13, 0.75, 0.64]), 32), cam(enO([0.6, 1.9, 3.2]), enO([-0.4, 1.2, -0.6]), 46)],
    render: (c) => (
      <Oficina>
        <Personaje pos={[0.4, 0, -0.6]} ropa={DON_BRUNO} cara="llora" pose={c.f > c.W('l20', 'ojo…') ? 'quieto' : 'llora'} f={c.f} rotY={-0.5} />
        <Personaje pos={[-1.4, 0, 0.6]} escala={NINO} ropa={MAX} cara={c.f > c.W('l20', 'ojo…') ? 'feliz' : 'triste'} pose="carga" f={c.f} rotY={1.6} />
        <Conejo p={[-1.13, 0.58, 0.64]} cosido ojo={c.desde('l20', 'ojo…', 5)} s={0.85} rotY={1.2} />
      </Oficina>
    ),
  },
  // [Ambos abrazan al conejo.] Ahora lo cuidamos los dos…
  abrazo: {
    pueblo: true,
    camaras: [cam([2.4, 1.9, 9.2], [0, 1.4, 4.2], 42), cam([-3.2, 3.2, 12], [0, 1.2, 3], 50), cam([0.9, 1.45, 6.8], [0, 1.2, 4.3], 34)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={c.u < 0.5 ? 9 : 17} />
        <Personaje pos={[0.55, 0, 4.0]} ropa={DON_BRUNO} cara="feliz" pose="abraza" f={c.f} rotY={-0.9} />
        <Personaje pos={[-0.6, 0, 4.6]} escala={NINO} ropa={MAX} cara="feliz" pose="abraza" f={c.f} rotY={0.9} />
        <Conejo p={[-0.05, 0.75, 4.35]} cosido ojo={1} s={0.9} rotY={0} />
      </group>
    ),
  },
  // [CTA] los personajes saludan a cámara en la plaza
  cta: {
    pueblo: true,
    camaras: [cam([0, 2.0, 13.5], [0, 1.2, 6.8], 46), cam([3.0, 1.8, 12.5], [0, 1.1, 6.8], 42)],
    render: (c) => (
      <group>
        <Pueblo f={c.f} hora={10} />
        <Personaje pos={[1.3, 0, 6.6]} ropa={DON_BRUNO} cara="feliz" pose="saluda" f={c.f} />
        <Personaje pos={[-0.4, 0, 7.1]} escala={NINO} ropa={MAX} cara="feliz" pose="saluda" f={c.f + 9} />
        <Conejo p={[0.35, 0, 7.5]} cosido ojo={1} de_pie={1} s={1.2} />
        <Personaje pos={[-2.3, 0, 6.3]} ropa={EXTRAS.abuela} cara="feliz" pose="saluda" f={c.f + 4} rotY={0.3} />
        <Personaje pos={[3.2, 0, 6.2]} ropa={EXTRAS.panadero} cara="feliz" pose="saluda" f={c.f + 13} rotY={-0.3} />
      </group>
    ),
  },
};
export const _ctx: Ctx | null = null;
export const _casa = Casa;
