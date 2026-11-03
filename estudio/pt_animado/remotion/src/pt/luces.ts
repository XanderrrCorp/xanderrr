// Peligro Tropical: 3 luces (amanecer dorado/durazno, día, noche azul) en el formato LightPreset de la skill (shade.ts /
// cardshade.ts las leen). La noche tiene «frío» 0..1: en los sustos se enfría y oscurece (lerp hacia NOCHE_SUSTO).
// Las de día y amanecer parten de los valores probados de la skill (day / golden) movidos a verdes y tierras tropicales.
import type { LightPreset } from "./lights";

export type NombreLuz = "amanecer" | "dia" | "noche";
type C3 = [number, number, number];

export const LUCES: Record<NombreLuz, LightPreset> = {
  dia: {
    az: 70, el: 50,
    lit: [1.58, 1.52, 1.34], shade: [0.42, 0.44, 0.4], lift: [0.05, 0.06, 0.04], lambert: 0.35, sideK: 0.84, term: 0.2,
    charTint: [1.0, 0.95, 0.92], charShade: 0.86, charGrad: 0.07, bodyGrad: 0.2, sideTint: [0.92, 0.92, 0.96],
    blob: [0.6, 0.6, 0.56], actorShadow: true,
    top: "#3f86d4", hor: "#c6dcea", skyCurve: [0.0, 0.5, 0.6], fog: "#c2d8e4", fogNear: 30, fogFar: 320, sunDisc: "#000000",
    sunCol: "#fff3e0", sunI: 2.8, sky: "#dcecff", ground: "#8a9a60", hemiI: 0.55,
    bias: -0.00025, normalBias: 0.015,
  },
  amanecer: {
    az: 58, el: 12,
    lit: [1.55, 0.95, 0.55], shade: [0.42, 0.33, 0.32], lift: [0.06, 0.04, 0.03], lambert: 0.35, sideK: 0.82, term: 0.08,
    charTint: [1.0, 0.84, 0.66], charShade: 0.88, charGrad: 0.1, bodyGrad: 0.25, sideTint: [0.86, 0.82, 0.95],
    blob: [0.74, 0.72, 0.86], actorShadow: true,
    top: "#7a6aa6", hor: "#ffcf96", skyCurve: [0.05, 0.6, 1.0], fog: "#f2b98f", fogNear: 50, fogFar: 380, sunDisc: "#ffd9a8",
    sunCol: "#ffb877", sunI: 5.0, sky: "#f6c89a", ground: "#8a7a50", hemiI: 0.5,
    bias: -0.0006, normalBias: 0.03,
  },
  noche: {
    az: 120, el: 32,
    lit: [0.34, 0.4, 0.6], shade: [0.1, 0.11, 0.17], lift: [0.03, 0.05, 0.12], lambert: 0.4, sideK: 0.8, term: 0.15,
    charTint: [0.66, 0.76, 1.0], charShade: 0.8, charGrad: 0.1, bodyGrad: 0.25, sideTint: [0.8, 0.85, 1.0],
    blob: [0.55, 0.58, 0.7], actorShadow: true,
    top: "#0a1230", hor: "#2c3f6e", skyCurve: [0.0, 0.5, 0.8], fog: "#22335c", fogNear: 12, fogFar: 170, sunDisc: "#000000",
    sunCol: "#9fb8ff", sunI: 1.6, sky: "#3a4c80", ground: "#202a30", hemiI: 0.35,
    bias: -0.0004, normalBias: 0.02,
  },
};

/** la noche en un susto: más fría y oscura */
const NOCHE_SUSTO: Partial<LightPreset> = {
  lit: [0.3, 0.44, 0.95], shade: [0.05, 0.07, 0.18], charTint: [0.55, 0.68, 1.0], top: "#050a20", hor: "#1b2a55", fog: "#152548",
};

const lerp3 = (a: C3, b: C3, t: number): C3 => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const hex = (h: string): C3 => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const lerpHex = (a: string, b: string, t: number) => "#" + lerp3(hex(a), hex(b), t).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");

/** la luz pedida; `frio` 0..1 la enfría (en cualquier luz: los sustos). */
export function luz(nombre: NombreLuz, frio = 0): LightPreset {
  const L = LUCES[nombre];
  if (frio <= 0) return L;
  const t = Math.min(1, frio) * (nombre === "noche" ? 1 : 0.55);
  const S = { ...LUCES.noche, ...NOCHE_SUSTO } as LightPreset;
  return {
    ...L,
    lit: lerp3(L.lit, S.lit, t), shade: lerp3(L.shade, S.shade, t), charTint: lerp3(L.charTint, S.charTint, t),
    top: lerpHex(L.top, S.top, t), hor: lerpHex(L.hor, S.hor, t), fog: lerpHex(L.fog, S.fog, t),
  };
}
