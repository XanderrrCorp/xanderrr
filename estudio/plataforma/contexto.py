"""Espacio de trabajo con el que corre el código en este momento (una petición o un trabajo).

El motor de video no sabe de usuarios: pide un estilo, un perfil o una plantilla por su
clave y aquí se decide dónde buscarlo: primero en el espacio actual (lo privado), luego en
el catálogo público de Xandart y por último en las carpetas viejas del código (compatibilidad
con la versión de un solo usuario mientras se migra).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from ..config import RAIZ

_espacio: ContextVar[str | None] = ContextVar("espacio_actual", default=None)


def espacio_actual() -> str | None:
    return _espacio.get()


@contextmanager
def usar_espacio(espacio_id: str | None):
    marca = _espacio.set(espacio_id)
    try:
        yield
    finally:
        _espacio.reset(marca)


def fijar_espacio(espacio_id: str | None) -> None:
    """Para hilos de trabajo que ya copiaron el contexto: fija el espacio sin bloque `with`."""
    _espacio.set(espacio_id)


def carpeta_catalogo() -> Path:
    """Catálogo público que viene con Xandart (solo lectura)."""
    return RAIZ / "catalogo"


def buscar(tipo: str, clave: str, archivo: str | None = None) -> Path | None:
    """Carpeta (o archivo dentro de ella) de un recurso por clave, en orden: espacio → catálogo → legado.
    tipo: estilos | perfiles | plantillas_miniatura | formulas."""
    from . import almacen

    legado = {"estilos": RAIZ / "estilos", "perfiles": RAIZ / "perfiles",
              "plantillas_miniatura": RAIZ / "canales", "formulas": None}
    candidatos = []
    esp = espacio_actual()
    if esp:
        candidatos.append(almacen.raiz_espacio(esp) / tipo / clave)
    candidatos.append(carpeta_catalogo() / tipo / clave)
    if legado.get(tipo):
        base = legado[tipo] / clave
        candidatos.append(base / "miniatura" if tipo == "plantillas_miniatura" else base)
    for c in candidatos:
        destino = c / archivo if archivo else c
        if destino.exists():
            return destino
    return None


def todas(tipo: str, archivo: str) -> list[Path]:
    """Todos los recursos visibles de un tipo (para listarlos), sin repetir claves."""
    from . import almacen

    raices = []
    esp = espacio_actual()
    if esp:
        raices.append(almacen.raiz_espacio(esp) / tipo)
    raices.append(carpeta_catalogo() / tipo)
    if tipo == "estilos":
        raices.append(RAIZ / "estilos")
    vistos, salida = set(), []
    for r in raices:
        for p in sorted(r.glob(f"*/{archivo}")):
            if p.parent.name not in vistos:
                vistos.add(p.parent.name)
                salida.append(p)
    return salida
