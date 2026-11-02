// FICHA DEL CANAL «USED TO» (Shorts en inglés, «Why ___ Used to ___»). Todas las reglas del dueño en un sitio:
// el montaje, la cámara, los subtítulos, la mezcla y el revisor (scripts/revisar_usedto.mjs) leen de aquí.
export const SPEC = {
  canal: 'USED TO',
  ancho: 1080, alto: 1920, fps: 30,
  duracionMin: 65, duracionMax: 80,
  // ritmo: ángulo o cambio visual nuevo cada 2–4 s, amarrado a cada frase
  planoMin: 2.0, planoMax: 4.0, planoIdeal: 2.8,
  // voz: inglés americano, ~155–165 palabras/min, un respiro tras cada «But,» y «So,»
  ppmMin: 155, ppmMax: 165, pausaTrasBisagra: 0.28,
  // mezcla (voz y música al mismo RMS, ver sonidos_usedto.py)
  musicaBajoVozDb: -18, musicaHuecoDb: -15,
  // paleta
  color: {
    teal: '#004040', tealClaro: '#4DB6AC', ambar: '#C88E16', maderaOscura: '#3E2723', maderaCalida: '#8D6E63',
    rojo: '#D32F2F', oro: '#D4AF37', blanco: '#FFFFFF', ladrillo: '#7a3b2a', mortero: '#b9ab98', acero: '#c9cfd6',
  },
  // luz: llave cálida ~3500 K arriba-izquierda, relleno frío a la derecha, contraluz fuerte
  luz: {llave: '#ffc58f', relleno: '#9cc4ff', contra: '#fff0dc'},
  sub: {tam: 74, y: 1390, amarillo: '#FFD400', blanco: '#FFFFFF'},
  // el cierre: texto sin voz en los 2 últimos segundos (no rompe el loop)
  cierre: 'Follow for more Why It Used To',
};
// palabras resaltadas en AMARILLO: las bisagras, números y nombres; los nombres propios de cada episodio
// se marcan en guion.json («resaltar»).
export const BISAGRAS = ['but', 'so', 'finally', 'today'];
export const dB = (db: number) => Math.pow(10, db / 20);
export const limpio = (w: string) => w.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^\p{L}\p{N}]/gu, '').toLowerCase();
