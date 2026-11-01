# Guion — Short «El avispón gigante contra la bola de calor» (Peligro Tropical)

> Origen: escrito por Claude a partir de la parte del avispón gigante asiático de tu video largo
> «abejas y avispas» (youtu.be/VvpIw8jRxJ4), con la skill remotion-problem-resolve-video.
> Versión 1 — ESPERANDO APROBACIÓN. Convención: tiempos MM:SS:FF a 30 cps; cuadros en intervalo
> semiabierto [inicio, fin): el último cuadro de una escena es el primero de la siguiente.

## 1. Resumen de producción

- **Tema/recorte:** el avispón gigante asiático (el n.º 1 de tu ranking) ataca una colmena; la abeja
  japonesa lo vence formando una bola que vibra y lo «cocina» con calor (~46 °C).
- **Público/objetivo:** el público de Peligro Tropical; entender CÓMO las abejas vencen a algo que
  sus picaduras casi no dañan, y llevar al video completo.
- **Formato:** 45 s, 1080 × 1920 (9:16), 30 cps (1.350 cuadros), español latino, tono de intriga y
  ritmo ágil, como el canal.
- **Dirección de arte:** diorama 3D low-poly (formas geométricas, materiales mate, sombras suaves):
  rama con un tronco hueco cortado a la mitad que muestra la colmena por dentro (panales hexagonales).
  Avispón naranja y negro con «casco» naranja y mandíbulas; abejas pequeñas doradas. Fondo en
  degradé verde selva oscuro que pasa a naranja-rojo cuando sube el calor. Rojo = problema ✖,
  verde = solución ✔, azul = dato ℹ, amarillo = pregunta ?.
- **El sistema que se construye a la vista:** la misma colmena en corte pasa por invasión →
  defensa en bola → subida de temperatura (termómetro 3D) → avispón vencido.
- **Voz planeada:** la de siempre del canal en MiniMax (cuesta menos de 300 COP para ~650 letras)
  o, si prefieres 0 pesos, la voz gratis edge-tts (es-CO). Tú eliges al aprobar.
- **Sin derechos de terceros:** todo el 3D, la música y los sonidos se hacen por código.

## 2. Tabla cronológica

| Tiempo (Inicio - Fin) | Cuadros (Inicial - Final a 30 cps) | Narración (voz) | Escena y cámara | Objetos 3D/2D | Animaciones y transiciones | Insignias y textos |
| --- | --- | --- | --- | --- | --- | --- |
| 00:00:00 – 00:05:00 | 0 – 150 | Este avispón es del tamaño de tu pulgar… y acaba de encontrar una colmena. | Plano de detalle: el avispón entra volando a cámara desde el fondo (dolly-out d=6→9, az −20°→0°); al final, giro y la colmena se ve detrás. | Avispón (alas batiendo), pulgar low-poly a escala junto a él (0–60), rama y tronco con la colmena al fondo desenfocada. | `hornet.fly` 0→1 (0–40, out); `thumb.show` spring 8–60 y sale 60–75; `wings.flap` continuo; whoosh en 0. | ? ¿DEL TAMAÑO DE TU PULGAR? (warning, 10→140). Resaltar: PULGAR, COLMENA. |
| 00:05:00 – 00:11:00 | 150 – 330 | Mide unos cinco centímetros. Su armadura es tan gruesa que las picaduras de abeja casi no le hacen daño. | Órbita alrededor del avispón posado en la entrada (d=7, az 0°→35°, el 10°); regla 3D de 5 cm debajo de él. | Avispón, regla con marcas, 3 abejas que pican y rebotan con chispas. | `ruler.grow` 0→1 (15–45); abejas `bees.attack` 70–150 (rebote con spring); destello en el cuerpo en cada golpe. | ℹ 5 CM (info, en «cinco»); ✖ ARMADURA (negative, en «armadura»). Resaltar: CINCO, ARMADURA, DAÑO. |
| 00:11:00 – 00:17:00 | 330 – 510 | Con sus mandíbulas, unos pocos avispones pueden acabar con una colmena entera en unas horas. | Dolly-in a la cabeza (mandíbulas abren/cierran, d=4); corte suave a plano medio de la colmena en corte (d=14) con 4 avispones más llegando. | Mandíbulas, colmena en corte con panales, 4 avispones extra, reloj 2D que gira rápido. | `jaws.open` oscila 0↔1; `hornets.extra` spring escalonado (+6 cuadros); `hive.alarm` pulso rojo; reloj gira 0→360° ×3. | ✖ COLMENA EN PELIGRO (negative, en «colmena»). Resaltar: MANDÍBULAS, COLMENA, HORAS. |
| 00:17:00 – 00:23:00 | 510 – 690 | Pero la abeja japonesa tiene un truco. Cuando el avispón entra, cientos lo rodean. | Dentro de la colmena (d=10, el 15°): el avispón entra por el agujero; las abejas salen de los panales y lo envuelven (órbita az 10°→40°). | Abejas instanciadas (~300) que vuelan en espiral hacia el avispón; avispón dentro. | `hornet.enter` 0→1 (20–60); `bees.swarm` 0→1 (70–170, inOut) de los panales a una esfera alrededor del avispón. | ✔ ABEJA JAPONESA (positive, en «japonesa»). Resaltar: TRUCO, CIENTOS. |
| 00:23:00 – 00:30:00 | 690 – 900 | Forman una bola apretada y empiezan a vibrar los músculos de las alas. Sin volar. | Plano de la bola (d=6→5, dolly-in lento); la bola tiembla; corte interno: media bola transparente para ver al avispón atrapado. | Bola de abejas, avispón dentro, ondas de vibración (anillos 3D que se expanden). | `ball.tight` 0→1 (0–40); `ball.vibrate` 0→1 (en «vibrar»), temblor ±0,03 u3d; anillos cada 12 cuadros. | ✔ BOLA DE ABEJAS (positive, en «bola»); ℹ SIN VOLAR (info, en «volar»). Resaltar: BOLA, VIBRAR. |
| 00:30:00 – 00:37:00 | 900 – 1110 | Esa vibración sube el calor hasta unos cuarenta y seis grados. Las abejas lo aguantan. El avispón, no. | Plano dividido en profundidad: termómetro 3D a la izquierda, la bola a la derecha (d=8); fondo pasa de verde a naranja-rojo. | Termómetro 3D con el líquido subiendo, número 2D que cuenta 35→46 °C, onda de calor (partículas que suben), la bola brilla naranja. | `heat.level` 0→1 (20–150, inOut); `counter` 35→46; `ball.glow` 0→1; fondo interpolado por `heat.level`. | ℹ ~46 °C (info, en «grados»); ✔ ABEJAS: AGUANTAN (positive); ✖ AVISPÓN: NO (negative). Resaltar: CALOR, GRADOS, AGUANTAN. |
| 00:37:00 – 00:45:00 | 1110 – 1350 | Lo cocinan con puro calor. ¿Y el que no puede picarte ni aunque quiera? Está en el video completo. | La bola se abre y las abejas vuelven a los panales; el avispón queda inmóvil; dolly-out a la colmena entera (d=16) que vuelve a verde; sin fundido final. | Colmena, abejas regresando, avispón quieto, flecha 2D animada abajo. | `ball.tight` 1→0 (0–50); `heat.level` 1→0; `hornet.down` 0→1; flecha rebota (spring cada 20 cuadros) desde 160. | ✔ AVISPÓN VENCIDO (positive, en «cocinan»); ? ¿EL QUE NO PUEDE PICARTE? (warning); VIDEO COMPLETO ▼ (grande, desde 160 hasta el final). Resaltar: CALOR, VIDEO, COMPLETO. |

## 3. Narración completa (116 palabras ≈ 155 palabras/min en 45 s)

Este avispón es del tamaño de tu pulgar… y acaba de encontrar una colmena. Mide unos cinco
centímetros. Su armadura es tan gruesa que las picaduras de abeja casi no le hacen daño. Con sus
mandíbulas, unos pocos avispones pueden acabar con una colmena entera en unas horas. Pero la abeja
japonesa tiene un truco. Cuando el avispón entra, cientos lo rodean. Forman una bola apretada y
empiezan a vibrar los músculos de las alas. Sin volar. Esa vibración sube el calor hasta unos
cuarenta y seis grados. Las abejas lo aguantan. El avispón, no. Lo cocinan con puro calor. ¿Y el que
no puede picarte ni aunque quiera? Está en el video completo.

Los tiempos son estimados: cuando exista la voz real, los cortes se ajustan a ella (cada escena entra
~0,25 s antes de su frase) sin cambiar el contenido.

## 4. Audio y montaje

- **Voz:** MiniMax (la del canal) o edge-tts gratis; tono de intriga, ritmo ágil.
- **Efectos hechos por código:** whoosh al entrar el avispón (0 s), zumbido grave del avispón
  (escenas 1–3, bajo), golpecitos metálicos cuando rebotan las picaduras (escena 2), latido de alarma
  (escena 3), enjambre que crece (escena 4), vibración grave (escenas 5–6), tic del contador de
  grados, «pop» de cada insignia, golpe suave final.
- **Música:** pista de suspenso hecha por código, que baja cuando habla la voz.
- **Subtítulos:** palabra por palabra y alineados a la voz real, con las palabras clave en color.

## 5. Datos y verificación

- Avispón gigante asiático: hasta ~5 cm (las reinas); aguijón de ~6 mm; pocos avispones pueden acabar
  con una colmena de abejas europeas en horas. (Datos de tu video largo y de fuentes de divulgación
  conocidas.)
- Abeja japonesa (Apis cerana japonica): forma una bola alrededor del avispón y la calienta con los
  músculos de vuelo hasta ~46 °C; el avispón no tolera esa temperatura y las abejas aguantan un poco
  más (~48–50 °C). Se dice «unos 46 grados», sin más cifras.
- Nada de consejos de salud en el Short.
- El 3D es esquemático (low-poly), no una foto: no hace falta etiqueta de contenido sintético
  realista, pero sí conviene marcar «contenido alterado o sintético» al subirlo si YouTube lo pide.

**Criterios de aceptación:** gancho en el primer segundo; cadena problema → solución entendible
(armadura → colmena en peligro → bola → calor → victoria); el mismo diorama de principio a fin; se ve
en celular; tabla completa; cuadros seguidos sin huecos (0–1350); narración que cabe en 45 s;
`scene-plan.ts` igual a la tabla.
