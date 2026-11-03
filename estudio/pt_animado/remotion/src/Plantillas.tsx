// Fase 3: las 4 plantillas de Peligro Tropical (INTRO, ENCUENTRO, TRANSICIÓN, CIERRE). Solo reciben: escenario, luz,
// imagen del animal, tiempos (s) de las palabras clave de Whisper, expresión del explorador y formato.
// Toda reacción visual cae 0-3 cuadros ANTES de su palabra (camara.antes). Ninguna toma queda quieta.
import React from "react";
import { AbsoluteFill, CalculateMetadataFunction, interpolate, useCurrentFrame } from "remotion";
import { Toma, Plan } from "./pt/Toma";
import { NombreEscenario } from "./pt/escenarios";
import { NombreLuz } from "./pt/luces";
import { Expr } from "./pt/toon";
import { Vec3, EstadoActor } from "./pt/mundo";
import { FPS, Formato, Clave, camaraEn, golpe, antes, suave } from "./pt/camara";

export type Tipo = "intro" | "encuentro" | "transicion" | "cierre";
export type PropsPlantilla = {
  escenario: NombreEscenario; luz: NombreLuz; animal?: string | null; formato: Formato;
  /** segundos (dentro del clip) de las palabras clave; `fin` = largo del clip */
  claves: Record<string, number>; expresion?: Expr;
  /** solo TRANSICIÓN: nivel de peligro 0-10 al que sube el medidor */
  nivel?: number;
};

const LARGO: Record<Tipo, number> = { intro: 10, encuentro: 8, transicion: 4, cierre: 12 };
export const metadatos = (tipo: Tipo): CalculateMetadataFunction<PropsPlantilla> => ({ props }) => ({
  durationInFrames: Math.round((props.claves.fin ?? LARGO[tipo]) * FPS),
  width: props.formato === "9:16" ? 1080 : 1920, height: props.formato === "9:16" ? 1920 : 1080,
});

const VEL = 1.25;               // m/s del caminado
const CICLO = 1.28;             // m por ciclo de pasos (dos pisadas)
const parpadeo = (f: number) => { const k = f % 61; return k < 4 ? [1, 1, 0.5, 0][k] : 0; }; // cada ~2 s, 4 cuadros
const sumar = (a: Vec3, b: Vec3): Vec3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const flashEn = (f: number, en: number) => (f >= en && f < en + 4 ? [1, 0.75, 0.45, 0.2][f - en] : 0);

/** pasos del explorador: camina de x0 a la velocidad VEL desde el cuadro a, frena en b */
const caminar = (f: number, a: number, b: number, x0: number) => {
  const t = (Math.min(f, b) - a) / FPS, frena = f > b ? suave((f - b) / 10) : 0;
  const x = x0 + Math.max(0, t) * VEL + (f > b ? (1 - frena) * 0.15 : 0);
  return { x, fase: ((x - x0) / CICLO) % 1, andando: f >= a && f < b };
};

// --------------------------------------------------------------------------------------------- INTRO
function planIntro(p: PropsPlantilla): { plan: Plan; flash: number } {
  const c = p.claves, F = Math.round((c.fin ?? 10) * FPS);
  const flash = antes(c.gancho_fin ?? 2.0), botas = antes(c.botas ?? 4.6), revela = antes(c.revela ?? 6.4), susto = antes(c.susto ?? 7.8);
  const ax: [number, number] = [2.6, -0.4];      // dónde está el animal
  const plan: Plan = (f) => {
    const w = caminar(f, flash, revela, -6);
    const actor: EstadoActor = { x: w.x, z: 0, vista: "lado", expr: "neutral", fase: w.fase, modo: w.andando ? "march" : "stand", parpadeo: parpadeo(f) };
    let claves: Clave[], dof = { cInf: 0, foco: undefined as Vec3 | undefined }, frio = 0;
    if (f < flash) { // descenso aéreo hasta el camino
      claves = [{ f: 0, pos: [-10, 38, 34], look: [-4, 0, -4], fov: 46 }, { f: flash, pos: [-7.5, 3.2, 9], look: [-5, 1, 0], fov: 40, desliza: Math.max(18, flash) }];
    } else if (f < botas) { // el explorador camina; la cámara lo acompaña
      claves = [{ f: flash, pos: [w.x + 0.8, 1.35, 5.6], look: [w.x + 0.4, 1.0, 0], fov: 38 }];
      dof = { cInf: 5, foco: [w.x, 1, 0] };
    } else if (f < revela) { // primer plano de las botas en el barro
      claves = [{ f: botas, pos: [w.x + 0.9, 0.32, 1.7], look: [w.x + 0.1, 0.28, 0], fov: 34, corte: true, empuje: 0.003 }];
      dof = { cInf: 14, foco: [w.x, 0.25, 0] };
    } else if (f < susto) { // aparece el animal: el foco pasa del explorador al animal
      claves = [{ f: revela, pos: [w.x + 1.3, 1.1, 4.6], look: [w.x + 1.6, 0.6, -0.2], fov: 36, corte: true, empuje: 0.0035 }];
      const k = suave((f - revela) / 12);
      dof = { cInf: 12, foco: [w.x + (ax[0] - w.x) * k, 0.6, ax[1] * k] };
    } else { // susto: golpe de cámara, cara de miedo de frente y luz más fría
      claves = [{ f: susto, pos: [w.x + 0.15, 1.62, 2.2], look: [w.x, 1.55, 0], fov: 32, corte: true, empuje: 0.004 }];
      actor.vista = "frente"; actor.modo = "stand"; actor.expr = p.expresion ?? "shock"; actor.inclinar = -3;
      frio = suave((f - susto) / 10);
      dof = { cInf: 13, foco: [w.x, 1.55, 0] };
    }
    const cam = camaraEn(claves, f, p.formato);
    cam.pos = sumar(cam.pos, golpe(f, [susto], 0.07));
    const vis = f < revela ? 0 : Math.min(1, (f - revela) / 6);
    return { cam, actor, animal: { x: ax[0], z: ax[1], alto: 0.9, visible: vis, bote: Math.sin((f - revela) * 0.6) * Math.max(0, 1 - (f - revela) / 15) }, frio, t: f / FPS, dof };
  };
  void F;
  return { plan, flash };
}

// --------------------------------------------------------------------------------------------- ENCUENTRO
function planEncuentro(p: PropsPlantilla): Plan {
  const c = p.claves, aparece = antes(c.aparece ?? 2.2), reaccion = antes(c.reaccion ?? 3.6), muerde = antes(c.muerde ?? 5.4);
  const ax: [number, number] = [1.6, -0.3];
  return (f) => {
    const w = caminar(f, 0, aparece, -2.4);
    const actor: EstadoActor = { x: w.x, z: 0, vista: f < aparece + 4 ? "lado" : "frente", expr: "neutral", fase: w.fase, modo: w.andando ? "march" : "stand", parpadeo: parpadeo(f) };
    let claves: Clave[], dof = { cInf: 4, foco: undefined as Vec3 | undefined }, frio = 0;
    if (f < reaccion) {
      claves = [{ f: 0, pos: [-0.8, 1.4, 5.8], look: [-0.4, 1.0, 0], fov: 38 }, { f: aparece + 14, pos: [0.4, 1.3, 5.2], look: [0.5, 0.8, -0.2], fov: 38, desliza: 18 }];
      if (f >= aparece) actor.expr = "nervous";
    } else {
      claves = [{ f: reaccion, pos: [w.x + 0.4, 1.5, 2.8], look: [w.x + 0.5, 1.2, 0], fov: 34, corte: true, empuje: 0.003 }];
      actor.expr = p.expresion ?? "shock"; frio = 0.6 * suave((f - reaccion) / 10);
      dof = { cInf: 10, foco: [w.x, 1.4, 0] };
      if (f >= muerde) { actor.expr = "pained"; frio = 0.8; }
    }
    const cam = camaraEn(claves, f, p.formato);
    cam.pos = sumar(cam.pos, golpe(f, [muerde], 0.08));
    const t = (f - aparece) / 8, pop = f < aparece ? 0 : t < 1 ? suave(t) * 1.12 : 1 + 0.12 * Math.exp(-(f - aparece - 8) / 4) * Math.cos((f - aparece - 8) * 0.7);
    return { cam, actor, animal: { x: ax[0], z: ax[1], alto: 0.85, visible: pop }, frio, t: f / FPS, dof };
  };
}

// --------------------------------------------------------------------------------------------- TRANSICIÓN
function planTransicion(p: PropsPlantilla): Plan {
  return (f) => {
    const w = caminar(f, 0, 9999, -3);
    const actor: EstadoActor = { x: w.x, z: 0, vista: "lado", expr: "neutral", fase: w.fase, modo: "march", parpadeo: parpadeo(f) };
    const cam = camaraEn([{ f: 0, pos: [w.x + 1.2, 1.25, 5.0], look: [w.x + 0.6, 1.0, 0], fov: 38, empuje: 0.0025 }], f, p.formato);
    return { cam, actor, frio: 0, t: f / FPS, dof: { cInf: 6, foco: [w.x, 1, 0] } };
  };
}

// --------------------------------------------------------------------------------------------- CIERRE
function planCierre(p: PropsPlantilla): Plan {
  const c = p.claves, remate = antes(c.remate ?? 2.0), comenta = antes(c.comenta ?? 6.0);
  return (f) => {
    const actor: EstadoActor = { x: 0, z: 0, vista: "frente", expr: f < remate ? "neutral" : f < comenta ? (p.expresion ?? "relief_open") : "smile", fase: 0, modo: "stand", parpadeo: parpadeo(f), mira: f < comenta ? 0.6 : 0 };
    const claves: Clave[] = [
      { f: 0, pos: [1.4, 1.4, 5.2], look: [0.2, 1.1, 0], fov: 38 },
      { f: remate, pos: [0.6, 1.5, 3.8], look: [0.05, 1.3, 0], fov: 36, desliza: 24 },
      { f: comenta, pos: [0.0, 1.58, 2.5], look: [0.0, 1.5, 0], fov: 33, desliza: 20, empuje: 0.0025 },
    ];
    const cam = camaraEn(claves, f, p.formato);
    return { cam, actor, frio: 0, t: f / FPS, dof: { cInf: f >= comenta ? 11 : 6, foco: [0, 1.4, 0] } };
  };
}

// --------------------------------------------------------------------------------------------- capas 2D
/** medidor de peligro que sube (TRANSICIÓN) */
const Medidor: React.FC<{ nivel: number; vertical: boolean }> = ({ nivel, vertical }) => {
  const f = useCurrentFrame();
  const v = interpolate(f, [8, 8 + 50], [0, nivel], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (x) => suave(x) });
  const W = vertical ? 760 : 620, H = 64, col = v < 4 ? "#f2c94c" : v < 7 ? "#f2994a" : "#e0453a";
  const latido = 1 + (v >= 7 ? 0.04 * Math.max(0, Math.sin(f * 0.5)) : 0);
  return (
    <div style={{ position: "absolute", left: vertical ? (1080 - W) / 2 : 70, top: vertical ? 230 : 60, width: W, transform: `scale(${latido})`, transformOrigin: "left center", fontFamily: "Bricolage Grotesque, DejaVu Sans, sans-serif" }}>
      <div style={{ fontSize: 46, fontWeight: 900, color: "#fff", WebkitTextStroke: "3px #241726", letterSpacing: 2, marginBottom: 10 }}>PELIGRO {Math.round(v)}/10</div>
      <div style={{ height: H, borderRadius: H / 2, background: "#241726", padding: 7, boxSizing: "border-box" }}>
        <div style={{ height: "100%", width: `${(v / 10) * 100}%`, borderRadius: H / 2, background: `linear-gradient(90deg, #f2c94c, ${col})` }} />
      </div>
    </div>
  );
};

/** globo de comentario (CIERRE): aparece cuando el explorador mira a cámara */
const Globo: React.FC<{ desde: number; vertical: boolean }> = ({ desde, vertical }) => {
  const f = useCurrentFrame();
  if (f < desde) return null;
  const k = Math.min(1, (f - desde) / 8), s = k < 1 ? suave(k) * 1.1 : 1 + 0.06 * Math.exp(-(f - desde - 8) / 5);
  const puntos = [0, 1, 2].map((i) => 0.5 + 0.5 * Math.sin((f - desde) * 0.35 - i * 0.9));
  return (
    <div style={{ position: "absolute", right: vertical ? 120 : 260, top: vertical ? 520 : 170, transform: `scale(${s})`, transformOrigin: "left bottom" }}>
      <svg width="260" height="190" viewBox="0 0 260 190">
        <path d="M30 20 h200 a22 22 0 0 1 22 22 v80 a22 22 0 0 1 -22 22 h-130 l-48 36 l10 -36 h-32 a22 22 0 0 1 -22 -22 v-80 a22 22 0 0 1 22 -22 z" fill="#fff" stroke="#241726" strokeWidth="9" strokeLinejoin="round" />
        {puntos.map((a, i) => <circle key={i} cx={82 + i * 48} cy={84} r={14} fill="#241726" opacity={0.35 + 0.65 * a} />)}
      </svg>
    </div>
  );
};

const Blanco: React.FC<{ en: number }> = ({ en }) => {
  const a = flashEn(useCurrentFrame(), en);
  return a > 0 ? <AbsoluteFill style={{ background: "#fff", opacity: a }} /> : null;
};

// --------------------------------------------------------------------------------------------- composiciones
export const Intro: React.FC<PropsPlantilla> = (p) => {
  const { plan, flash } = React.useMemo(() => planIntro(p), [p]);
  return <AbsoluteFill style={{ background: "#000" }}><Toma escenario={p.escenario} luz={p.luz} plan={plan} animal={p.animal} /><Blanco en={flash} /></AbsoluteFill>;
};
export const Encuentro: React.FC<PropsPlantilla> = (p) => {
  const plan = React.useMemo(() => planEncuentro(p), [p]);
  return <AbsoluteFill style={{ background: "#000" }}><Toma escenario={p.escenario} luz={p.luz} plan={plan} animal={p.animal} /></AbsoluteFill>;
};
export const Transicion: React.FC<PropsPlantilla> = (p) => {
  const plan = React.useMemo(() => planTransicion(p), [p]);
  return <AbsoluteFill style={{ background: "#000" }}><Toma escenario={p.escenario} luz={p.luz} plan={plan} animal={p.animal} /><Medidor nivel={p.nivel ?? 6} vertical={p.formato === "9:16"} /></AbsoluteFill>;
};
export const Cierre: React.FC<PropsPlantilla> = (p) => {
  const plan = React.useMemo(() => planCierre(p), [p]);
  return <AbsoluteFill style={{ background: "#000" }}><Toma escenario={p.escenario} luz={p.luz} plan={plan} animal={p.animal} /><Globo desde={antes(p.claves.comenta ?? 6.0)} vertical={p.formato === "9:16"} /></AbsoluteFill>;
};
