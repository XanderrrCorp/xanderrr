"""Consultas pequeñas que el motor de video necesita sin saber de la base de datos."""
from __future__ import annotations


def nombre_canal(clave: str) -> str:
    """Nombre visible de un canal del espacio actual (si la base no está lista, la clave)."""
    try:
        from sqlalchemy import select

        from . import contexto, db
        from .modelos import Canal

        esp = contexto.espacio_actual()
        if not esp:
            return clave
        with db.sesion() as s:
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave))
            return c.nombre if c else clave
    except Exception:  # noqa: BLE001 — en modo viejo (sin base) basta la clave
        return clave
