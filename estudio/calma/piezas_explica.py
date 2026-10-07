"""Piezas de El Calvo Explica: cuadrícula de temas, textos, corchete rojo, íconos para diagramas e imágenes.

Mismo trazo de marcador que el resto (trazo.py). Se registran en `piezas.PIEZAS` al importar piezas.py.
"""
from __future__ import annotations

import base64
import math
from pathlib import Path

from . import personaje as P
from .piezas import PIEZAS, Dibujo, _rect, _texto, ancho_texto, dibujar
from .trazo import AMARILLO, BLANCO, CREMA, GRIS, NEGRO, ROJO, arco, elipse, figura, raya, tubo

ROSA = "#F2A7A0"


# ------------------------------------------------------------------ textos

def texto(e: dict) -> Dibujo:
    """Etiqueta suelta en mayúsculas: negra (bajo las imágenes) o roja (palabra clave). Sin caja."""
    t = str(e.get("texto", "")).upper()
    alto = float(e.get("alto", 72))
    color = ROJO if e.get("color") == "rojo" else NEGRO
    w = ancho_texto(t, alto) + 20
    return Dibujo(_texto(0, alto * 0.04, t, alto, color), (-w / 2, -alto * 0.8, w, alto * 1.6))


def titulo_tema(e: dict) -> Dibujo:
    """El nombre del tema en grande, mayúsculas, negro (una palabra puede ir en rojo con «rojo»)."""
    t = str(e.get("texto", "")).upper()
    alto = float(e.get("alto", 110))
    rojo = str(e.get("rojo", "")).upper()
    w = ancho_texto(t, alto) + 30
    if rojo and rojo in t:
        a, _, b = t.partition(rojo)
        x = -w / 2 + 15
        partes = []
        for trozo, color in ((a, NEGRO), (rojo, ROJO), (b, NEGRO)):
            limpio = trozo.strip()
            if trozo.startswith(" "):                  # el SVG se come los espacios de las orillas
                x += ancho_texto(" ", alto)
            if limpio:
                partes.append(_texto(x, alto * 0.04, limpio, alto, color, ancla="start"))
                x += ancho_texto(limpio, alto)
            if trozo.endswith(" ") and limpio:
                x += ancho_texto(" ", alto)
        return Dibujo("".join(partes), (-w / 2, -alto * 0.8, w, alto * 1.6))
    return Dibujo(_texto(0, alto * 0.04, t, alto), (-w / 2, -alto * 0.8, w, alto * 1.6))


# ------------------------------------------------------------------ cuadrícula de temas

def circulo_tema(e: dict) -> Dibujo:
    """Un tema de la cuadrícula: círculo con su ícono adentro y la etiqueta debajo.
    «icono»: {"pieza": ..., "estado": {...}, "escala": ...} o «?» para un tema sin revelar."""
    r = 120
    relleno = AMARILLO if e.get("actual") else "#E4E4E4" if e.get("visto") else BLANCO
    partes = [figura(elipse(0, 0, r, r, n=60), f"circ/{e.get('etiqueta', '')}", relleno)]
    ic = e.get("icono")
    if ic == "?" or not ic:
        partes.append(_texto(0, 8, "?", 150, GRIS))
    else:
        d = dibujar(ic["pieza"], ic.get("estado", {}))
        x0, y0, w, h = d.caja
        k = float(ic.get("escala", 0)) or min(1.5 * r / w, 1.5 * r / h)
        cx, cy = x0 + w / 2, y0 + h / 2
        partes.append(f'<g transform="scale({k:.3f}) translate({-cx:.1f},{-cy:.1f})">{d.svg}</g>')
    if e.get("visto"):                                # ya explicado: chulo verde encima
        partes.append(f'<g transform="translate({r * 0.62:.1f},{-r * 0.62:.1f}) scale(0.42)">'
                      f'{PIEZAS["chulo"]({}).svg}</g>')
    etiqueta = str(e.get("etiqueta", "")).upper()
    if etiqueta:
        lineas = [etiqueta]
        if ancho_texto(etiqueta, 46) > 2.6 * r and " " in etiqueta:      # en dos renglones parejos
            palabras = etiqueta.split()
            corte = min(range(1, len(palabras)),
                        key=lambda k: abs(len(" ".join(palabras[:k])) - len(" ".join(palabras[k:]))))
            lineas = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
        alto = min([46.0] + [2.6 * r / ancho_texto(l, 1) for l in lineas])
        for k, linea in enumerate(lineas):
            partes.append(_texto(0, r + 50 + k * alto * 1.1, linea, alto))
    return Dibujo("".join(partes), (-1.35 * r, -r - 14, 2.7 * r, 2 * r + 140))


# ------------------------------------------------------------------ resaltar

def corchete(e: dict) -> Dibujo:
    """Corchete rojo para resaltar algo (abre hacia la derecha; gíralo con «rotacion»)."""
    alto = float(e.get("alto", 300))
    pts = [(30, -alto / 2), (0, -alto / 2), (0, alto / 2), (30, alto / 2)]
    return Dibujo(tubo(pts, f"corchete/{alto:.0f}", ROJO, 14, float(e.get("trazo", 1))),
                  (-30, -alto / 2 - 30, 90, alto + 60))


def circulo_rojo(e: dict) -> Dibujo:
    """Óvalo rojo a mano alrededor de algo."""
    rx, ry = float(e.get("ancho", 220)) / 2, float(e.get("alto", 160)) / 2
    pts = arco(0, 0, rx, ry, -100, 250, 40)
    return Dibujo(tubo(pts, "circ_rojo", ROJO, 10, float(e.get("trazo", 1))),
                  (-rx - 30, -ry - 30, 2 * rx + 60, 2 * ry + 60))


# ------------------------------------------------------------------ íconos (diagramas)

def cerebro(e: dict) -> Dibujo:
    partes = [figura(elipse(0, 0, 150, 110, n=60), "cerebro", ROSA)]
    for i, pts in enumerate(([(-110, -20), (-70, -50), (-40, -10), (-10, -60)],
                             [(-100, 40), (-60, 10), (-20, 50), (20, 20)],
                             [(20, -70), (40, -20), (80, -50), (110, -10)],
                             [(40, 30), (70, 70), (110, 40)])):
        partes.append(raya(pts, f"cerebro/p{i}", NEGRO, 6))
    partes.append(raya([(0, -108), (6, -40), (-4, 30), (4, 108)], "cerebro/mitad", NEGRO, 6))
    if e.get("despierta"):                          # la parte que sigue despierta, en amarillo
        partes.append(figura(elipse(80, -40, 52, 40, n=26), "cerebro/despierta", AMARILLO, amplitud=0.8))
    return Dibujo("".join(partes), (-170, -130, 340, 260))


def musculo(e: dict) -> Dibujo:
    """Brazo doblado mostrando el músculo. «relajado»: el brazo cuelga y no hay bulto."""
    if e.get("relajado"):
        partes = [tubo([(-150, -60), (10, -50), (40, 110)], "musc/rel", CREMA, 54),
                  figura(elipse(48, 130, 34, 30, n=20), "musc/rel/puno", CREMA)]
    else:
        partes = [tubo([(-150, 50), (40, 50), (50, -110)], "musc/tenso", CREMA, 54),
                  figura(elipse(-45, 12, 72, 46, n=34), "musc/bulto", CREMA),
                  figura(elipse(52, -128, 36, 32, n=20), "musc/puno", CREMA)]
    return Dibujo("".join(partes), (-200, -180, 300, 360))


def rayo(e: dict) -> Dibujo:
    color = ROJO if e.get("color") == "rojo" else AMARILLO
    pts = [(10, -90), (-40, 10), (0, 10), (-20, 90), (50, -20), (10, -20), (30, -90)]
    return Dibujo(figura(pts, f"rayo/{color}", color), (-60, -105, 125, 210))


def corazon(e: dict) -> Dibujo:
    pts = arco(-40, -20, 42, 42, 150, 340, 14) + arco(40, -20, 42, 42, 200, 390, 14) + [(0, 90)]
    return Dibujo(figura(pts, "corazon", ROJO), (-100, -80, 200, 190))


def cafe(e: dict) -> Dibujo:
    partes = [figura([(-70, -40), (70, -40), (55, 80), (-55, 80)], "cafe/taza", BLANCO),
              tubo(arco(75, 15, 30, 30, -80, 80, 10), "cafe/asa", BLANCO, 10),
              figura(elipse(0, -38, 68, 12, n=24), "cafe/liq", "#6B3F22", amplitud=0.6)]
    for i, x in enumerate((-25, 15)):
        partes.append(raya([(x, -60), (x + 12, -85), (x - 4, -110), (x + 8, -135)], f"cafe/humo{i}", GRIS, 7))
    return Dibujo("".join(partes), (-90, -150, 210, 245))


def zzz(e: dict) -> Dibujo:
    partes = []
    for i, (x, y, k) in enumerate(((0, 30, 1.0), (60, -30, 0.75), (105, -80, 0.55))):
        s = 50 * k
        partes.append(raya([(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x - s / 2, y + s / 2), (x + s / 2, y + s / 2)],
                           f"zzz/{i}", NEGRO, 9))
    return Dibujo("".join(partes), (-40, -110, 190, 180))


def escalon(e: dict) -> Dibujo:
    """Escalera gris que sube y le falta el último escalón (dibujado punteado)."""
    partes = [figura([(-250, 120), (-250, 60), (-170, 60), (-170, 0), (-90, 0), (-90, -60), (-10, -60), (-10, 120)],
                     "escalon/esc", GRIS),
              f'<path d="M -10 -120 L 70 -120 L 70 120" fill="none" stroke="{NEGRO}" stroke-width="7" '
              f'stroke-dasharray="18 14" stroke-linecap="round"/>']
    return Dibujo("".join(partes), (-265, -140, 350, 275))


def estres(e: dict) -> Dibujo:
    """Nube de tormenta (estrés)."""
    partes = [figura(elipse(-50, 0, 60, 45, n=26) , "estres/n1", GRIS), figura(elipse(30, -20, 70, 55, n=30), "estres/n2", GRIS),
              figura(elipse(80, 10, 50, 40, n=24), "estres/n3", GRIS),
              figura([(0, 40), (-20, 90), (5, 90), (-10, 130), (30, 75), (5, 75), (20, 40)], "estres/rayo", AMARILLO)]
    return Dibujo("".join(partes), (-125, -90, 270, 235))


def imagen(e: dict) -> Dibujo:
    """Ilustración generada (PNG/JPG) como pieza, con marco fino opcional. «ancho» en px de 1080."""
    ruta = Path(e["archivo"])
    from PIL import Image

    with Image.open(ruta) as im:
        w0, h0 = im.size
    ancho = float(e.get("ancho", 1500))
    alto = ancho * h0 / w0
    datos = base64.b64encode(ruta.read_bytes()).decode()
    mime = "image/png" if ruta.suffix.lower() == ".png" else "image/jpeg"
    svg = (f'<image x="{-ancho / 2:.1f}" y="{-alto / 2:.1f}" width="{ancho:.1f}" height="{alto:.1f}" '
           f'href="data:{mime};base64,{datos}"/>')
    return Dibujo(svg, (-ancho / 2 - 4, -alto / 2 - 4, ancho + 8, alto + 8))


def lineas_movimiento(e: dict) -> Dibujo:
    """Rayitas alrededor de algo que se sacude."""
    partes = []
    for i, a in enumerate((-160, -120, -60, -20, 200, 160)):
        c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
        partes.append(raya([(c * 150, s * 150), (c * 200, s * 200)], f"mov/{i}", NEGRO, 8,
                           parcial=float(e.get("trazo", 1))))
    return Dibujo("".join(partes), (-215, -215, 430, 430))


PIEZAS.update({
    "texto": texto, "titulo_tema": titulo_tema, "circulo_tema": circulo_tema, "corchete": corchete,
    "circulo_rojo": circulo_rojo, "cerebro": cerebro, "musculo": musculo, "rayo": rayo, "corazon": corazon,
    "cafe": cafe, "zzz": zzz, "escalon": escalon, "estres": estres, "imagen": imagen,
    "lineas_movimiento": lineas_movimiento,
})

# ------------------------------------------------------------------ primer video: partes que ya no sirven

def muneca(e: dict) -> Dibujo:
    """Primer plano de la mano del personaje (amarilla), palma hacia ti y la muñeca abajo.
    «dedos»: abierta | pinza (pulgar tocando el meñique). «tendon»: el cordón que salta en el centro."""
    pinza = e.get("dedos") == "pinza"
    partes = [tubo([(0, 460), (0, 60)], "mun/antebrazo", AMARILLO, 170)]
    dedos = [("indice", (-62, -120), (-78, -330)), ("medio", (-18, -130), (-20, -360)),
             ("anular", (30, -125), (44, -335))]
    for nombre, a, b in dedos:
        partes.append(tubo([a, b], f"mun/{nombre}", AMARILLO, 50))
    if pinza:
        partes.append(tubo([(78, -100), (108, -185), (66, -222)], "mun/menique_p", AMARILLO, 46))
    else:
        partes.append(tubo([(78, -100), (124, -270)], "mun/menique", AMARILLO, 46))
        partes.append(tubo([(-118, 10), (-210, -110)], "mun/pulgar", AMARILLO, 52))
    partes.append(figura(elipse(-4, -20, 128, 140, n=60), "mun/palma", AMARILLO))
    if pinza:                                          # el pulgar va por encima de la palma
        partes.append(tubo([(-118, 0), (-70, -140), (10, -205), (52, -218)], "mun/pulgar_p2", AMARILLO, 52))
        partes.append(figura(elipse(58, -220, 30, 26, n=20), "mun/yemas", AMARILLO, amplitud=0.6))
    partes += [raya(arco(0, 150, 70, 16, 200, 340, 10), "mun/pliegue1", NEGRO, 5),
               raya(arco(0, 185, 62, 14, 200, 340, 10), "mun/pliegue2", NEGRO, 5)]
    if e.get("tendon"):
        partes += [f'<path d="M -9 330 L -11 110 L 11 110 L 9 330 Z" fill="#FFE98A" stroke="none"/>',
                   raya([(-11, 330), (-12, 110)], "mun/tend1", NEGRO, 6),
                   raya([(11, 330), (12, 110)], "mun/tend2", NEGRO, 6)]
    return Dibujo("".join(partes), (-260, -400, 420, 870))


def rama(e: dict) -> Dibujo:
    """Rama de árbol gris con hojas verdes (para trepar y colgarse)."""
    partes = [tubo([(-420, 10), (-100, -6), (200, 8), (430, -10)], "rama", "#8A8A8A", 34),
              tubo([(-200, 0), (-260, -90)], "rama/r1", "#8A8A8A", 16),
              tubo([(240, 4), (300, -80)], "rama/r2", "#8A8A8A", 16)]
    for i, (x, y) in enumerate(((-270, -110), (-230, -120), (300, -100), (340, -80), (420, -40))):
        partes.append(figura(elipse(x, y, 34, 18, rot=-30 + 20 * i, n=18), f"rama/h{i}", "#5BB85C", amplitud=0.7))
    return Dibujo("".join(partes), (-445, -150, 900, 190))


def fila_personas(e: dict) -> Dibujo:
    """Fila de personas en gris; la «destacada» va en rojo (una de cada siete)."""
    n = int(e.get("cuantas", 7))
    dest = e.get("destacada")
    partes = []
    for i in range(n):
        x = (i - (n - 1) / 2) * 170
        color = ROJO if dest == i else "#B5B5B5"
        partes.append(f'<g transform="translate({x:.1f},0) scale(0.55)">'
                      f'{P.personaje("de_pie", "abiertos", "amable", color, False)}</g>')
    w = n * 170 + 60
    return Dibujo("".join(partes), (-w / 2, -330, w, 350))


def grafica_barras(e: dict) -> Dibujo:
    """Gráfica simple de barras grises sin números (para «cambia mucho de un lugar a otro»)."""
    valores = e.get("valores", [0.4, 0.8, 0.25, 0.6, 0.15])
    w, h = 700, 380
    partes = [raya([(-w / 2, -h / 2), (-w / 2, h / 2), (w / 2, h / 2)], "graf/ejes", NEGRO, 8)]
    paso = (w - 60) / len(valores)
    for i, v in enumerate(valores):
        alto = (h - 30) * max(0.05, min(1.0, float(v)))
        x = -w / 2 + 40 + i * paso
        partes.append(figura([(x, h / 2), (x, h / 2 - alto), (x + paso * 0.62, h / 2 - alto), (x + paso * 0.62, h / 2)],
                             f"graf/b{i}", ROJO if i == e.get("destacada") else GRIS))
    return Dibujo("".join(partes), (-w / 2 - 20, -h / 2 - 20, w + 40, h + 40))


def cordon(e: dict) -> Dibujo:
    """Un tendón suelto, como un cordón (el repuesto que usan los cirujanos)."""
    pts = [(-260, 20), (-140, -30), (0, 10), (140, -20), (260, 15)]
    return Dibujo(tubo(pts, "cordon", "#FFE98A", 22, float(e.get("trazo", 1))), (-290, -70, 580, 130))


PIEZAS.update({"muneca": muneca, "rama": rama, "fila_personas": fila_personas, "grafica_barras": grafica_barras,
               "cordon": cordon})

_ = (P, BLANCO, _rect)
