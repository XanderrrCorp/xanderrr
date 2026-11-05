// La composición compartida de «En este pueblo…». Cada episodio le pasa su guion y sus escenas.
import React, {useLayoutEffect} from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {montar, Montaje} from './montaje';
import {SPEC, dB, limpio} from './spec';
import {Mirada} from './look/mirada';
import {FUENTE} from './fuente';
import type {Episodio, Cam} from './tipos';
import {clamp, lerp, prog, sp} from '../anim';

const FPS = SPEC.fps;
const aplicar = (c: THREE.PerspectiveCamera, cam: Cam) => {
  c.position.set(...cam.pos); c.lookAt(...cam.look); c.fov = cam.fov ?? 40;
  c.aspect = SPEC.ancho / SPEC.alto; c.near = 0.05; c.far = 200; c.updateProjectionMatrix(); c.updateMatrixWorld();
};
const Camara: React.FC<{mt: Montaje}> = ({mt}) => {
  const f = useCurrentFrame();
  const {camera} = useThree();
  useLayoutEffect(() => aplicar(camera as THREE.PerspectiveCamera, mt.planoEn(f).cam), [f, camera, mt]);
  return null;
};
const Mundo: React.FC<{ep: Episodio; mt: Montaje}> = ({ep, mt}) => {
  const f = useCurrentFrame();
  const e = ep.escenas[mt.escenaEn(f).id];
  return (<><Mirada cam={mt.planoEn(f).cam} noche={e.noche} interior={e.interior} />{e.render(mt.ctx(f))}</>);
};
/** punch-in del 5 % en los golpes (se queda hasta el final del plano) */
const punch = (mt: Montaje, f: number) => {
  const p = mt.planoEn(f);
  return p.golpeDesde !== undefined && f >= p.golpeDesde ? lerp(1, SPEC.punchIn, prog(f, p.golpeDesde, p.golpeDesde + 3, 'out')) : 1;
};

// ---------- capa 2D ----------
const Contorneado: React.FC<{texto: string; color: string; tam: number; trazo: number}> = ({texto, color, tam, trazo}) => (
  <span style={{position: 'relative', display: 'inline-block', fontSize: tam}}>
    <span style={{position: 'absolute', left: 0, top: 0, color: '#000', WebkitTextStroke: `${trazo}px #000`, textShadow: '0 8px 18px rgba(0,0,0,0.45)'}}>{texto}</span>
    <span style={{position: 'relative', color}}>{texto}</span>
  </span>
);
type Pal = {t: string; s: number; e: number; clave: boolean};
const trozosDe = (ep: Episodio, mt: Montaje) => {
  const claves = new Set(ep.guion.claves.map(limpio));
  return mt.L.flatMap((l) => {
    const cl = new Set([...(l.clave ?? []).map(limpio), ...claves]);
    const out: Pal[][] = [];
    let cur: Pal[] = [];
    l.m.words.forEach((w) => {
      const prev = cur[cur.length - 1];
      if (cur.length && (cur.length >= 4 || (cur.length >= 2 && /[.,…?!:]$/.test(prev.t)))) { out.push(cur); cur = []; }
      cur.push({t: w.text.replace(/[—«»"]/g, ''), s: l.clipAt + w.start * FPS, e: l.clipAt + w.end * FPS, clave: cl.has(limpio(w.text)) || /\d/.test(w.text)});
    });
    if (cur.length) out.push(cur);
    return out;
  });
};
const Subtitulos: React.FC<{tr: Pal[][]; f: number}> = ({tr, f}) => {
  const k = tr.findIndex((t, i) => f >= t[0].s - 2 && f < (tr[i + 1]?.[0].s ?? t[t.length - 1].e + 10) - 2);
  if (k < 0 || f > tr[k][tr[k].length - 1].e + 12) return null;
  const S = SPEC.sub, a = sp(f, tr[k][0].s - 2, 12, 0.45);
  return (
    <div style={{position: 'absolute', top: S.y, left: 40, width: 1000, textAlign: 'center', fontFamily: FUENTE, fontWeight: 800, lineHeight: 1.15,
      transform: `scale(${0.85 + 0.15 * clamp(a, 0, 1.08)})`}}>
      {tr[k].map((w, j) => (
        <span key={j} style={{margin: '0 13px', display: 'inline-block'}}>
          <Contorneado texto={w.t.replace(/[,:;]$/, '').toUpperCase()} color={w.clave ? S.amarillo : S.blanco} tam={S.tam} trazo={S.trazo} />
        </span>
      ))}
    </div>
  );
};
/** globo de diálogo encima de la cabeza de quien habla (posición proyectada desde la cámara del plano) */
const cam2d = new THREE.PerspectiveCamera();
const Globo: React.FC<{ep: Episodio; mt: Montaje; f: number}> = ({ep, mt, f}) => {
  const l = mt.lineaEn(f);
  if (!l.quien || f > l.clipAt + l.m.voiceEnd * FPS + 10) return null;
  const e = ep.escenas[l.escena];
  const cabeza = e.cabezas?.[l.quien];
  if (!cabeza) return null;
  aplicar(cam2d, mt.planoEn(f).cam);
  const v = new THREE.Vector3(cabeza[0], cabeza[1] + 0.35, cabeza[2]).project(cam2d);
  const pk = punch(mt, f);
  let x = ((v.x * pk) * 0.5 + 0.5) * 1080, y = ((-v.y * pk) * 0.5 + 0.5) * 1920;
  if (v.z > 1) return null;
  x = Math.max(320, Math.min(760, x)); y = Math.max(260, Math.min(1150, y));
  const a = sp(f, l.from + 1, 11, 0.5);
  const txt = l.texto.replace(/^—\s*/, '').replace(/^«|»$/g, '');
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -100%) scale(${clamp(a, 0, 1.1)})`, transformOrigin: '50% 100%'}}>
      <div style={{background: '#fff', color: '#111', fontFamily: FUENTE, fontWeight: 800, fontSize: 60, lineHeight: 1.12, padding: '24px 34px', borderRadius: 34,
        border: '6px solid #111', width: 600, boxSizing: 'border-box', textAlign: 'center', boxShadow: '0 10px 0 rgba(0,0,0,0.18)'}}>{txt}</div>
      <div style={{position: 'absolute', left: '50%', bottom: -30, width: 0, height: 0, marginLeft: -18, borderLeft: '18px solid transparent', borderRight: '18px solid transparent', borderTop: '32px solid #111'}} />
      <div style={{position: 'absolute', left: '50%', bottom: -20, width: 0, height: 0, marginLeft: -11, borderLeft: '11px solid transparent', borderRight: '11px solid transparent', borderTop: '22px solid #fff'}} />
    </div>
  );
};
const Titulo: React.FC<{ep: Episodio; f: number}> = ({ep, f}) => {
  const fin = Math.round(2.6 * FPS);
  if (f > fin + 8) return null;
  const a = sp(f, 0, 12, 0.5), o = 1 - prog(f, fin, fin + 8, 'in');
  return (
    <div style={{position: 'absolute', top: 170, left: 50, width: 980, textAlign: 'center', fontFamily: FUENTE, fontWeight: 800, lineHeight: 1.1, opacity: o,
      transform: `scale(${clamp(a, 0, 1.08)}) rotate(-2deg)`}}>
      <Contorneado texto={ep.guion.titulo} color="#FFD400" tam={ep.guion.titulo.length > 34 ? 72 : 86} trazo={20} />
    </div>
  );
};
/** íconos genéricos de «me gusta» y «suscribirse» con campana (dibujados aquí, sin logos de nadie) */
const CTA: React.FC<{mt: Montaje; f: number}> = ({mt, f}) => {
  const a0 = mt.TOTAL - Math.round(mt.CTA_S * FPS) - Math.round(1.2 * FPS);
  if (f < a0) return null;
  const rebote = (d: number) => clamp(sp(f, a0 + d, 8, 0.5), 0, 1.25) * (1 + 0.06 * Math.sin((f - a0 - d) / 3.5));
  return (
    <div style={{position: 'absolute', top: 760, width: 1080, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 40}}>
      <div style={{transform: `scale(${rebote(0)})`, width: 220, height: 220, borderRadius: 60, background: '#fff', border: '8px solid #111', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 12px 0 rgba(0,0,0,0.2)'}}>
        <svg width={130} height={130} viewBox="0 0 24 24"><path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.3l1-4.6v-.3c0-.4-.2-.8-.4-1.1L13.2 1 6.6 7.6C6.2 8 6 8.5 6 9v10c0 1.1.9 2 2 2h9c.8 0 1.5-.5 1.8-1.2l3-7.1c.1-.2.2-.5.2-.7v-2z" fill="#1e88e5" /></svg>
      </div>
      <div style={{transform: `scale(${rebote(6)})`, display: 'flex', alignItems: 'center', gap: 18, background: '#e53935', color: '#fff', fontFamily: FUENTE, fontWeight: 800, fontSize: 64, padding: '36px 44px', borderRadius: 40, border: '8px solid #111', boxShadow: '0 12px 0 rgba(0,0,0,0.2)'}}>
        SUSCRIBIRSE
        <svg width={86} height={86} viewBox="0 0 24 24" style={{transform: `rotate(${Math.sin(f / 2.2) * 16}deg)`}}><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.1-1.6-5.6-4.5-6.3V4a1.5 1.5 0 0 0-3 0v.7C7.6 5.4 6 7.9 6 11v5l-2 2v1h16v-1l-2-2z" fill="#fff" /></svg>
      </div>
    </div>
  );
};

// ---------- audio ----------
const SFX_GAIN = 0.5;
export const crearShort = (ep: Episodio) => {
  const Short: React.FC = () => {
    const f = useCurrentFrame();
    const mt = montar(ep);
    const tr = React.useMemo(() => trozosDe(ep, mt), [mt]);
    const tensa = (fr: number) => (mt.lineaEn(fr).tensa ? 1 : 0);
    const R = (n: string) => staticFile(`pueblo/${n}.wav`); // la música es la misma en los 6: es la marca
    const sfx = mt.L.flatMap((l) => (l.sfx ?? []).map((s) => ({s: s.s, at: (s.palabra ? mt.W(l.id, s.palabra) : l.from) + (s.retraso ?? 0) * FPS - 1})));
    const musica = (fr: number, cual: 0 | 1) => {
      // fundido de ~0,7 s entre la música cálida y la tensa
      let k = 0;
      for (let d = -10; d <= 10; d++) k += tensa(Math.max(0, fr + d));
      const t = k / 21, peso = cual ? t : 1 - t;
      return lerp(dB(SPEC.musicaHuecoDb), dB(SPEC.musicaBajoVozDb), mt.vozEn(fr)) * peso * Math.min(1, fr / 6);
    };
    const pk = punch(mt, f);
    return (
      <AbsoluteFill style={{background: SPEC.color.cielo}}>
        <AbsoluteFill style={{transform: `scale(${pk})`}}>
          <ThreeCanvas width={SPEC.ancho} height={SPEC.alto} shadows gl={{antialias: false, stencil: false, powerPreference: 'high-performance', toneMappingExposure: 1.0}} camera={{fov: 40, near: 0.05, far: 800, position: [0, 5, 20]}}>
            <Mundo ep={ep} mt={mt} />
          </ThreeCanvas>
        </AbsoluteFill>
        <Titulo ep={ep} f={f} />
        <Globo ep={ep} mt={mt} f={f} />
        <Subtitulos tr={tr} f={f} />
        <CTA mt={mt} f={f} />
        {mt.L.filter((l) => l.real).map((l) => (
          <Sequence key={l.id} from={l.clipAt} layout="none"><Audio src={staticFile(`${ep.carpetaAudio}/vo/${l.id}.wav`)} /></Sequence>
        ))}
        <Audio src={R('musica_calida')} loop volume={(fr) => musica(fr, 0)} />
        <Audio src={R('musica_tensa')} loop volume={(fr) => musica(fr, 1)} />
        {sfx.map((c, i) => (
          <Sequence key={i} from={Math.max(0, Math.round(c.at))} layout="none">
            <Audio src={staticFile(`pueblo/sfx/${c.s}.wav`)} volume={(fr) => SFX_GAIN * lerp(1, 0.45, mt.vozEn(Math.round(c.at) + fr))} />
          </Sequence>
        ))}
      </AbsoluteFill>
    );
  };
  return Short;
};
