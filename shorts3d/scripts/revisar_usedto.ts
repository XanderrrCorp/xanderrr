// Revisa el montaje de «Used To» contra su ficha (src/usedto/spec.ts). Uso: node scripts/revisar_usedto.mjs
import {PLANOS, POSE_LOOP, camaraEn} from '../src/usedto/planos';
import {TOTAL, FPS, ESTIMADO, VO, GUION, CIERRE_S} from '../src/usedto/timing';
import {SPEC} from '../src/usedto/spec';

const fallos: string[] = [], avisos: string[] = [];
const seg = TOTAL / FPS, habla = seg - CIERRE_S;
const palabras = Object.values(VO).reduce((n, l) => n + l.words.length, 0);
const ppm = (palabras / habla) * 60;
const durs = PLANOS.map((p) => (p.to - p.from) / FPS);
console.log(`«${GUION.titulo}» · voz ${ESTIMADO ? 'ESTIMADA (sin grabar)' : 'real'} · ${GUION.frases.length} frases · ${palabras} palabras`);
console.log(`duración ${seg.toFixed(1)} s · ${ppm.toFixed(0)} palabras/min · ${PLANOS.length} planos (media ${(seg / PLANOS.length).toFixed(2)} s, de ${Math.min(...durs).toFixed(2)} a ${Math.max(...durs).toFixed(2)} s)`);
if (seg < SPEC.duracionMin || seg > SPEC.duracionMax) fallos.push(`duración ${seg.toFixed(1)} s fuera de ${SPEC.duracionMin}–${SPEC.duracionMax}`);
if (!ESTIMADO && (ppm < SPEC.ppmMin || ppm > SPEC.ppmMax)) avisos.push(`voz a ${ppm.toFixed(0)} palabras/min (ficha ${SPEC.ppmMin}–${SPEC.ppmMax}): cambiar «speed» en guion.json`);
PLANOS.forEach((p, i) => {
  if (durs[i] > SPEC.planoMax + 0.05) fallos.push(`plano ${i + 1} (${p.toma}) dura ${durs[i].toFixed(2)} s > ${SPEC.planoMax}`);
  if (durs[i] < SPEC.planoMin - 0.6) avisos.push(`plano ${i + 1} (${p.toma}) corto: ${durs[i].toFixed(2)} s`);
});
const a = camaraEn(0), b = camaraEn(TOTAL - 1);
const d = Math.hypot(...a.pos.map((v, k) => v - b.pos[k])) + Math.hypot(...a.look.map((v, k) => v - b.look[k]));
if (d > 0.05) fallos.push(`el último cuadro no coincide con el primero (diferencia ${d.toFixed(2)})`);
if (Math.hypot(...a.pos.map((v, k) => v - POSE_LOOP.pos[k])) > 0.05) fallos.push('el primer cuadro no está en la pose del loop');
const bis = GUION.frases.filter((f) => /^(So|But),/.test(f.texto)).length;
console.log(`bisagras So/But: ${bis} · cierre sin voz: ${CIERRE_S} s («${SPEC.cierre}»)`);
if (process.env.LISTA) PLANOS.forEach((p, i) => console.log(`  ${String(i + 1).padStart(2)} ${(p.from / FPS).toFixed(2).padStart(6)}s ${durs[i].toFixed(2)}s ${p.escena.padEnd(4)} ${p.toma} ${p.corte === 'barrido' ? '(barrido)' : ''}`));
avisos.forEach((x) => console.log('  aviso:', x));
fallos.forEach((x) => console.log('  FALLA:', x));
console.log(fallos.length ? `\n${fallos.length} fallos` : '\ncumple la ficha');
process.exit(fallos.length ? 1 : 0);
