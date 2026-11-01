import {spring} from 'remotion';
export type V3 = [number, number, number];
export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const lerp3 = (a: V3, b: V3, t: number): V3 => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
export const add3 = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const E = {
  linear: (t: number) => t,
  in: (t: number) => t * t * t,
  out: (t: number) => 1 - Math.pow(1 - t, 3),
  inOut: (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  soft: (t: number) => 0.5 - 0.5 * Math.cos(Math.PI * t),
};
export type EaseName = keyof typeof E;
/** progreso 0..1 entre los cuadros a y b */
export const prog = (f: number, a: number, b: number, e: EaseName = 'inOut') => E[e](clamp((f - a) / Math.max(1e-6, b - a)));
export const sp = (f: number, start: number, damping = 12, mass = 0.6) =>
  spring({frame: f - start, fps: 30, config: {damping, mass, stiffness: 120}});
/** pseudoaleatorio determinístico */
export const rnd = (i: number, s = 1) => {
  const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453;
  return x - Math.floor(x);
};
export const bez3 = (a: V3, c: V3, b: V3, t: number): V3 => lerp3(lerp3(a, c, t), lerp3(c, b, t), t);
