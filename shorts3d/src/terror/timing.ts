// Línea de tiempo del Short de terror. Los cortes salen de la VOZ REAL (vo.json, que escribe
// scripts/voz_terror.py). Mientras no haya voz grabada, cada línea se ESTIMA a 2,7 palabras/s
// para poder ensayar el montaje sin pagar nada; la composición dice cuál de los dos usa.
import guionJson from './guion.json';
import vo from './vo.json';
import {SPEC} from './spec';

export const FPS = SPEC.fps;
export type Efecto = {palabra: string; sfx?: string; shake?: number; rayo?: boolean; stinger?: boolean};
export type Toma = {tipo: string; foco: string};
export type Frase = {texto: string; etiqueta?: string; efectos?: Efecto[]; tomas: Toma[]};
export type Linea = {key: string; giro?: boolean; cta?: boolean; cola?: number; frases: Frase[]};
export const GUION = guionJson as unknown as {titulo: string; voz: {voice_id: string; speed: number}; lineas: Linea[]};
type Word = {text: string; start: number; end: number};
type Medida = {text: string; seconds: number; voiceStart: number; voiceEnd: number; words: Word[]};
const REAL = vo as unknown as Record<string, Medida>;
export const textoDe = (l: Linea) => l.frases.map((f) => f.texto).join(' ');

/** misma cadencia que pide la ficha: palabras de largo medio a 2,7 por segundo, con las pausas de la puntuación */
const estimar = (texto: string): Medida => {
  const palabras = texto.split(/\s+/).filter(Boolean);
  const peso = (p: string) => p.replace(/[^\p{L}\p{N}]/gu, '').length + 2.2;
  const pausa = (p: string) => (/[.…:?!»]$/.test(p) ? 0.34 : /,$/.test(p) ? 0.16 : 0);
  const k = 0.335 / 7.4; // una palabra media (5,2 letras) dura ~0,33 s: con las pausas sale ~2,7 palabras/s
  let t = 0.1;
  const words = palabras.map((p) => {
    const w = {text: p, start: +t.toFixed(3), end: +(t + peso(p) * k).toFixed(3)};
    t = w.end + pausa(p);
    return w;
  });
  const fin = words[words.length - 1].end;
  return {text: texto, seconds: fin + 0.15, voiceStart: 0.1, voiceEnd: fin, words};
};
export const ESTIMADO = GUION.lineas.some((l) => !REAL[l.key]);
export const VO: Record<string, Medida> = Object.fromEntries(GUION.lineas.map((l) => [l.key, REAL[l.key] ?? estimar(textoDe(l))]));

export type Escena = {key: string; i: number; from: number; dur: number; clipAt: number; linea: Linea};
export const ESCENAS: Escena[] = [];
{
  let t = 0;
  GUION.lineas.forEach((l, i) => {
    const m = VO[l.key];
    const lead = (i === 0 ? 0.05 : 0.12) + (l.giro ? SPEC.pausaAntesDelGiro : 0);
    const tail = (i === GUION.lineas.length - 1 ? 0.12 : 0.18) + (l.cola ?? 0); // «cola»: aire extra tras un golpe
    const from = Math.round(t * FPS);
    const clipAt = Math.round((t + lead - m.voiceStart) * FPS);
    t += lead + (m.voiceEnd - m.voiceStart) + tail;
    ESCENAS.push({key: l.key, i, from, dur: Math.round(t * FPS) - from, clipAt, linea: l});
  });
}
export const TOTAL = ESCENAS[ESCENAS.length - 1].from + ESCENAS[ESCENAS.length - 1].dur;
const esc = (key: string) => ESCENAS.find((e) => e.key === key)!;
/** cuadro global donde empieza la palabra n de la línea */
export const W = (key: string, n: number) => esc(key).clipAt + VO[key].words[Math.min(n, VO[key].words.length - 1)].start * FPS;
/** índice de la palabra dentro de la línea, buscándola por su texto a partir de la palabra `desde` */
export const idx = (key: string, palabra: string, desde = 0) => {
  const n = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}]/gu, '').toLowerCase();
  const ws = VO[key].words;
  for (let k = desde; k < ws.length; k++) if (n(ws[k].text) === n(palabra)) return k;
  throw new Error(`«${palabra}» no está en ${key}: ${ws.map((w) => w.text).join(' ')}`);
};
export const Wp = (key: string, palabra: string, desde = 0) => W(key, idx(key, palabra, desde));
/** cuadro donde termina de hablar la línea */
export const finVoz = (key: string) => esc(key).clipAt + VO[key].voiceEnd * FPS;
export const escenaDe = (key: string) => esc(key);
/** frases con su primera palabra (índice en la línea) */
export const FRASES = GUION.lineas.flatMap((l) => {
  let n = 0;
  return l.frases.map((f, j) => {
    const desde = n;
    n += f.texto.split(/\s+/).filter(Boolean).length;
    return {linea: l, j, frase: f, desde, hasta: n};
  });
});
/** la voz suena en el cuadro f (0..1, suavizado) */
const habla = (f: number) => ESCENAS.some((s) => {
  const m = VO[s.key];
  return f >= s.clipAt + m.voiceStart * FPS - 3 && f <= s.clipAt + m.voiceEnd * FPS + 3;
});
const HABLA = Array.from({length: TOTAL + 20}, (_, f) => (habla(f) ? 1 : 0));
export const vozEn = (f: number) => {
  let n = 0;
  for (let k = -6; k <= 6; k++) n += HABLA[Math.max(0, Math.min(HABLA.length - 1, Math.round(f) + k))];
  return n / 13;
};
export const GIRO = ESCENAS.find((e) => e.linea.giro);
/** cuadro del giro: arranca la primera palabra de la línea marcada con "giro" */
export const CUADRO_GIRO = GIRO ? W(GIRO.key, 0) : -1;
/** líneas que ya tienen voz grabada y medida (las demás van estimadas y en silencio) */
export const CON_VOZ = new Set(GUION.lineas.filter((l) => REAL[l.key]).map((l) => l.key));
