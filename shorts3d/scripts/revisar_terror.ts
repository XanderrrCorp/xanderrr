// Revisa que el montaje cumpla la ficha del canal (src/terror/spec.ts). Uso: node scripts/revisar_terror.mjs
import {PLANOS, ENCUADRE_LOOP, WHOOSH} from '../src/terror/planos';
import {TOTAL, FPS, ESTIMADO, VO, GUION, CUADRO_GIRO, ESCENAS} from '../src/terror/timing';
import {SPEC} from '../src/terror/spec';

const fallos: string[] = [], avisos: string[] = [];
const seg = TOTAL / FPS;
const durs = PLANOS.map((p) => (p.to - p.from) / FPS);
const palabras = Object.values(VO).reduce((n, l) => n + l.words.length, 0);
const habla = Object.values(VO).reduce((n, l) => n + (l.voiceEnd - l.voiceStart), 0);
console.log(`«${GUION.titulo}» · voz ${ESTIMADO ? 'ESTIMADA (sin grabar)' : 'real'}`);
console.log(`duración ${seg.toFixed(1)} s · ${PLANOS.length} planos · media ${(seg / PLANOS.length).toFixed(2)} s · ${palabras} palabras · ${(palabras / seg).toFixed(2)} palabras/s = ${((palabras / seg) * 60).toFixed(0)} palabras/min (${((palabras / habla) * 60).toFixed(0)} al hablar)`);
const ppm = (palabras / seg) * 60;
if (!ESTIMADO && (ppm < SPEC.ppmMin || ppm > SPEC.ppmMax)) avisos.push(`voz a ${ppm.toFixed(0)} palabras/min (ficha ${SPEC.ppmMin}–${SPEC.ppmMax}): cambiar «speed» en guion.json y volver a grabar`);
if (seg < SPEC.duracionMin || seg > SPEC.duracionMax) fallos.push(`duración ${seg.toFixed(1)} s fuera de ${SPEC.duracionMin}–${SPEC.duracionMax}`);
else if (seg < SPEC.duracionIdealMin || seg > SPEC.duracionIdealMax) avisos.push(`duración ${seg.toFixed(1)} s fuera del ideal ${SPEC.duracionIdealMin}–${SPEC.duracionIdealMax}`);
if (PLANOS.length < SPEC.planosMin || PLANOS.length > SPEC.planosMax) fallos.push(`${PLANOS.length} planos (ficha: ${SPEC.planosMin}–${SPEC.planosMax})`);
PLANOS.forEach((p, i) => {
  const d = durs[i];
  if (d > SPEC.planoTope + 1e-6) fallos.push(`plano ${i + 1} (${p.tipo}:${p.foco}) dura ${d.toFixed(2)} s > ${SPEC.planoTope}`);
  else if (d < SPEC.planoMin - 0.25) avisos.push(`plano ${i + 1} (${p.tipo}:${p.foco}) muy corto: ${d.toFixed(2)} s`);
});
const enRango = durs.filter((d) => d >= SPEC.planoMin && d <= SPEC.planoMax).length;
console.log(`planos en 1,2–1,6 s: ${enRango}/${PLANOS.length} · el más largo ${Math.max(...durs).toFixed(2)} s · el más corto ${Math.min(...durs).toFixed(2)} s`);
// plano general solo al inicio y en el clímax (último tercio)
PLANOS.forEach((p, i) => {
  if (p.tipo === 'general' && p.from > 4 * FPS && p.from < TOTAL * 0.66) fallos.push(`plano general en ${(p.from / FPS).toFixed(1)} s: solo al inicio y en el clímax`);
});
// dos planos seguidos con el mismo encuadre
PLANOS.slice(1).forEach((p, i) => { if (p.tipo === PLANOS[i].tipo && p.foco === PLANOS[i].foco) avisos.push(`planos ${i + 1} y ${i + 2} con el mismo encuadre (${p.tipo}:${p.foco})`); });
// loop: el último plano arranca donde empieza el primero
const ult = PLANOS[PLANOS.length - 1], pri = PLANOS[0];
const dist = Math.hypot(...ult.a.pos.map((v, k) => v - pri.a.pos[k]));
if (dist > 3) fallos.push(`el último plano no se parece al primero (cámara a ${dist.toFixed(1)} m)`);
if (pri.a !== ENCUADRE_LOOP.a) fallos.push('el primer plano no usa el encuadre del loop');
// giro
if (CUADRO_GIRO < 0) fallos.push('el guion no marca ninguna línea con "giro"');
else console.log(`giro en ${(CUADRO_GIRO / FPS).toFixed(2)} s (pausa ${SPEC.pausaAntesDelGiro} s, música en silencio ${SPEC.silencioAntesDelGiro} s antes, stinger)`);
if (!ESCENAS.some((e) => e.linea.cta)) fallos.push('el guion no marca la línea del CTA');
console.log(`transiciones whoosh: ${WHOOSH.length}`);
if (process.env.LISTA) PLANOS.forEach((p, i) => console.log(`  ${String(i + 1).padStart(2)} ${(p.from / FPS).toFixed(2).padStart(6)}s ${durs[i].toFixed(2)}s ${p.escena.padEnd(4)} ${p.tipo}:${p.foco}`));
avisos.forEach((a) => console.log('  aviso:', a));
fallos.forEach((a) => console.log('  FALLA:', a));
console.log(fallos.length ? `\n${fallos.length} fallos` : '\ncumple la ficha');
process.exit(fallos.length ? 1 : 0);
