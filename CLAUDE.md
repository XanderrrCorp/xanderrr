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
- REGLA FIJA (21-10): NUNCA borrar, renombrar ni modificar sus canales, estilos, personajes, presets ni proyectos
  existentes sin pedirle permiso explícito antes.
- Reglas fijas: no dosis ni tratamientos de salud; no descargar videos de terceros; audio solo con licencia
  verificable; marcar contenido sintético; no copiar textos, personajes ni marcas de la competencia (solo técnicas);
  no borrar nada existente (migraciones, nunca borrar y recrear tablas).
- Advertir (una vez, sin sermón) cuando algo arriesga el canal: caras o nombres de personas reales, contenido
  reutilizado, música sin licencia.

## Visión de producto Xandart (21-10, del dueño: aplicar en R y en B a J, y en todo chat nuevo)
- Usuarios BETA: miembros de su comunidad que empiezan en YouTube, NO técnicos (no saben qué es capa, batch, TTS,
  group size ni character lock). Quieren poner su idea y tener un video listo para subir. El OWNER conserva todas las
  funciones avanzadas y sus módulos privados.
- Principios OBLIGATORIOS en toda pantalla nueva o rediseñada:
  1. Un solo camino principal: idea → guion → video → miniatura y SEO → descargar (desde Inicio, sin perderse).
  2. Modo simple por defecto (duración, voz, estilo, segundos por escena, calidad ya decididos); lo técnico en
     «Opciones avanzadas».
  3. Cero lenguaje técnico para BETA: «Calidad: Normal / Alta», «Voz», «Tu personaje», «Duración».
  4. Ver antes de pagar: costo en créditos junto a cada botón que gasta (componente interfaz/src/componentes/Costo.tsx).
  5. Nada se pierde: guardado automático, salir y volver a un proyecto, deshacer en el editor.
  6. Errores humanos: qué pasó en palabras simples, «Reintentar», créditos devueltos solos (api.humano, ErrorAmable).
  7. Español por defecto (inglés en la interfaz más adelante).
- Protección de sus fórmulas: para BETA, guion/SEO/miniaturas con fórmulas GENÉRICAS de buenas prácticas de YouTube
  escritas desde cero; NUNCA sus prompts privados (estructura de Tracy, plantillas de miniatura, CTA de productos,
  prompts de sus canales).
- OLA 1 (beta, prioridad alta; antes de programar: tabla existe / a medias / no existe y esperar aprobación):
  onboarding guiado (de qué es el canal, idioma, tipo de video → sugerir voz/estilo/personaje → primer video de
  prueba), video de prueba gratis con créditos de bienvenida, guion desde un tema o pegado, revisión del guion con
  duración y costo antes de producir, aviso en la app y por correo al terminar (cola visible), storyboard en vivo
  (hecho en R), editor básico de escenas (regenerar con palabras, cambiar texto/duración, «Reintentar esta escena»),
  subtítulos con 3-4 estilos editables, miniatura con 2-3 opciones, paquete SEO (título, descripción, tags), descarga
  completa (video, miniatura, SRT, SEO; 16:9 y 9:16), historial de créditos claro, ayuda por pantalla + «Reportar
  problema» con la información del error.
- Ola 1 APROBADA (21-10) con este orden: Bloque 1 (historial de créditos, ayuda + reportar, revisión con duración y
  costo total, «Reintentar esta escena», avisos) → pasos B, C, D → Bloque 2 (guion genérico + pegar guion, SEO,
  miniatura genérica con 3 opciones, 3-4 estilos de subtítulos, descarga completa .zip y 9:16, KIT DE CANAL) → pasos E
  a J → Bloque 3 (onboarding guiado completo, video de prueba gratis, kit dentro del onboarding).
- KIT DE CANAL DE YOUTUBE (aprobado): a) 10 nombres con @handle (nada de famosos ni marcas: aviso + alternativas;
  «posiblemente ocupado» mirando youtube.com/@handle, siempre «confírmalo en YouTube»); b) logo 800×800, 3 opciones,
  vista en círculo, puede ser el personaje; c) banner 2560×1440: Google pinta solo el fondo y el nombre/frase van por
  código dentro de la zona segura 1546×423, vista celular/PC/TV, 2-3 opciones con la paleta del logo; d) descripción
  ≤1.000 caracteres editable; e) palabras clave para copiar; f) guía de YouTube Studio + «Descargar mi kit» (.zip) y
  botones de copiar. Se guarda en el canal (nombre, logo, paleta) y se usa en miniaturas y videos. Precios: textos 10
  créditos, logo 30, banner 30, kit 70, regenerar logo/banner 10 (costo real ≈ 0,45 USD). GRATIS una vez a cada
  usuario nuevo, APARTE de los 300 créditos de bienvenida. Fórmulas genéricas, nunca sus prompts.
- OLA 2 (NO programar todavía): generador de ideas y títulos, Shorts automáticos de los mejores momentos, música de
  fondo con volumen automático bajo la voz, galería de ejemplos por estilo, mini tutoriales en video.

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
- Animación por código (04-10): `estudio/calma/` = personaje en piezas SVG (trazo de marcador, resvg-py), movimientos
  con rebote, escenas.json atado a palabras de Whisper, render OpenCV+ffmpeg (60 s en ~30 s). Canal «Hazlo con Calma»
  (supervivencia, página /calma, prueba de la garrapata): guardado TAL CUAL, no tocar; le falta el código de voz.
- «El Calvo Explica» (nombre interno provisional, `estudio/explica/`, página /explica): cuerpo y mente, molde de 5
  partes, fondo blanco, voz de Peligro Tropical a 1.3 (a 1.0 el dueño lo sintió lento), silencios recortados a
  0,22 s, ritmo 0.75 y cámara siempre en movimiento; algo cambia cada ≤1,5–2 s. Imágenes por GOOGLE (Together
  descartado: no proponerlo). Cara amable por defecto (canal.GESTO_POR_POSE). Escenas por código (piezas en
  calma/piezas_explica.py y piezas_cuerpo.py); 4 tipos: cuadrícula (explica/escenas.cuadricula, con «4 de 12»),
  ilustración, código, personaje. Primer video «Partes de tu cuerpo que YA NO SIRVEN para nada»: guion en
  explica/guiones/partes_que_no_sirven.txt (+ _dudas.md), escenas en partes_que_no_sirven_escenas.py → ejemplos/
  partes_que_no_sirven.json. Revisor del guion: explica/guion.py. El dueño NO quiere revisar guiones: el guion
  es trabajo de Claude (estructura que enganche); él solo mira la lista de dudas.
- Efectos de sonido por código (calma/sonidos.py: pop, swoosh, rayón, golpe, error, ding; con freno) y fondos de
  lugar pálidos (calma/escenarios.py: cuarto, cuarto_noche, baño, sala, cocina, clase, consultorio, piscina) solo en
  escenas «ilustracion»; los elige el autor (Claude). Activos en El Calvo Explica (efectos_sonido True).
- Segundo video (07-10) «Cómo sería morir en cada planeta»: guion en explica/guiones/morir_en_cada_planeta.txt
  (+ _dudas.md), 12 temas (Luna → planetas → Titán, Plutón, Sol, agujero negro), escenas hechas por el autor
  (Claude) en ejemplos/morir_en_cada_planeta.json; piezas en calma/piezas_espacio.py (planeta {tipo}, medidor,
  termómetro, estirado, alas…), casco y ojos «x» del personaje, fondos del espacio en escenarios.py. Video de
  8:23 enviado sin música (en la nube no hay biblioteca). Voz: 125 COP. El dueño está validando ideas: no
  proponer ni empezar videos nuevos sin que él lo pida.
- Video HÍBRIDO de Peligro Tropical (07-10, pedido del dueño): el guion NO cambia; tras escribirlo,
  estudio/animaciones_codigo.py hace que Claude elija ~25 % de escenas que explican algo (estilo.animaciones_codigo
  = 0.25 vía CAMPOS) y las arme con piezas de calma (sin el Calvo; puede usar la imagen del animal del nivel).
  Esas escenas reusan una imagen anterior (no pagan). Tras la voz se dibujan (assets/animaciones/*.mp4) sobre el
  papel cuadriculado del canal; la EDL les pone el efecto «animacion» (pantalla completa). `deshacer` lo revierte.
  Probado de punta a punta en la nube con imágenes simuladas (36 COP de voz). Receta: en el gancho solo 1 de cada 3
  escenas va en tarjeta de foto (el dueño, molesto: «no abusar de las tarjetas»; las demás a pantalla completa).
- RECETA de Peligro Tropical (07/16-10, spec del dueño): perfil peligro_tropical_v2.json (receta: true) →
  estudio/receta_pt.py (EDL) + render_receta.py (dibujo): niveles altos en negro con humo, veredicto por nivel,
  «PERO ESPERA», destello blanco, subtítulos 1-3 palabras con la activa en amarillo, like ~1:40, suscribirse ~3:00,
  cierre con carrusel y mascota; sonidos por código (sello, campanita, tic_tac, boing, glitch, ding); piezas
  lista/mapa/pin/etiqueta/advertencia para las animaciones híbridas. Falta: mandarle el video de prueba.
- Tracy (16-10): el PC del dueño (16 GB) se trababa: ensamblar usa máximo 2 FFmpeg, 2 hilos y espera memoria.
- COLA DE LA SEMANA (16-10): estudio/cola.py + cola_api.py + página /cola (interfaz/src/paginas/Cola.tsx).
  Pega varios guiones de Tracy (con etiqueta del canal de YouTube) o ideas de Peligro Tropical / El Calvo Explica;
  un solo trabajador los hace UNO A LA VEZ (datos/cola.json; si se cierra Xandart, «haciendo» vuelve a esperar).
  Peligro corre guion→imágenes→video sin parar (respeta el tope; «Dar permiso y seguir» si lo pasa).
  Semana del dueño: lunes un canal Tracy, martes Mentalidad Imparable, miércoles Peligro Tropical, jueves El Calvo.
- LIBERAR ESPACIO (16-10): estudio/limpieza.py + página /espacio (Mis recursos). Seguro: pedazos de render de
  videos terminados, capas 2.5D, clips de Pexels sin uso y el video final guardado dos veces (ahora enlace duro:
  copiar_o_enlazar en las 4 entregas). Con permiso: copias de seguridad viejas (deja la última) y archivos de trabajo
  de videos terminados hace >30 días con su final a salvo en Videos (marca archivado.json). La cola limpia sola.
- El Calvo: ILUSTRACIONES DE GOOGLE (17-10, pedido del dueño): autor.marcar_google marca 1 de cada 5 escenas de la
  historia (preset proporcion_google 0.2); explica/ilustraciones.aplicar las dibuja al hacer el video (referencia del
  personaje, caché por prompt, respeta el tope: si frena, quedan por código) y las pone a pantalla completa.
  ≈120 COP c/u, ~2.000 COP por video de 12 temas. Solo videos nuevos (escenas armadas después de este cambio).
- Primera persona (17-10, error que el dueño vio mucho en Peligro Tropical): en «pov_personaje» Google dibujaba al
  personaje dentro de la escena. Ahora no se manda su foto y el prompt lleva prompts.POV_SIN_PERSONAJE; lo ya pagado
  con la forma vieja se reconoce (Trabajo.antes) y no se vuelve a pedir; al regenerar sale corregida.
- Velocidad de render (17-10, el dueño: «2 horas por video de Peligro Tropical»): el perfil mostró que casi la
  mitad era tira.quitar_fondo_liso (ImageDraw.floodfill en Python) → ahora numpy+cv2.floodFill (mismo recorte); y
  estela (desenfoque de movimiento) se calcula a mitad de tamaño si el rastro es largo. 20 s de video: 98 s → 33 s.
  Su config/render.json está en 60 cps (pedido suyo): bajar a 30 cps lo haría el doble de rápido otra vez.
- El Calvo: ASPECTO NUEVO (17-10, el dueño eligió 2-6 de mis sugerencias: «no solo fondo blanco, no tan
  matachinado»): explica/ambiente.py da a cada tema un lugar (Claude lo elige al hacer el video, gratis; respaldo por
  palabras), partículas (lluvia, nieve, ceniza, polvo, hojas, chispas, burbujas) y luz (día, noche, atardecer,
  tormenta con relámpago); el fondo se pinta UNA vez por tema con Google (preset fondos_google, ≈120 COP c/u,
  caché en fondos/, respeta el tope; si frena, escenario por código). Ilustración/personaje: lugar completo;
  código: «lavado:» (pálido); cuadrícula en blanco. 11 escenarios nuevos en calma/escenarios.py (playa, volcán,
  bosque, selva, océano, desierto, montaña nevada, tormenta, ciudad, parque, cielo). Trazo limpio (trazo.fijar_estilo,
  temblor ×0.3), sombra suave en las piezas (raster.con_sombra) y profundidad (fondo con 40 % del zoom y paneo de
  lado; render.cuadro_en con video.parallax). Todo por banderas en datos["video"]: Hazlo con Calma no cambia.
- LLAMADOS A COMENTAR (17-10, spec del dueño, Peligro Tropical): estudio/llamados.py. 5 llamados fijos en el guion
  de escala (apuesta con 3 opciones —la correcta en posición 1/2/3 según el tema—, experiencia, debate, país,
  cierre «¿Qué animal quieres en la próxima escala?»), máx. 85 palabras; Claude marca líneas con [COMENTA:tipo] y
  Xandart las revisa (máx. 2 correcciones; si falla, guarda y avisa) y QUITA las etiquetas antes de guardar (además
  voz.Grupo.texto y edicion.trozos_subtitulo las limpian). No hay escenas nuevas: esas frases reusan imagen.
  llamados.json + comentario_fijado.txt (respuesta + pregunta del cierre, con emoji; la voz nunca dice emojis);
  la página del video los muestra con «Copiar». Interruptor por canal en /canales (Canal.ajustes.llamados_comentar;
  sin elegir: solo estilo enciclopedia_mascota). CUADRO DE COMENTARIO animado (pedido del dueño): direccion
  «comentarios» → EDL efecto «comentario» (edicion._cuadros_comentario, pop + sfx «tecleo») → render_receta.comentario
  (tarjeta tipo YouTube que se escribe sola con el EJEMPLO que da Claude, corazón al final).
- El Calvo, MENOS PLAN DE CLAUDE (17-10, el dueño iba al 66 % de su límite): escenas y revisión con modelo
  «sonnet» y 2000 de razonamiento (preset modelo_escenas / pensamiento_escenas; el guion sigue con el completo);
  revisión con imagen solo si autor.motivos_revision ve algo (notas, escena pobre, texto chiquito; preset
  revision "si_hace_falta" | "siempre"); cada tema armado queda en revision/tema_XX.json con huella de sus frases y
  se retoma sin llamar a Claude («Volver a armar» lo borra). LLAMADOS en El Calvo: 3 en el guion
  («[COMENTA:tipo|ejemplo] frase»: experiencia en el tema 2, debate a la mitad, cierre en FINAL); guion.leer quita
  la etiqueta (tema["comentarios"], no cuentan para el largo) y la escena lleva «comentario» → calma.render dibuja
  el mismo cuadro de Peligro Tropical (render_receta.comentario) + pop.
- El Calvo, FOTOS REALISTAS (17-10, el dueño: «imágenes muy similares a lo que se necesita», ya advertido del
  riesgo de copiar personajes con dueño y decidió seguir): en las escenas Claude puede poner «foto» (descripción fiel,
  máx. 2 por tema, preset fotos/fotos_por_tema/max_fotos) → ilustraciones.aplicar la pide a Google como fotografía
  realista SIN la referencia del personaje (≈120 COP, con freno) y la pone a pantalla completa; avisa marcar
  contenido sintético al subir. Wikimedia Commons (gratis, con licencia) quedó propuesto, sin hacer.
- (17-10) REVISAR ANTES DE SUBIR: estudio/revision_video.py + POST /api/videos/{slug}/revisar (botón en la página
  del video terminado): hoja de 24 cuadros del final.mp4 con el minuto y lo que dice la voz → Claude (sonnet, con
  Read) lista errores visibles (POV con personaje, textos cortados, imagen que no cuadra, villano antes de tiempo…)
  → render/revision.json. Solo con el botón (gasta plan de Claude). Calvo: 11 POSES NUEVAS en calma/personaje.py
  (brazos_cruzados, saludando, celebrando, saltando, manos_cabeza, tapandose, mano_boca, caminando, cansado,
  empujando, cayendo; «caja_grande» en piezas.personaje), con su cara en canal.GESTO_POR_POSE y en el catálogo.
- REPO PRIVADO (17-10): el dueño lo pidió. OJO: instalar/*.bat y *.ps1 bajan el código de GitHub SIN clave; si se
  vuelve privado dejan de funcionar. Cambiar el instalador para usar una clave guardada en su PC fue bloqueado por
  el clasificador de permisos: decidir con el dueño antes de volverlo privado.
- MAPAS POR CÓDIGO (18-10, spec del dueño «Parte A»): estudio/geo/ (mapa.py = datos Natural Earth 1:50m dominio
  público + banderas flag-icons MIT en geo/recursos, proyección Miller, vistas, dibujo con Pillow; escena.py = escena
  «mapa»: highlight/arrow/zoom_region/compare, colores de sentimiento, país base (COL) con su bandera y borde
  blanco, marcador/HUD (barra AMIGOS vs CON PROBLEMAS, 4 categorías con pop, tarjeta del país con bandera, estado y
  2 líneas de historia, región, anterior), El Calvo por código reaccionando (POSES happy→senalando_contento…)).
  calma.render.cuadro_en dibuja tipo «mapa» (~0,06 s/cuadro). «Modo mapa» por video, APAGADO por defecto:
  El Calvo → video.json modo_mapa/pais_base (checkbox en /explica) → autor añade MAPA_PROMPT, valida países
  (si no existe: ilustración de respaldo + nota) y reglas_mapa (1.ª vez highlight, máx. 4 seguidos). Peligro
  Tropical → Proyecto.modo_mapa (casilla «Modo mapa» al crear) → animaciones_codigo puede devolver «mapa» (sin el
  Calvo); _marcador_mapas calcula el marcador del video. Nunca se pide un mapa o bandera a la IA. Regresión: con el
  modo apagado los cuadros son idénticos (huella comparada).
- (19-10) BUG «fondo solo mientras la voz habla» (El Calvo): si Whisper oía distinto la palabra de un elemento,
  calma.escenas._buscar la hallaba minutos después y corría TODAS las escenas siguientes. Ahora _buscar_cerca
  (ventana de 40 palabras; si no está, entra con el corte) y explica.flujo llama E.asegurar_movimiento (lo
  primero entra con el corte, escena vacía → el Calvo pensando, >2,5 s sin cambio → empujón suave de cámara).
- (19-10) MENOS PLAN DE CLAUDE en TODO Xandart: claude_cli.ejecutar va con --system-prompt corto (SISTEMA_CORTO) y
  --tools (solo las pedidas): «OK» pasó de ~32.000 a ~1.500 tokens; si el CLI no entiende las opciones, vuelve solo a
  la forma de siempre (_LIVIANO). El instalador ya no copia CLAUDE.md (Claude lo leía en CADA pedido: las carpetas de
  proyectos están dentro de la instalación). Esta sesión de chat también se volvió enorme: recomendado abrir otra.
- (19-10) El Calvo usa PEXELS: escenas «foto» llevan {descripcion, busqueda}; explica/fotos_pexels.buscar trae 4
  candidatas por foto, UNA hoja de contacto y UNA revisión de Claude (sonnet) para todas; lo aprobado va gratis
  (créditos en ilustraciones/creditos_pexels.txt), lo demás lo pinta Google. Decisiones en ilustraciones/pexels.json.
- (20-10) IMÁGENES MÁS RÁPIDAS con el límite de Google (el dueño: 121 min y no terminaban): generador.py ya no
  espera cada vez más por imagen (10→90 s, 8 veces); un ritmo compartido (turno/intervalo) sube ×1,5 con cada 429
  (máx. 20 s, pausa fija de 15 s, un solo aviso) y baja ×0,93 con cada éxito. Lo de fondo: pedir más cuota en
  Google Cloud (se le explicó al dueño cómo).
- (20-10) WIKIMEDIA COMMONS (el dueño: «Pexels me falla mucho»): estudio/wikimedia.py (gratis, sin clave; solo
  dominio público/CC0/CC BY/CC BY-SA, fotos ≥800 px) suma candidatas a la MISMA hoja de contacto en Peligro Tropical
  (stock.preparar_stock y por temas) y en El Calvo (explica/fotos_pexels, también sin clave de Pexels). Créditos
  (obligatorios en CC BY) se muestran para copiar en la página del video (PT: «Créditos de las fotos reales»;
  El Calvo: en la página del video). Commons está bloqueado en la nube: probado solo con respuestas simuladas.
- (20-10) GOOGLE CLOUD COMPLETO + LOTES (el dueño: 1 imagen cada 20 s; la clave de API = modo exprés, cupo bajo
  y fijo; la página de cuotas no mostraba nada que subir). imagenes/google_cloud.py: archivo de cuenta de servicio
  (credenciales_google.json en la raíz de la instalación, gitignored; Ajustes → «Subir archivo .json», prueba gratis
  con countTokens; dependencia google-auth). ProveedorVertex usa projects/{p}/locations/global con token; si Google
  lo rechaza (401/403) vuelve a la clave. imagenes/lotes.py: con «Imágenes por lotes» (XANDART_IMAGENES_LOTES=1)
  generador._por_lotes manda TODAS las escenas que faltan en un batchPredictionJob (depósito xandart-lotes-{p},
  borrado a 7 días; global → us-central1), espera (sondeo 60 s, máx. 26 h; reanudable con imagenes/lote.json), guarda
  en imagenes/lote/ y ConLote las entrega a mitad de precio; lo que no llega va normal. Los assets van normal antes.
  NO probado contra Google real (en la nube no hay acceso): faltan la prueba del dueño y confirmar que su modelo
  acepta lotes. El dueño prefiere quedarse en Cloud por sus créditos (~700.000 COP); AI Studio quedó descartado.
- Estrategia del dueño (16-10): foco en los 2 canales Tracy monetizados y Peligro Tropical; El Calvo en pausa.
- Aquí (nube) la voz MiniMax sí funciona; Whisper no baja su modelo: vista previa con voz frase por frase.
- (21-10) BETA CERRADA / SaaS (spec larga del dueño: roles, permisos, aislamiento, lista negra, costos, admin).
  Decisiones del dueño: TODO en su PC por ahora (nada de servidor hasta que él lo apruebe, al final, con proveedor y
  costo); OWNER sigue con su suscripción de Claude (claude_cli), BETA con ANTHROPIC_API_KEY en .env (sin clave: BETA no
  genera guiones, mensaje claro); imágenes siguen en Google con costo real por imagen; Buscanichos/replicar por
  link/clonar voz/TTS solo/modo HD NO existen en este repo: solo permisos y lista negra listos. Orden: A (hecho) →
  R (rediseño React; PRIMERO mostrarle propuesta de paleta, tipografía y pantallas y esperar su visto bueno) →
  B login → C permisos por ruta (todo cerrado por defecto: ruta sin regla = solo OWNER) → D aislamiento y enlaces
  firmados → E catálogo genérico (sin copiar sus prompts) → F permisos por usuario → G lista negra → H costos y
  límites → I admin → J seguridad y entrega.
  PASO A (21-10): migración 0005 (roles ceo→owner, cliente→beta, + admin; usuarios.bloqueado/clave_hash/
  ultima_actividad; visibilidad privado|publico en recursos y canales; tablas permisos_usuario, lista_negra (con
  @codigodelexito22) y costos_llamada). db.preparar hace copia COMPLETA (no solo la base) antes de cualquier
  migración pendiente: Documentos/Xandart copias/<fecha>_antes_de_migrar_0005, anotada en
  datos/ultima_copia_migracion.json. Constantes ROL_OWNER/ROL_ADMIN/ROL_BETA en plataforma/modelos.py.
  PASO R (21-10, rediseño React, acento LIMA con texto oscuro en botones): tokens en interfaz/src/estilos.css (nombres
  viejos --violeta/--rosa/--degradado apuntan al acento; :where() da estilo base a controles sin clase), letras
  Geist + Bricolage Grotesque (@fontsource-variable, dentro del bundle), lucide-react (Icono.tsx traduce los nombres
  de siempre). Menú Home/Create/Assets/Inspire (+ «Tu estudio» solo owner: Cola, Tracy, El Calvo, Calma); barra de
  abajo en celular. Pantallas nuevas: Producir (/producir, /producir/video, /producir/:slug con storyboard grande, % y
  tiempo estimado: EnMarcha.progresoTotal), CanalNuevo (4 pasos; POST /api/v2/canales; el estilo y la voz del canal
  ahora se usan: consultas.estilo_del_canal / voz_del_canal), PersonajeDetalle (asistente que ya existía sin pantalla),
  Estilos, Miniaturas, Media; Estados.tsx (vacío, esqueleto, girando, error) y Costo.tsx junto a cada botón que gasta.
  Para revisar a ojo: scratchpad demo/lanzar.py (puerto 8099, imágenes simuladas) + capturas con Playwright.
  BLOQUE 1 (21-10, hecho): estudio/avisos.py («tu video está listo / no se pudo terminar» en la app y por correo:
  pipeline.lanzar llama avisos.al_terminar; un video está listo si dejó un .mp4 nuevo en Videos/Xandart; campana en la
  barra + mensaje flotante; GET/POST /api/v2/avisos); aviso al abrir de la copia de seguridad antes de migrar
  (avisos.respaldo lee datos/ultima_copia_migracion.json; si la copia falla db.preparar lo anota y NO migra);
  «Reportar problema» en el cajón de Ayuda (POST /api/v2/reportes → datos/reportes/*.json + correo, sin claves);
  ayuda corta por pantalla (componentes/Ayuda.tsx); historial de créditos /creditos (con el nombre de cada acción);
  revisión del guion con selector de duración (POST /api/videos/{slug}/guion {minutos}) y costo del video completo;
  «Reintentar esta escena» en las escenas sin imagen. Los cajones y mensajes flotantes van con createPortal (la barra
  tiene backdrop-filter y atrapa a los fixed).
  (22-10) COPIA LIVIANA (pedido del dueño: sus videos viejos ya están en YouTube; lo único que importa es que
  El Calvo, Peligro Tropical y Tracy sigan saliendo igual): antes de migrar, copias.hacer_copia(liviano=True) =
  base de datos, config, estilos, canales, perfiles, catálogo, datos/espacios (sin videos ni audios), módulos
  tracy/explica/calma, biblioteca, .env, credenciales_google.json y datos/*.json. Sin proyectos. Simulada: 33 MB.
  db.PREPARANDO + avisos.respaldo dicen «copiando/actualizando» (banner con giro y recarga al terminar); antes, con la
  copia completa, la página quedaba sin canales (captura del dueño). Inicio ya no ofrece «crea tu canal» si fallan.
  PRIVADO DEL DUEÑO (22-10): api.DEL_DUENO (formatos y fórmulas escala_peligro/paradoja_documental, plantilla
  escala_2x3) solo para OWNER (marcados «estudio»: grupo «Tu estudio» del selector); api.MODULOS_DEL_DUENO (Tracy,
  El Calvo, Calma, Cola) solo por GET /api/v2/estudio (403 a otros); sus pantallas van con React.lazy (fuera del
  archivo principal). tests/test_privado.py lo comprueba (BETA por dependency_overrides). Elegir en Canal uno con
  página propia (El Calvo → /explica, sin estilo → /tracy) lleva a esa página; Peligro Tropical carga su formato.
  voz_del_canal ignora «voz_principal» (la de proveedores.json sigue mandando, igual que antes).
  /espacio muestra «Tus proyectos, del más pesado al más liviano» (limpieza.proyectos_por_peso): SOLO mirar; se borra
  únicamente lo que el dueño diga.
  PASO B (22-10, LOGIN, aprobado con estas decisiones del dueño: él también entra con contraseña en su PC con
  «Recordarme» 30 días; las cuentas beta las crea él a mano con contraseña temporal, sin registro abierto):
  plataforma/acceso.py = contraseñas scrypt con sal (stdlib; «temporal:» delante = obliga a cambiarla), galleta
  firmada xandart_sesion (HttpOnly, SameSite=Strict; secreto en datos/secreto_sesion.key, nunca en el repo; lleva
  huella de la contraseña → cambiarla cierra las demás sesiones), 5 fallos = 15 min de espera, y PuertaDeEntrada
  (middleware por FUERA de EspacioDeLaPeticion): sin sesión las API dan 401 y las páginas viejas (/, /admin,
  /archivos) llevan a /app/entrar?volver=…; libres solo /app (archivos de la página), /web, /api/version,
  /api/v2/sesion|entrar|salir|crear-clave-dueno, /api/apagar SIN cabecera Origin (lo usa el acceso directo) y,
  mientras db.PREPARANDO, estado-local y respaldo. Petición con Origin de otro sitio que cambia algo → 403.
  plataforma/api_acceso.py: /sesion, /entrar, /salir, /crear-clave-dueno (primera vez, solo desde_este_pc: cliente
  127.0.0.1 y sin cabeceras de túnel/proxy), /cambiar-clave, /admin/usuarios (crear beta con temporal + bienvenida,
  bloqueo, clave-temporal nueva; la cuenta owner no se toca desde ahí). api.usuario_actual ya lee la sesión
  (acceso.conectado()); EspacioDeLaPeticion: owner → espacio de la instalación (igual que antes), otros → el suyo.
  SIN migración nueva (si hiciera falta una, db.preparar ya usa la copia liviana). Recuperar la contraseña del dueño
  sin correo: estudio/restablecer_clave.py (la pide 2 veces en la ventana negra) vía instalar/«Restablecer mi
  contrasena.bat» + acceso directo «Restablecer mi contraseña de Xandart Nueva» en el menú Inicio → Xandart.
  Los trabajos NO dependen de la sesión: cola_api.recuperar_al_abrir() sigue la cola al abrir Xandart (antes
  esperaba a que la página pidiera /api/cola). Pruebas: conftest.entrar_como_dueno (acceso.EN_PRUEBAS, solo por
  código, nunca por .env) deja las pruebas de siempre como el dueño; tests/test_acceso.py prueba la puerta real.
  Interfaz: paginas/Entrar.tsx (crear / entrar / cambiar temporal), MiCuenta.tsx (/cuenta: cambiar contraseña y
  salir; /cuentas: cuentas beta, la temporal se muestra UNA vez con «Copiar»); api.ts lanza «xandart:sin-sesion»
  ante un 401 y App vuelve a la pantalla de entrar. Correo de avisos con 127.0.0.1 (no localhost: otra galleta).
  PASO C (23-10, PERMISOS POR RUTA): plataforma/permisos_rutas.py = REGLAS (métodos, plantilla, nivel libre|sesion|
  admin|owner; gana la primera); SIN regla = solo owner. PRIVADAS_APP: los archivos de la página de Tracy/Calma/
  Explica/Cola (/app/assets/<Nombre>-*.js) solo al dueño. acceso.PuertaDeEntrada: «libre» sale de estas reglas; con
  sesión, si el rol no alcanza → 403 «Esto no está disponible en tu cuenta.» (páginas → /app/). /api/apagar libre
  solo sin galleta, sin Origin y desde este PC (el acceso directo). Beta: cuenta, créditos, canales, recursos,
  personajes, avisos, reportes, videos (crear/guion/imágenes/video/escenas/editor/animar/short, /archivos).
  Solo owner: módulos privados, miniaturas de hoy (escala 2x3 y texto+retrato; la genérica llega en Bloque 2),
  revisar (gasta su plan de Claude), Ajustes (/), claves, Google, biblioteca, espacio, copias, importar, estado-local
  y respaldo. Admin: /admin y /api/v2/admin/* (menos copias). tests/test_permisos_rutas.py falla si una dirección
  nueva no tiene regla. Interfaz: api.conectado/esDueno/esAdmin esconden menú y botones (Ajustes, Liberar espacio,
  Miniatura, Revisar, Media muestra «pronto» a beta). FALTA Paso D: las rutas de videos aún usan la carpeta de siempre.
## Pendiente
- Preguntas sin responder del dueño: ¿en qué canal notó la voz lenta? (Peligro Tropical está en 1.3 en
  config/proveedores.json; Tracy en 1.0 por pedido suyo). ¿En qué momento sale «la tira de animales» sin sentido?
- Propuesto y sin empezar: subtítulos palabra por palabra; revisión automática del video con Claude antes de
  subir; título/descripción/capítulos; volver PRIVADO el repositorio (recomendado ya); asistente para crear canales;
  luz y textura (grano, destellos, color) solo si él lo pide tras ver los videos; estilo simple de Tracy.
- Canal nuevo «Hazlo con Calma»: el dueño mandará capturas y guiones de la competencia; analizar escena por escena
  y sacar la estructura del guion (sin copiar textos) antes de construir.
- Editor (música, mover, cortar): en pausa por pedido del dueño; backend hecho, sin interfaz.
- Prueba inestable: 1 de 3 corridas completas falló una prueba (no identificada) el 04-10; el dueño dijo no perseguirla aún.
- El Calvo Explica: (17-10) /explica tiene «Hacer el video completo» (guion→escenas→video sin parar, explica.api.hacer_todo, lo mismo que usa la cola) y «Hacer todo lo que falta» en cada video. Falta música
  tranquila (biblioteca), miniatura (personaje señalando la muñeca + «¿TÚ LO TIENES?») y título. Muestras de
  Google sin generar (botón en /explica).
