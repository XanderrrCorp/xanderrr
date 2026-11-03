// Texturas pintadas por código (Canvas2D), diseño propio de Peligro Tropical: pasto, barro, teja, pared encalada con
// zócalo, baldosa, madera, agua, piedra, y tarjetas con transparencia (pasto, helecho, hoja grande).
import * as THREE from "three";

export const rnd = (seed: number) => { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); };

const tex = (w: number, h: number, draw: (g: CanvasRenderingContext2D, r: () => number) => void, seed = 1, repeat: [number, number] = [1, 1], alpha = false) => {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  const g = c.getContext("2d")!;
  draw(g, rnd(seed));
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = repeat[0] === 1 && repeat[1] === 1 && alpha ? THREE.ClampToEdgeWrapping : THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  t.anisotropy = 8;
  return t;
};

const manchas = (g: CanvasRenderingContext2D, r: () => number, w: number, h: number, cols: string[], n: number, rmin: number, rmax: number, a = 0.35) => {
  for (let i = 0; i < n; i++) {
    g.globalAlpha = a * (0.5 + r() * 0.5);
    g.fillStyle = cols[Math.floor(r() * cols.length)];
    g.beginPath(); g.ellipse(r() * w, r() * h, rmin + r() * (rmax - rmin), (rmin + r() * (rmax - rmin)) * 0.6, r() * 3, 0, 7); g.fill();
  }
  g.globalAlpha = 1;
};

export const pasto = (rep: [number, number], seco = 0) => tex(512, 512, (g, r) => {
  g.fillStyle = seco ? "#6a8440" : "#4a8434"; g.fillRect(0, 0, 512, 512);
  manchas(g, r, 512, 512, seco ? ["#7a9248", "#5a7a36", "#8a8a52"] : ["#55913c", "#3d742c", "#62a042", "#47803a"], 120, 14, 50, 0.18);
  g.lineCap = "round";
  for (let i = 0; i < 400; i++) { // briznas cortas
    const x = r() * 512, y = r() * 512, l = 4 + r() * 9;
    g.strokeStyle = r() < 0.5 ? "rgba(40,80,25,.35)" : "rgba(150,200,90,.35)"; g.lineWidth = 1.4;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 3, y - l); g.stroke();
  }
}, 11, rep);

export const barro = (rep: [number, number]) => tex(512, 512, (g, r) => {
  g.fillStyle = "#7a5638"; g.fillRect(0, 0, 512, 512);
  manchas(g, r, 512, 512, ["#8a6442", "#654630", "#946e4a", "#5a3e2a"], 260, 6, 40, 0.4);
  for (let i = 0; i < 40; i++) { // charcos y huellas
    g.fillStyle = "rgba(60,40,28,.45)"; g.beginPath(); g.ellipse(r() * 512, r() * 512, 6 + r() * 14, 4 + r() * 8, r() * 3, 0, 7); g.fill();
  }
}, 12, rep);

export const teja = (rep: [number, number]) => tex(512, 512, (g, r) => {
  g.fillStyle = "#a8472c"; g.fillRect(0, 0, 512, 512);
  const fil = 8, col = 10, hf = 512 / fil, wc = 512 / col;
  for (let j = 0; j < fil; j++) for (let i = 0; i < col; i++) {
    const x = i * wc + ((j % 2) * wc) / 2, y = j * hf, tono = ["#b5532f", "#9e4128", "#c06038", "#a84a2e", "#8f3a24"][Math.floor(r() * 5)];
    const gr = g.createLinearGradient(x, 0, x + wc, 0);
    gr.addColorStop(0, "#6e2a1a"); gr.addColorStop(0.25, tono); gr.addColorStop(0.6, tono); gr.addColorStop(1, "#5e2416");
    g.fillStyle = gr; g.fillRect(x, y, wc, hf);
    g.fillStyle = "rgba(40,15,10,.55)"; g.fillRect(x, y + hf - 5, wc, 5);
  }
  manchas(g, r, 512, 512, ["#6a5a3a", "#3e3a2a"], 40, 6, 22, 0.18); // musgo y hollín
}, 13, rep);

/** pared encalada con zócalo de color (casa campesina colombiana) */
export const pared = (rep: [number, number], zocalo = "#2f7f8f", base = "#f1ead8") => tex(512, 512, (g, r) => {
  g.fillStyle = base; g.fillRect(0, 0, 512, 512);
  manchas(g, r, 512, 512, ["#000000", "#ffffff"], 40, 8, 60, 0.04);
  g.fillStyle = zocalo; g.fillRect(0, 400, 512, 112);
  g.fillStyle = "rgba(0,0,0,.18)"; g.fillRect(0, 400, 512, 6);
  manchas(g, r, 512, 112, ["#000000"], 30, 4, 18, 0.06);
  for (let i = 0; i < 10; i++) { g.strokeStyle = "rgba(120,100,80,.25)"; g.lineWidth = 1; g.beginPath(); const x = r() * 512, y = r() * 380; g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 40, y + 20 + r() * 40); g.stroke(); }
}, 14, rep);

export const baldosa = (rep: [number, number]) => tex(512, 512, (g, r) => {
  const n = 4, s = 512 / n;
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    g.fillStyle = (i + j) % 2 ? "#9c5a40" : "#d6c8a8"; g.fillRect(i * s, j * s, s, s);
    manchas(g, r, s, s, ["#000000"], 0, 1, 1);
  }
  g.strokeStyle = "rgba(60,30,20,.6)"; g.lineWidth = 4;
  for (let k = 0; k <= n; k++) { g.beginPath(); g.moveTo(k * s, 0); g.lineTo(k * s, 512); g.stroke(); g.beginPath(); g.moveTo(0, k * s); g.lineTo(512, k * s); g.stroke(); }
  manchas(g, r, 512, 512, ["#5a3a2a", "#ffffff"], 60, 6, 30, 0.08);
}, 15, rep);

export const madera = (rep: [number, number], base = "#8a5a34") => tex(256, 512, (g, r) => {
  g.fillStyle = base; g.fillRect(0, 0, 256, 512);
  for (let i = 0; i < 60; i++) { g.strokeStyle = r() < 0.5 ? "rgba(50,25,10,.25)" : "rgba(255,220,170,.12)"; g.lineWidth = 1 + r() * 2; const x = r() * 256; g.beginPath(); g.moveTo(x, 0); g.bezierCurveTo(x + (r() - 0.5) * 20, 170, x + (r() - 0.5) * 20, 340, x + (r() - 0.5) * 10, 512); g.stroke(); }
  g.fillStyle = "rgba(30,15,5,.6)"; for (let k = 1; k < 4; k++) g.fillRect(k * 64 - 2, 0, 4, 512);
}, 16, rep);

export const agua = (rep: [number, number], noche = false) => tex(512, 512, (g, r) => {
  g.fillStyle = noche ? "#1d3550" : "#3f86a6"; g.fillRect(0, 0, 512, 512);
  manchas(g, r, 512, 512, noche ? ["#26456a", "#162a40"] : ["#4a94b0", "#357a98", "#5aa2b8"], 120, 12, 60, 0.4);
  g.lineCap = "round";
  for (let i = 0; i < 160; i++) { const x = r() * 512, y = r() * 512, l = 10 + r() * 40; g.strokeStyle = `rgba(230,245,240,${0.15 + r() * 0.3})`; g.lineWidth = 2; g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + l / 2, y - 3, x + l, y); g.stroke(); }
}, 17, rep);

export const piedra = () => tex(256, 256, (g, r) => {
  g.fillStyle = "#8a8378"; g.fillRect(0, 0, 256, 256);
  manchas(g, r, 256, 256, ["#9a9384", "#776f64", "#6a6a52", "#a39b8a"], 90, 6, 30, 0.45);
}, 18);

/** tarjeta de pasto alto (alfa) */
export const tarjetaPasto = (seed: number, cols = ["#4f8f34", "#6aa844", "#3d7a2c", "#86b850"]) => tex(256, 256, (g, r) => {
  g.lineCap = "round";
  for (let i = 0; i < 46; i++) {
    const x = 20 + r() * 216, h = 90 + r() * 150, curva = (r() - 0.5) * 70;
    g.strokeStyle = cols[Math.floor(r() * cols.length)]; g.lineWidth = 5 + r() * 5;
    g.beginPath(); g.moveTo(x, 256); g.quadraticCurveTo(x + curva * 0.3, 256 - h * 0.5, x + curva, 256 - h); g.stroke();
  }
}, seed, [1, 1], true);

/** hoja de helecho / mata de selva (alfa) */
export const tarjetaHelecho = (seed: number, col = "#3f8a3a") => tex(256, 256, (g, r) => {
  for (let k = 0; k < 7; k++) {
    const a = -Math.PI / 2 + (k - 3) * 0.32 + (r() - 0.5) * 0.15, L = 120 + r() * 100;
    const x0 = 128, y0 = 250;
    for (let i = 4; i < 26; i++) {
      const t = i / 26, x = x0 + Math.cos(a) * L * t + Math.sin(t * 3) * 10 * (k - 3) / 3, y = y0 + Math.sin(a) * L * t + t * t * 50;
      const w = (1 - t) * 26 + 4;
      g.fillStyle = k % 2 ? col : "#4f9a40";
      g.beginPath(); g.ellipse(x, y, w, 4.5, a + Math.PI / 2 - 0.5, 0, 7); g.fill();
      g.beginPath(); g.ellipse(x, y, w, 4.5, a + Math.PI / 2 + 0.5, 0, 7); g.fill();
    }
  }
}, seed, [1, 1], true);

/** hoja grande tropical (plátano / bijao) para primer plano (alfa) */
export const tarjetaHoja = (seed: number, col = "#3e8c34") => tex(256, 512, (g, r) => {
  g.fillStyle = col;
  g.beginPath(); g.moveTo(128, 505);
  g.bezierCurveTo(10, 400, 0, 120, 128, 8); g.bezierCurveTo(256, 120, 246, 400, 128, 505); g.fill();
  g.strokeStyle = "#b6d67a"; g.lineWidth = 6; g.beginPath(); g.moveTo(128, 505); g.lineTo(128, 12); g.stroke();
  g.strokeStyle = "rgba(20,60,20,.4)"; g.lineWidth = 2;
  for (let y = 60; y < 480; y += 18) { g.beginPath(); g.moveTo(128, y); g.lineTo(28 + r() * 8, y - 40); g.moveTo(128, y); g.lineTo(228 - r() * 8, y - 40); g.stroke(); }
  for (let i = 0; i < 4; i++) { const y = 80 + r() * 380, s = r() < 0.5 ? -1 : 1; g.clearRect(s < 0 ? 0 : 140, y, 120, 3); } // rasgaduras
}, seed, [1, 1], true);

/** sombra de contacto (mancha redonda que oscurece el piso) */
export const manchaSombra = () => tex(128, 128, (g) => {
  const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, "rgb(120,120,120)"); gr.addColorStop(0.55, "rgb(190,190,190)"); gr.addColorStop(1, "rgb(255,255,255)");
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
}, 1, [1, 1], true);
