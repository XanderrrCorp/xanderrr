"""El trazo de marcador: línea negra gruesa, un poco temblorosa, igual en todas las piezas.

El temblor sale de una semilla fija por pieza: el mismo dibujo da siempre la misma línea
(en la animación no «hierve» entre cuadros).
"""
from __future__ import annotations

import math
import random

NEGRO = "#151515"
BLANCO = "#FFFFFF"
GRIS = "#9A9A9A"
AMARILLO = "#FFD21F"
ROJO = "#E5322D"
VERDE = "#2DB84B"
CREMA = "#F7E6C4"

LINEA = 7.0          # grosor del contorno en TODAS las piezas
TEMBLOR = 1.5        # cuánto se aparta la línea del trazo perfecto


def _remuestrear(puntos: list[tuple[float, float]], cerrado: bool, paso: float) -> list[tuple[float, float]]:
    pts = list(puntos) + ([puntos[0]] if cerrado else [])
    salida = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        largo = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(largo / paso))
        for i in range(1, n + 1):
            salida.append((x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n))
    return salida[:-1] if cerrado else salida


def temblar(puntos, semilla: str, cerrado: bool = False, amplitud: float = TEMBLOR, paso: float = 6.0):
    """Mueve cada punto un poco sobre la normal con dos ondas lentas (como la mano con marcador)."""
    rng = random.Random(semilla)
    f1, f2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    l1, l2 = rng.uniform(55, 85), rng.uniform(24, 36)
    pts = _remuestrear(puntos, cerrado, paso)
    salida, recorrido = [], 0.0
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        if i:
            recorrido += math.hypot(x - pts[i - 1][0], y - pts[i - 1][1])
        a = pts[i - 1] if (i or cerrado) else pts[i]
        b = pts[(i + 1) % n] if (i < n - 1 or cerrado) else pts[i]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        desp = amplitud * (0.65 * math.sin(recorrido / l1 * 6.283 + f1) + 0.35 * math.sin(recorrido / l2 * 6.283 + f2))
        if not cerrado and (i == 0 or i == n - 1):
            desp *= 0.4
        salida.append((x + nx * desp, y + ny * desp))
    return salida


def recortar(pts, parcial: float):
    """Solo el primer `parcial` (0 a 1) del recorrido: así una línea «se dibuja» de punta a punta."""
    if parcial >= 1:
        return pts
    largos = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    falta = sum(largos) * max(0.0, parcial)
    salida = [pts[0]]
    for (a, b), l in zip(zip(pts, pts[1:]), largos):
        if falta >= l:
            salida.append(b)
            falta -= l
            continue
        k = falta / l if l else 0
        salida.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k))
        break
    return salida


def camino(puntos, semilla: str, cerrado: bool = False, amplitud: float = TEMBLOR, parcial: float = 1.0) -> str:
    pts = temblar(puntos, semilla, cerrado, amplitud)
    if parcial < 1:
        pts = recortar(pts + ([pts[0]] if cerrado else []), parcial)
        cerrado = False
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + (" Z" if cerrado else "")


def elipse(cx, cy, rx, ry, rot: float = 0.0, n: int = 0) -> list[tuple[float, float]]:
    n = n or max(16, int((rx + ry) * 0.6))
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    salida = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        salida.append((cx + x * c - y * s, cy + x * s + y * c))
    return salida


def arco(cx, cy, rx, ry, desde: float, hasta: float, n: int = 14) -> list[tuple[float, float]]:
    """Grados en sentido de la pantalla (0 = derecha, 90 = abajo)."""
    return [(cx + rx * math.cos(math.radians(desde + (hasta - desde) * i / n)),
             cy + ry * math.sin(math.radians(desde + (hasta - desde) * i / n))) for i in range(n + 1)]


def figura(puntos, semilla: str, relleno: str, cerrado: bool = True, linea: float = LINEA,
           amplitud: float = TEMBLOR) -> str:
    """Forma rellena con contorno de marcador."""
    return (f'<path d="{camino(puntos, semilla, cerrado, amplitud)}" fill="{relleno}" stroke="{NEGRO}" '
            f'stroke-width="{linea}" stroke-linejoin="round" stroke-linecap="round"/>')


def raya(puntos, semilla: str, color: str = NEGRO, ancho: float = LINEA, amplitud: float = TEMBLOR,
         parcial: float = 1.0) -> str:
    """Línea suelta (cejas, boca, flechas). `parcial` < 1 la deja dibujada a medias."""
    if parcial <= 0.001:
        return ""
    return (f'<path d="{camino(puntos, semilla, False, amplitud, parcial)}" fill="none" stroke="{color}" '
            f'stroke-width="{ancho}" stroke-linejoin="round" stroke-linecap="round"/>')


def tubo(puntos, semilla: str, relleno: str, grueso: float, parcial: float = 1.0) -> str:
    """Extremidad: tubo de color con contorno (la misma línea temblorosa dos veces)."""
    if parcial <= 0.001:
        return ""
    d = camino(puntos, semilla, False, parcial=parcial)
    return (f'<path d="{d}" fill="none" stroke="{NEGRO}" stroke-width="{grueso + 2 * LINEA}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{relleno}" stroke-width="{grueso}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>')
