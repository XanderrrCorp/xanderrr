import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {Mundo, LOOP} from './Mundo';
import {Overlay} from './Overlay';
import {SCENES, VO, FPS, W} from './timing';
import {lerp} from '../anim';

/** efectos: siempre por debajo de la voz */
const SFX_GAIN = 0.45;
const SFX: {src: string; at: number; vol: number}[] = [
  {src: 'whoosh', at: W(0, 3) - 4, vol: 0.5},
  ...Array.from({length: 8}, (_, i) => ({src: 'pop', at: W(0, 3) + i * 6, vol: 0.18})),
  ...[SCENES[2].from + 4, SCENES[3].from + 4, SCENES[5].from + 4, SCENES[6].from + 4].map((a) => ({src: 'whoosh', at: a, vol: 0.4})),
  {src: 'brillo', at: W(2, 15), vol: 0.5},
  ...Array.from({length: 10}, (_, i) => ({src: 'pop', at: W(2, 19) - 3 + i * 1.5, vol: 0.15})),
  {src: 'golpe', at: W(3, 14), vol: 0.5},
  {src: 'pop', at: SCENES[4].from + 2, vol: 0.4},
  {src: 'campanita', at: W(4, 5) + 4, vol: 0.55},
  {src: 'golpe', at: W(5, 17), vol: 0.55},
  {src: 'tecleo', at: W(6, 4) + 2, vol: 0.4},
  {src: 'corte', at: LOOP - 2, vol: 0.4},
  ...[W(1, 0), W(2, 5), W(2, 15), W(3, 4), W(3, 14), W(5, 6), W(5, 16)].map((a) => ({src: 'badge', at: a, vol: 0.25})),
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

export const ShortDepartamentos: React.FC = () => {
  useCurrentFrame();
  return (
    <AbsoluteFill style={{background: 'linear-gradient(180deg, #4f8fc8 0%, #173a5e 100%)'}}>
      <ThreeCanvas width={1080} height={1920} shadows flat gl={{antialias: true, alpha: true}} camera={{fov: 32, position: [0, 30, 20]}}>
        <Mundo />
      </ThreeCanvas>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 62%, rgba(0,0,0,0.28) 100%)'}} />
      <Overlay />
      {SCENES.map((s) => (
        <Sequence key={s.key} from={s.clipAt} layout="none">
          <Audio src={staticFile(`colombia/vo/${s.key}.wav`)} />
        </Sequence>
      ))}
      {SFX.map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(c.at))} layout="none">
          <Audio src={staticFile(`colombia/sfx/${c.src}.wav`)} volume={(fr) => c.vol * SFX_GAIN * lerp(1, 0.4, voiceOn(Math.round(c.at) + fr))} />
        </Sequence>
      ))}
      <Audio src={staticFile('audio/musica.wav')} volume={(fr) => lerp(0.3, 0.14, voiceOn(fr)) * Math.min(1, fr / 6)} />
    </AbsoluteFill>
  );
};
