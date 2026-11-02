// Qué pasa en la historia en cada cuadro: dónde está cada personaje y qué hace. Todo amarrado a la voz.
import {FRASES, Wp, W, escenaDe, ESCENAS, TOTAL, Efecto} from './timing';
import {V3, lerp, prog, clamp} from '../anim';

export const EFECTOS: (Efecto & {f: number})[] = FRASES.flatMap(({linea, frase, desde}) =>
  (frase.efectos ?? []).map((e) => ({...e, f: Math.round(Wp(linea.key, e.palabra, desde))})));
const desdeLinea = (key: string) => escenaDe(key).from;
const golpes = EFECTOS.filter((e) => e.sfx === 'golpe').map((e) => e.f);
const rayos = EFECTOS.filter((e) => e.rayo).map((e) => e.f);

// lugares (metros). La casa de Tomás mira a +z; su ventana está en la pared z = 2.
export const L = {
  ventana: [0, 1.5, 2] as V3,
  cerrojo: [0.5, 1.3, 1.93] as V3,
  cama: [-1.35, 0, -0.9] as V3,
  junto: [0, 0, 1.2] as V3,
  reloj: [-2.33, 2.0, -0.4] as V3,
  fuera: [0.15, 0, 3.75] as V3, // la cosa pegada a la ventana
  calle: [0, 0, 7.2] as V3, // la cosa en medio de la calle (plano final)
  vecinos: [8, 0, 0] as V3,
  cementerio: [-14, 0, 7] as V3,
};
export type Estado = ReturnType<typeof estado>;
const pulso = (f: number, ts: number[], a = 2, b = 7) => ts.reduce((m, t) => Math.max(m, f >= t - a && f < t + b ? (f < t ? (f - t + a) / a : 1 - (f - t) / b) : 0), 0);

export const estado = (f: number) => {
  const s7 = escenaDe('s7'), s9 = escenaDe('s9'), s11 = escenaDe('s11'), s12 = escenaDe('s12'), s13 = escenaDe('s13'), s3 = escenaDe('s3');
  // Tomás: sentado en la cama hasta que se acerca a la ventana (s7)
  const camina = prog(f, s7.from + 4, Wp('s7', 'ventana.') + 4, 'inOut');
  const tomas = {
    pos: [lerp(L.cama[0] + 0.55, L.junto[0], camina), 0, lerp(L.cama[2] + 0.3, L.junto[2], camina)] as V3,
    yaw: lerp(0.35, 0, camina),
    sentado: 1 - prog(f, s7.from, s7.from + 10, 'inOut'),
    paso: camina > 0 && camina < 1 ? (f - s7.from) * 0.5 : 0,
    mano: prog(f, Wp('s7', 'mano'), Wp('s7', 'cerrojo.') + 4, 'inOut') * (1 - prog(f, s9.from + 10, s9.from + 18)),
    miedo: f >= s3.from ? 1 : 0,
    boca: f >= W('s9', 0) - 1 ? 1 : 0,
  };
  // la madre aparece detrás de él en el giro
  const madre = {visible: f >= W('s9', 0) - 2 && f < s12.from, pos: [0.1, 0, 0.62] as V3, mano: prog(f, W('s9', 0) - 2, W('s9', 0) + 2, 'out')};
  // la cosa
  const enVentana = f >= s3.from && f < s12.from;
  const agachada = f < escenaDe('s5').from ? 1 : f < escenaDe('s6').from ? 0 : 1; // en s5 se ve entera, de pie
  const monstruo = {
    visible: enVentana || f >= s13.from,
    pos: (f >= s13.from ? L.calle : agachada ? L.fuera : [0.35, 0, 4.3]) as V3,
    yaw: f >= s13.from ? 0 : Math.PI, // de cara a la casa o de cara a la cámara final
    agacha: f >= s13.from ? 0.15 : agachada * (0.85 + 0.05 * Math.sin(f / 14)),
    golpe: pulso(f, golpes),
    sonrisa: f >= s13.from ? 1 : prog(f, Wp('s11', 'sonrió.') - 2, Wp('s11', 'sonrió.') + 8, 'out'),
    respira: Math.sin(f / 11),
  };
  const rayo = pulso(f, rayos, 1, 10) * (0.6 + 0.4 * Math.abs(Math.sin(f * 1.7)));
  return {tomas, madre, monstruo, rayo, dia: f >= s12.from && f < s13.from ? 1 : 0, vecinosAbierta: f >= s12.from && f < s13.from, f, TOTAL, desdeLinea, ESCENAS};
};
export const clampEstado = clamp;
