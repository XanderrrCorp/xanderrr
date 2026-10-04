"""Catálogo de piezas en SVG, todas con el mismo trazo de marcador.

Cada pieza es una función `estado -> Dibujo`: el SVG (sin la etiqueta <svg>) en coordenadas
propias, con el punto de anclaje en (0, 0), y la caja que ocupa. Tamaño 1 = tamaño natural en
un video de 1080 de alto. Las piezas que cambian por dentro (barra que se llena, aguja del
cronómetro, llama que alterna color) reciben ese valor en `estado`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from . import personaje as P
from .trazo import (AMARILLO, BLANCO, CREMA, GRIS, LINEA, NEGRO, ROJO, VERDE, arco, elipse, figura, raya,
                    tubo)

FUENTE = Path(__file__).resolve().parents[1] / "fuentes" / "ArchivoBlack-Regular.ttf"
FAMILIA = "Archivo Black"
GRIS_OSCURO = "#5B5B5B"


@dataclass
class Dibujo:
    svg: str
    caja: tuple[float, float, float, float]      # x0, y0, ancho, alto (coordenadas propias)


def _caja_de(pts, margen: float = LINEA * 2) -> tuple[float, float, float, float]:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - margen, min(ys) - margen, max(xs) - min(xs) + 2 * margen, max(ys) - min(ys) + 2 * margen)


def _rect(x, y, w, h, r: float = 14) -> list[tuple[float, float]]:
    """Rectángulo de esquinas redondeadas como lista de puntos (para temblar)."""
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        pts += arco(cx, cy, r, r, a0, a0 + 90, 5)
    return pts


def ancho_texto(texto: str, alto: float) -> float:
    from PIL import ImageFont

    f = ImageFont.truetype(str(FUENTE), int(alto))
    return f.getlength(texto)


def _texto(x, y, texto: str, alto: float, color: str = NEGRO, contorno: str | None = None,
           ancla: str = "middle") -> str:
    texto = texto.replace("&", "&amp;").replace("<", "&lt;")
    borde = (f' stroke="{contorno}" stroke-width="{alto * 0.16:.1f}" stroke-linejoin="round" paint-order="stroke"'
             if contorno else "")
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FAMILIA}" font-size="{alto:.1f}" fill="{color}" '
            f'text-anchor="{ancla}" dominant-baseline="central"{borde}>{texto}</text>')


# ------------------------------------------------------------------ personaje

def personaje(e: dict) -> Dibujo:
    pose = e.get("pose", "de_pie")
    svg = P.personaje(pose, e.get("ojos", "abiertos"), e.get("gesto", "neutral"),
                      e.get("color", AMARILLO), e.get("mochila", True))
    return Dibujo(svg, (-190, -560, 380, 590))


def vecino(e: dict) -> Dibujo:
    """Otra persona: el mismo dibujo en gris y sin mochila."""
    return personaje({**e, "color": GRIS, "mochila": False})


def gente(e: dict) -> Dibujo:
    """«Todo el mundo»: tres personas en gris, la del medio un poco adelante."""
    partes = []
    for dx, esc, gesto in ((-150, 0.62, "neutral"), (150, 0.62, "concentrado"), (0, 0.72, "neutral")):
        partes.append(f'<g transform="translate({dx},0) scale({esc})">'
                      f'{P.personaje("de_pie", e.get("ojos", "abiertos"), gesto, GRIS, False)}</g>')
    return Dibujo("".join(partes), (-280, -420, 560, 440))


# ------------------------------------------------------------------ signos

def x_roja(e: dict) -> Dibujo:
    r = 110
    return Dibujo(tubo([(-r, -r), (r, r)], "x/1", ROJO, 34) + tubo([(r, -r), (-r, r)], "x/2", ROJO, 34),
                  (-r - 40, -r - 40, 2 * r + 80, 2 * r + 80))


def chulo(e: dict) -> Dibujo:
    return Dibujo(tubo([(-100, 0), (-30, 70), (110, -90)], "chulo", VERDE, 34), (-150, -140, 300, 260))


def flecha(e: dict) -> Dibujo:
    """Flecha curva que apunta a la derecha; se orienta con «rotacion» del elemento."""
    largo = float(e.get("largo", 220))
    color = ROJO if e.get("color", "rojo") == "rojo" else NEGRO
    curva = float(e.get("curva", 0.18))
    pts = [(-largo / 2 + largo * t, -math.sin(math.pi * t) * largo * curva) for t in [i / 12 for i in range(13)]]
    fin = pts[-1]
    ang = math.atan2(pts[-1][1] - pts[-3][1], pts[-1][0] - pts[-3][0])
    punta = []
    for a, d in ((0, 34), (2.45, 38), (-2.45, 38)):
        punta.append((fin[0] + math.cos(ang + a) * d * (1 if a == 0 else 1),
                      fin[1] + math.sin(ang + a) * d))
    cuerpo = tubo(pts[:-1], "flecha/c", color, 20)
    cabeza = figura([punta[0], punta[1], punta[2]], "flecha/p", color)
    return Dibujo(cuerpo + cabeza, (-largo / 2 - 30, -largo * curva - 60, largo + 90, largo * curva + 120))


def rotulo(e: dict) -> Dibujo:
    """Rótulo en mayúsculas. Colores: negro (texto negro en caja blanca), rojo (blanco en caja roja),
    verde, amarillo. «caja»: false = solo el texto con borde blanco."""
    texto = str(e.get("texto", "")).upper()
    alto = float(e.get("alto", 92))
    color = e.get("color", "negro")
    fondo, letra = {"negro": (BLANCO, NEGRO), "rojo": (ROJO, BLANCO), "verde": (VERDE, BLANCO),
                    "amarillo": (AMARILLO, NEGRO)}.get(color, (BLANCO, NEGRO))
    w = ancho_texto(texto, alto) + alto * 0.9
    h = alto * 1.45
    if not e.get("caja", True):
        svg = _texto(0, 0, texto, alto, letra if color != "negro" else NEGRO, BLANCO)
        return Dibujo(svg, (-w / 2, -h / 2, w, h))
    caja = figura(_rect(-w / 2, -h / 2, w, h, 18), f"rotulo/{texto}", fondo)
    return Dibujo(caja + _texto(0, alto * 0.04, texto, alto, letra), (-w / 2 - 12, -h / 2 - 12, w + 24, h + 24))


def numero(e: dict) -> Dibujo:
    """Número o contador grande dentro de un círculo amarillo."""
    valor = str(e.get("valor", "1"))
    r = 95 if len(valor) <= 2 else 70 + 22 * len(valor)
    color = {"rojo": ROJO, "amarillo": AMARILLO, "blanco": BLANCO}.get(e.get("color", "amarillo"), AMARILLO)
    texto = BLANCO if color == ROJO else NEGRO
    svg = figura(elipse(0, 0, r, 95, n=48), f"numero/{len(valor)}", color) + _texto(0, 6, valor, 120, texto)
    return Dibujo(svg, (-r - 14, -109, 2 * r + 28, 218))


def barra(e: dict) -> Dibujo:
    """Barra que se llena (tiempo, peligro). «relleno» de 0 a 1 lo mueve el movimiento llenar_barra."""
    w, h = float(e.get("ancho", 620)), 70
    rell = max(0.0, min(1.0, float(e.get("relleno", 0))))
    color = {"rojo": ROJO, "verde": VERDE, "amarillo": AMARILLO, "gris": GRIS}.get(e.get("color", "rojo"), ROJO)
    fondo = figura(_rect(-w / 2, -h / 2, w, h, 20), "barra/f", BLANCO)
    dentro = ""
    if rell > 0.01:
        a = (w - 20) * rell
        dentro = f'<rect x="{-w / 2 + 10:.1f}" y="{-h / 2 + 10:.1f}" width="{a:.1f}" height="{h - 20}" rx="12" fill="{color}"/>'
    borde = (f'<path d="{_d(_rect(-w / 2, -h / 2, w, h, 20), "barra/f")}" fill="none" stroke="{NEGRO}" '
             f'stroke-width="{LINEA}" stroke-linejoin="round"/>')
    etiqueta = e.get("etiqueta")
    extra = _texto(-w / 2, -h / 2 - 46, str(etiqueta).upper(), 50, NEGRO, ancla="start") if etiqueta else ""
    return Dibujo(fondo + dentro + borde + extra, (-w / 2 - 12, -h / 2 - 80, w + 24, h + 92))


def _d(pts, semilla) -> str:
    from .trazo import camino

    return camino(pts, semilla, True)


def cronometro(e: dict) -> Dibujo:
    """Cronómetro: la aguja apunta a «aguja» grados (0 = arriba); girar la mueve."""
    r = 120
    ang = math.radians(float(e.get("aguja", 0)) - 90)
    partes = [
        tubo([(0, -r - 6), (0, -r - 34)], "crono/cuello", GRIS, 22),
        figura(_rect(-34, -r - 66, 68, 34, 10), "crono/boton", ROJO),
        tubo([(r * 0.7, -r * 0.78), (r * 0.86, -r * 0.94)], "crono/boton2", GRIS, 18),
        figura(elipse(0, 0, r, r, n=60), "crono/cara", BLANCO),
    ]
    for i in range(12):
        a = math.radians(i * 30 - 90)
        l0 = r - (26 if i % 3 == 0 else 16)
        partes.append(raya([(math.cos(a) * l0, math.sin(a) * l0), (math.cos(a) * (r - 8), math.sin(a) * (r - 8))],
                           f"crono/m{i}", NEGRO, 6 if i % 3 == 0 else 4, 0.4))
    partes.append(tubo([(0, 0), (math.cos(ang) * (r - 30), math.sin(ang) * (r - 30))], "crono/aguja", ROJO, 9))
    partes.append(f'<circle r="12" fill="{NEGRO}"/>')
    return Dibujo("".join(partes), (-r - 14, -r - 80, 2 * r + 28, 2 * r + 94))


def calendario(e: dict) -> Dibujo:
    texto = str(e.get("texto", "HOY")).upper()
    w, h = 240, 250
    partes = [figura(_rect(-w / 2, -h / 2, w, h, 16), f"cal/{texto}", BLANCO),
              figura(_rect(-w / 2, -h / 2, w, 70, 16), f"cal/top/{texto}", ROJO)]
    for dx in (-60, 60):
        partes.append(tubo([(dx, -h / 2 - 22), (dx, -h / 2 + 16)], f"cal/an{dx}", GRIS, 12))
    alto = min(74.0, (w - 34) / max(1.0, ancho_texto(texto, 1)))
    partes.append(_texto(0, 34, texto, alto))
    return Dibujo("".join(partes), (-w / 2 - 12, -h / 2 - 40, w + 24, h + 52))


def documento(e: dict) -> Dibujo:
    """Una guía oficial: hoja con título, renglones y sello rojo (sin escudos ni logos reales)."""
    titulo = str(e.get("titulo", "GUÍA")).upper()
    w, h = 300, 390
    partes = [figura([(-w / 2, -h / 2), (w / 2 - 50, -h / 2), (w / 2, -h / 2 + 50), (w / 2, h / 2), (-w / 2, h / 2)],
                     "doc/hoja", BLANCO),
              raya([(w / 2 - 50, -h / 2), (w / 2 - 50, -h / 2 + 50), (w / 2, -h / 2 + 50)], "doc/dobl"),
              _texto(-w / 2 + 30, -h / 2 + 62, titulo, 58, NEGRO, ancla="start")]
    for i, largo in enumerate((0.8, 0.7, 0.82, 0.55, 0.75)):
        y = -h / 2 + 140 + i * 40
        partes.append(raya([(-w / 2 + 30, y), (-w / 2 + 30 + (w - 60) * largo, y)], f"doc/r{i}", GRIS, 8, 0.6))
    partes.append(figura(elipse(w / 2 - 70, h / 2 - 66, 46, 46, n=30), "doc/sello", ROJO))
    partes.append(figura(elipse(w / 2 - 70, h / 2 - 66, 26, 26, n=20), "doc/sello2", ROJO, amplitud=0.6))
    return Dibujo("".join(partes), (-w / 2 - 12, -h / 2 - 12, w + 24, h + 24))


def casa(e: dict) -> Dibujo:
    partes = [figura([(-150, -40), (150, -40), (150, 160), (-150, 160)], "casa/m", BLANCO),
              figura([(-185, -30), (0, -175), (185, -30)], "casa/t", ROJO),
              figura([(-40, 50), (40, 50), (40, 160), (-40, 160)], "casa/p", GRIS),
              figura([(70, 10), (125, 10), (125, 60), (70, 60)], "casa/v", BLANCO),
              figura([(-125, 10), (-70, 10), (-70, 60), (-125, 60)], "casa/v2", BLANCO)]
    return Dibujo("".join(partes), (-200, -190, 400, 365))


def gotas(e: dict) -> Dibujo:
    partes = []
    for i, (x, y, s) in enumerate(((-50, 0, 1.0), (30, -40, 0.8), (55, 45, 0.7))):
        pts = [(x, y - 40 * s)] + arco(x, y + 4 * s, 24 * s, 24 * s, -20, 200, 12)
        partes.append(figura(pts, f"gota/{i}", ROJO))
    return Dibujo("".join(partes), (-90, -90, 180, 180))


def vena(e: dict) -> Dibujo:
    """Corte de la piel: capa crema arriba y un vaso de sangre rojo debajo."""
    w = float(e.get("ancho", 900))
    partes = [figura([(-w / 2, -120), (w / 2, -120), (w / 2, 10), (-w / 2, 10)], "vena/piel", CREMA),
              figura([(-w / 2, 50), (w / 2, 50), (w / 2, 140), (-w / 2, 140)], "vena/vaso", ROJO)]
    for i in range(5):
        x = -w / 2 + 80 + i * (w - 160) / 4
        partes.append(figura(elipse(x, 95, 22, 13, n=16), f"vena/g{i}", "#B8231F", amplitud=0.5))
    return Dibujo("".join(partes), (-w / 2 - 12, -132, w + 24, 284))


# ------------------------------------------------------------------ objetos del guion de garrapatas

def garrapata(e: dict) -> Dibujo:
    """Vista de arriba. variante: normal | llena (después de horas comiendo) | irritada | apretada."""
    v = e.get("variante", "normal")
    rx, ry = {"normal": (70, 92), "llena": (110, 128), "irritada": (70, 92), "apretada": (112, 64)}.get(v, (70, 92))
    color = {"llena": GRIS, "apretada": GRIS}.get(v, GRIS_OSCURO)
    partes = []
    for lado in (-1, 1):                                     # 8 patas
        for i, (y0, dy) in enumerate(((-ry * 0.45, -60), (-ry * 0.15, -20), (ry * 0.15, 20), (ry * 0.45, 60))):
            x0 = lado * rx * 0.75
            rod = (lado * (rx + 50), y0 + dy * 0.6 - 22)
            pie = (lado * (rx + 70), y0 + dy + 20)
            partes.append(raya([(x0, y0), rod, pie], f"garr/{v}/p{lado}{i}", NEGRO, 10))
    cabeza_y = -ry - 22
    partes.append(figura(elipse(0, cabeza_y, 30, 28, n=20), f"garr/{v}/cab", NEGRO))
    partes.append(raya([(-10, cabeza_y - 22), (-14, cabeza_y - 48)], f"garr/{v}/b1", NEGRO, 9))
    partes.append(raya([(10, cabeza_y - 22), (14, cabeza_y - 48)], f"garr/{v}/b2", NEGRO, 9))
    partes.append(figura(elipse(0, 0, rx, ry, n=44), f"garr/{v}/cuerpo", color))
    partes.append(figura(elipse(0, -ry * 0.5, rx * 0.62, ry * 0.42, n=30), f"garr/{v}/escudo", NEGRO, amplitud=0.8))
    if v in ("normal", "irritada"):
        partes.append(raya(arco(-rx * 0.25, ry * 0.15, rx * 0.35, ry * 0.4, 110, 200, 8), f"garr/{v}/brillo",
                           BLANCO, 8, 0.5))
    if v == "irritada":                                      # rayitas de enojo
        for i, (x, y, a) in enumerate(((-rx - 95, -ry, -30), (rx + 95, -ry, 30), (0, -ry - 110, 0))):
            ca, sa = math.cos(math.radians(a - 90)), math.sin(math.radians(a - 90))
            pts = [(x + ca * k * 18 + (8 if k % 2 else -8) * -sa, y + sa * k * 18 + (8 if k % 2 else -8) * ca)
                   for k in range(4)]
            partes.append(raya(pts, f"garr/ira{i}", ROJO, 9))
    if v == "apretada":
        for i, x in enumerate((-rx - 40, rx + 40)):
            partes.append(figura([(x, -24)] + arco(x, 6, 18, 18, -20, 200, 10), f"garr/gota{i}", ROJO))
    m = max(rx + 110, 160)
    return Dibujo("".join(partes), (-m, -ry - 160, 2 * m, 2 * ry + 260))


def _pierna_pts():
    """Pierna de lado: la espinilla baja desde arriba y el pie apunta a la derecha (suela en y=0)."""
    return [(-72, -440), (58, -440), (52, -150), (66, -96), (190, -64), (246, -36), (252, 0),
            (-88, 0), (-94, -56), (-74, -150)]


def pierna(e: dict) -> Dibujo:
    """Pierna y pie (piel crema). El tobillo queda cerca de (40, -120)."""
    partes = [figura(_pierna_pts(), "pierna", CREMA),
              raya(arco(46, -116, 18, 18, 200, 340, 8), "pierna/tob", NEGRO, 5, 0.5)]
    return Dibujo("".join(partes), (-105, -452, 370, 465))


def calcetin(e: dict) -> Dibujo:
    """Calcetín blanco con franjas grises; va encima de «pierna» (mismo origen) y sale deslizando."""
    pts = [(-80, -280), (66, -280), (60, -150), (72, -100), (194, -70), (252, -40), (258, 6),
           (-94, 6), (-100, -56), (-82, -150)]
    partes = [figura(pts, "calcetin", BLANCO)]
    for i, y in enumerate((-256, -228)):
        partes.append(raya([(-78, y), (62, y)], f"calcetin/f{i}", GRIS, 9, 0.6))
    partes.append(raya([(-90, -10), (-86, -60), (-62, -70)], "calcetin/talon", GRIS, 9, 0.6))
    return Dibujo("".join(partes), (-115, -295, 390, 315))


def brazo(e: dict) -> Dibujo:
    """Brazo amarillo que entra desde la derecha; la mano (punta) queda en (0, 0)."""
    partes = [tubo([(520, 60), (260, 30), (40, 0)], "brazo", AMARILLO, 30),
              tubo([(40, 0), (-6, -16)], "brazo/d1", AMARILLO, 14),
              tubo([(40, 4), (-2, 22)], "brazo/d2", AMARILLO, 14)]
    return Dibujo("".join(partes), (-40, -60, 600, 160))


def dedos(e: dict) -> Dibujo:
    """Mano amarilla pinzando con dos dedos (tirar con los dedos / apretar); las yemas en (0, 0)."""
    ab = 22 if e.get("cerrados", False) else 60
    partes = [tubo([(520, 40), (240, 10)], "dedos/brazo", AMARILLO, 30),
              tubo([(190, -20), (90, -ab - 20), (8, -ab)], "dedos/a", AMARILLO, 24),
              tubo([(190, 20), (90, ab + 20), (8, ab)], "dedos/b", AMARILLO, 24),
              figura(elipse(205, 0, 62, 54, n=30), "dedos/puno", AMARILLO)]
    return Dibujo("".join(partes), (-30, -130, 590, 260))


def pinzas(e: dict) -> Dibujo:
    """Pinzas de punta plana (gris) apuntando a la izquierda; la punta queda en (0, 0)."""
    ab = 12 if e.get("cerradas", False) else 40
    partes = [figura([(330, -26), (40, -ab - 16), (0, -ab - 12), (0, -ab + 6), (40, -ab + 6), (330, -2)],
                     "pinzas/a", GRIS),
              figura([(330, 26), (40, ab + 16), (0, ab + 12), (0, ab - 6), (40, ab - 6), (330, 2)], "pinzas/b", GRIS)]
    return Dibujo("".join(partes), (-20, -80, 360, 160))


def encendedor(e: dict) -> Dibujo:
    """Encendedor con llama; «llama» = amarillo o rojo (alternar color)."""
    llama = ROJO if e.get("llama") == "rojo" else AMARILLO
    partes = [figura(_rect(-60, -40, 120, 210, 22), "enc/cuerpo", ROJO),
              figura(_rect(-58, -96, 116, 60, 10), "enc/metal", GRIS),
              figura(elipse(28, -108, 20, 14, n=16), "enc/rueda", GRIS_OSCURO, amplitud=0.6),
              figura([(-16, -100), (-30, -160), (-8, -205), (4, -175), (22, -230), (34, -160), (14, -100)],
                     "enc/llama", llama)]
    return Dibujo("".join(partes), (-75, -245, 150, 430))


def aceite(e: dict) -> Dibujo:
    partes = [figura([(-30, -170), (30, -170), (30, -120), (80, -60), (80, 160), (-80, 160), (-80, -60), (-30, -120)],
                     "aceite/bot", BLANCO),
              figura([(-76, -10), (76, -10), (76, 156), (-76, 156)], "aceite/liq", AMARILLO, amplitud=0.8),
              figura(_rect(-36, -210, 72, 44, 10), "aceite/tapa", GRIS),
              figura([(0, 40)] + arco(0, 82, 26, 26, -20, 200, 10), "aceite/gota", BLANCO)]
    return Dibujo("".join(partes), (-95, -225, 190, 400))


def vaselina(e: dict) -> Dibujo:
    partes = [figura(_rect(-110, -40, 220, 150, 26), "vas/frasco", BLANCO),
              figura(_rect(-80, 0, 160, 76, 12), "vas/etiq", AMARILLO),
              figura(_rect(-120, -90, 240, 60, 16), "vas/tapa", GRIS)]
    return Dibujo("".join(partes), (-135, -105, 270, 230))


PIEZAS = {
    "personaje": personaje, "vecino": vecino, "gente": gente,
    "x_roja": x_roja, "chulo": chulo, "flecha": flecha, "rotulo": rotulo, "numero": numero,
    "barra": barra, "cronometro": cronometro, "calendario": calendario, "documento": documento,
    "casa": casa, "gotas": gotas, "vena": vena,
    "garrapata": garrapata, "pierna": pierna, "calcetin": calcetin, "brazo": brazo, "dedos": dedos,
    "pinzas": pinzas, "encendedor": encendedor, "aceite": aceite, "vaselina": vaselina,
}


def dibujar(pieza: str, estado: dict) -> Dibujo:
    if pieza not in PIEZAS:
        raise KeyError(f"no hay pieza «{pieza}» (hay: {', '.join(sorted(PIEZAS))})")
    return PIEZAS[pieza](estado)
