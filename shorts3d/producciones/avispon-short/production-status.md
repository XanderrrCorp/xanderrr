# Estado de producción — Short del avispón gigante

- Fase: 2 (armado y grabación). Guion versión 1 APROBADO por el dueño el 01-11-2026 («si y si la de minimax»).
- Voz: MiniMax, voz clonada del canal, velocidad 1,3; 715 caracteres cobrados en total (incluye volver a grabar s4).
- Ajuste de contenido avisado: s4 decía «cientos la rodean» (error de concordancia); se grabó «cientos lo rodean».
- Ajustes de sincronía (sin cambiar contenido): los cortes salen de la voz real (31 s de habla);
  duración final ≈ 38,9 s (1168 cuadros) en vez de 45 s. Cuadros de inicio: s1 0, s2 126, s3 304, s4 451,
  s5 612, s6 749, s7 940.
- Proyecto: scratchpad/rem (src/timing.ts, estado.ts, camara.ts, World.tsx, Overlay.tsx, Short.tsx;
  scripts/voz_minimax.py, medir_voz.py, sonidos.py, cuadros.mjs, hoja.sh).
- Volver a grabar: npx remotion render src/index.ts AvisponGigante out/avispon-raw.mp4 --gl=swangle --concurrency=4 --crf=17
  (con --browser-executable del Chromium instalado).
- Pendiente: render completo, revisión con ffprobe y cuadros del MP4, normalizar volumen.
