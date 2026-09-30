"""Segmentos visuales del modo Tracy: oraciones agrupadas en clips de 8-20 s, nunca más de 30.

Cada segmento cubre desde el inicio de su primera oración hasta el inicio del siguiente
segmento (el primero desde 0 y el último hasta el final del audio), así la imagen nunca
queda en negro. Los cortes caen siempre al final de una oración completa.

El agrupado es el óptimo (programación dinámica): minimiza cuánto se sale cada segmento del
rango objetivo y, a igualdad, prefiere duraciones cercanas al centro del rango. Solo si una
oración sola pasa del máximo se parte dentro de ella, en la pausa más clara (coma o silencio).
"""
from __future__ import annotations

from ..config import escribir_json, leer_json
from ..proyecto import CarpetaProyecto


def _partir(unidad: dict, fin_cobertura: float, maximo: float, inicio_cobertura: float | None = None) -> list[dict]:
    """Parte una oración que (con su pausa) dura más que `maximo` en la mejor pausa interna."""
    pal = unidad["palabras"]
    inicio_cobertura = unidad["inicio"] if inicio_cobertura is None else inicio_cobertura
    if fin_cobertura - inicio_cobertura <= maximo or len(pal) < 2:
        return [unidad]
    medio = (unidad["inicio"] + fin_cobertura) / 2
    mejor, mejor_k = None, None
    for k in range(1, len(pal)):
        hueco = pal[k]["inicio"] - pal[k - 1]["fin"]
        puntuacion = hueco + (0.35 if pal[k - 1]["p"].endswith((",", ";", ":", "—")) else 0)
        puntuacion -= 0.02 * abs(pal[k]["inicio"] - medio)
        if mejor is None or puntuacion > mejor:
            mejor, mejor_k = puntuacion, k
    a = {"texto": " ".join(p["p"] for p in pal[:mejor_k]), "inicio": pal[0]["inicio"],
         "fin": pal[mejor_k - 1]["fin"], "palabras": pal[:mejor_k], "oraciones": unidad["oraciones"], "partida": True}
    b = {"texto": " ".join(p["p"] for p in pal[mejor_k:]), "inicio": pal[mejor_k]["inicio"],
         "fin": unidad["fin"], "palabras": pal[mejor_k:], "oraciones": unidad["oraciones"], "partida": True}
    return _partir(a, b["inicio"], maximo, inicio_cobertura) + _partir(b, fin_cobertura, maximo)


def _costo(dur: float, lo: float, hi: float) -> float:
    fuera = (lo - dur) if dur < lo else (dur - hi) if dur > hi else 0.0
    centro = (lo + hi) / 2
    return fuera ** 2 * 10 + 0.001 * (dur - centro) ** 2


def segmentar(oraciones: list[dict], duracion: float, objetivo: tuple[float, float] = (8.0, 20.0),
              maximo: float = 30.0) -> list[dict]:
    """oraciones = [{"texto", "inicio", "fin", "palabras"?}] en orden. Devuelve los segmentos."""
    if not oraciones:
        return []
    lo, hi = objetivo
    # unidades: oraciones enteras (o trozos de las que solas pasan del máximo)
    unidades: list[dict] = []
    for i, o in enumerate(oraciones):
        fin_cob = oraciones[i + 1]["inicio"] if i + 1 < len(oraciones) else duracion
        base = {**o, "oraciones": [o.get("id", i)], "palabras": o.get("palabras") or []}
        unidades += _partir(base, fin_cob, maximo, 0.0 if i == 0 else None)   # el primero cubre desde 0
    n = len(unidades)
    ini = [0.0] + [u["inicio"] for u in unidades[1:]]
    fin_cob = ini[1:] + [duracion]
    inf = float("inf")
    mejor = [inf] * (n + 1)
    desde = [0] * (n + 1)
    mejor[0] = 0.0
    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            dur = fin_cob[i - 1] - ini[j]
            if dur > maximo and j < i - 1:
                break                                  # agregar más oraciones solo lo alarga
            c = mejor[j] + _costo(dur, lo, hi) + (1e6 if dur > maximo else 0)
            if c < mejor[i]:
                mejor[i], desde[i] = c, j
    cortes, i = [], n
    while i > 0:
        cortes.append((desde[i], i))
        i = desde[i]
    segmentos = []
    for k, (j, i) in enumerate(reversed(cortes)):
        grupo = unidades[j:i]
        ids: list[int] = []
        for u in grupo:
            ids += [x for x in u["oraciones"] if x not in ids]
        segmentos.append({"id": k, "inicio": round(ini[j], 3), "fin": round(fin_cob[i - 1], 3),
                          "duracion": round(fin_cob[i - 1] - ini[j], 3),
                          "voz_inicio": round(grupo[0]["inicio"], 3), "voz_fin": round(grupo[-1]["fin"], 3),
                          "texto": " ".join(u["texto"] for u in grupo), "oraciones": ids,
                          "oracion_partida": any(u.get("partida") for u in grupo)})
    return segmentos


def segmentar_proyecto(carpeta: CarpetaProyecto, preset: dict) -> list[dict]:
    datos = leer_json(carpeta.ruta / "audio" / "oraciones.json")
    segs = segmentar(datos["oraciones"], datos["duracion"], tuple(preset["clip_objetivo_s"]), preset["clip_max_s"])
    escribir_json(carpeta.ruta / "segmentos.json",
                  {"duracion": datos["duracion"], "objetivo_s": preset["clip_objetivo_s"],
                   "maximo_s": preset["clip_max_s"], "segmentos": segs})
    return segs
