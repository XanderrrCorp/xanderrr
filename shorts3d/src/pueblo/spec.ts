// FICHA DEL CANAL «EN ESTE PUEBLO…» (6 Shorts que comparten pueblo, estilo y personajes). Una regla, un número.
export const SPEC = {
  ancho: 1080, alto: 1920, fps: 30,
  duracionMin: 105, duracionMax: 125, // 1:45–2:05
  ppmMin: 170, ppmMax: 180, // voz rápida y rítmica
  planoMin: 1.0, planoMax: 2.0, planoIdeal: 1.5, // cámara estática por plano, cortes de 1–2 s
  punchIn: 1.05, // zoom del 5 % en los golpes
  reglaAntesDe: 2.0, // la regla del pueblo va en los primeros 2 s
  // tono de la voz para los diálogos (un solo narrador): más agudo para niños, más grave para Don Bruno
  tono: {narrador: 0, nino: 4, nina: 5, bruno: -5, adulto: -2, criatura: -7, abuela: 3},
  musicaBajoVozDb: -18, musicaHuecoDb: -14,
  sub: {tam: 82, trazo: 18, y: 1330, blanco: '#FFFFFF', amarillo: '#FFD400', contorno: '#000000'},
  color: {
    cielo: '#4fb4ff', cieloBajo: '#bfe6ff', pasto: '#4cc24a', camino: '#d9c7a0', plaza: '#cfc8bb',
    noche: '#1b2a5a', nocheBajo: '#2c4a8a', ventana: '#ffc45c', farol: '#ffb347',
    techoRojo: '#e0442f', techoNaranja: '#f28a1b', techoAzul: '#2f6fe0',
  },
};
export const dB = (db: number) => Math.pow(10, db / 20);
export const limpio = (w: string) => w.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}:]/gu, '').toLowerCase();
