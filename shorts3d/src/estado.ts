// Todo el estado del mundo como función pura del cuadro global f (sin acumular nada).
import {W, at, voEnd, FPS} from './timing';
import {prog, sp, lerp, lerp3, bez3, V3, clamp} from './anim';
import {PERCH, ENTRY, CAV, FLOOR} from './lugares';

const s = (x: number) => x * FPS;
export const T = {
  llegaFin: at(0, 0) + s(1.6),
  pulgar: W(0, 4) - 6, pulgarFuera: W(0, 8),
  regla: W(1, 1), golpes: [W(1, 11), W(1, 13) + 2, W(1, 17)],
  mandibulas: W(2, 2) - 4, mandibulasFin: W(2, 5),
  extras: W(2, 4), puerta: W(2, 9) - 8, alarma: W(2, 10), reloj: W(2, 14) - 4,
  extrasSeVan: at(3, 0) + 4,
  entra: W(3, 7) - 4, entraFin: W(3, 10) + 6, enjambre: W(3, 11) - 4, enjambreFin: voEnd(3) + 4,
  aprieta: W(4, 0), vibra: W(4, 7) - 3, corte: W(4, 13) - 6,
  calor: W(5, 2), calorFin: W(5, 10) + 4,
  suelta: W(6, 1) + 4, cae: W(6, 1) + 10, cta: W(6, 14) - 6,
};

export const hornet = (f: number) => {
  let pos: V3 = PERCH, heading = Math.PI, flap = 0, roll = 0, dark = 0;
  if (f < T.llegaFin) {
    const t = prog(f, at(0, 0) - 2, T.llegaFin, 'out');
    const c: V3 = [ENTRY[0] - 1, PERCH[1] + 2.2, PERCH[2] + 3.5];
    pos = bez3(ENTRY, c, PERCH, t);
    const nx = bez3(ENTRY, c, PERCH, Math.min(1, t + 0.02));
    heading = lerp(Math.atan2(-(nx[2] - pos[2]), nx[0] - pos[0]), Math.PI, prog(t, 0.75, 1, 'inOut'));
    flap = 1 - prog(t, 0.85, 1);
    pos = [pos[0], pos[1] + 0.06 * Math.sin(f * 0.9) * (1 - t), pos[2]];
  }
  if (f >= T.entra) {
    const t = prog(f, T.entra, T.entraFin, 'inOut');
    const c: V3 = [2.2, 3.4, 1.6];
    pos = bez3(PERCH, c, CAV, t);
    flap = Math.min(1, t * 4) * (1 - prog(f, T.entraFin, T.entraFin + 10)) + 0.15;
    heading = Math.PI + 0.25 * Math.sin(t * Math.PI);
  }
  if (f >= T.cae) {
    const t = prog(f, T.cae, T.cae + 30, 'in');
    pos = lerp3(CAV, FLOOR, t);
    roll = lerp(0, 2.7, prog(f, T.cae, T.cae + 26, 'inOut'));
    flap = 0;
    dark = 0.55 * prog(f, T.cae, T.cae + 40);
  }
  const jaws = f >= T.mandibulas && f < T.mandibulasFin ? 0.5 - 0.5 * Math.cos((f - T.mandibulas) * 0.45) : 0;
  const hit = Math.max(0, ...T.golpes.map((g) => (f >= g ? Math.exp(-(f - g) / 4) : 0)));
  const heat = calor(f);
  const idle = f >= T.llegaFin && f < T.entra ? 0.025 * Math.sin(f / 9) : 0;
  return {pos: [pos[0], pos[1] + idle, pos[2]] as V3, heading, flap, roll, dark, jaws, hit, heat};
};

export const thumb = (f: number) => (f < T.pulgarFuera ? sp(f, T.pulgar, 11) : 1 - prog(f, T.pulgarFuera, T.pulgarFuera + 12, 'in'));
export const ruler = (f: number) => (f < at(2, 0) ? prog(f, T.regla, T.regla + 20, 'out') : 1 - prog(f, at(2, 0), at(2, 0) + 8));
export const door = (f: number) => prog(f, T.puerta, T.puerta + 34, 'inOut');
export const alarm = (f: number) => (f >= T.alarma && f < T.entra ? (0.5 - 0.5 * Math.cos((f - T.alarma) * 0.32)) * (1 - prog(f, T.entra - 10, T.entra)) : 0);
/** 0 = abejas en los panales, 1 = bola completa alrededor del avispón */
export const swarm = (f: number) => (f < T.suelta ? prog(f, T.enjambre, T.enjambreFin, 'linear') : 1 - prog(f, T.suelta, T.suelta + 45, 'linear'));
export const tight = (f: number) => (f < T.suelta ? prog(f, T.aprieta, T.aprieta + 24, 'out') : 1 - prog(f, T.suelta, T.suelta + 20));
export const vibrate = (f: number) => (f < T.suelta ? prog(f, T.vibra, T.vibra + 10) : 0);
export const cutaway = (f: number) => (f < T.suelta ? prog(f, T.corte, T.corte + 26, 'inOut') : 1 - prog(f, T.suelta, T.suelta + 15));
export function calor(f: number) {
  return f < T.suelta ? prog(f, T.calor, T.calorFin, 'inOut') : 1 - prog(f, T.suelta, T.suelta + 50, 'inOut');
}
export const thermoShow = (f: number) => (f < at(6, 0) + 20 ? sp(f, at(5, 0) - 6, 12) : 1 - prog(f, at(6, 0) + 20, at(6, 0) + 34, 'in'));
export const extras = (f: number) => {
  const inn = clamp(sp(f, T.extras, 14));
  const out = prog(f, T.extrasSeVan, T.extrasSeVan + 30, 'in');
  return {inn, out};
};
