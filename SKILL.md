---
name: ines-video
description: Produce un video terminado de La Libreta de Inés (canal de finanzas prácticas para mujeres, personaje Inés dibujado a mano) a partir de solo una idea o título: guion con fórmula de retención, plan de escenas, voz MiniMax, animación, música y paquete SEO.
---

# Video de La Libreta de Inés: de la idea al MP4

El usuario solo da una idea o un título. Tú entregas `video_final.mp4`, la miniatura (prompt de Flow) y el paquete SEO, sin pedirle nada más salvo que algo sea imposible.

## Requisitos (revisa una vez)
- Python 3.10+ con `pip install pillow numpy`
- `ffmpeg` y `ffprobe` en el PATH
- Variable de entorno `MINIMAX_API_KEY` (y `MINIMAX_GROUP_ID` si la cuenta lo pide). Voz: `Spanish_Fussyhostess`.
  Si el usuario ya genera voz con MiniMax de otra forma en esta PC, usa ese mismo método y guarda los MP3 en `proyectos/<slug>/voz/` con los nombres que lista `python engine/make_video.py <plan> --textos` (archivo voz/textos.json), o ajusta `engine/tts.py` (host y modelo se cambian con `MINIMAX_HOST` y `MINIMAX_MODEL`).

## Flujo (en este orden, sin saltarte pasos)
1. **Guion.** Lee `references/guion.md` y escribe el guion completo siguiendo la fórmula: español neutro, dólares, sin regionalismos, 1.700–2.300 palabras. Guárdalo en `proyectos/<slug>/guion.md`.
2. **Plan de escenas.** Lee `references/plan.md`. Parte el guion en escenas de 1 a 3 frases (de 4 a 10 s cada una) y asigna a cada una una plantilla. Escribe `proyectos/<slug>/plan.json`. Usa `proyectos/7-cosas-ya-no-compro/hacer_plan.py` como ejemplo de cómo se ve un plan bueno.
3. **Revisión visual barata:** `python engine/make_video.py proyectos/<slug>/plan.json --sin-voz --fotos`. Abre las fotos en `proyectos/<slug>/fotos/` y corrige textos que se salgan, palabras repetidas o escenas aburridas (no más de 2 escenas seguidas de la misma plantilla).
4. **Video completo:** `python engine/make_video.py proyectos/<slug>/plan.json`. Genera la voz por escena (con caché), renderiza en paralelo, mezcla música y efectos, y normaliza a -14 LUFS. Si cambias una escena, vuelve a correr el comando: solo se renderiza lo que cambió.
5. **Control de calidad:** saca 6 fotogramas del MP4 final con ffmpeg y míralos. Revisa que la duración total esté entre 10 y 16 min y que el audio no se corte.
6. **Paquete de publicación** (`proyectos/<slug>/publicar.md`), según `references/seo.md`: título, prompt de miniatura para Flow, descripción, etiquetas y comentario fijado.

## Reglas del canal (no negociables)
- Inés es un personaje original. No imites a otros canales (ni Estoy Tiesa, ni Sra. Economy, ni El té de Hana): ni su personaje, ni sus frases, ni su formato de miniatura.
- Las cifras de ejemplo deben ser coherentes (haz la cuenta en Python). Los datos reales llevan la fuente en pantalla (`nota`) y en la descripción.
- El producto se menciona una vez cerca del minuto 1–2 y una vez en el cierre. Nunca más.
- Al subir, marca la casilla de contenido alterado o sintético (la voz es IA).
- Lema del canal: "Aquí hacemos las cuentas que nadie te muestra." Cierre fijo: "El dinero sí alcanza. Cuando haces las cuentas."
