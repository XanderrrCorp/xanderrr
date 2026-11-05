// MONTAJE compartido de «En este pueblo…»: tiempos de la voz (reales o estimados a ~175 palabras/min), escenas
// = tomas entre [corchetes], cortes cada 1–2 s amarrados a las palabras, y una cámara FIJA por plano (se turnan
// los encuadres de la escena; nunca dos iguales seguidos).
import {SPEC, limpio} from './spec';
import type {Episodio, Linea, Ctx, Cam} from './tipos';

const FPS = SPEC.fps;
type Word = {text: string; start: number; end: number};
type Medida = {text: string; seconds: number; voiceStart: number; voiceEnd: number; words: Word[]};
const estimar = (texto: string): Medida => {
  const ps = texto.replace(/—/g, '').split(/\s+/).filter(Boolean);
  const peso = (p: string) => p.replace(/[^\p{L}\p{N}]/gu, '').length + 2.2;
  const pausa = (p: string) => (/[.…:?!»]$/.test(p) ? 0.22 : /,$/.test(p) ? 0.1 : 0);
  const k = 0.357 / 7.4; // ~175 palabras/min con el aire entre líneas
  let t = 0.05;
  const words = ps.map((p) => { const w = {text: p, start: +t.toFixed(3), end: +(t + peso(p) * k).toFixed(3)}; t = w.end + pausa(p); return w; });
  const fin = words[words.length - 1].end;
  return {text: texto, seconds: fin + 0.08, voiceStart: 0.05, voiceEnd: fin, words};
};
export type LineaT = Linea & {i: number; from: number; to: number; clipAt: number; m: Medida; real: boolean};
export type Plano = {n: number; from: number; to: number; escena: string; cam: Cam; camIdx: number; linea: string; golpeDesde?: number};
export type Montaje = ReturnType<typeof montar>;

const CACHE = new Map<string, ReturnType<typeof montarSinCache>>();
export const montar = (ep: Episodio) => {
  if (!CACHE.has(ep.id)) CACHE.set(ep.id, montarSinCache(ep));
  return CACHE.get(ep.id)!;
};
const montarSinCache = (ep: Episodio) => {
  const REAL = ep.vo as Record<string, Medida>;
  // 1) líneas en el tiempo: sin pausas largas (aire corto entre líneas, un poco más al cambiar de escena)
  let t = 0;
  const L: LineaT[] = ep.guion.lineas.map((l, i) => {
    const m = REAL[l.id] ?? estimar(l.texto);
    const cambio = i > 0 && ep.guion.lineas[i - 1].escena !== l.escena;
    const lead = i === 0 ? 0.03 : cambio ? 0.12 : 0.06;
    const tail = i === ep.guion.lineas.length - 1 ? 0.6 : 0.08;
    const from = Math.round(t * FPS);
    const clipAt = Math.round((t + lead - m.voiceStart) * FPS);
    t += lead + (m.voiceEnd - m.voiceStart) + tail;
    return {...l, i, from, to: Math.round(t * FPS), clipAt, m, real: !!REAL[l.id]};
  });
  const CTA_S = 3.0; // saludo final + íconos con rebote
  const TOTAL = L[L.length - 1].to + Math.round(CTA_S * FPS);
  L[L.length - 1].to = TOTAL;
  const linea = (id: string) => {
    const x = L.find((q) => q.id === id);
    if (!x) throw new Error(`no hay línea ${id}`);
    return x;
  };
  const W = (id: string, palabra?: string | number) => {
    const x = linea(id);
    if (palabra === undefined) return x.clipAt + x.m.voiceStart * FPS;
    const n = typeof palabra === 'number' ? palabra : x.m.words.findIndex((w) => limpio(w.text) === limpio(palabra));
    if (n < 0) throw new Error(`«${palabra}» no está en ${id}: ${x.texto}`);
    return Math.round(x.clipAt + x.m.words[Math.min(n, x.m.words.length - 1)].start * FPS);
  };
  // 2) escenas = tramos de líneas seguidas con la misma escena
  const esc: {id: string; from: number; to: number}[] = [];
  L.forEach((l) => {
    const u = esc[esc.length - 1];
    if (u && u.id === l.escena) u.to = l.to; else esc.push({id: l.escena, from: l.from, to: l.to});
  });
  // 3) planos: el mejor juego de cortes por escena (en inicios de palabra, prefiriendo inicios de línea)
  const coste = (d: number) => {
    const s = d / FPS;
    if (s > SPEC.planoMax + 1e-6 || s < 0.7) return Infinity;
    const fuera = s < SPEC.planoMin ? SPEC.planoMin - s : 0;
    return fuera * fuera * 30 + Math.abs(s - SPEC.planoIdeal) * 0.3;
  };
  const planos: Plano[] = [];
  esc.forEach((e) => {
    const cand: {f: number; inicio: boolean}[] = [{f: e.from, inicio: true}];
    L.filter((l) => l.escena === e.id && l.from >= e.from && l.to <= e.to).forEach((l, k) => {
      l.m.words.forEach((_, w) => {
        const c = W(l.id, w) - 2;
        if (c > e.from + 10 && c < e.to - 10) cand.push({f: c, inicio: w === 0});
      });
    });
    // tras la última palabra (el cierre con los íconos) también se puede cortar, cada ~1,5 s
    const ultima = L.filter((l) => l.escena === e.id).pop();
    if (ultima) for (let c = Math.round(ultima.clipAt + ultima.m.voiceEnd * FPS) + 20; c < e.to - 20; c += 45) cand.push({f: c, inicio: false});
    cand.sort((a, b) => a.f - b.f);
    cand.push({f: e.to, inicio: true});
    const best = cand.map(() => Infinity), prev = cand.map(() => -1);
    best[0] = 0;
    for (let j = 1; j < cand.length; j++) for (let i = 0; i < j; i++) {
      const c = best[i] + coste(cand[j].f - cand[i].f) - (cand[j].inicio ? 0.25 : 0);
      if (c < best[j]) { best[j] = c; prev[j] = i; }
    }
    let marcas: number[] = [];
    if (isFinite(best[cand.length - 1])) {
      for (let j = cand.length - 1; j >= 0; j = prev[j]) { marcas.unshift(cand[j].f); if (j === 0) break; }
    } else marcas = [e.from, e.to]; // escena demasiado corta: un solo plano
    const cams = ep.escenas[e.id]?.camaras;
    if (!cams) throw new Error(`escena sin definir: ${e.id}`);
    for (let q = 0; q + 1 < marcas.length; q++) {
      const idx = q % cams.length;
      const ln = [...L].reverse().find((l) => l.from <= marcas[q]) ?? L[0];
      planos.push({n: planos.length, from: marcas[q], to: marcas[q + 1], escena: e.id, cam: cams[idx], camIdx: idx, linea: ln.id});
    }
  });
  // golpes: punch-in del 5 % desde la palabra hasta el final del plano
  L.forEach((l) => {
    if (!l.golpe) return;
    const g = W(l.id, l.golpe);
    const p = planos.find((x) => g >= x.from && g < x.to);
    if (p) p.golpeDesde = g;
  });
  const planoEn = (f: number) => {
    for (let i = planos.length - 1; i >= 0; i--) if (f >= planos[i].from) return planos[i];
    return planos[0];
  };
  const escenaEn = (f: number) => {
    for (let i = esc.length - 1; i >= 0; i--) if (f >= esc[i].from) return esc[i];
    return esc[0];
  };
  const ctx = (f: number): Ctx => {
    const e = escenaEn(f);
    return {
      f, f0: e.from, f1: e.to, u: Math.min(1, Math.max(0, (f - e.from) / Math.max(1, e.to - e.from))), W,
      desde: (id, palabra, dur = 8) => Math.min(1, Math.max(0, (f - W(id, palabra)) / dur)),
    };
  };
  const habla = Array.from({length: TOTAL + 20}, (_, f) => (L.some((l) => f >= l.clipAt + l.m.voiceStart * FPS - 3 && f <= l.clipAt + l.m.voiceEnd * FPS + 3) ? 1 : 0));
  const vozEn = (f: number) => {
    let n = 0;
    for (let k = -6; k <= 6; k++) n += habla[Math.max(0, Math.min(habla.length - 1, Math.round(f) + k))];
    return n / 13;
  };
  const lineaEn = (f: number) => [...L].reverse().find((l) => f >= l.from) ?? L[0];
  return {L, TOTAL, W, linea, planos, planoEn, escenas: esc, escenaEn, ctx, vozEn, lineaEn, estimado: L.some((l) => !l.real), CTA_S};
};
