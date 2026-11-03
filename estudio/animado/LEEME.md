# Motor de videos animados «Código del Éxito» (El Profesor)

Videos 100 % por código (sin stock): voz MiniMax por segmento, El Profesor con boca de Rhubarb, escenas Pillow,
barra de progreso, efectos de sonido, master -14 LUFS, capítulos, pantalla final, miniaturas y Shorts verticales.
Hecho fuera de Xandart (02/03-11-2026) para 3 videos; PENDIENTE integrarlo a Xandart (ver CLAUDE.md).

Carpeta de cada video (NO va al repo: es contenido privado del dueño):
  guion.txt (marcas <#1.5#> / <#3#>), codigo/ (estos .py), codigo/contenido.py (P = lista de escenas con su frase ancla,
  CAPITULOS, DESCRIPCION, FRASE_FUERTE, ETIQUETA_PROGRESO…), profesor/ (capas PNG 1200x1200 del dueño),
  sfx/ (lapiz, clic, tick, tono, whoosh, pop .wav del dueño), fuentes/ (BebasNeue, Playfair-400/600/700.woff,
  Caveat-400/600/700.woff de @fontsource), musica/ (opcional; pistas sin atribución).

Orden: voz.py → (cd codigo && python plan.py) → labios.py → entrega.py → render.py [segundos] [salida] →
mezcla.py video_sin_mezcla.mp4 final.mp4 → qc_movimiento.py final.mp4 → miniatura_*.py → shorts.py (ganchos aprobados).
render.py --hoja t1,t2,… hoja.jpg  = hoja de cuadros para revisar.
