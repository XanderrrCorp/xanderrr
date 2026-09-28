"""Escala de peligro 0–10 a pantalla completa (dibujada con código: nítida, igual en todos los
videos y sin gastar imágenes). Barra de 11 segmentos de verde a rojo, la palabra del nivel en su
color, «X/10» grande y una flecha roja que se desliza desde el 0 hasta el valor."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FUENTES = Path(__file__).parent / "fuentes"
COLORES = ["#3fb54a", "#66c947", "#a6d64a", "#f2e53a", "#f5cc2a", "#f5a52a", "#f28a2a", "#e8621f",
           "#c62328", "#a81c22", "#8e151b"]
ETIQUETAS = [(1, "INOFENSIVO"), (3, "LEVE"), (5, "MODERADO"), (7, "PELIGROSO"), (9, "MUY PELIGROSO"), (10, "MORTAL")]


def etiqueta(valor: int) -> str:
    return next(t for tope, t in ETIQUETAS if valor <= tope)


def valor_por_posicion(numero: int, total: int) -> int:
    """Si el guion no trae el valor: el primer nivel es 0 y el último 10, repartido en medio."""
    if total <= 1:
        return 10
    return round(10 * (numero - 1) / (total - 1))


@lru_cache(maxsize=8)
def _fuente(tam: int) -> ImageFont.FreeTypeFont:
    for nombre in ("ArchivoBlack-Regular.ttf", "Fredoka-SemiBold.ttf"):
        if (FUENTES / nombre).exists():
            return ImageFont.truetype(str(FUENTES / nombre), tam)
    return ImageFont.load_default()


def _suave(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _texto_centrado(d: ImageDraw.ImageDraw, cx: float, y: float, texto: str, tam: int, color: str,
                    borde: int, escala: float = 1.0) -> None:
    f = _fuente(max(8, int(tam * escala)))
    caja = d.textbbox((0, 0), texto, font=f, stroke_width=borde)
    d.text((cx - (caja[2] - caja[0]) / 2, y - (caja[3] - caja[1]) / 2 - caja[1]), texto, font=f, fill=color,
           stroke_width=borde, stroke_fill="#111111")


def dibujar(valor: int, t: float, ancho: int = 1920, alto: int = 1080) -> Image.Image:
    """Capa transparente de la escala en el segundo t desde que aparece (la flecha tarda 0,9 s)."""
    valor = max(0, min(10, int(valor)))
    capa = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    k = ancho / 1920
    x0, x1, yb, hb = 190 * k, 1730 * k, 548 * k, 78 * k
    seg = (x1 - x0) / 11
    # barra: 11 segmentos dentro de una máscara con extremos redondeados
    bw, bh = int(x1 - x0), int(hb)
    barra = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    db = ImageDraw.Draw(barra)
    for i, c in enumerate(COLORES):
        db.rectangle([round(i * seg), 0, round((i + 1) * seg), bh], fill=c)
    mascara = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2, fill=255)
    capa.paste(barra, (int(x0), int(yb)), mascara)
    for i in range(11):                                                                  # números arriba
        _texto_centrado(d, x0 + (i + 0.5) * seg, yb - 70 * k, str(i), int(92 * k), "#111111", 0)
    # flecha: viaja del 0 al valor y rebota un poco al llegar
    avance = _suave(t / 0.9)
    pos = avance * valor
    rebote = math.sin(max(0.0, t - 0.9) * 14) * math.exp(-max(0.0, t - 0.9) * 5) * 0.12 if t > 0.9 else 0
    cx = x0 + (pos + rebote + 0.5) * seg
    punta = (cx, yb + hb + 12 * k)
    cola = (cx - 95 * k, yb + hb + 175 * k)
    _flecha(d, cola, punta, k)
    # palabra y puntaje: aparecen con un pop cuando la flecha llega
    if t >= 0.9:
        p = _suave((t - 0.9) / 0.18)
        pop = 1 + 0.18 * math.sin(p * math.pi)
        color = COLORES[valor]
        _texto_centrado(d, ancho / 2, 250 * k, etiqueta(valor), int(150 * k), color, max(2, int(9 * k)), pop)
        _texto_centrado(d, ancho / 2, 890 * k, f"{valor}/10", int(150 * k), color, max(2, int(9 * k)), pop)
    return capa


def _flecha(d: ImageDraw.ImageDraw, cola: tuple[float, float], punta: tuple[float, float], k: float) -> None:
    """Flecha roja curva con borde negro, apuntando a la barra."""
    pasos = 40
    ctrl = (cola[0] - 30 * k, (cola[1] + punta[1]) / 2 + 20 * k)
    puntos = []
    for i in range(pasos + 1):
        u = i / pasos
        x = (1 - u) ** 2 * cola[0] + 2 * (1 - u) * u * ctrl[0] + u * u * punta[0]
        y = (1 - u) ** 2 * cola[1] + 2 * (1 - u) * u * ctrl[1] + u * u * punta[1]
        puntos.append((x, y))
    cuerpo = puntos[:-8]
    for grosor, color in ((42 * k, "#111111"), (28 * k, "#e11b1b")):
        r = grosor / 2
        for x, y in cuerpo:                       # círculos seguidos: trazo continuo sin cortes
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    ang = math.atan2(punta[1] - puntos[-9][1], punta[0] - puntos[-9][0])
    largo, ancho = 78 * k, 66 * k
    base = (punta[0] - largo * math.cos(ang), punta[1] - largo * math.sin(ang))
    izq = (base[0] + ancho * math.sin(ang), base[1] - ancho * math.cos(ang))
    der = (base[0] - ancho * math.sin(ang), base[1] + ancho * math.cos(ang))
    d.polygon([punta, izq, der], fill="#e11b1b", outline="#111111", width=max(2, int(7 * k)))
