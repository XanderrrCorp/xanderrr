// Composición del Short de terror: escena 3D + niebla + screen shake + whoosh entre escenas, y la MEZCLA:
// voz siempre al frente, música 15–18 dB por debajo con ducking, silencio total 0,5 s antes del giro y stinger.
import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {Mundo} from './Mundo';
import {Overlay, Niebla, Destello} from './Overlay';
import {ESCENAS, FPS, TOTAL, vozEn, CUADRO_GIRO, CON_VOZ} from './timing';
import {EFECTOS, estado} from './estado';
import {WHOOSH, planoEn} from './planos';
import {SPEC, dB} from './spec';
import {clamp, lerp, rnd} from '../anim';

const R = (n: string) => staticFile(`terror/${n}.wav`);
// ---------- screen shake: pasos, golpes, puertas, gritos, rayos ----------
const SACUDIDAS = [...EFECTOS.filter((e) => e.shake).map((e) => ({f: e.f, i: e.shake!})), ...(CUADRO_GIRO > 0 ? [{f: CUADRO_GIRO, i: 1.2}] : [])];
export const sacudida = (f: number) => {
  let x = 0, y = 0, r = 0;
  for (const s of SACUDIDAS) {
    if (f < s.f || f > s.f + 14) continue;
    const k = s.i * Math.exp(-(f - s.f) / 4.5);
    x += (rnd(f, 1) - 0.5) * 56 * k;
    y += (rnd(f, 2) - 0.5) * 44 * k;
    r += (rnd(f, 3) - 0.5) * 1.6 * k;
  }
  return {x, y, r};
};
// ---------- whoosh: barrido con desenfoque de movimiento en cada cambio de escena ----------
export const barrido = (f: number) => {
  for (let i = 0; i < WHOOSH.length; i++) {
    const c = WHOOSH[i], d = f - c;
    if (d >= -3 && d <= 4) {
      const k = 1 - Math.abs(d) / (d < 0 ? 3.5 : 4.5);
      return {blur: 70 * k, x: (i % 2 ? 1 : -1) * (d < 0 ? -1 : 1) * 140 * k * k, k};
    }
  }
  return {blur: 0, x: 0, k: 0};
};

// ---------- mezcla ----------
const silencioGiro = (f: number) => {
  if (CUADRO_GIRO < 0) return 1;
  const a = CUADRO_GIRO - SPEC.silencioAntesDelGiro * FPS;
  if (f >= a && f < CUADRO_GIRO) return 0;
  if (f >= a - 4 && f < a) return (a - f) / 4;
  if (f >= CUADRO_GIRO && f < CUADRO_GIRO + 24) return (f - CUADRO_GIRO) / 24;
  return 1;
};
export const volMusica = (f: number) => lerp(dB(SPEC.musicaHuecoDb), dB(SPEC.musicaBajoVozDb), vozEn(f)) * silencioGiro(f) * Math.min(1, f / 8);
const SFX_GAIN = 0.5; // los efectos nunca tapan la voz: además bajan al 40 % mientras habla
const SFX = [
  ...EFECTOS.filter((e) => e.sfx).map((e) => ({src: e.sfx!, at: e.f - (e.sfx === 'golpe' ? 1 : 0), vol: e.sfx === 'grito' ? 0.7 : 0.9})),
  ...EFECTOS.filter((e) => e.rayo).map((e) => ({src: 'trueno', at: e.f, vol: 0.9})),
  ...WHOOSH.map((c) => ({src: 'whoosh', at: c - 4, vol: 0.55})),
];

export const ShortTerror: React.FC = () => {
  const f = useCurrentFrame();
  const sh = sacudida(f), wb = barrido(f);
  const dia = estado(f).dia;
  const [a, b] = dia ? ['#55627c', '#2a3346'] : [SPEC.color.cieloArriba, SPEC.color.cieloAbajo];
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <filter id="barrido"><feGaussianBlur stdDeviation={`${wb.blur} ${wb.blur * 0.06}`} /></filter>
      </svg>
      <AbsoluteFill style={{transform: `translate(${sh.x + wb.x}px, ${sh.y}px) rotate(${sh.r}deg) scale(${1.06 + wb.k * 0.04})`, filter: wb.blur > 0.5 ? 'url(#barrido)' : undefined}}>
        <AbsoluteFill style={{background: `linear-gradient(180deg, ${a} 0%, ${b} 100%)`}} />
        <ThreeCanvas width={SPEC.ancho} height={SPEC.alto} shadows gl={{antialias: true, alpha: true}} camera={{fov: 34, near: 0.03, far: 200, position: [0, 2, 15]}}>
          <Mundo />
        </ThreeCanvas>
        <Niebla f={f} />
        <Destello f={f} />
      </AbsoluteFill>
      {wb.k > 0.05 && <AbsoluteFill style={{background: `linear-gradient(90deg, rgba(160,190,255,0) 0%, rgba(160,190,255,${0.22 * wb.k}) 50%, rgba(160,190,255,0) 100%)`}} />}
      <AbsoluteFill style={{transform: `translate(${sh.x * 0.35}px, ${sh.y * 0.35}px)`}}>
        <Overlay />
      </AbsoluteFill>
      {ESCENAS.filter((s) => CON_VOZ.has(s.key)).map((s) => (
        <Sequence key={s.key} from={s.clipAt} layout="none"><Audio src={staticFile(`terror/vo/${s.key}.wav`)} /></Sequence>
      ))}
      <Audio src={R('musica')} volume={(fr) => volMusica(fr)} />
      {CUADRO_GIRO > 0 && <Sequence from={CUADRO_GIRO} layout="none"><Audio src={R('stinger')} volume={0.75} /></Sequence>}
      {SFX.map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(c.at))} layout="none">
          <Audio src={R(c.src)} volume={(fr) => c.vol * SFX_GAIN * lerp(1, 0.4, vozEn(Math.round(c.at) + fr))} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
export {TOTAL, clamp, planoEn};
