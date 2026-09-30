"""Clips del modo Tracy: stock de Pexels y tramos del video base del seminario.

Stock (Licencia de Pexels: uso gratis y comercial, sin atribución obligatoria):
- se buscan videos horizontales de al menos 1920x1080 que duren al menos lo que el segmento;
- si con las keywords no sale nada, se reintenta con búsquedas más generales;
- no se repite un clip usado en los últimos 15 videos del canal ni dentro del mismo video;
- las descargas quedan en caché en disco (datos/cache/pexels): un clip se baja una sola vez.

Seminario: tramos al azar del clip base, sin solaparse dentro del video y evitando los usados en
los últimos 5 videos del canal. Si el clip base es corto y no alcanza, primero se relaja el
historial y, solo si aun así no cabe, se permite repetir (con aviso).
"""
from __future__ import annotations

import os
import random
import re
import subprocess
from pathlib import Path

import requests

from ..config import escribir_json
from ..proyecto import CarpetaProyecto
from . import historial

API_VIDEOS = "https://api.pexels.com/videos/search"
LICENCIA = "Licencia de Pexels: uso gratis, también comercial; sin atribución obligatoria (pexels.com/license)"
POR_PAGINA = 30
GENERALES = ["business success", "people working", "city life", "nature landscape", "sunrise", "teamwork",
             "office", "walking"]


# ------------------------------------------------------------------ caché

def carpeta_cache() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "cache" / "pexels"
    c.mkdir(parents=True, exist_ok=True)
    return c


# ------------------------------------------------------------------ Pexels

def _cabeceras() -> dict:
    from ..stock import _cabeceras as cab

    return cab()


def _mejor_archivo(video: dict) -> dict | None:
    """El MP4 horizontal de al menos 1080p más liviano (1920x1080 si existe; si no, el que siga)."""
    buenos = [a for a in video.get("video_files", [])
              if a.get("file_type") == "video/mp4" and (a.get("width") or 0) >= 1920 and (a.get("height") or 0) >= 1080
              and (a.get("width") or 0) > (a.get("height") or 0)]
    return min(buenos, key=lambda a: a["width"] * a["height"], default=None)


def buscar(consulta: str, minimo_s: float, excluir: set[str], sesion=requests) -> list[dict]:
    r = sesion.get(API_VIDEOS, params={"query": consulta, "per_page": POR_PAGINA, "orientation": "landscape",
                                       "size": "medium"}, headers=_cabeceras(), timeout=30)
    from ..stock import _revisar

    _revisar(r)
    salida = []
    for v in r.json().get("videos", []):
        if str(v["id"]) in excluir or (v.get("duration") or 0) < minimo_s:
            continue
        a = _mejor_archivo(v)
        if not a:
            continue
        salida.append({"pexels_id": str(v["id"]), "duracion": float(v.get("duration") or 0), "url_origen": v.get("url", ""),
                       "autor": (v.get("user") or {}).get("name", ""), "descarga": a["link"],
                       "ancho": a["width"], "alto": a["height"], "consulta": consulta})
    return salida


def consultas(keywords: list[str], mood: str) -> list[str]:
    """De lo más preciso a lo más general."""
    kws = [k for k in keywords if k]
    salida = []
    if len(kws) >= 2:
        salida.append(" ".join(kws[:2]))
    salida += kws
    # la palabra principal de cada keyword («man running at sunrise» → «running»)
    for k in kws:
        partes = [p for p in re.split(r"\s+", k) if len(p) > 3]
        if partes:
            salida.append(partes[-1] if len(partes) > 1 else partes[0])
    if mood:
        salida.append(f"{mood} {kws[0]}" if kws else mood)
    salida += GENERALES
    vistas, unicas = set(), []
    for c in salida:
        c = c.strip().lower()
        if c and c not in vistas:
            vistas.add(c)
            unicas.append(c)
    return unicas


def descargar(clip: dict, sesion=requests) -> Path:
    destino = carpeta_cache() / f"pexels_{clip['pexels_id']}_{clip['ancho']}x{clip['alto']}.mp4"
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    tmp = destino.with_suffix(".part")
    with sesion.get(clip["descarga"], stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for trozo in r.iter_content(1 << 20):
                f.write(trozo)
    os.replace(tmp, destino)
    return destino


def elegir_stock(plan: list[dict], canal: str, slug: str, avisar=print, sesion=requests, rng=None) -> dict[int, dict]:
    """Un clip de Pexels (ya descargado) por cada segmento «stock»."""
    rng = rng or random.Random(slug)
    usados = historial.stock_usado(canal, excluir=slug)
    en_video: set[str] = set()
    elegidos: dict[int, dict] = {}
    cache_busquedas: dict[str, list[dict]] = {}
    for p in plan:
        if p["type"] != "stock":
            continue
        clip = None
        for q in consultas(p.get("keywords") or [], p.get("mood", "")):
            if q not in cache_busquedas:
                cache_busquedas[q] = buscar(q, 0, set(), sesion=sesion)
            opciones = [c for c in cache_busquedas[q]
                        if c["duracion"] >= p["duracion"] and c["pexels_id"] not in usados | en_video]
            if opciones:
                clip = rng.choice(opciones[:8])        # entre los más relevantes, sin ser siempre el primero
                break
        if clip is None:
            raise RuntimeError(f"Pexels no tiene un clip nuevo de {p['duracion']:.0f} s o más para el segmento "
                               f"{p['id']} ({', '.join(p.get('keywords') or [])})")
        en_video.add(clip["pexels_id"])
        avisar(f"  segmento {p['id']}: stock «{clip['consulta']}» (Pexels {clip['pexels_id']})")
        elegidos[p["id"]] = {**clip, "archivo": str(descargar(clip, sesion=sesion))}
    return elegidos


# ------------------------------------------------------------------ seminario

def duracion_video(ruta: Path | str, ffmpeg: str) -> float:
    r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(ruta)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
    if not m:
        raise RuntimeError(f"no pude leer la duración de {ruta}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def _choca(a: float, b: float, tramos: list[tuple[float, float]]) -> bool:
    return any(a < y and x < b for x, y in tramos)


def _lugar(dur: float, total: float, ocupados: list[tuple[float, float]], rng) -> float | None:
    """Un inicio al azar donde [inicio, inicio+dur] no choque con ningún tramo ocupado."""
    if dur > total:
        return None
    libres, cursor = [], 0.0
    for x, y in sorted(ocupados):
        if x - cursor >= dur:
            libres.append((cursor, x - dur))
        cursor = max(cursor, y)
    if total - cursor >= dur:
        libres.append((cursor, total - dur))
    if not libres:
        return None
    pesos = [b - a + 1e-3 for a, b in libres]
    a, b = rng.choices(libres, weights=pesos)[0]
    return round(rng.uniform(a, b), 3)


def elegir_seminario(plan: list[dict], clip_base: str, total: float, canal: str, slug: str, avisar=print,
                     rng=None) -> dict[int, dict]:
    rng = rng or random.Random(slug + "|seminario")
    historicos = historial.tramos_usados(canal, clip_base, excluir=slug)
    propios: list[tuple[float, float]] = []
    elegidos: dict[int, dict] = {}
    for p in plan:
        if p["type"] != "seminar":
            continue
        dur = p["duracion"]
        inicio = _lugar(dur, total, propios + historicos, rng)
        if inicio is None:
            inicio = _lugar(dur, total, propios, rng)
            if inicio is not None:
                avisar(f"  segmento {p['id']}: el clip base es corto; reuso un tramo de un video anterior")
        if inicio is None:
            inicio = round(rng.uniform(0, max(0.0, total - dur)), 3)
            avisar(f"  segmento {p['id']}: el clip base no alcanza para no repetir dentro del video")
        propios.append((inicio, inicio + dur))
        elegidos[p["id"]] = {"archivo": clip_base, "inicio": inicio, "fin": round(inicio + dur, 3)}
    return elegidos


# ------------------------------------------------------------------ todo junto

def elegir_clips(carpeta: CarpetaProyecto, plan: list[dict], preset: dict, ffmpeg: str, avisar=print,
                 sesion=requests) -> dict:
    """Escribe `clips.json` (qué archivo y qué tramo va en cada segmento) y el registro de licencias."""
    proyecto = carpeta.cargar()
    canal, slug = proyecto.canal, proyecto.slug
    clip_base = preset["clip_base"]
    necesita_seminario = any(p["type"] == "seminar" for p in plan)
    seminario: dict[int, dict] = {}
    if necesita_seminario:
        if not Path(clip_base).exists():
            raise RuntimeError(f"No encuentro el video del seminario en «{clip_base}». Ponlo ahí o elige otro "
                               "archivo en la página de Tracy.")
        total = duracion_video(clip_base, ffmpeg)
        seminario = elegir_seminario(plan, clip_base, total, canal, slug, avisar=avisar)
    stock = elegir_stock(plan, canal, slug, avisar=avisar, sesion=sesion)
    fondo = None
    finales = [p for p in plan if p["type"] == "final"]
    if finales:
        fondo = elegir_fondo_final(canal, slug, {s["pexels_id"] for s in stock.values()}, avisar=avisar, sesion=sesion)
    clips = []
    for p in plan:
        if p["type"] == "final":
            # el mismo fondo corre en bucle continuo por toda la escena final
            desde = round((p["inicio"] - finales[0]["inicio"]) % max(1.0, fondo["duracion"] - 0.5), 3)
            clips.append({"id": p["id"], "tipo": "final", "archivo": fondo["archivo"], "desde": desde,
                          "duracion": p["duracion"], "inicio": p["inicio"], "fin": p["fin"],
                          "pexels_id": fondo["pexels_id"]})
        elif p["type"] == "seminar":
            s = seminario[p["id"]]
            clips.append({"id": p["id"], "tipo": "seminario", "archivo": s["archivo"], "desde": s["inicio"],
                          "duracion": p["duracion"], "inicio": p["inicio"], "fin": p["fin"]})
        else:
            s = stock[p["id"]]
            # un tramo al azar del clip de stock (así un clip largo no siempre muestra su comienzo)
            holgura = max(0.0, s["duracion"] - p["duracion"] - 0.5)
            desde = round(random.Random(f"{slug}|{p['id']}").uniform(0, holgura), 3) if holgura > 0 else 0.0
            clips.append({"id": p["id"], "tipo": "stock", "archivo": s["archivo"], "desde": desde,
                          "duracion": p["duracion"], "inicio": p["inicio"], "fin": p["fin"],
                          "pexels_id": s["pexels_id"]})
    escribir_json(carpeta.ruta / "clips.json", {"clips": clips})
    lic = [{"segmento": pid, "pexels_id": s["pexels_id"], "url_origen": s["url_origen"], "autor": s["autor"],
            "busqueda": s["consulta"]} for pid, s in stock.items()]
    if fondo:
        lic.append({"segmento": "escena final", "pexels_id": fondo["pexels_id"], "url_origen": fondo["url_origen"],
                    "autor": fondo["autor"], "busqueda": fondo["consulta"]})
    escribir_json(carpeta.ruta / "stock_licencias.json", {"licencia": LICENCIA, "clips": lic})
    historial.registrar(canal, slug,
                        [{"tipo": "stock", "clip": s["pexels_id"]} for s in stock.values()]
                        + ([{"tipo": "stock", "clip": fondo["pexels_id"]}] if fondo else [])
                        + [{"tipo": "seminario", "clip": clip_base, "inicio": s["inicio"], "fin": s["fin"]}
                           for s in seminario.values()])
    return {"clips": clips, "stock": len(stock), "seminario": len(seminario), "final": len(finales)}


def elegir_fondo_final(canal: str, slug: str, en_video: set[str], avisar=print, sesion=requests) -> dict:
    """Un video de naturaleza (se pasa a blanco y negro al montar) para la escena final."""
    from .escena_final import BUSQUEDAS_FONDO

    rng = random.Random(slug + "|fondo")
    usados = historial.stock_usado(canal, excluir=slug) | en_video
    orden = BUSQUEDAS_FONDO[:]
    rng.shuffle(orden)
    for q in orden:
        opciones = [c for c in buscar(q, 12, set(), sesion=sesion) if c["pexels_id"] not in usados]
        if opciones:
            c = rng.choice(opciones[:6])
            avisar(f"  escena final: fondo «{q}» (Pexels {c['pexels_id']})")
            return {**c, "archivo": str(descargar(c, sesion=sesion))}
    raise RuntimeError("Pexels no devolvió ningún video de naturaleza para la escena final")
