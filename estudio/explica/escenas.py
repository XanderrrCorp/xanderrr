"""Escenas propias de El Calvo Explica que se arman solas a partir de la lista de temas.

La cuadrícula abre cada tema: todos los temas del video como círculos con su etiqueta; los ya vistos
en gris con chulo verde, los que faltan con «?», y un contador «3 DE 12». El círculo del tema actual
crece y pasa al centro, los demás desaparecen y sale el nombre del tema (una palabra en rojo).
"""
from __future__ import annotations


def _posiciones(n: int) -> list[tuple[float, float]]:
    por_fila = n if n <= 5 else (n + 1) // 2
    filas = [list(range(por_fila)), list(range(n - por_fila))] if n > 5 else [list(range(n))]
    paso = 1700 / max(por_fila, 1)
    salida = []
    for f, fila in enumerate(filas):
        y = 330 if len(filas) == 2 and f == 0 else (680 if len(filas) == 2 else 480)
        x0 = 960 - paso * (len(fila) - 1) / 2
        salida += [(round(x0 + i * paso), y) for i in fila]
    return salida


def cuadricula(temas: list[dict], actual: int, palabra_inicio: str, palabra_fin: str, nombre: str,
               rojo: str = "") -> dict:
    """Escena de cuadrícula para el tema `actual` (desde 0).

    temas: [{"etiqueta": "Sacudida", "icono": {"pieza": ..., "estado": {...}}}, ...]
    palabra_inicio / palabra_fin: la primera y la última palabra del nombre del tema (anclas de tiempo).
    """
    n = len(temas)
    tam = 0.85 if n <= 9 else 0.74
    elementos = []
    for i, (t, (x, y)) in enumerate(zip(temas, _posiciones(n))):
        visto = i < actual
        estado = {"etiqueta": t.get("etiqueta", "") if (visto or i == actual) else "",
                  "icono": t.get("icono") if (visto or i == actual) else "?",
                  "visto": visto, "actual": i == actual}
        movs: list = [{"tipo": "aparecer", "t_rel": 0.035 * i}]
        if i == actual:
            movs += [{"tipo": "cambiar_pose", "palabra": palabra_fin, "estado": {"etiqueta": ""}},   # el título lo dice
                     {"tipo": "deslizar", "hasta": [960, 430], "palabra": palabra_fin, "duracion": 0.6},
                     {"tipo": "crecer", "hasta": round(1.6 / tam, 2), "palabra": palabra_fin, "duracion": 0.6}]
        else:
            movs.append({"tipo": "desaparecer", "palabra": palabra_fin, "retraso": round(0.025 * i, 3)})
        elementos.append({"id": f"tema{i + 1}", "pieza": "circulo_tema", "estado": estado, "posicion": [x, y],
                          "tamano": tam, "movimiento": movs, "ya_estaba": True})
    elementos.append(elementos.pop(actual))           # el que se mueve va encima de los demás
    elementos.insert(0, {"id": "contador", "pieza": "texto", "estado": {"texto": f"{actual + 1} de {n}"},
                         "posicion": [960, 105], "tamano": 0.8, "movimiento": ["aparecer"], "ya_estaba": True})
    elementos.append({"id": "titulo", "pieza": "titulo_tema", "estado": {"texto": nombre, "rojo": rojo},
                      "posicion": [960, 860], "tamano": 1.0, "movimiento": ["aparecer"], "palabra": palabra_fin,
                      "retraso": 0.45})
    return {"tipo": "cuadricula", "palabra_inicio": palabra_inicio, "fondo": "blanco", "temblor": [],
            "elementos": elementos}
