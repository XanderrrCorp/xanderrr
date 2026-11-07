# Para Claude Code en el PC del dueño: dejar listo «Código del Éxito» (videos largos con el Profesor + Pexels)

El dueño abre Claude Code en `C:\Users\USUARIO\AppData\Local\XandartNueva` y escribe «lee estudio/codigo_exito/PREPARAR_EN_EL_PC.md
y prepáralo». Respóndele siempre en español, corto y sin jerga (no es técnico). NUNCA hagas esto mientras Xandart esté
haciendo un video. No borres ni muevas nada suyo: solo COPIA.

## Qué hay que dejar listo
Carpeta destino (créala si no existe): `datos\codigo_exito\` dentro de la instalación, con tres carpetas:

1. `profesor\` — las capas PNG del Profesor (OBLIGATORIO). Son estos archivos (1200x1200, transparentes):
   `fondo.png, cuerpo.png, cabeza_base.png, ojos_abiertos.png, ojos_cerrados.png, rasgos.png, bigote.png, brazo_sien.png,
   boca_A.png … boca_H.png, boca_X.png`.
   Búscalos en su PC: suelen estar en `Descargas` (`C:\Users\USUARIO\Downloads`), en el Escritorio o en Documentos, sueltos
   o dentro de un .zip (p. ej. «profesor.zip»). Busca por el nombre `cabeza_base.png` (también dentro de los .zip).
   Si hay varias copias, usa la más reciente. Si no aparecen, pregúntale dónde guardó «las capas del Profesor».
2. `sfx\` — sus efectos de sonido: `whoosh.wav, pop.wav, clic.wav, lapiz.wav, tick.wav, tono.wav` (búscalos igual; si no
   están, sigue: el video sale sin efectos).
3. `musica\` — su música de fondo (mp3/wav) SOLO si tiene una carpeta de música con licencia para este canal; pregúntale
   antes de copiar cualquier música (regla: solo audio con licencia). Si no, vacía: se usa una música suave por código.

## Además
- Rhubarb Lip Sync (gratis, para que la boca del Profesor siga la voz sílaba por sílaba): bájalo de
  https://github.com/DanielSWolf/rhubarb-lip-sync/releases (Rhubarb-Lip-Sync-1.13.0-Windows.zip), descomprímelo en
  `datos\codigo_exito\rhubarb\` y guarda en el archivo `.env` de la instalación la línea `RHUBARB=<ruta completa a rhubarb.exe>`
  (no borres ninguna otra línea del .env). Sin Rhubarb la boca se mueve con el volumen (también sirve).
- Node.js: `node --version`. Si no está: `winget install OpenJS.NodeJS.LTS`.
- Clave de Pexels: que exista `PEXELS_API_KEY` en el `.env` (la misma de Tracy). No la muestres en pantalla.

## Al terminar
Abre la página de Xandart «Código del Éxito» (menú «Tu estudio») y dile qué quedó listo y qué falta. Si quiere probar:
el guion de prueba está en `estudio/codigo_exito/ejemplos/prueba_regla_dos_minutos.txt` (cuesta ~40 pesos de voz:
pídele permiso antes).
