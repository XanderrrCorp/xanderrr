"""API del modo Tracy (/api/tracy): todo desde la página, sin terminal.

- GET  /api/tracy           → ajustes del canal (clip base, música, voz, proporción) y si los archivos están.
- POST /api/tracy/ajustes   → cambia rutas o proporción.
- POST /api/tracy/archivo   → sube el video del seminario o la canción (quedan en datos/tracy).
- POST /api/tracy/videos    → guion pegado → video completo en segundo plano (voz, Whisper, plan,
                              clips, ensamblaje). El avance se ve como el de cualquier video.
- POST /api/tracy/videos/{slug}/seguir → reanuda un video que se cortó (lo pagado no se repite).
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .preset import CLAVE_CANAL, EXT_AUDIO, EXT_VIDEO, cargar_preset, crear_canal_tracy, encontrar

rutas = APIRouter(prefix="/api/tracy")


def _estado(clave: str = CLAVE_CANAL) -> dict:
    p = cargar_preset(clave)
    clip, musica = encontrar(p["clip_base"], EXT_VIDEO), encontrar(p.get("musica"), EXT_AUDIO)
    return {"canal": clave, "clip_base": clip or p["clip_base"], "clip_existe": bool(clip),
            "musica": musica or p.get("musica") or "", "musica_existe": bool(musica),
            "proporcion_seminario": p["proporcion_seminario"], "voz_id": p.get("voz_id"),
            "volumen_musica_db": p.get("volumen_musica_db"), "whisper": _whisper_instalado()}


def _whisper_instalado() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:  # noqa: BLE001
        return False


@rutas.get("")
def ver():
    return _estado()


class Ajustes(BaseModel):
    clip_base: str | None = None
    musica: str | None = None
    proporcion_seminario: float | None = Field(None, ge=0, le=1)


def _limpiar_ruta(r: str | None) -> str | None:
    if r is None:
        return None
    return r.strip().strip('"').strip("'")


@rutas.post("/ajustes")
def ajustar(a: Ajustes):
    try:
        crear_canal_tracy(clip_base=_limpiar_ruta(a.clip_base), musica=_limpiar_ruta(a.musica),
                          proporcion_seminario=a.proporcion_seminario)
    except (RuntimeError, ValueError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return _estado()


def carpeta_archivos() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "tracy"
    c.mkdir(parents=True, exist_ok=True)
    return c


@rutas.post("/archivo")
def subir(que: str = Form(...), archivo: UploadFile = File(...)):
    """que = «seminario» | «musica». Se copia por partes (un video largo no se carga entero en memoria)."""
    nombre = Path(archivo.filename or "archivo").name
    ext = Path(nombre).suffix.lower()
    if que == "seminario" and ext not in EXT_VIDEO:
        raise HTTPException(400, "El seminario tiene que ser un video (.mp4, .mov…)")
    if que == "musica" and ext not in EXT_AUDIO:
        raise HTTPException(400, "La música tiene que ser un audio (.mp3, .m4a, .wav…)")
    if que not in ("seminario", "musica"):
        raise HTTPException(400, "archivo desconocido")
    base = re.sub(r"[^\w.\- ]", "_", Path(nombre).stem)[:60] or que
    destino = carpeta_archivos() / f"{que}_{base}{ext}"
    tmp = destino.with_suffix(destino.suffix + ".part")
    with open(tmp, "wb") as f:
        shutil.copyfileobj(archivo.file, f, 1 << 20)
    os.replace(tmp, destino)
    cambio = {"clip_base": str(destino)} if que == "seminario" else {"musica": str(destino)}
    try:
        crear_canal_tracy(**cambio)
    except RuntimeError as ex:
        raise HTTPException(400, str(ex)) from ex
    return _estado()


class NuevoTracy(BaseModel):
    guion: str = Field(min_length=40)
    titulo: str = ""
    permiso: bool = False


def _lanzar(c, permiso: bool = False):
    from .. import pipeline
    from .flujo import producir

    try:
        pipeline.lanzar(c.ruta.name, "tracy", lambda t: producir(c, t, permiso=permiso))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return pipeline.resumen(c)


@rutas.post("/videos")
def nuevo(n: NuevoTracy):
    from .flujo import crear_proyecto

    try:
        crear_canal_tracy()                    # deja el canal listo la primera vez (sin cambiar lo guardado)
    except RuntimeError as ex:
        raise HTTPException(400, str(ex)) from ex
    est = _estado()
    if not est["whisper"]:
        raise HTTPException(400, "Falta Whisper (para los tiempos de la voz). Vuelve a correr «Instalar Xandart "
                                 "Nueva» y queda listo.")
    c = crear_proyecto(n.guion.strip(), canal=CLAVE_CANAL, titulo=n.titulo.strip() or None)
    return _lanzar(c, n.permiso)


class Seguir(BaseModel):
    permiso: bool = False


@rutas.post("/videos/{slug}/seguir")
def seguir(slug: str, s: Seguir = Seguir()):
    from ..proyecto import CarpetaProyecto

    try:
        c = CarpetaProyecto.abrir(slug)
    except FileNotFoundError as ex:
        raise HTTPException(404) from ex
    if c.cargar().visual_mode != "stock":
        raise HTTPException(400, "Ese video no es del modo Tracy")
    return _lanzar(c, s.permiso)
