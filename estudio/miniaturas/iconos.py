"""Íconos del protagonista, dibujados por código (vectoriales: salen nítidos a
cualquier tamaño). Para agregar uno: una función aquí, o un PNG con transparencia
en canales/<canal>/miniatura/iconos/<nombre>.png (ese manda sobre el dibujado)."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

AMARILLO, ROJO, NEGRO, BLANCO = (255, 204, 0, 255), (225, 20, 20, 255), (20, 20, 20, 255), (255, 255, 255, 255)
SS = 4          # se dibuja 4 veces más grande y se reduce: bordes suaves


def _lienzo(tam: int):
    im = Image.new("RGBA", (tam * SS, tam * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im), tam * SS


def _fin(im: Image.Image, tam: int) -> Image.Image:
    return im.resize((tam, tam), Image.Resampling.LANCZOS)


def advertencia(tam: int) -> Image.Image:
    im, d, t = _lienzo(tam)
    m = t * 0.06
    pts = [(t / 2, m), (t - m, t - m * 1.4), (m, t - m * 1.4)]
    d.polygon(pts, fill=NEGRO)
    k = t * 0.075
    d.polygon([(t / 2, m + k * 1.9), (t - m - k * 1.7, t - m * 1.4 - k), (m + k * 1.7, t - m * 1.4 - k)], fill=AMARILLO)
    ancho = t * 0.1
    d.rounded_rectangle((t / 2 - ancho / 2, t * 0.34, t / 2 + ancho / 2, t * 0.66), radius=ancho / 2, fill=NEGRO)
    d.ellipse((t / 2 - ancho * 0.62, t * 0.71, t / 2 + ancho * 0.62, t * 0.71 + ancho * 1.24), fill=NEGRO)
    return _fin(im, tam)


def prohibido(tam: int) -> Image.Image:
    im, d, t = _lienzo(tam)
    g = t * 0.11
    d.ellipse((g / 2, g / 2, t - g / 2, t - g / 2), fill=BLANCO)
    # mano abierta (palma y dedos)
    cx, cy = t / 2, t * 0.56
    d.rounded_rectangle((cx - t * 0.16, cy - t * 0.1, cx + t * 0.16, cy + t * 0.2), radius=t * 0.08, fill=NEGRO)
    for k, (dx, largo) in enumerate([(-0.12, 0.22), (-0.04, 0.27), (0.04, 0.27), (0.12, 0.22)]):
        x = cx + dx * t
        d.rounded_rectangle((x - t * 0.035, cy - t * 0.1 - largo * t, x + t * 0.035, cy), radius=t * 0.035, fill=NEGRO)
    d.rounded_rectangle((cx - t * 0.3, cy - t * 0.06, cx - t * 0.13, cy + t * 0.03), radius=t * 0.04, fill=NEGRO)
    d.ellipse((g / 2, g / 2, t - g / 2, t - g / 2), outline=ROJO, width=int(g))
    a = math.radians(45)
    r = t / 2 - g
    d.line([(t / 2 - r * math.cos(a), t / 2 - r * math.sin(a)), (t / 2 + r * math.cos(a), t / 2 + r * math.sin(a))],
           fill=ROJO, width=int(g))
    return _fin(im, tam)


def calavera(tam: int) -> Image.Image:
    im, d, t = _lienzo(tam)
    d.ellipse((t * 0.12, t * 0.06, t * 0.88, t * 0.72), fill=BLANCO, outline=NEGRO, width=int(t * 0.04))
    d.rounded_rectangle((t * 0.3, t * 0.55, t * 0.7, t * 0.9), radius=t * 0.06, fill=BLANCO, outline=NEGRO,
                        width=int(t * 0.04))
    d.rectangle((t * 0.18, t * 0.5, t * 0.82, t * 0.66), fill=BLANCO)
    d.ellipse((t * 0.25, t * 0.33, t * 0.45, t * 0.53), fill=NEGRO)
    d.ellipse((t * 0.55, t * 0.33, t * 0.75, t * 0.53), fill=NEGRO)
    d.polygon([(t * 0.5, t * 0.56), (t * 0.45, t * 0.66), (t * 0.55, t * 0.66)], fill=NEGRO)
    for x in (0.4, 0.5, 0.6):
        d.line([(t * x, t * 0.72), (t * x, t * 0.88)], fill=NEGRO, width=int(t * 0.03))
    return _fin(im, tam)


def rayo(tam: int) -> Image.Image:
    im, d, t = _lienzo(tam)
    pts = [(0.58, 0.02), (0.18, 0.56), (0.46, 0.56), (0.36, 0.98), (0.84, 0.4), (0.54, 0.4), (0.7, 0.02)]
    d.polygon([(x * t, y * t) for x, y in pts], fill=AMARILLO, outline=NEGRO, width=int(t * 0.045))
    return _fin(im, tam)


def interrogacion(tam: int) -> Image.Image:
    from ..render import _fuente

    im, d, t = _lienzo(tam)
    d.ellipse((t * 0.04, t * 0.04, t * 0.96, t * 0.96), fill=ROJO, outline=BLANCO, width=int(t * 0.05))
    f = _fuente(int(t * 0.72))
    caja = d.textbbox((0, 0), "?", font=f)
    d.text(((t - (caja[2] - caja[0])) / 2 - caja[0], (t - (caja[3] - caja[1])) / 2 - caja[1]), "?", font=f, fill=BLANCO)
    return _fin(im, tam)


def reloj(tam: int) -> Image.Image:
    im, d, t = _lienzo(tam)
    d.ellipse((t * 0.05, t * 0.05, t * 0.95, t * 0.95), fill=BLANCO, outline=NEGRO, width=int(t * 0.07))
    for k in range(12):
        a = math.radians(k * 30)
        r1, r2 = t * 0.34, t * (0.3 if k % 3 else 0.26)
        d.line([(t / 2 + r1 * math.sin(a), t / 2 - r1 * math.cos(a)), (t / 2 + r2 * math.sin(a), t / 2 - r2 * math.cos(a))],
               fill=NEGRO, width=int(t * 0.025))
    d.line([(t / 2, t / 2), (t / 2, t * 0.22)], fill=NEGRO, width=int(t * 0.05))
    d.line([(t / 2, t / 2), (t * 0.7, t * 0.6)], fill=ROJO, width=int(t * 0.04))
    d.ellipse((t * 0.46, t * 0.46, t * 0.54, t * 0.54), fill=NEGRO)
    return _fin(im, tam)


DIBUJADOS = {"advertencia": advertencia, "prohibido": prohibido, "calavera": calavera, "rayo": rayo,
             "interrogacion": interrogacion, "reloj": reloj}


def disponibles(carpeta_plantilla: Path | None = None) -> list[str]:
    extra = sorted(p.stem for p in (carpeta_plantilla / "iconos").glob("*.png")) if carpeta_plantilla else []
    return sorted(set(DIBUJADOS) | set(extra))


def icono(nombre: str, tam: int, carpeta_plantilla: Path | None = None) -> Image.Image:
    if carpeta_plantilla and (carpeta_plantilla / "iconos" / f"{nombre}.png").exists():
        im = Image.open(carpeta_plantilla / "iconos" / f"{nombre}.png").convert("RGBA")
        im.thumbnail((tam, tam), Image.Resampling.LANCZOS)
        return im
    if nombre not in DIBUJADOS:
        raise KeyError(f"ícono desconocido: {nombre}")
    return DIBUJADOS[nombre](tam)
