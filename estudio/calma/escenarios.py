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
