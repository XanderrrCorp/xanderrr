// Capa 2D: niebla y partículas en exteriores, destello del rayo, etiqueta de personaje/lugar arriba,
// subtítulos palabra por palabra (números en naranja y más grandes, palabras de peligro en rojo) y el CTA.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {ESCENAS, VO, FPS, TOTAL} from './timing';
import {PLANOS, planoEn} from './planos';
import {estado} from './estado';
import {SPEC, tipoDe} from './spec';
import {clamp, lerp, prog, rnd, sp} from '../anim';

import {continueRender, delayRender} from 'remotion';
import archivo from './fuentes/ArchivoBlack-Regular.ttf';

// fuente gruesa de los subtítulos, cargada antes del primer cuadro (si no, Chrome pinta la de respaldo)
const FONT = '"Archivo Black", "Arial Black", Impact, sans-serif';
if (typeof document !== 'undefined') {
  const espera = delayRender('fuente de los subtítulos');
  const ff = new FontFace('Archivo Black', `url(${archivo})`);
  ff.load().then((f) => { document.fonts.add(f); continueRender(espera); }).catch(() => continueRender(espera));
}
const S = SPEC.sub;

// ---------- niebla animada (exteriores de noche) ----------
export const Niebla: React.FC<{f: number}> = ({f}) => {
  const p = planoEn(f);
  const fuera = p.lugar === 'fuera' || p.tipo === 'ventana';
  if (!fuera) return null;
  const capas = Array.from({length: 6}, (_, i) => {
    const x = ((rnd(i, 1) * 1400 + f * (0.6 + rnd(i, 2) * 1.4)) % 1700) - 300;
    const y = 900 + rnd(i, 3) * 900;
    return <div key={i} style={{position: 'absolute', left: x - 500, top: y - 260, width: 1000, height: 520, borderRadius: '50%',
      background: `radial-gradient(ellipse at center, rgba(150,165,190,${0.16 + rnd(i, 4) * 0.12}) 0%, rgba(150,165,190,0) 70%)`, filter: 'blur(18px)'}} />;
  });
  const motas = Array.from({length: 46}, (_, i) => {
    const x = (rnd(i, 5) * 1080 + Math.sin(f / 40 + i) * 40 + f * 0.4 * (rnd(i, 6) - 0.3)) % 1080;
    const y = (rnd(i, 7) * 1920 + f * (0.5 + rnd(i, 8))) % 1920;
    const r = 2 + rnd(i, 9) * 4;
    return <div key={'m' + i} style={{position: 'absolute', left: x, top: y, width: r, height: r, borderRadius: r, background: 'rgba(220,230,255,0.55)', filter: 'blur(1px)'}} />;
  });
  return <div style={{position: 'absolute', inset: 0, overflow: 'hidden', mixBlendMode: 'screen'}}>{capas}{motas}</div>;
};

// ---------- etiqueta de personaje o lugar ----------
const Etiqueta: React.FC<{f: number}> = ({f}) => {
  const p = [...PLANOS].reverse().find((q) => q.etiqueta && f >= q.from && f < q.from + 2.2 * FPS);
  if (!p) return null;
  const inn = sp(f, p.from + 1, 13, 0.5), out = prog(f, p.from + 1.9 * FPS, p.from + 2.2 * FPS, 'in');
  return (
    <div style={{position: 'absolute', top: 170, width: 1080, display: 'flex', justifyContent: 'center'}}>
      <div style={{fontFamily: FONT, fontSize: 40, letterSpacing: 4, color: '#fff', padding: '12px 28px', borderRadius: 10,
        background: 'rgba(8,12,24,0.72)', borderLeft: `8px solid ${SPEC.color.ventana}`, opacity: clamp(inn) * (1 - out),
        transform: `translateY(${(1 - clamp(inn)) * -24}px)`}}>{p.etiqueta}</div>
    </div>
  );
};

// ---------- subtítulos palabra por palabra ----------
type Pal = {t: string; s: number; e: number};
const TROZOS: Pal[][] = ESCENAS.flatMap((sc) => {
  const out: Pal[][] = [];
  let cur: Pal[] = [], len = 0;
  VO[sc.key].words.forEach((w) => {
    const t = w.text.replace(/[«»"]/g, '');
    const prev = cur[cur.length - 1];
    if (cur.length && (len + t.length > 13 || cur.length >= 3 || /[.,…?!:]$/.test(prev.t))) { out.push(cur); cur = []; len = 0; }
    cur.push({t, s: sc.clipAt + w.start * FPS, e: sc.clipAt + w.end * FPS});
    len += t.length + 1;
  });
  if (cur.length) out.push(cur);
  return out;
});
const Subtitulos: React.FC<{f: number}> = ({f}) => {
  const k = TROZOS.findIndex((tr, i) => f >= tr[0].s - 1 && f < (TROZOS[i + 1]?.[0].s ?? tr[tr.length - 1].e + 10) - 1);
  if (k < 0) return null;
  const tr = TROZOS[k];
  if (f > tr[tr.length - 1].e + 12) return null;
  return (
    <div style={{position: 'absolute', top: S.y, left: 40, width: 1000, textAlign: 'center', lineHeight: 1.12, fontFamily: FONT}}>
      {tr.map((w, j) => {
        const visto = f >= w.s - 1;
        const tipo = tipoDe(w.t);
        const ahora = visto && (j === tr.length - 1 || f < tr[j + 1].s - 1);
        const pop = ahora ? 1 + 0.16 * Math.max(0, 1 - (f - w.s) / 4) : 1;
        const tam = tipo === 'numero' ? S.tamNumero : S.tam;
        const txt = w.t.replace(/[.,:;]$/, '').toUpperCase();
        const color = tipo === 'numero' ? S.numero : tipo === 'peligro' ? S.peligro : S.blanco;
        return (
          <span key={j} style={{display: 'inline-block', position: 'relative', margin: '0 14px', fontSize: tam, opacity: visto ? 1 : 0,
            transform: `scale(${pop}) rotate(${tipo === 'peligro' && ahora ? Math.sin(f * 2.3) * 2 : 0}deg)`, verticalAlign: 'middle'}}>
            {/* contorno negro grueso detrás y el relleno encima (paint-order no sirve en texto HTML) */}
            <span style={{position: 'absolute', left: 0, top: 0, color: S.contorno, WebkitTextStroke: `${S.trazo * 2}px ${S.contorno}`, textShadow: '0 10px 24px rgba(0,0,0,0.8)'}}>{txt}</span>
            <span style={{position: 'relative', color}}>{txt}</span>
          </span>
        );
      })}
    </div>
  );
};

// ---------- CTA (mientras la cosa mira a cámara) ----------
const CTA: React.FC<{f: number}> = ({f}) => {
  const cta = ESCENAS.find((e) => e.linea.cta);
  if (!cta || f < cta.from) return null;
  const inn = sp(f, cta.from + 2, 11, 0.6);
  const late = 1 + 0.05 * Math.sin((f - cta.from) / 3.5);
  return (
    <div style={{position: 'absolute', top: 1560, width: 1080, display: 'flex', justifyContent: 'center', transform: `scale(${clamp(inn, 0, 1.15) * late})`}}>
      <div style={{fontFamily: FONT, fontSize: 56, color: '#fff', background: '#c4161c', padding: '18px 40px', borderRadius: 18, letterSpacing: 2,
        boxShadow: '0 0 40px rgba(255,40,40,0.55), 0 12px 30px rgba(0,0,0,0.5)', border: '5px solid #fff'}}>SÍGUEME · PARTE 2</div>
    </div>
  );
};

export const Destello: React.FC<{f: number}> = ({f}) => {
  const r = estado(f).rayo;
  return r > 0.01 ? <div style={{position: 'absolute', inset: 0, background: `rgba(225,235,255,${0.75 * r})`}} /> : null;
};

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,10,0.55) 100%)'}} />
      <Etiqueta f={f} />
      <Subtitulos f={f} />
      <CTA f={f} />
    </>
  );
};
export {TOTAL, lerp};
