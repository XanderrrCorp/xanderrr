# plan.json: formato y plantillas

```json
{"titulo": "...", "velocidad_voz": 1.05, "musica": true,
 "escenas": [ {"texto": "lo que dice la voz", "tipo": "habla", "p": {...}, "subtitulo": "opcional", "min": 1.6, "pausa": 0.35} ]}
```
- `texto`: la frase o frases exactas que dice la voz. La duración de la escena sale del audio.
- `subtitulo`: una píldora negra abajo. Úsalo poco.
- `p.sacudida`: true o false fuerza la sacudida de cámara en los impactos (por defecto la tienen numero, dinero, titulo y cuenta).
- Colores: "rojo", "verde", "morado", "terra", "negro", "gris" o [r, g, b].
- Poses de Inés (`pose`): down, hip, present, phone, point, cry. Caras (`cara`): meh (párpados a media asta, su cara base), normal, wide (susto), happy, cry.
- Fondos (`fondo`): blanco (por defecto), sala, cocina.

| tipo | Para qué | Parámetros |
|---|---|---|
| habla | Inés hablando, con una palabra grande opcional | pose, cara, ines (izq/centro/der), fondo, palabra, sub, color, tam, en (0–1) |
| numero | Entrada de cada punto de la lista | n, titulo, pose, cara |
| dinero | Cifra grande con reacción; puede contar | cifra, o desde+hasta+pre+post; etiqueta, color, nota (fuente), en |
| cuenta | Operación que se arma por partes | partes ["$30", "× 12", "= $360"], etiqueta, color, nota |
| tachar | Lista de 1 a 4 cosas; con tachar=false sirve de lista de reglas | items, titulo, tachar |
| telefono | Celular con app y cobros | app, cobros [[nombre, monto]], marca (índice a resaltar), total |
| comparar | Dos tarjetas: mal contra bien | izq [titulo, texto], der [titulo, texto] |
| titulo | Cartel a pantalla completa | lineas [], colores [], tam |
| gloria | Cocina con Gloria, la nevera (humor) | cartel, color, tiembla, pose, cara |
| libreta | Mención del producto | frase, donde |
| suscribete | Botón de suscripción que se presiona, con remate | remate, cara |
| pregunta | Burbuja con la pregunta para los comentarios | frase |

Ritmo: alterna plantillas y no pongas más de 2 "habla" seguidas. Cada número o cifra que se dice en voz alta debe verse en pantalla.
