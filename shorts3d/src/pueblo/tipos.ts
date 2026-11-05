// Contrato de un episodio: el guion (JSON) + sus escenas (código). Todo lo demás es compartido.
import type React from 'react';
import type * as THREE from 'three';
export type V3 = [number, number, number];
export type Hablante = 'narrador' | 'nino' | 'nina' | 'bruno' | 'adulto' | 'criatura';
export type Linea = {
  id: string; texto: string; escena: string;
  habla?: Hablante; quien?: string; // quien = personaje sobre el que sale el globo
  clave?: string[]; sfx?: {s: string; palabra?: string; retraso?: number}[];
  golpe?: string; tensa?: boolean;
};
export type Guion = {titulo: string; voz: {voice_id: string; speed: number}; claves: string[]; lineas: Linea[]};
export type Cam = {pos: V3; look: V3; fov?: number};
export type Ctx = {
  f: number; f0: number; f1: number; u: number; // cuadro, inicio y fin de la escena, avance 0..1
  W: (id: string, palabra?: string | number) => number; // cuadro donde la línea dice esa palabra
  desde: (id: string, palabra?: string | number, dur?: number) => number; // 0..1 desde esa palabra
};
export type Escena = {
  noche?: boolean; interior?: boolean; pueblo?: boolean; hora?: number;
  camaras: Cam[];
  /** puntos de las cabezas para los globos de diálogo */
  cabezas?: Record<string, V3>;
  render: (c: Ctx) => React.ReactNode;
};
export type Episodio = {id: string; guion: Guion; escenas: Record<string, Escena>; vo: Record<string, unknown>; carpetaAudio: string};
export type {THREE};
