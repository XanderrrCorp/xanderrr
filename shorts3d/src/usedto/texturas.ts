// Texturas hechas por código (nada que bajar ni licenciar): ladrillo, azulejo verde azulado, veta de madera y la
// placa grabada con el nombre del canal.
import * as THREE from 'three';
import {SPEC} from './spec';
import {rnd} from '../anim';

const lienzo = (w: number, h: number, pintar: (c: CanvasRenderingContext2D) => void, rep: [number, number] = [1, 1]) => {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  pintar(cv.getContext('2d')!);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...rep);
  t.anisotropy = 8;
  return t;
};
const cache = new Map<string, THREE.Texture>();
const una = (k: string, hacer: () => THREE.Texture) => {
  if (!cache.has(k)) cache.set(k, hacer());
  return cache.get(k)!;
};

export const ladrillo = () => una('ladrillo', () => lienzo(1024, 1024, (c) => {
  c.fillStyle = SPEC.color.mortero; c.fillRect(0, 0, 1024, 1024);
  const fh = 64, fw = 170;
  for (let r = 0; r < 1024 / fh; r++) for (let k = -1; k < 1024 / fw + 1; k++) {
    const x = k * fw + (r % 2) * fw / 2, y = r * fh, i = r * 31 + k;
    const tono = 0.75 + rnd(i, 1) * 0.4;
    c.fillStyle = `rgb(${Math.round(122 * tono)},${Math.round(59 * tono)},${Math.round(42 * tono)})`;
    c.fillRect(x + 5, y + 5, fw - 10, fh - 10);
    for (let m = 0; m < 30; m++) { c.fillStyle = `rgba(0,0,0,${rnd(i * 7 + m, 2) * 0.12})`; c.fillRect(x + 5 + rnd(i + m, 3) * (fw - 14), y + 5 + rnd(i - m, 4) * (fh - 14), 6, 4); }
  }
}, [9, 4]));

export const azulejo = () => una('azulejo', () => lienzo(512, 512, (c) => {
  c.fillStyle = '#d9d4c8'; c.fillRect(0, 0, 512, 512);
  const fh = 64, fw = 128;
  for (let r = 0; r < 8; r++) for (let k = -1; k < 5; k++) {
    const x = k * fw + (r % 2) * fw / 2, y = r * fh;
    const g = c.createLinearGradient(x, y, x, y + fh);
    g.addColorStop(0, '#2c7f78'); g.addColorStop(0.5, SPEC.color.teal); g.addColorStop(1, '#013232');
    c.fillStyle = g; c.fillRect(x + 3, y + 3, fw - 6, fh - 6);
    c.fillStyle = 'rgba(255,255,255,0.12)'; c.fillRect(x + 8, y + 7, fw - 16, 6);
  }
}, [16, 4]));

export const madera = (clara = false) => una('madera' + clara, () => lienzo(512, 512, (c) => {
  const [a, b] = clara ? ['#8D6E63', '#6d4c41'] : ['#4e342e', SPEC.color.maderaOscura];
  c.fillStyle = a; c.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 140; i++) {
    c.strokeStyle = i % 3 ? `rgba(30,15,8,${0.08 + rnd(i, 1) * 0.18})` : b;
    c.lineWidth = 1 + rnd(i, 2) * 3;
    c.beginPath();
    const y0 = rnd(i, 3) * 512;
    for (let x = 0; x <= 512; x += 16) c.lineTo(x, y0 + Math.sin(x / 60 + i) * 6 + Math.sin(x / 17 + i * 3) * 1.5);
    c.stroke();
  }
}, [2, 1]));

/** placa grabada: madera oscura con el nombre del canal hundido y relleno de oro viejo */
export const placa = (texto: string) => una('placa' + texto, () => lienzo(2048, 256, (c) => {
  c.fillStyle = '#2e1d18'; c.fillRect(0, 0, 2048, 256);
  for (let i = 0; i < 80; i++) { c.strokeStyle = `rgba(0,0,0,${0.1 + rnd(i, 5) * 0.2})`; c.beginPath(); const y = rnd(i, 6) * 256; c.moveTo(0, y); c.bezierCurveTo(700, y + 8, 1300, y - 8, 2048, y + 4); c.stroke(); }
  c.font = '800 150px Montserrat'; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.letterSpacing = '24px';
  c.fillStyle = 'rgba(0,0,0,0.7)'; c.fillText(texto, 1024 - 3, 134 - 4); // sombra del hundido
  const g = c.createLinearGradient(0, 60, 0, 200); g.addColorStop(0, '#f2d27a'); g.addColorStop(1, '#9c7a26');
  c.fillStyle = g; c.fillText(texto, 1024, 134);
}));
