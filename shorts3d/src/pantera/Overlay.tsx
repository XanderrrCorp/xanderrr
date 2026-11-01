// Capa 2D: insignias, subtítulos palabra por palabra, rótulos anclados al 3D y llamado al video completo.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {SCENES, VO, W, at, FPS, TOTAL} from './timing';
import {clamp, prog, sp, lerp} from '../anim';
import {project, PLANOS, SET} from './planos';

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
const P = (id: string) => PLANOS.find((p) => p.id.startsWith(id))!;
const BADGES: Badge[] = [
  {text: '¿NO EXISTE?', v: 'warn', from: W(0, 3), to: end(0) + 2},
  {text: 'JAGUAR', v: 'info', from: W(2, 2), to: P('P5').from - 1},
  {text: 'LEOPARDO', v: 'info', from: W(2, 7), to: P('P6').from - 1},
  {text: 'MELANISMO', v: 'info', from: W(2, 14), to: end(2) - 2},
  {text: 'INVISIBLE DE NOCHE', v: 'neg', from: W(3, 1), to: P('P9').from - 1},
  {text: 'MORDIDA BRUTAL', v: 'neg', from: W(3, 16), to: end(3) - 2},
  {text: 'MANCHAS ESCONDIDAS', v: 'pos', from: W(4, 5), to: end(4) - 2},
  {text: '¿LO SABÍAS?', v: 'warn', from: W(5, 0), to: end(5) - 2},
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
  s1: ['PANTERA', 'NEGRA', 'EXISTE'], s2: ['MIRANDO', 'OSCURIDAD'], s3: ['JAGUAR', 'LEOPARDO', 'MUTACIÓN', 'NEGRO'],
  s4: ['INVISIBLE', 'RAMA', 'MORDIDA', 'TORTUGA'], s5: ['MANCHAS', 'ESCONDIDAS', 'LUZ'], s6: ['SÍ', 'NO'],
  s7: ['DIFÍCIL', 'VIDEO', 'COMPLETO'],
};
const RED = new Set(['MORDIDA', 'TORTUGA', 'EXISTE', 'DIFÍCIL', 'NO']);
const GREEN = new Set(['MANCHAS', 'ESCONDIDAS', 'LUZ', 'SÍ']);
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

const tag = (txt: string, bg = '#111') => (
  <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 54, color: '#fff', background: bg, padding: '8px 24px', borderRadius: 16, whiteSpace: 'nowrap', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}}>{txt}</div>
);

const Labels: React.FC<{f: number}> = ({f}) => {
  const p4 = P('P4'), p5 = P('P5'), p7 = P('P7'), p6 = P('P6');
  const B = SET.pedestales, H = SET.pelo;
  const on = (a: number, b: number) => (f >= a && f < b ? sp(f, a + 2, 12) : 0);
  return (
    <>
      <Label f={f} pt={[B[0] - 3.5, -0.15, 2.2]} op={on(p4.from, p5.from)}>{tag('AMÉRICA', '#1f6fd6')}</Label>
      <Label f={f} pt={[B[0] + 3.5, -0.15, 2.2]} op={on(p5.from, p6.from)}>{tag('ÁFRICA Y ASIA', '#1f6fd6')}</Label>
      <Label f={f} pt={[H[0] + 1.9, H[1] + 2.4, H[2]]} op={on(p6.from + 6, p6.to)}>{tag('PIGMENTO', '#3a2412')}</Label>
    </>
  );
};

const SiNo: React.FC<{f: number}> = ({f}) => {
  const a = W(5, 4), b = W(5, 6);
  if (f < a - 2 || f >= end(5)) return null;
  const btn = (txt: string, st: number, bg: string) => {
    const s = clamp(sp(f, st, 9), 0, 1.25);
    const bob = 1 + 0.05 * Math.sin((f - st) / 4);
    return (
      <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 110, color: '#fff', background: bg, width: 330, textAlign: 'center', padding: '20px 0', borderRadius: 36,
        transform: `scale(${s * bob})`, boxShadow: '0 14px 40px rgba(0,0,0,0.5)', border: '8px solid #fff'}}>{txt}</div>
    );
  };
  return (
    <div style={{position: 'absolute', top: 820, left: 0, width: 1080, display: 'flex', justifyContent: 'center', gap: 80}}>
      {btn('SÍ', a, '#1f9d55')}
      {btn('NO', b, '#d6332a')}
    </div>
  );
};

const CTA: React.FC<{f: number}> = ({f}) => {
  const p15 = P('P15');
  if (f < p15.from || f >= P('P16').from) return null;
  const q = sp(f, p15.from + 2, 10, 0.6);
  const st = W(6, 12) - 4;
  const inn = f >= st ? sp(f, st, 10, 0.6) : 0;
  const bounce = Math.abs(Math.sin((f - st) / 6)) * 28;
  return (
    <>
      <div style={{position: 'absolute', top: 560, width: 1080, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 420, color: '#ffd23f',
        transform: `scale(${clamp(q, 0, 1.2)}) rotate(${Math.sin(f / 9) * 8}deg)`, textShadow: '0 0 60px rgba(255,210,63,0.6)'}}>?</div>
      {inn > 0 && (
        <div style={{position: 'absolute', top: 1560, left: 0, width: 1080, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${clamp(inn, 0, 1.2)})`}}>
          <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 88, color: '#1a1200', background: '#ffd23f', padding: '14px 40px', borderRadius: 24, boxShadow: '0 12px 36px rgba(0,0,0,0.45)'}}>VIDEO COMPLETO</div>
          <svg width={120} height={110} viewBox="0 0 120 110" style={{marginTop: 10 + bounce}}>
            <path d="M60 100 L10 40 L40 40 L40 5 L80 5 L80 40 L110 40 Z" fill="#ffd23f" stroke="#1a1200" strokeWidth={7} strokeLinejoin="round" />
          </svg>
        </div>
      )}
    </>
  );
};

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <Labels f={f} />
      <Badges f={f} />
      <SiNo f={f} />
      <CTA f={f} />
      <Captions f={f} />
    </>
  );
};
export {at, TOTAL};
