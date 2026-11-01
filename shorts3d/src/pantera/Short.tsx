import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {World} from './World';
import {Overlay} from './Overlay';
import {SCENES, VO, FPS, W} from './timing';
import {PLANOS, planoAt} from './planos';
import {lerp} from '../anim';

const P = (id: string) => PLANOS.find((p) => p.id.startsWith(id))!;
/** efectos: siempre por debajo de la voz (lección del Short del avispón) */
const SFX_GAIN = 0.45;
const SFX: {src: string; at: number; vol: number}[] = [
  {src: 'grunido', at: 0, vol: 0.55},
  ...PLANOS.slice(1).map((p) => ({src: 'corte', at: p.from - 2, vol: 0.35})),
  {src: 'pop', at: W(2, 2), vol: 0.3},
  {src: 'pop', at: W(2, 7), vol: 0.3},
  {src: 'brillo', at: P('P7').from + 4, vol: 0.45},
  {src: 'crujido', at: W(3, 17), vol: 0.8},
  {src: 'brillo', at: W(4, 3), vol: 0.6},
  {src: 'pop', at: W(5, 4), vol: 0.45},
  {src: 'pop', at: W(5, 6), vol: 0.45},
  {src: 'golpe', at: P('P15').from, vol: 0.5},
  ...[W(0, 3), W(3, 1), W(3, 16), W(4, 5), W(5, 0)].map((a) => ({src: 'badge', at: a, vol: 0.25})),
];
const on = (f: number) => SCENES.some((s) => {
  const l = VO[s.key];
  return f >= s.clipAt + l.voiceStart * FPS - 4 && f <= s.clipAt + l.voiceEnd * FPS + 4;
});
const voiceOn = (f: number) => {
  let n = 0;
  for (let k = -8; k <= 8; k++) n += on(f + k) ? 1 : 0;
  return n / 17;
};
const FONDO: Record<string, [string, string]> = {
  noche: ['#0c1a33', '#02060c'], pedestales: ['#1b2a48', '#070b14'], pelo: ['#123040', '#04101a'], tortuga: ['#0c1a33', '#02060c'], vacio: ['#05070d', '#000000'],
};

export const ShortPantera: React.FC = () => {
  const f = useCurrentFrame();
  const pl = planoAt(f);
  const [top, bot] = pl.id.startsWith('P2') ? ['#02040a', '#000000'] : FONDO[pl.set];
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${top} 0%, ${bot} 100%)`}}>
      <ThreeCanvas width={1080} height={1920} shadows flat gl={{antialias: true, alpha: true}} camera={{fov: 32, near: 0.05, far: 300, position: [5, 2, 5]}}>
        <World />
      </ThreeCanvas>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 50%, rgba(0,0,0,0.55) 100%)'}} />
      <Overlay />
      {SCENES.map((s) => (
        <Sequence key={s.key} from={s.clipAt} layout="none">
          <Audio src={staticFile(`pantera/vo/${s.key}.wav`)} />
        </Sequence>
      ))}
      {SFX.map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(c.at))} layout="none">
          <Audio src={staticFile(`pantera/sfx/${c.src}.wav`)} volume={(fr) => c.vol * SFX_GAIN * lerp(1, 0.4, voiceOn(Math.round(c.at) + fr))} />
        </Sequence>
      ))}
      <Audio src={staticFile('pantera/selva_noche.wav')} volume={(fr) => lerp(0.22, 0.1, voiceOn(fr))} />
      <Audio src={staticFile('audio/musica.wav')} volume={(fr) => lerp(0.3, 0.14, voiceOn(fr)) * Math.min(1, fr / 6)} />
    </AbsoluteFill>
  );
};
