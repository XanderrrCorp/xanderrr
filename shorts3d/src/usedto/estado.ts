// El mecanismo en cada cuadro, con física sencilla (caídas con gravedad, rebote, trinquete que engancha) y cada
// evento amarrado a la palabra de la voz que lo nombra.
import {ESCENAS, Wp, FPS, escenaEn, KEYS} from './timing';
import {clamp, lerp, prog} from '../anim';

export type V3 = [number, number, number];
// medidas del diorama (metros de maqueta)
export const M = {
  baseTop: 0.28, rielX: 0.47, rielTop: 3.3, poleaY: 3.47, arriba: 2.05, abajo: 0.3, alturaCoche: 0.8,
  dientePaso: 0.055, moderno: 2.9, // x del ascensor moderno, en la misma repisa
};
const G = 9.8 * 0.32; // gravedad de maqueta: la caída se ve pesada pero cabe en el plano
type Ev = {f: number; tipo: string; key: string};
export const EVENTOS: Ev[] = ESCENAS.flatMap((e) => (e.frase.efectos ?? []).filter((x) => x.evento).map((x) => ({f: Math.round(Wp(e.key, x.palabra)), tipo: x.evento!, key: e.key})));
const ev = (key: string, tipo: string) => EVENTOS.find((e) => e.key === key && e.tipo === tipo);
const versionEn = (f: number) => escenaEn(f).frase.version;
const inicioVersion = (f: number) => {
  const v = versionEn(f);
  let i = ESCENAS.indexOf(escenaEn(f));
  while (i > 0 && ESCENAS[i - 1].frase.version === v) i--;
  return ESCENAS[i].from;
};
/** caída libre desde y0 con rebote amortiguado al tocar fondo */
const caida = (dt: number, y0: number, suelo: number, g = G) => {
  const h = y0 - suelo, tImpacto = Math.sqrt((2 * h) / g);
  if (dt < tImpacto) return {y: y0 - 0.5 * g * dt * dt, v: g * dt, golpe: 0};
  const u = dt - tImpacto;
  return {y: suelo + Math.abs(Math.sin(u * 14)) * 0.05 * Math.exp(-u * 6), v: 0, golpe: Math.exp(-u * 8)};
};
/** el trinquete engancha en el diente de abajo más cercano */
const diente = (y: number) => Math.floor((y - M.baseTop) / M.dientePaso) * M.dientePaso + M.baseTop;

export const estado = (f: number) => {
  const v = versionEn(f);
  const e = escenaEn(f);
  let y = M.arriba, roto = 0, retroceso = 0, desgaste = 0, muelleAbierto = 0, tambor = 0, regulador = 0, bolas = 0, golpe = 0, sacudida = 0;
  const cuerda = v === 'cuerda' ? 'canamo' : v === 'alambre' ? 'alambre' : v === 'moderno' ? 'canamo' : 'alambre';
  const otis = ['otis', 'otis_feria', 'motor', 'regulador'].includes(v);
  const sombrero = v === 'otis_feria';
  const t0 = inicioVersion(f);
  // balanceo leve de la cabina colgando (vida en todos los planos)
  const balanceo = Math.sin(f / 21) * 0.006;
  if (v === 'cuerda' || v === 'alambre') {
    const k = v === 'cuerda' ? KEYS[1] : KEYS[3];
    const r = ev(k, 'rotura');
    const d = ev(k, 'desgaste');
    desgaste = v === 'cuerda' ? prog(f, 0, r ? r.f : 1, 'in') : d ? prog(f, d.f, r ? r.f : d.f + 30, 'in') : 0;
    if (r && f >= r.f) {
      const c = caida((f - r.f) / FPS, M.arriba, M.abajo);
      y = c.y; roto = 1; retroceso = prog(f, r.f, r.f + 8, 'out'); golpe = c.golpe;
    }
  } else if (otis) {
    const k = v === 'otis' ? KEYS[7] : v === 'otis_feria' ? KEYS[8] : v === 'motor' ? KEYS[11] : KEYS[13];
    const r = ev(k, 'rotura');
    if ((v === 'otis' || v === 'otis_feria') && r && f >= r.f) {
      roto = 1; retroceso = prog(f, r.f, r.f + 8, 'out');
      muelleAbierto = prog(f, r.f + 1, r.f + 5, 'out');
      const parada = diente(M.arriba - 0.09);
      const c = caida((f - r.f) / FPS, M.arriba, parada);
      y = c.y; golpe = c.golpe * 0.6;
    }
    const emb = ev(k, 'embalado');
    if (emb && f >= emb.f) {
      // el motor falla: la cabina baja cada vez más rápido CON la cuerda puesta (el muelle no salta)
      const dt = (f - emb.f) / FPS, a = G * 0.55;
      const fr = ev(k, 'freno');
      if (v === 'motor') {
        const c = caida(dt, M.arriba, M.abajo, a);
        y = c.y; golpe = c.golpe;
      } else if (fr) {
        const dtF = (fr.f - emb.f) / FPS;
        const yF = M.arriba - 0.5 * a * dtF * dtF;
        y = f < fr.f ? M.arriba - 0.5 * a * dt * dt : Math.max(diente(yF - 0.04), yF - 0.04 * prog(f, fr.f, fr.f + 3));
        muelleAbierto = prog(f, fr.f, fr.f + 4, 'out');
        bolas = Math.max(prog(f, ev(k, 'bolas')?.f ?? fr.f, fr.f, 'out'), 0);
      }
      tambor = (M.arriba - y) * 9;
    }
    regulador = v === 'regulador' ? (f - t0) * 0.35 + Math.max(0, (M.arriba - y)) * 26 : 0;
    if (v === 'regulador' && !emb) bolas = 0.15;
    if (v === 'regulador' && bolas < 0.15) bolas = 0.15 + 0.1 * Math.max(0, M.arriba - y);
  }
  // ascensor moderno: varios cables; se cortan de uno en uno y la cabina ni se mueve
  const cm = ev(KEYS[16], 'cortes_modernos');
  const cortes = !cm ? 0 : [Wp(KEYS[16], 'each'), Wp(KEYS[16], 'strong'), Wp(KEYS[16], 'hold')].filter((t) => f >= t).length;
  sacudida = golpe;
  return {v, y: y + (roto ? 0 : balanceo * 0.3), roto, retroceso, desgaste, cuerda, otis: otis && v !== 'moderno', muelleAbierto, sombrero, tambor, regulador, bolas, golpe, sacudida, cortes, mostrarRegulador: v === 'regulador', escena: e};
};
export type Estado = ReturnType<typeof estado>;
export const clampE = clamp;
export const lerpE = lerp;
