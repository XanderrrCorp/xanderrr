// Composición «Used To»: escena 3D con posproceso + subtítulos, y la mezcla: voz al frente, música 15–18 dB debajo
// con ducking, efectos reales en cada acción (también por debajo de la voz).
import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {Mundo} from './Mundo';
import {Overlay} from './Overlay';
import {ESCENAS, TOTAL, vozEn, CON_VOZ, Wp, FPS} from './timing';
import {estado} from './estado';
import {PLANOS} from './planos';
import {SPEC, dB} from './spec';
import {lerp, rnd} from '../anim';

const R = (n: string) => staticFile(`usedto/${n}.wav`);
export const volMusica = (f: number) => lerp(dB(SPEC.musicaHuecoDb), dB(SPEC.musicaBajoVozDb), vozEn(f)) * Math.min(1, f / 6);
const SFX = [
  ...ESCENAS.flatMap((e) => (e.frase.efectos ?? []).filter((x) => x.sfx).map((x) => ({src: x.sfx!, at: Wp(e.key, x.palabra) + (x.retraso ?? 0) * FPS - 1, vol: 0.9}))),
  // un roce suave en los barridos de cámara de una versión a otra
  ...PLANOS.filter((p) => p.corte === 'barrido').map((p) => ({src: 'barrido', at: p.from, vol: 0.5})),
];
const SFX_GAIN = 0.55;

export const ShortUsedTo: React.FC = () => {
  const f = useCurrentFrame();
  const g = estado(f).sacudida;
  const sh = g > 0.02 ? {x: (rnd(f, 1) - 0.5) * 22 * g, y: (rnd(f, 2) - 0.5) * 18 * g} : {x: 0, y: 0};
  return (
    <AbsoluteFill style={{background: '#0d1a1a'}}>
      <AbsoluteFill style={{transform: `translate(${sh.x}px, ${sh.y}px) scale(${g > 0.02 ? 1.02 : 1})`}}>
        <ThreeCanvas width={SPEC.ancho} height={SPEC.alto} shadows="soft" gl={{antialias: false, toneMapping: THREE.NoToneMapping, powerPreference: 'high-performance'}}
          camera={{fov: 44, near: 0.02, far: 80, position: [0, 2, 5]}}>
          <Mundo />
        </ThreeCanvas>
      </AbsoluteFill>
      <Overlay />
      {ESCENAS.filter((s) => CON_VOZ.has(s.key)).map((s) => (
        <Sequence key={s.key} from={s.clipAt} layout="none"><Audio src={staticFile(`usedto/vo/${s.key}.wav`)} /></Sequence>
      ))}
      <Audio src={R('musica')} volume={(fr) => volMusica(fr)} />
      {SFX.map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(c.at))} layout="none">
          <Audio src={R(c.src)} volume={(fr) => c.vol * SFX_GAIN * lerp(1, 0.45, vozEn(Math.round(c.at) + fr))} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
export {TOTAL};
