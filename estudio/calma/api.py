"""API de Hazlo con Calma (/api/calma): el video de prueba animado desde la página.

- GET  /api/calma            → ajustes (voz, música, volumen), costo de la voz, avance y último informe.
- POST /api/calma/ajustes    → guarda el código de la voz, la velocidad, la música elegida a mano o el volumen.
- POST /api/calma/prueba     → arranca el video de prueba (voz → Whisper → escenas → render) en segundo plano.
- GET  /api/calma/video      → el MP4 terminado.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import leer_json
from . import flujo

rutas = APIRouter(prefix="/api/calma")
NOMBRE = "garrapata_60s"
SLUG = f"calma-{NOMBRE}"


def _musicas() -> list[dict]:
    try:
        from .. import biblioteca

        return [{"ruta": str(biblioteca.raiz() / a["archivo"]), "nombre": a.get("nombre_original") or a["archivo"],
                 "animo": a["tipo"]} for a in biblioteca.indice()
                if a["clase"] == "musica" and not a.get("revisar_licencia")]
    except Exception:  # noqa: BLE001
        return []


def _estado() -> dict:
    from .. import pipeline

    c = flujo.carpeta_base() / NOMBRE
    informe = leer_json(c / "informe.json") if (c / "informe.json").exists() else None
    t = pipeline.TRABAJOS.get(SLUG)
    trabajo = ({"paso": t.paso, "progreso": round(t.progreso, 3), "mensaje": t.mensaje, "activo": t.activo,
                "error": t.error, "registro": t.registro[-12:]} if t else None)
    return {"ajustes": flujo.ajustes(), "costo_voz": flujo.costo_estimado(NOMBRE), "musicas": _musicas(),
            "informe": informe, "trabajo": trabajo, "video": (c / "final.mp4").exists()}


@rutas.get("")
def ver():
    return _estado()


class Ajustes(BaseModel):
    voz_id: str | None = Field(None, max_length=200)
    velocidad: float | None = Field(None, ge=0.7, le=1.5)
    musica: str | None = None                  # "" = que la elija sola
    volumen_musica_db: float | None = Field(None, ge=-40, le=-10)


@rutas.post("/ajustes")
def ajustar(a: Ajustes):
    cambios = {k: v for k, v in a.model_dump().items() if v is not None}
    if "voz_id" in cambios:
        cambios["voz_id"] = cambios["voz_id"].strip() or None
    if "musica" in cambios:
        validas = {m["ruta"] for m in _musicas()}
        if cambios["musica"] and cambios["musica"] not in validas:
            raise HTTPException(400, "Esa música no está en la biblioteca con licencia")
        cambios["musica"] = cambios["musica"] or None
    flujo.guardar_ajustes(cambios)
    return _estado()


class Prueba(BaseModel):
    permiso: bool = False


@rutas.post("/prueba")
def prueba(p: Prueba = Prueba()):
    from .. import pipeline

    if not flujo.ajustes().get("voz_id"):
        raise HTTPException(400, "Primero pega el código de la voz de Hazlo con Calma (la de MiniMax)")
    c = flujo.preparar(NOMBRE)
    try:
        pipeline.lanzar(SLUG, "calma", lambda t: flujo.producir(c, t, permiso=p.permiso))
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _estado()


@rutas.get("/video")
def video():
    ruta = flujo.carpeta_base() / NOMBRE / "final.mp4"
    if not ruta.exists():
        raise HTTPException(404, "Todavía no hay video")
    return FileResponse(ruta, media_type="video/mp4")
