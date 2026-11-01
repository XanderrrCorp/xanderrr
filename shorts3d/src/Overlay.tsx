// Capa 2D: insignias, subtítulos palabra por palabra, rótulos anclados al 3D y llamado al video completo.
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {SCENES, VO, W, at, FPS} from './timing';
import {clamp, prog, sp, lerp} from './anim';
import {project} from './camara';
import {PERCH, THERMO, THERMO_H} from './lugares';
import * as S from './estado';

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
  {text: '¿DEL TAMAÑO DE TU PULGAR?', v: 'warn', from: W(0, 1), to: end(0) - 4},
  {text: '5 CM', v: 'info', from: W(1, 2), to: W(1, 5) - 2},
  {text: 'ARMADURA', v: 'neg', from: W(1, 5), to: end(1) - 4},
  {text: 'COLMENA EN PELIGRO', v: 'neg', from: W(2, 10), to: end(2) - 4},
  {text: 'ABEJA JAPONESA', v: 'pos', from: W(3, 2), to: end(3) - 4},
  {text: 'BOLA DE ABEJAS', v: 'pos', from: W(4, 2), to: W(4, 13) - 2},
  {text: 'SIN VOLAR', v: 'info', from: W(4, 13), to: end(4) - 4},
  {text: '~46 °C', v: 'info', from: W(5, 7), to: end(5) - 3},
  {text: 'ABEJAS: AGUANTAN', v: 'pos', from: W(5, 12), to: end(5) - 3},
  {text: 'AVISPÓN: NO', v: 'neg', from: W(5, 15), to: end(5) - 3},
  {text: 'AVISPÓN VENCIDO', v: 'pos', from: W(6, 1), to: W(6, 5) - 2},
  {text: '¿EL QUE NO PUEDE PICARTE?', v: 'warn', from: W(6, 5), to: end(6) + 10},
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
  s1: ['PULGAR', 'COLMENA'], s2: ['CINCO', 'ARMADURA', 'DAÑO'], s3: ['MANDÍBULAS', 'COLMENA', 'HORAS'],
  s4: ['JAPONESA', 'TRUCO', 'CIENTOS'], s5: ['BOLA', 'VIBRAR'], s6: ['CALOR', 'CUARENTA', 'SEIS', 'GRADOS', 'AGUANTAN', 'NO'],
  s7: ['COCINAN', 'CALOR', 'VIDEO', 'COMPLETO'],
};
const RED = new Set(['ARMADURA', 'DAÑO', 'MANDÍBULAS', 'NO', 'HORAS']);
const GREEN = new Set(['JAPONESA', 'TRUCO', 'BOLA', 'AGUANTAN', 'COCINAN']);
const clean = (w: string) => w.replace(/[^\p{L}\p{N}]/gu, '').toUpperCase();
type Chunk = {words: {t: string; s: number; e: number}[]};
const chunks = (i: number): Chunk[] => {
  const sc = SCENES[i], l = VO[sc.key];
  const out: Chunk[] = [];
  let cur: Chunk = {words: []}, len = 0;
  l.words.forEach((w) => {
    const t = w.text.replace('…', '…');
    if (cur.words.length && (len + t.length + 1 > 17 || /[.,…?]$/.test(cur.words[cur.words.length - 1].t))) {
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
    <div style={{position: 'absolute', top: 1360, left: 90, width: 900, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 70, lineHeight: 1.15}}>
      {found.ch.words.map((w, j) => {
        const on = f >= w.s - 1;
        const now = on && (j === found!.ch.words.length - 1 || f < found!.ch.words[j + 1].s - 1);
        const c = clean(w.t);
        const color = hl.includes(c) ? (RED.has(c) ? '#ff5a4a' : GREEN.has(c) ? '#5df08a' : '#ffd23f') : '#ffffff';
        const pop = now ? 1 + 0.1 * Math.max(0, 1 - (f - w.s) / 5) + 0.04 : 1;
        return (
          <span key={j} style={{
            display: 'inline-block', margin: '0 16px', color, opacity: on ? 1 : 0.0, transform: `scale(${pop})`,
            WebkitTextStroke: '12px #0b0b0b', paintOrder: 'stroke fill', textShadow: '0 6px 16px rgba(0,0,0,0.5)',
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

const Clock: React.FC<{f: number}> = ({f}) => {
  const a = (f - S.T.reloj) * 22;
  return (
    <svg width={150} height={150} viewBox="0 0 150 150">
      <circle cx={75} cy={75} r={66} fill="#ffffff" stroke="#111" strokeWidth={9} />
      {Array.from({length: 12}, (_, i) => (
        <line key={i} x1={75} y1={17} x2={75} y2={27} stroke="#111" strokeWidth={5} transform={`rotate(${i * 30} 75 75)`} />
      ))}
      <line x1={75} y1={75} x2={75} y2={40} stroke="#d6332a" strokeWidth={8} strokeLinecap="round" transform={`rotate(${a} 75 75)`} />
      <line x1={75} y1={75} x2={75} y2={52} stroke="#111" strokeWidth={9} strokeLinecap="round" transform={`rotate(${a / 12} 75 75)`} />
      <circle cx={75} cy={75} r={7} fill="#111" />
    </svg>
  );
};

const tag = (txt: string, bg = '#111') => (
  <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 52, color: '#fff', background: bg, padding: '8px 22px', borderRadius: 16, whiteSpace: 'nowrap', boxShadow: '0 8px 24px rgba(0,0,0,0.4)'}}>{txt}</div>
);

const Labels: React.FC<{f: number}> = ({f}) => {
  const r = S.ruler(f);
  const th = S.thermoShow(f);
  const temp = Math.round(lerp(35, 46, S.calor(f)));
  const clockOp = f >= S.T.reloj && f < end(2) ? sp(f, S.T.reloj, 12) * (1 - prog(f, end(2) - 8, end(2))) : 0;
  return (
    <>
      <Label f={f} pt={[PERCH[0] + 0.05, PERCH[1] - 0.95, PERCH[2] + 0.7]} op={prog(r, 0.6, 1)}>{tag('≈ 5 cm', '#b8860b')}</Label>
      <Label f={f} pt={[THERMO[0], THERMO[1] + THERMO_H + 1.25, THERMO[2]]} op={th}>
        <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 96, color: '#fff', WebkitTextStroke: '12px #3a0a00', paintOrder: 'stroke fill'}}>{temp} °C</div>
      </Label>
      <Label f={f} pt={[2.4, 5.6, 0.6]} op={clockOp}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
          <Clock f={f} />
          {tag('EN HORAS', '#d6332a')}
        </div>
      </Label>
    </>
  );
};

const CTA: React.FC<{f: number}> = ({f}) => {
  const st = S.T.cta;
  if (f < st) return null;
  const inn = sp(f, st, 10, 0.6);
  const bounce = Math.abs(Math.sin((f - st) / 7)) * 26;
  return (
    <div style={{position: 'absolute', top: 1540, left: 0, width: 1080, display: 'flex', flexDirection: 'column', alignItems: 'center', transform: `scale(${clamp(inn, 0, 1.2)})`}}>
      <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 84, color: '#1a1200', background: '#ffd23f', padding: '14px 40px', borderRadius: 24, boxShadow: '0 12px 36px rgba(0,0,0,0.45)', letterSpacing: 1}}>
        VIDEO COMPLETO
      </div>
      <svg width={120} height={110} viewBox="0 0 120 110" style={{marginTop: 10 + bounce}}>
        <path d="M60 100 L10 40 L40 40 L40 5 L80 5 L80 40 L110 40 Z" fill="#ffd23f" stroke="#1a1200" strokeWidth={7} strokeLinejoin="round" />
      </svg>
    </div>
  );
};

export const Overlay: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <>
      <Labels f={f} />
      <Badges f={f} />
      <Captions f={f} />
      <CTA f={f} />
    </>
  );
};
export {at};
