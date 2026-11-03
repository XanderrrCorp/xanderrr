// La casa por dentro, nivel «caricatura con detalle» (pedido del dueño 03-11): sala colombiana llena de objetos, todos
// por código y de diseño propio (técnica: contorno negro en todo, colores limpios, mucha utilería; nada copiado de
// otros canales). Cuarto de 8 x 8 m abierto hacia la cámara; el explorador entra cerca de z = 0.
// Pared de atrás: puerta, sofá con cuadros encima, lámpara de pie, ventana con cortinas y una matera grande.
// Pared izquierda: hamaca de rayas colgada y sombrero vueltiao. Pared derecha: repisa con radio, reloj y calendario.
// Techo de tablilla con ventilador que gira. Noche: luz de luna azul + charco cálido de la lámpara (brillo sin tinta).
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { twoTone } from "./shade";
import { NOINK } from "./ink";
import { tex, rnd, tarjetaHoja } from "./pintura";

const lam = (color: THREE.ColorRepresentation, map?: THREE.Texture | null) => twoTone(new THREE.MeshLambertMaterial({ color, map: map ?? null }));
const malla = (geo: THREE.BufferGeometry, mat: THREE.Material, sombra = true) => {
  const m = new THREE.Mesh(geo, mat); m.castShadow = sombra; m.receiveShadow = true; return m;
};
const caja = (w: number, h: number, d: number, mat: THREE.Material, r = 0.04, sombra = true) =>
  malla(r > 0 ? new RoundedBoxGeometry(w, h, d, 2, Math.min(r, w / 2.2, h / 2.2, d / 2.2)) : new THREE.BoxGeometry(w, h, d), mat, sombra);
const en = <T extends THREE.Object3D>(o: T, x: number, y: number, z: number, ry = 0): T => { o.position.set(x, y, z); o.rotation.y = ry; return o; };

// ---------- texturas (Canvas2D, nítidas: líneas limpias, pocos tonos) ----------
const papel = () => tex(512, 512, (g) => {
  g.fillStyle = "#f4e9cf"; g.fillRect(0, 0, 512, 512);
  g.fillStyle = "#ebdcb8"; for (let x = 0; x < 512; x += 64) g.fillRect(x + 28, 0, 8, 512);         // franjas suaves
  for (let fy = 0; fy < 4; fy++) for (let fx = 0; fx < 4; fx++) {                                    // florecita de café
    const x = fx * 128 + (fy % 2 ? 64 : 0) + 0, y = fy * 128 + 64;
    g.fillStyle = "#c9786a"; for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + 0.4; g.beginPath(); g.ellipse(x + Math.cos(a) * 7, y + Math.sin(a) * 7, 6, 3.5, a, 0, 7); g.fill(); }
    g.fillStyle = "#7a9a52"; g.beginPath(); g.ellipse(x - 11, y + 13, 7, 3, -0.6, 0, 7); g.fill(); g.beginPath(); g.ellipse(x + 11, y + 13, 7, 3, 0.6, 0, 7); g.fill();
    g.fillStyle = "#e9c46a"; g.beginPath(); g.arc(x, y, 3.5, 0, 7); g.fill();
  }
}, 11, [3, 1.5]);

const tablas = () => tex(512, 512, (g, r) => {
  const cols = ["#c98a4e", "#bf7f45", "#d3955a", "#b87a42"];
  for (let i = 0; i < 8; i++) {
    g.fillStyle = cols[Math.floor(r() * cols.length)]; g.fillRect(0, i * 64, 512, 64);
    g.strokeStyle = "rgba(120,70,30,.25)"; g.lineWidth = 2;
    for (let k = 0; k < 3; k++) { const y = i * 64 + 14 + r() * 36; g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(170, y + 6, 340, y - 6, 512, y + 2); g.stroke(); }
    g.fillStyle = "#6e4222"; g.fillRect(0, i * 64, 512, 3);
    const corte = r() * 512; g.fillRect(corte, i * 64, 3, 64);
  }
}, 21, [4, 7]);

const tapete = () => tex(512, 384, (g) => {
  g.fillStyle = "#efe1c2"; g.fillRect(0, 0, 512, 384);
  const banda = (y: number, col: string) => { g.fillStyle = col; g.fillRect(24, y, 464, 14); };
  g.fillStyle = "#b8442e"; g.fillRect(0, 0, 512, 22); g.fillRect(0, 362, 512, 22); g.fillRect(0, 0, 22, 384); g.fillRect(490, 0, 22, 384);
  banda(40, "#e3a33a"); banda(330, "#e3a33a");
  for (let i = 0; i < 9; i++) { // rombos de colores en el centro (diseño geométrico propio)
    const x = 56 + i * 50, y = 192, c = ["#2f8f86", "#b8442e", "#e3a33a"][i % 3];
    g.fillStyle = c; g.beginPath(); g.moveTo(x, y - 46); g.lineTo(x + 22, y); g.lineTo(x, y + 46); g.lineTo(x - 22, y); g.closePath(); g.fill();
    g.fillStyle = "#efe1c2"; g.beginPath(); g.moveTo(x, y - 18); g.lineTo(x + 9, y); g.lineTo(x, y + 18); g.lineTo(x - 9, y); g.closePath(); g.fill();
  }
  g.strokeStyle = "#2a2a2a"; g.lineWidth = 3; g.strokeRect(1.5, 1.5, 509, 381);
}, 31);

const rayas = (cols: string[], ancho = 32, vertical = false) => tex(256, 256, (g) => {
  for (let i = 0; i * ancho < 256; i++) { g.fillStyle = cols[i % cols.length]; if (vertical) g.fillRect(i * ancho, 0, ancho, 256); else g.fillRect(0, i * ancho, 256, ancho); }
}, 41);

const lienzo = (w: number, h: number, draw: (g: CanvasRenderingContext2D) => void) => tex(w, h, (g) => { draw(g); g.strokeStyle = "#1a1a1a"; g.lineWidth = 6; g.strokeRect(3, 3, w - 6, h - 6); });

const cuadroMontanas = () => lienzo(320, 240, (g) => {
  g.fillStyle = "#9fd3e8"; g.fillRect(0, 0, 320, 240);
  g.fillStyle = "#f6c445"; g.beginPath(); g.arc(240, 70, 30, 0, 7); g.fill();
  g.fillStyle = "#5e9a4a"; g.beginPath(); g.moveTo(-10, 240); g.lineTo(90, 90); g.lineTo(190, 240); g.fill();
  g.fillStyle = "#3f7a3a"; g.beginPath(); g.moveTo(110, 240); g.lineTo(220, 110); g.lineTo(340, 240); g.fill();
  g.fillStyle = "#2f5f2e"; for (let i = 0; i < 9; i++) { g.beginPath(); g.arc(30 + i * 34, 222, 12, 0, 7); g.fill(); }
  g.fillStyle = "#c0392b"; for (let i = 0; i < 9; i++) { g.beginPath(); g.arc(34 + i * 34, 218, 3, 0, 7); g.fill(); } // granos de café
});
const cuadroTinto = () => lienzo(200, 240, (g) => {
  g.fillStyle = "#f0a35e"; g.fillRect(0, 0, 200, 240);
  g.fillStyle = "#fff6e6"; g.beginPath(); g.ellipse(100, 150, 60, 14, 0, 0, 7); g.fill();
  g.fillRect(50, 110, 100, 60); g.fillStyle = "#5a3418"; g.beginPath(); g.ellipse(100, 112, 50, 10, 0, 0, 7); g.fill();
  g.strokeStyle = "#fff6e6"; g.lineWidth = 10; g.beginPath(); g.arc(158, 136, 16, -1.4, 1.4); g.stroke();
  g.strokeStyle = "rgba(255,255,255,.8)"; g.lineWidth = 6; for (const x of [80, 100, 120]) { g.beginPath(); g.moveTo(x, 96); g.bezierCurveTo(x - 14, 76, x + 14, 60, x, 40); g.stroke(); }
});
const cuadroGuacamaya = () => lienzo(200, 260, (g) => {
  g.fillStyle = "#2f8f86"; g.fillRect(0, 0, 200, 260);
  g.fillStyle = "#3a6a2a"; g.fillRect(20, 190, 160, 12);
  g.fillStyle = "#d8352a"; g.beginPath(); g.ellipse(100, 130, 32, 52, 0.15, 0, 7); g.fill();
  g.beginPath(); g.arc(108, 80, 24, 0, 7); g.fill();
  g.fillStyle = "#2f6fd0"; g.beginPath(); g.moveTo(80, 150); g.lineTo(60, 240); g.lineTo(100, 175); g.fill();
  g.fillStyle = "#f2c230"; g.beginPath(); g.ellipse(88, 128, 14, 30, 0.3, 0, 7); g.fill();
  g.fillStyle = "#fff"; g.beginPath(); g.arc(116, 76, 7, 0, 7); g.fill(); g.fillStyle = "#111"; g.beginPath(); g.arc(118, 76, 3.5, 0, 7); g.fill();
  g.fillStyle = "#222"; g.beginPath(); g.moveTo(128, 82); g.quadraticCurveTo(146, 86, 132, 100); g.lineTo(124, 92); g.fill();
});
const cuadroFlor = () => lienzo(180, 180, (g) => {
  g.fillStyle = "#f7e6a8"; g.fillRect(0, 0, 180, 180);
  g.fillStyle = "#9b59b6"; for (let k = 0; k < 5; k++) { const a = k * 1.2566; g.beginPath(); g.ellipse(90 + Math.cos(a) * 30, 85 + Math.sin(a) * 30, 26, 15, a, 0, 7); g.fill(); }
  g.fillStyle = "#f4d03f"; g.beginPath(); g.arc(90, 85, 14, 0, 7); g.fill();
  g.strokeStyle = "#4a8a30"; g.lineWidth = 6; g.beginPath(); g.moveTo(90, 110); g.lineTo(90, 170); g.stroke();
});
const calendario = () => tex(160, 220, (g) => {
  g.fillStyle = "#fffdf6"; g.fillRect(0, 0, 160, 220);
  g.fillStyle = "#5e9a4a"; g.fillRect(8, 8, 144, 80); g.fillStyle = "#f6c445"; g.beginPath(); g.arc(120, 34, 14, 0, 7); g.fill();
  g.fillStyle = "#3f7a3a"; g.beginPath(); g.moveTo(8, 88); g.lineTo(60, 40); g.lineTo(110, 88); g.fill();
  g.fillStyle = "#c0392b"; g.font = "bold 20px sans-serif"; g.textAlign = "center"; g.fillText("NOVIEMBRE", 80, 112);
  g.strokeStyle = "#999"; g.lineWidth = 1; for (let i = 0; i < 6; i++) for (let j = 0; j < 7; j++) g.strokeRect(10 + j * 20, 122 + i * 15, 20, 15);
  g.strokeStyle = "#c0392b"; g.lineWidth = 2.5; for (let j = 0; j < 4; j++) { const x = 10 + j * 20, y = 137; g.beginPath(); g.moveTo(x + 4, y + 3); g.lineTo(x + 16, y + 12); g.moveTo(x + 16, y + 3); g.lineTo(x + 4, y + 12); g.stroke(); }
  g.strokeStyle = "#1a1a1a"; g.lineWidth = 4; g.strokeRect(2, 2, 156, 216);
});
const relojCara = () => tex(256, 256, (g) => {
  g.fillStyle = "#fffaf0"; g.beginPath(); g.arc(128, 128, 124, 0, 7); g.fill();
  g.fillStyle = "#1a1a1a"; for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; g.save(); g.translate(128 + Math.sin(a) * 100, 128 - Math.cos(a) * 100); g.rotate(a); g.fillRect(-4, -12, 8, k % 3 ? 14 : 24); g.restore(); }
  g.lineWidth = 10; g.strokeStyle = "#1a1a1a"; g.beginPath(); g.arc(128, 128, 120, 0, 7); g.stroke();
}, 51, [1, 1], true);
const vueltiao = () => tex(256, 256, (g) => { // anillos negros y crema (trenzado del sombrero)
  for (let i = 0; i < 12; i++) { g.fillStyle = i % 2 ? "#1d1a16" : "#efe2bf"; g.beginPath(); g.arc(128, 128, 128 - i * 10.6, 0, 7); g.fill(); }
  g.fillStyle = "#1d1a16"; for (let k = 0; k < 24; k++) { const a = k * Math.PI / 12; g.beginPath(); g.arc(128 + Math.cos(a) * 112, 128 + Math.sin(a) * 112, 4, 0, 7); g.fill(); }
}, 61, [1, 1], true);
const afuera = (noche: boolean) => tex(512, 384, (g, r) => {
  const cielo = g.createLinearGradient(0, 0, 0, 260);
  if (noche) { cielo.addColorStop(0, "#0c1a46"); cielo.addColorStop(1, "#2c4a8c"); } else { cielo.addColorStop(0, "#5fb3ea"); cielo.addColorStop(1, "#cdeaf6"); }
  g.fillStyle = cielo; g.fillRect(0, 0, 512, 384);
  if (noche) { g.fillStyle = "#fff8d8"; for (let i = 0; i < 40; i++) g.fillRect(r() * 512, r() * 200, 2, 2); g.beginPath(); g.arc(400, 70, 28, 0, 7); g.fill(); g.fillStyle = "#0c1a46"; g.beginPath(); g.arc(414, 62, 26, 0, 7); g.fill(); }
  else { g.fillStyle = "#ffffff"; for (const [x, y] of [[90, 70], [330, 50]]) { for (let k = 0; k < 4; k++) { g.beginPath(); g.arc(x + k * 24, y + (k % 2) * 6, 22, 0, 7); g.fill(); } } }
  g.fillStyle = noche ? "#1f3456" : "#6fae5a"; g.beginPath(); g.moveTo(0, 300); g.lineTo(140, 170); g.lineTo(300, 300); g.fill();
  g.fillStyle = noche ? "#172a48" : "#4f9446"; g.beginPath(); g.moveTo(180, 300); g.lineTo(380, 150); g.lineTo(560, 300); g.fill();
  g.fillStyle = noche ? "#3a2a2a" : "#c4592e"; g.beginPath(); g.moveTo(250, 260); g.lineTo(330, 210); g.lineTo(512, 210); g.lineTo(512, 260); g.fill(); // techo del vecino
  g.fillStyle = noche ? "#4a4a5a" : "#f1e4c4"; g.fillRect(260, 260, 252, 124);
  g.fillStyle = noche ? "#f6c96a" : "#5a3a22"; g.fillRect(300, 290, 40, 40); g.fillRect(420, 290, 40, 40);
  g.fillStyle = noche ? "#203a30" : "#5aa04a"; g.fillRect(0, 300, 260, 84);
}, 71);
const brillo = (col: string) => tex(256, 256, (g) => {
  const rg = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  rg.addColorStop(0, col); rg.addColorStop(0.35, col.replace(/[\d.]+\)$/, "0.45)")); rg.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = rg; g.fillRect(0, 0, 256, 256);
}, 81, [1, 1], true);

/** tarjeta de brillo (sin tinta, se suma a lo de atrás): el charco de luz de la lámpara */
const glow = (w: number, h: number, col: string, intensidad: number) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: brillo(col), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: intensidad, fog: false }));
  m.layers.set(NOINK); m.renderOrder = 5; return m;
};

// ---------- muebles y utilería ----------
function sofa(color: string) {
  const g = new THREE.Group(), tela = lam(color), oscuro = lam(new THREE.Color(color).multiplyScalar(0.8)), pata = lam("#4a2e1a");
  g.add(en(caja(2.5, 0.42, 0.95, oscuro, 0.06), 0, 0.33, 0));
  for (const x of [-0.58, 0.58]) g.add(en(caja(1.12, 0.2, 0.86, tela, 0.08), x, 0.64, 0.05));                 // cojines del asiento
  for (const x of [-0.58, 0.58]) { const c = en(caja(1.1, 0.62, 0.24, tela, 0.1), x, 0.98, -0.36); c.rotation.x = -0.12; g.add(c); } // espaldar
  for (const s of [-1, 1]) g.add(en(caja(0.26, 0.72, 0.98, oscuro, 0.1), s * 1.32, 0.5, 0));                    // brazos
  for (const [x, z] of [[-1.3, 0.38], [1.3, 0.38], [-1.3, -0.38], [1.3, -0.38]]) g.add(en(malla(new THREE.CylinderGeometry(0.05, 0.035, 0.14, 8), pata), x, 0.07, z));
  const cojin = en(caja(0.42, 0.4, 0.14, lam("#e3a33a"), 0.07), -0.95, 0.88, -0.18); cojin.rotation.set(-0.25, 0.3, 0.15); g.add(cojin);
  return g;
}
function mesaCentro() {
  const g = new THREE.Group(), madera = lam("#8a5530");
  g.add(en(caja(1.3, 0.07, 0.7, madera, 0.02), 0, 0.42, 0));
  g.add(en(caja(1.15, 0.04, 0.58, madera, 0.01), 0, 0.12, 0));
  for (const [x, z] of [[-0.58, -0.28], [0.58, -0.28], [-0.58, 0.28], [0.58, 0.28]]) g.add(en(caja(0.07, 0.42, 0.07, madera, 0.01), x, 0.21, z));
  const pocillo = new THREE.Group(); // pocillo de tinto con plato
  pocillo.add(en(malla(new THREE.CylinderGeometry(0.11, 0.11, 0.015, 20), lam("#fffaf0")), 0, 0, 0));
  pocillo.add(en(malla(new THREE.CylinderGeometry(0.055, 0.045, 0.08, 16), lam("#fffaf0")), 0, 0.045, 0));
  const asa = en(malla(new THREE.TorusGeometry(0.025, 0.008, 6, 12), lam("#fffaf0")), 0.06, 0.05, 0); g.add(en(pocillo, 0.3, 0.46, 0.05)); pocillo.add(asa);
  const libro = en(caja(0.3, 0.05, 0.22, lam("#2f6fd0"), 0.01), -0.3, 0.48, -0.05); libro.rotation.y = 0.3; g.add(libro);
  const libro2 = en(caja(0.26, 0.04, 0.2, lam("#d8352a"), 0.01), -0.32, 0.525, -0.05); libro2.rotation.y = 0.1; g.add(libro2);
  return g;
}
function lampara(noche: boolean) {
  const g = new THREE.Group(), metal = lam("#2a2a2a");
  g.add(en(malla(new THREE.CylinderGeometry(0.2, 0.24, 0.05, 20), metal), 0, 0.025, 0));
  g.add(en(malla(new THREE.CylinderGeometry(0.025, 0.025, 1.55, 8), metal), 0, 0.8, 0));
  const pantalla = malla(new THREE.CylinderGeometry(0.2, 0.34, 0.38, 24, 1, true), noche
    ? new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 1.6, 0.9), side: THREE.DoubleSide }) : twoTone(new THREE.MeshLambertMaterial({ color: "#f3e3c0", side: THREE.DoubleSide })));
  g.add(en(pantalla, 0, 1.68, 0));
  if (noche) {
    const bombillo = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color(4, 3, 1.6) }));
    bombillo.layers.set(NOINK); g.add(en(bombillo, 0, 1.58, 0));
  }
  return g;
}
function matera(r: () => number, alto = 1.3) {
  const g = new THREE.Group();
  g.add(en(malla(new THREE.CylinderGeometry(0.3, 0.22, 0.5, 16), lam("#c4592e")), 0, 0.25, 0));
  g.add(en(malla(new THREE.CylinderGeometry(0.32, 0.32, 0.06, 16), lam("#a8461f")), 0, 0.5, 0));
  for (let i = 0; i < 9; i++) { // hojas grandes en abanico (tarjetas sin tinta: el dibujo trae su borde)
    const mat = twoTone(new THREE.MeshLambertMaterial({ map: tarjetaHoja(90 + i, i % 2 ? "#3e8c34" : "#2f7a2a"), alphaTest: 0.5, side: THREE.DoubleSide }));
    const h = new THREE.Mesh(new THREE.PlaneGeometry(0.5, alto * 0.75), mat); h.geometry.translate(0, alto * 0.37, 0);
    h.layers.set(NOINK); h.castShadow = true;
    h.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: mat.map, alphaTest: 0.5 });
    h.position.y = 0.48; h.rotation.set(0, i * 2.4 + r() * 0.3, (i % 2 ? 1 : -1) * (0.25 + r() * 0.4)); g.add(h);
  }
  return g;
}
function cuadro(map: THREE.Texture, w: number, h: number, marco = "#5a3418") {
  const g = new THREE.Group();
  g.add(en(caja(w + 0.08, h + 0.08, 0.04, lam(marco), 0.01, false), 0, 0, 0));
  g.add(en(malla(new THREE.PlaneGeometry(w, h), lam("#ffffff", map), false), 0, 0, 0.022));
  return g;
}
function ventana(noche: boolean, ancho = 1.5, alto = 1.3) {
  const g = new THREE.Group(), marco = lam("#f7f2e6");
  const vista = new THREE.Mesh(new THREE.PlaneGeometry(ancho, alto), new THREE.MeshBasicMaterial({ map: afuera(noche), fog: false, color: noche ? new THREE.Color(1, 1, 1) : new THREE.Color(1.25, 1.25, 1.25) }));
  g.add(vista);
  for (const [x, y, w, h] of [[0, alto / 2, ancho + 0.2, 0.1], [0, -alto / 2, ancho + 0.3, 0.12], [-ancho / 2, 0, 0.1, alto], [ancho / 2, 0, 0.1, alto], [0, 0, 0.05, alto], [0, 0.1, ancho, 0.05]] as const)
    g.add(en(caja(w, h, 0.1, marco, 0.01, false), x, y, 0.05));
  g.add(en(caja(ancho + 0.4, 0.06, 0.24, marco, 0.01, false), 0, -alto / 2 - 0.06, 0.12)); // alféizar
  return g;
}
function cortina(color: string, alto = 2.1, ancho = 0.6) { // tela con pliegues reales (la tinta dibuja los dobleces)
  const geo = new THREE.PlaneGeometry(ancho, alto, 24, 1), p = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) p.setZ(i, 0.05 * Math.sin(p.getX(i) / ancho * Math.PI * 7));
  geo.computeVertexNormals();
  const m = malla(geo, twoTone(new THREE.MeshLambertMaterial({ color, map: rayas(["#ffffff", "#f3e9d0"], 16, true), side: THREE.DoubleSide })), false);
  return m;
}
function puerta() {
  const g = new THREE.Group(), madera = lam("#7a4a26"), marco = lam("#f7f2e6");
  g.add(en(caja(1.0, 2.1, 0.06, madera, 0.01, false), 0, 1.05, 0));
  for (const [x, y, w, h] of [[-0.22, 1.5, 0.36, 0.7], [0.22, 1.5, 0.36, 0.7], [-0.22, 0.55, 0.36, 0.7], [0.22, 0.55, 0.36, 0.7]] as const)
    g.add(en(caja(w, h, 0.03, lam("#8a5a32"), 0.01, false), x, y, 0.035));
  for (const [x, y, w, h] of [[-0.56, 1.1, 0.1, 2.25], [0.56, 1.1, 0.1, 2.25], [0, 2.22, 1.22, 0.1]] as const) g.add(en(caja(w, h, 0.08, marco, 0.01, false), x, y, 0.02));
  g.add(en(malla(new THREE.SphereGeometry(0.04, 10, 8), lam("#e3b23a")), 0.38, 1.05, 0.08));
  return g;
}
function hamaca(desde: THREE.Vector3, hasta: THREE.Vector3) { // tela de rayas que cuelga entre dos ganchos
  const n = 30, m = 6, ancho = 0.9, pos: number[] = [], uv: number[] = [], idx: number[] = [];
  const dir = hasta.clone().sub(desde), L = dir.length(), lado = new THREE.Vector3(-dir.z, 0, dir.x).normalize();
  for (let i = 0; i <= n; i++) for (let j = 0; j <= m; j++) {
    const t = i / n, s = j / m - 0.5, abre = Math.sin(t * Math.PI) ** 0.6;           // se abre en el centro
    const p = desde.clone().addScaledVector(dir, t).addScaledVector(lado, s * ancho * abre);
    p.y -= Math.sin(t * Math.PI) * 0.7 - Math.abs(s) * abre * 0.35 * Math.sin(t * Math.PI); // panza y bordes más altos
    pos.push(p.x, p.y, p.z); uv.push(t * (L / 0.5), j / m);
  }
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) { const a = i * (m + 1) + j, b = a + m + 1; idx.push(a, b, a + 1, b, b + 1, a + 1); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2)); geo.setIndex(idx); geo.computeVertexNormals();
  const mapa = rayas(["#d8352a", "#f2c230", "#2f8f86", "#2f6fd0", "#e3843a"], 52, true); mapa.repeat.set(1, 1);
  const g = new THREE.Group();
  g.add(malla(geo, twoTone(new THREE.MeshLambertMaterial({ map: mapa, side: THREE.DoubleSide }))));
  for (const p of [desde, hasta]) g.add(en(malla(new THREE.TorusGeometry(0.05, 0.015, 6, 12), lam("#555555"), false), p.x, p.y, p.z));
  return g;
}
function sombrero() { // vueltiao colgado en la pared (ala plana + copa), mirando hacia el cuarto
  const g = new THREE.Group(), mapa = vueltiao();
  const ala = malla(new THREE.CylinderGeometry(0.36, 0.36, 0.02, 40), twoTone(new THREE.MeshLambertMaterial({ map: mapa })), false);
  g.add(ala);
  const copa = malla(new THREE.CylinderGeometry(0.13, 0.16, 0.16, 28), twoTone(new THREE.MeshLambertMaterial({ map: rayas(["#1d1a16", "#efe2bf"], 21) })), false);
  copa.position.y = 0.09; g.add(copa);
  g.rotation.z = -Math.PI / 2; // la copa hacia +x (sale de la pared izquierda)
  return g;
}
function repisa() {
  const g = new THREE.Group(), madera = lam("#8a5530");
  g.add(en(caja(1.4, 0.05, 0.3, madera, 0.01), 0, 0, 0));
  const radio = new THREE.Group(); // radio viejo de perillas
  radio.add(en(caja(0.46, 0.28, 0.2, lam("#b8442e"), 0.04), 0, 0, 0));
  radio.add(en(malla(new THREE.CircleGeometry(0.09, 20), lam("#e9d8b0"), false), -0.1, 0, 0.101));
  for (const x of [0.1, 0.18]) { const k = en(malla(new THREE.CylinderGeometry(0.025, 0.025, 0.03, 10), lam("#2a2a2a")), x, -0.04, 0.11); k.rotation.x = Math.PI / 2; radio.add(k); }
  g.add(en(radio, -0.35, 0.17, 0));
  for (let i = 0; i < 4; i++) g.add(en(caja(0.07, 0.26 + (i % 2) * 0.05, 0.2, lam(["#2f6fd0", "#e3a33a", "#2f8f86", "#d8352a"][i]), 0.01), 0.2 + i * 0.08, 0.16, 0));
  g.add(en(malla(new THREE.CylinderGeometry(0.08, 0.06, 0.14, 12), lam("#c4592e")), 0.55, 0.1, 0));
  g.add(en(malla(new THREE.SphereGeometry(0.12, 10, 8), lam("#3e8c34")), 0.55, 0.24, 0));
  return g;
}
function reloj() {
  const g = new THREE.Group();
  const aro = malla(new THREE.CylinderGeometry(0.26, 0.26, 0.06, 32), lam("#2f8f86")); aro.rotation.x = Math.PI / 2; g.add(aro);
  const cara = malla(new THREE.CircleGeometry(0.23, 32), twoTone(new THREE.MeshLambertMaterial({ map: relojCara(), transparent: false })), false); cara.position.z = 0.032; g.add(cara);
  const hora = en(caja(0.02, 0.12, 0.01, lam("#1a1a1a"), 0, false), 0, 0.05, 0.04), minuto = en(caja(0.014, 0.18, 0.01, lam("#1a1a1a"), 0, false), 0, 0.08, 0.045);
  const ph = new THREE.Group(), pm = new THREE.Group(); ph.add(hora); pm.add(minuto); hora.position.set(0, 0.05, 0.04); minuto.position.set(0, 0.08, 0.045); g.add(ph, pm);
  return { g, mover: (t: number) => { pm.rotation.z = -t * 0.6; ph.rotation.z = -1.2 - t * 0.05; } };
}
function ventilador() {
  const g = new THREE.Group(), cafe = lam("#a8743e"), metal = lam("#e9e1cc");
  g.add(en(malla(new THREE.CylinderGeometry(0.02, 0.02, 0.4, 8), metal), 0, -0.2, 0));
  g.add(en(malla(new THREE.CylinderGeometry(0.16, 0.12, 0.16, 16), metal), 0, -0.45, 0));
  const aspas = new THREE.Group();
  for (let k = 0; k < 4; k++) { const a = en(caja(0.95, 0.025, 0.2, cafe, 0.01, false), 0, 0, 0); a.position.set(Math.cos(k * Math.PI / 2) * 0.6, 0, Math.sin(k * Math.PI / 2) * 0.6); a.rotation.set(0.22, -k * Math.PI / 2, 0, "YXZ"); aspas.add(a); }
  aspas.position.y = -0.52; g.add(aspas);
  return { g, mover: (t: number) => { aspas.rotation.y = t * 2.2; } };
}

function butaca() { // silla de madera con asiento y espaldar de cuero (taburete)
  const g = new THREE.Group(), madera = lam("#7a4a26"), cuero = lam("#b87a42");
  for (const [x, z] of [[-0.25, -0.25], [0.25, -0.25], [-0.25, 0.25], [0.25, 0.25]]) g.add(en(caja(0.07, 0.48, 0.07, madera, 0.01), x, 0.24, z));
  g.add(en(caja(0.6, 0.06, 0.6, cuero, 0.02), 0, 0.5, 0));
  for (const x of [-0.25, 0.25]) g.add(en(caja(0.07, 0.6, 0.07, madera, 0.01), x, 0.82, -0.25));
  g.add(en(caja(0.6, 0.32, 0.04, cuero, 0.02), 0, 0.92, -0.26));
  return g;
}
function canasto() { // canasto tejido con frutas (mango, banano)
  const g = new THREE.Group();
  g.add(en(malla(new THREE.CylinderGeometry(0.34, 0.26, 0.32, 18), lam("#ffffff", rayas(["#c9a063", "#a87c45"], 16))), 0, 0.16, 0));
  for (const [x, z, c] of [[-0.1, 0.05, "#f2a32a"], [0.12, -0.05, "#e3532f"], [0.02, 0.14, "#8ab83a"]] as const) g.add(en(malla(new THREE.SphereGeometry(0.11, 12, 10), lam(c)), x, 0.36, z));
  const banano = malla(new THREE.TorusGeometry(0.16, 0.035, 8, 16, 2.0), lam("#f6d23a")); banano.rotation.set(-1.2, 0, 0.4); banano.position.set(-0.02, 0.4, -0.12); g.add(banano);
  return g;
}

export type Sala = { root: THREE.Group; animar: (t: number) => void; piso: THREE.Mesh };

export function construirSala(noche: boolean): Sala {
  const r = rnd(4242), root = new THREE.Group();
  const W = 8, Z0 = -4.5, Z1 = 6, H = 3.1, ZOC = 0.95;
  const piso = malla(new THREE.PlaneGeometry(W, Z1 - Z0), lam("#ffffff", tablas()), false);
  piso.rotation.x = -Math.PI / 2; piso.position.z = (Z0 + Z1) / 2; root.add(piso);
  // paredes: papel de colgadura arriba, zócalo verde abajo, moldura de madera entre los dos
  const papelMat = lam("#ffffff", papel()), zocMat = lam("#3e9a8c"), moldura = lam("#f7f2e6");
  const pared = (w: number, x: number, z: number, ry: number) => {
    const g = new THREE.Group();
    g.add(en(malla(new THREE.PlaneGeometry(w, H - ZOC), papelMat, false), 0, ZOC + (H - ZOC) / 2, 0));
    g.add(en(malla(new THREE.PlaneGeometry(w, ZOC), zocMat, false), 0, ZOC / 2, 0));
    g.add(en(caja(w, 0.07, 0.05, moldura, 0.01, false), 0, ZOC, 0.02));
    g.add(en(caja(w, 0.12, 0.04, moldura, 0.01, false), 0, 0.06, 0.02));       // guardaescoba
    g.add(en(caja(w, 0.12, 0.08, moldura, 0.01, false), 0, H - 0.06, 0.03));    // cornisa
    g.position.set(x, 0, z); g.rotation.y = ry; root.add(g);
  };
  pared(W, 0, Z0, 0);
  pared(Z1 - Z0, -W / 2, (Z0 + Z1) / 2, Math.PI / 2);
  pared(Z1 - Z0, W / 2, (Z0 + Z1) / 2, -Math.PI / 2);
  // techo de tablilla blanca con vigas
  const techo = malla(new THREE.PlaneGeometry(W, Z1 - Z0), lam("#ffffff", rayas(["#f4f1e8", "#e6e1d2"], 8)), false);
  techo.rotation.x = Math.PI / 2; techo.position.set(0, H, (Z0 + Z1) / 2); root.add(techo);
  // pared de atrás
  const pu = puerta(); root.add(en(pu, -3.0, 0, Z0 + 0.04));
  const so = sofa("#d0583a"); root.add(en(so, -0.65, 0, Z0 + 0.62));
  root.add(en(cuadro(cuadroMontanas(), 0.8, 0.6), -1.0, 2.05, Z0 + 0.03));
  root.add(en(cuadro(cuadroTinto(), 0.42, 0.5, "#2a2a2a"), -0.0, 2.15, Z0 + 0.03));
  root.add(en(cuadro(cuadroGuacamaya(), 0.42, 0.55, "#e3b23a"), -1.85, 2.1, Z0 + 0.03));
  root.add(en(cuadro(cuadroFlor(), 0.34, 0.34, "#2a2a2a"), -0.02, 1.6, Z0 + 0.03));
  const la = lampara(noche); root.add(en(la, 0.95, 0, Z0 + 0.45));
  const ve = ventana(noche); root.add(en(ve, 2.55, 1.7, Z0 + 0.02));
  for (const x of [1.55, 3.55]) root.add(en(cortina("#e7ad2e"), x, 1.72, Z0 + 0.14));
  root.add(en(caja(2.6, 0.04, 0.04, lam("#6a4428"), 0.01, false), 2.55, 2.8, Z0 + 0.14)); // varilla
  root.add(en(matera(r, 1.5), 3.55, 0, Z0 + 0.65));
  // pared izquierda: hamaca y sombrero vueltiao
  root.add(hamaca(new THREE.Vector3(-W / 2 + 0.05, 1.75, -3.9), new THREE.Vector3(-W / 2 + 0.05, 1.75, -1.0)));
  root.add(en(sombrero(), -W / 2 + 0.03, 2.35, -1.5));
  root.add(en(cuadro(cuadroFlor(), 0.4, 0.4, "#2f8f86"), -W / 2 + 0.03, 2.3, -3.3, Math.PI / 2));
  // pared derecha: repisa con radio, reloj y calendario
  root.add(en(repisa(), W / 2 - 0.17, 1.45, -2.2, -Math.PI / 2));
  const re = reloj(); root.add(en(re.g, W / 2 - 0.04, 2.35, -2.2, -Math.PI / 2));
  root.add(en(malla(new THREE.PlaneGeometry(0.4, 0.55), lam("#ffffff", calendario()), false), W / 2 - 0.02, 1.95, -0.8, -Math.PI / 2));
  root.add(en(caja(0.08, 0.12, 0.02, moldura, 0.01, false), W / 2 - 0.02, 1.25, -0.3, -Math.PI / 2)); // interruptor
  root.add(en(matera(r, 1.1), W / 2 - 0.5, 0, 1.6));
  // centro: tapete y mesa con pocillo de tinto
  const tap = malla(new THREE.PlaneGeometry(3.4, 2.4), lam("#ffffff", tapete()), false); tap.rotation.x = -Math.PI / 2; tap.position.set(-0.5, 0.008, -2.3); root.add(tap);
  root.add(en(mesaCentro(), -0.6, 0, -2.45));
  const bu = butaca(); bu.rotation.y = 0.7; root.add(en(bu, -2.4, 0, 1.0, 0.6));
  root.add(en(canasto(), 2.5, 0, 1.6));
  const fan = ventilador(); root.add(en(fan.g, -0.3, H, -1.5));
  // noche: charco cálido de la lámpara (sobre pared, sofá y piso) y la luz azul de la ventana
  if (noche) {
    const p1 = glow(3.4, 3.4, "rgba(255,170,80,0.9)", 0.75); p1.position.set(0.95, 1.6, Z0 + 0.12); root.add(p1);
    const p2 = glow(4.2, 2.6, "rgba(255,150,70,0.8)", 0.45); p2.rotation.x = -Math.PI / 2; p2.position.set(0.6, 0.02, Z0 + 1.6); root.add(p2);
    const p3 = glow(2.4, 2.0, "rgba(120,160,255,0.8)", 0.35); p3.position.set(2.55, 1.6, Z0 + 0.12); root.add(p3);
  }
  // sombras: solo los muebles (el «sol» de interior no lo tapan paredes ni techo)
  root.traverse((o) => { if ((o as THREE.Mesh).isMesh) (o as THREE.Mesh).receiveShadow = true; });
  return { root, piso, animar: (t) => { re.mover(t); fan.mover(t); } };
}
