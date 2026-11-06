"""Clips de Pexels para los bloques [STOCK] (y los respiros del aura): horizontales 1920x1080, máx. 30 s por clip,
varios clips distintos encadenados si el bloque es más largo. Reusa la búsqueda y la caché de Tracy (datos/cache/pexels:
un clip se baja una sola vez). Pedido del dueño: NINGÚN clip se repite dentro del mismo video → registro en
stock/usados.json del video (id de Pexels, autor, enlace, bloque y tramo), que también sirve de crédito.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

MAX_CLIP = 30.0                  # pedido del dueño: ningún clip pasa de 30 s
TOMA = 8.0                       # (06-11, «más dopaminérgico») cada toma de stock dura como mucho ~8 s
MIN_CLIP = 6.0
GENERALES_AURA = ["golden hour nature", "calm sunset clouds", "candle light dark", "ocean waves sunset", "forest light rays"]


def _enlazar(origen: Path, destino: Path) -> None:
    if destino.exists():
        return
    try:
        os.link(origen, destino)                      # ocupa el espacio una sola vez
    except OSError:
        shutil.copy(origen, destino)


def tramos(dur: float) -> list[float]:
    """Largo de cada toma para cubrir `dur` (ninguna pasa de TOMA s; todas iguales: ninguna queda chiquita)."""
    n = max(1, int(-(-dur // min(MAX_CLIP, TOMA))))
    return [round(dur / n, 3)] * n


def elegir(trabajo: Path, pedidos: list[dict], avisar=print, sesion=None) -> dict:
    """pedidos: [{clave, claves[], dur}] → {clave: [{archivo, dur, pexels_id}]}. Lo ya elegido para ese pedido se reusa."""
    import requests

    from ..tracy.clips import buscar, consultas, descargar

    sesion = sesion or requests
    d = trabajo / "stock"
    d.mkdir(parents=True, exist_ok=True)
    reg_ruta = d / "usados.json"
    reg = json.loads(reg_ruta.read_text("utf-8")) if reg_ruta.exists() else {"clips": [], "pedidos": {}}
    usados = {c["pexels_id"] for c in reg["clips"]}
    salida: dict = {}
    for p in pedidos:
        largos = tramos(p["dur"])
        guardado = reg["pedidos"].get(p["clave"])
        if guardado and len(guardado) == len(largos) and all((d / g["archivo"]).exists() for g in guardado):
            salida[p["clave"]] = [{**g, "dur": l} for g, l in zip(guardado, largos)]
            continue
        elegidos = []
        for k, largo in enumerate(largos):
            clip = None
            for q in consultas(p["claves"], "") + (GENERALES_AURA if p.get("aura") else []):
                candidatos = [c for c in buscar(q, min(largo, MAX_CLIP) * 0.9, usados, sesion=sesion) if c["pexels_id"] not in usados]
                if candidatos:
                    clip = max(candidatos, key=lambda c: c["duracion"] >= largo)
                    break
            if clip is None:
                raise RuntimeError(f"Pexels no tiene clips nuevos para «{', '.join(p['claves'])}»")
            usados.add(clip["pexels_id"])
            origen = descargar(clip, sesion=sesion)
            nombre = f"pexels_{clip['pexels_id']}.mp4"
            _enlazar(origen, d / nombre)
            avisar(f"  stock «{clip['consulta']}» (Pexels {clip['pexels_id']}) para {p['clave']}")
            elegidos.append({"archivo": nombre, "pexels_id": clip["pexels_id"], "duracion_clip": clip["duracion"], "dur": largo})
            reg["clips"].append({"pexels_id": clip["pexels_id"], "autor": clip["autor"], "url": clip["url_origen"],
                                 "consulta": clip["consulta"], "pedido": p["clave"], "tramo": k + 1})
        reg["pedidos"][p["clave"]] = [{k2: v for k2, v in e.items() if k2 != "dur"} for e in elegidos]
        reg_ruta.write_text(json.dumps(reg, ensure_ascii=False, indent=1), "utf-8")
        salida[p["clave"]] = elegidos
    return salida
