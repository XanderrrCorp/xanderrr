"""API de Código del Éxito híbrido (/api/codigo-exito), solo para el dueño (página /codigo-exito, «Tu estudio»).

- GET  /api/codigo-exito                  → qué falta en este PC (capas del Profesor, efectos, música, Node, Pexels) y
                                            la lista de videos
- POST /api/codigo-exito/videos           → {titulo, guion} guion etiquetado → carpeta del video + costo de la voz
- GET  /api/codigo-exito/videos/{slug}    → estado, avance, bloques, capítulos y créditos de Pexels
- POST /api/codigo-exito/videos/{slug}/hacer {permiso} → arma el video en segundo plano (lo hecho no se repite)
- GET  /api/codigo-exito/videos/{slug}/final.mp4
- POST /api/codigo-exito/abrir {que: recursos|videos} → abre la carpeta en el Explorador
El video final se copia también a Videos/Xandart (como los demás), con sus capítulos al lado.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

rutas = APIRouter(prefix="/api/codigo-exito")
_TRABAJOS: dict[str, threading.Thread] = {}


def carpeta_videos_ce() -> Path:
    from ..config import ruta_proyectos

    c = ruta_proyectos() / "codigo_exito"
    c.mkdir(parents=True, exist_ok=True)
    return c


def carpeta_recursos() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "codigo_exito"
    for sub in ("profesor", "sfx", "musica"):
        (c / sub).mkdir(parents=True, exist_ok=True)
    return c


def _faltan() -> dict:
    from ..config import clave_api
    from .profesor import carpeta_capas

    r = carpeta_recursos()
    return {"carpeta": str(r), "profesor": (carpeta_capas() / "cabeza_base.png").exists(),
            "efectos": any((r / "sfx").glob("*.wav")), "musica": len([p for p in (r / "musica").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")]),
            "node": bool(shutil.which("node")), "pexels": bool(clave_api("PEXELS_API_KEY")),
            "rhubarb": bool(_rhubarb())}


def _rhubarb() -> str | None:
    """Rhubarb: variable RHUBARB (entorno o .env de Xandart), en el PATH o en datos/codigo_exito/rhubarb"""
    from ..config import clave_api

    r = os.environ.get("RHUBARB") or clave_api("RHUBARB") or shutil.which("rhubarb")
    if not r:
        hallado = next(iter(carpeta_recursos().glob("rhubarb/**/rhubarb.exe")), None) or next(iter(carpeta_recursos().glob("rhubarb/**/rhubarb")), None)
        r = str(hallado) if hallado else None
    if r:
        os.environ["RHUBARB"] = r
    return r


def _estado(carpeta: Path) -> dict:
    ruta = carpeta / "estado.json"
    return json.loads(ruta.read_text("utf-8")) if ruta.exists() else {"estado": "nuevo", "log": []}


def _guardar_estado(carpeta: Path, **cambios) -> dict:
    e = _estado(carpeta)
    e.update(cambios)
    (carpeta / "estado.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), "utf-8")
    return e


def _costo(guion: str) -> dict:
    from ..config import ConfigCostos, formato_cop
    from .guion import leer

    bloques = leer(guion)
    letras = sum(len(b["texto"]) for b in bloques)
    c = ConfigCostos.cargar()
    usd = letras / 1000 * c.precio("tts_por_1000_caracteres")
    minutos = sum(len(b["texto"].split()) for b in bloques) / (2.9 * 1.15) / 60
    return {"bloques": len(bloques), "partes": len({b["parte"] for b in bloques}), "letras": letras,
            "minutos": round(minutos, 1), "costo_voz": formato_cop(c.a_cop(usd)),
            "por_tipo": {t: sum(1 for b in bloques if b["tipo"] == t) for t in ("profesor", "stock", "aura")}}


def _video(slug: str) -> Path:
    c = carpeta_videos_ce() / slug
    if not (c / "guion.txt").exists():
        raise HTTPException(404, "Ese video no existe")
    return c


def _resumen(c: Path) -> dict:
    meta = json.loads((c / "video.json").read_text("utf-8")) if (c / "video.json").exists() else {}
    e = _estado(c)
    return {"slug": c.name, "titulo": meta.get("titulo") or c.name, "estado": e.get("estado"), "mensaje": (e.get("log") or [""])[-1],
            "final": (c / "final.mp4").exists()}


@rutas.get("")
def estado():
    videos = sorted((p for p in carpeta_videos_ce().iterdir() if (p / "guion.txt").exists()), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"faltan": _faltan(), "videos": [_resumen(v) for v in videos]}


class NuevoVideo(BaseModel):
    titulo: str = Field(min_length=3, max_length=120)
    guion: str = Field(min_length=40)


@rutas.post("/videos")
def crear(d: NuevoVideo):
    from ..proyecto import slugificar

    try:
        costo = _costo(d.guion)
    except ValueError as ex:
        raise HTTPException(422, f"El guion no se pudo leer: {ex}") from ex
    base = slugificar(d.titulo)
    slug, k = base, 2
    while (carpeta_videos_ce() / slug).exists():
        slug, k = f"{base}-{k}", k + 1
    c = carpeta_videos_ce() / slug
    c.mkdir(parents=True)
    (c / "guion.txt").write_text(d.guion.strip() + "\n", "utf-8")
    (c / "video.json").write_text(json.dumps({"titulo": d.titulo, "creado": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False), "utf-8")
    _guardar_estado(c, estado="nuevo", log=["Guion guardado. Revisa el costo y dale «Hacer el video»."])
    return {**_resumen(c), "costo": costo}


@rutas.get("/videos/{slug}")
def ver(slug: str):
    c = _video(slug)
    leer = lambda n: (c / n).read_text("utf-8") if (c / n).exists() else ""  # noqa: E731
    return {**_resumen(c), "costo": _costo((c / "guion.txt").read_text("utf-8")), "log": _estado(c).get("log", [])[-40:],
            "error": _estado(c).get("error"), "capitulos": leer("capitulos.txt"), "bloques_txt": leer("bloques.txt"),
            "creditos": leer("creditos_pexels.txt"), "trabajando": slug in _TRABAJOS and _TRABAJOS[slug].is_alive()}


class Hacer(BaseModel):
    permiso: bool = False


def _correr(c: Path, permiso: bool) -> None:
    from ..limpieza import copiar_o_enlazar
    from ..pipeline import carpeta_videos
    from .armar import hacer

    def avisar(txt: str) -> None:
        e = _estado(c)
        log = (e.get("log") or []) + [str(txt).strip()]
        _guardar_estado(c, log=log[-200:])

    r = carpeta_recursos()
    musica = r / "musica" if any((r / "musica").glob("*")) else None
    os.environ.setdefault("CODIGO_EXITO_SFX", str(r / "sfx"))
    _rhubarb()
    try:
        _guardar_estado(c, estado="haciendo", error=None)
        final = hacer(c / "guion.txt", c, permiso=permiso, avisar=avisar, carpeta_musica=musica)
        titulo = json.loads((c / "video.json").read_text("utf-8")).get("titulo") or c.name
        from ..proyecto import slugificar

        destino = carpeta_videos() / f"{slugificar(titulo)[:60]}.mp4"
        copiar_o_enlazar(final, destino)
        for n in ("capitulos.txt", "creditos_pexels.txt"):
            if (c / n).exists():
                shutil.copy(c / n, destino.with_name(destino.stem + "_" + n))
        avisar(f"Video listo en {destino}")
        _guardar_estado(c, estado="listo")
    except PermissionError as ex:
        _guardar_estado(c, estado="nuevo", error=str(ex))
    except Exception as ex:  # noqa: BLE001 — se muestra en la página; lo hecho queda guardado y se retoma
        avisar(f"Se detuvo: {str(ex)[:300]}")
        _guardar_estado(c, estado="error", error=str(ex)[:500])


@rutas.post("/videos/{slug}/hacer")
def hacer_video(slug: str, d: Hacer):
    c = _video(slug)
    if slug in _TRABAJOS and _TRABAJOS[slug].is_alive():
        raise HTTPException(409, "Ese video ya se está haciendo")
    hilo = threading.Thread(target=_correr, args=(c, d.permiso), daemon=True, name=f"codigo-exito-{slug}")
    _TRABAJOS[slug] = hilo
    hilo.start()
    return ver(slug)


@rutas.get("/videos/{slug}/final.mp4")
def final(slug: str):
    c = _video(slug)
    if not (c / "final.mp4").exists():
        raise HTTPException(404, "Todavía no está el video")
    return FileResponse(c / "final.mp4", media_type="video/mp4")


class Abrir(BaseModel):
    que: str = "recursos"


@rutas.post("/abrir")
def abrir(d: Abrir):
    from ..pipeline import carpeta_videos

    destino = carpeta_recursos() if d.que == "recursos" else carpeta_videos()
    if os.name == "nt":
        os.startfile(destino)  # type: ignore[attr-defined]
    return {"carpeta": str(destino)}
