// La criatura de las 3:33 (episodio 2), dibujada con el Pen de la skill: altísima, brazos larguísimos, ojos grandes
// y amables, y su bufanda roja (que al final le pone al niño solo). Lienzo de 600x1000, suela en y = 975.
import type {Pen} from '../Carta2D';
const INK = '#241726';
export type CriaturaOpts = {bufanda?: boolean; ojos?: 'abiertos' | 'mira' | 'cerrados'; brazos?: number; agacha?: number};
export const dibujaCriatura = (p: Pen, o: CriaturaOpts = {}) => {
  const {bufanda = true, ojos = 'abiertos', brazos = 0, agacha = 0} = o;
  const piel = '#3e4f93', panza = '#5b6fb8';
  const hy = 210 + agacha * 90; // cabeza más baja si se agacha
  // piernas largas
  for (const s of [-1, 1]) p.line([[300 + s * 45, 700], [300 + s * 60, 960]], piel, 34);
  for (const s of [-1, 1]) p.ell(300 + s * 70, 965, 46, 16, piel, 9);
  // brazos larguísimos (hasta casi el suelo), se levantan con `brazos`
  for (const s of [-1, 1]) {
    const mx = 300 + s * (170 + brazos * 60), my = 520 - brazos * 120, hx = 300 + s * (190 + brazos * 110), hy2 = 860 - brazos * 330;
    p.line([[300 + s * 95, hy + 190], [mx, my], [hx, hy2]], piel, 26);
    for (const k of [-1, 0, 1]) p.line([[hx, hy2], [hx + s * 10 + k * 14, hy2 + 38]], piel, 10);
  }
  // cuerpo largo
  p.ell(300, hy + 330, 120, 260, piel, 11);
  p.ell(300, hy + 380, 70, 170, panza, 0);
  // cabeza
  p.ell(300, hy, 125, 112, piel, 11);
  if (ojos === 'cerrados') for (const s of [-1, 1]) p.stroke([[300 + s * 70, hy], [300 + s * 30, hy]], 9);
  else for (const s of [-1, 1]) {
    p.ell(300 + s * 50, hy - 5, 34, 38, '#fff6d8', 7);
    p.ell(300 + s * 50 + (ojos === 'mira' ? 0 : s * 4), hy + 2, 13, 15, INK, 0);
  }
  p.stroke([[262, hy + 62], [300, hy + 70], [338, hy + 62]], 7); // boca tranquila
  if (bufanda) {
    p.ell(300, hy + 125, 118, 34, '#e63946', 9);
    p.poly([[340, hy + 135], [385, hy + 300], [330, hy + 300], [315, hy + 150]], '#e63946', 9);
    for (const k of [0, 1, 2]) p.stroke([[300 - 90 + k * 60, hy + 112], [300 - 75 + k * 60, hy + 140]], 6, '#ffffff');
  }
};
