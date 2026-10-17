"""Escenarios de fondo (cuarto, baño, sala, cocina, clase, consultorio, piscina, noche…) para las escenas de la
historia. Van suaves: colores pálidos y la línea en GRIS, para que el personaje y las piezas (línea negra) resalten.
Los adornos quedan en las orillas; el centro queda libre. El piso empieza en y≈960 (los pies del personaje van en 990).
"""
from __future__ import annotations

from .trazo import arco, camino, elipse

W, H = 1920, 1080
LINEA_FONDO = "#A8A8A8"
PISO_Y = 940


def _f(puntos, semilla, relleno, cerrado=True, ancho=5):
    return (f'<path d="{camino(puntos, semilla, cerrado, 1.2)}" fill="{relleno}" stroke="{LINEA_FONDO}" '
            f'stroke-width="{ancho}" stroke-linejoin="round" stroke-linecap="round"/>')


def _r(puntos, semilla, ancho=5, color=LINEA_FONDO):
    return (f'<path d="{camino(puntos, semilla, False, 1.2)}" fill="none" stroke="{color}" stroke-width="{ancho}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')


def _rect(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]


def _cuarto(pared="#F4EFE7", piso="#E6D8C3", s="cuarto") -> list[str]:
    return [f'<rect width="{W}" height="{H}" fill="{pared}"/>',
            _f([(-20, PISO_Y), (W + 20, PISO_Y), (W + 20, H + 20), (-20, H + 20)], f"{s}/piso", piso),
            _r([(-20, PISO_Y - 18), (W + 20, PISO_Y - 18)], f"{s}/zocalo", 4)]


def _ventana(x, y, w, h, cielo="#DDEEF8", s="v"):
    return [_f(_rect(x, y, w, h), f"{s}/marco", cielo),
            _r([(x + w / 2, y), (x + w / 2, y + h)], f"{s}/cruz1", 4), _r([(x, y + h / 2), (x + w, y + h / 2)], f"{s}/cruz2", 4)]


def cuarto() -> str:
    p = _cuarto()
    p += _ventana(110, 140, 300, 260, s="cuarto/v")
    p += [_f(_rect(1560, 170, 220, 160), "cuarto/cuadro", "#EFE3CF"),
          _r([(1590, 300), (1650, 230), (1700, 280), (1750, 210)], "cuarto/cuadro_m", 4),
          _f(_rect(1640, 700, 220, 240), "cuarto/mesita", "#E8DCC8"),
          _f([(1690, 700), (1720, 610), (1780, 610), (1810, 700)], "cuarto/lampara", "#F6E7B0")]
    return "".join(p)


def cuarto_noche() -> str:
    p = _cuarto("#DCE1EE", "#C9C3D6", "noche")
    p += _ventana(110, 140, 300, 260, "#5D6B8E", "noche/v")
    p += [f'<circle cx="300" cy="215" r="34" fill="#F4EFC9"/>',
          _f(_rect(1640, 700, 220, 240), "noche/mesita", "#CFCADB"),
          _f([(1690, 700), (1720, 610), (1780, 610), (1810, 700)], "noche/lampara", "#E9E2B8")]
    return "".join(p)


def bano() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#EAF3F6"/>']
    for i in range(0, W, 120):
        p.append(_r([(i, 0), (i, PISO_Y)], f"bano/v{i}", 2))
    for j in range(0, PISO_Y, 120):
        p.append(_r([(0, j), (W, j)], f"bano/h{j}", 2))
    p += [_f([(-20, PISO_Y), (W + 20, PISO_Y), (W + 20, H + 20), (-20, H + 20)], "bano/piso", "#D7E3E8"),
          _f(_rect(1520, 150, 300, 380), "bano/espejo", "#F7FBFD"),
          _r([(1560, 200), (1620, 140)], "bano/brillo", 4),
          _f([(1500, 640), (1840, 640), (1800, 740), (1540, 740)], "bano/lavamanos", "#FFFFFF"),
          _f(_rect(1640, 740, 60, 200), "bano/pie", "#FFFFFF")]
    return "".join(p)


def sala() -> str:
    p = _cuarto("#F2EEE8", "#DDD3C4", "sala")
    p += _ventana(1480, 140, 330, 280, s="sala/v")
    p += [_f([(60, 940), (60, 700), (110, 640), (420, 640), (470, 700), (470, 940)], "sala/sofa", "#D9C9B6"),
          _f(_rect(90, 760, 350, 90), "sala/cojin", "#E6D9C8"),
          _f([(1700, 940), (1680, 820), (1780, 820), (1760, 940)], "sala/maceta", "#E2C9A8"),
          _f(elipse(1730, 760, 70, 80, n=24), "sala/planta", "#CFE3BF")]
    return "".join(p)


def cocina() -> str:
    p = _cuarto("#F5F1E6", "#DED5C2", "cocina")
    p += [_f(_rect(0, 120, 520, 220), "cocina/alacena", "#E5DCCB"), _r([(260, 120), (260, 340)], "cocina/al1", 4),
          _f(_rect(0, 640, 560, 300), "cocina/meson", "#E5DCCB"), _f(_rect(0, 620, 600, 40), "cocina/tope", "#EDE7DC"),
          _f(_rect(1500, 300, 300, 640), "cocina/nevera", "#EEF1F3"), _r([(1500, 560), (1800, 560)], "cocina/nev1", 4),
          _r([(1530, 400), (1530, 480)], "cocina/manija", 6)]
    return "".join(p)


def clase() -> str:
    p = _cuarto("#EFF2E8", "#D9D2C2", "clase")
    p += [_f(_rect(80, 120, 520, 320), "clase/pizarra", "#7E9C82"), _f(_rect(70, 440, 540, 20), "clase/borde", "#C9BCA6"),
          _r([(130, 200), (330, 200)], "clase/tiza1", 4, "#F3F3F3"), _r([(130, 260), (420, 260)], "clase/tiza2", 4, "#F3F3F3"),
          _f(_rect(1500, 760, 340, 40), "clase/pupitre", "#D8C6A6"), _r([(1530, 800), (1530, 940)], "clase/p1", 6),
          _r([(1810, 800), (1810, 940)], "clase/p2", 6)]
    return "".join(p)


def consultorio() -> str:
    p = _cuarto("#EEF4F7", "#D6E0E4", "consultorio")
    p += [_r([(1900, 60), (1600, 120), (1480, 260)], "cons/brazo", 10),
          _f(elipse(1450, 300, 90, 50, rot=-20, n=24), "cons/lampara", "#FFF6CF"),
          _f(_rect(60, 520, 300, 420), "cons/mueble", "#E3ECF0"), _r([(60, 730), (360, 730)], "cons/c1", 4),
          _f(_rect(90, 160, 240, 300), "cons/cartel", "#FFFFFF"), _r([(130, 230), (290, 230)], "cons/l1", 4),
          _r([(130, 300), (260, 300)], "cons/l2", 4)]
    return "".join(p)


def piscina() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#EAF5FB"/>',
         f'<circle cx="1700" cy="170" r="70" fill="#FCEBA0"/>',
         _f([(-20, 700), (W + 20, 700), (W + 20, H + 20), (-20, H + 20)], "pisc/borde", "#EFE6D6"),
         _f([(-20, 790), (W + 20, 790), (W + 20, H + 20), (-20, H + 20)], "pisc/agua", "#BFE1EE")]
    for i in range(6):
        x = 80 + i * 320
        p.append(_r(arco(x, 860 + (i % 2) * 60, 60, 14, 200, 340, 10), f"pisc/ola{i}", 4, "#8FBFD4"))
    p += [_r([(1760, 640), (1760, 900)], "pisc/esc1", 8), _r([(1830, 640), (1830, 900)], "pisc/esc2", 8)]
    return "".join(p)


ESCENARIOS = {"cuarto": cuarto, "cuarto_noche": cuarto_noche, "bano": bano, "sala": sala, "cocina": cocina,
              "clase": clase, "consultorio": consultorio, "piscina": piscina}


# ------------------------------------------------------------------ el espacio (cielos pálidos, suelos de cada lugar)

def _estrellitas(semilla: str, color="#B9BCCB", n=14, alto=560) -> list[str]:
    import random

    r = random.Random(semilla)
    salida = []
    for i in range(n):
        x, y, k = r.uniform(40, W - 40), r.uniform(30, alto), r.uniform(5, 11)
        salida.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{k:.1f}" fill="{color}"/>')
    return salida


def _suelo(cielo: str, suelo: str, s: str, crateres: str | None = None, rocas: str | None = None) -> list[str]:
    p = [f'<rect width="{W}" height="{H}" fill="{cielo}"/>',
         _f([(-20, PISO_Y + 10), (500, PISO_Y - 20), (1100, PISO_Y + 15), (1500, PISO_Y - 10), (W + 20, PISO_Y + 5),
             (W + 20, H + 20), (-20, H + 20)], f"{s}/suelo", suelo)]
    if crateres:
        for i, (x, y, rx) in enumerate(((240, 1010, 120), (900, 1040, 80), (1560, 1000, 140))):
            p.append(_f(elipse(x, y, rx, rx * 0.22, n=24), f"{s}/cr{i}", crateres))
    if rocas:
        for i, (x, y, r) in enumerate(((120, PISO_Y + 10, 50), (1780, PISO_Y + 5, 64), (1400, PISO_Y + 40, 30))):
            p.append(_f(arco(x, y, r, r * 0.7, 180, 360, 14), f"{s}/roca{i}", rocas))
    return p


def luna() -> str:
    p = _suelo("#D9DBE6", "#CFCFCF", "luna", crateres="#BDBDBD")
    return "".join(p + _estrellitas("luna"))


def mercurio() -> str:
    p = _suelo("#E4DEDB", "#C7BCB0", "merc", crateres="#B5A99C")
    p.insert(1, f'<circle cx="1660" cy="190" r="150" fill="#FBE6A6"/>')
    return "".join(p + _estrellitas("merc", n=8))


def venus() -> str:
    p = _suelo("#F3E0B6", "#DDBE90", "venus", rocas="#CFAE7E")
    for i, y in enumerate((120, 230, 330)):
        p.append(_r([(x, y + 14 * ((x // 160) % 2)) for x in range(-40, W + 80, 160)], f"venus/nube{i}", 6, "#D9BB80"))
    return "".join(p)


def marte() -> str:
    p = _suelo("#F2DCC8", "#E5AE90", "marte", rocas="#D49174")
    p.append(_f(arco(1500, PISO_Y + 5, 420, 160, 180, 360, 30), "marte/colina", "#E9B99E"))
    return "".join(p)


def nubes_gas() -> str:
    """Dentro de un gigante de gas (Júpiter, Saturno): franjas de nubes, sin suelo."""
    p = [f'<rect width="{W}" height="{H}" fill="#F3E3C8"/>']
    for i, (y, color) in enumerate(((140, "#EBD3AE"), (380, "#E6C9A0"), (640, "#EAD2B0"), (880, "#DFBE94"))):
        pts = [(x, y + 26 * ((x // 240) % 2)) for x in range(-60, W + 300, 240)]
        p.append(_f(pts + [(W + 60, y + 150), (-60, y + 150)], f"gas/f{i}", color))
    return "".join(p)


def nubes_hielo() -> str:
    """Dentro de Urano o Neptuno: franjas frías, azul pálido."""
    p = [f'<rect width="{W}" height="{H}" fill="#E1F0F6"/>']
    for i, (y, color) in enumerate(((160, "#D2E9F1"), (420, "#C7E2EE"), (700, "#D5EBF3"))):
        pts = [(x, y + 24 * ((x // 260) % 2)) for x in range(-60, W + 300, 260)]
        p.append(_f(pts + [(W + 60, y + 170), (-60, y + 170)], f"hielo/f{i}", color))
    return "".join(p)


def titan() -> str:
    p = _suelo("#F5DCB2", "#D6BD95", "titan", rocas="#C4A982")
    p.append(_f(elipse(330, 1000, 300, 40, n=30), "titan/lago", "#B6A6C4"))
    return "".join(p)


def pluton() -> str:
    p = _suelo("#DCDDE8", "#F3F2F4", "pluton", crateres="#E1DFE6")
    p.insert(1, f'<circle cx="1640" cy="180" r="12" fill="#FFF3C4"/>')
    return "".join(p + _estrellitas("pluton", n=16))


def espacio() -> str:
    return "".join([f'<rect width="{W}" height="{H}" fill="#E8E9F2"/>'] + _estrellitas("espacio", n=30, alto=H - 40))


def sol_cerca() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#FDF0D2"/>']
    for i, r in enumerate((900, 700, 520)):
        p.append(f'<circle cx="{W + 120}" cy="{H // 2}" r="{r}" fill="{("#FCE4B0", "#FBD892", "#FAC873")[i]}"/>')
    return "".join(p)


ESCENARIOS.update({"luna": luna, "mercurio": mercurio, "venus": venus, "marte": marte, "nubes_gas": nubes_gas,
                   "nubes_hielo": nubes_hielo, "titan": titan, "pluton": pluton, "espacio": espacio,
                   "sol_cerca": sol_cerca})


# ------------------------------------------------------------------ afuera (17-10, El Calvo Explica: el lugar de cada tema)

def _nubes(semilla: str, color="#FFFFFF", filas=((300, 170, 1.0), (1500, 120, 0.8), (1080, 240, 0.55))) -> list[str]:
    p = []
    for i, (cx, cy, k) in enumerate(filas):
        for j, (dx, dy, r) in enumerate(((-70, 10, 50), (-10, -20, 66), (60, 0, 54), (110, 18, 38))):
            p.append(_f(elipse(cx + dx * k, cy + dy * k, r * k, r * k * 0.86, n=26), f"{semilla}/n{i}{j}", color, ancho=4))
    return p


def _pino(x, y, alto, s, color="#B7D3A8", tronco="#D6C2A5"):
    return [_f(_rect(x - 12, y - 40, 24, 40), f"{s}/tr", tronco, ancho=4),
            _f([(x - alto * 0.38, y - 30), (x, y - alto), (x + alto * 0.38, y - 30)], f"{s}/copa", color, ancho=4)]


def _arbol(x, y, alto, s, color="#BFDDAE", tronco="#D6C2A5"):
    return [_f(_rect(x - 16, y - alto * 0.5, 32, alto * 0.5), f"{s}/tr", tronco, ancho=4),
            _f(elipse(x, y - alto * 0.68, alto * 0.36, alto * 0.3, n=28), f"{s}/copa", color, ancho=4)]


def _horizonte(cielo: str, suelo: str, s: str, y: int = PISO_Y, ondas: bool = True) -> list[str]:
    pts = [(-20, y + (14 if ondas else 0)), (600, y - (18 if ondas else 0)), (1200, y + (10 if ondas else 0)),
           (W + 20, y - (8 if ondas else 0)), (W + 20, H + 20), (-20, H + 20)]
    return [f'<rect width="{W}" height="{H}" fill="{cielo}"/>', _f(pts, f"{s}/suelo", suelo)]


def cielo() -> str:
    return "".join(_horizonte("#E3F1FA", "#D5E8C6", "cielo") + _nubes("cielo"))


def parque() -> str:
    p = _horizonte("#E3F1FA", "#D2E7C2", "parque") + _nubes("parque", filas=((420, 150, 0.8), (1450, 110, 0.7)))
    p += _arbol(160, PISO_Y + 10, 430, "parque/a1") + _arbol(1760, PISO_Y + 5, 470, "parque/a2")
    p += [_f(_rect(1380, 800, 260, 26), "parque/banca", "#E2CFAF", ancho=4),
          _r([(1400, 826), (1400, 900)], "parque/p1", 4), _r([(1620, 826), (1620, 900)], "parque/p2", 4)]
    return "".join(p)


def bosque() -> str:
    p = _horizonte("#E6F0E4", "#CFE0C0", "bosque")
    for i, (x, h) in enumerate(((90, 520), (280, 420), (1620, 470), (1810, 560), (1440, 360))):
        p += _pino(x, PISO_Y + 12, h, f"bosque/p{i}", ("#B2CFA2", "#A9C899", "#B9D6AA")[i % 3])
    return "".join(p)


def selva() -> str:
    p = _horizonte("#E2F0DE", "#C4DDB0", "selva")
    for i, (x, y, r) in enumerate(((60, 160, 230), (1860, 120, 260), (-20, 640, 200), (1940, 620, 220))):
        p.append(_f(elipse(x, y, r, r * 0.7, n=30), f"selva/h{i}", ("#B4D4A0", "#A6CB92")[i % 2], ancho=4))
    for i, x in enumerate((240, 1680)):
        p.append(_r([(x, -10), (x + 30, 300), (x - 10, 620)], f"selva/liana{i}", 6, "#9DBD8A"))
    return "".join(p)


def playa() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#E1F2FB"/>',
         _f([(-20, 700), (W + 20, 690), (W + 20, 860), (-20, 870)], "playa/mar", "#BFE0EF"),
         _f([(-20, 860), (700, 830), (1300, 860), (W + 20, 840), (W + 20, H + 20), (-20, H + 20)], "playa/arena", "#F4E6C4")]
    for i, y in enumerate((740, 790)):
        p.append(_r([(x, y + 10 * ((x // 120) % 2)) for x in range(-40, W + 120, 120)], f"playa/ola{i}", 4, "#A9D3E6"))
    p += [f'<circle cx="1650" cy="200" r="90" fill="#FCEBB0"/>',
          _r([(1780, 860), (1800, 600), (1830, 440)], "playa/palma", 10, "#D6C2A5")]
    for i, (dx, dy) in enumerate(((-150, 40), (150, 30), (-90, 90), (110, 100))):
        p.append(_r([(1830, 440), (1830 + dx * 0.5, 440 + dy * 0.2 - 30), (1830 + dx, 440 + dy)], f"playa/hoja{i}", 8, "#B4D4A0"))
    return "".join(p)


def oceano() -> str:
    """Bajo el agua: azul pálido, rayos de luz y burbujas en las orillas."""
    p = [f'<rect width="{W}" height="{H}" fill="#D6ECF5"/>']
    for i, x in enumerate((300, 800, 1400)):
        p.append(f'<path d="M{x},0 L{x + 160},0 L{x + 360},{H} L{x + 120},{H} Z" fill="#E4F3F9"/>')
    p.append(_f([(-20, 980), (700, 960), (1300, 990), (W + 20, 970), (W + 20, H + 20), (-20, H + 20)], "oceano/fondo", "#EADFC2"))
    for i, (x, y, r) in enumerate(((140, 400, 18), (180, 300, 11), (1760, 520, 16), (1720, 420, 10), (1790, 330, 7))):
        p.append(_f(elipse(x, y, r, r, n=14), f"oceano/b{i}", "#E8F6FB", ancho=3))
    for i, x in enumerate((120, 1800)):
        p.append(_r([(x, 990), (x - 20, 860), (x + 15, 760), (x - 5, 660)], f"oceano/alga{i}", 9, "#A8CFA0"))
    return "".join(p)


def volcan() -> str:
    p = _horizonte("#F6E6DA", "#D9C6B6", "volcan")
    p.append(_f([(1080, PISO_Y + 10), (1380, 330), (1520, 330), (1880, PISO_Y + 10)], "volcan/cono", "#CDB5A2"))
    p.append(_f([(1380, 330), (1420, 380), (1460, 350), (1520, 330)], "volcan/lava", "#F5B38F", ancho=4))
    for i, (x, y, r) in enumerate(((1450, 240, 60), (1520, 160, 80), (1430, 90, 70))):
        p.append(_f(elipse(x, y, r, r * 0.75, n=22), f"volcan/humo{i}", "#E4DCD6", ancho=4))
    return "".join(p)


def desierto() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#FBF0DC"/>', f'<circle cx="1620" cy="210" r="110" fill="#FCE0A0"/>',
         _f([(-20, 860), (500, 760), (1000, 880), (1500, 800), (W + 20, 880), (W + 20, H + 20), (-20, H + 20)],
            "desierto/duna", "#F1DCB0")]
    p += [_r([(220, 880), (220, 640)], "desierto/cactus", 30, "#BCD3A4"), _r([(220, 760), (170, 760), (170, 690)],
                                                                           "desierto/brazo", 22, "#BCD3A4")]
    return "".join(p)


def montana_nieve() -> str:
    p = _horizonte("#E7F0F7", "#F5F8FA", "nieve")
    for i, (a, b, c, alto) in enumerate(((-100, 300, 700, 330), (500, 900, 1300, 260), (1200, 1600, 2050, 300))):
        p.append(_f([(a, PISO_Y + 5), (b, alto), (c, PISO_Y + 5)], f"nieve/m{i}", "#D8E3EC"))
        p.append(_f([(b - 70, alto + 90), (b, alto), (b + 70, alto + 90), (b + 20, alto + 70)], f"nieve/pico{i}", "#FFFFFF", ancho=4))
    p += _pino(120, PISO_Y + 20, 300, "nieve/p1", "#C6D9CC") + _pino(1790, PISO_Y + 20, 340, "nieve/p2", "#C6D9CC")
    return "".join(p)


def tormenta() -> str:
    p = _horizonte("#D9DEE6", "#C9D3C2", "tormenta")
    p += _nubes("tormenta", "#C8CED8", ((300, 150, 1.4), (1000, 110, 1.2), (1650, 160, 1.5)))
    return "".join(p)


def ciudad() -> str:
    p = [f'<rect width="{W}" height="{H}" fill="#E6EEF5"/>']
    for i, (x, w, h) in enumerate(((0, 220, 520), (240, 180, 380), (1460, 200, 440), (1680, 260, 600))):
        p.append(_f(_rect(x, PISO_Y - h, w, h), f"ciudad/e{i}", ("#DCE1E8", "#E3E0DA")[i % 2]))
        for f in range(int(h // 110)):
            for cx in range(x + 30, x + w - 50, 70):
                p.append(_f(_rect(cx, PISO_Y - h + 40 + f * 110, 36, 50), f"ciudad/v{i}{f}{cx}", "#F4F6F9", ancho=3))
    p.append(_f([(-20, PISO_Y), (W + 20, PISO_Y), (W + 20, H + 20), (-20, H + 20)], "ciudad/calle", "#D4D4D4"))
    return "".join(p)


ESCENARIOS.update({"cielo": cielo, "parque": parque, "bosque": bosque, "selva": selva, "playa": playa,
                   "oceano": oceano, "volcan": volcan, "desierto": desierto, "montana_nieve": montana_nieve,
                   "tormenta": tormenta, "ciudad": ciudad})
