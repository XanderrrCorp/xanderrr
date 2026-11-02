// MONTAJE: cada frase de la voz se parte en 1 o 2 planos (los que pide el guion) y ningún plano pasa del tope
// de la ficha (2 s): si una frase es larga, el plano se corta en dos con otro encuadre del mismo tipo.
// Cada plano tiene una pose inicial y una final de cámara: la cámara SIEMPRE se mueve (push-in, paneo
// o flotación), no hay ni un cuadro quieto.
import * as THREE from 'three';
import {FRASES, W, ESCENAS, TOTAL, FPS, Toma} from './timing';
import {SPEC} from './spec';
import {estado, L} from './estado';
import {cabezaCosa} from './Personajes';
import {V3, lerp, clamp, E, EaseName, add3, rnd} from '../anim';

type Pose = {pos: V3; look: V3; fov: number};
export type Plano = Toma & {n: number; from: number; to: number; a: Pose; b: Pose; e: EaseName; zoomRapido: boolean; lugar: 'cuarto' | 'fuera'; escena: string; etiqueta?: string};

// 1) cortes: frase -> tramos -> planos
const COMPLEMENTO: Record<string, string> = {
  'cara:tomas': 'hombro:tomas', 'hombro:tomas': 'cara:tomas', 'medio:tomas': 'cara:tomas', 'cara:tomas_boca': 'hombro:madre',
  'contrapicado:cara_monstruo': 'ventana:monstruo', 'ventana:monstruo': 'contrapicado:cara_monstruo', 'contrapicado:monstruo': 'contrapicado:brazos',
  'contrapicado:brazos': 'hombro:tomas', 'cara:madre': 'hombro:madre', 'hombro:madre': 'cara:madre', 'medio:cuarto': 'cara:madre',
  'detalle:golpe': 'cara:tomas', 'detalle:cerrojo': 'cara:tomas', 'detalle:reloj': 'cara:tomas', 'medio:ventana_dentro': 'detalle:golpe',
  'ventana:cara_monstruo': 'cara:tomas', 'ventana:calle': 'contrapicado:monstruo', 'contrapicado:sonrisa': 'ventana:cara_monstruo',
  'contrapicado:mira_camara': 'cara:mira_camara', 'cara:mira_camara': 'contrapicado:mira_camara', 'general:calle': 'detalle:ventana_fuera',
  'general:cementerio': 'medio:ventana_fuera', 'general:pueblo': 'medio:vecinos', 'medio:ventana_fuera': 'detalle:ventana_fuera',
  'detalle:ventana_fuera': 'medio:ventana_fuera', 'medio:vecinos': 'detalle:vecinos_ventana', 'detalle:vecinos_ventana': 'medio:vecinos',
  'detalle:vecinos_dentro': 'detalle:vecinos_ventana', 'final:calle': 'cara:mira_camara',
};
const comp = (t: Toma): Toma => {
  const c = COMPLEMENTO[`${t.tipo}:${t.foco}`];
  if (!c) throw new Error(`sin encuadre complementario para ${t.tipo}:${t.foco}`);
  const [tipo, foco] = c.split(':');
  return {tipo, foco};
};
const repartir = (prop: Toma[], n: number): Toma[] => {
  if (n <= prop.length) return prop.length === 1 || n === prop.length ? prop.slice(0, n) : prop[prop.length - 1].tipo === 'final' ? prop.slice(-n) : prop.slice(0, n);
  const out = [...prop];
  const finalAl = out[out.length - 1].tipo === 'final';
  while (out.length < n) {
    const i = finalAl ? out.length - 1 : out.length; // insertar antes del final del loop
    const prev = out[i - 1];
    out.splice(i, 0, comp(prev).tipo === out[i]?.tipo && comp(prev).foco === out[i]?.foco ? comp(comp(prev)) : comp(prev));
  }
  return out;
};
const cortes: {toma: Toma; from: number; to: number; escena: string; etiqueta?: string}[] = [];
// Por cada línea de voz se elige el MEJOR juego de cortes: se puede cortar al empezar cualquier palabra, se
// prefiere cortar donde empieza una frase, y cada plano cuesta según se aleje de 1,2–1,6 s (más de 2 s o menos
// de 0,75 s no se permite). Es una programación dinámica pequeña: una línea tiene 10–25 palabras.
const coste = (d: number) => {
  const s = d / FPS;
  if (s > SPEC.planoTope + 1e-6 || s < 0.75) return Infinity;
  const fuera = s < SPEC.planoMin ? SPEC.planoMin - s : s > SPEC.planoMax ? s - SPEC.planoMax : 0;
  return fuera * fuera * 20 + Math.abs(s - 1.4) * 0.2;
};
ESCENAS.forEach((esc, li) => {
  const key = esc.key;
  const fin = li + 1 < ESCENAS.length ? ESCENAS[li + 1].from : TOTAL;
  const frases = FRASES.filter((fr) => fr.linea.key === key);
  // las frases con rayo o stinger son un golpe de montaje: ahí el corte es obligatorio
  const fuerte = (k: number) => (frases[k].frase.efectos ?? []).some((e) => e.rayo || e.stinger);
  const cand: {f: number; frase: number; obligado?: boolean}[] = [{f: esc.from, frase: 0}];
  frases.forEach((fr, k) => {
    for (let w = fr.desde; w < fr.hasta; w++) if (w > 0) cand.push({f: Math.round(W(key, w)) - 2, frase: w === fr.desde ? k : -1, obligado: w === fr.desde && fuerte(k)});
  });
  cand.push({f: fin, frase: -2});
  const best = cand.map(() => Infinity), prev = cand.map(() => -1);
  best[0] = 0;
  for (let j = 1; j < cand.length; j++) {
    for (let i = j - 1; i >= 0; i--) {
      if (i < j - 1 && cand[i + 1].obligado) break; // no se puede saltar un corte obligatorio
      const c = best[i] + coste(cand[j].f - cand[i].f) - (cand[j].frase >= 0 ? 0.3 : 0);
      if (c < best[j]) { best[j] = c; prev[j] = i; }
    }
  }
  if (!isFinite(best[cand.length - 1])) throw new Error(`la línea ${key} no se puede cortar dentro de la ficha`);
  const marcas: number[] = [];
  for (let j = cand.length - 1; j >= 0; j = prev[j]) { marcas.unshift(cand[j].f); if (j === 0) break; }
  // cada plano pertenece a la frase donde empieza; esa frase pone sus tomas y, si le tocan más, los complementos
  const deFrase = (f0: number) => {
    let k = 0;
    frases.forEach((fr, q) => { if (q > 0 && f0 >= Math.round(W(key, fr.desde)) - 2) k = q; });
    return k;
  };
  const grupos = new Map<number, [number, number][]>();
  for (let q = 0; q + 1 < marcas.length; q++) {
    const k = deFrase(marcas[q]);
    grupos.set(k, [...(grupos.get(k) ?? []), [marcas[q], marcas[q + 1]]]);
  }
  [...grupos.entries()].sort((x, y) => x[0] - y[0]).forEach(([k, tramos]) => {
    const tomas = repartir(frases[k].frase.tomas, tramos.length);
    tramos.forEach(([a, b2], q) => cortes.push({toma: tomas[q], from: a, to: b2, escena: key, etiqueta: q === 0 ? frases[k].frase.etiqueta : undefined}));
  });
});
// nunca dos planos seguidos con el mismo encuadre: el segundo pasa a su complementario
cortes.forEach((c, i) => {
  const p = cortes[i - 1];
  if (p && p.toma.tipo === c.toma.tipo && p.toma.foco === c.toma.foco && c.toma.tipo !== 'final') c.toma = comp(c.toma);
});

// 2) encuadres por tipo de plano
const o = (pos: V3, look: V3, fov = 34): Pose => ({pos, look, fov});
const cabezaTomas = (f: number): V3 => {
  const s = estado(f).tomas;
  return [s.pos[0], s.sentado > 0.5 ? 1.0 : 1.22, s.pos[2]];
};
const cabezaMonstruo = (f: number): V3 => {
  const m = estado(f).monstruo;
  return cabezaCosa(m.pos, m.yaw, m.agacha);
};
const lugarDe = (t: Toma): 'cuarto' | 'fuera' =>
  ['ventana_fuera', 'calle', 'cementerio', 'pueblo', 'vecinos', 'vecinos_ventana', 'vecinos_dentro', 'mira_camara'].includes(t.foco) || t.tipo === 'general' || t.tipo === 'final' || t.tipo === 'contrapicado' ? 'fuera' : 'cuarto';

/** el primer y el último plano son EL MISMO encuadre: así el Short empalma solo cuando YouTube lo repite */
export const ENCUADRE_LOOP = {a: o([0.6, 3.0, 17.5], [0, 1.9, 3.5], 38), b: o([0.3, 2.7, 15.2], [0, 1.95, 3.5], 36)};

const encuadre = (t: Toma, f: number, n: number): {a: Pose; b: Pose; e: EaseName; zoomRapido?: boolean} => {
  const j = (s: number, k = 1) => (rnd(n, s) - 0.5) * k; // variación determinística entre planos
  const T = cabezaTomas(f), M = cabezaMonstruo(f);
  switch (`${t.tipo}:${t.foco}`) {
    case 'general:calle': return {...ENCUADRE_LOOP, e: 'linear'};
    case 'final:calle': return {a: ENCUADRE_LOOP.b, b: o([0.15, 2.5, 13.6], [0, 2.1, 5], 34), e: 'out'};
    case 'general:cementerio': return {a: o([-4, 2.6, 15], [-14, 1.2, 6], 40), b: o([-6, 2.2, 14], [-14, 1.4, 6.5], 36), e: 'linear'};
    case 'general:pueblo': return {a: o([12, 10, 24], [0, 1, 3], 40), b: o([10, 8.5, 21], [0, 1.2, 3], 38), e: 'linear'};
    case 'detalle:ventana_fuera': return {a: o([1.6, 1.4, 6.5], [0, 1.5, 2], 32), b: o([1.1, 1.45, 5.2], [0, 1.5, 2], 30), e: 'linear'};
    case 'medio:ventana_fuera': return {a: o([-2.2, 1.6, 8], [0, 1.6, 2], 34), b: o([-1.6, 1.7, 7], [0, 1.6, 2], 32), e: 'linear'};
    case 'medio:tomas': return {a: o([T[0] + 1.6, 1.25, T[2] + 2.2], add3(T, [0, -0.15, 0]), 36), b: o([T[0] + 1.25, 1.2, T[2] + 1.8], add3(T, [0, -0.1, 0]), 34), e: 'soft'};
    case 'cara:tomas': case 'cara:tomas_boca': {
      const az = 0.25 + j(1, 0.7), d = 0.95;
      const p = (dd: number): V3 => [T[0] + Math.sin(az) * dd, T[1] + 0.04, T[2] + Math.cos(az) * dd];
      return {a: o(p(d + 0.2), T, 42), b: o(p(d - 0.05), T, 30), e: 'out', zoomRapido: true};
    }
    case 'cara:madre': {
      const H: V3 = [0.1, 1.55, 0.62];
      return {a: o([H[0] + 0.5, 1.6, H[2] + 1.0], H, 40), b: o([H[0] + 0.35, 1.58, H[2] + 0.8], H, 30), e: 'out', zoomRapido: true};
    }
    case 'cara:mira_camara': {
      const H = cabezaMonstruo(f);
      return {a: o([H[0], H[1] - 0.15, H[2] + 2.6], H, 40), b: o([H[0], H[1] - 0.1, H[2] + 1.9], H, 28), e: 'out', zoomRapido: true};
    }
    case 'detalle:reloj': return {a: o([-1.3, 1.95, -0.2], L.reloj, 34), b: o([-1.6, 1.98, -0.35], L.reloj, 30), e: 'linear'};
    case 'detalle:golpe': return {a: o([0.2 + j(2, 0.4), 1.55, 0.7], [0, 1.65, 2], 36), b: o([0.15, 1.6, 1.05], [0, 1.65, 2], 32), e: 'linear'};
    case 'detalle:cerrojo': return {a: o([0.15, 1.45, 1.35], L.cerrojo, 34), b: o([0.3, 1.4, 1.55], L.cerrojo, 30), e: 'linear'};
    case 'medio:ventana_dentro': return {a: o([-1.1, 1.3, -1.6], [0, 1.5, 2], 40), b: o([-0.8, 1.35, -1.0], [0, 1.5, 2], 36), e: 'linear'};
    case 'medio:cuarto': return {a: o([1.7, 1.7, -1.8], [0, 1.2, 1], 44), b: o([1.4, 1.6, -1.3], [0, 1.25, 1], 40), e: 'linear'};
    case 'ventana:monstruo': case 'ventana:cara_monstruo': case 'ventana:calle': {
      // POV desde dentro, a través del vidrio (el marco de la ventana encuadra la cosa)
      const cerca = t.foco === 'cara_monstruo';
      const mira: V3 = t.foco === 'calle' ? [0.2, 2.1, 6] : M;
      // con la madre y Tomás junto a la ventana, la cámara se corre a un lado para no quedar dentro de ellos
      const x = estado(f).madre.visible || estado(f).tomas.sentado < 0.5 ? 0.85 : 0.1 + j(3, 0.3);
      return {a: o([x, 1.5, cerca ? 1.2 : 0.2], mira, cerca ? 34 : 46), b: o([x * 0.9, 1.52, cerca ? 1.5 : 0.6], mira, cerca ? 28 : 42), e: 'linear'};
    }
    case 'hombro:tomas': return {a: o([T[0] - 0.35, T[1] + 0.22, T[2] - 0.55], [0, 1.7, 3.2], 40), b: o([T[0] - 0.25, T[1] + 0.2, T[2] - 0.35], [0, 1.75, 3.2], 36), e: 'soft'};
    case 'hombro:madre': return {a: o([-0.45, 1.75, -0.2], [0.05, 1.15, 1.2], 38), b: o([-0.35, 1.72, 0.05], [0.05, 1.15, 1.2], 34), e: 'soft'};
    case 'contrapicado:monstruo': case 'contrapicado:cara_monstruo': case 'contrapicado:sonrisa': case 'contrapicado:brazos': case 'contrapicado:mira_camara': {
      // cámara baja mirando hacia arriba: la cosa se ve enorme
      const m = estado(f).monstruo;
      const deFrente = m.yaw === 0;
      const lado = rnd(n, 4) > 0.5 ? 1 : -1;
      const cerca = t.foco === 'cara_monstruo' || t.foco === 'sonrisa';
      const mira: V3 = t.foco === 'brazos' ? [m.pos[0] + 0.3, 1.1, m.pos[2]] : cerca ? M : [M[0], M[1] - 0.5, M[2]];
      // de cara a la cámara final: por delante; pegada a la casa: de lado y un poco por delante (entre ella y la pared)
      const base: V3 = deFrente
        ? [m.pos[0] + lado * 0.6, 0.3, m.pos[2] + (cerca ? 1.5 : 2.8)]
        : [m.pos[0] + lado * (cerca ? 1.3 : 1.8), cerca ? 0.55 : 0.3, Math.max(2.45, m.pos[2] - (cerca ? 0.5 : 0.9))];
      const dir: V3 = [(m.pos[0] - base[0]) * 0.12, 0.05, (m.pos[2] - base[2]) * 0.12];
      return {a: o(base, mira, 44), b: o(add3(base, dir), mira, 38), e: 'linear'};
    }
    case 'medio:vecinos': return {a: o([4, 1.8, 9], [8, 1.6, 2], 36), b: o([4.8, 1.7, 7.6], [8, 1.6, 2], 32), e: 'linear'};
    case 'detalle:vecinos_ventana': return {a: o([7.2, 1.6, 4.4], [8, 1.55, 2], 34), b: o([7.5, 1.58, 3.6], [8, 1.55, 2], 30), e: 'linear'};
    case 'detalle:vecinos_dentro': return {a: o([8, 1.55, 3.4], [8, 1.3, -1], 40), b: o([8, 1.5, 2.6], [8, 1.3, -1], 34), e: 'in'};
  }
  throw new Error(`encuadre sin definir: ${t.tipo}:${t.foco}`);
};

export const PLANOS: Plano[] = cortes.map((c, n) => {
  const en = encuadre(c.toma, c.from, n);
  return {...c.toma, n, from: c.from, to: c.to, a: en.a, b: en.b, e: en.e, zoomRapido: !!en.zoomRapido, lugar: lugarDe(c.toma), escena: c.escena, etiqueta: c.etiqueta};
});
export const planoEn = (f: number) => {
  for (let i = PLANOS.length - 1; i >= 0; i--) if (f >= PLANOS[i].from) return PLANOS[i];
  return PLANOS[0];
};
/** transición whoosh: en cada cambio de escena (o de dentro a fuera) */
export const WHOOSH = PLANOS.slice(1).filter((p, i) => p.escena !== PLANOS[i].escena || p.lugar !== PLANOS[i].lugar).map((p) => p.from);

export const poseEn = (f: number): Pose => {
  const p = planoEn(f);
  const u = clamp((f - p.from) / Math.max(1, p.to - p.from));
  const t = E[p.e](u);
  // zoom rápido de los primeros planos de cara: el fov cae en 5 cuadros y luego sigue el push-in lento
  const fov = p.zoomRapido ? lerp(p.a.fov, p.b.fov, 0.75 * E.out(clamp((f - p.from) / 5)) + 0.25 * u) : lerp(p.a.fov, p.b.fov, t);
  // flotación leve (cámara en mano) encima del movimiento: nunca un cuadro quieto
  const fl = (k: number, s: number) => Math.sin(f / k + p.n * 1.3) * s;
  return {
    pos: [lerp(p.a.pos[0], p.b.pos[0], t) + fl(17, 0.012), lerp(p.a.pos[1], p.b.pos[1], t) + fl(23, 0.01), lerp(p.a.pos[2], p.b.pos[2], t)],
    look: [lerp(p.a.look[0], p.b.look[0], t) + fl(29, 0.01), lerp(p.a.look[1], p.b.look[1], t) + fl(31, 0.008), lerp(p.a.look[2], p.b.look[2], t)],
    fov,
  };
};
export const aplicarPose = (c: THREE.PerspectiveCamera, f: number) => {
  const p = poseEn(f);
  c.position.set(...p.pos);
  c.up.set(0, 1, 0);
  c.lookAt(...p.look);
  c.fov = p.fov;
  c.aspect = SPEC.ancho / SPEC.alto;
  c.near = 0.03;
  c.far = 200;
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
};
