// Utilería de la finca (nivel «caricatura con detalle», pedido del dueño 03-11): todo por código y de diseño propio.
// Platanera, cafetos con granos rojos, gallinas, tanque de agua, cuerda con ropa, carretilla, canecas de leche, leña,
// cayenas, matas colgantes y banca del corredor. Formas simples con contorno de tinta (la tinta dibuja los bordes).
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { twoTone } from "./shade";

const lam = (color: THREE.ColorRepresentation, extra: THREE.MeshLambertMaterialParameters = {}) => twoTone(new THREE.MeshLambertMaterial({ color, ...extra }));
const malla = (geo: THREE.BufferGeometry, mat: THREE.Material, sombra = true) => { const m = new THREE.Mesh(geo, mat); m.castShadow = sombra; m.receiveShadow = true; return m; };
const caja = (w: number, h: number, d: number, mat: THREE.Material, r = 0.04) => malla(new RoundedBoxGeometry(w, h, d, 2, Math.min(r, w / 2.2, h / 2.2, d / 2.2)), mat);
const en = <T extends THREE.Object3D>(o: T, x: number, y: number, z: number, ry = 0): T => { o.position.set(x, y, z); o.rotation.y = ry; return o; };

/** hoja de plátano: lámina larga curvada (geometría real, la tinta dibuja el borde y la vena) */
function hojaPlatano(largo: number, ancho: number, mat: THREE.Material) {
  const geo = new THREE.PlaneGeometry(ancho, largo, 4, 10), p = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i) + largo / 2, t = y / largo;
    p.setX(i, x * Math.sin(Math.PI * Math.min(1, t * 1.15)) + 0.001);    // se angosta en la punta
    p.setY(i, y);
    p.setZ(i, -0.35 * t * t * largo * 0.4 + Math.abs(x) * 0.25);           // se dobla y hace canal
  }
  geo.computeVertexNormals();
  const m = malla(geo, mat); return m;
}
export function platanera(r: () => number, alto = 3.2) {
  const g = new THREE.Group(), verde = lam("#4f9a32", { side: THREE.DoubleSide }), claro = lam("#6db640", { side: THREE.DoubleSide });
  g.add(en(malla(new THREE.CylinderGeometry(0.14, 0.22, alto, 10), lam("#7d8f45")), 0, alto / 2, 0));
  for (let k = 0; k < 7; k++) {
    const h = hojaPlatano(2.1 + r() * 0.5, 1.0, k % 2 ? verde : claro);
    h.position.y = alto - 0.1; h.rotation.set(-1.15 + r() * 0.3, k * 0.9 + r() * 0.3, 0, "YXZ"); g.add(h);
  }
  const racimo = new THREE.Group(); // racimo de plátanos verdes con su bellota morada
  for (let i = 0; i < 10; i++) racimo.add(en(malla(new THREE.CapsuleGeometry(0.045, 0.2, 3, 6), lam("#8fbf3a")), Math.cos(i * 1.3) * 0.12, -i * 0.05, Math.sin(i * 1.3) * 0.12));
  const bellota = en(malla(new THREE.ConeGeometry(0.1, 0.28, 8), lam("#7a2a52")), 0, -0.68, 0); bellota.rotation.x = Math.PI; racimo.add(bellota);
  g.add(en(racimo, 0.35, alto - 0.5, 0.1));
  return g;
}
export function cafeto(r: () => number) {
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) {
    const b = malla(new THREE.IcosahedronGeometry(0.42 + r() * 0.12, 1), lam(i % 2 ? "#2f7a2a" : "#3d8c30"));
    b.position.set((r() - 0.5) * 0.4, 0.45 + i * 0.32, (r() - 0.5) * 0.3); b.scale.y = 0.8; g.add(b);
  }
  const rojo = lam("#d8352a");
  for (let i = 0; i < 16; i++) { const a = r() * 6.28, y = 0.35 + r() * 0.9, rr = 0.36 + r() * 0.08; g.add(en(malla(new THREE.SphereGeometry(0.045, 6, 5), rojo, false), Math.cos(a) * rr, y, Math.sin(a) * rr)); }
  return g;
}
export function gallina(color = "#f3efe4", r: () => number = Math.random) {
  const g = new THREE.Group(), cuerpo = lam(color);
  const c = malla(new THREE.SphereGeometry(0.17, 12, 10), cuerpo); c.scale.set(1.25, 1, 0.95); c.position.y = 0.24; g.add(c);
  g.add(en(malla(new THREE.SphereGeometry(0.09, 10, 8), cuerpo), 0.17, 0.4, 0));
  const cola = malla(new THREE.ConeGeometry(0.08, 0.18, 6), cuerpo); cola.position.set(-0.2, 0.34, 0); cola.rotation.z = 0.9; g.add(cola);
  const cresta = malla(new THREE.BoxGeometry(0.08, 0.05, 0.02), lam("#d8352a")); cresta.position.set(0.18, 0.5, 0); g.add(cresta);
  const pico = malla(new THREE.ConeGeometry(0.025, 0.07, 6), lam("#f2b31f")); pico.rotation.z = -Math.PI / 2; pico.position.set(0.27, 0.4, 0); g.add(pico);
  for (const z of [-0.05, 0.05]) g.add(en(malla(new THREE.CylinderGeometry(0.012, 0.012, 0.12, 5), lam("#f2b31f")), 0, 0.06, z));
  for (const z of [-0.06, 0.06]) g.add(en(malla(new THREE.SphereGeometry(0.014, 6, 5), lam("#111111"), false), 0.22, 0.43, z));
  g.rotation.y = r() * 6.28;
  return g;
}
export function tanque() {
  const g = new THREE.Group();
  g.add(en(malla(new THREE.CylinderGeometry(0.55, 0.5, 1.05, 20), lam("#2f6fd0")), 0, 1.25, 0));
  g.add(en(malla(new THREE.CylinderGeometry(0.58, 0.58, 0.08, 20), lam("#255bb0")), 0, 1.8, 0));
  const base = lam("#9a9488");
  g.add(en(caja(1.3, 0.7, 1.3, base, 0.03), 0, 0.35, 0));
  return g;
}
export function tendedero(largo = 4.5) {
  const g = new THREE.Group(), palo = lam("#7a5a3a");
  for (const x of [-largo / 2, largo / 2]) g.add(en(malla(new THREE.CylinderGeometry(0.05, 0.06, 1.9, 6), palo), x, 0.95, 0));
  const cuerda = new THREE.CatmullRomCurve3([new THREE.Vector3(-largo / 2, 1.8, 0), new THREE.Vector3(0, 1.68, 0), new THREE.Vector3(largo / 2, 1.8, 0)]);
  g.add(malla(new THREE.TubeGeometry(cuerda, 20, 0.012, 4), lam("#e9e1cc"), false));
  const prendas: [number, string, number, number][] = [[-1.6, "#d8352a", 0.55, 0.6], [-0.9, "#f2c230", 0.45, 0.7], [-0.2, "#2f8f86", 0.6, 0.5], [0.6, "#ffffff", 0.5, 0.65], [1.3, "#2f6fd0", 0.45, 0.8]];
  for (const [x, col, w, h] of prendas) {
    const y = cuerda.getPoint((x + largo / 2) / largo).y;
    const geo = new THREE.PlaneGeometry(w, h, 6, 1), p = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) p.setZ(i, 0.03 * Math.sin(p.getX(i) * 18));
    geo.computeVertexNormals();
    g.add(en(malla(geo, lam(col, { side: THREE.DoubleSide })), x, y - h / 2, 0));
  }
  return g;
}
export function carretilla() {
  const g = new THREE.Group(), metal = lam("#c8452e"), madera = lam("#7a5a3a");
  const cuba = malla(new THREE.CylinderGeometry(0.42, 0.3, 0.3, 4, 1, false), metal); cuba.rotation.y = Math.PI / 4; cuba.scale.set(1.3, 1, 0.8); cuba.position.y = 0.5; g.add(cuba);
  const rueda = malla(new THREE.TorusGeometry(0.16, 0.05, 8, 16), lam("#222222")); rueda.position.set(0.62, 0.2, 0); g.add(rueda);
  for (const z of [-0.2, 0.2]) { const m = malla(new THREE.CylinderGeometry(0.025, 0.025, 1.3, 6), madera); m.rotation.z = Math.PI / 2 - 0.12; m.position.set(-0.1, 0.35, z); g.add(m); }
  for (const z of [-0.2, 0.2]) g.add(en(malla(new THREE.CylinderGeometry(0.02, 0.02, 0.3, 5), madera), -0.3, 0.15, z));
  // algo de leña adentro
  for (let i = 0; i < 4; i++) { const l = malla(new THREE.CylinderGeometry(0.05, 0.05, 0.6, 6), lam("#8a6440")); l.rotation.set(0, i * 0.4, Math.PI / 2); l.position.set(0, 0.68, -0.15 + i * 0.1); g.add(l); }
  return g;
}
export function canecas() {
  const g = new THREE.Group(), lata = lam("#c9cdd2");
  for (const [x, z] of [[0, 0], [0.42, 0.1], [0.2, -0.38]]) {
    g.add(en(malla(new THREE.CylinderGeometry(0.18, 0.2, 0.62, 16), lata), x, 0.31, z));
    g.add(en(malla(new THREE.CylinderGeometry(0.1, 0.12, 0.12, 12), lata), x, 0.68, z));
  }
  return g;
}
export function lena() {
  const g = new THREE.Group(), cafe = ["#8a6440", "#7a5634", "#9a7048"];
  for (let f = 0; f < 3; f++) for (let i = 0; i < 4 - f; i++) {
    const l = malla(new THREE.CylinderGeometry(0.11, 0.11, 0.9, 8), lam(cafe[(i + f) % 3])); l.rotation.x = Math.PI / 2;
    l.position.set(-0.33 + i * 0.22 + f * 0.11, 0.11 + f * 0.19, 0); g.add(l);
    const corte = malla(new THREE.CircleGeometry(0.1, 10), lam("#e0b878"), false); corte.position.set(l.position.x, l.position.y, 0.452); g.add(corte);
  }
  return g;
}
export function cayena(r: () => number) { // arbusto con flores rojas grandes (hibisco)
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) { const b = malla(new THREE.IcosahedronGeometry(0.4 + r() * 0.15, 1), lam("#3a8a2c")); b.position.set((r() - 0.5) * 0.6, 0.4 + r() * 0.3, (r() - 0.5) * 0.3); g.add(b); }
  const flor = lam("#e8344a"), centro = lam("#f2c230");
  for (let i = 0; i < 9; i++) {
    const a = r() * 6.28, y = 0.4 + r() * 0.6, rr = 0.4;
    const f = new THREE.Group();
    for (let k = 0; k < 5; k++) { const p = malla(new THREE.SphereGeometry(0.07, 6, 5), flor, false); p.scale.set(1, 0.4, 0.6); p.position.set(Math.cos(k * 1.256) * 0.06, 0, Math.sin(k * 1.256) * 0.06); f.add(p); }
    f.add(en(malla(new THREE.SphereGeometry(0.025, 6, 5), centro, false), 0, 0.02, 0));
    f.position.set(Math.cos(a) * rr, y, Math.sin(a) * rr + 0.1); f.rotation.x = 1.2; g.add(f);
  }
  return g;
}
export function materaColgante(col = "#c4592e") {
  const g = new THREE.Group();
  g.add(en(malla(new THREE.CylinderGeometry(0.18, 0.12, 0.22, 12), lam(col)), 0, 0, 0));
  for (let i = 0; i < 6; i++) { const h = malla(new THREE.CapsuleGeometry(0.035, 0.4 + (i % 3) * 0.1, 3, 6), lam(i % 2 ? "#3e8c34" : "#2f7a2a")); h.position.set(Math.cos(i) * 0.14, -0.25, Math.sin(i) * 0.14); h.rotation.z = (i - 2.5) * 0.15; g.add(h); }
  g.add(en(malla(new THREE.CylinderGeometry(0.006, 0.006, 0.6, 4), lam("#5a5a5a"), false), 0, 0.4, 0));
  return g;
}
export function banca() {
  const g = new THREE.Group(), madera = lam("#8a5530");
  g.add(en(caja(1.6, 0.08, 0.4, madera, 0.02), 0, 0.45, 0));
  for (const x of [-0.65, 0.65]) g.add(en(caja(0.08, 0.45, 0.36, madera, 0.02), x, 0.22, 0));
  return g;
}
/** postigos de colores para las ventanas de la casa (abiertos hacia los lados) */
export function ventanaCasa(color = "#2f8f86") {
  const g = new THREE.Group();
  g.add(en(caja(0.9, 0.95, 0.06, lam("#3a4f5a"), 0.01), 0, 0, 0));
  for (const s of [-1, 1]) { const p = caja(0.45, 0.95, 0.05, lam(color), 0.01); p.position.set(s * 0.7, 0, 0.05); p.rotation.y = s * 0.25; g.add(p); }
  g.add(en(caja(1.15, 0.08, 0.2, lam("#f7f2e6"), 0.01), 0, -0.52, 0.06));
  const flores = new THREE.Group(); // jardinera con flores en la ventana
  flores.add(en(caja(0.9, 0.16, 0.18, lam("#c4592e"), 0.02), 0, 0, 0));
  for (let i = 0; i < 6; i++) flores.add(en(malla(new THREE.SphereGeometry(0.06, 6, 5), lam(["#e8344a", "#f2c230", "#ffffff"][i % 3]), false), -0.35 + i * 0.14, 0.12, 0));
  g.add(en(flores, 0, -0.62, 0.12));
  return g;
}
