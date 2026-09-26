# Retomar: prueba real de imágenes (Fase 1)

Estado al 26-09-2026. El dueño no es técnico: hacer todo desde la sesión en la nube.

## Qué falta (criterio de éxito del bloque)
Generar las imágenes de las **primeras 10 escenas del proyecto de alacranes** con el
proveedor real y mostrar: la hoja de contacto, el costo real en pesos y la
proyección para el video completo (~222 imágenes). Con ese número el dueño decide
si seguir.

## Requisitos (los configura el dueño en el entorno)
- Credencial del entorno tipo Bearer para `api.together.xyz` (el proxy inyecta `Authorization`; el código
  no necesita la clave). Alternativa: variable `TOGETHER_API_KEY`. Nunca escribirla en el repo: es público.
- Si `api.together.xyz` sigue bloqueado, añadirlo también en el acceso a red del entorno.
- El `escenas.json` de alacranes: lo adjunta en el chat (queda en /root/.claude/uploads/...).

## Pasos
```bash
pip install -e ".[dev]"
python -m estudio importar-v1 <ruta escenas.json> --slug alacranes --canal animales-peligrosos
python -m estudio generar-imagenes --slug alacranes --primeras 10 --proveedor simulado   # ensayo gratis
python -m estudio generar-imagenes --slug alacranes --primeras 10                        # real (Together)
```
Luego mandarle al dueño `proyectos/alacranes/render/hoja_imagenes.png` (SendUserFile) y
el resumen en pesos.

## Riesgos conocidos
- El importador v1→v2 se escribió sin ver el archivo real: ajustar alias de campos
  en `estudio/importar_v1.py` si falla.
- Together documenta `reference_images` como URLs; se mandan como data URI. Si da
  error con `reference_images`, subir la referencia a una URL o probar sin ella.
- Precio configurado: 0,0403 USD por imagen (medido por el dueño). Confirmar con
  lo que registre el libro de costos.
- Las pruebas de `xandart/` que fallan por fuentes tipográficas faltantes fallan
  igual en el código original.
