// Capa 2D: insignias, subtítulos palabra por palabra, rótulos anclados al 3D y llamado al video completo.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {SCENES, VO, W, at, FPS, TOTAL} from './timing';
import {clamp, prog, sp, lerp} from '../anim';
import {project, LOOP} from './Mundo';
import {cen} from './Mapa';

const FONT = 'Inter, "Inter Display", sans-serif';
type Variant = 'pos' | 'neg' | 'info' | 'warn';
const VC: Record<Variant, {bg: string; ic: string}> = {
  pos: {bg: '#1f9d55', ic: '✔'},
  neg: {bg: '#d6332a', ic: '✖'},
  info: {bg: '#1f6fd6', ic: 'i'},
  warn: {bg: '#f2b705', ic: '?'},
};
type Badge = {text: string; v: Variant; from: number; to: number};
const end = (i: number) => SCENES[i].from + SCENES[i].dur;
const BADGES: Badge[] = [
  {text: '¿Y EL TUYO?', v: 'warn', from: W(1, 0), to: end(1) + 4},
  {text: 'RANA DORADA', v: 'info', from: W(2, 5), to: W(2, 15) - 2},
  {text: 'VENENO EN LA PIEL', v: 'neg', from: W(2, 15), to: end(2) - 2},
  {text: 'ESCORPIÓN', v: 'info', from: W(3, 4), to: W(3, 14) - 2},
  {text: 'EMERGENCIA', v: 'neg', from: W(3, 14), to: end(3) - 2},
  {text: 'SE ESCONDE', v: 'warn', from: W(5, 6), to: W(5, 16) - 2},
  {text: 'MÁS MORDEDURAS', v: 'neg', from: W(5, 16), to: end(5) - 2},
];

const Icon: React.FC<{v: Variant}> = ({v}) => {
  const c = '#fff';
  const svg: Record<Variant, React.ReactNode> = {
    pos: <path d="M12 26 L22 36 L40 16" stroke={c} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />,
    neg: <path d="M15 15 L37 37 M37 15 L15 37" stroke={c} strokeWidth={7} strokeLinecap="round" />,
    info: <><circle cx={26} cy={14} r={4} fill={c} /><rect x={22.5} y={21} width={7} height={19} rx={3} fill={c} /></>,
    warn: <text x={26} y={40} textAnchor="middle" fontFamily={FONT} fontWeight={900} fontSize={38} fill="#3a2a00">?</text>,
  };
  return (
    <svg width={52} height={52} viewBox="0 0 52 52" style={{flex: 'none'}}>
      <circle cx={26} cy={26} r={26} fill={v === 'warn' ? '#fff3c0' : 'rgba(0,0,0,0.22)'} />
      {svg[v]}
    </svg>
  );
};

const Badges: React.FC<{f: number}> = ({f}) => {
  const act = BADGES.filter((b) => f >= b.from - 1 && f < b.to + 8);
  return (
    <div style={{position: 'absolute', top: 262, left: 0, width: 1080, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18}}>
      {act.map((b) => {
        const inn = sp(f, b.from, 11, 0.5);
        const out = prog(f, b.to, b.to + 8, 'in');
        const sc = lerp(0.55, 1, clamp(inn, 0, 1.15)) * (inn > 1 ? 1 + (inn - 1) * 0.6 : 1);
        return (
          <div key={b.text} style={{
            display: 'flex', alignItems: 'center', gap: 18, padding: '18px 34px 18px 20px', borderRadius: 60,
            background: VC[b.v].bg, color: b.v === 'warn' ? '#2a1d00' : '#fff', fontFamily: FONT, fontWeight: 900, fontSize: 46,
            letterSpacing: 1, boxShadow: '0 10px 30px rgba(0,0,0,0.35)', transform: `scale(${sc}) translateY(${-out * 30}px)`,
            opacity: clamp(inn * 1.5) * (1 - out), whiteSpace: 'nowrap',
          }}>
            <Icon v={b.v} />
            {b.text}
          </div>
        );
      })}
    </div>
  );
};

// ---- subtítulos ----
const HL: Record<string, string[]> = {
  s1: ['COLOMBIA', 'MATARTE'], s2: ['TUYO'], s3: ['CAUCA', 'RANA', 'DORADA', 'VENENO', 'DIEZ'], s4: ['TOLIMA', 'ESCORPIÓN', 'EMERGENCIA', 'NIÑOS'],
  s5: ['PELIGROSO', 'SUSCRÍBETE'], s6: ['ANTIOQUIA', 'VÍBORA', 'ESCONDE', 'MORDEDURAS'], s7: ['DEPARTAMENTO'], s8: ['VIDEO', 'COMPLETO'],
};
const RED = new Set(['MATARTE', 'VENENO', 'EMERGENCIA', 'MORDEDURAS', 'PELIGROSO']);
const GREEN = new Set(['SUSCRÍBETE']);
const clean = (w: string) => w.replace(/[^\p{L}\p{N}]/gu, '').toUpperCase();
type Chunk = {words: {t: string; s: number; e: number}[]};
const chunks = (i: number): Chunk[] => {
  const sc = SCENES[i], l = VO[sc.key];
  const out: Chunk[] = [];
  let cur: Chunk = {words: []}, len = 0;
  l.words.forEach((w) => {
    const t = w.text.replace('…', '…');
    if (cur.words.length && (len + t.length + 1 > 15 || /[.,…?]$/.test(cur.words[cur.words.length - 1].t))) {
      out.push(cur);
      cur = {words: []};
      len = 0;
    }
    cur.words.push({t, s: sc.clipAt + w.start * FPS, e: sc.clipAt + w.end * FPS});
    len += t.length + 1;
  });
  if (cur.words.length) out.push(cur);
  return out;
};
const ALL = SCENES.map((_, i) => ({i, ch: chunks(i)}));

const Captions: React.FC<{f: number}> = ({f}) => {
  let found: {ch: Chunk; key: string} | null = null;
  for (const {i, ch} of ALL) {
    for (let k = 0; k < ch.length; k++) {
      const a = ch[k].words[0].s, nxt = ch[k + 1]?.words[0].s ?? ch[k].words[ch[k].words.length - 1].e + 8;
      if (f >= a - 1 && f < nxt) found = {ch: ch[k], key: SCENES[i].key};
    }
  }
  if (!found) return null;
  const hl = HL[found.key];
  return (
    <div style={{position: 'absolute', top: 1300, left: 70, width: 940, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 88, lineHeight: 1.15}}>
      {found.ch.words.map((w, j) => {
        const on = f >= w.s - 1;
        const now = on && (j === found!.ch.words.length - 1 || f < found!.ch.words[j + 1].s - 1);
        const c = clean(w.t);
        const color = hl.includes(c) ? (RED.has(c) ? '#ff5a4a' : GREEN.has(c) ? '#5df08a' : '#ffd23f') : '#ffffff';
        const pop = now ? 1 + 0.1 * Math.max(0, 1 - (f - w.s) / 5) + 0.04 : 1;
        return (
          <span key={j} style={{
            display: 'inline-block', margin: '0 16px', color, opacity: on ? 1 : 0.0, transform: `scale(${pop})`,
            WebkitTextStroke: '14px #0b0b0b', paintOrder: 'stroke fill', textShadow: '0 6px 16px rgba(0,0,0,0.5)',
          }}>
            {w.t.toUpperCase()}
          </span>
        );
      })}
    </div>
  );
};

// ---- rótulos anclados ----
const Label: React.FC<{f: number; pt: [number, number, number]; children: React.ReactNode; op: number}> = ({f, pt, children, op}) => {
  const p = project(f, pt);
  if (p.behind || op <= 0.01) return null;
  return (
    <div style={{position: 'absolute', left: p.x, top: p.y, transform: `translate(-50%,-50%) scale(${lerp(0.7, 1, clamp(op))})`, opacity: clamp(op)}}>
      {children}
    </div>
  );
};

const Persona: React.FC<{c: string}> = ({c}) => (
  <svg width={64} height={96} viewBox="0 0 64 96"><circle cx={32} cy={18} r={15} fill={c} /><path d="M10 92 L10 52 Q10 36 32 36 Q54 36 54 52 L54 92 Z" fill={c} /></svg>
);
const Diez: React.FC<{f: number}> = ({f}) => {
  const st = W(2, 19) - 3;
  if (f < st || f >= end(2)) return null;
  return (
    <div style={{position: 'absolute', top: 470, left: 0, width: 1080, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10, padding: '0 150px', boxSizing: 'border-box'}}>
      {Array.from({length: 10}, (_, i) => {
        const s = clamp(sp(f, st + i * 1.5, 10), 0, 1.2);
        return <div key={i} style={{transform: `scale(${s})`, filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.5))'}}><Persona c={f > st + 22 ? '#ff4a3a' : '#ffffff'} /></div>;
      })}
    </div>
  );
};

const Suscribirse: React.FC<{f: number}> = ({f}) => {
  const a = SCENES[4].from, b = end(4);
  if (f < a || f >= b + 4) return null;
  const tap = W(4, 5);
  const inn = clamp(sp(f, a + 2, 10), 0, 1.2);
  const out = prog(f, b - 2, b + 4, 'in');
  const done = f >= tap + 4;
  const press = f >= tap && f < tap + 6 ? 0.9 : 1;
  const bell = done ? Math.sin((f - tap) / 1.6) * 22 * Math.exp(-(f - tap) / 18) : 0;
  const hx = lerp(820, 640, prog(f, tap - 14, tap, 'out')), hy = lerp(1180, 1010, prog(f, tap - 14, tap, 'out'));
  return (
    <div style={{opacity: 1 - out}}>
      <div style={{position: 'absolute', top: 860, left: 0, width: 1080, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 26, transform: `scale(${inn * press})`}}>
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 70, color: done ? '#3a3a3a' : '#fff', background: done ? '#e6e6e6' : '#ff0033', padding: '26px 60px', borderRadius: 80,
          boxShadow: '0 14px 40px rgba(0,0,0,0.45)'}}>{done ? 'SUSCRITO' : 'SUSCRIBIRSE'}</div>
        <svg width={110} height={110} viewBox="0 0 24 24" style={{transform: `rotate(${bell}deg)`, background: '#fff', borderRadius: 60, padding: 14, boxShadow: '0 10px 30px rgba(0,0,0,0.4)'}}>
          <path d="M12 2a6 6 0 0 0-6 6v4l-2 3v1h16v-1l-2-3V8a6 6 0 0 0-6-6zm0 20a3 3 0 0 0 3-3H9a3 3 0 0 0 3 3z" fill={done ? '#111' : '#666'} />
        </svg>
      </div>
      {f < tap + 14 && (
        <svg width={120} height={140} viewBox="0 0 60 70" style={{position: 'absolute', left: hx, top: hy, transform: `scale(${f >= tap && f < tap + 5 ? 0.9 : 1})`}}>
          <path d="M22 4 q4 -3 8 0 v26 l4 -3 q4 -2 7 1 l3 -2 q4 -2 7 1 l2 -1 q4 -1 6 3 v18 q0 12 -12 20 h-18 q-8 -6 -14 -18 l-6 -12 q-2 -5 3 -6 q4 0 7 4 l3 4 z" fill="#fff" stroke="#111" strokeWidth={3} strokeLinejoin="round" />
        </svg>
      )}
    </div>
  );
};

const Comentario: React.FC<{f: number}> = ({f}) => {
  const st = W(6, 4) - 4;
  if (f < st || f >= end(6)) return null;
  const txt = 'Soy de Nariño, ¿cuál me toca? 👀';
  const n = Math.floor(clamp((f - st - 6) / 20) * txt.length);
  const s = clamp(sp(f, st, 10), 0, 1.1);
  return (
    <div style={{position: 'absolute', top: 820, left: 90, width: 900, transform: `scale(${s})`, background: '#fff', borderRadius: 28, padding: '28px 34px', boxShadow: '0 14px 40px rgba(0,0,0,0.45)',
      display: 'flex', gap: 22, alignItems: 'flex-start', fontFamily: FONT}}>
      <div style={{width: 84, height: 84, borderRadius: 42, background: '#2d8cff', color: '#fff', fontWeight: 900, fontSize: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none'}}>V</div>
      <div>
        <div style={{fontSize: 34, color: '#606060', fontWeight: 600}}>@vale_del_sur · hace 1 min</div>
        <div style={{fontSize: 48, color: '#0f0f0f', fontWeight: 700, marginTop: 6, minHeight: 60}}>{txt.slice(0, n)}{n < txt.length && f % 16 < 8 ? '|' : ''}</div>
      </div>
    </div>
  );
};

const CTA: React.FC<{f: number}> = ({f}) => {
  const st = W(7, 7) - 4;
  if (f < st || f >= LOOP) return null;
  const inn = sp(f, st, 10, 0.6);
  const bounce = Math.abs(Math.sin((f - st) / 6)) * 28;
  return (
    <div style={{position: 'absolute', top: 1560, left: 0, width: 1080, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${clamp(inn, 0, 1.2)})`}}>
      <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 88, color: '#1a1200', background: '#ffd23f', padding: '14px 40px', borderRadius: 24, boxShadow: '0 12px 36px rgba(0,0,0,0.45)'}}>VIDEO COMPLETO</div>
      <svg width={120} height={110} viewBox="0 0 120 110" style={{marginTop: 10 + bounce}}>
        <path d="M60 100 L10 40 L40 40 L40 5 L80 5 L80 40 L110 40 Z" fill="#ffd23f" stroke="#1a1200" strokeWidth={7} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

const NombreDep: React.FC<{f: number}> = ({f}) => {
  const items: [string, string, number, number][] = [['CAUCA', 'Cauca', SCENES[2].from + 8, end(2)], ['TOLIMA', 'Tolima', SCENES[3].from + 8, end(3)], ['ANTIOQUIA', 'Antioquia', SCENES[5].from + 8, end(5)]];
  const it = items.find(([, , a, b]) => f >= a && f < b);
  if (!it) return null;
  const c = cen(it[1]);
  const p = project(f, [c[0], c[1] + 0.3, c[2]]);
  const y = Math.min(Math.max(p.y + 60, 560), 1150); // nunca encima de los subtítulos (1300)
  return (
    <div style={{position: 'absolute', left: Math.min(Math.max(p.x, 260), 820), top: y, transform: `translate(-50%, 0) scale(${clamp(sp(f, it[2], 11), 0, 1.15)})`,
      fontFamily: FONT, fontWeight: 900, fontSize: 64, color: '#1a1200', background: '#ffd23f', padding: '10px 30px', borderRadius: 18, boxShadow: '0 10px 30px rgba(0,0,0,0.4)', whiteSpace: 'nowrap'}}>
      {it[0]}
    </div>
  );
};

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <NombreDep f={f} />
      <Badges f={f} />
      <Diez f={f} />
      <Suscribirse f={f} />
      <Comentario f={f} />
      <CTA f={f} />
      <Captions f={f} />
    </>
  );
};
export {at, TOTAL};
