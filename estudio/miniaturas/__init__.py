"""Producción de miniaturas de formato «escala» (2x3), por piezas.

La IA no dibuja la miniatura entera (falla con marcos, textos y protagonistas
torcidos). En su lugar:

1. Claude planifica (plan.py): qué mide la escala, el gancho, los 6 sujetos, el
   texto y el ícono del protagonista.
2. Gemini dibuja CADA sujeto por separado sobre blanco, con 2-3 referencias de
   estilo de la plantilla del canal (generar.py).
3. El código quita el fondo (recorte.py) y compone la miniatura con fuentes reales
   (composicion.py): layout, aura, íconos y textos siempre salen perfectos.
4. Claude con visión revisa el resultado y se regenera lo que falle (qa.py).

Todo vive en <proyecto>/miniatura_escala/ y la plantilla de cada canal en
canales/<canal>/miniatura/.

Fase 2 (sin construir): «Analizar miniaturas de referencia» leerá 3-6 miniaturas
de otro canal y escribirá una plantilla nueva con el mismo formato de plantilla.json.
"""
