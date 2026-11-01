// Planos con CORTE SECO (fórmula de Shorts: cambio de imagen cada 1,5–2 s). Cada plano tiene su escenario,
// una pose inicial y una final de cámara, y el cuadro donde empieza (amarrado a las palabras de la voz).
import * as THREE from 'three';
import {SCENES, W, TOTAL} from './timing';
import {E, EaseName, lerp, V3, clamp} from '../anim';

export const SET = {noche: [0, 0, 0] as V3, pedestales: [60, 0, 0] as V3, pelo: [120, 0, 0] as V3, tortuga: [180, 0, 0] as V3, vacio: [240, 0, 0] as V3};
export type SetName = keyof typeof SET;
type Pose = {t: V3; d: number; az: number; el: number};
const o = (t: V3, d: number, az: number, el: number): Pose => ({t, d, az, el});
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export type Plano = {id: string; set: SetName; from: number; to: number; a: Pose; b: Pose; e: EaseName; fov?: number};

const N = SET.noche, P = SET.pedestales, H = SET.pelo, T = SET.tortuga, V = SET.vacio;
const cara: V3 = [2.05, 1.86, 0];             // cara de la pantera (en el escenario de noche)
const CARA_A = o(cara, 3.0, 76, 3), CARA_B = o(cara, 2.4, 82, 2);
const r = Math.round;
const end = (i: number) => SCENES[i].from + SCENES[i].dur;

const RAW: Omit<Plano, 'to'>[] = [
  {id: 'P1-cara', set: 'noche', from: 0, a: CARA_A, b: CARA_B, e: 'linear'},
  {id: 'P2-ojos', set: 'noche', from: SCENES[1].from, a: o([1.6, 1.6, 0], 9.5, 72, 2), b: o([1.6, 1.6, 0], 8.2, 78, 2), e: 'linear'},
  {id: 'P3-luna', set: 'noche', from: r(W(1, 7)) - 3, a: o([0.3, 1.9, 0], 7.2, 28, -9), b: o([0.6, 1.9, 0], 6.6, 40, -11), e: 'soft'},
  {id: 'P4-jaguar', set: 'pedestales', from: SCENES[2].from, a: o(add(P, [-3.5, 1.7, 0]), 6.2, 10, 8), b: o(add(P, [-3.5, 1.7, 0]), 5.6, 24, 8), e: 'soft'},
  {id: 'P5-leopardo', set: 'pedestales', from: r(W(2, 5)) - 3, a: o(add(P, [3.5, 1.7, 0]), 6.2, -8, 8), b: o(add(P, [3.5, 1.7, 0]), 5.6, -24, 8), e: 'soft'},
  {id: 'P6-pigmento', set: 'pelo', from: r(W(2, 12)) - 3, a: o(add(H, [0, 1.2, 0]), 10, 18, 6), b: o(add(H, [0, 1.6, 0]), 8.6, 34, 8), e: 'soft'},
  {id: 'P7-negros', set: 'pedestales', from: r(W(2, 19)) - 4, a: o(add(P, [0, 0.4, 0]), 27, 0, 10), b: o(add(P, [0, 0.4, 0]), 25, 6, 11), e: 'soft'},
  {id: 'P8-sombra', set: 'noche', from: SCENES[3].from, a: o([1.2, 1.4, 0], 9, 40, 6), b: o([2.6, 1.4, 0], 9, 30, 6), e: 'linear'},
  {id: 'P9-rama', set: 'noche', from: r(W(3, 5)) - 3, a: o([3.0, 0.35, 0.3], 3.0, 22, 8), b: o([3.9, 0.35, 0.3], 2.8, 30, 8), e: 'linear'},
  {id: 'P10-mordida', set: 'tortuga', from: r(W(3, 10)) - 3, a: o(add(T, [1.9, 1.2, 0]), 5.6, 14, 6), b: o(add(T, [2.1, 1.15, 0]), 4.8, 22, 6), e: 'soft'},
  {id: 'P10b-crujido', set: 'tortuga', from: r(W(3, 16)) - 3, a: o(add(T, [2.45, 1.0, 0]), 3.2, 40, 14), b: o(add(T, [2.5, 0.95, 0]), 2.7, 52, 16), e: 'soft'},
  {id: 'P11-luz', set: 'noche', from: SCENES[4].from, a: o([0, 1.4, 0], 8.8, 2, 4), b: o([0, 1.4, 0], 8.4, -4, 4), e: 'soft'},
  {id: 'P12-manchas', set: 'noche', from: r(W(4, 8)) - 3, a: o([-0.3, 1.35, 0.3], 3.0, 8, 6), b: o([0.4, 1.35, 0.3], 2.8, 14, 6), e: 'linear'},
  {id: 'P13-entera', set: 'noche', from: r(W(4, 14)) - 3, a: o([0, 1.4, 0], 9.5, 18, 8), b: o([0, 1.4, 0], 8.8, 30, 9), e: 'soft'},
  {id: 'P14-mira', set: 'noche', from: SCENES[5].from, a: o([1.9, 1.75, 0], 4.6, 62, 3), b: o([1.9, 1.75, 0], 4.0, 58, 3), e: 'soft'},
  {id: 'P15-vacio', set: 'vacio', from: SCENES[6].from, a: o(add(V, [0, 1, 0]), 8, 0, 0), b: o(add(V, [0, 1, 0]), 7, 0, 0), e: 'linear'},
  // vuelve al mismo plano del cuadro 0: cuando YouTube repite el Short, empalma con «La pantera negra no existe»
  {id: 'P16-loop', set: 'noche', from: r(W(6, 14)) - 3, a: o(cara, 4.4, 70, 6), b: CARA_A, e: 'out'},
];
export const PLANOS: Plano[] = RAW.map((p, i) => ({...p, to: i + 1 < RAW.length ? RAW[i + 1].from : TOTAL}));
export const planoAt = (f: number) => {
  for (let i = PLANOS.length - 1; i >= 0; i--) if (f >= PLANOS[i].from) return PLANOS[i];
  return PLANOS[0];
};
export const poseAt = (f: number): Pose => {
  const p = planoAt(f);
  const t = E[p.e](clamp((f - p.from) / Math.max(1, p.to - p.from)));
  return {
    t: [lerp(p.a.t[0], p.b.t[0], t), lerp(p.a.t[1], p.b.t[1], t), lerp(p.a.t[2], p.b.t[2], t)],
    d: Math.exp(lerp(Math.log(p.a.d), Math.log(p.b.d), t)),
    az: lerp(p.a.az, p.b.az, t) + (p.id === 'P1-cara' || p.id === 'P16-loop' ? 0 : 0.8 * Math.sin(f / 23)),
    el: lerp(p.a.el, p.b.el, t),
  };
};
export const camPos = (p: Pose): V3 => {
  const az = (p.az * Math.PI) / 180, el = (p.el * Math.PI) / 180;
  return [p.t[0] + p.d * Math.sin(az) * Math.cos(el), p.t[1] + p.d * Math.sin(el), p.t[2] + p.d * Math.cos(az) * Math.cos(el)];
};
const cam = new THREE.PerspectiveCamera(32, 1080 / 1920, 0.05, 300);
export const applyPose = (c: THREE.PerspectiveCamera, f: number) => {
  const p = poseAt(f);
  c.position.set(...camPos(p));
  c.lookAt(...p.t);
  c.fov = 32;
  c.aspect = 1080 / 1920;
  c.near = 0.05;
  c.far = 300;
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
};
export const project = (f: number, pt: V3) => {
  applyPose(cam, f);
  const v = new THREE.Vector3(...pt).project(cam);
  return {x: (v.x * 0.5 + 0.5) * 1080, y: (-v.y * 0.5 + 0.5) * 1920, behind: v.z > 1};
};
export {end};
