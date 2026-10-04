"""SVG → imagen RGBA (numpy) con resvg, con caché: cada pieza en cada estado se dibuja una sola vez."""
from __future__ import annotations

import json

import cv2
import numpy as np

from .piezas import FUENTE, Dibujo, dibujar

_CACHE: dict[str, tuple[np.ndarray, tuple[float, float]]] = {}


def svg_a_rgba(svg: str, ancho: int, alto: int) -> np.ndarray:
    import resvg_py

    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, font_files=[str(FUENTE)], skip_system_fonts=True))
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)
    if img.shape[2] == 3:
        img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    return img                                              # BGRA, como el resto de OpenCV


def rasterizar(d: Dibujo, escala: float) -> tuple[np.ndarray, tuple[float, float]]:
    """La pieza a `escala` px por unidad. Devuelve la imagen y dónde cae el ancla (0,0) dentro de ella."""
    x0, y0, w, h = d.caja
    W, H = max(1, int(np.ceil(w * escala))), max(1, int(np.ceil(h * escala)))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="{x0} {y0} {w} {h}">'
           f'{d.svg}</svg>')
    return svg_a_rgba(svg, W, H), (-x0 * escala, -y0 * escala)


def sprite(pieza: str, estado: dict, escala: float) -> tuple[np.ndarray, tuple[float, float]]:
    clave = f"{pieza}|{json.dumps(estado, sort_keys=True)}|{escala:.3f}"
    if clave not in _CACHE:
        _CACHE[clave] = rasterizar(dibujar(pieza, estado), escala)
    return _CACHE[clave]


def vaciar_cache() -> None:
    _CACHE.clear()
