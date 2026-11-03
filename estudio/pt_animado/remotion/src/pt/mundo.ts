// El mundo de una toma: escenario + cielo + sol + niebla + explorador (tarjeta dibujada con toon.ts e iluminada con
// cardshade.ts) + animal (tarjeta 2D con contorno de tinta, iluminada por la escena, con sombra de contacto).
// Todo es función pura del estado de cada cuadro (Estado): mismo cuadro → misma imagen.
import * as THREE from "three";
import { getInputProps } from "remotion";
import { TONE, CHAR, untone } from "./shade";
import { cardShade, blobMaterial, CARD_K } from "./cardshade";
import { NOINK } from "./ink";
import { Pen, bodyFront, bodySide, EXPLORADOR, Expr } from "./toon";
import { luz, NombreLuz } from "./luces";
import { construir, NombreEscenario, Escena } from "./escenarios";
import { manchaSombra } from "./pintura";

export type Vec3 = [number, number, number];
export type EstadoActor = {
  x: number; z: number; vista: "frente" | "lado"; expr: Expr; fase: number; modo: "march" | "stand"; parpadeo: number;
  mira?: number; salto?: number; escala?: number; inclinar?: number; visible?: boolean;
};
export type EstadoAnimal = { x: number; z: number; alto: number; visible: number; bote?: number };
export type Estado = {
  cam: { pos: Vec3; look: Vec3; fov: number; roll?: number };
  actor: EstadoActor; animal?: EstadoAnimal; frio: number; t: number;
};

const VISTA_SOMBRA = (getInputProps() as { vista?: boolean }).vista ? 1024 : 2048;
const ALTO_TARJETA = 2.3; // m: alto de la tarjeta de 600x1000 (el explorador mide ~1,75 m con sombrero)
const K = 1.6;            // resolución del dibujo (960x1600)

/** cielo: degradado por elevación (colores en pantalla, ya invertidos para el tone map) */
function cieloMat() {
  return new THREE.ShaderMaterial({
    uniforms: { top: { value: new THREE.Color() }, hor: { value: new THREE.Color() } },
    vertexShader: "varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: "uniform vec3 top; uniform vec3 hor; varying vec3 vP; void main(){ float e = clamp(vP.y, 0.0, 1.0); gl_FragColor = vec4(mix(hor, top, pow(smoothstep(0.0, 0.55, e), 0.8)), 1.0); }",
    side: THREE.BackSide, depthWrite: false, fog: false,
  });
}

/** recorta los bordes transparentes de la imagen del animal */
function recortar(img: HTMLImageElement | HTMLCanvasElement): HTMLCanvasElement {
  const w = img.width, h = img.height, c = document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d")!; g.drawImage(img, 0, 0);
  const d = g.getImageData(0, 0, w, h).data;
  let x0 = w, y0 = h, x1 = 0, y1 = 0;
  for (let y = 0; y < h; y += 2) for (let x = 0; x < w; x += 2) if (d[(y * w + x) * 4 + 3] > 40) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
  if (x1 <= x0 || y1 <= y0) return c;
  const m = 6, o = document.createElement("canvas"); o.width = x1 - x0 + 2 * m; o.height = y1 - y0 + m;
  o.getContext("2d")!.drawImage(c, x0 - m, y0 - m, o.width, o.height, 0, 0, o.width, o.height);
  return o;
}

export class Mundo {
  root = new THREE.Group();
  esc: Escena;
  sol = new THREE.DirectionalLight("#ffffff", 2.5);
  hemi = new THREE.HemisphereLight("#ffffff", "#888888", 0.5);
  cielo: THREE.Mesh;
  fog = new THREE.Fog("#ffffff", 30, 300);
  actor: THREE.Mesh; actorG: CanvasRenderingContext2D; actorTex: THREE.CanvasTexture; actorBlob: THREE.Mesh;
  animal: THREE.Mesh | null = null; animalBlob: THREE.Mesh | null = null;
  private ultimoDibujo = "";
  luzNombre: NombreLuz;

  constructor(escenario: NombreEscenario, luzNombre: NombreLuz, animalImg?: HTMLImageElement | HTMLCanvasElement | null) {
    this.luzNombre = luzNombre;
    if ((getInputProps() as { medir?: boolean }).medir) console.log("[pt] Mundo nuevo", performance.now().toFixed(0));
    this.esc = construir(escenario, luzNombre === "noche");
    this.root.add(this.esc.root);
    this.cielo = new THREE.Mesh(new THREE.SphereGeometry(900, 32, 16), cieloMat());
    this.cielo.layers.set(NOINK); this.cielo.renderOrder = -1;
    this.root.add(this.cielo, this.hemi, this.sol, this.sol.target);
    this.sol.castShadow = true;
    this.sol.shadow.mapSize.set(VISTA_SOMBRA, VISTA_SOMBRA);
    const sc = this.sol.shadow.camera; sc.left = -16; sc.right = 16; sc.top = 16; sc.bottom = -16; sc.near = 1; sc.far = 120;
    // explorador
    const c = document.createElement("canvas"); c.width = 600 * K; c.height = 1000 * K;
    this.actorG = c.getContext("2d")!;
    this.actorTex = new THREE.CanvasTexture(c); this.actorTex.colorSpace = THREE.SRGBColorSpace;
    const mat = cardShade(new THREE.MeshLambertMaterial({ map: this.actorTex, alphaTest: 0.5, side: THREE.DoubleSide }));
    this.actor = new THREE.Mesh(new THREE.PlaneGeometry(ALTO_TARJETA * 0.6, ALTO_TARJETA), mat);
    this.actor.geometry.translate(0, ALTO_TARJETA * (0.5 - 0.025), 0); // suelas (y = 975 de 1000) en el piso
    this.actor.castShadow = true;
    this.actor.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: this.actorTex, alphaTest: 0.5 });
    this.actor.layers.set(NOINK);
    this.actorBlob = this.blob(0.9, 0.4);
    this.root.add(this.actor);
    if (animalImg) this.ponerAnimal(animalImg);
  }

  private blob(w: number, d: number) {
    const b = new THREE.Mesh(new THREE.PlaneGeometry(w, d), blobMaterial(manchaSombra()));
    b.rotation.x = -Math.PI / 2; b.position.y = 0.02; b.layers.set(NOINK); b.renderOrder = 1;
    this.root.add(b);
    return b;
  }

  ponerAnimal(img0: HTMLImageElement | HTMLCanvasElement) {
    const img = recortar(img0); // sin márgenes transparentes: la base del animal toca el piso
    const t = new THREE.Texture(img); t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true; t.anisotropy = (getInputProps() as { vista?: boolean }).vista ? 1 : 8;
    const asp = img.width / img.height;
    const mat = cardShade(new THREE.MeshLambertMaterial({ map: t, alphaTest: 0.4, side: THREE.DoubleSide, transparent: false }));
    const geo = new THREE.PlaneGeometry(asp, 1); geo.translate(0, 0.5, 0);
    this.animal = new THREE.Mesh(geo, mat);
    this.animal.castShadow = true;
    this.animal.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: t, alphaTest: 0.4 });
    this.animal.layers.set(NOINK);
    this.root.add(this.animal);
    this.animalBlob = this.blob(asp * 0.95, 0.45);
  }

  /** dibuja el explorador en su tarjeta solo si cambió algo */
  private dibujarActor(a: EstadoActor, luzAng: number) {
    const clave = `${a.vista}|${a.expr}|${a.fase.toFixed(3)}|${a.modo}|${a.parpadeo.toFixed(2)}|${(a.mira ?? 0).toFixed(2)}|${(a.inclinar ?? 0).toFixed(1)}|${luzAng.toFixed(2)}`;
    if (clave === this.ultimoDibujo) return;
    this.ultimoDibujo = clave;
    const g = this.actorG;
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, 600 * K, 1000 * K); g.setTransform(K, 0, 0, K, 0, 0);
    const p = new Pen(g);
    if (a.vista === "lado") bodySide(p, EXPLORADOR, { phase: a.fase, mode: a.modo, expr: a.expr, blink: a.parpadeo, stride: 0.75, stomp: 0.8, light: luzAng, seed: 3 });
    else bodyFront(p, EXPLORADOR, { mode: a.modo === "march" ? "stroll" : "stand", phase: a.fase, expr: a.expr, blink: a.parpadeo, look: a.mira ?? 0, tilt: a.inclinar ?? 0, light: luzAng, seed: 3 });
    this.actorTex.needsUpdate = true;
  }

  /** pone todo en su sitio para este cuadro; devuelve el punto al que mira la cámara */
  update(s: Estado, cam: THREE.PerspectiveCamera, scene: THREE.Scene, alto: number) {
    const L = luz(this.luzNombre, s.frio);
    // cámara
    cam.position.set(...s.cam.pos); cam.fov = s.cam.fov; cam.up.set(0, 1, 0);
    const look = new THREE.Vector3(...s.cam.look);
    cam.lookAt(look);
    if (s.cam.roll) cam.rotateZ((s.cam.roll * Math.PI) / 180);
    cam.updateProjectionMatrix(); cam.updateMatrixWorld();
    // cielo, niebla y luces
    const m = this.cielo.material as THREE.ShaderMaterial;
    untone(L.top, m.uniforms.top.value); untone(L.hor, m.uniforms.hor.value);
    this.cielo.position.copy(cam.position);
    this.fog.color.copy(untone(L.fog)); this.fog.near = L.fogNear; this.fog.far = L.fogFar;
    const nb = this.esc.niebla;
    if (nb) { // la selva: niebla verde y cerrada, oscurecida con la luz
      const k = this.luzNombre === "noche" ? 0.35 : this.luzNombre === "amanecer" ? 0.8 : 1;
      this.fog.color.lerp(untone(nb.color), 0.7 * k); this.fog.near = Math.min(L.fogNear, nb.cerca); this.fog.far = Math.min(L.fogFar, nb.lejos);
    }
    scene.fog = this.fog; scene.background = null;
    TONE.uLitCol.value.set(...L.lit); TONE.uShadeCol.value.set(...L.shade); TONE.uShadeLift.value.set(...L.lift);
    TONE.uLambert.value = L.lambert; TONE.uSideK.value = L.sideK; TONE.uTerm.value = L.term; TONE.uSat.value = this.luzNombre === "noche" ? 0.55 : 1.08;
    if (this.esc.interior && this.luzNombre === "noche") { TONE.uLitCol.value.set(0.5, 0.4, 0.3); TONE.uShadeCol.value.set(0.16, 0.13, 0.13); } // bombillo cálido adentro
    CHAR.uCharTint.value.set(...L.charTint); CHAR.uCharShade.value = L.charShade; CHAR.uGrad.value = L.charGrad; CHAR.uBodyGrad.value = L.bodyGrad; CHAR.uSideTint.value.set(...L.sideTint);
    CARD_K.uPx.value = alto / 1080;
    // el explorador y el animal se oscurecen con la luz de la escena (la tarjeta normaliza el tinte: sin esto de noche brillan)
    CARD_K.uNorm.value = this.luzNombre === "dia" ? 0.7 : 0.15; // de noche/amanecer el color de la luz sí tiñe al explorador
    CARD_K.uGain.value = (this.luzNombre === "noche" ? 0.2 : this.luzNombre === "amanecer" ? 0.75 : 1.03) * (1 - 0.55 * Math.min(1, s.frio));
    this.hemi.color.set(L.sky); this.hemi.groundColor.set(L.ground); this.hemi.intensity = L.hemiI;
    // sol relativo a la cámara (az desde el eje de la cámara), congelado por toma
    const fwd = new THREE.Vector3(); cam.getWorldDirection(fwd); fwd.y = 0; fwd.normalize();
    const az = ((this.esc.interior ? 150 : L.az) * Math.PI) / 180, el = ((this.esc.interior ? Math.max(L.el, 35) : L.el) * Math.PI) / 180; // adentro: luz desde la cámara
    const right = new THREE.Vector3().crossVectors(fwd, new THREE.Vector3(0, 1, 0));
    const dir = fwd.clone().multiplyScalar(Math.cos(az)).add(right.multiplyScalar(Math.sin(az))).multiplyScalar(Math.cos(el)).setY(Math.sin(el)).normalize();
    const centro = new THREE.Vector3(s.actor.x, 0, s.actor.z);
    this.sol.position.copy(centro).addScaledVector(dir, 60); this.sol.target.position.copy(centro);
    this.sol.color.set(L.sunCol); this.sol.intensity = L.sunI;
    this.sol.shadow.bias = L.bias; this.sol.shadow.normalBias = L.normalBias;
    // ángulo de la luz en el dibujo: de qué lado (en pantalla) viene el sol
    const solPantalla = dir.clone().transformDirection(cam.matrixWorldInverse);
    const luzAng = Math.atan2(-Math.max(0.35, solPantalla.y), solPantalla.x || 0.01); // ángulo en el lienzo (y hacia abajo)
    // explorador (tarjeta que mira a la cámara solo en y)
    const a = s.actor;
    this.actor.visible = a.visible !== false; this.actorBlob.visible = this.actor.visible;
    this.dibujarActor(a, luzAng);
    const esc = a.escala ?? 1;
    this.actor.position.set(a.x, a.salto ?? 0, a.z); this.actor.scale.setScalar(esc);
    this.actor.rotation.set(0, Math.atan2(cam.position.x - a.x, cam.position.z - a.z), 0);
    this.actorBlob.position.set(a.x, 0.02, a.z); this.actorBlob.scale.setScalar(esc * (1 - Math.min(0.5, (a.salto ?? 0) * 0.6)));
    // animal
    if (this.animal && this.animalBlob) {
      const an = s.animal;
      const vis = !!an && an.visible > 0.001;
      this.animal.visible = vis; this.animalBlob.visible = vis;
      if (an && vis) {
        const k = an.alto * Math.min(1, an.visible);
        this.animal.scale.set(k, k * (1 + 0.04 * (an.bote ?? 0)), k);
        this.animal.position.set(an.x, 0, an.z);
        this.animal.rotation.set(0, Math.atan2(cam.position.x - an.x, cam.position.z - an.z), 0);
        this.animalBlob.position.set(an.x, 0.021, an.z); this.animalBlob.scale.setScalar(k);
      }
    }
    this.esc.animar(s.t);
    return look;
  }
}
