"""Modo local (un computador, un dueño): la primera vez que se usa, la instalación se
migra a datos del espacio del dueño y desde ahí todo corre dentro de ese espacio.

Si algo falla al migrar, Xandart sigue funcionando como antes (sin espacio: busca en las
carpetas de siempre) y el error queda en `error()` para mostrarlo.
"""
from __future__ import annotations

import os
import threading

_CERROJO = threading.Lock()
_estado: dict = {}


def activo() -> bool:
    return os.environ.get("XANDART_SIN_MIGRAR", "") not in ("1", "true", "si")


def espacio() -> str | None:
    """Id del espacio del dueño (migra la primera vez; las siguientes es inmediato)."""
    if not activo():
        return None
    clave = (os.environ.get("XANDART_DATOS", ""), os.environ.get("XANDART_DB", ""))
    if _estado.get("clave") == clave:
        return _estado.get("espacio")
    with _CERROJO:
        if _estado.get("clave") != clave:
            from .migrar import migrar_instalacion

            try:
                r = migrar_instalacion()
                _estado.update(clave=clave, espacio=r["espacio"], resumen=r, error=None)
            except Exception as ex:  # noqa: BLE001 — la versión de siempre sigue sirviendo
                _estado.update(clave=clave, espacio=None, resumen=None, error=f"{ex.__class__.__name__}: {ex}")
    return _estado.get("espacio")


def error() -> str | None:
    return _estado.get("error")


def olvidar() -> None:
    """Para pruebas: la próxima llamada vuelve a migrar."""
    _estado.clear()
