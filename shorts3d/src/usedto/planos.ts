// CÁMARA de «Used To»: movimientos CONTINUOS (órbitas lentas, push-in, seguimiento de la pieza que se mueve) y un
// ángulo nuevo cada 2–4 s amarrado a la frase. Cada plano dice también DÓNDE ENFOCA (la profundidad de campo
// corta deja el fondo suave y la pieza nítida).
import * as THREE from 'three';
import {ESCENAS, W, TOTAL, FPS, VO} from './timing';
import {SPEC} from './spec';
import {estado, M, V3} from './estado';
import {lerp, clamp, E, EaseName} from '../anim';

type Pose = {pos: V3; look: V3; fov: number};
export type Plano = {toma: string; n: number; from: number; to: number; escena: string; corte: 'seco' | 'barrido'};

// 1) cortes: cada frase reparte sus tomas; una toma que pasaría de 4 s se parte en dos con la variante «b»
const cortes: Plano[] = [];
ESCENAS.forEach((e, i) => {
  const fin = i + 1 < ESCENAS.length ? ESCENAS[i + 1].from : TOTAL;
  const n0 = e.frase.tomas.length;
  const span = (fin - e.from) / FPS;
  const n = Math.max(n0, Math.ceil(span / SPEC.planoMax));
  // si hacen falta más tomas, la variante «~» se inserta ANTES del último plano del loop (ese nunca se parte)
  const ult = e.frase.tomas[n0 - 1];
  const fijo = ult === 'loop_final';
  const base = fijo ? e.frase.tomas.slice(0, -1) : e.frase.tomas;
  const extra = Array.from({length: n - n0}, (_, q) => `${base[base.length - 1]}~${q + 2}`);
  const tomas = fijo ? [...base, ...extra, ult] : [...base, ...extra];
  // cortes internos en el inicio de la palabra más cercana al reparto parejo
  const ws = VO[e.key].words;
  const marcas = [e.from];
  for (let q = 1; q < n; q++) {
    const ideal = e.from + ((fin - e.from) * q) / n;
    let mejor = ideal, d = 1e9;
    ws.forEach((_, w) => {
      const c = Math.round(W(e.key, w)) - 2;
      if (Math.abs(c - ideal) < d && c - marcas[marcas.length - 1] >= SPEC.planoMin * FPS * 0.9 && fin - c >= SPEC.planoMin * FPS * 0.9) { d = Math.abs(c - ideal); mejor = c; }
    });
    marcas.push(Math.round(mejor));
  }
  marcas.push(fin);
  tomas.forEach((t, q) => cortes.push({toma: t, n: cortes.length, from: marcas[q], to: marcas[q + 1], escena: e.key, corte: t === 'estante' || t === 'loop_final' ? 'barrido' : 'seco'}));
});
export const PLANOS = cortes;
export const planoEn = (f: number) => {
  for (let i = PLANOS.length - 1; i >= 0; i--) if (f >= PLANOS[i].from) return PLANOS[i];
  return PLANOS[0];
};

// 2) encuadres. `u` va de 0 a 1 a lo largo del plano; `s` es el estado del mecanismo en ese cuadro.
const orbita = (centro: V3, r: number, az: number, alto: number): V3 => [centro[0] + Math.sin(az) * r, alto, centro[2] + Math.cos(az) * r];
/** el primer y el último cuadro son el MISMO: así el Short empalma solo al repetirse */
export const POSE_LOOP: Pose = {pos: orbita([0, 1.9, 0], 4.6, -0.42, 2.35), look: [0, 1.85, 0], fov: 44};
const cabina = (s: ReturnType<typeof estado>): V3 => [0, s.y + 0.4, 0];

const encuadre = (toma: string, u: number, f: number): {pose: Pose; foco: V3} => {
  const s = estado(f);
  const [base, variante] = toma.split('~');
  const vv = variante ? 0.6 : 0; // la variante gira la órbita al otro lado
  const C = cabina(s);
  switch (base) {
    case 'orbita_inicio': {
      const az = lerp(-0.42, -0.2, u);
      return {pose: {pos: orbita([0, 1.9, 0], lerp(4.6, 4.1, u), az, lerp(2.35, 2.45, u)), look: [0, 1.85, 0], fov: 44}, foco: [0, 2.3, 0]};
    }
    case 'cuerda_macro': case 'cuerda_corte': {
      const p: V3 = [0, 3.0, 0];
      return {pose: {pos: [lerp(0.55, 0.42, u) - vv, lerp(3.08, 3.02, u), lerp(0.45, 0.32, u)], look: p, fov: 34}, foco: p};
    }
    case 'caida': {
      // seguimiento: la cámara baja con la cabina
      return {pose: {pos: [1.3 - vv * 2.4, C[1] + 0.35, 2.0], look: [0, C[1] - 0.1, 0], fov: 46}, foco: C};
    }
    case 'cable_subida': return {pose: {pos: orbita([0, 2.6, 0], lerp(2.4, 2.0, u), lerp(0.5, 0.25, u), 2.95), look: [0, 2.9, 0], fov: 42}, foco: [0, 3.0, 0]};
    case 'cable_macro': {
      const p: V3 = [0, 3.05, 0];
      return {pose: {pos: [lerp(-0.4, -0.3, u), 3.12, lerp(0.42, 0.3, u)], look: p, fov: 30}, foco: p};
    }
    case 'orbita_otis': return {pose: {pos: orbita([0, 2.4, 0], lerp(3.4, 2.7, u), lerp(0.55, 0.3, u), 3.0), look: [0, 2.75, 0], fov: 42}, foco: [0, 2.85, 0]};
    case 'muelle_macro': {
      const p: V3 = [0.2, s.y + 0.8, 0];
      return {pose: {pos: [lerp(0.95, 0.75, u) - vv * 1.6, s.y + 1.05, lerp(0.75, 0.6, u)], look: p, fov: 36}, foco: p};
    }
    case 'muelle_lado': {
      const p: V3 = [0, s.y + 0.78, 0];
      return {pose: {pos: [lerp(-1.1, -0.9, u), s.y + 0.95, lerp(1.0, 1.25, u)], look: p, fov: 40}, foco: p};
    }
    case 'dientes': {
      // seguimiento a lo largo del riel dentado
      const yy = lerp(1.75, 0.95, E.soft(u)); // por debajo de la cabina: solo riel y dientes
      const p: V3 = [M.rielX - 0.03, yy, 0];
      return {pose: {pos: [M.rielX - 0.32, yy + 0.06, 0.42], look: p, fov: 34}, foco: p};
    }
    case 'traba_macro': {
      const p: V3 = [M.rielX - 0.04, s.y + 0.8, 0];
      return {pose: {pos: [M.rielX - 0.42 + vv * 0.1, s.y + 0.92, lerp(0.42, 0.34, u)], look: p, fov: 32}, foco: p};
    }
    case 'feria': return {pose: {pos: orbita([0, 1.8, 0], lerp(4.2, 3.8, u), lerp(0.2, 0.05, u), 1.1), look: [0, 2.3, 0], fov: 46}, foco: C};
    case 'sombrero': {
      const p: V3 = [0.12, s.y + 0.12, 0.05];
      return {pose: {pos: [lerp(0.9, 0.7, u), s.y + 0.32, lerp(1.1, 0.9, u)], look: p, fov: 36}, foco: p};
    }
    case 'tambor': {
      const p: V3 = [0.95, 0.5, 0];
      return {pose: {pos: [lerp(1.7, 1.5, u), 0.85, lerp(1.0, 0.85, u)], look: p, fov: 38}, foco: p};
    }
    case 'regulador': case 'regulador_macro': {
      const p: V3 = [-0.38, 3.62, 0];
      const cerca = base === 'regulador_macro';
      return {pose: {pos: orbita([-0.38, 3.6, 0], lerp(cerca ? 0.9 : 1.7, cerca ? 0.75 : 1.4, u), lerp(0.4, 0.9, u) + vv, 3.72), look: p, fov: 38}, foco: p};
    }
    case 'estante': {
      // barrido lateral del ascensor viejo al moderno, que está al lado en la repisa
      const x = lerp(0, M.moderno, E.inOut(clamp(u * 1.25)));
      return {pose: {pos: [x + 0.4, 2.2, 3.9], look: [x, 1.9, 0], fov: 44}, foco: [x, 1.9, 0]};
    }
    case 'cables_moderno': return {pose: {pos: orbita([M.moderno, 2.4, 0], lerp(3.0, 2.6, u), lerp(-0.2, 0.05, u), 2.7), look: [M.moderno, 2.6, 0], fov: 42}, foco: [M.moderno, 2.8, 0]};
    case 'cables_macro': {
      const p: V3 = [M.moderno, 3.05, 0];
      return {pose: {pos: [M.moderno + lerp(0.5, 0.38, u), 3.15, lerp(0.5, 0.4, u)], look: p, fov: 32}, foco: p};
    }
    case 'loop_final': {
      // vuelve al ascensor viejo y termina EXACTAMENTE en la pose del primer cuadro
      const k = E.inOut(u); // el barrido dura todo el plano y llega a la pose del loop justo en el último cuadro
      const desde: Pose = {pos: [M.moderno + 0.4, 2.2, 3.9], look: [M.moderno, 1.9, 0], fov: 44};
      return {pose: {pos: [lerp(desde.pos[0], POSE_LOOP.pos[0], k), lerp(desde.pos[1], POSE_LOOP.pos[1], k), lerp(desde.pos[2], POSE_LOOP.pos[2], k)],
        look: [lerp(desde.look[0], POSE_LOOP.look[0], k), lerp(desde.look[1], POSE_LOOP.look[1], k), 0], fov: 44}, foco: [lerp(M.moderno, 0, k), 2.3, 0]};
    }
  }
  throw new Error(`toma sin encuadre: ${toma}`);
};

export const camaraEn = (f: number) => {
  const p = planoEn(f);
  const u = clamp((f - p.from) / Math.max(1, p.to - p.from));
  const r = encuadre(p.toma, u, f);
  // respiración de cámara en mano, muy leve (y nada en el primer y el último cuadro: el loop empalma exacto)
  const amp = f < 2 || f > TOTAL - 3 ? 0 : 1;
  const fl = (k: number, a: number) => Math.sin(f / k + p.n) * a * amp;
  return {pos: [r.pose.pos[0] + fl(19, 0.006), r.pose.pos[1] + fl(23, 0.005), r.pose.pos[2]] as V3, look: r.pose.look, fov: r.pose.fov, foco: r.foco};
};
export const aplicarCamara = (c: THREE.PerspectiveCamera, f: number) => {
  const p = camaraEn(f);
  c.position.set(...p.pos);
  c.lookAt(...p.look);
  c.fov = p.fov;
  c.aspect = SPEC.ancho / SPEC.alto;
  c.near = 0.02;
  c.far = 80;
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
};
export type {EaseName};
