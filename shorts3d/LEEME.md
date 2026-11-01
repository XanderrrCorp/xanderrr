# Shorts 3D (Remotion)

Shorts verticales en 3D low-poly para Peligro Tropical, hechos por código con Remotion + Three.js.
Código propio: sigue las TÉCNICAS de la skill «remotion-problem-resolve-video» (el ZIP no trae licencia,
así que no se copió su código).

## Producciones
- `producciones/avispon-short`: el avispón gigante y la bola de calor (composición `AvisponGigante`, 39 s).
- `producciones/pantera-short`: «La pantera negra no existe» (composición `PanteraNegra`, ~31 s), con la
  fórmula de Shorts del dueño (ver CLAUDE.md).

## Cómo se arma uno
1. Guion con la fórmula de Shorts → aprobación del dueño (y del costo de la voz).
2. Voz: `python scripts/voz_minimax.py` (MiniMax, voz del canal, velocidad 1,3; COBRA, unos 10 pesos por Short)
   y `python scripts/medir_voz.py` (tiempos por palabra → `vo.json`). Con `PROD=pantera` para la pantera.
3. Sonidos y música por código: `python scripts/sonidos.py` y `python scripts/sonidos_pantera.py`.
4. Revisar cuadros: `node scripts/cuadros.mjs 10,200,400 carpeta` (con `COMP=PanteraNegra`) y `scripts/hoja.sh carpeta`.
5. Grabar: `npx remotion render src/index.ts <Composición> out/<nombre>.mp4 --gl=swangle --concurrency=4 --crf=17`
   (en la nube con `--browser-executable` del Chromium instalado; en el PC con NVIDIA se puede usar `--gl=angle`).
6. Volumen YouTube: `ffmpeg -i in.mp4 -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k out.mp4`.

## Reglas aprendidas
- Los efectos SIEMPRE por debajo de la voz (ganancia 0,45 y bajan al 40 % mientras habla).
- Nada de sonidos de fondo continuos sintéticos (grillos, zumbidos): se oyen como un zumbido molesto.
- Escenas de noche CLARAS: cielo azul medio, luz de relleno fuerte y pelaje gris carbón (no negro puro); solo un plano puede ser casi negro.
- Los cortes salen de la voz real (`timing.ts`), no de los tiempos del guion.
- Marcar «contenido alterado o sintético» al subir (la voz es clonada) y poner el largo en «Video relacionado».
