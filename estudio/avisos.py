"""Avisos para el usuario (Bloque 1, 21-10): «tu video está listo» o «no se pudo terminar», dentro de la app y por
correo, y el estado de la última copia de seguridad que se hizo antes de actualizar la base.

Los avisos viven en datos/avisos.json (los últimos 50). Un trabajo terminó un video si dejó un .mp4 nuevo en la
carpeta Videos/Xandart (las 4 entregas copian ahí el final).
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

MAXIMO = 50
_CERROJO = threading.Lock()
# trabajos que no son de un video (personajes «personaje~id», miniaturas «slug~miniatura», muestras de Google):
# sus errores ya se ven en su propia pantalla
SIN_AVISO = ("explica-muestras",)


def _ruta() -> Path:
    from .plataforma.db import carpeta_datos

    return carpeta_datos() / "avisos.json"


def listar() -> list[dict]:
    r = _ruta()
    try:
        return json.loads(r.read_text(encoding="utf-8")) if r.exists() else []
    except (OSError, ValueError):
        return []


def registrar(tipo: str, titulo: str, texto: str, enlace: str | None = None) -> dict:
    a = {"id": uuid.uuid4().hex[:12], "tipo": tipo, "titulo": titulo, "texto": texto, "enlace": enlace,
         "fecha": time.time(), "leido": False}
    with _CERROJO:
        todos = ([a] + listar())[:MAXIMO]
        _ruta().parent.mkdir(parents=True, exist_ok=True)
        _ruta().write_text(json.dumps(todos, ensure_ascii=False), encoding="utf-8")
    return a


def marcar_leidos() -> None:
    with _CERROJO:
        todos = [{**a, "leido": True} for a in listar()]
        if todos:
            _ruta().write_text(json.dumps(todos, ensure_ascii=False), encoding="utf-8")


def _titulo_y_enlace(slug: str) -> tuple[str, str]:
    from .config import ruta_proyectos

    if slug.startswith("explica-"):
        return slug.removeprefix("explica-").replace("-", " ").capitalize(), "/app/explica"
    p = ruta_proyectos() / slug / "proyecto.json"
    try:
        titulo = json.loads(p.read_text(encoding="utf-8")).get("titulo") or slug
    except (OSError, ValueError):
        titulo = slug.replace("-", " ").capitalize()
    return titulo, f"/app/videos/{slug}"


def _video_nuevo(desde: float) -> Path | None:
    from .pipeline import carpeta_videos

    try:
        nuevos = [f for f in carpeta_videos().glob("*.mp4") if f.stat().st_mtime >= desde - 1]
    except OSError:
        return None
    return max(nuevos, key=lambda f: f.stat().st_mtime, default=None)


def al_terminar(slug: str, trabajo, correo_a=None) -> dict | None:
    """Lo llama pipeline.lanzar al terminar cualquier trabajo. Avisa si salió un video nuevo o si un video falló."""
    if "~" in slug or slug in SIN_AVISO:
        return None
    titulo, enlace = _titulo_y_enlace(slug)
    if trabajo.error:
        a = registrar("error", f"No se pudo terminar «{titulo}»",
                      "Algo falló a mitad de camino. Ábrelo y dale «Intentar otra vez»: lo que ya estaba hecho no se "
                      "vuelve a pagar.", enlace)
    else:
        video = _video_nuevo(trabajo.inicio)
        if video is None:
            return None
        a = registrar("listo", f"Tu video «{titulo}» está listo",
                      f"Quedó guardado en tu carpeta de videos: {video}", enlace)
    _correo(a, correo_a)
    return a


def _correo(a: dict, para: str | None = None) -> None:
    """Por correo, en segundo plano (si el correo está configurado en Ajustes); nunca frena nada."""
    def enviar():
        try:
            from .plataforma import correo

            destino = para or correo.para_avisos(_email_dueno())
            if destino:
                correo.enviar(destino, a["titulo"], f"{a['texto']}\n\nÁbrelo en Xandart: http://localhost:8031{a['enlace'] or '/app'}")
        except Exception:  # noqa: BLE001 — sin internet o sin correo: el aviso igual queda en la app
            pass
    threading.Thread(target=enviar, daemon=True).start()


def _email_dueno() -> str | None:
    try:
        from sqlalchemy import select

        from .plataforma import db
        from .plataforma.modelos import ROL_OWNER, Usuario

        with db.sesion() as s:
            u = s.scalar(select(Usuario).where(Usuario.rol == ROL_OWNER).order_by(Usuario.creado))
            return u.email if u else None
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ copia de seguridad antes de actualizar la base

def respaldo() -> dict:
    """Estado de la última copia hecha antes de actualizar la base (la anota plataforma/db.py)."""
    from .plataforma.db import carpeta_datos

    r = carpeta_datos() / "ultima_copia_migracion.json"
    if not r.exists():
        return {"estado": "ninguna"}
    try:
        d = json.loads(r.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"estado": "ninguna"}
    estado = "error" if d.get("error") else "ok"
    if estado == "ok" and d.get("carpeta") and not Path(d["carpeta"]).exists():
        estado = "movida"
    return {**d, "estado": estado}


def respaldo_visto() -> None:
    from .plataforma.db import carpeta_datos

    r = carpeta_datos() / "ultima_copia_migracion.json"
    if r.exists():
        d = json.loads(r.read_text(encoding="utf-8"))
        d["visto"] = True
        r.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


# ------------------------------------------------------------------ «Reportar problema»

def reportar(texto: str, ruta: str = "", error: str = "", navegador: str = "") -> dict:
    """Guarda el reporte con lo que hace falta para entender el fallo (la pantalla, el último error y los trabajos
    que fallaron) y se lo manda al dueño por correo. Nunca incluye claves ni el .env."""
    from datetime import datetime

    from .plataforma.db import carpeta_datos
    from . import pipeline

    trabajos = [{"trabajo": k, "paso": t.paso, "error": t.error, "ultimos": t.registro[-6:]}
                for k, t in list(pipeline.TRABAJOS.items()) if t.error][-5:]
    try:
        from .app import VERSION
    except Exception:  # noqa: BLE001
        VERSION = "?"
    rep = {"fecha": datetime.now().isoformat(timespec="seconds"), "texto": texto.strip()[:3000], "pantalla": ruta[:300],
           "error_en_pantalla": error[:1500], "navegador": navegador[:300], "version": VERSION, "trabajos_con_error": trabajos}
    d = carpeta_datos() / "reportes"
    d.mkdir(parents=True, exist_ok=True)
    archivo = d / f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:6]}.json"
    archivo.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    _correo({"titulo": "Xandart: nuevo reporte de un problema", "enlace": "/app",
             "texto": json.dumps(rep, ensure_ascii=False, indent=2)[:6000]})
    return {"guardado": str(archivo)}
