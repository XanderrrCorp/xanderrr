// FICHA DEL CANAL DE TERROR 3D: todas las reglas del dueño en un solo sitio.
// El montaje (planos.ts), la mezcla (Short.tsx), los subtítulos (Overlay.tsx) y el revisor
// (scripts/revisar_terror.mjs) leen de aquí: cambiar una regla es cambiar un número.
export const SPEC = {
  // FORMATO
  ancho: 1080, alto: 1920, fps: 30,
  duracionMin: 45, duracionMax: 75, duracionIdealMin: 55, duracionIdealMax: 65,
  // RITMO
  planoMin: 1.2, planoMax: 1.6, planoTope: 2.0, // corte cada 1,2–1,6 s; nunca más de 2 s
  planosMin: 35, planosMax: 45,
  planosPorFrase: [1, 2] as const,
  // VOZ
  palabrasPorSegundo: 2.75, // ≈165 palabras por minuto en el video, pausas incluidas (como Rako: 160–170)
  ppmMin: 160, ppmMax: 170,
  pausaAntesDelGiro: 0.4,
  aireAntes: 0.06, aireDespues: 0.1, // aire entre líneas: poco, para que el video quede en 160–170 palabras/min
  // AUDIO (dB relativos a la voz; voz y música salen normalizadas al mismo nivel, ver sonidos_terror.py)
  musicaBajoVozDb: -18, // mientras habla (ducking)
  musicaHuecoDb: -15, // en los huecos sin voz
  silencioAntesDelGiro: 0.5, // la música se calla del todo y luego entra el stinger
  // COLORES (paleta nocturna; el monstruo siempre más frío y pálido que los humanos)
  color: {
    cieloArriba: '#1b2d4f', cieloAbajo: '#0a1222', niebla: '#5d6b80', ventana: '#ffab4a', linterna: '#ff9a3c',
    piel: '#d9a07a', ropa: '#b4512f', madre: '#8a5a7a', monstruo: '#c3d2e2', ojosMonstruo: '#9fe8ff',
  },
  // SUBTÍTULOS
  sub: {
    tam: 92, tamNumero: 130, trazo: 16, y: 1180, // centrados abajo-medio
    blanco: '#ffffff', numero: '#ffb21e', peligro: '#ff3b30', contorno: '#000000',
  },
};
// Palabras de peligro (rojo). Se comparan sin tildes ni signos.
export const PELIGRO = [
  'muerte', 'muerto', 'muerta', 'muertos', 'morir', 'monstruo', 'grito', 'grita', 'gritar', 'corre', 'corrio', 'correr',
  'sangre', 'peligro', 'eso', 'cosa', 'mato', 'matar', 'nadie',
];
// Números y cuentas regresivas (amarillo/naranja y más grandes).
export const NUMEROS = [
  'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez', 'once', 'doce', 'trece',
  'veinte', 'treinta', 'cien', 'mil',
];
export const normal = (w: string) => w.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}:]/gu, '').toLowerCase();
export type TipoPalabra = 'normal' | 'numero' | 'peligro';
export const tipoDe = (w: string): TipoPalabra => {
  const n = normal(w);
  if (/\d/.test(n) || NUMEROS.includes(n)) return 'numero';
  if (PELIGRO.includes(n)) return 'peligro';
  return 'normal';
};
export const dB = (db: number) => Math.pow(10, db / 20);
