import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {World} from './World';
import {Overlay} from './Overlay';
import {SCENES, VO, TOTAL, FPS} from './timing';
import {calor, T} from './estado';
import {lerp} from './anim';
import {W, at} from './timing';

// efectos (hechos por código en scripts/sonidos.py), amarrados a las palabras y a los eventos
const SFX: {src: string; at: number; vol: number}[] = [
  {src: 'whoosh', at: 0, vol: 0.55},
  {src: 'zumbido', at: 2, vol: 0.22},
  {src: 'pop', at: T.pulgar + 4, vol: 0.35},
  {src: 'zumbido', at: at(1, 0), vol: 0.12},
  ...T.golpes.map((g) => ({src: 'tic_metal', at: g, vol: 0.45})),
  {src: 'whoosh', at: T.mandibulas - 8, vol: 0.3},
  {src: 'zumbido', at: T.extras, vol: 0.25},
  {src: 'madera', at: T.puerta, vol: 0.5},
  {src: 'alarma', at: T.alarma, vol: 0.35},
  {src: 'whoosh', at: T.entra, vol: 0.4},
  {src: 'enjambre', at: T.enjambre, vol: 0.45},
  {src: 'vibracion', at: T.vibra, vol: 0.5},
  {src: 'subida', at: T.calor, vol: 0.4},
  {src: 'golpe', at: T.cae + 22, vol: 0.5},
  {src: 'whoosh', at: T.cta - 6, vol: 0.4},
  {src: 'pop', at: T.cta, vol: 0.45},
  ...[W(0, 1), W(1, 2), W(1, 5), W(2, 10), W(3, 2), W(4, 2), W(4, 13), W(5, 7), W(5, 12), W(5, 15), W(6, 1), W(6, 5)].map((a) => ({src: 'badge', at: a, vol: 0.22})),
];

/** los efectos quedan por debajo de la voz: más bajos siempre y todavía más mientras habla */
const SFX_GAIN = 0.45;

const mix = (a: string, b: string, t: number) => {
  const pa = a.match(/\w\w/g)!.map((h) => parseInt(h, 16)), pb = b.match(/\w\w/g)!.map((h) => parseInt(h, 16));
  return `rgb(${pa.map((v, i) => Math.round(lerp(v, pb[i], t))).join(',')})`;
};

/** la música baja mientras habla la voz */
const on = (f: number) => SCENES.some((s) => {
  const l = VO[s.key];
  return f >= s.clipAt + l.voiceStart * FPS - 4 && f <= s.clipAt + l.voiceEnd * FPS + 4;
});
const voiceOn = (f: number) => {
  let n = 0;
  for (let k = -8; k <= 8; k++) n += on(f + k) ? 1 : 0;
  return n / 17;
};

export const Short: React.FC = () => {
  const f = useCurrentFrame();
  const h = calor(f);
  const top = mix('#1d5a3c', '#8a2a08', h), bot = mix('#04150d', '#240703', h);
  return (
    <AbsoluteFill style={{background: `linear-gradient(180deg, ${top} 0%, ${bot} 100%)`}}>
      <ThreeCanvas width={1080} height={1920} shadows flat gl={{antialias: true, alpha: true}} camera={{fov: 30, near: 0.1, far: 200, position: [0, 3, 20]}}>
        <World />
      </ThreeCanvas>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.5) 100%)'}} />
      <Overlay />
      {SCENES.map((s) => (
        <Sequence key={s.key} from={s.clipAt} layout="none">
          <Audio src={staticFile(`audio/vo/${s.key}.wav`)} volume={1} />
        </Sequence>
      ))}
      {SFX.map((c, i) => (
        <Sequence key={i} from={Math.round(c.at)} layout="none">
          <Audio src={staticFile(`audio/sfx/${c.src}.wav`)} volume={(fr) => c.vol * SFX_GAIN * lerp(1, 0.4, voiceOn(Math.round(c.at) + fr))} />
        </Sequence>
      ))}
      <Audio src={staticFile('audio/musica.wav')} volume={(fr) => lerp(0.34, 0.15, voiceOn(fr)) * Math.min(1, fr / 15)} />
    </AbsoluteFill>
  );
};
export {TOTAL, T};
