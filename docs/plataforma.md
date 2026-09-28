# Xandart como plataforma (SaaS): plan y decisiones

Rama de trabajo: `claude/xandart-saas`. La versión de producción (`claude/new-session-uq98jd`)
sigue sacando los videos de Peligro Tropical hasta que el dueño apruebe que la nueva produce un
video completo igual o mejor.

## Decisiones del dueño
- Claude: la cuenta del dueño usa su suscripción; los clientes, la API de Anthropic (va en la tabla de precios).
- Estilo desde YouTube: miniatura pública automática + capturas que suba el usuario. **Nunca descargar el video.**
- 1 crédito = 0,01 USD al cliente, siempre mostrado también en minutos equivalentes.
- Los créditos del plan que no se usan se acumulan hasta 2 meses del plan.
- Interfaz nueva en React + Vite construida en GitHub Actions; el repositorio pasa a privado en la Fase 2
  (antes hay que cambiar el instalador).
- Correos por SMTP de Gmail con contraseña de aplicación.
- Planes: Lite 29 USD / 20 min, Starter 59 / 45, Creator 129 / 110.

## Formatos de video y estilos: cada usuario hace el suyo (pedido del dueño, 28-09-2026)
Referencia: el «Productor» de la competencia (selector de formato + duración + modo Auto/Personalizado,
e «Inicio rápido» con Sleep video, Storytelling, Top X, Doodle Character, Doodle Stickman, Stickman).

- **Formato** (tabla `formatos`): plantilla de video que se elige al crear. Junta fórmula de guion,
  estilo visual y perfil de edición, con sus duraciones y una idea de ejemplo.
  - El catálogo público de Xandart trae los formatos base (hoy: Escala de peligro). Pendientes de
    diseñar: Top X, Storytelling, Video para dormir, Stickman, Personaje doodle.
  - **Cada usuario puede crear los formatos y estilos que quiera**, sin límite de diseño: duplicando uno
    del catálogo y editándolo, o desde cero con el asistente de estilo (referencias subidas, miniaturas
    públicas de YouTube). Lo suyo es privado de su espacio.
  - Un canal tiene un formato «de siempre»; cada video guarda con qué formato se hizo.
- Formatos base pedidos por el dueño para el catálogo (referencias visuales de la competencia, 28-09-2026;
  las imágenes de Xandart se generan con estilos propios, no se copian las de ellos):
  1. **Videos para dormir**: paisajes pintados, luz cálida y calma (bosques, montañas, costas, pueblos
     antiguos, barcos al atardecer, fogatas), sin personajes en primer plano, cortes lentos, voz suave,
     30–120 min.
  2. **Narración de historias** (Storytelling): ilustración de cómic o novela gráfica, personajes con
     expresión, escenas de época y de noche, relato continuo.
  3. **Top X**: cuenta regresiva numerada con escenas ilustradas cálidas y un número grande por puesto.
  4. **Garabato · personaje regular** (Doodle character): personaje simple y fijo (cabeza cuadrada o
     caricatura) dentro de escenarios detallados y coloridos.
  5. **Garabato · hombre de palo** (Stickman): muñecos de palitos con caras expresivas sobre fondos
     pintados con detalle (historia, viajes, humor).
  6. **Escala de peligro** (el de Peligro Tropical) — ya existe.
- La caja de inicio: escribir la idea, elegir formato, duración y canal. Modo **Auto** (Xandart decide
  todo y el usuario aprueba cada paso) o **Personalizado** (el usuario ajusta guion, estilo y voz antes).

## Idea del dueño: disfraz de la mascota según el animal del video (28-09-2026)
Referencia vista en otro canal: el personaje lleva un hoodie con capota del animal del que habla el video
(rana → capota de rana con ojos arriba). Cómo encaja en Xandart:
- Al crear el video se genera UNA imagen de la mascota del canal con el hoodie del animal (misma cara y
  trazo, con la mascota de siempre como referencia). Esa imagen es la referencia del personaje solo en
  ese video: todas las escenas con la mascota la usan sin costo extra.
- Las poses guardadas del canal (reacciones que se reusan gratis) no tienen el disfraz: o se rehacen
  para ese video (~10 imágenes, ~$0.70) o ese video usa solo escenas generadas con la mascota.
- Opción por canal/formato: «disfraz según el tema» sí/no. Aplica también a la miniatura.
- Ojo con el parecido: es una idea general (disfraz temático), no se copia el personaje ni el estilo del otro canal.

## Funciones pedidas para el inicio (según la competencia)
Producir: video largo, short vertical, recortes a shorts (solo de videos propios).
Identidad del canal: personaje, estilo visual, canal. Generar suelto: imagen, clip animado, voz.
Publicar: miniatura escala 2×3, títulos y descripción, avance (tráiler de 30 s).

## Interfaz nueva (Fase 2)
- Código en `interfaz/` (React + Vite + TypeScript). `npm run build` deja lo construido en
  `estudio/web_app/`, que Xandart sirve en `/app`. El workflow «Interfaz» lo construye en GitHub
  Actions y lo sube solo cuando cambia; el instalador lo baja con el resto del código.
- Diseño aprobado (mezcla): menú lateral angosto con grupos Crear / Mis recursos / Inspiración que
  abren un panel de herramientas; créditos siempre arriba a la derecha (la cuenta del dueño ve su
  gasto real del mes); inicio con la caja de idea (formato, canal, duración, Auto/Personalizado) y al
  lado el video en marcha con el storyboard que se va llenando; planes solo visual (sin pasarela).
- Mientras tanto, la revisión y aprobación de cada video sigue en la página de siempre (`/#slug`).

## Fases
1. Datos multiusuario, créditos, migración de Peligro Tropical, API v2 y administración — **hecha**.
3. Asistente de personaje (atajo pedido por Paradoja Sapiens).
2. Sistema de diseño + React, render a 60 cps más rápido, repositorio privado.
4–7. Asistente de estilo, asistente de canal, biblioteca, onboarding, pasarela de pago.
