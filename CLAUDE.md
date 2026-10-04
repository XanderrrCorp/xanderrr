# Xandart: notas para retomar (se cargan solas en cada sesión)

Estado al 04-10-2026. El repositorio es PÚBLICO: nunca escribir claves, tokens ni datos privados aquí.

## El dueño y cómo trabajar con él
- No es técnico. Responder SIEMPRE en español, claro y corto, sin jerga. Explicar qué tiene que hacer él, paso a paso.
- Usa Xandart en su PC con Windows (NVIDIA con NVENC; CUDA 12.9 + cuDNN 9 instalados). Instala la versión nueva con
  «Instalar Xandart Nueva». **Nunca decirle que instale mientras haya un video en proceso.**
- Ser proactivo: antes de cualquier proceso, decirle qué debe instalar o preparar. Si dice «espera», esperar.
- **No gastar en pruebas**: nada de llamadas pagadas (imágenes, voz) sin permiso explícito. Probar con proveedor
  simulado, imágenes de colores y Claude falso. Decir el costo antes de gastar; nunca pasar el tope sin permiso.
- Claude (CLI) va por su suscripción: 0 pesos.
- Reglas fijas: no dosis ni tratamientos de salud; no descargar videos de terceros; audio solo con licencia
  verificable; marcar contenido sintético; no copiar textos, personajes ni marcas de la competencia (solo técnicas);
  no borrar nada existente (migraciones, nunca borrar y recrear tablas).
- Advertir (una vez, sin sermón) cuando algo arriesga el canal: caras o nombres de personas reales, contenido
  reutilizado, música sin licencia.

## Ramas y forma de entregar
- Desarrollo: `claude/xandart-saas` (la «versión nueva» que instala). Producción: `claude/new-session-uq98jd`: NO tocar.
- Antes de cada commit: `python -m pytest -q tests` (≈4 min, todo en verde). Si algo falla, no guardar.
- Commit con las líneas de atribución que pida el sistema. Push: `git fetch origin claude/xandart-saas && git merge
  origin/claude/xandart-saas` (la acción «Interfaz» sube builds automáticos) y luego `git push origin claude/xandart-saas`.
- La interfaz React (interfaz/src) la construye la GitHub Action en estudio/web_app: NO subir builds locales
  (si se construye para probar: `git checkout -- estudio/web_app && git clean -fdq estudio/web_app`).
- Para revisar a ojo: renderizar proyectos de prueba en el scratchpad y mandarle hojas de cuadros (SendUserFile).

## Arquitectura (lo esencial)
- `estudio/`: FastAPI (app.py) + motor. Guion (guionista.py, Claude CLI) → imágenes (imagenes/, proveedor Google
  «vertex»; Together ya NO se usa) → voz (voz.py, MiniMax) → EDL (edicion.py) → render (render.py, Pillow+OpenCV,
  tramos en paralelo, NVENC).
- Estilos en estilos/<id>/estilo.json, copiados al espacio de trabajo del usuario. `estudio/imagenes/arreglos.py`
  (CAMPOS + tipos nuevos) lleva los cambios a esas copias al arrancar. Perfiles de edición en perfiles/*.json; ojo:
  el espacio guarda copia de cada perfil la primera vez, así que un cambio de comportamiento va en un perfil NUEVO
  y se apunta con CAMPOS.
- Canales: Peligro Tropical = estilo `enciclopedia_mascota` (canal `animales-peligrosos`), perfil
  `peligro_tropical.json` (movimiento «deslizar»). Paradoja Sapiens = estilo `paradoja_sapiens`, perfil
  `paradoja_historia.json` (movimiento «historia»). Tracy = `estudio/tracy/` (modo stock: guion pegado, MiniMax,
  Whisper, Pexels + clip del seminario, escena final). Mentalidad Imparable = canal solo con plantilla de miniatura.
- Miniaturas: `estudio/miniaturas/` (escala 2x3 de Peligro Tropical) y `texto_retrato.py` + `servicio_texto.py`
  (plantilla «texto_izquierda_retrato_derecha», usada por Tracy con rótulo «BRIAN TRACY» y por Mentalidad Imparable).

## Lo hecho en las últimas sesiones (03 y 04-10)
- Peligro Tropical como la competencia (notas en docs/referencias/competencia_peligro_tropical.md): sin vaivén,
  entradas de lado con swoosh, flechas rojas curvas, escalonado, títulos negros, logo en la esquina, tarjeta de
  especie, tira con guía, término a pantalla completa, pizarra, mini historias, fondo de lugar (Pexels), personaje
  al lado, rayos X. Escenas ilustradas completas a pantalla completa (tarjetas solo para fotos reales y el gancho).
- Paradoja «historia»: pantalla completa con zoom de documental alternado, fundidos, tarjetas de capítulo, viñeta,
  flechas de marcador negro.
- Aspecto de editor (ambos stickman): desenfoque de movimiento, barrido (whip pan) entre escenas, profundidad 2.5D
  (rembg separa sujeto y fondo; cacheado en assets/capas).
- Miniatura texto+retrato: 4 opciones por fórmula, Claude lee el guion, paleta automática, fondos que rotan.
- Arreglos: máximo 8 niveles en el guion, «componer» en video sin niveles usa la imagen vecina.

## Pendiente
- Preguntas sin responder del dueño: ¿en qué canal notó la voz lenta? (Peligro Tropical está en 1.3 en
  config/proveedores.json; Tracy en 1.0 por pedido suyo). ¿En qué momento sale «la tira de animales» sin sentido?
- Propuesto y sin empezar: subtítulos palabra por palabra; revisión automática del video con Claude antes de
  subir; título/descripción/capítulos; volver PRIVADO el repositorio (recomendado ya); asistente para crear canales;
  luz y textura (grano, destellos, color) solo si él lo pide tras ver los videos; estilo simple de Tracy.
- Canal nuevo «Hazlo con Calma»: el dueño mandará capturas y guiones de la competencia; analizar escena por escena
  y sacar la estructura del guion (sin copiar textos) antes de construir.
- Editor (música, mover, cortar): en pausa por pedido del dueño; backend hecho, sin interfaz.
