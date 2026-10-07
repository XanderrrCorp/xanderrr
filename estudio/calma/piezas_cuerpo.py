"""Piezas del primer video de El Calvo Explica («Partes de tu cuerpo que YA NO SIRVEN»): partes del cuerpo y
animales simples, con el mismo trazo de marcador. Se registran en `piezas.PIEZAS`."""
from __future__ import annotations

import math

from .piezas import PIEZAS, Dibujo, dibujar
from .trazo import AMARILLO, BLANCO, CREMA, GRIS, NEGRO, ROJO, VERDE, arco, elipse, figura, raya, tubo

ROSA = "#F2A7A0"
GRIS_GATO = "#B9B9B9"


def oreja(e: dict) -> Dibujo:
    """Oreja de perfil (crema). «bulto»: el piquito en el borde de arriba. «punta»: oreja de animal."""
    borde = arco(0, -10, 120, 175, 200, 520, 40)
    if e.get("punta"):
        borde = [(-95, -60), (-20, -300), (90, -80)] + arco(0, 20, 110, 150, -20, 160, 20)
    partes = [figura(borde, "oreja/borde" + ("p" if e.get("punta") else ""), CREMA)]
    partes.append(raya(arco(10, 10, 70, 110, 230, 470, 24), "oreja/dentro", NEGRO, 6))
    partes.append(raya(arco(20, 40, 28, 40, 180, 400, 12), "oreja/hueco", NEGRO, 6))
    if e.get("bulto"):
        partes.append(figura(elipse(95, -120, 22, 18, rot=30, n=16), "oreja/bulto", CREMA, amplitud=0.6))
    return Dibujo("".join(partes), (-160, -330, 330, 540))


def gato(e: dict) -> Dibujo:
    """Cabeza de gato gris (sin marca ni raza): orejas en punta que giran con «giro_orejas»; «erizado»: pelo
    parado; «oliendo»: boca entreabierta (mueca de oler)."""
    g = float(e.get("giro_orejas", 0))
    partes = []
    for lado in (-1, 1):
        base = (lado * 70, -70)
        ang = math.radians(-90 + lado * (25 + g))
        punta = (base[0] + math.cos(ang) * 120, base[1] + math.sin(ang) * 120)
        partes.append(figura([(base[0] - 45, base[1] + 20), punta, (base[0] + 45, base[1] + 20)],
                             f"gato/oreja{lado}", GRIS_GATO))
        partes.append(figura([(base[0] - 22, base[1] + 5), (base[0] + (punta[0] - base[0]) * 0.6,
                                                           base[1] + (punta[1] - base[1]) * 0.6), (base[0] + 22, base[1] + 5)],
                             f"gato/oreja_in{lado}", ROSA, amplitud=0.6))
    if e.get("erizado"):
        for i in range(18):
            a = math.radians(-180 + i * 20)
            partes.append(raya([(math.cos(a) * 140, math.sin(a) * 125 + 10), (math.cos(a) * 175, math.sin(a) * 160 + 10)],
                               f"gato/pelo{i}", NEGRO, 7))
    partes.append(figura(elipse(0, 10, 145, 130, n=50), "gato/cara", GRIS_GATO))
    for lado in (-1, 1):
        partes.append(figura(elipse(lado * 55, -10, 24, 30, n=20), f"gato/ojo{lado}", "#D9E87A", amplitud=0.6))
        partes.append(f'<ellipse cx="{lado * 55}" cy="-10" rx="7" ry="22" fill="{NEGRO}"/>')
        for k in (-1, 1):
            partes.append(raya([(lado * 60, 55 + k * 10), (lado * 160, 45 + k * 25)], f"gato/bigote{lado}{k}", NEGRO, 4))
    partes.append(figura([(-16, 30), (16, 30), (0, 46)], "gato/nariz", ROSA, amplitud=0.4))
    if e.get("oliendo"):
        partes.append(figura(elipse(0, 78, 26, 16, n=18), "gato/boca_o", NEGRO, amplitud=0.5))
    else:
        partes.append(raya([(-26, 62), (-12, 72), (0, 60), (12, 72), (26, 62)], "gato/boca", NEGRO, 6))
    return Dibujo("".join(partes), (-215, -240, 430, 450))


def ondas(e: dict) -> Dibujo:
    """Ondas de sonido (o de señal) que salen hacia la derecha."""
    color = ROJO if e.get("color") == "rojo" else NEGRO
    partes = [raya(arco(0, 0, 40 + 40 * i, 40 + 40 * i, -40, 40, 10), f"ondas/{i}", color, 9,
                   parcial=float(e.get("trazo", 1))) for i in range(3)]
    return Dibujo("".join(partes), (-10, -110, 170, 220))


def piel(e: dict) -> Dibujo:
    """Pedazo de piel del brazo con pelitos: acostados, o parados con puntitos («parados»)."""
    w, h = 700, 300
    partes = [figura([(-w / 2, -h / 2), (w / 2, -h / 2 + 20), (w / 2, h / 2), (-w / 2, h / 2 - 20)], "piel", CREMA)]
    parados = e.get("parados")
    for i in range(14):
        x = -w / 2 + 50 + i * (w - 100) / 13
        y = -20 + (i % 3) * 30
        if parados:
            partes.append(f'<circle cx="{x:.1f}" cy="{y + 6:.1f}" r="11" fill="#E9C9A0" stroke="{NEGRO}" stroke-width="4"/>')
            partes.append(raya([(x, y), (x + 4, y - 60)], f"piel/p{i}", NEGRO, 5))
        else:
            partes.append(raya([(x - 20, y + 4), (x + 30, y - 6)], f"piel/a{i}", NEGRO, 5))
    return Dibujo("".join(partes), (-w / 2 - 12, -h / 2 - 90, w + 24, h + 110))


def nieve(e: dict) -> Dibujo:
    partes = []
    for i, (x, y) in enumerate(((-200, -60), (-60, 40), (90, -80), (210, 30), (-140, 120), (150, 130))):
        for k in range(3):
            a = math.radians(k * 60)
            partes.append(raya([(x - 22 * math.cos(a), y - 22 * math.sin(a)), (x + 22 * math.cos(a), y + 22 * math.sin(a))],
                               f"nieve/{i}{k}", "#7FA8C9", 5))
    return Dibujo("".join(partes), (-240, -120, 480, 290))


def ojo(e: dict) -> Dibujo:
    """Ojo humano de cerca, con el pliegue rosado en la esquina de adentro (a la izquierda).
    «animal»: un tercer párpado gris que cruza medio ojo."""
    partes = [figura(arco(0, 0, 260, 120, 180, 360, 30) + arco(0, 0, 260, 120, 0, 180, 30), "ojo/forma", BLANCO),
              figura(elipse(20, 0, 95, 95, n=40), "ojo/iris", "#8A6A3E", amplitud=0.8),
              f'<circle cx="20" cy="0" r="42" fill="{NEGRO}"/><circle cx="42" cy="-22" r="14" fill="{BLANCO}"/>']
    if e.get("animal"):
        partes.append(figura([(-255, -10), (-60, -110), (40, -60), (60, 40), (-60, 100), (-250, 15)], "ojo/tercer", "#C9C9C9"))
    else:
        partes.append(figura(arco(-230, 0, 34, 60, 270, 450, 14), "ojo/pliegue", ROSA, amplitud=0.6))
    partes.append(raya(arco(0, -10, 280, 160, 200, 340, 24), "ojo/parpado", NEGRO, 7))
    return Dibujo("".join(partes), (-290, -185, 580, 320))


def boca(e: dict) -> Dibujo:
    """Fila de muelas de abajo vista de lado. «grande»: mandíbula larga (cabe la del juicio);
    «torcida»: la última muela sale inclinada empujando a las demás."""
    grande = e.get("grande")
    largo = 820 if grande else 640
    partes = [figura([(-largo / 2, 0), (largo / 2, 0), (largo / 2 - 30, 130), (-largo / 2 + 30, 130)], "boca/encia", ROSA)]
    n = 5 if not grande else 6
    for i in range(n):
        x = -largo / 2 + 70 + i * 120
        ultima = i == n - 1
        rot = -28 if (ultima and e.get("torcida")) else 0
        color = AMARILLO if ultima and e.get("resaltar") else BLANCO
        cx, cy = x + 40, -40
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        pts = [(-45, 40), (-50, -40), (-25, -60), (0, -45), (25, -60), (50, -40), (45, 40)]
        pts = [(cx + px * c - py * s, cy + px * s + py * c) for px, py in pts]
        partes.append(figura(pts, f"boca/m{i}{'t' if rot else ''}", color))
    return Dibujo("".join(partes), (-largo / 2 - 20, -130, largo + 40, 280))


def columna(e: dict) -> Dibujo:
    """Columna vista de lado: vértebras grises y, abajo, el coxis (en rojo si «resaltar»)."""
    partes = []
    for i in range(9):
        y = -400 + i * 75
        x = 20 * math.sin(i / 3)
        partes.append(figura([(x - 50, y), (x + 50, y + 6), (x + 46, y + 56), (x - 46, y + 50)], f"col/v{i}", "#E2E2E2"))
    color = ROJO if e.get("resaltar") else "#E2E2E2"
    for i, (x, y, k) in enumerate(((10, 290, 1.0), (0, 335, 0.8), (-12, 372, 0.6), (-26, 402, 0.45))):
        partes.append(figura(elipse(x, y, 34 * k + 6, 18 * k + 5, rot=20, n=16), f"col/c{i}", color, amplitud=0.6))
    return Dibujo("".join(partes), (-90, -420, 180, 860))


def embrion(e: dict) -> Dibujo:
    """Embrión simple y tierno (curvado), con colita si «cola»."""
    partes = [figura(arco(0, 20, 120, 150, 120, 420, 40), "emb/cuerpo", "#F6D3C4"),
              figura(elipse(-10, -120, 90, 80, n=36), "emb/cabeza", "#F6D3C4"),
              f'<circle cx="-30" cy="-120" r="10" fill="{NEGRO}"/>']
    if e.get("cola", True):
        partes.append(tubo([(60, 140), (110, 190), (90, 230)], "emb/cola", "#F6D3C4", 26))
    return Dibujo("".join(partes), (-150, -215, 300, 470))


def nariz(e: dict) -> Dibujo:
    """Cabeza de perfil (crema) con la nariz a la derecha; «sensor»: punto amarillo dentro de la nariz;
    «desconectado»: un cable que no llega al cerebro."""
    partes = [figura(arco(0, 0, 200, 220, 150, 365, 40) + [(205, -40), (300, 70), (210, 95), (180, 180), (-150, 140)],
                     "nariz/cabeza", CREMA)]
    partes.append(f'<circle cx="110" cy="-30" r="12" fill="{NEGRO}"/>')
    if e.get("sensor"):
        partes.append(figura(elipse(225, 45, 24, 17, n=16), "nariz/sensor", AMARILLO, amplitud=0.5))
    if e.get("desconectado"):
        partes.append(f'<path d="M 205 40 C 140 0 70 -60 30 -80" fill="none" stroke="{ROJO}" stroke-width="7" '
                      f'stroke-dasharray="16 12" stroke-linecap="round"/>')
        partes.append(figura(elipse(-40, -110, 85, 60, n=30), "nariz/cerebro", "#F2A7A0"))
    return Dibujo("".join(partes), (-230, -245, 560, 470))


def bebe(e: dict) -> Dibujo:
    """Bebé recién nacido envuelto en una cobija; «agarra»: su manita aprieta un dedo amarillo."""
    partes = [figura(elipse(0, 120, 150, 120, n=40), "bebe/cobija", "#DDE8F2"),
              figura(elipse(0, -40, 110, 100, n=40), "bebe/cara", CREMA),
              raya(arco(-38, -40, 18, 10, 20, 160, 8), "bebe/ojo1", NEGRO, 5),
              raya(arco(38, -40, 18, 10, 20, 160, 8), "bebe/ojo2", NEGRO, 5),
              raya(arco(0, 5, 16, 10, 20, 160, 8), "bebe/boca", NEGRO, 5)]
    if e.get("agarra"):
        partes += [tubo([(420, 40), (170, 60)], "bebe/dedo", AMARILLO, 40),
                   figura(elipse(150, 60, 42, 38, n=22), "bebe/mano", CREMA)]
    return Dibujo("".join(partes), (-170, -160, 620, 410))


def intestino(e: dict) -> Dibujo:
    """Intestino simplificado (tubo rosado en curvas) con el apéndice colgando abajo a la izquierda (en rojo si
    «resaltar»). «bacterias»: puntitos verdes adentro del apéndice."""
    pts = [(-260, 120), (-260, -160), (260, -160), (260, 140), (-150, 140), (-150, -60), (150, -60), (150, 50), (-40, 50)]
    partes = [tubo(pts, "int/tubo", "#F2B8A8", 70)]
    partes.append(tubo([(-260, 150), (-240, 260), (-200, 300)], "int/apendice", ROJO if e.get("resaltar") else "#F2B8A8", 30))
    if e.get("bacterias"):
        for i, (x, y) in enumerate(((-245, 215), (-228, 255), (-212, 285))):
            partes.append(figura(elipse(x, y, 11, 8, rot=30 * i, n=12), f"int/b{i}", VERDE, amplitud=0.4))
    return Dibujo("".join(partes), (-320, -220, 640, 560))


def bacterias(e: dict) -> Dibujo:
    """Grupito de bacterias buenas (verdes, con carita)."""
    partes = []
    for i, (x, y, r) in enumerate(((-70, 0, 1.0), (40, -40, 0.85), (60, 60, 0.9), (-20, 80, 0.7))):
        partes.append(figura(elipse(x, y, 46 * r, 30 * r, rot=20 * i, n=20), f"bac/{i}", VERDE))
        partes.append(f'<circle cx="{x - 10 * r:.1f}" cy="{y - 4:.1f}" r="4" fill="{NEGRO}"/>'
                      f'<circle cx="{x + 10 * r:.1f}" cy="{y - 4:.1f}" r="4" fill="{NEGRO}"/>')
    return Dibujo("".join(partes), (-130, -90, 250, 210))


def torso(e: dict) -> Dibujo:
    """Silueta neutra de un torso gris con dos puntos (sin detalles), para el tema de las tetillas."""
    partes = [figura([(-150, -200), (150, -200), (130, 220), (-130, 220)], "torso", "#D5D5D5"),
              f'<circle cx="-65" cy="-60" r="10" fill="#B07A6A"/><circle cx="65" cy="-60" r="10" fill="#B07A6A"/>']
    return Dibujo("".join(partes), (-165, -215, 330, 450))


def plano(e: dict) -> Dibujo:
    """Un plano (hoja cuadriculada) con la silueta de un cuerpo: «el mismo plano para todos»."""
    w, h = 360, 460
    partes = [figura([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)], "plano/hoja", "#EAF1F6")]
    for i in range(1, 6):
        partes.append(raya([(-w / 2 + i * w / 6, -h / 2 + 10), (-w / 2 + i * w / 6, h / 2 - 10)], f"plano/v{i}", "#B9CCD9", 3, 0.3))
        partes.append(raya([(-w / 2 + 10, -h / 2 + i * h / 6), (w / 2 - 10, -h / 2 + i * h / 6)], f"plano/h{i}", "#B9CCD9", 3, 0.3))
    partes.append(f'<g transform="translate(0,190) scale(0.62)">'
                  f'{dibujar("personaje", {"pose": "de_pie", "gesto": "neutral", "color": "#9FB4C4", "mochila": False}).svg}</g>')
    return Dibujo("".join(partes), (-w / 2 - 12, -h / 2 - 12, w + 24, h + 24))


def cable(e: dict) -> Dibujo:
    """Enchufe desconectado: un cable con su clavija separada del tomacorriente."""
    partes = [tubo([(-300, 0), (-160, -30), (-60, 10)], "cable", GRIS, 14),
              figura([(-60, -30), (20, -30), (20, 40), (-60, 40)], "cable/clavija", GRIS),
              raya([(20, -10), (55, -10)], "cable/p1", NEGRO, 8), raya([(20, 20), (55, 20)], "cable/p2", NEGRO, 8),
              figura([(160, -60), (260, -60), (260, 70), (160, 70)], "cable/toma", BLANCO),
              f'<rect x="185" y="-15" width="10" height="20" fill="{NEGRO}"/><rect x="225" y="-15" width="10" height="20" fill="{NEGRO}"/>']
    return Dibujo("".join(partes), (-320, -80, 600, 170))


PIEZAS.update({"oreja": oreja, "gato": gato, "ondas": ondas, "piel": piel, "nieve": nieve, "ojo": ojo, "boca": boca,
               "columna": columna, "embrion": embrion, "nariz": nariz, "bebe": bebe, "intestino": intestino,
               "bacterias": bacterias, "torso": torso, "plano": plano, "cable": cable})
