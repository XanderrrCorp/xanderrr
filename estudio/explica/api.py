"""API de El Calvo Explica (/api/explica).

- GET  /api/explica                 → ajustes del canal, costo de las 3 muestras, muestras hechas y avance.
- POST /api/explica/muestras        → genera las 3 ilustraciones de muestra (en segundo plano, con freno).
- GET  /api/explica/muestras/{arch} → una imagen de muestra.
- POST /api/explica/tema-prueba     → el tema 1 del primer video con voz real (voz → Whisper → render).
- GET  /api/explica/tema-prueba/video → el MP4 del tema de prueba.
"""
from __future__ import annotations

import json

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


# ------------------------------------------------------------------ videos nuevos hechos por Xandart sola

class NuevoVideo(BaseModel):
    titulo: str
    temas: int = 9
    datos: str = ""


def _carpeta_video(slug: str):
    if not re.fullmatch(r"[a-z0-9-]{1,60}", slug):
        raise HTTPException(404)
    return F.carpeta_base() / "videos" / slug


def _estado_video(slug: str) -> dict:
    from . import autor

    c = _carpeta_video(slug)
    if not c.exists():
        raise HTTPException(404, "No existe ese video")
    info = (c / "video.json")
    meta = json.loads(info.read_text(encoding="utf-8")) if info.exists() else {"titulo": slug}
    return {"slug": slug, **meta, **autor.estado_video(c), "trabajo": _trabajo(f"explica-{slug}"),
            "costo_voz": _costo_voz(c)}


def _costo_voz(c) -> dict | None:
    if not (c / "guion.txt").exists():
        return None
    from ..config import ConfigCostos
    from ..costos import formato_cop
    from . import guion as G

    try:
        texto = G.texto_para_voz(G.leer((c / "guion.txt").read_text(encoding="utf-8")))
    except ValueError:
        return None
    config = ConfigCostos.cargar()
    usd = len(texto) / 1000 * config.precio("tts_por_1000_caracteres")
    return {"caracteres": len(texto), "cop": formato_cop(config.a_cop(usd))}


@rutas.get("/videos")
def videos():
    base = F.carpeta_base() / "videos"
    salida = []
    for d in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True) if base.exists() else []:
        if (d / "video.json").exists():
            salida.append({"slug": d.name, **json.loads((d / "video.json").read_text(encoding="utf-8"))})
    return salida


def _lanzar(slug: str, funcion):
    from .. import pipeline

    try:
        pipeline.lanzar(f"explica-{slug}", "explica", funcion)
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _estado_video(slug)


@rutas.post("/videos")
def nuevo_video(n: NuevoVideo):
    from ..proyecto import slugificar
    from . import autor

    titulo = n.titulo.strip()
    if len(titulo) < 4:
        raise HTTPException(400, "Escribe el tema del video")
    if not 3 <= n.temas <= 15:
        raise HTTPException(400, "Entre 3 y 15 temas")
    base = slugificar(titulo)[:50] or "video"
    slug, k = base, 2
    while (F.carpeta_base() / "videos" / slug).exists():
        slug, k = f"{base}-{k}", k + 1
    c = F.carpeta_base() / "videos" / slug
    c.mkdir(parents=True)
    (c / "video.json").write_text(json.dumps({"titulo": titulo, "temas": n.temas}, ensure_ascii=False), encoding="utf-8")
    return _lanzar(slug, lambda t: autor.escribir_guion(c, titulo, n.temas, n.datos, avisar=t.avisar))


@rutas.get("/videos/{slug}")
def ver_video(slug: str):
    return _estado_video(slug)


class Guion(BaseModel):
    texto: str


@rutas.put("/videos/{slug}/guion")
def guardar_guion(slug: str, g: Guion):
    """El dueño cambió algo del guion a mano: se guarda y se revisa (las escenas hay que volver a armarlas)."""
    from . import guion as G

    c = _carpeta_video(slug)
    try:
        temas = G.leer(g.texto)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    (c / "guion.txt").write_text(g.texto.strip() + "\n", encoding="utf-8")
    (c / "guion_info.json").write_text(json.dumps({"avisos": G.revisar(temas), "editado": True}, ensure_ascii=False),
                                       encoding="utf-8")
    return _estado_video(slug)


@rutas.post("/videos/{slug}/escenas")
def armar(slug: str):
    from . import autor

    c = _carpeta_video(slug)
    if not (c / "guion.txt").exists():
        raise HTTPException(400, "Primero el guion")
    return _lanzar(slug, lambda t: autor.armar_escenas(c, avisar=t.avisar))


@rutas.post("/videos/{slug}/video")
def hacer(slug: str, p: Permiso = Permiso()):
    from ..calma.flujo import Carpeta

    c = _carpeta_video(slug)
    if not (c / "escenas.json").exists():
        raise HTTPException(400, "Primero arma las escenas")
    return _lanzar(slug, lambda t: F.producir(Carpeta(c), t, permiso=p.permiso))


@rutas.get("/videos/{slug}/hoja/{archivo}")
def hoja(slug: str, archivo: str):
    if not re.fullmatch(r"tema_\d{2}\.png", archivo):
        raise HTTPException(404)
    ruta = _carpeta_video(slug) / "revision" / archivo
    if not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta, media_type="image/png")


@rutas.get("/videos/{slug}/archivo")
def archivo_video(slug: str):
    ruta = _carpeta_video(slug) / "final.mp4"
    if not ruta.exists():
        raise HTTPException(404, "Todavía no hay video")
    return FileResponse(ruta, media_type="video/mp4")
