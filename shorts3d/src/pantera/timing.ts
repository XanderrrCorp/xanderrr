// Línea de tiempo única: los cortes salen de la duración REAL de cada frase (vo.json).
import vo from './vo.json';
export const FPS = 30;
export const KEYS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7'] as const;
export type VoKey = (typeof KEYS)[number];
type Word = {text: string; start: number; end: number};
type Line = {text: string; seconds: number; voiceStart: number; voiceEnd: number; words: Word[]};
export const VO = vo as unknown as Record<VoKey, Line>;
const LEAD = [0.08, 0.25, 0.25, 0.25, 0.25, 0.3, 0.25]; // el gancho arranca casi en el cuadro 0
const TAIL = [0.2, 0.3, 0.35, 0.4, 0.45, 0.55, 0.2]; // ritmo rápido; la última corta justo para el loop
export type Scene = {key: VoKey; from: number; dur: number; clipAt: number};
export const SCENES: Scene[] = [];
{
  let t = 0;
  KEYS.forEach((k, i) => {
    const l = VO[k];
    const secs = LEAD[i] + (l.voiceEnd - l.voiceStart) + TAIL[i];
    const from = Math.round(t * FPS);
    const clipAt = Math.round((t + LEAD[i] - l.voiceStart) * FPS); // cuadro global donde arranca el audio de la frase
    t += secs;
    SCENES.push({key: k, from, dur: Math.round(t * FPS) - from, clipAt});
  });
}
export const TOTAL = SCENES[SCENES.length - 1].from + SCENES[SCENES.length - 1].dur;
export const sc = (i: number) => SCENES[i];
/** cuadro global en una fracción de la escena i */
export const at = (i: number, frac: number) => SCENES[i].from + frac * SCENES[i].dur;
/** cuadro global donde EMPIEZA la palabra n (0 = primera) de la frase de la escena i */
export const W = (i: number, n: number) => SCENES[i].clipAt + VO[SCENES[i].key].words[n].start * FPS;
/** cuadro global donde TERMINA la frase de la escena i */
export const voEnd = (i: number) => SCENES[i].clipAt + VO[SCENES[i].key].voiceEnd * FPS;
export const sceneAt = (f: number) => {
  for (let i = SCENES.length - 1; i >= 0; i--) if (f >= SCENES[i].from) return i;
  return 0;
};
