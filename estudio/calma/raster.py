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


def sprite(pieza: str, estado: dict, escala: float, sombra: bool = False) -> tuple[np.ndarray, tuple[float, float]]:
    from .trazo import factor_temblor

    clave = f"{pieza}|{json.dumps(estado, sort_keys=True)}|{escala:.3f}|{factor_temblor():.2f}|{int(sombra)}"
    if clave not in _CACHE:
        img, ancla = rasterizar(dibujar(pieza, estado), escala)
        _CACHE[clave] = con_sombra(img, ancla) if sombra else (img, ancla)
    return _CACHE[clave]


def con_sombra(img: np.ndarray, ancla: tuple[float, float], dx: int = 7, dy: int = 10, desenfoque: int = 11,
               opacidad: float = 0.22) -> tuple[np.ndarray, tuple[float, float]]:
    """La pieza con una sombra suave abajo a la derecha (se calcula una vez: queda en la caché del sprite)."""
    m = desenfoque + max(dx, dy)
    h, w = img.shape[:2]
    lienzo = np.zeros((h + 2 * m, w + 2 * m, 4), np.uint8)
    a = np.zeros((h + 2 * m, w + 2 * m), np.float32)
    a[m + dy:m + dy + h, m + dx:m + dx + w] = img[:, :, 3] / 255.0
    a = cv2.GaussianBlur(a, (0, 0), desenfoque / 2) * opacidad
    lienzo[:, :, :3] = (40, 35, 30)
    alfa_p = img[:, :, 3:4].astype(np.float32) / 255.0
    sub_a = a[m:m + h, m:m + w, None]
    salida_a = alfa_p + sub_a * (1 - alfa_p)
    color = (img[:, :, :3].astype(np.float32) * alfa_p + 35 * sub_a * (1 - alfa_p)) / np.maximum(salida_a, 1e-6)
    lienzo[:, :, 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    lienzo[m:m + h, m:m + w, :3] = np.clip(color, 0, 255).astype(np.uint8)
    lienzo[m:m + h, m:m + w, 3] = np.clip(salida_a[:, :, 0] * 255, 0, 255).astype(np.uint8)
    return lienzo, (ancla[0] + m, ancla[1] + m)


def vaciar_cache() -> None:
    _CACHE.clear()
