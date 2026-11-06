"""Guion etiquetado de Código del Éxito → bloques.

Cada párrafo empieza con su etiqueta en una línea propia (o al inicio del párrafo):
  [PROFESOR]                       escena animada del Profesor (gancho, inicio de cada regla, CTAs)
  [STOCK: palabras clave en inglés] clips de Pexels
  [AURA]                           fondo con visualizador del audio (pasajes reflexivos, afirmaciones, rituales)
Un texto sin etiqueta sigue con la etiqueta del párrafo anterior. Cada [PROFESOR] abre una PARTE nueva (la unidad de
render: si algo falla se repite solo esa parte).
"""
from __future__ import annotations

import re

ETIQUETA = re.compile(r"^\s*\[(PROFESOR|AURA|STOCK)(?:\s*:\s*([^\]]*))?\]\s*", re.I)


def leer(texto: str) -> list[dict]:
    bloques: list[dict] = []
    actual: dict | None = None
    for parrafo in re.split(r"\n\s*\n", texto.strip()):
        p = parrafo.strip()
        if not p:
            continue
        m = ETIQUETA.match(p)
        if m:
            tipo = m.group(1).lower()
            claves = [k.strip() for k in (m.group(2) or "").split(",") if k.strip()]
            cuerpo = " ".join(p[m.end():].split())
            actual = {"tipo": tipo, "claves": claves, "texto": cuerpo}
            bloques.append(actual)
        elif actual is None:
            actual = {"tipo": "profesor", "claves": [], "texto": " ".join(p.split())}
            bloques.append(actual)
        else:
            actual["texto"] = (actual["texto"] + " " + " ".join(p.split())).strip()
    bloques = [b for b in bloques if b["texto"]]
    parte = 0
    for k, b in enumerate(bloques):
        if b["tipo"] == "profesor" and k > 0:
            parte += 1
        b["id"] = k + 1
        b["parte"] = parte
        if b["tipo"] == "stock" and not b["claves"]:
            raise ValueError(f"el bloque {k + 1} es [STOCK] pero no trae palabras clave")
    if not bloques:
        raise ValueError("el guion no tiene bloques")
    return bloques
