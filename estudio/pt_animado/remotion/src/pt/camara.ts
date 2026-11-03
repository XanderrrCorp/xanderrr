// Cámara de las plantillas: tomas con cortes secos o deslizamientos suaves (smootherstep de 18-40 cuadros), toda toma
// fija con un acercamiento lento (nunca plano quieto), golpes de cámara que cambian de signo cada cuadro y se apagan en
// 7 cuadros, y reencuadre para 16:9 o 9:16.
import type { Vec3 } from "./mundo";

export const FPS = 30;
export type Formato = "16:9" | "9:16";
export type Clave = { f: number; pos: Vec3; look: Vec3; fov: number; roll?: number; corte?: boolean; desliza?: number; empuje?: number };

export const suave = (x: number) => { const t = Math.min(1, Math.max(0, x)); return t * t * t * (t * (t * 6 - 15) + 10); };
const mezcla = (a: Vec3, b: Vec3, t: number): Vec3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** reencuadre: en vertical la cámara retrocede y abre el lente para que quepan personaje y animal */
export function reencuadrar(c: { pos: Vec3; look: Vec3; fov: number }, formato: Formato) {
  if (formato === "16:9") return c;
  const d: Vec3 = [c.pos[0] - c.look[0], c.pos[1] - c.look[1], c.pos[2] - c.look[2]];
  return { pos: [c.look[0] + d[0] * 1.15, c.look[1] + d[1] * 1.15 + 0.15, c.look[2] + d[2] * 1.15] as Vec3, look: c.look, fov: Math.min(75, c.fov * 1.55) };
}

/** pose de la cámara en el cuadro f según las claves (ordenadas por f) */
export function camaraEn(claves: Clave[], f: number, formato: Formato) {
  let i = 0;
  while (i + 1 < claves.length && claves[i + 1].f <= f) i++;
  const a = claves[i], b = claves[i + 1];
  let pos = a.pos, look = a.look, fov = a.fov, roll = a.roll ?? 0;
  // la siguiente clave que no es corte empieza a deslizarse `desliza` cuadros antes
  if (b && !b.corte) {
    const dur = b.desliza ?? 24, t = suave((f - (b.f - dur)) / dur);
    if (t > 0) { pos = mezcla(a.pos, b.pos, t); look = mezcla(a.look, b.look, t); fov = a.fov + (b.fov - a.fov) * t; roll = roll + ((b.roll ?? 0) - roll) * t; }
  }
  // acercamiento lento en toda toma (0,2 %/cuadro, más en palabras fuertes con `empuje`)
  const k = 1 - Math.min(0.35, (f - a.f) * (a.empuje ?? 0.002));
  pos = [look[0] + (pos[0] - look[0]) * k, look[1] + (pos[1] - look[1]) * k, look[2] + (pos[2] - look[2]) * k];
  return { ...reencuadrar({ pos, look, fov }, formato), roll };
}

/** golpe de cámara: sacudida que cambia de signo cada cuadro y se apaga en 7 cuadros */
export function golpe(f: number, en: number[], fuerza = 0.06): Vec3 {
  let dx = 0, dy = 0;
  for (const g of en) {
    const k = f - g;
    if (k >= 0 && k < 7) { const a = fuerza * (1 - k / 7) * (k % 2 ? -1 : 1); dx += a; dy += a * 0.6; }
  }
  return [dx, dy, 0];
}

/** cuadro en el que debe reaccionar algo para una palabra que se dice en t segundos (0-3 cuadros antes) */
export const antes = (t: number | undefined, adelanto = 2) => (t === undefined ? Infinity : Math.max(0, Math.round(t * FPS) - adelanto));
