"""Dónde viven los archivos (imágenes, audio, videos) de cada espacio.

Hoy: datos/espacios/<espacio_id>/… en el disco del PC. En la nube este módulo pasará a
S3/R2 sin que el resto del código cambie: todo pide rutas por aquí, nunca las arma a mano.
"""
from __future__ import annotations

import re
from pathlib import Path

from .db import carpeta_datos

_SEGURO = re.compile(r"^[A-Za-z0-9_\-.]+$")


def raiz_espacio(espacio_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", espacio_id or ""):
        raise ValueError("espacio no válido")
    r = carpeta_datos() / "espacios" / espacio_id
    r.mkdir(parents=True, exist_ok=True)
    return r


def ruta(espacio_id: str, *partes: str) -> Path:
    """Ruta dentro del espacio; nunca se sale de él (sin «..» ni rutas absolutas)."""
    for p in partes:
        if not _SEGURO.match(p) or p in (".", ".."):
            raise ValueError(f"nombre no válido: {p!r}")
    return raiz_espacio(espacio_id).joinpath(*partes)


def carpeta_videos(espacio_id: str) -> Path:
    d = ruta(espacio_id, "videos")
    d.mkdir(parents=True, exist_ok=True)
    return d


def catalogo(*partes: str) -> Path:
    """Archivos del catálogo público de Xandart (estilos y personajes predeterminados)."""
    for p in partes:
        if not _SEGURO.match(p) or p in (".", ".."):
            raise ValueError(f"nombre no válido: {p!r}")
    return carpeta_datos().joinpath("catalogo", *partes)
