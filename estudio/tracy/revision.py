"""(01-11) Revisión antes de exportar (edición humana del modo Tracy): el dueño ve las tomas marcadas por sección
(gancho, cuerpo, venta, cierre) y puede cambiar el clip, alargar o acortar una toma (siempre hasta el final de una
oración) o cambiar el texto grande. Después «Exportar» arma el video con lo revisado."""
from __future__ import annotations

import hashlib
import random
import subprocess
from pathlib import Path

from ..config import escribir_json, leer_json
from ..proyecto import CarpetaProyecto

MINIMO_S = 2.0


def pendiente(c: CarpetaProyecto) -> bool:
    """Hay un plan de edición humana listo y todavía no se exportó con él."""
    plan, clips, final = c.ruta / "plan_visual.json", c.ruta / "clips.json", c.ruta / "render" / "final.mp4"
    if not (plan.exists() and clips.exists()) or leer_json(plan).get("origen") != "humano":
        return False
    return not final.exists() or final.stat().st_mtime < clips.stat().st_mtime


def _miniatura(c: CarpetaProyecto, clip: dict, ffmpeg: str) -> str | None:
    clave = hashlib.sha1(f"{clip['archivo']}|{clip['desde']}|{clip['tipo']}".encode()).hexdigest()[:10]
    rel = f"render/tracy/mini/c{clip['id']:04d}_{clave}.jpg"
    destino = c.ruta / rel
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        filtro = "scale=320:180:force_original_aspect_ratio=increase,crop=320:180" + \
                 (",hue=s=0" if clip["tipo"] in ("seminario", "final") else "")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{float(clip['desde']) + 0.5:.2f}", "-i",
                        str(clip["archivo"]), "-frames:v", "1", "-vf", filtro, str(destino)], capture_output=True)
    return rel if destino.exists() else None


def ver(c: CarpetaProyecto, ffmpeg: str | None = None) -> dict:
    clips = leer_json(c.ruta / "clips.json")["clips"]
    ors = {o["id"]: o["texto"] for o in leer_json(c.ruta / "audio" / "oraciones.json")["oraciones"]}
    salida = []
    for x in clips:
        salida.append({"id": x["id"], "tipo": x["tipo"], "seccion": x.get("seccion", "cuerpo"), "rol": x.get("rol"),
                       "inicio": x["inicio"], "fin": x["fin"], "duracion": round(x["fin"] - x["inicio"], 2),
                       "texto": " ".join(ors.get(i, "") for i in x.get("oraciones") or []).strip(),
                       "grande": x.get("grande"), "keywords": x.get("keywords") or [],
                       "movimiento": x.get("movimiento"), "transicion": x.get("transicion"),
                       "miniatura": _miniatura(c, x, ffmpeg) if ffmpeg else None})
    reporte = c.ruta / "reporte_edicion.json"
    return {"pendiente": pendiente(c), "clips": salida,
            "reporte": leer_json(reporte) if reporte.exists() and not pendiente(c) else None}


def _guardar(c: CarpetaProyecto, clips: list[dict]) -> None:
    escribir_json(c.ruta / "clips.json", {"clips": clips})
    _registrar_usos(c, clips)


def _registrar_usos(c: CarpetaProyecto, clips: list[dict]) -> None:
    from . import historial

    p = c.cargar()
    historial.registrar(p.canal, p.slug,
                        [{"tipo": "stock", "clip": x["pexels_id"]} for x in clips if x.get("pexels_id")]
                        + [{"tipo": "seminario", "clip": x["archivo"], "inicio": x["desde"],
                            "fin": round(x["desde"] + x["fin"] - x["inicio"], 3)}
                           for x in clips if x["tipo"] == "seminario"])


def _limites(c: CarpetaProyecto) -> list[float]:
    """Dónde se puede cortar: el inicio de cada oración (como en el plan)."""
    return sorted(o["inicio"] for o in leer_json(c.ruta / "audio" / "oraciones.json")["oraciones"])


def cambiar(c: CarpetaProyecto, clip_id: int, accion: str, texto: str | None = None, preset: dict | None = None,
            ffmpeg: str | None = None, sesion=None) -> dict:
    """accion: «otro_stock» | «seminario» | «alargar» | «acortar» | «texto»."""
    clips = leer_json(c.ruta / "clips.json")["clips"]
    k = next((i for i, x in enumerate(clips) if x["id"] == clip_id), None)
    if k is None:
        raise ValueError("Esa toma no existe")
    x = clips[k]
    if x["tipo"] == "final" and accion not in ("texto",):
        raise ValueError("La escena final no se cambia aquí")
    if accion == "texto":
        x["grande"] = (texto or "").strip()[:40] or None
    elif accion in ("alargar", "acortar"):
        _mover_corte(c, clips, k, +1 if accion == "alargar" else -1)
    elif accion == "seminario":
        _a_seminario(c, clips, k, preset or {}, ffmpeg)
    elif accion == "otro_stock":
        _otro_stock(c, clips, k, sesion)
    else:
        raise ValueError("Acción desconocida")
    _guardar(c, clips)
    return ver(c, ffmpeg)


def _mover_corte(c: CarpetaProyecto, clips: list[dict], k: int, sentido: int) -> None:
    """Mueve el final de la toma k al inicio de la oración siguiente (alargar) o anterior (acortar); la toma de
    al lado se corre igual, sin dejar huecos y sin cortar ninguna frase."""
    if k + 1 >= len(clips):
        raise ValueError("Es la última toma: su final es el final del video")
    x, sig = clips[k], clips[k + 1]
    limites = _limites(c)
    if sentido > 0:
        nuevo = next((b for b in limites if b > x["fin"] + 1e-3), None)
        if nuevo is None or sig["fin"] - nuevo < MINIMO_S or nuevo - x["inicio"] > 30.0:
            raise ValueError("No se puede alargar más sin dejar la toma siguiente demasiado corta")
    else:
        nuevo = next((b for b in reversed(limites) if b < x["fin"] - 1e-3), None)
        if nuevo is None or nuevo - x["inicio"] < MINIMO_S:
            raise ValueError("No se puede acortar más: quedaría de menos de dos segundos")
        if sig["fin"] - nuevo > 30.0:
            raise ValueError("La toma siguiente pasaría de 30 segundos")
    delta = round(nuevo - x["fin"], 3)
    x["fin"] = round(nuevo, 3)
    x["duracion"] = round(x["fin"] - x["inicio"], 3)
    sig["inicio"] = round(nuevo, 3)
    sig["duracion"] = round(sig["fin"] - sig["inicio"], 3)
    if sig["tipo"] in ("stock", "seminario"):
        sig["desde"] = round(max(0.0, sig["desde"] + delta), 3)


def _a_seminario(c: CarpetaProyecto, clips: list[dict], k: int, preset: dict, ffmpeg: str | None) -> None:
    from . import historial
    from .clips import _lugar, duracion_video

    x = clips[k]
    base = preset.get("clip_base")
    if not base or not Path(base).exists():
        raise ValueError("No encuentro el video del seminario")
    p = c.cargar()
    dur = x["fin"] - x["inicio"]
    ocupados = [(y["desde"], y["desde"] + y["fin"] - y["inicio"]) for y in clips
                if y["tipo"] == "seminario" and y["id"] != x["id"]]
    ocupados += historial.tramos_usados(p.canal, base, excluir=p.slug)
    rng = random.Random(f"{p.slug}|{x['id']}|{x['desde']}")
    inicio = _lugar(dur, duracion_video(base, ffmpeg or "ffmpeg"), ocupados, rng)
    if inicio is None:
        raise ValueError("El video del seminario no tiene un tramo libre de ese largo")
    x.update(tipo="seminario", archivo=base, desde=inicio)
    x.pop("pexels_id", None)


def _otro_stock(c: CarpetaProyecto, clips: list[dict], k: int, sesion) -> None:
    import requests

    from . import historial
    from .clips import buscar, consultas, descargar

    x = clips[k]
    p = c.cargar()
    excluir = historial.stock_usado(p.canal, excluir=p.slug) | {y.get("pexels_id") for y in clips if y.get("pexels_id")}
    dur = x["fin"] - x["inicio"]
    rng = random.Random(f"{p.slug}|{x['id']}|otro|{len(excluir)}")
    for q in consultas(x.get("keywords") or [], ""):
        opciones = [o for o in buscar(q, dur, excluir, sesion=sesion or requests) if o["duracion"] >= dur]
        if opciones:
            nuevo = rng.choice(opciones[:8])
            x.update(tipo="stock", archivo=str(descargar(nuevo, sesion=sesion or requests)), desde=0.0,
                     pexels_id=nuevo["pexels_id"])
            ruta = c.ruta / "stock_licencias.json"
            if ruta.exists():                       # el registro de licencias sigue al día
                lic = leer_json(ruta)
                lic["clips"].append({"segmento": x["id"], "pexels_id": nuevo["pexels_id"],
                                     "url_origen": nuevo["url_origen"], "autor": nuevo["autor"], "busqueda": q})
                escribir_json(ruta, lic)
            return
    raise ValueError("Pexels no tiene otro clip nuevo para esa toma")
