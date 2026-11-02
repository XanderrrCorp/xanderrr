// Subtítulos: Montserrat ExtraBold blanca en el tercio de abajo, por frases cortas sincronizadas con la voz,
// palabra a palabra con un pop suave; en AMARILLO las bisagras (But, So, Finally, Today), números, nombres y el
// nombre final. En los 2 últimos segundos, sin voz: «Follow for more Why It Used To».
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {ESCENAS, VO, FPS, TOTAL, GUION, CIERRE_S} from './timing';
import {SPEC, BISAGRAS, limpio} from './spec';
import {FUENTE} from './fuente';
import {clamp, prog, sp} from '../anim';

const S = SPEC.sub;
const RES = new Set(GUION.resaltar.map(limpio));
const amarilla = (w: string) => BISAGRAS.includes(limpio(w)) || RES.has(limpio(w)) || /\d/.test(w);
type Pal = {t: string; s: number; e: number};
const TROZOS: Pal[][] = ESCENAS.flatMap((sc) => {
  const out: Pal[][] = [];
  let cur: Pal[] = [], len = 0;
  VO[sc.key].words.forEach((w) => {
    const prev = cur[cur.length - 1];
    if (cur.length && (len + w.text.length > 18 || cur.length >= 4 || /[.,?!:]$/.test(prev.t))) { out.push(cur); cur = []; len = 0; }
    cur.push({t: w.text, s: sc.clipAt + w.start * FPS, e: sc.clipAt + w.end * FPS});
    len += w.text.length + 1;
  });
  if (cur.length) out.push(cur);
  return out;
});

const Subtitulos: React.FC<{f: number}> = ({f}) => {
  const k = TROZOS.findIndex((tr, i) => f >= tr[0].s - 2 && f < (TROZOS[i + 1]?.[0].s ?? tr[tr.length - 1].e + 12) - 2);
  if (k < 0) return null;
  const tr = TROZOS[k];
  if (f > tr[tr.length - 1].e + 14) return null;
  return (
    <div style={{position: 'absolute', top: S.y, left: 60, width: 960, textAlign: 'center', fontFamily: FUENTE, fontWeight: 800, fontSize: S.tam, lineHeight: 1.18}}>
      {tr.map((w, j) => {
        const a = sp(f, w.s - 2, 14, 0.5);
        const txt = w.t.replace(/[,:;]$/, '');
        return (
          <span key={j} style={{display: 'inline-block', margin: '0 11px', color: amarilla(w.t) ? S.amarillo : S.blanco, opacity: clamp(a * 1.6),
            transform: `translateY(${(1 - clamp(a)) * 14}px) scale(${0.92 + 0.08 * clamp(a, 0, 1.06)})`,
            textShadow: '0 4px 14px rgba(0,0,0,0.75), 0 0 3px rgba(0,0,0,0.9)'}}>{txt}</span>
        );
      })}
    </div>
  );
};

const Cierre: React.FC<{f: number}> = ({f}) => {
  const a = TOTAL - Math.round(CIERRE_S * FPS);
  if (f < a) return null;
  const inn = prog(f, a, a + 8, 'out'), out = prog(f, TOTAL - 6, TOTAL - 1, 'in');
  return (
    <div style={{position: 'absolute', top: 1390, width: 1080, display: 'flex', justifyContent: 'center', opacity: inn * (1 - out)}}>
      <div style={{fontFamily: FUENTE, fontWeight: 800, fontSize: 52, color: '#fff', padding: '18px 36px', borderRadius: 18,
        background: 'rgba(0,40,40,0.72)', border: `3px solid ${SPEC.color.oro}`, transform: `translateY(${(1 - inn) * 20}px)`}}>
        {SPEC.cierre}
      </div>
    </div>
  );
};

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (<><Subtitulos f={f} /><Cierre f={f} /></>);
};
