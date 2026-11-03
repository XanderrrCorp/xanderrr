# Para Claude Code en el PC del dueño: video de prueba de Peligro Tropical ANIMADO

El dueño abre Claude Code en `C:\Users\USUARIO\AppData\Local\XandartNueva` y escribe «haz el video de la granja».
Respóndele siempre en español, corto y sin jerga (no es técnico). NUNCA lo hagas mientras Xandart esté haciendo otro video.

## Qué es
Guion: `estudio/pt_animado/prueba/guion_granja.json` («De la gallina más mansa al animal de granja que más gente manda al
hospital», ~70 s, 6 animales). Dudas de datos en `prueba/dudas_granja.md`. Todo animado con Remotion
(`estudio/pt_animado/remotion`: explorador, finca/río/sala, plantillas Intro/Encuentro/Cierre) + sonido de la Fase 1
(`estudio/pt_animado/audio/capa.py`). Los canales de Peligro Tropical son GENERALES (no de Colombia).

## Costo (pedir permiso ANTES, una vez)
- Voz MiniMax: ~20 pesos. Imágenes de los 6 animales con Google: ~120 pesos c/u (~720 en total).
- Sin Google (`--sin-google`) los animales salen como la serpiente de prueba: solo paga la voz.

## Pasos
1. ¿Hay Node.js? `node --version`. Si no: `winget install OpenJS.NodeJS.LTS` (o pedirle que lo baje de nodejs.org, LTS) y abrir una
   terminal nueva.
2. Con el Python de Xandart: `.venv\Scripts\python -m estudio.pt_animado.hacer_prueba` (sin gastar: muestra el costo).
3. Con su permiso: `.venv\Scripts\python -m estudio.pt_animado.hacer_prueba --permiso`.
   La primera vez instala lo de Remotion (`npm install` en estudio/pt_animado/remotion) y Remotion baja su Chrome.
   Los clips usan la tarjeta NVIDIA (gl «angle»). Si sale negro o falla el GL, probar `set PT_GL=egl` o `set PT_GL=vulkan`.
4. Queda en `Videos\Xandart\PT animado prueba\peligro_tropical_animado_prueba.mp4`, con `revision\` (short_qa: cuadros negros,
   congelados, saltos) y `cuadro_1..3.jpg`. Revisar el informe de short_qa, arreglar lo que encuentre y mostrarle los 3 cuadros.
5. Se puede retomar: lo ya pagado (voz por frase, imagen por animal, clips hechos) no se repite. Para rehacer un clip, borrar
   solo su .mp4 en `clips\`.

## Reglas
- No tocar Tracy, El Calvo ni otros canales; no borrar nada del dueño (solo los `remotion-webpack-bundle-*` de la carpeta temporal).
- Efectos del veneno o ataques siempre de caricatura, sin sangre ni heridas.
- Avisar que el video lleva imágenes hechas con IA (marcar contenido sintético al subir).
