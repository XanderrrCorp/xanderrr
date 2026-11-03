// Los 4 escenarios de Peligro Tropical, hechos por código (diseño propio, sin modelos de terceros): casa colombiana por
// dentro, finca con potrero, cerca y casa de teja, selva espesa y orilla de río. Todos con el mismo contrato: el piso en
// y = 0, el explorador camina por el eje x cerca de z = 0 y la cámara base mira hacia -z.
import * as THREE from "three";
import { twoTone } from "./shade";
import { NOINK } from "./ink";
import * as P from "./pintura";

export type NombreEscenario = "casa" | "finca" | "selva" | "rio";
export const ESCENARIOS: NombreEscenario[] = ["casa", "finca", "selva", "rio"];

export type Escena = {
  root: THREE.Group;
  /** objetos animados por cuadro (agua que corre, hojas que se mecen) */
  animar: (t: number) => void;
  /** dónde se para el explorador y dónde aparece el animal por defecto */
  actor: [number, number]; animal: [number, number];
  /** cámara base: posición y punto al que mira */
  cam: { pos: [number, number, number]; look: [number, number, number]; fov: number };
  interior: boolean;
  /** niebla propia del escenario (la selva: verde y cerrada); se mezcla con la de la luz */
  niebla?: { color: string; cerca: number; lejos: number };
};

const lam = (color: THREE.ColorRepresentation, map?: THREE.Texture, extra: THREE.MeshLambertMaterialParameters = {}) =>
  twoTone(new THREE.MeshLambertMaterial({ color, map: map ?? null, ...extra }));
const tarjetaMat = (map: THREE.Texture, color: THREE.ColorRepresentation = "#ffffff") =>
  twoTone(new THREE.MeshLambertMaterial({ color, map, alphaTest: 0.5, side: THREE.DoubleSide }));

const malla = (geo: THREE.BufferGeometry, mat: THREE.Material, sombra = true) => {
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = sombra; m.receiveShadow = true;
  return m;
};
/** tarjeta con transparencia: fuera de la tinta del mundo, con sombra recortada */
const tarjeta = (geo: THREE.BufferGeometry, mat: THREE.MeshLambertMaterial, normalArriba = true) => {
  if (normalArriba) { const n = geo.attributes.normal as THREE.BufferAttribute; for (let i = 0; i < n.count; i++) n.setXYZ(i, 0, 1, 0); }
  const m = malla(geo, mat);
  m.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: mat.map, alphaTest: 0.5 });
  m.layers.set(NOINK);
  return m;
};

const jitter = (geo: THREE.BufferGeometry, r: () => number, k: number) => {
  const p = geo.attributes.position as THREE.BufferAttribute, v = new THREE.Vector3(), mapa = new Map<string, number>();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const key = `${v.x.toFixed(3)},${v.y.toFixed(3)},${v.z.toFixed(3)}`; // vértices repetidos se mueven igual (sin grietas)
    if (!mapa.has(key)) mapa.set(key, 1 + (r() - 0.5) * k);
    v.multiplyScalar(mapa.get(key)!);
    p.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  return geo;
};

const VERDES = ["#3f7a2a", "#4a8a30", "#356f26", "#468a2c"];

export function arbol(r: () => number, alto = 6, verdes = VERDES): THREE.Group {
  const g = new THREE.Group();
  const tronco = malla(new THREE.CylinderGeometry(0.16, 0.3, alto * 0.62, 8), lam("#6a4a32"));
  tronco.position.y = alto * 0.31; tronco.rotation.z = (r() - 0.5) * 0.12; g.add(tronco);
  const n = 3 + Math.floor(r() * 3);
  for (let i = 0; i < n; i++) {
    const rad = alto * (0.2 + r() * 0.12);
    const copa = malla(jitter(new THREE.IcosahedronGeometry(rad, 4), r, 0.06), lam(verdes[Math.floor(r() * verdes.length)]));
    copa.receiveShadow = false;
    copa.position.set((r() - 0.5) * alto * 0.35, alto * (0.62 + r() * 0.25), (r() - 0.5) * alto * 0.3);
    copa.scale.y = 0.8;
    g.add(copa);
  }
  return g;
}

const hojaPalma = (() => {
  let t: THREE.Texture | null = null;
  return () => (t ??= P.tarjetaHelecho(77, "#3c8a36"));
})();

export function palma(r: () => number, alto = 8): THREE.Group {
  const g = new THREE.Group();
  const curva = new THREE.CatmullRomCurve3([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0.4, alto * 0.4, 0), new THREE.Vector3(0.2 + r() * 0.8, alto, (r() - 0.5))]);
  g.add(malla(new THREE.TubeGeometry(curva, 16, 0.17, 7), lam("#8a7350")));
  const tope = curva.getPoint(1);
  const mat = tarjetaMat(hojaPalma(), "#ffffff");
  for (let k = 0; k < 8; k++) {
    const geo = new THREE.PlaneGeometry(1.4, 3.6, 1, 8);
    const p = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < p.count; i++) { const y = p.getY(i) + 1.8; p.setZ(i, -0.12 * y * y); p.setY(i, y); } // se dobla hacia abajo
    geo.computeVertexNormals();
    const h = tarjeta(geo, mat);
    h.position.copy(tope);
    h.rotation.set(-Math.PI / 2 + 0.5, (k / 8) * Math.PI * 2 + r() * 0.3, 0, "YXZ");
    g.add(h);
  }
  return g;
}

export function arbusto(r: () => number, tam = 1): THREE.Group {
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) {
    const b = malla(jitter(new THREE.IcosahedronGeometry(tam * (0.5 + r() * 0.3), 2), r, 0.15), lam(VERDES[Math.floor(r() * VERDES.length)]));
    b.receiveShadow = false;
    b.position.set((r() - 0.5) * tam, tam * 0.4, (r() - 0.5) * tam * 0.6); b.scale.y = 0.75;
    g.add(b);
  }
  return g;
}

export function roca(r: () => number, tam = 1): THREE.Mesh {
  const m = malla(jitter(new THREE.DodecahedronGeometry(tam, 1), r, 0.35), lam("#ffffff", P.piedra()));
  m.scale.y = 0.6; m.position.y = tam * 0.25; m.rotation.y = r() * 6;
  return m;
}

const PASTOS: THREE.Texture[] = [];
export function mata(r: () => number, ancho = 1.2, alto = 0.9, tipo: "pasto" | "helecho" = "pasto"): THREE.Group {
  if (!PASTOS.length) PASTOS.push(P.tarjetaPasto(21), P.tarjetaPasto(22, ["#8a9a44", "#a3a85a", "#6f8a3c"]), P.tarjetaHelecho(23), P.tarjetaHelecho(24, "#2f7a34"));
  const t = tipo === "pasto" ? PASTOS[Math.floor(r() * 2)] : PASTOS[2 + Math.floor(r() * 2)];
  const g = new THREE.Group(), mat = tarjetaMat(t);
  for (let k = 0; k < 2; k++) {
    const m = tarjeta(new THREE.PlaneGeometry(ancho, alto), mat);
    m.position.y = alto / 2; m.rotation.y = k * Math.PI / 2 + r() * 0.5;
    g.add(m);
  }
  return g;
}

export function montanas(r: () => number, z = -230, color = "#8fa88a", n = 7): THREE.Group {
  const g = new THREE.Group();
  for (let i = 0; i < n; i++) {
    const h = 35 + r() * 35, m = malla(new THREE.ConeGeometry(h * 1.3, h, 4, 1), lam(color, undefined, { fog: false }), false);
    m.receiveShadow = false; m.castShadow = false; m.rotation.y = Math.PI / 4 + (r() - 0.5) * 0.3;
    m.position.set(-300 + (i / (n - 1)) * 600 + (r() - 0.5) * 60, h / 2 - 3, z - r() * 60);
    g.add(m);
  }
  return g;
}

function piso(map: THREE.Texture, tam = 400): THREE.Mesh {
  const m = malla(new THREE.PlaneGeometry(tam, tam), lam("#ffffff", map), false);
  m.rotation.x = -Math.PI / 2;
  return m;
}

/** camino de barro que serpentea por x, con bordes irregulares */
function camino(r: () => number, ancho = 1.8, largo = 70, z0 = 0.6, curva = 1.2): THREE.Mesh {
  const geo = new THREE.PlaneGeometry(largo, ancho, 140, 2), p = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), borde = Math.abs(y) > ancho * 0.45 ? (r() - 0.5) * 0.35 : 0;
    p.setY(i, y + borde + z0 * -1 + Math.sin(x * 0.11) * curva);
  }
  geo.computeVertexNormals();
  const m = malla(geo, lam("#ffffff", P.barro([largo / 4, 1]), { polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 }), false);
  m.rotation.x = -Math.PI / 2; m.position.y = 0.01;
  return m;
}

function cerca(desde: [number, number], hasta: [number, number]): THREE.Group {
  const g = new THREE.Group(), [x0, z0] = desde, [x1, z1] = hasta, L = Math.hypot(x1 - x0, z1 - z0), n = Math.ceil(L / 2.4);
  const madera = lam("#7a5a3a"), alambre = lam("#5a5a5a");
  for (let i = 0; i <= n; i++) {
    const t = i / n, poste = malla(new THREE.CylinderGeometry(0.07, 0.09, 1.4, 6), madera);
    poste.position.set(x0 + (x1 - x0) * t, 0.7, z0 + (z1 - z0) * t); poste.rotation.z = (Math.sin(i * 7.3) * 0.06);
    g.add(poste);
  }
  void alambre;
  for (const y of [0.55, 1.05]) { // cerca de varas de madera
    const a = malla(new THREE.BoxGeometry(0.07, 0.12, L), madera, false);
    a.position.set((x0 + x1) / 2, y, (z0 + z1) / 2); a.rotation.y = Math.PI / 2 - Math.atan2(z1 - z0, x1 - x0);
    g.add(a);
  }
  return g;
}

/** casa campesina de bahareque encalado, zócalo de color, techo de teja a dos aguas y corredor */
function casaTeja(zocalo = "#b5583a", base = "#e8a070"): THREE.Group {
  const g = new THREE.Group(), W = 8, D = 5.5, H = 2.8;
  const paredMat = lam("#ffffff", P.pared([2, 1], zocalo, base));
  const cuerpo = malla(new THREE.BoxGeometry(W, H, D), paredMat);
  cuerpo.position.y = H / 2; g.add(cuerpo);
  const tri = new THREE.Shape([new THREE.Vector2(-D / 2, 0), new THREE.Vector2(D / 2, 0), new THREE.Vector2(0, 1.6)]);
  for (const s of [-1, 1]) {
    const m = malla(new THREE.ShapeGeometry(tri), lam(base));
    m.position.set(s * W / 2, H, 0); m.rotation.y = s * Math.PI / 2; g.add(m);
  }
  const tejaMat = lam("#ffffff", P.teja([3, 2]), { side: THREE.DoubleSide }), largo = Math.hypot(D / 2 + 1.5, 1.6 + 0.45);
  for (const s of [-1, 1]) {
    const t = malla(new THREE.BoxGeometry(W + 1.4, 0.08, largo), tejaMat);
    const ang = Math.atan2(1.6 + 0.45, D / 2 + 1.5);
    t.position.set(0, H + 1.6 / 2 - 0.15, s * (D / 4 + 0.75) * 1.0); t.rotation.x = s * ang;
    g.add(t);
  }
  const madera = lam("#ffffff", P.madera([1, 1], "#6a4428"));
  const puerta = malla(new THREE.BoxGeometry(1.0, 2.0, 0.08), madera);
  puerta.position.set(-1.2, 1.0, D / 2 + 0.03); g.add(puerta);
  for (const x of [1.4, 3.0]) {
    const v = malla(new THREE.BoxGeometry(0.9, 0.9, 0.08), lam("#2a3a44")); v.position.set(x, 1.6, D / 2 + 0.03); g.add(v);
    const marco = malla(new THREE.BoxGeometry(1.1, 0.12, 0.14), madera); marco.position.set(x, 1.1, D / 2 + 0.06); g.add(marco);
  }
  for (const x of [-W / 2 + 0.3, 0, W / 2 - 0.3]) { // horcones del corredor
    const p = malla(new THREE.CylinderGeometry(0.09, 0.11, H, 6), madera); p.position.set(x, H / 2, D / 2 + 1.3); g.add(p);
  }
  return g;
}

const cielo = (g: THREE.Group, r: () => number, nubes = 6) => {
  for (let i = 0; i < nubes; i++) {
    const n = new THREE.Group();
    for (let k = 0; k < 4; k++) { const b = new THREE.Mesh(jitter(new THREE.IcosahedronGeometry(6 + r() * 6, 1), r, 0.2), lam("#ffffff")); b.position.set(k * 7 - 10, r() * 3, 0); b.scale.y = 0.55; n.add(b); }
    n.position.set(-200 + r() * 400, 60 + r() * 40, -260 - r() * 60); n.layers.set(NOINK); n.traverse((o) => o.layers.set(NOINK));
    g.add(n);
  }
};

// ------------------------------------------------------------------------------------------------ los 4 escenarios
export function construir(nombre: NombreEscenario, noche = false): Escena {
  const r = P.rnd(nombre.length * 977 + 13), root = new THREE.Group();
  let animar = (_t: number) => {};
  const vacio: [number, number] = [0, 0];
  if (nombre === "finca") {
    root.add(piso(P.pasto([90, 90], 1)));
    root.add(camino(r, 1.6, 90, 0.2, 0.8));
    const casa = casaTeja(); casa.position.set(-7, 0, -12); casa.rotation.y = 0.35; root.add(casa);
    root.add(cerca([-40, -4], [40, -5.5]));
    root.add(cerca([12, -5.3], [16, -40]));
    for (let i = 0; i < 7; i++) { const a = arbol(r, 6 + r() * 4); a.position.set(-40 + r() * 80, 0, -18 - r() * 40); root.add(a); }
    for (let i = 0; i < 4; i++) { const p = palma(r, 8 + r() * 4); p.position.set(r() < 0.5 ? -18 - r() * 10 : 14 + r() * 14, 0, -8 - r() * 16); root.add(p); }
    for (let i = 0; i < 26; i++) { const m = mata(r, 1.0, 0.7); m.position.set(-25 + r() * 50, 0, 2.2 + r() * 6); root.add(m); }
    for (let i = 0; i < 18; i++) { const m = mata(r, 1.2, 0.9); m.position.set(-30 + r() * 60, 0, -1.4 - r() * 4); root.add(m); }
    root.add(montanas(r, -200, "#7f9a62")); root.add(montanas(r, -320, "#a8a0c0", 6));
    cielo(root, r);
    return { root, animar, actor: vacio, animal: [2.2, 0.4], cam: { pos: [0.5, 1.55, 7.2], look: [0.3, 1.0, 0], fov: 38 }, interior: false };
  }
  if (nombre === "selva") {
    root.add(piso(P.pasto([90, 90])));
    root.add(camino(r, 1.3, 90, 0.2, 0.6));
    // dosel: copas altas que tapan casi todo el cielo
    for (let i = 0; i < 110; i++) {
      const d = malla(jitter(new THREE.IcosahedronGeometry(5 + r() * 4, 3), r, 0.08), lam(["#2f6a22", "#3a7a2a", "#285c1f"][Math.floor(r() * 3)]), true);
      d.receiveShadow = false; d.scale.y = 0.6; d.position.set(-45 + r() * 90, 8 + r() * 6, -4 - r() * 36); root.add(d);
    }
    for (let i = 0; i < 70; i++) {
      const z = -2.5 - r() * 32, x = -40 + r() * 80;
      const a = r() < 0.35 ? palma(r, 9 + r() * 5) : arbol(r, 9 + r() * 8, ["#2f6a22", "#3a7a2a", "#285c1f", "#468a2c"]);
      a.position.set(x, 0, z); a.scale.set(1.8, 1, 1.8); root.add(a);
    }
    for (let i = 0; i < 70; i++) { const m = mata(r, 1.6 + r(), 1.4 + r(), "helecho"); m.position.set(-30 + r() * 60, 0, -1.2 - r() * 10); root.add(m); }
    for (let i = 0; i < 30; i++) { const m = mata(r, 1.4, 1.0, r() < 0.5 ? "helecho" : "pasto"); m.position.set(-25 + r() * 50, 0, 2 + r() * 6); root.add(m); }
    // segundo piso del monte: copas medianas y matas altas que cierran el hueco entre troncos
    for (let i = 0; i < 70; i++) {
      const d = malla(jitter(new THREE.IcosahedronGeometry(1.6 + r() * 1.6, 3), r, 0.08), lam(["#3a7a2a", "#2f6a22", "#468a2c"][Math.floor(r() * 3)]));
      d.receiveShadow = false; d.position.set(-40 + r() * 80, 3 + r() * 4, -3 - r() * 22); root.add(d);
    }
    for (let i = 0; i < 40; i++) { const m = mata(r, 3 + r() * 2, 2.5 + r() * 1.5, "helecho"); m.position.set(-30 + r() * 60, 0, -2.5 - r() * 12); root.add(m); }
    // bejucos que cuelgan
    for (let i = 0; i < 14; i++) {
      const x = -15 + r() * 30, z = -2 - r() * 8, c = new THREE.CatmullRomCurve3([new THREE.Vector3(x, 12, z), new THREE.Vector3(x + 0.5, 7, z + 0.3), new THREE.Vector3(x + 0.2, 3 + r() * 3, z)]);
      root.add(malla(new THREE.TubeGeometry(c, 12, 0.04, 5), lam("#4a5a2a"), false));
    }
    // hojas grandes de primer plano
    const hojas: THREE.Mesh[] = [];
    for (let i = 0; i < 6; i++) {
      const h = tarjeta(new THREE.PlaneGeometry(1.1, 2.2), tarjetaMat(P.tarjetaHoja(40 + i)));
      h.position.set(i % 2 ? 3.5 + r() * 2 : -3.5 - r() * 2, 0.9, 3.4 + r()); h.rotation.set(-0.2, (r() - 0.5), (i % 2 ? -0.5 : 0.5));
      root.add(h); hojas.push(h);
    }
    animar = (t) => hojas.forEach((h, i) => { h.rotation.z = (i % 2 ? -0.5 : 0.5) + 0.04 * Math.sin(t * 1.3 + i); });
    return { root, animar, actor: vacio, animal: [2.0, 0.3], cam: { pos: [0.4, 1.45, 6.4], look: [0.3, 1.0, 0], fov: 40 }, interior: false, niebla: { color: "#2f5a2a", cerca: 20, lejos: 140 } };
  }
  if (nombre === "rio") {
    root.add(piso(P.pasto([90, 90])));
    const orilla = malla(new THREE.PlaneGeometry(200, 4.5), lam("#ffffff", P.barro([40, 1])), false);
    orilla.rotation.x = -Math.PI / 2; orilla.position.set(0, 0.012, -0.6); root.add(orilla);
    const aguaT = P.agua([30, 4], noche);
    const agua = malla(new THREE.PlaneGeometry(200, 22), lam("#ffffff", aguaT), false);
    agua.rotation.x = -Math.PI / 2; agua.position.set(0, -0.06, -13.6); root.add(agua);
    const bajo = malla(new THREE.PlaneGeometry(200, 22), lam("#2f4a4a"), false); bajo.rotation.x = -Math.PI / 2; bajo.position.set(0, -0.6, -14.5); root.add(bajo);
    // el piso no tapa el agua: lo recortamos dejando la franja del río
    (root.children[0] as THREE.Mesh).geometry = new THREE.PlaneGeometry(200, 60); root.children[0].position.z = 27.2;
    const lejos = piso(P.pasto([60, 30])); lejos.geometry = new THREE.PlaneGeometry(200, 100); lejos.position.z = -75.5; root.add(lejos);
    for (let i = 0; i < 10; i++) { const ro = roca(r, 0.3 + r() * 0.5); ro.position.x = -14 + r() * 28; ro.position.z = -2.6 - r() * 0.4; root.add(ro); }
    for (let i = 0; i < 10; i++) { const m = mata(r, 1.0, 1.0); m.position.set(-20 + r() * 40, 0, -2.5 - r() * 0.3); root.add(m); }
    for (let i = 0; i < 26; i++) { const a = arbol(r, 7 + r() * 6); a.position.set(-60 + r() * 120, 0, -27 - r() * 14); root.add(a); }
    const banda = piso(P.pasto([30, 3])); banda.geometry = new THREE.PlaneGeometry(200, 8); banda.position.set(0, 0.01, -28); (banda.material as THREE.MeshLambertMaterial).color.set("#b8c8a8"); root.add(banda);
    for (let i = 0; i < 16; i++) { const m = mata(r, 1.1, 0.8); m.position.set(-20 + r() * 40, 0, 2 + r() * 5); root.add(m); }
    root.add(montanas(r, -190, "#7f9a62")); root.add(montanas(r, -300, "#a8a0c0", 6));
    cielo(root, r);
    animar = (t) => { aguaT.offset.x = t * 0.035; };
    return { root, animar, actor: vacio, animal: [2.0, -0.8], cam: { pos: [0.3, 2.0, 6.6], look: [0.3, 0.8, -1], fov: 40 }, interior: false };
  }
  // casa por dentro: cuarto abierto hacia la cámara
  const W = 7, D = 6, H = 3;
  const suelo = malla(new THREE.PlaneGeometry(W, D + 4), lam("#ffffff", P.baldosa([3.5, 5])), false);
  suelo.rotation.x = -Math.PI / 2; suelo.position.z = -D / 2 + 2; root.add(suelo);
  const paredMat = lam("#ffffff", P.pared([2, 1], "#3a6fa0"));
  const fondo = malla(new THREE.PlaneGeometry(W, H), paredMat, false); fondo.position.set(0, H / 2, -D + 1); root.add(fondo);
  for (const s of [-1, 1]) {
    const lado = malla(new THREE.PlaneGeometry(D + 3, H), paredMat, false);
    lado.position.set(s * W / 2, H / 2, -D / 2 + 1.5); lado.rotation.y = -s * Math.PI / 2; root.add(lado);
  }
  const madera = lam("#ffffff", P.madera([1, 1], "#6a4428"));
  for (let i = 0; i < 5; i++) { const v = malla(new THREE.BoxGeometry(W, 0.16, 0.2), madera, false); v.position.set(0, H - 0.2, -D + 1.6 + i * 1.6); root.add(v); }
  const techo = malla(new THREE.PlaneGeometry(W, D + 4), lam("#ffffff", P.madera([6, 2], "#5a3a22")), false);
  techo.rotation.x = Math.PI / 2; techo.position.set(0, H, -D / 2 + 2); root.add(techo);
  const puerta = malla(new THREE.BoxGeometry(1.0, 2.1, 0.08), madera); puerta.position.set(-2.2, 1.05, -D + 1.05); root.add(puerta);
  // ventana con la luz de afuera (brilla: bloom)
  const vent = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.1), new THREE.MeshBasicMaterial({ color: noche ? "#3a4f8a" : new THREE.Color(1.6, 1.5, 1.2), toneMapped: true }));
  vent.position.set(1.6, 1.7, -D + 1.02); root.add(vent);
  for (const [x, y, w, h] of [[1.6, 2.28, 1.6, 0.1], [1.6, 1.12, 1.6, 0.1], [0.85, 1.7, 0.1, 1.2], [2.35, 1.7, 0.1, 1.2], [1.6, 1.7, 0.06, 1.1]] as const) {
    const m = malla(new THREE.BoxGeometry(w, h, 0.1), madera, false); m.position.set(x, y, -D + 1.06); root.add(m);
  }
  const mesa = new THREE.Group();
  const tabla = malla(new THREE.BoxGeometry(1.6, 0.08, 0.9), madera); tabla.position.y = 0.78; mesa.add(tabla);
  for (const [x, z] of [[-0.7, -0.35], [0.7, -0.35], [-0.7, 0.35], [0.7, 0.35]]) { const p = malla(new THREE.BoxGeometry(0.08, 0.78, 0.08), madera); p.position.set(x, 0.39, z); mesa.add(p); }
  mesa.position.set(-1.6, 0, -2.6); root.add(mesa);
  for (const x of [-2.4, -0.8]) { const s = malla(new THREE.BoxGeometry(0.45, 0.06, 0.45), madera); s.position.set(x, 0.46, -2.0); root.add(s); const e = malla(new THREE.BoxGeometry(0.45, 0.6, 0.06), madera); e.position.set(x, 0.76, -1.8); root.add(e); }
  const matera = malla(new THREE.CylinderGeometry(0.28, 0.2, 0.5, 10), lam("#b5583a")); matera.position.set(2.8, 0.25, -3.8); root.add(matera);
  const planta = arbusto(r, 0.7); planta.position.set(2.8, 0.45, -3.8); root.add(planta);
  const cuadro = malla(new THREE.BoxGeometry(0.7, 0.5, 0.04), lam("#d9a441")); cuadro.position.set(-0.3, 1.9, -D + 1.03); root.add(cuadro);
  const olla = malla(new THREE.CylinderGeometry(0.18, 0.15, 0.2, 10), lam("#3a3a3a")); olla.position.set(-1.9, 0.92, -2.6); root.add(olla);
  // en la casa las paredes no tapan el sol (luz de estudio, estilizada)
  root.traverse((o) => { if ((o as THREE.Mesh).isMesh && o !== suelo) (o as THREE.Mesh).castShadow = o.parent === mesa || o === matera; });
  return { root, animar, actor: vacio, animal: [1.6, -0.6], cam: { pos: [0.2, 1.5, 5.2], look: [0.2, 1.05, -1], fov: 42 }, interior: true };
}
