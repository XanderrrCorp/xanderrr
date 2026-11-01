import * as THREE from 'three';
import {at, sc, SCENES} from './timing';
import {E, EaseName, lerp, V3, clamp} from './anim';
import {PERCH, CAV, THERMO} from './lugares';
export const FOV = 30;
type Pose = {t: V3; d: number; az: number; el: number};
type Key = {f: number; p: Pose; e: EaseName};
const o = (t: V3, d: number, az: number, el: number): Pose => ({t, d, az, el});
const head: V3 = [PERCH[0] - 0.7, PERCH[1] - 0.25, PERCH[2]];
const dn = (p: V3, d: number): V3 => [p[0], p[1] - d, p[2]];
const RAW: [number, number, Pose, EaseName][] = [
  [0, 0, o([6.2, 2.3, 3.2], 12.5, 32, 6), 'linear'],
  [0, 0.4, o(dn(PERCH, 0.45), 11, 18, 6), 'soft'],
  [0, 1, o(dn(PERCH, 0.45), 11, 6, 8), 'soft'],
  [1, 0.15, o(dn(PERCH, 0.45), 9.6, 0, 9), 'soft'],
  [1, 1, o(dn(PERCH, 0.45), 9.2, 34, 12), 'soft'],
  [2, 0.28, o(head, 5.2, 28, 4), 'soft'],
  [2, 0.6, o([1.6, 2.0, 0.2], 23, 16, 10), 'inOut'],
  [2, 1, o([1.6, 2.1, 0.2], 22, 8, 11), 'soft'],
  [3, 0.45, o([1.0, 1.9, 0.6], 17, 6, 12), 'soft'],
  [3, 1, o([0.4, 1.8, 0.9], 14.5, 22, 13), 'soft'],
  [4, 0.35, o(dn(CAV, 0.3), 11.5, 18, 8), 'soft'],
  [4, 1, o(dn(CAV, 0.3), 10.2, 8, 6), 'soft'],
  [5, 0.25, o([(CAV[0] + THERMO[0]) / 2, 1.8, (CAV[2] + THERMO[2]) / 2], 15.5, -6, 7), 'soft'],
  [5, 1, o([(CAV[0] + THERMO[0]) / 2, 1.8, (CAV[2] + THERMO[2]) / 2], 14.8, -18, 8), 'soft'],
  [6, 0.45, o([0.6, 1.9, 0.3], 19, 0, 10), 'soft'],
  [6, 1, o([0.8, 2.1, 0.0], 23.5, 14, 12), 'soft'],
];
const KEYS: Key[] = RAW.map(([i, fr, p, e]) => ({f: at(i, fr), p, e}));
export const poseAt = (f: number): Pose => {
  let k = 0;
  while (k < KEYS.length - 1 && f >= KEYS[k + 1].f) k++;
  const a = KEYS[k], b = KEYS[Math.min(k + 1, KEYS.length - 1)];
  const t = b === a ? 0 : E[b.e](clamp((f - a.f) / Math.max(1, b.f - a.f)));
  const p: Pose = {
    t: [lerp(a.p.t[0], b.p.t[0], t), lerp(a.p.t[1], b.p.t[1], t), lerp(a.p.t[2], b.p.t[2], t)],
    d: Math.exp(lerp(Math.log(a.p.d), Math.log(b.p.d), t)),
    az: lerp(a.p.az, b.p.az, t) + 1.2 * Math.sin(f / 37),
    el: lerp(a.p.el, b.p.el, t) + 0.6 * Math.sin(f / 53),
  };
  return p;
};
export const camPos = (p: Pose): V3 => {
  const az = (p.az * Math.PI) / 180, el = (p.el * Math.PI) / 180;
  return [p.t[0] + p.d * Math.sin(az) * Math.cos(el), p.t[1] + p.d * Math.sin(el), p.t[2] + p.d * Math.cos(az) * Math.cos(el)];
};
const cam = new THREE.PerspectiveCamera(FOV, 1080 / 1920, 0.1, 200);
export const applyPose = (c: THREE.PerspectiveCamera, f: number) => {
  const p = poseAt(f);
  c.position.set(...camPos(p));
  c.up.set(0, 1, 0);
  c.lookAt(...p.t);
  c.fov = FOV;
  c.aspect = 1080 / 1920;
  c.near = 0.1;
  c.far = 200;
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
};
/** punto 3D -> píxeles de la pantalla 1080x1920 en el cuadro f */
export const project = (f: number, pt: V3) => {
  applyPose(cam, f);
  const v = new THREE.Vector3(...pt).project(cam);
  return {x: (v.x * 0.5 + 0.5) * 1080, y: (-v.y * 0.5 + 0.5) * 1920, behind: v.z > 1};
};
export const camDir = (f: number): V3 => {
  const p = poseAt(f), c = camPos(p);
  const d: V3 = [c[0] - p.t[0], c[1] - p.t[1], c[2] - p.t[2]];
  const n = Math.hypot(...d);
  return [d[0] / n, d[1] / n, d[2] / n];
};
export {SCENES, sc};
