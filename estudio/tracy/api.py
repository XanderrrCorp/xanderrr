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

from .preset import CLAVE_CANAL, EXT_AUDIO, EXT_IMAGEN, EXT_VIDEO, cargar_preset, crear_canal_tracy, encontrar

rutas = APIRouter(prefix="/api/tracy")


def _estado(clave: str = CLAVE_CANAL) -> dict:
    p = cargar_preset(clave)
    clip, musica = encontrar(p["clip_base"], EXT_VIDEO), encontrar(p.get("musica"), EXT_AUDIO)
    presentador = encontrar(p.get("presentador"), EXT_IMAGEN)
    return {"canal": clave, "clip_base": clip or p["clip_base"], "clip_existe": bool(clip),
            "musica": musica or p.get("musica") or "", "musica_existe": bool(musica),
            "presentador": presentador or p.get("presentador") or "", "presentador_existe": bool(presentador),
            "escena_final_desde": p["escena_final_desde"],
            "proporcion_seminario": p["proporcion_seminario"], "voz_id": p.get("voz_id"),
            "volumen_musica_db": p.get("volumen_musica_db"), "velocidad": p.get("velocidad"),
            "seminario_s": p.get("seminario_s"), "barras_cine": p.get("barras_cine"), "whisper": _whisper_instalado(),
            "humano": p["humano"]}


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
    escena_final_desde: float | None = Field(None, ge=0.05, le=1)
    velocidad: float | None = Field(None, ge=0.7, le=1.5)
    seminario_s: float | None = Field(None, ge=3, le=12)
    barras_cine: bool | None = None
    volumen_musica_db: float | None = Field(None, ge=-40, le=0)


def _limpiar_ruta(r: str | None) -> str | None:
    if r is None:
        return None
    return r.strip().strip('"').strip("'")


@rutas.post("/ajustes")
def ajustar(a: Ajustes):
    try:
        crear_canal_tracy(clip_base=_limpiar_ruta(a.clip_base), musica=_limpiar_ruta(a.musica),
                          proporcion_seminario=a.proporcion_seminario, escena_final_desde=a.escena_final_desde,
                          velocidad=a.velocidad, volumen_musica_db=a.volumen_musica_db,
                          seminario_s=a.seminario_s, barras_cine=a.barras_cine)
    except (RuntimeError, ValueError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return _estado()


class Humano(BaseModel):
    """(01-11) Ajustes de la «Edición humana» (solo lo que llega se cambia)."""
    activo: bool | None = None
    fenix_max: float | None = Field(None, ge=0, le=0.6)
    revisar_antes: bool | None = None
    escena_final_desde: float | None = Field(None, ge=0.05, le=1)
    carpeta_musica: str | None = None
    velocidad_cierre: float | None = Field(None, ge=0.85, le=1)
    suaves: float | None = Field(None, ge=0, le=0.5)
    color_calido: bool | None = None


@rutas.post("/humano")
def ajustar_humano(h: Humano):
    actual = dict(cargar_preset(CLAVE_CANAL)["humano"])
    cambios = {k: v for k, v in h.model_dump().items() if v is not None}
    if "carpeta_musica" in cambios:
        cambios["carpeta_musica"] = _limpiar_ruta(cambios["carpeta_musica"]) or ""
    try:
        crear_canal_tracy(humano={**actual, **cambios})
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
    """que = «seminario» | «musica» | «presentador». Se copia por partes (un video largo no se carga
    entero en memoria)."""
    nombre = Path(archivo.filename or "archivo").name
    ext = Path(nombre).suffix.lower()
    if que == "seminario" and ext not in EXT_VIDEO:
        raise HTTPException(400, "El seminario tiene que ser un video (.mp4, .mov…)")
    if que == "musica" and ext not in EXT_AUDIO:
        raise HTTPException(400, "La música tiene que ser un audio (.mp3, .m4a, .wav…)")
    if que == "presentador" and ext not in EXT_IMAGEN:
        raise HTTPException(400, "El presentador tiene que ser una imagen (.png sin fondo es lo mejor)")
    if que not in ("seminario", "musica", "presentador"):
        raise HTTPException(400, "archivo desconocido")
    base = re.sub(r"[^\w.\- ]", "_", Path(nombre).stem)[:60] or que
    destino = carpeta_archivos() / f"{que}_{base}{ext}"
    tmp = destino.with_suffix(destino.suffix + ".part")
    with open(tmp, "wb") as f:
        shutil.copyfileobj(archivo.file, f, 1 << 20)
    os.replace(tmp, destino)
    cambio = {"seminario": {"clip_base": str(destino)}, "musica": {"musica": str(destino)},
              "presentador": {"presentador": str(destino)}}[que]
    try:
        crear_canal_tracy(**cambio)
    except RuntimeError as ex:
        raise HTTPException(400, str(ex)) from ex
    return _estado()


class NuevoTracy(BaseModel):
    guion: str = Field(min_length=40)
    titulo: str = ""
    permiso: bool = False
    prueba: bool = False            # (01-11) «Probar 3 minutos»: solo el comienzo del guion


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
    prueba = cargar_preset(CLAVE_CANAL)["humano"]["prueba_s"] if n.prueba else None
    c = crear_proyecto(n.guion.strip(), canal=CLAVE_CANAL, titulo=n.titulo.strip() or None, prueba_s=prueba)
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


# ------------------------------------------------------------------ (01-11) revisión antes de exportar

def _abrir(slug: str):
    from ..proyecto import CarpetaProyecto

    try:
        c = CarpetaProyecto.abrir(slug)
    except FileNotFoundError as ex:
        raise HTTPException(404) from ex
    if c.cargar().visual_mode != "stock":
        raise HTTPException(400, "Ese video no es del modo Tracy")
    return c


@rutas.get("/videos/{slug}/revision")
def ver_revision(slug: str):
    from ..pipeline import ffmpeg
    from .revision import ver

    c = _abrir(slug)
    if not (c.ruta / "clips.json").exists():
        return {"pendiente": False, "clips": [], "reporte": None}
    return ver(c, ffmpeg())


class Cambio(BaseModel):
    accion: str
    texto: str | None = None


@rutas.post("/videos/{slug}/revision/{clip_id}")
def cambiar_toma(slug: str, clip_id: int, cambio: Cambio):
    from ..pipeline import TRABAJOS, ffmpeg
    from .preset import EXT_VIDEO
    from .revision import cambiar

    c = _abrir(slug)
    t = TRABAJOS.get(c.ruta.name)
    if t is not None and t.activo:
        raise HTTPException(409, "Espera a que termine lo que está haciendo")
    preset = cargar_preset(c.cargar().canal)
    preset["clip_base"] = encontrar(preset["clip_base"], EXT_VIDEO) or preset["clip_base"]
    try:
        return cambiar(c, clip_id, cambio.accion, cambio.texto, preset=preset, ffmpeg=ffmpeg())
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex


@rutas.post("/videos/{slug}/exportar")
def exportar_video(slug: str):
    from .. import pipeline
    from .flujo import exportar_y_entregar

    c = _abrir(slug)
    try:
        pipeline.lanzar(c.ruta.name, "tracy", lambda t: exportar_y_entregar(c, t))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return pipeline.resumen(c)
