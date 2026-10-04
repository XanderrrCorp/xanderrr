"""API de El Calvo Explica (/api/explica).

- GET  /api/explica                 → ajustes del canal, costo de las 3 muestras, muestras hechas y avance.
- POST /api/explica/muestras        → genera las 3 ilustraciones de muestra (en segundo plano, con freno).
- GET  /api/explica/muestras/{arch} → una imagen de muestra.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import canal as C
from . import ilustraciones as I

rutas = APIRouter(prefix="/api/explica")
SLUG_MUESTRAS = "explica-muestras"


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
                         "error": t.error} if t else None)}


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
