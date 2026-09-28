"""Motor de base de datos y sesiones.

SQLite en el PC (archivo datos/xandart.db, fuera del código: el instalador no lo toca).
Para la nube basta con poner XANDART_DB=postgresql+psycopg://… : el resto no cambia.
El esquema se versiona con Alembic (carpeta migraciones/): nunca se edita a mano.
"""
from __future__ import annotations

import os
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


def preparar() -> None:
    """Deja la base al día (migraciones de Alembic). Se llama al abrir Xandart."""
    from alembic import command
    from alembic.config import Config

    from . import modelos  # noqa: F401 — registra las tablas

    motor()                                   # crea la carpeta de datos si hace falta
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(__file__).with_name("migraciones")))
    cfg.set_main_option("sqlalchemy.url", url())
    command.upgrade(cfg, "head")
