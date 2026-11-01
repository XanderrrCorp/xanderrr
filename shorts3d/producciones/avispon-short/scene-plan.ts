// Plan de escenas del Short «El avispón gigante contra la bola de calor» (versión 1, ESPERANDO APROBACIÓN).
// Mismo contrato que src/data/scenes.ts: startFrame global, todo lo demás en cuadros LOCALES.
// Antes de la voz real los cortes salen de PLANNED_SECONDS; después, de la duración medida de cada frase.

export const PLANNED_SECONDS = [5, 6, 6, 6, 7, 7, 8]; // suman 45 s = 1350 cuadros
export const VO_KEYS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7"] as const;

type Vec3 = [number, number, number];
type Pose = { target: Vec3; dist: number; az: number; el: number };
const orbit = (target: Vec3, dist: number, az: number, el: number): Pose => ({ target, dist, az, el });

export const SCENES = [
  {
    id: "s1-pulgar", startFrame: 0, durationInFrames: 150, voKey: "s1",
    narration: "Este avispón es del tamaño de tu pulgar… y acaba de encontrar una colmena.",
    camera: { movement: "dolly-out", keys: [
      { at: 0, pose: orbit([0, 1.2, 4], 6, -20, 6) },
      { at: 150, pose: orbit([0, 1.2, 2], 9, 0, 8), easing: "soft" } ] },
    objects: ["hornet", "thumb", "branch", "trunk", "hive"],
    animations: [
      { type: "interpolate", target: "hornet.fly", startFrame: 0, endFrame: 40, from: 0, to: 1, easing: "out", unit: "0-1" },
      { type: "spring", target: "thumb.show", startFrame: 8, endFrame: 60, from: 0, to: 1, damping: 12, unit: "0-1" },
      { type: "interpolate", target: "thumb.show", startFrame: 60, endFrame: 75, from: 1, to: 0, easing: "in", unit: "0-1" },
    ],
    badges: [{ text: "¿DEL TAMAÑO DE TU PULGAR?", variant: "warning", icon: "?", appearAt: 10, disappearAt: 140 }],
    highlights: ["PULGAR", "COLMENA"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/whoosh.wav", at: 0, volume: 0.5 }, { kind: "sfx", src: "audio/sfx/zumbido.wav", at: 0, volume: 0.25 }],
  },
  {
    id: "s2-armadura", startFrame: 150, durationInFrames: 180, voKey: "s2",
    narration: "Mide unos cinco centímetros. Su armadura es tan gruesa que las picaduras de abeja casi no le hacen daño.",
    camera: { movement: "orbit", keys: [
      { at: 0, pose: orbit([0, 1.2, 2], 9, 0, 8) },
      { at: 30, pose: orbit([0, 1.1, 2], 7, 10, 10), easing: "soft" },
      { at: 180, pose: orbit([0, 1.1, 2], 7, 35, 10) } ] },
    objects: ["hornet", "ruler", "bees.attackers", "hive"],
    animations: [
      { type: "interpolate", target: "ruler.grow", startFrame: 15, endFrame: 45, from: 0, to: 1, easing: "out", unit: "0-1" },
      { type: "interpolate", target: "bees.attack", startFrame: 70, endFrame: 150, from: 0, to: 1, easing: "linear", unit: "0-1" },
    ],
    badges: [
      { text: "5 CM", variant: "info", appearAt: 12, disappearAt: 70 },
      { text: "ARMADURA", variant: "negative", appearAt: 60, disappearAt: 175 },
    ],
    highlights: ["CINCO", "ARMADURA", "DAÑO"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/tic-metal.wav", at: 80, volume: 0.4 }, { kind: "sfx", src: "audio/sfx/tic-metal.wav", at: 105, volume: 0.4 }, { kind: "sfx", src: "audio/sfx/tic-metal.wav", at: 130, volume: 0.4 }],
  },
  {
    id: "s3-mandibulas", startFrame: 330, durationInFrames: 180, voKey: "s3",
    narration: "Con sus mandíbulas, unos pocos avispones pueden acabar con una colmena entera en unas horas.",
    camera: { movement: "dolly-in", keys: [
      { at: 0, pose: orbit([0, 1.1, 2], 7, 35, 10) },
      { at: 50, pose: orbit([0, 1.25, 2.4], 4, 20, 6), easing: "soft" },
      { at: 100, pose: orbit([0, 1.5, 0], 14, 15, 12), easing: "inOut" },
      { at: 180, pose: orbit([0, 1.5, 0], 13, 5, 12) } ] },
    objects: ["hornet", "hornets.extra", "hive", "clock"],
    animations: [
      { type: "interpolate", target: "jaws.open", startFrame: 0, endFrame: 100, from: 0, to: 1, easing: "linear", unit: "0-1" },
      { type: "spring", target: "hornets.extra", startFrame: 95, endFrame: 150, from: 0, to: 1, damping: 11, unit: "0-1" },
      { type: "interpolate", target: "hive.alarm", startFrame: 110, endFrame: 180, from: 0, to: 1, easing: "linear", unit: "0-1" },
    ],
    badges: [{ text: "COLMENA EN PELIGRO", variant: "negative", appearAt: 100, disappearAt: 175 }],
    highlights: ["MANDÍBULAS", "COLMENA", "HORAS"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/alarma.wav", at: 110, volume: 0.3 }],
  },
  {
    id: "s4-truco", startFrame: 510, durationInFrames: 180, voKey: "s4",
    narration: "Pero la abeja japonesa tiene un truco. Cuando el avispón entra, cientos lo rodean.",
    camera: { movement: "orbit", keys: [
      { at: 0, pose: orbit([0, 1.5, 0], 13, 5, 12) },
      { at: 60, pose: orbit([0, 1.4, 0], 10, 10, 15), easing: "soft" },
      { at: 180, pose: orbit([0, 1.4, 0], 9, 40, 15) } ] },
    objects: ["hornet", "hive", "bees.swarm"],
    animations: [
      { type: "interpolate", target: "hornet.enter", startFrame: 20, endFrame: 60, from: 0, to: 1, easing: "inOut", unit: "0-1" },
      { type: "interpolate", target: "bees.swarm", startFrame: 70, endFrame: 170, from: 0, to: 1, easing: "inOut", unit: "0-1" },
    ],
    badges: [{ text: "ABEJA JAPONESA", variant: "positive", appearAt: 20, disappearAt: 175 }],
    highlights: ["TRUCO", "CIENTOS", "JAPONESA"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/enjambre.wav", at: 70, volume: 0.35 }],
  },
  {
    id: "s5-bola", startFrame: 690, durationInFrames: 210, voKey: "s5",
    narration: "Forman una bola apretada y empiezan a vibrar los músculos de las alas. Sin volar.",
    camera: { movement: "dolly-in", keys: [
      { at: 0, pose: orbit([0, 1.4, 0], 9, 40, 15) },
      { at: 50, pose: orbit([0, 1.4, 0], 6, 30, 10), easing: "soft" },
      { at: 210, pose: orbit([0, 1.4, 0], 5, 15, 8) } ] },
    objects: ["hive", "bees.ball", "hornet", "vibration.rings"],
    animations: [
      { type: "interpolate", target: "ball.tight", startFrame: 0, endFrame: 40, from: 0, to: 1, easing: "out", unit: "0-1" },
      { type: "interpolate", target: "ball.vibrate", startFrame: 80, endFrame: 100, from: 0, to: 1, easing: "out", unit: "0-1" },
      { type: "interpolate", target: "ball.cutaway", startFrame: 120, endFrame: 150, from: 0, to: 1, easing: "inOut", unit: "0-1" },
    ],
    badges: [
      { text: "BOLA DE ABEJAS", variant: "positive", appearAt: 20, disappearAt: 130 },
      { text: "SIN VOLAR", variant: "info", appearAt: 150, disappearAt: 205 },
    ],
    highlights: ["BOLA", "VIBRAR"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/vibracion.wav", at: 80, volume: 0.35 }],
  },
  {
    id: "s6-calor", startFrame: 900, durationInFrames: 210, voKey: "s6",
    narration: "Esa vibración sube el calor hasta unos cuarenta y seis grados. Las abejas lo aguantan. El avispón, no.",
    camera: { movement: "tracking", keys: [
      { at: 0, pose: orbit([0, 1.4, 0], 5, 15, 8) },
      { at: 40, pose: orbit([-0.8, 1.5, 0], 8, 0, 6), easing: "soft" },
      { at: 210, pose: orbit([-0.6, 1.5, 0], 7.5, -10, 6) } ] },
    objects: ["hive", "bees.ball", "hornet", "thermometer", "heat.particles"],
    animations: [
      { type: "interpolate", target: "heat.level", startFrame: 20, endFrame: 150, from: 0, to: 1, easing: "inOut", unit: "0-1" },
      { type: "interpolate", target: "ball.glow", startFrame: 20, endFrame: 150, from: 0, to: 1, easing: "inOut", unit: "0-1" },
    ],
    badges: [
      { text: "~46 °C", variant: "info", appearAt: 110, disappearAt: 205 },
      { text: "ABEJAS: AGUANTAN", variant: "positive", appearAt: 150, disappearAt: 205 },
      { text: "AVISPÓN: NO", variant: "negative", appearAt: 180, disappearAt: 208 },
    ],
    highlights: ["CALOR", "GRADOS", "AGUANTAN"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/tic.wav", at: 20, volume: 0.3 }],
  },
  {
    id: "s7-video-completo", startFrame: 1110, durationInFrames: 240, voKey: "s7",
    narration: "Lo cocinan con puro calor. ¿Y el que no puede picarte ni aunque quiera? Está en el video completo.",
    camera: { movement: "dolly-out", keys: [
      { at: 0, pose: orbit([-0.6, 1.5, 0], 7.5, -10, 6) },
      { at: 120, pose: orbit([0, 1.5, 0], 16, 10, 14), easing: "soft" },
      { at: 240, pose: orbit([0, 1.5, 0], 17, 18, 15) } ] },
    objects: ["hive", "bees.swarm", "hornet", "cta.arrow"],
    animations: [
      { type: "interpolate", target: "ball.tight", startFrame: 0, endFrame: 50, from: 1, to: 0, easing: "inOut", unit: "0-1" },
      { type: "interpolate", target: "heat.level", startFrame: 0, endFrame: 60, from: 1, to: 0, easing: "inOut", unit: "0-1" },
      { type: "interpolate", target: "hornet.down", startFrame: 20, endFrame: 60, from: 0, to: 1, easing: "in", unit: "0-1" },
    ],
    badges: [
      { text: "AVISPÓN VENCIDO", variant: "positive", appearAt: 10, disappearAt: 90 },
      { text: "¿EL QUE NO PUEDE PICARTE?", variant: "warning", icon: "?", appearAt: 95, disappearAt: 240 },
      { text: "VIDEO COMPLETO ▼", variant: "info", size: "large", appearAt: 160 },
    ],
    highlights: ["CALOR", "VIDEO", "COMPLETO"],
    audioCues: [{ kind: "sfx", src: "audio/sfx/golpe.wav", at: 160, volume: 0.4 }],
  },
] as const;
