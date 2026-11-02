// Línea de tiempo de «Used To». Una toma de voz por FRASE (cada frase = un golpe visual). Los tiempos salen de la
// voz real (vo.json, de scripts/voz_usedto.py); sin voz grabada se ESTIMAN a ~160 palabras/min para ensayar gratis.
import guionJson from './guion.json';
import vo from './vo.json';
import {SPEC, limpio} from './spec';

export const FPS = SPEC.fps;
export type Efecto = {palabra: string; sfx?: string; evento?: string; retraso?: number};
export type Frase = {texto: string; version: string; tomas: string[]; efectos?: Efecto[]};
export const GUION = guionJson as unknown as {titulo: string; voz: {voice_id: string; speed: number}; resaltar: string[]; frases: Frase[]};
type Word = {text: string; start: number; end: number};
type Medida = {text: string; seconds: number; voiceStart: number; voiceEnd: number; words: Word[]};
const REAL = vo as unknown as Record<string, Medida>;
export const KEYS = GUION.frases.map((_, i) => `f${i + 1}`);

const estimar = (texto: string): Medida => {
  const palabras = texto.split(/\s+/).filter(Boolean);
  const peso = (p: string) => p.replace(/[^\p{L}\p{N}]/gu, '').length + 2.4;
  const pausa = (p: string) => (/^(but|so),$/i.test(p) ? SPEC.pausaTrasBisagra : /[.:?!]$/.test(p) ? 0.3 : /,$/.test(p) ? 0.14 : 0);
  const k = 0.358 / 7.1; // ~160 palabras/min con las pausas
  let t = 0.08;
  const words = palabras.map((p) => {
    const w = {text: p, start: +t.toFixed(3), end: +(t + peso(p) * k).toFixed(3)};
    t = w.end + pausa(p);
    return w;
  });
  const fin = words[words.length - 1].end;
  return {text: texto, seconds: fin + 0.12, voiceStart: 0.08, voiceEnd: fin, words};
};
export const ESTIMADO = KEYS.some((k) => !REAL[k]);
export const CON_VOZ = new Set(KEYS.filter((k) => REAL[k]));
export const VO: Record<string, Medida> = Object.fromEntries(KEYS.map((k, i) => [k, REAL[k] ?? estimar(GUION.frases[i].texto)]));

export type Escena = {key: string; i: number; from: number; dur: number; clipAt: number; frase: Frase};
export const ESCENAS: Escena[] = [];
/** segundos de cierre sin voz (texto «Follow for more…») para no romper el loop */
export const CIERRE_S = 2.0;
{
  let t = 0;
  GUION.frases.forEach((fr, i) => {
    const k = KEYS[i], m = VO[k];
    const lead = i === 0 ? 0.04 : 0.13;
    const tail = 0.2; // aire entre frases: deja la voz en 155–165 palabras/min
    const from = Math.round(t * FPS);
    const clipAt = Math.round((t + lead - m.voiceStart) * FPS);
    t += lead + (m.voiceEnd - m.voiceStart) + tail + (i === GUION.frases.length - 1 ? CIERRE_S : 0);
    ESCENAS.push({key: k, i, from, dur: Math.round(t * FPS) - from, clipAt, frase: fr});
  });
}
export const TOTAL = ESCENAS[ESCENAS.length - 1].from + ESCENAS[ESCENAS.length - 1].dur;
export const W = (key: string, n: number) => {
  const e = ESCENAS.find((x) => x.key === key)!;
  return e.clipAt + VO[key].words[Math.min(n, VO[key].words.length - 1)].start * FPS;
};
export const Wp = (key: string, palabra: string) => {
  const ws = VO[key].words;
  const n = ws.findIndex((w) => limpio(w.text) === limpio(palabra));
  if (n < 0) throw new Error(`«${palabra}» no está en ${key}: ${ws.map((w) => w.text).join(' ')}`);
  return W(key, n);
};
export const finVoz = (key: string) => {
  const e = ESCENAS.find((x) => x.key === key)!;
  return e.clipAt + VO[key].voiceEnd * FPS;
};
const habla = (f: number) => ESCENAS.some((s) => f >= s.clipAt + VO[s.key].voiceStart * FPS - 3 && f <= s.clipAt + VO[s.key].voiceEnd * FPS + 3);
const HABLA = Array.from({length: TOTAL + 20}, (_, f) => (habla(f) ? 1 : 0));
export const vozEn = (f: number) => {
  let n = 0;
  for (let k = -6; k <= 6; k++) n += HABLA[Math.max(0, Math.min(HABLA.length - 1, Math.round(f) + k))];
  return n / 13;
};
export const escenaEn = (f: number) => {
  for (let i = ESCENAS.length - 1; i >= 0; i--) if (f >= ESCENAS[i].from) return ESCENAS[i];
  return ESCENAS[0];
};
