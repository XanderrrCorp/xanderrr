"""Motor de base de datos y sesiones.

SQLite en el PC (archivo datos/xandart.db, fuera del código: el instalador no lo toca).
Para la nube basta con poner XANDART_DB=postgresql+psycopg://… : el resto no cambia.
El esquema se versiona con Alembic (carpeta migraciones/): nunca se edita a mano.
"""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..config import RAIZ


class Base(DeclarativeBase):
    pass


def carpeta_datos() -> Path:
    return Path(os.environ.get("XANDART_DATOS") or RAIZ / "datos")


def url() -> str:
    return os.environ.get("XANDART_DB") or f"sqlite:///{(carpeta_datos() / 'xandart.db').as_posix()}"


_MOTORES: dict[str, object] = {}


def motor():
    u = url()
    if u not in _MOTORES:
        if u.startswith("sqlite:///"):
            Path(u.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        m = create_engine(u, future=True)
        if u.startswith("sqlite"):
            @event.listens_for(m, "connect")
            def _pragmas(con, _):                     # claves foráneas y escrituras seguras en SQLite
                cur = con.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.execute("PRAGMA journal_mode=WAL")
                cur.close()
        _MOTORES[u] = m
    return _MOTORES[u]


def fabrica() -> sessionmaker:
    return sessionmaker(bind=motor(), expire_on_commit=False, future=True)


@contextmanager
def sesion() -> Session:
    s = fabrica()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


_PREPARADAS: set[str] = set()
# (22-10) mientras se hace la copia y se actualiza la base, la página lo muestra (avisos.respaldo) en vez de quedarse vacía
PREPARANDO: dict = {}
_CERROJO_MIGRAR = threading.Lock()


def preparar() -> None:
    """Deja la base al día (migraciones de Alembic), una sola vez por base y proceso.
    Alembic no aguanta dos migraciones a la vez en el mismo proceso: van en fila."""
    from alembic import command
    from alembic.config import Config

    from . import modelos  # noqa: F401 — registra las tablas

    direccion = url()
    if direccion in _PREPARADAS:
        return
    with _CERROJO_MIGRAR:
        if direccion in _PREPARADAS:
            return
        motor()                                   # crea la carpeta de datos si hace falta
        cfg = Config()
        cfg.set_main_option("script_location", str(Path(__file__).with_name("migraciones")))
        cfg.set_main_option("sqlalchemy.url", direccion)
        pendiente = _pendiente(cfg, direccion)
        if pendiente:
            # regla del dueño: antes de cambiar la estructura de una base con datos, copia de seguridad LIVIANA
            # (22-10: base, configuración, estilos, personajes, voces, plantillas, módulos privados y .env; sin videos
            # ni audios de proyectos). Si la copia falla, no se migra.
            import json

            from .copias import hacer_copia

            from .copias import CopiaFallida

            import time

            nota = carpeta_datos() / "ultima_copia_migracion.json"
            PREPARANDO.update(fase="copiando", desde=time.time(), migracion=pendiente)
            try:
                info = hacer_copia(f"antes_de_migrar_{pendiente}", liviano=True)
            except CopiaFallida as ex:      # se avisa al abrir Xandart (avisos.respaldo) y NO se migra
                PREPARANDO.clear()
                nota.write_text(json.dumps({"error": str(ex), "migracion": pendiente}, ensure_ascii=False, indent=2),
                                encoding="utf-8")
                raise
            PREPARANDO.update(fase="actualizando")
            nota.write_text(
                json.dumps({"carpeta": info["carpeta"], "fecha": info["fecha"], "migracion": pendiente,
                            "total_bytes": info["total_bytes"], "liviana": True,
                            "partes": {k: v["archivos"] for k, v in info["partes"].items()}},
                           ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            command.upgrade(cfg, "head")
        finally:
            PREPARANDO.clear()
        _PREPARADAS.add(direccion)


def _pendiente(cfg, direccion: str) -> str | None:
    """La migración a la que se va a pasar (p. ej. «0005») si la base ya tiene datos y le falta alguna; None si
    está al día o es nueva (una base nueva no necesita copia)."""
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    with motor().connect() as c:
        actual = MigrationContext.configure(c).get_current_revision()
    destino = ScriptDirectory.from_config(cfg).get_current_head()
    return destino if actual is not None and actual != destino else None
