"""API de El Calvo Explica (/api/explica).

- GET  /api/explica                 → ajustes del canal, costo de las 3 muestras, muestras hechas y avance.
- POST /api/explica/muestras        → genera las 3 ilustraciones de muestra (en segundo plano, con freno).
- GET  /api/explica/muestras/{arch} → una imagen de muestra.
- POST /api/explica/tema-prueba     → el tema 1 del primer video con voz real (voz → Whisper → render).
- GET  /api/explica/tema-prueba/video → el MP4 del tema de prueba.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import canal as C
from . import flujo as F
from . import ilustraciones as I

rutas = APIRouter(prefix="/api/explica")
SLUG_MUESTRAS = "explica-muestras"
SLUG_TEMA = "explica-tema-prueba"
SLUG_VIDEO = "explica-video"
VIDEO = "partes_que_no_sirven"          # primer video: «Partes de tu cuerpo que YA NO SIRVEN para nada»


def _trabajo(slug: str):
    from .. import pipeline

    t = pipeline.TRABAJOS.get(slug)
    return ({"paso": t.paso, "progreso": round(t.progreso, 3), "mensaje": t.mensaje, "activo": t.activo,
             "error": t.error} if t else None)


def _estado() -> dict:
    from .. import pipeline

    t = pipeline.TRABAJOS.get(SLUG_MUESTRAS)
    try:
        costo = I.costo_muestras()
    except Exception as ex:  # noqa: BLE001 — sin clave igual se muestra la página
        costo = {"error": str(ex)}
    return {"canal": {"clave": C.CLAVE_CANAL, "nombre": C.NOMBRE_CANAL}, "ajustes": C.cargar(),
            "costo_muestras": costo, "muestras": I.estado_muestras(),
            "trabajo": ({"paso": t.paso, "progreso": round(t.progreso, 3), "mensaje": t.mensaje, "activo": t.activo,
                         "error": t.error} if t else None),
            "tema_prueba": {**F.estado(), "costo_voz": F.costo_voz(), "trabajo": _trabajo(SLUG_TEMA)},
            "video": {**F.estado(VIDEO), "costo_voz": F.costo_voz(VIDEO, VIDEO), "trabajo": _trabajo(SLUG_VIDEO),
                      "titulo": "Partes de tu cuerpo que YA NO SIRVEN para nada"}}


@rutas.get("")
def ver():
    return _estado()


class Permiso(BaseModel):
    permiso: bool = False


@rutas.post("/muestras")
def muestras(p: Permiso = Permiso()):
    from .. import pipeline

    try:
        pipeline.lanzar(SLUG_MUESTRAS, "muestras", lambda t: I.generar_muestras(t, permiso=p.permiso))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _estado()


@rutas.get("/muestras/{archivo}")
def muestra(archivo: str):
    if not re.fullmatch(r"[a-z_]+\.png", archivo):
        raise HTTPException(404)
    ruta = I.carpeta() / archivo
    if not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta, media_type="image/png")


@rutas.post("/tema-prueba")
def tema_prueba(p: Permiso = Permiso()):
    from .. import pipeline

    c = F.preparar()
    try:
        pipeline.lanzar(SLUG_TEMA, "tema", lambda t: F.producir(c, t, permiso=p.permiso))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _estado()


@rutas.get("/tema-prueba/video")
def tema_prueba_video():
    ruta = F.carpeta_base() / F.TEMA_PRUEBA / "final.mp4"
    if not ruta.exists():
        raise HTTPException(404, "Todavía no hay video")
    return FileResponse(ruta, media_type="video/mp4")


@rutas.post("/video")
def video_completo(p: Permiso = Permiso()):
    from .. import pipeline

    c = F.preparar(VIDEO, VIDEO)
    try:
        pipeline.lanzar(SLUG_VIDEO, "video", lambda t: F.producir(c, t, permiso=p.permiso))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _estado()


@rutas.get("/video/archivo")
def video_archivo():
    ruta = F.carpeta_base() / VIDEO / "final.mp4"
    if not ruta.exists():
        raise HTTPException(404, "Todavía no hay video")
    return FileResponse(ruta, media_type="video/mp4")
