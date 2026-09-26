# Especificación · Estudio de producción dentro de Buscanichos

Documento para Claude Code. Describe cómo agregar a Buscanichos un módulo completo de producción de video: de un outlier o una idea a un video largo ya editado, con línea de tiempo editable, animación opcional por escena y un "Director de edición" con IA. Reemplaza el desarrollo anterior de Xandart, que se rehace desde cero aquí.

Léelo completo antes de escribir código. Si algo contradice lo que ya existe en Buscanichos, pregunta antes de cambiar lo existente.

---

## 0. Principios que no se negocian

1. **Usuario único, uso local.** Por ahora la herramienta es solo para el dueño. Nada de créditos, planes, login con Google ni multiusuario. Se diseña limpio para poder agregarlo después, pero no se construye ahora.
2. **La IA decide, el motor ejecuta.** Ningún modelo de IA renderiza ni toca archivos de video directamente. La IA produce decisiones en JSON (escenas, línea de tiempo, efectos). Un motor determinista (FFmpeg) las ejecuta. Lo que el usuario ve en la línea de tiempo es exactamente lo que se renderiza.
3. **Presupuesto duro por video.** Cada video debe costar entre **15.000 y 20.000 pesos colombianos** en llamadas a APIs. El sistema estima el costo antes de empezar, lleva la cuenta en tiempo real y nunca pasa del tope sin permiso explícito (ver sección 2).
4. **Tiempos reales, no estimados.** La duración de cada escena sale del audio real de la voz mediante alineación forzada del texto conocido contra el audio (sección 5.5), nunca de estimaciones del modelo de lenguaje.
5. **Todo reanudable.** Cada paso guarda su resultado en disco. Si algo falla o se corta, se reanuda desde el último paso completo sin volver a pagar lo ya generado.
6. **Cada decisión de la IA lleva su razón.** Toda decisión de edición guarda un campo `razon` en lenguaje simple, visible en la interfaz, para que el usuario la acepte o la deshaga.

---

## 1. Arquitectura general

```
Buscanichos (ya existe)
  └─ Outlier / canal de referencia / idea
        │
        ▼
[1] Estratega ── Niche Bending: separa formato y mercado, propone ideas
        ▼
[2] Guionista ── guion completo + división en escenas (escenas.json v2)
        ▼
[3] Director visual ── prompt de imagen por escena, bloqueo de personaje, reutilización
        ▼
[4] Generador de assets ── imágenes, recortes sin fondo, composiciones (tira de niveles)
        ▼
[5] Voz ── TTS de la narración completa
        ▼
[6] Alineador ── alineación forzada del texto contra el audio: tiempo real de cada escena
        ▼
[7] Director de edición ── construye la línea de tiempo (edl.json) con efectos, sonido y música
        ▼
[8] Validador de reglas ── revisa la EDL con reglas fijas (sin IA) y la corrige
        ▼
[9] Motor de render ── FFmpeg ejecuta la EDL (vista previa en baja resolución)
        ▼
[10] Revisor ── la IA mira fotogramas del render y propone correcciones (máx. 2 vueltas)
        ▼
[11] Editor (interfaz) ── línea de tiempo editable + edición por chat + botón "Animar"
        ▼
[12] Export final en alta calidad
```

Cada bloque es un módulo independiente con entrada y salida en archivos JSON dentro de la carpeta del proyecto. Así cada uno se puede probar, repetir o reemplazar por separado.

### Estructura de carpetas por proyecto

```
proyectos/<slug-del-video>/
├── proyecto.json          (estado, configuración, presupuesto, historial de costos)
├── estrategia.json        (salida del Estratega)
├── guion.md               (narración legible)
├── escenas.json           (contrato principal, ver sección 3)
├── assets/                (personaje base, tira de niveles, elementos reutilizables)
├── imagenes/              (imágenes por escena)
├── imagenes/sin_fondo/
├── audio/voz.wav
├── audio/alineacion.json  (salida del Alineador)
├── edl.json               (línea de tiempo, ver sección 3)
├── render/preview.mp4
├── render/final.mp4
└── logs/costos.jsonl      (una línea por cada llamada pagada)
```

---

## 2. Presupuesto por video

### Configuración

Todo en `config/costos.json`, editable sin tocar código:

```json
{
  "trm_cop_por_usd": 3100,
  "presupuesto_objetivo_cop": 15000,
  "presupuesto_maximo_cop": 20000,
  "precios_usd": {
    "claude_input_por_millon_tokens": null,
    "claude_output_por_millon_tokens": null,
    "imagen_por_unidad": 0.02,
    "tts_por_1000_caracteres": 0.004,
    "animacion_por_segundo": null
  },
  "ultima_revision_precios": "AAAA-MM-DD"
}
```

- La TRM rondaba los 3.100 pesos en septiembre de 2026; debe poder actualizarse a mano en la configuración.
- Los precios marcados `null` deben llenarse con los valores actuales de cada proveedor antes de la primera corrida. Verifícalos en la documentación oficial de cada proveedor; no los inventes.
- Valores de referencia medidos por el dueño en su pipeline anterior (úsalos solo como punto de partida y confírmalos): imagen con la API de Gemini alrededor de 0,02 USD; imagen vía Together (flash-image-2.5) 0,0403 USD; TTS MiniMax alrededor de 0,01 USD por bloque de 2.500 caracteres; brief con Claude 0,05 USD; guion con Claude alrededor de 0,20 USD por lote de 30 escenas.

Con una TRM de 3.100, el rango de 15.000 a 20.000 pesos equivale a unos **4,8 a 6,5 USD por video**.

### Reparto orientativo

El ejemplo de abajo es para un video de 15 a 18 minutos (~300 escenas). **El estimador no debe asumir esa cifra:** calcula todo a partir de la duración objetivo del video y del estilo elegido (escenas = duración en segundos ÷ segundos promedio por escena del perfil de edición; imágenes nuevas = escenas × proporción de imágenes únicas del estilo). Los outliers del nicho de animales peligrosos duran de 8 a 11 minutos, así que un video típico de ese canal debería necesitar aproximadamente la mitad de escenas, imágenes y tokens que este ejemplo.

| Bloque | Presupuesto aproximado |
|---|---|
| Estratega + Guionista + Director visual (Claude) | 0,8 a 1,2 USD |
| Director de edición + Revisor (Claude, texto y visión) | 0,6 a 1,0 USD |
| Voz (TTS) | 0,05 a 0,15 USD |
| Imágenes | 2,5 a 3,5 USD |
| Alineador, FFmpeg, música y efectos locales | 0 |
| Animación | 0 por defecto (ver abajo) |

A 0,02 USD por imagen, eso permite unas **125 a 175 imágenes nuevas por video**. Con escenas cada 3 a 4 segundos habrá más escenas que imágenes: la diferencia se cubre con reutilización inteligente (sección 5.3).

### Reglas del presupuesto

1. **Estimación previa obligatoria.** Antes de generar nada, el sistema calcula el costo esperado de todo el video y lo muestra en pesos y en dólares. Si supera el objetivo, propone ajustes automáticos (más reutilización, menos escenas únicas) antes de pedir permiso.
2. **Libro de costos.** Cada llamada pagada se registra en `logs/costos.jsonl` con: módulo, proveedor, modelo, unidades, costo en USD y en COP, fecha y hora.
3. **Contador visible en la interfaz**, en pesos, durante toda la producción.
4. **Degradación automática** cuando el gasto proyectado supera el objetivo, en este orden: aumentar la reutilización de imágenes de fondo gris (recortes), bajar las escenas de tipo "escena completa" a "recorte sobre papel", reducir las vueltas del Revisor a 1.
5. **Mejora automática** cuando el gasto proyectado queda claramente por debajo del objetivo (por ejemplo, en videos de 8 a 11 minutos): usar ese margen para subir la proporción de imágenes únicas donde más se nota la calidad, en este orden: el gancho (primeros 30 a 60 segundos), las escenas con intención `revelacion` o `amenaza`, y las transiciones de sección. Nunca se usa el margen para animar sin confirmación, y la proyección con la mejora aplicada no puede pasar del objetivo.
6. **Freno duro** al llegar al máximo (20.000 pesos): el sistema se pausa y pregunta. Nunca sigue gastando solo.
7. **La animación nunca entra en el presupuesto base.** Es un gasto opcional que el usuario activa escena por escena, viendo el costo antes de confirmar.

---

## 3. Contratos de datos

Estos archivos son la columna vertebral del sistema. Valídalos con un esquema (por ejemplo, Pydantic o JSON Schema) en cada entrada y salida de módulo.

### 3.1 `escenas.json` (versión 2)

Se basa en el archivo real del proyecto de alacranes (que debe usarse como caso de prueba, ver fase 0), con tres cambios: la intención de cada escena, los efectos estructurados en lugar de texto libre, y los tiempos reales.

```json
{
  "video": "Del alacrán que solo arde al que te manda directo a urgencias",
  "canal": "animales-peligrosos",
  "idioma": "es",
  "relacion_aspecto": "16:9",
  "assets": [
    { "id": "mascota_base", "tipo": "personaje", "prompt": "...", "archivo": "assets/mascota_base.png", "quitar_fondo": true },
    { "id": "tira_1", "tipo": "animal_fondo_gris", "prompt": "...", "archivo": "assets/tira_1.png", "quitar_fondo": true }
  ],
  "escenas": [
    {
      "id": 17,
      "seccion": "Gancho",
      "narracion": "Pero aquí viene el primer giro:",
      "intencion": "giro",
      "intensidad": 4,
      "tiempo": { "estimado_inicio": 41.2, "estimado_duracion": 2.5, "real_inicio": null, "real_fin": null },
      "visual": {
        "accion": "generar",
        "tipo": "diagrama_fondo_blanco",
        "prompt": "...",
        "archivo": "imagenes/escena_017.png",
        "quitar_fondo": true,
        "referencias": [],
        "reusar_de": null
      },
      "efectos_sugeridos": [
        { "efecto": "corte_seco" },
        { "efecto": "zoom_golpe", "intensidad": 0.08 },
        { "efecto": "sfx", "sonido": "golpe_grave" }
      ]
    }
  ]
}
```

- `intencion`: uno de la lista cerrada de la sección 4.1.
- `intensidad`: de 1 a 5, alimenta la curva emocional.
- `efectos_sugeridos`: sugerencias del Guionista o del Director visual. El Director de edición tiene la última palabra.
- `tiempo.real_*`: lo llena el Alineador (sección 5.5).

### 3.2 `edl.json` (línea de tiempo)

La línea de tiempo completa. Es lo que el editor muestra y lo que el motor renderiza.

```json
{
  "version": 3,
  "duracion_total": 1062.4,
  "pistas": {
    "fondo":     [ { "id": "f1", "inicio": 0, "fin": 1062.4, "tipo": "textura", "archivo": "assets/papel_arrugado.png" } ],
    "escenas":   [ { "id": "c17", "escena": 17, "inicio": 41.2, "fin": 43.9, "archivo": "imagenes/sin_fondo/escena_017.png",
                     "modo": "recorte_sobre_papel", "movimiento": { "tipo": "zoom_lento", "de": 1.0, "a": 1.04 },
                     "transicion_entrada": "corte", "razon": "Giro del gancho: corte seco para marcar el cambio" } ],
    "elementos": [ { "id": "e5", "inicio": 41.3, "fin": 43.9, "tipo": "icono", "valor": "advertencia", "posicion": "arriba_izquierda" } ],
    "textos":    [ { "id": "t2", "inicio": 41.2, "fin": 43.0, "texto": "EL PRIMER GIRO", "estilo": "titulo_contorno" } ],
    "subtitulos":[ { "inicio": 41.2, "fin": 43.9, "texto": "Pero aquí viene el primer giro:" } ],
    "voz":       [ { "inicio": 0, "archivo": "audio/voz.wav" } ],
    "musica":    [ { "id": "m2", "inicio": 38.0, "fin": 120.0, "archivo": "musica/tension_02.mp3", "volumen": 0.18, "ducking": true } ],
    "sfx":       [ { "id": "s9", "inicio": 41.2, "archivo": "sfx/golpe_grave.wav", "volumen": 0.7 } ]
  },
  "historial": [ { "version": 2, "autor": "director_edicion", "cambio": "...", "razon": "..." } ]
}
```

- Toda modificación (del Director, del Revisor o del usuario) crea una nueva versión y queda en `historial`, para poder deshacer.
- Cada elemento tiene un `id` estable para poder editarlo desde el chat.

### 3.3 `perfil_canal.json`

Configuración guardada por canal, para no repetirla en cada video: idioma, voz, personaje y su bloqueo (descripción literal que se copia igual en cada prompt), bloque de estilo visual, tipos de escena permitidos, paleta, tipografías, efectos preferidos y prohibidos, rango de duración del video, perfil de edición (3.4) y biblioteca de música por estado de ánimo.

### 3.4 `perfil_edicion.json`

El "ritmo" de edición de un canal, aprendido de videos de referencia (sección 4.5):

```json
{
  "fuente": ["https://www.youtube.com/watch?v=..."],
  "segundos_promedio_por_imagen": 3.2,
  "interrupcion_de_patron_cada_seg": 7,
  "efectos_por_minuto": 9,
  "sfx_por_minuto": 6,
  "cambios_de_musica": "por_seccion",
  "texto_en_pantalla_por_minuto": 3,
  "densidad_primeros_30s": "alta",
  "notas": "Revelaciones con fondo rojo y calaveras; mascota reacciona en cada nivel"
}
```

---

## 4. Director de edición (módulo central)

Es un agente con Claude que recibe `escenas.json` con tiempos reales, `perfil_canal.json` y `perfil_edicion.json`, y produce `edl.json`. Trabaja en tres pasadas para mantener la calidad y el costo controlados:

1. **Pasada de estructura:** revisa y corrige la `intencion` e `intensidad` de cada escena, arma la curva emocional del video y decide las secciones musicales.
2. **Pasada de edición:** recorre el video por bloques de unos 60 segundos y asigna movimiento, transiciones, textos, elementos y efectos de sonido, aplicando la gramática (4.2) y el perfil de edición.
3. **Pasada de música:** asigna pistas por sección según el estado de ánimo y marca los cambios en las transiciones de sección.

Luego el Validador (4.3) revisa el resultado sin IA.

### 4.1 Intenciones (lista cerrada)

`gancho`, `pregunta_al_espectador`, `giro`, `revelacion`, `dato_impactante`, `explicacion`, `comparacion`, `tension_creciente`, `amenaza`, `alivio`, `humor`, `consejo_practico`, `advertencia`, `llamado_accion`, `transicion_de_seccion`, `cierre`.

### 4.2 Gramática de edición (intención → decisiones)

Punto de partida; el perfil de edición de cada canal puede ajustarla.

| Intención | Movimiento | Transición | Sonido | Otros |
|---|---|---|---|---|
| gancho | zoom lento de entrada | corte | subida de tensión suave | ritmo más rápido que el resto |
| pregunta_al_espectador | ninguno o muy leve | corte | pausa corta en la música | mascota señalando a cámara |
| giro | zoom golpe (4 a 8 %) | corte seco | golpe grave | texto corto en pantalla |
| revelacion | acercamiento | destello (rojo si es amenaza) | golpe grave + silencio breve | quitar pixelado si lo había |
| dato_impactante | zoom lento | corte | "pop" suave | número o dato en grande |
| explicacion | paneo lento | corte o fundido corto | ninguno | flechas sobre el detalle |
| comparacion | ninguno | corte | ninguno | dos imágenes lado a lado |
| tension_creciente | zoom lento continuo | corte | latido o zumbido creciente | fondo que se oscurece |
| amenaza | acercamiento lento | corte | zumbido grave | ícono ⚠️, tinte rojo |
| alivio | alejamiento lento | fundido corto | música se relaja | mascota aliviada |
| humor | leve rebote | corte | efecto cómico corto | reacción exagerada de mascota |
| consejo_practico | ninguno | corte | "pop" suave | texto con el consejo |
| advertencia | zoom golpe leve | corte | alerta corta | ícono ⚠️ |
| llamado_accion | ninguno | corte | ninguno | mascota con pulgar arriba o señalando |
| transicion_de_seccion | según la sección | barrido o deslizamiento | cambio de música | tira de niveles si aplica |
| cierre | alejamiento lento | fundido | música final | resumen visual |

**Regla general de movimiento:** los zooms y paneos continuos son siempre lentos y sutiles, con un máximo del 5 % de escala por escena. Solo `zoom_golpe` puede ser rápido, y nunca en dos escenas seguidas.

### 4.3 Validador de reglas (sin IA, determinista)

Código normal que revisa la EDL y corrige o marca problemas. Barato, rápido e infalible:

- Ninguna imagen permanece más de 4,5 segundos sin un **cambio visual real**: corte a otra imagen, aparición de un elemento nuevo (flecha, ícono, texto, recorte) o cambio de encuadre. El movimiento continuo (zoom o paneo lento) **no cuenta** como cambio.
- Hay una interrupción de patrón al menos cada `interrupcion_de_patron_cada_seg` del perfil.
- Nunca el mismo efecto de sonido o `zoom_golpe` en dos escenas consecutivas.
- La misma imagen no se repite dentro de una ventana de 30 segundos (salvo reusos intencionales marcados).
- Los primeros 30 segundos cumplen la densidad "alta" del perfil.
- Los textos en pantalla no se superponen con la zona de subtítulos.
- La música baja automáticamente (ducking) mientras suena la voz.
- Toda la duración de la voz está cubierta por escenas, sin huecos negros.
- La intensidad media de la última cuarta parte del video no es menor que la de la primera mitad (escalada).

Si una regla no se puede corregir sola, se marca para el Revisor o para el usuario.

### 4.4 Revisor visual (después del render de vista previa)

- **No envíes fotogramas sueltos.** En un video de 18 minutos, un fotograma cada 2 segundos más los cambios de escena suman unas 840 imágenes por vuelta; a unos 1.200 tokens de entrada cada una en 720p, una sola vuelta rondaría el millón de tokens y se comería buena parte del presupuesto.
- En su lugar, arma **hojas de contacto**: grillas de 3×3 fotogramas reducidos en una sola imagen, cada uno con su número de escena, su tiempo y el texto narrado debajo. Un fotograma por escena (tomado en el punto medio de la escena) más un fotograma extra en escenas de más de 4 segundos. Esto baja el costo unas 8 a 10 veces sin perder lo que el Revisor necesita ver.
- Si una hoja de contacto muestra un posible problema, el Revisor puede pedir ese fotograma puntual en resolución completa.
- Antes de cada vuelta, el sistema estima el costo del Revisor y lo descuenta del presupuesto; si no alcanza, se salta la vuelta y lo avisa.
- Claude con visión revisa las hojas por bloques: imagen que no coincide con la narración, momentos visualmente muertos, textos ilegibles o tapados, personaje inconsistente, errores visuales evidentes (animal deforme, letras basura en la imagen).
- Devuelve una lista de correcciones como cambios a la EDL o solicitudes de regenerar una imagen puntual.
- **Máximo 2 vueltas**, y solo si el presupuesto lo permite. Regenerar imágenes en esta etapa descuenta del presupuesto de imágenes.

### 4.5 Aprender el ritmo de un video de referencia

El usuario pega el link de un video que funciona (por ejemplo, un outlier encontrado en Buscanichos). El sistema:

1. Obtiene la transcripción y la duración.
2. Analiza el video con un modelo que entienda video. Opciones reales, en este orden:
   - **Gemini analizando la URL de YouTube**, si la API del proveedor lo permite en ese momento (verifícalo en su documentación).
   - **Paso manual:** el dueño hace el análisis en el chat de Claude, donde tiene NexLev conectado, y pega el resultado en el Estudio. El sistema debe aceptar ese texto o JSON pegado y convertirlo en `perfil_edicion.json`.
   - NexLev **no** está disponible desde el código local de Buscanichos (está conectado a Claude en el chat, no al servidor); no intentes llamarlo salvo que el dueño confirme que tiene una API propia configurada.
   No descargues ni guardes el video de terceros.
3. Extrae métricas: segundos promedio por imagen, interrupciones por minuto, uso de texto en pantalla, momentos de cambio de música, tipos de escena, estructura de secciones y cómo presenta cada nivel o giro.
4. Guarda el resultado en `perfil_edicion.json` del canal, mostrando al usuario un resumen para aprobarlo.

### 4.6 Edición por chat

En el editor hay un chat. El usuario escribe cosas como "haz más intenso el nivel 3", "el inicio está lento" o "quita el sonido de golpe de la escena 40". El agente:

1. Identifica las escenas y elementos afectados por `id`.
2. Propone un parche a la EDL mostrando qué cambia y por qué.
3. Aplica el parche al aceptar, pasa el Validador y re-renderiza solo el tramo afectado en la vista previa.

---

## 5. Módulos de generación

### 5.1 Estratega y Guionista

- El Estratega aplica el método de Niche Bending (la skill `niche-bending` del dueño describe el proceso) y deja `estrategia.json` con formato, mercado, ángulo, videos de referencia e ideas de título.
- El Guionista escribe el guion completo y lo divide en escenas de 3 a 4 segundos de narración, **cada escena cerrando una idea o frase completa**.
- **Los números siempre en palabras** ("catorce centímetros", "veinte mil"), porque el TTS lee mal los dígitos con separadores.
- Longitud objetivo configurable por canal. Referencia: los outliers analizados del nicho de animales peligrosos duran de 8 a 11 minutos.
- En temas de salud, el guion no da dosis ni tratamientos; solo orienta a buscar atención médica. Marca para revisión humana cualquier dato médico.

### 5.2 Director visual

- Asigna a cada escena su tipo visual y su prompt estructurado, con el bloque de estilo del canal y el bloqueo de personaje copiado literal.
- Los tipos de escena **no son fijos**: los define el estilo de video elegido (sección 12). Por ejemplo, el estilo "Enciclopedia + mascota" del proyecto de alacranes usa `animal_fondo_gris`, `mascota_fondo_gris`, `diagrama_fondo_blanco`, `escena_cartoon_completa`, `escena_mixta` y `amenaza_cinematografica`; el estilo "Stickman 2D" usa otros.
- Rota ángulos de cámara para no repetir el mismo encuadre en escenas seguidas.
- Si la narración de una escena menciona varios objetos visuales distintos, puede dividirla en sub-imágenes repartiendo la duración.
- Los prompts nunca piden texto dentro de la imagen; los textos se ponen en la EDL.

### 5.3 Reutilización inteligente (clave para el presupuesto)

Como habrá más escenas que imágenes nuevas, el Director visual decide qué escenas reutilizan una imagen existente, variando la presentación para que no se note:

- Otro encuadre del mismo recorte (plano general, acercamiento a la cabeza, al aguijón).
- Otro movimiento (zoom de entrada frente a alejamiento).
- Combinaciones: recorte del animal + recorte de la mascota reaccionando, sobre el papel.
- Elementos superpuestos (flechas, ⚠️, círculo rojo) que cambian el sentido de la imagen.
- Los assets reutilizables (tira de niveles, personaje en poses frecuentes) se generan una sola vez por canal y se guardan para videos futuros, lo que abarata cada video siguiente.

### 5.4 Generador de assets

- Genera con el proveedor de imágenes configurado (el dueño logró buena consistencia de personaje con la API de imágenes de Gemini, familia Nano Banana). El proveedor y el modelo van en configuración.
- Personaje: se genera primero la imagen base y se pasa como referencia en todas las escenas donde aparece.
- Quita fondos con una herramienta local (por ejemplo, `rembg`). Personajes de piel blanca se generan sobre gris, nunca sobre blanco.
- Control de calidad por imagen (letras en la imagen, personaje distinto, anatomía rota) con reintento máximo de 2 veces por escena, descontando del presupuesto.
- Composiciones programáticas (por ejemplo, la tira de niveles) se arman con código (Pillow), no con el generador.
- Procesa en paralelo con un límite configurable y reanuda si se interrumpe.

### 5.5 Voz y alineación

- TTS del guion completo con la voz configurada del canal (el dueño usaba MiniMax y quiere poder usar voces clonadas).
- **Primero, marcas del propio TTS:** si el proveedor de voz devuelve marcas de tiempo por palabra o por carácter, úsalas directamente.
- **Si no, alineación forzada:** como el texto exacto ya se conoce, se alinea ese texto contra el audio (por ejemplo, con WhisperX o stable-ts en modo de alineación), en lugar de transcribir y luego emparejar frases. Es más preciso y no falla cuando el reconocimiento escucha mal una palabra.
- Con las marcas por palabra se llenan `tiempo.real_inicio` y `real_fin` de cada escena.
- Si una escena no se puede alinear con confianza, se marca y se usa la estimación proporcional solo para esa escena.

---

## 6. Motor de render

- FFmpeg, invocado desde código a partir de `edl.json`. Puede usarse una capa de composición (por ejemplo, MoviePy o filtros complejos de FFmpeg) si simplifica, pero la EDL es la única fuente de verdad.
- **Catálogo de efectos con nombre fijo**, cada uno con parámetros y valores por defecto: `zoom_lento`, `alejamiento_lento`, `paneo_lento`, `zoom_golpe`, `corte`, `corte_seco`, `fundido_corto`, `destello`, `destello_rojo`, `pixelar`, `revelar_pixelado`, `entrada_rebote`, `temblor_leve`, `tinte_rojo`, `oscurecer_fondo`, `tira_deslizar_a_nivel`, `lado_a_lado`, `flecha`, `circulo_rojo`, `icono_advertencia`.
- Modos de escena: `recorte_sobre_papel` (imagen sin fondo sobre la textura de papel) y `recuadro_sobre_papel` (imagen completa enmarcada con borde, sobre el papel).
- Subtítulos quemados con el estilo del canal (grandes, blancos con contorno negro, abajo al centro) y también exportables como SRT.
- Mezcla de audio: voz al frente, música con ducking automático, efectos de sonido a su volumen de la EDL, normalización final de sonoridad.
- **Vista previa** rápida en 720p para el editor y el Revisor; **export final** en 1080p o más, en segundo plano.
- **Render por tramos solo para el video:** al cambiar una parte, se re-renderiza únicamente el tramo de video afectado, cortando siempre en cortes secos entre escenas, y se vuelve a unir.
- **El audio se mezcla siempre completo:** la música cruza varios tramos y tiene ducking, así que mezclar el audio por pedazos produce saltos audibles en las uniones. Cada render (vista previa o final) vuelve a mezclar voz, música y efectos de todo el video y lo une al video.

### Música y efectos de sonido

- Biblioteca local organizada por estado de ánimo (`tension`, `misterio`, `epico`, `alivio`, `curiosidad`, `final`) y efectos por tipo (`golpe_grave`, `pop`, `zumbido`, `latido`, `subida_tension`, `alerta`, `comico`).
- Solo material con licencia que permita su uso en YouTube (por ejemplo, la Biblioteca de audio de YouTube). Guarda la fuente y la licencia de cada archivo en un índice.
- **La biblioteca se llena a mano:** la Biblioteca de audio de YouTube no tiene API, así que no intentes automatizar la descarga. Construye solo una pantalla o carpeta de importación donde el dueño suelta los archivos y les asigna estado de ánimo o tipo.

---

## 7. Editor (interfaz)

Integrado en la interfaz actual de Buscanichos como una sección nueva ("Estudio"), respetando su estilo visual.

- **Storyboard en vivo** durante la producción: grilla de miniaturas por escena que se van marcando a medida que se completan.
- **Línea de tiempo con pistas:** escenas, elementos, textos, subtítulos, voz (forma de onda), música y efectos de sonido.
- **Por escena:** alargar o acortar arrastrando, cambiar la imagen por otra del proyecto, regenerar con una instrucción escrita ("que el alacrán mire a cámara"), cambiar movimiento y transición, activar o quitar efectos.
- **Razones visibles:** al seleccionar cualquier elemento, se muestra la `razon` de la IA.
- **Chat de edición** (4.6).
- **Deshacer y rehacer** usando el historial de versiones de la EDL.
- **Contador de costo** del video en pesos, siempre visible.
- Vista previa reproducible con la voz.

### Botón "Animar" (opcional, por escena)

- Convierte la imagen de la escena en un clip de video usando la imagen como primer fotograma, con un prompt de movimiento que la IA escribe a partir de la narración y la intención ("el alacrán levanta la cola lentamente, niebla moviéndose").
- **Antes de animar, muestra el costo en pesos y el tiempo estimado**, y pide confirmación.
- La IA puede **sugerir** las escenas que más ganan con animación (gancho, revelaciones, momentos de amenaza), pero nunca anima sin confirmación.
- Recorta el clip a la duración de la escena y conserva la imagen original para volver atrás.
- Proveedor y modelo de video configurables. El gasto en animación se muestra aparte del presupuesto base.

---

## 8. Aprendizaje con resultados reales (fase final)

- Conectar YouTube Analytics con OAuth (ya previsto para "Mis canales").
- Traer la curva de retención de cada video publicado desde el Estudio y cruzarla con la EDL: qué intención, efecto o tipo de escena había en cada caída o subida.
- Tras varios videos, proponer ajustes al `perfil_edicion.json` del canal ("las caídas coinciden con explicaciones de más de 12 segundos sin cambio de plano"). El usuario aprueba cada ajuste.

---

## 9. Plan por fases

Cada fase termina con criterios de aceptación verificables. No avances a la siguiente sin que la anterior los cumpla.

### Fase 0 · Base y caso de prueba
- Estructura de carpetas, configuración, esquemas de datos y libro de costos.
- **Esquema de `estilo.json` (sección 12) desde el primer día**, con un solo estilo implementado: "Enciclopedia + mascota". Ningún tipo de escena, plantilla de prompt ni modo de montaje debe quedar escrito en el código; todo se lee del estilo.
- Importar el proyecto de alacranes existente (`escenas.json` v1) y convertirlo a v2 como caso de prueba.
- **Acepta:** el proyecto de alacranes carga, valida contra el esquema, usa el estilo "Enciclopedia + mascota" leído desde `estilo.json`, y la estimación de costo se muestra en pesos calculada según su duración real.

### Fase 1 · Generación de assets
- Director visual con reutilización, generador de imágenes con personaje de referencia, quitar fondos, tira de niveles, control de calidad y reanudación.
- **Acepta:** el proyecto de alacranes genera todas sus imágenes sin superar el presupuesto de imágenes, y una interrupción a mitad de camino se reanuda sin regenerar lo existente.

### Fase 2 · Voz, alineación y montaje automático básico
- TTS, alineación (marcas del TTS o alineación forzada), EDL generada con reglas simples (sin Director de edición todavía), motor de render con el catálogo de efectos, subtítulos y música.
- **Acepta:** sale un `preview.mp4` completo donde cada imagen coincide con lo que se narra en ese momento (verificado revisando 20 escenas al azar) y la música baja con la voz.

### Fase 3 · Director de edición y Validador
- Las tres pasadas del Director, la gramática de edición, el Validador y la vista de razones.
- **Acepta:** la EDL cumple todas las reglas del Validador y cada elemento tiene su razón.

### Fase 4 · Editor
- Línea de tiempo, edición por escena, regenerar con instrucción, deshacer, render por tramos, contador de costos.
- **Acepta:** el usuario puede cambiar la duración de una escena, regenerar una imagen con instrucción y deshacer, y ver el resultado en la vista previa en menos de un minuto.

### Fase 5 · Revisor visual y chat de edición
- **Acepta:** el Revisor detecta al menos una imagen que no corresponde con su narración cuando se introduce una a propósito como prueba, y el chat aplica correctamente un pedido como "haz más intenso el nivel 3".

### Fase 6 · Animación opcional
- **Acepta:** animar una escena muestra el costo antes, genera el clip, lo ajusta a la duración y permite volver a la imagen fija.

### Fase 7 · Estratega integrado con Buscanichos
- Desde un outlier del feed, un botón "Crear video con este formato" que corre Estratega y Guionista y abre el proyecto en el Estudio.
- **Acepta:** de un outlier se llega a un guion con `escenas.json` v2 válido.

### Fase 7b · Catálogo de estilos
- El esquema ya existe desde la Fase 0. Aquí se agregan los demás estilos iniciales de la sección 12, el selector de estilo y "Crear estilo nuevo".
- **Acepta:** el mismo guion produce dos videos coherentes con dos estilos distintos (por ejemplo, "Enciclopedia + mascota" y "Stickman 2D") sin cambiar código.

### Fase 8 · Perfil de edición desde referencia, "Crear estilo desde un video" y aprendizaje con Analytics.

---

## 10. Lecciones del desarrollo anterior (Xandart)

- La duración de las escenas estimada por el modelo de lenguaje desincroniza imagen y voz: usar siempre marcas del TTS o alineación forzada.
- Los números en dígitos arruinan el TTS: escribirlos en palabras.
- Zooms rápidos se ven mal: movimiento lento y sutil por defecto.
- Separar el trabajo en capas (guion, visual, edición) mejora la calidad y baja el costo frente a pedirle todo a un solo paso.
- El bloqueo de personaje debe copiarse literal en cada prompt.
- El servidor local debe correr como servicio estable que se reinicie solo; no depender de un agente o terminal abierta.
- Claves de API solo en `.env`, nunca en el código ni en el repositorio.
- Alertas cuando el saldo prepago de cada proveedor baje de un umbral.

---

## 11. Lo que no se debe hacer

- No construir créditos, planes, pagos ni login de terceros en esta etapa.
- No dejar que la IA escriba comandos de FFmpeg directamente; solo produce la EDL.
- No gastar por encima del máximo sin confirmación explícita.
- No inventar precios de proveedores: leerlos de la configuración y avisar si faltan.
- No descargar ni almacenar videos de terceros para analizarlos.
- No usar música o efectos sin licencia verificable.
- No meter texto dentro de las imágenes generadas.

---

## 12. Catálogo de estilos de video

El Estudio no produce un solo tipo de video. Cada canal elige un **estilo**, y el estilo define cómo se ve y cómo se edita todo el video. Los módulos (Director visual, Generador, Director de edición, Motor) leen el estilo desde datos; nada de esto va escrito en el código.

### 12.1 `estilo.json`

```json
{
  "id": "stickman_2d",
  "nombre": "Stickman 2D",
  "descripcion": "Personaje de palitos con cabeza redonda en escenas simples, fondo claro, humor ligero",
  "miniatura": "estilos/stickman_2d/preview.png",
  "con_personaje": true,
  "bloque_estilo": "Clean 2D stickman illustration, thick black lines, flat pastel colors, simple backgrounds...",
  "personaje_por_defecto": "A stickman with a round white head, simple dot eyes...",
  "tipos_de_escena": [
    { "id": "personaje_escena", "plantilla_prompt": "{bloque_estilo} {personaje} {accion} in {lugar}. 16:9, no text.", "quitar_fondo": false, "modo_montaje": "pantalla_completa" },
    { "id": "objeto_explicativo", "plantilla_prompt": "{bloque_estilo} {objeto}, isolated on plain white. 16:9, no text.", "quitar_fondo": true, "modo_montaje": "recorte_sobre_fondo" }
  ],
  "mezcla_recomendada": { "personaje_escena": 0.7, "objeto_explicativo": 0.3 },
  "fondo_montaje": { "tipo": "color", "valor": "#F4F1EA" },
  "modos_de_montaje_permitidos": ["pantalla_completa", "recorte_sobre_fondo"],
  "gramatica_edicion": "gramaticas/estandar.json",
  "perfil_edicion": "perfiles/stickman_ritmo_medio.json",
  "movimiento_maximo": 0.05,
  "subtitulos": { "estilo": "blanco_contorno_negro", "posicion": "abajo_centro" },
  "musica_por_defecto": ["curiosidad", "humor"],
  "costo_relativo": 1.0
}
```

- `tipos_de_escena`: los tipos que el Director visual puede asignar en este estilo, cada uno con su plantilla de prompt, si se le quita el fondo y cómo se monta.
- `mezcla_recomendada`: proporción orientativa de cada tipo en el video.
- `con_personaje`: si es `true`, el canal debe tener un personaje fijo con imagen de referencia.
- `gramatica_edicion` y `perfil_edicion`: permiten que cada estilo tenga su propio ritmo (un estilo documental edita más lento que uno de retención alta).
- `costo_relativo`: ayuda al estimador de presupuesto (estilos con más recortes y combinaciones pueden necesitar más imágenes).

### 12.2 Estilos iniciales

Crea estos estilos como punto de partida, cada uno con su `estilo.json` y una imagen de vista previa generada:

| Estilo | Personaje | Descripción |
|---|---|---|
| **Enciclopedia + mascota** | Sí | El del proyecto de alacranes: ilustración detallada tipo enciclopedia, mascota cartoon, recortes sobre papel arrugado, escenas mixtas y amenazas cinematográficas. |
| **Stickman 2D** | Sí | Personaje de palitos con cabeza redonda en escenas simples; explicaciones, supervivencia, desarrollo personal. |
| **Cavernícola / historia ilustrada** | Sí | Personajes ilustrados en escenas de época, al estilo de canales de historia antigua y evolución humana (como la referencia Homo Curioso). |
| **Minimalista de íconos** | No | Íconos y objetos planos sobre fondo liso, animaciones simples; ideal para finanzas, listas y explicaciones rápidas. |
| **Pizarra** | No | Dibujos de línea negra sobre fondo blanco, como si se dibujaran a mano; educativo. |
| **Documental realista** | No | Imágenes fotorrealistas con movimiento lento y tono serio; historia, misterio, naturaleza. |
| **Recortes de papel** | Opcional | Collage con textura de papel y sombras, look artesanal. |

No copies estilos, personajes ni marcas de canales o estudios concretos: cada estilo debe ser genérico y original, tomando solo ideas generales de composición y ritmo.

### 12.3 Selección de estilo

- Al crear un canal en el Estudio, se elige el estilo desde una galería de miniaturas (con filtro "con personaje / sin personaje").
- Si el estilo lleva personaje, el siguiente paso es generar y aprobar el personaje del canal, que queda fijo para todos sus videos.
- Un video puede sobrescribir el estilo del canal si el usuario lo pide, pero por defecto hereda el del canal.

### 12.4 Crear estilo nuevo

Dos caminos, igual que en las plataformas de referencia:

1. **Desde cero:** el usuario escribe una descripción y sube 1 a 5 imágenes de ejemplo propias. Claude redacta el `bloque_estilo`, propone los tipos de escena y genera 4 imágenes de prueba. El usuario ajusta hasta aprobar, y el estilo queda guardado en el catálogo.
2. **Desde un video (Fase 8):** el usuario pega el link de un video de referencia. El sistema analiza su estilo visual (sin descargar ni guardar el video, igual que en 4.5) y propone un estilo inspirado en él, **genérico y original**, junto con su perfil de edición. Siempre pasa por aprobación del usuario con imágenes de prueba.

### 12.5 Reglas

- El estilo cambia el aspecto y el ritmo, nunca las reglas de presupuesto, el Validador ni el control de calidad.
- El Director visual solo puede usar los tipos de escena del estilo elegido.
- La reutilización inteligente (5.3) se adapta al estilo: en estilos de pantalla completa se reutiliza con otro encuadre o movimiento; en estilos de recortes, combinando elementos.

---

## 14. Edición con sensación humana

> Anexo agregado después de la Fase 0. No existe una sección 13 en esta versión del documento.

### Objetivo

Que la edición no se sienta automática. Lo que delata una edición de máquina es la regularidad: escenas de igual duración, zooms idénticos, cortes en cualquier punto de la frase, música en bucle y cero silencios. Estas reglas lo evitan.

### 14.1 Cambios de esquema

- `escenas.json` (por escena): agregar `palabra_clave` (la palabra más importante de la frase, la marca el Director) y `pausa_despues_seg` (0 por defecto).
- `perfil_edicion.json`: agregar `variacion_minima_duracion` (coeficiente de variación mínimo de la duración de escenas), `respiros_max_por_minuto` (1 por defecto), `uso_maximo_por_recurso` (porcentaje máximo del video que puede usar una misma transición, movimiento o efecto) y guardar también la variación, no solo promedios, cuando se aprende de un video de referencia.
- `edl.json`: en `movimiento` agregar `curva` (`ease_in_out` por defecto) y `punto_foco` (coordenadas normalizadas del sujeto importante); en `sfx` agregar `variante` y `tono` (factor de ajuste); en `escenas` agregar `respiro`: true/false.

### 14.2 Ritmo variable

- Las duraciones de escena no deben ser parejas. Alterna ráfagas rápidas (1,5 a 2,5 s) con planos más largos según la curva emocional: ráfaga antes de un golpe, plano sostenido después.
- Respiros: después de una `revelacion`, `advertencia` fuerte o `alivio`, se permite sostener una imagen hasta 6 s si antes hubo una secuencia rápida. Máximo `respiros_max_por_minuto`.
- Se ajusta la regla del Validador de "máximo 4,5 s sin cambio visual real": los respiros marcados con `"respiro": true` son la única excepción, hasta 6 s.

### 14.3 Cortes anclados a la palabra (marcas por palabra del Alineador)

- El corte a una imagen nueva cae 2 a 4 fotogramas **antes** de la palabra que la introduce.
- `zoom_golpe`, destellos y efectos de énfasis caen exactamente sobre `palabra_clave`.
- Los textos en pantalla aparecen cuando la voz dice esa palabra, no al inicio de la escena.
- Ningún corte cae en medio de una palabra.

### 14.4 Movimiento con curvas y variación

- Todo movimiento usa curvas suaves (ease in-out), nunca velocidad lineal.
- Dirección del paneo, punto de foco del zoom y porcentaje (dentro del máximo de 5 %) varían entre escenas con aleatoriedad controlada: semilla fija por proyecto para que el render sea repetible.
- El zoom se acerca al sujeto importante (`punto_foco`), no siempre al centro.
- Temblor leve de cámara solo en `amenaza` o `tension_creciente`.
- Algunas escenas sin ningún movimiento, para que el contraste haga notar los demás.

### 14.5 Silencios y pausas

- El guion puede marcar pausas ("…" o `pausa_despues_seg`). Si el TTS no las soporta, el motor inserta silencio en el audio y desplaza la línea de tiempo.
- Antes de una revelación, la música se corta o baja de golpe 0,3 a 0,8 s y el efecto de la revelación cae en ese silencio.
- Cortes J y L: los cambios de música entre secciones empiezan un poco antes o terminan un poco después del corte visual.

### 14.6 Música editada

- Detecta tempo y pulsos de cada pista (por ejemplo, con librosa) y alinea cambios de sección y algunos cortes importantes con los tiempos fuertes.
- Recorta y une pistas en puntos musicales, sin bucles audibles ni cortes a mitad de compás.
- Caídas de música en revelaciones, subidas en tensión creciente, fundidos que terminan en un tiempo fuerte.
- El audio se mezcla siempre completo, nunca por tramos.

### 14.7 Sonido con variación

- Cada tipo de efecto tiene un grupo de variantes; se elige al azar sin repetir la misma variante dos veces seguidas.
- Variación leve de tono (±5 %) y volumen en cada efecto.
- Las subidas de tensión terminan exactamente en el corte o revelación que anuncian.
- Los barridos van en la dirección del movimiento de la transición.

### 14.8 Referencias a lo ya visto

Cuando la narración vuelve sobre algo anterior ("¿te acuerdas del dato…?"), se reutiliza la misma imagen de ese momento, en pequeño o con el mismo encuadre.

### 14.9 Subtítulos naturales

- Bloques de 1 a 4 palabras cortados en pausas naturales, nunca separando artículo y sustantivo.
- `palabra_clave` resaltada en el color del estilo en el momento exacto en que se dice.
- Tiempos desde las marcas por palabra, no repartiendo el texto en partes iguales.

### 14.10 Detector de patrones mecánicos (dentro del Validador)

- Si la variación de duración de escenas en un tramo es menor que `variacion_minima_duracion`, rehace el ritmo de ese tramo.
- Ninguna transición, movimiento o efecto supera `uso_maximo_por_recurso`.
- Nunca la misma transición ni el mismo movimiento tres veces seguidas.
- Busca periodicidad (un recurso a intervalos regulares) y rómpela.

### 14.11 Voz

- Usa la mejor voz disponible o una voz clonada natural.
- Si el proveedor lo permite, varía levemente la velocidad según la intensidad.
- Genera primero solo los primeros 60 segundos de voz y pide aprobación antes de generar el resto.

### 14.12 Comprobación final

- El Revisor visual agrega la pregunta "¿algún tramo se siente mecánico o repetitivo?" y propone correcciones concretas.
- El Estudio compara las métricas de la EDL (duración media y variación de escenas, efectos por minuto, respiros, cambios de música) contra el perfil de referencia y muestra dónde se aleja.

### 14.13 Dónde encaja en las fases

| Puntos | Fase |
|---|---|
| 14.1 Cambios de esquema | Inmediato (Fase 0) |
| 14.3 a 14.7 y 14.9: alineación por palabra, curvas, silencios, música y sonido con variación, subtítulos | Fase 2 |
| 14.2, 14.8 y 14.10: ritmo variable, respiros, referencias, detector de patrones | Fase 3 |
| 14.12 Comprobación final | Fase 5 |
