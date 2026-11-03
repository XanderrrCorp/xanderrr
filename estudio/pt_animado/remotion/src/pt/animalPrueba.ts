// Animal de PRUEBA dibujado por código (serpiente de caricatura con contorno de tinta y fondo transparente).
// En producción la imagen la hace Gemini (Google); esto solo sirve para probar sin gastar.
import { INK } from "./toon";

export function serpientePrueba(): HTMLCanvasElement {
  const c = document.createElement("canvas"); c.width = 1200; c.height = 800;
  const g = c.getContext("2d")!;
  g.lineCap = "round"; g.lineJoin = "round";
  const cuerpo: [number, number][] = [];
  for (let i = 0; i <= 60; i++) { const t = i / 60; cuerpo.push([140 + t * 760, 690 - 40 * Math.sin(t * 9) * (1 - t) - t * t * 300]); }
  const trazo = (w: number, col: string) => { g.strokeStyle = col; g.lineWidth = w; g.beginPath(); cuerpo.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke(); };
  trazo(118, INK); trazo(96, "#8a6a3a");
  // equis del dibujo (talla equis)
  g.strokeStyle = "#4a321c"; g.lineWidth = 12;
  for (let i = 4; i < 56; i += 6) { const [x, y] = cuerpo[i]; g.beginPath(); g.moveTo(x - 26, y - 30); g.lineTo(x + 26, y + 30); g.moveTo(x + 26, y - 30); g.lineTo(x - 26, y + 30); g.stroke(); }
  trazo(28, "rgba(255,240,200,.35)");
  // cabeza
  const [hx, hy] = cuerpo[60];
  g.fillStyle = "#8a6a3a"; g.strokeStyle = INK; g.lineWidth = 12;
  g.beginPath(); g.ellipse(hx + 70, hy - 20, 115, 78, -0.25, 0, 7); g.fill(); g.stroke();
  g.fillStyle = "#fff"; g.beginPath(); g.ellipse(hx + 95, hy - 60, 30, 26, 0, 0, 7); g.fill(); g.stroke();
  g.fillStyle = INK; g.beginPath(); g.ellipse(hx + 105, hy - 58, 7, 18, 0, 0, 7); g.fill();
  g.strokeStyle = INK; g.lineWidth = 9; g.beginPath(); g.moveTo(hx + 120, hy + 20); g.quadraticCurveTo(hx + 160, hy + 10, hx + 180, hy - 5); g.stroke();
  g.strokeStyle = "#d0384a"; g.lineWidth = 8; g.beginPath(); g.moveTo(hx + 180, hy - 5); g.lineTo(hx + 240, hy + 5); g.moveTo(hx + 230, hy + 4); g.lineTo(hx + 255, hy - 10); g.moveTo(hx + 230, hy + 4); g.lineTo(hx + 255, hy + 18); g.stroke();
  return c;
}
