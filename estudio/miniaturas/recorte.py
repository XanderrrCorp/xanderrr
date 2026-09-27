"""Paso 3a: quitar el fondo blanco de cada sujeto, en el PC y gratis.

Con `rembg` (si está instalado; el instalador lo intenta) el recorte respeta bordes
difíciles como pelo o antenas. Sin él, se inunda el blanco desde los bordes, lo que
conserva las partes blancas DENTRO del animal. En los dos casos se limpia el halo
blanco de los bordes para que no quede un contorno raro sobre el lienzo.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_SESION = None


def _rembg(img: Image.Image) -> Image.Image | None:
    global _SESION
    try:
        from rembg import new_session, remove
    except Exception:  # noqa: BLE001
        return None
    try:
        if _SESION is None:
            _SESION = new_session("isnet-general-use")
        return remove(img.convert("RGB"), session=_SESION)
    except Exception:  # noqa: BLE001 — sin modelo (sin internet la primera vez): recorte simple
        return None


def _inundar(img: Image.Image, tolerancia: int = 30) -> Image.Image:
    base = img.convert("RGB")
    trabajo = base.copy()
    w, h = trabajo.size
    marca = (255, 0, 255)
    paso = max(1, min(w, h) // 24)
    bordes = [(x, 0) for x in range(0, w, paso)] + [(x, h - 1) for x in range(0, w, paso)] + \
             [(0, y) for y in range(0, h, paso)] + [(w - 1, y) for y in range(0, h, paso)]
    for x, y in bordes:
        r, g, b = trabajo.getpixel((x, y))
        if (r, g, b) != marca and min(r, g, b) > 200:          # solo se inunda lo que es fondo claro
            ImageDraw.floodfill(trabajo, (x, y), marca, thresh=tolerancia)
    a = np.asarray(trabajo)
    fondo = (a[:, :, 0] == 255) & (a[:, :, 1] == 0) & (a[:, :, 2] == 255)
    alfa = Image.fromarray(np.where(fondo, 0, 255).astype("uint8"))
    alfa = alfa.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.0))
    salida = base.convert("RGBA")
    salida.putalpha(alfa)
    return salida


def _sin_halo(rgba: Image.Image) -> Image.Image:
    """Quita el tinte blanco de los bordes semitransparentes (el color «se despega» del fondo)."""
    a = np.asarray(rgba).astype(np.float32)
    alfa = a[:, :, 3:4] / 255
    borde = (alfa > 0.04) & (alfa < 0.98)
    limpio = np.where(borde, (a[:, :, :3] - (1 - alfa) * 255) / np.maximum(alfa, 0.04), a[:, :, :3])
    a[:, :, :3] = np.clip(limpio, 0, 255)
    return Image.fromarray(a.astype("uint8"), "RGBA")


def recortar(img: Image.Image, usar_rembg: bool = True) -> tuple[Image.Image, str]:
    """Sujeto sin fondo, recortado a su contorno. Devuelve (imagen RGBA, método usado)."""
    rgba = _rembg(img) if usar_rembg else None
    metodo = "rembg"
    if rgba is None:
        rgba, metodo = _inundar(img), "inundado"
    rgba = _sin_halo(rgba)
    caja = rgba.split()[-1].point(lambda v: 255 if v > 24 else 0).getbbox()
    return (rgba.crop(caja) if caja else rgba), metodo


def restos_de_fondo(rgba: Image.Image) -> float:
    """Proporción de píxeles casi blancos y opacos pegados al contorno (restos del fondo)."""
    a = np.asarray(rgba)
    alfa = a[:, :, 3] > 200
    borde = alfa & ~np.asarray(Image.fromarray((alfa * 255).astype("uint8")).filter(ImageFilter.MinFilter(5))).astype(bool)
    if not borde.any():
        return 0.0
    blancos = (a[:, :, :3].min(axis=2) > 235) & borde
    return float(blancos.sum() / borde.sum())
