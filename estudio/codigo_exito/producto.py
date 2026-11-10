"""Escena del producto cuando la voz nombra MI VALOR o MI CÓDIGO (10-11, el dueño: «quiero que se vea como cuando lo
hacíamos a mano»). Son LAS MISMAS escenas de los primeros videos animados (estudio/animado: «mivalor» = el PDF con el sello
de 7 días de garantía; «micodigo» = el planner de 7 días en el celular), sin cambios:

- en un bloque del Profesor: la escena entra justo cuando la voz dice el nombre y se queda al menos DUR_MIN s;
- en un bloque de stock o de aura: un clip de esa escena (DUR_INSERTO s) tapa el stock en ese momento (Remotion).
Una vez por bloque y, del mismo producto, como mucho una cada SEPARACION_S (un guion largo lo nombra muchas veces).
"""
from __future__ import annotations

import re
import unicodedata

PRODUCTOS = {"mivalor": re.compile(r"\bmi valor\b"), "micodigo": re.compile(r"\bmi codigo\b")}
DUR_MIN = 4.5
DUR_INSERTO = 5.5
SEPARACION_S = 45.0


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def momento(b: dict) -> tuple[str, float] | None:
    """(tipo de escena, segundo DENTRO del bloque) en que la voz nombra un producto, o None"""
    texto = _plano(b.get("texto", ""))
    hallado = min(((m.start(), tipo) for tipo, rx in PRODUCTOS.items() if (m := rx.search(texto))), default=None)
    if not hallado:
        return None
    _, tipo = hallado
    trozos = b.get("trozos") or []
    unido, pos = "", []
    for z in trozos:                                 # el texto de los trozos seguido, sabiendo dónde empieza cada uno
        pos.append(len(unido))
        unido += _plano(z["texto"]) + " "
    m = PRODUCTOS[tipo].search(unido)
    if m and trozos:
        k = max(i for i, p in enumerate(pos) if p <= m.start())
        return tipo, max(0.0, round(trozos[k]["ini"] - b.get("inicio", 0.0), 3))
    return tipo, 0.0


def elegir(bloques: list[dict]) -> dict[int, tuple[str, float]]:
    """{id del bloque: (tipo, segundo)} respetando la separación entre apariciones del mismo producto"""
    salida, ultimo = {}, {}
    for b in bloques:
        m = momento(b)
        if not m:
            continue
        tipo, t = m
        cuando = b.get("inicio", 0.0) + t
        if cuando - ultimo.get(tipo, -1e9) < SEPARACION_S:
            continue
        ultimo[tipo] = cuando
        salida[b["id"]] = (tipo, t)
    return salida


def escena(tipo: str) -> dict:
    e = {"tipo": tipo, "profesor": None}
    if tipo == "mivalor":
        e["sello"] = True                            # el sello de «7 días de garantía», como en los primeros videos
    return e


def en_plan(plan: list[dict], ranura: float, tipo: str, t: float) -> list[dict]:
    """mete la escena del producto en el plan del Profesor en el segundo t (quita lo que la tape)"""
    t = min(max(0.0, t), max(0.0, ranura - DUR_MIN))
    fin = t + DUR_MIN
    resto = [e for e in plan if not (t - 0.01 <= float(e.get("inicio", 0)) < fin)]
    nuevo = {**escena(tipo), "inicio": round(t, 3)}
    salida = sorted(resto + [nuevo], key=lambda e: float(e.get("inicio", 0)))
    if salida and float(salida[0].get("inicio", 0)) > 0:
        salida[0]["inicio"] = 0.0
    return salida
