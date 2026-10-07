"""Piezas del espacio para El Calvo Explica («Cómo sería morir en cada planeta»): planetas, el Sol, el agujero
negro y objetos para explicar (termómetro, medidor de presión, viento, diamante…). Mismo trazo de marcador.
Se registran en `piezas.PIEZAS`."""
from __future__ import annotations

import math

from . import personaje as P
from .piezas import PIEZAS, Dibujo
from .trazo import AMARILLO, BLANCO, GRIS, NEGRO, ROJO, arco, camino, elipse, figura, raya, tubo

AZUL = "#5B8FD9"
NARANJA = "#F2A541"
CAFE = "#A87B57"
R = 200                                   # radio de un planeta a tamaño 1

# tipo: (color base, [(y relativo, alto, color) de las franjas], extra)
_FRANJAS = {
    "jupiter": ("#E9D2B0", [(-0.62, 0.16, "#C99A6C"), (-0.28, 0.2, "#B9805A"), (0.12, 0.14, "#D8B48C"),
                            (0.42, 0.18, "#B9805A"), (0.72, 0.12, "#C99A6C")]),
    "saturno": ("#F1DFAE", [(-0.5, 0.18, "#E2C47E"), (-0.05, 0.14, "#D9B66D"), (0.38, 0.2, "#E8CF92")]),
    "venus": ("#F3D79A", [(-0.55, 0.22, "#EBC77F"), (0.0, 0.26, "#F7E2B4"), (0.5, 0.2, "#E6BC6E")]),
    "urano": ("#A8E0E3", [(-0.3, 0.2, "#9AD5D9"), (0.35, 0.18, "#B6E8EA")]),
    "neptuno": ("#4E79D6", [(-0.45, 0.14, "#5F8BE3"), (0.3, 0.18, "#4269C2")]),
    "titan": ("#F0B65E", [(-0.4, 0.3, "#F4C47A"), (0.35, 0.3, "#E3A04A")]),
}
_LISOS = {"luna": "#C9C9C9", "mercurio": "#B8ADA2", "marte": "#E07A4F", "tierra": "#6FA8E8", "pluton": "#D9C3A5"}
TIPOS_PLANETA = ("luna", "mercurio", "venus", "tierra", "marte", "jupiter", "saturno", "titan", "urano", "neptuno",
                 "pluton", "sol", "agujero_negro")


def _recorte(nombre: str, r: float = R) -> tuple[str, str]:
    """<defs> con un círculo de recorte (para franjas y manchas que no se salgan del planeta)."""
    cid = f"rec_{nombre}"
    return (f'<defs><clipPath id="{cid}"><circle cx="0" cy="0" r="{r - 2}"/></clipPath></defs>', cid)


def _crateres(s: str, color: str) -> list[str]:
    salida = []
    for i, (x, y, rr) in enumerate(((-70, -80, 34), (60, -20, 24), (-20, 70, 40), (95, 85, 20), (-110, 30, 18),
                                    (30, -130, 16))):
        salida.append(figura(elipse(x, y, rr, rr * 0.86, n=20), f"{s}/cr{i}", color, linea=4, amplitud=0.6))
    return salida


def _anillo(s: str, inclinacion: float, parte: str, color: str = "#D9C38E") -> str:
    """Media elipse de anillo (atrás o adelante del planeta)."""
    a, b = (180, 360) if parte == "atras" else (0, 180)
    pts = arco(0, 0, R * 1.75, R * 0.42, a, b, 40)
    c, s_ = math.cos(math.radians(inclinacion)), math.sin(math.radians(inclinacion))
    pts = [(x * c - y * s_, x * s_ + y * c) for x, y in pts]
    return (f'<path d="{camino(pts, s + "/an" + parte)}" fill="none" stroke="{NEGRO}" stroke-width="34" '
            f'stroke-linecap="round"/><path d="{camino(pts, s + "/an" + parte)}" fill="none" stroke="{color}" '
            f'stroke-width="22" stroke-linecap="round"/>')


def planeta(e: dict) -> Dibujo:
    """Un planeta, luna, el Sol o un agujero negro. estado {tipo}. Radio ~200 px a tamaño 1."""
    tipo = str(e.get("tipo", "tierra"))
    s = f"planeta/{tipo}"
    caja = (-R - 20, -R - 20, 2 * R + 40, 2 * R + 40)
    if tipo == "sol":
        rayos = "".join(raya([(math.cos(a) * (R + 30), math.sin(a) * (R + 30)),
                              (math.cos(a) * (R + 85), math.sin(a) * (R + 85))], f"{s}/r{i}", NARANJA, 14)
                        for i, a in enumerate(math.radians(k * 30) for k in range(12)))
        cuerpo = figura(elipse(0, 0, R, R, n=70), s, "#FFD24A")
        manchas = "".join(figura(elipse(x, y, rr, rr * 0.7, n=16), f"{s}/m{i}", "#FFB83A", linea=0, amplitud=0.6)
                          for i, (x, y, rr) in enumerate(((-60, -50, 40), (70, 40, 30), (-20, 90, 24))))
        return Dibujo(rayos + cuerpo + manchas, (-R - 110, -R - 110, 2 * R + 220, 2 * R + 220))
    if tipo == "agujero_negro":
        disco = (f'<ellipse cx="0" cy="0" rx="{R * 1.6}" ry="{R * 0.45}" fill="none" stroke="{NARANJA}" '
                 f'stroke-width="46" opacity="0.9"/>')
        brillo = f'<circle cx="0" cy="0" r="{R * 1.08}" fill="none" stroke="#FFD27A" stroke-width="26"/>'
        frente = (f'<path d="M {-R * 1.6} 0 A {R * 1.6} {R * 0.45} 0 0 0 {R * 1.6} 0" fill="none" stroke="#FFB347" '
                  f'stroke-width="46"/>')
        return Dibujo(disco + brillo + figura(elipse(0, 0, R, R, n=70), s, NEGRO) + frente,
                      (-R * 1.6 - 40, -R * 1.15 - 20, R * 3.2 + 80, R * 2.3 + 40))
    defs, cid = _recorte(tipo)
    partes = [defs]
    if tipo == "saturno":
        partes.append(_anillo(s, -12, "atras"))
    if tipo == "urano":
        partes.append(_anillo(s, 82, "atras", "#CDE9EC"))
    base = _FRANJAS[tipo][0] if tipo in _FRANJAS else _LISOS.get(tipo, "#CCCCCC")
    partes.append(figura(elipse(0, 0, R, R, n=70), s, base))
    dentro = []
    if tipo in _FRANJAS:
        for i, (y, h, color) in enumerate(_FRANJAS[tipo][1]):
            pts = ([(-R - 10, (y - h / 2) * R + 8 * math.sin(k)) for k in range(1)]
                   + [(-R + k * 2 * R / 10, (y - h / 2) * R + 8 * math.sin(k * 1.3 + i)) for k in range(11)]
                   + [(-R + k * 2 * R / 10, (y + h / 2) * R + 8 * math.sin(k * 1.1 + i)) for k in range(10, -1, -1)])
            dentro.append(f'<path d="{camino(pts, f"{s}/f{i}", True, 0.8)}" fill="{color}" stroke="none"/>')
    if tipo in ("luna", "mercurio"):
        dentro += _crateres(s, "#B2B2B2" if tipo == "luna" else "#A2968A")
    if tipo == "marte":
        dentro += [figura(elipse(-50, 30, 70, 40, rot=-20, n=24), f"{s}/m1", "#C2603A", linea=0, amplitud=0.8),
                   figura(elipse(80, -40, 40, 26, n=20), f"{s}/m2", "#C2603A", linea=0, amplitud=0.8),
                   figura(elipse(0, -R + 18, 70, 30, n=24), f"{s}/polo", BLANCO, linea=4)]
    if tipo == "tierra":
        dentro += [figura([(-120, -100), (-40, -140), (10, -80), (-30, -20), (-110, -10)], f"{s}/c1", "#8CC66A"),
                   figura([(40, 10), (130, -20), (150, 60), (90, 130), (40, 90)], f"{s}/c2", "#8CC66A")]
    if tipo == "jupiter":
        dentro.append(figura(elipse(70, 70, 56, 32, n=26), f"{s}/mancha", "#D2553A", linea=5))
    if tipo == "neptuno":
        dentro += [figura(elipse(-50, -40, 44, 24, n=22), f"{s}/mancha", "#2E4F9E", linea=4),
                   raya([(-10, 40), (60, 34), (110, 44)], f"{s}/nube", BLANCO, 10)]
    if tipo == "pluton":
        corazon = arco(20, 10, 44, 40, 150, 340, 12) + arco(100, 10, 44, 40, 200, 390, 12) + [(60, 120)]
        dentro += [figura(elipse(-90, -60, 60, 40, n=22), f"{s}/m", "#B98E6A", linea=0, amplitud=0.8),
                   figura(corazon, f"{s}/corazon", "#FAF7F0", linea=4)]
    if tipo == "titan":
        dentro.append(f'<circle cx="0" cy="0" r="{R}" fill="none" stroke="#F8D7A0" stroke-width="40" opacity="0.6"/>')
    partes.append(f'<g clip-path="url(#{cid})">{"".join(dentro)}</g>')
    partes.append(raya(elipse(0, 0, R, R, n=70) + [elipse(0, 0, R, R, n=70)[0]], s + "/borde", NEGRO, 7))
    if tipo == "saturno":
        partes.append(_anillo(s, -12, "frente"))
        caja = (-R * 1.8, -R - 20, R * 3.6, 2 * R + 40)
    if tipo == "urano":
        partes.append(_anillo(s, 82, "frente", "#CDE9EC"))
        caja = (-R - 60, -R * 1.8, 2 * R + 120, R * 3.6)
    return Dibujo("".join(partes), caja)


def estrellas(e: dict) -> Dibujo:
    """Estrellitas de cuatro puntas (el espacio). Ocupan ~900x500 a tamaño 1."""
    partes = []
    for i, (x, y, k) in enumerate(((-380, -180, 1.0), (-120, -220, 0.6), (200, -160, 0.9), (400, -60, 0.6),
                                   (-300, 120, 0.7), (60, 40, 0.5), (320, 180, 1.0), (-60, 210, 0.6))):
        r = 26 * k
        pts = [(x, y - r), (x + r * 0.25, y - r * 0.25), (x + r, y), (x + r * 0.25, y + r * 0.25), (x, y + r),
               (x - r * 0.25, y + r * 0.25), (x - r, y), (x - r * 0.25, y - r * 0.25)]
        partes.append(figura(pts, f"estrellas/{i}", "#FFE07A", linea=4, amplitud=0.4))
    return Dibujo("".join(partes), (-430, -260, 860, 500))


def cohete(e: dict) -> Dibujo:
    """Cohete blanco con ventanita y fuego abajo. Ancla en el centro."""
    partes = [figura([(-60, 120), (-120, 190), (-60, 170)], "cohete/aleta1", ROJO),
              figura([(60, 120), (120, 190), (60, 170)], "cohete/aleta2", ROJO)]
    if e.get("fuego", True):
        partes.append(figura([(-40, 175), (0, 290), (40, 175)], "cohete/fuego", NARANJA))
    partes += [figura(arco(0, 0, 62, 180, 180, 360, 30) + [(62, 175), (-62, 175)], "cohete/cuerpo", BLANCO),
               figura(elipse(0, -40, 30, 30, n=22), "cohete/ventana", "#A9D6F5")]
    return Dibujo("".join(partes), (-135, -200, 270, 500))


def termometro(e: dict) -> Dibujo:
    """Termómetro. estado {nivel: 0-1, color: rojo|azul}. Alto ~460 px."""
    nivel = max(0.0, min(1.0, float(e.get("nivel", 0.5))))
    color = AZUL if e.get("color") == "azul" else ROJO
    alto = 330
    partes = [figura([(-34, 150), (-34, -200)] + arco(0, -200, 34, 34, 180, 360, 12) + [(34, 150)],
                     "termo/tubo", BLANCO),
              f'<rect x="-14" y="{150 - alto * nivel:.1f}" width="28" height="{alto * nivel + 20:.1f}" fill="{color}"/>',
              figura(elipse(0, 190, 62, 62, n=30), "termo/bulbo", color)]
    for i in range(6):
        y = 120 - i * 55
        partes.append(raya([(34, y), (64, y)], f"termo/m{i}", NEGRO, 5))
    return Dibujo("".join(partes), (-75, -250, 160, 520))


def medidor(e: dict) -> Dibujo:
    """Medidor de presión (manómetro). estado {nivel: 0-1}: la aguja de casi nada a lleno; >0.8 en rojo."""
    nivel = max(0.0, min(1.0, float(e.get("nivel", 0.5))))
    partes = [figura(elipse(0, 0, 170, 170, n=60), "medidor/caja", BLANCO),
              raya(arco(0, 0, 130, 130, 150, 300, 24), "medidor/arco", NEGRO, 8),
              raya(arco(0, 0, 130, 130, 330, 390, 10), "medidor/rojo", ROJO, 16)]
    for i in range(9):
        a = math.radians(150 + i * 30)
        partes.append(raya([(math.cos(a) * 112, math.sin(a) * 112), (math.cos(a) * 140, math.sin(a) * 140)],
                           f"medidor/m{i}", NEGRO, 5))
    a = math.radians(150 + 240 * nivel)
    partes += [tubo([(0, 0), (math.cos(a) * 115, math.sin(a) * 115)], "medidor/aguja", ROJO if nivel > 0.8 else NEGRO, 10),
               f'<circle cx="0" cy="0" r="16" fill="{NEGRO}"/>']
    return Dibujo("".join(partes), (-185, -185, 370, 370))


def viento(e: dict) -> Dibujo:
    """Líneas de viento con remolinos, de izquierda a derecha. Entra con dibujar."""
    k = float(e.get("trazo", 1))
    partes = []
    for i, (y, largo) in enumerate(((-90, 520), (0, 640), (90, 460))):
        pts = [(-320 + j * largo / 12, y + 12 * math.sin(j * 0.9 + i)) for j in range(13)]
        pts += arco(pts[-1][0], y - 32, 34, 34, 90, -200, 14)
        partes.append(raya(pts, f"viento/{i}", GRIS if i == 1 else NEGRO, 9, parcial=k))
    return Dibujo("".join(partes), (-340, -170, 720, 310))


def burbujas(e: dict) -> Dibujo:
    """Burbujitas que hierven (saliva, agua, sangre de la piel). Pequeñas, ~200 px."""
    partes = [figura(elipse(x, y, r, r, n=16), f"burbuja/{i}", "#DDF1FB", linea=4, amplitud=0.4)
              for i, (x, y, r) in enumerate(((-60, 20, 22), (-10, -30, 16), (40, 10, 26), (10, 60, 14), (70, -50, 12),
                                             (-50, -70, 10)))]
    return Dibujo("".join(partes), (-95, -95, 200, 195))


def vapor(e: dict) -> Dibujo:
    """Tres líneas onduladas de vapor o calor hacia arriba."""
    partes = [raya([(x + 18 * math.sin(j * 1.2), 80 - j * 32) for j in range(7)], f"vapor/{i}", GRIS, 9,
                   parcial=float(e.get("trazo", 1))) for i, x in enumerate((-60, 0, 60))]
    return Dibujo("".join(partes), (-100, -150, 200, 250))


def fuego(e: dict) -> Dibujo:
    """Llama (calor extremo, horno, fogata)."""
    afuera = [(-90, 100), (-110, 10), (-60, -60), (-40, 0), (0, -150), (40, -20), (70, -70), (105, 20), (90, 100)]
    adentro = [(-45, 100), (-55, 40), (-20, 0), (0, -60), (25, 10), (50, 50), (45, 100)]
    return Dibujo(figura(afuera, "fuego/a", NARANJA) + figura(adentro, "fuego/b", "#FFD24A", amplitud=0.6),
                  (-125, -165, 250, 280))


def diamante(e: dict) -> Dibujo:
    """Diamante celeste con sus caras."""
    pts = [(-110, -40), (-60, -100), (60, -100), (110, -40), (0, 120)]
    partes = [figura(pts, "diamante", "#CFEFFF"), raya([(-110, -40), (110, -40)], "diamante/l1", NEGRO, 5),
              raya([(-60, -100), (-30, -40), (0, 120), (30, -40), (60, -100)], "diamante/l2", NEGRO, 5),
              raya([(-30, -40), (0, -100), (30, -40)], "diamante/l3", NEGRO, 5)]
    return Dibujo("".join(partes), (-130, -120, 260, 260))


def hexagono(e: dict) -> Dibujo:
    """El hexágono del polo de Saturno visto desde arriba, con remolino al centro. Entra con dibujar."""
    k = float(e.get("trazo", 1))
    pts = [(math.cos(math.radians(30 + 60 * i)) * 230, math.sin(math.radians(30 + 60 * i)) * 230) for i in range(7)]
    partes = [f'<circle cx="0" cy="0" r="300" fill="#F1DFAE" stroke="{NEGRO}" stroke-width="7"/>',
              f'<polygon points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts[:6])}" fill="#E2C47E" '
              f'opacity="{min(1.0, k * 1.5):.2f}"/>',
              tubo(pts, "hexagono", "#C99A6C", 22, k)]
    espiral = [(math.cos(t) * (8 + t * 9), math.sin(t) * (8 + t * 9)) for t in [i * 0.35 for i in range(36)]]
    partes.append(raya(espiral, "hexagono/remolino", NEGRO, 6, parcial=k))
    return Dibujo("".join(partes), (-310, -310, 620, 620))


def lago(e: dict) -> Dibujo:
    """Lago oscuro (de metano en Titán; de agua si «color»: azul). ~600x200."""
    color = AZUL if e.get("color") == "azul" else "#5A4A6E"
    return Dibujo(figura(elipse(0, 0, 300, 90, n=40), "lago", color)
                  + raya([(-120, -10), (-40, -14)], "lago/brillo", "#B7A9C9", 6)
                  + raya([(60, 24), (160, 18)], "lago/brillo2", "#B7A9C9", 6), (-320, -110, 640, 220))


def lluvia(e: dict) -> Dibujo:
    """Gotas que caen (de metano o agua). estado {color}."""
    color = AZUL if e.get("color") == "azul" else "#8E7DB0"
    partes = []
    for i in range(12):
        x, y = -330 + (i * 61) % 660, -150 + (i * 97) % 300
        partes.append(figura([(x, y - 30), (x + 14, y + 4)] + arco(x, y + 6, 14, 14, 0, 180, 8), f"lluvia/{i}",
                             color, linea=4, amplitud=0.4))
    return Dibujo("".join(partes), (-360, -200, 720, 400))


def alas(e: dict) -> Dibujo:
    """Un par de alas blancas (se ponen detrás del personaje, a la altura de los hombros)."""
    partes = []
    for lado in (-1, 1):
        borde = [(lado * 20, 0)] + [(lado * x, y) for x, y in arco(150, -60, 150, 120, 180, 300, 16)]
        plumas = []
        for j in range(4):                                  # borde de abajo en ondas (plumas)
            cx = 280 - j * 70
            plumas += [(lado * x, y) for x, y in arco(cx, -20 + j * 12, 36, 30, 0, 180, 8)]
        partes.append(figura(borde + plumas, f"alas/{lado}", BLANCO))
        for j in range(3):
            partes.append(raya([(lado * (110 + j * 60), -60), (lado * (150 + j * 60), -20)], f"alas/p{lado}{j}", GRIS, 5))
    return Dibujo("".join(partes), (-340, -200, 680, 260))


def tanque(e: dict) -> Dibujo:
    """Tanque de oxígeno con mascarilla."""
    partes = [figura(arco(0, -150, 70, 40, 180, 360, 16) + [(70, 160), (-70, 160)], "tanque", "#7FC6A4"),
              figura([(-20, -210), (20, -210), (20, -180), (-20, -180)], "tanque/valvula", GRIS),
              tubo([(20, -195), (110, -230), (160, -150)], "tanque/manguera", GRIS, 10),
              figura(elipse(170, -120, 46, 36, n=22), "tanque/mascara", BLANCO)]
    partes.append(f'<text x="0" y="20" font-family="Arial Black, Arial" font-weight="900" font-size="64" '
                  f'text-anchor="middle" fill="{NEGRO}">O₂</text>')
    return Dibujo("".join(partes), (-90, -250, 320, 430))


def huella(e: dict) -> Dibujo:
    """Huella de bota en el polvo."""
    partes = [figura(elipse(0, -40, 55, 85, n=30), "huella/punta", "#B2B2B2"),
              figura(elipse(0, 95, 45, 50, n=24), "huella/talon", "#B2B2B2")]
    for i in range(4):
        partes.append(raya([(-38, -90 + i * 34), (38, -90 + i * 34)], f"huella/l{i}", NEGRO, 5))
    return Dibujo("".join(partes), (-70, -140, 140, 300))


def tormenta(e: dict) -> Dibujo:
    """Nube de polvo enorme (tormenta de Marte). estado {color}: cafe (por defecto) o roja."""
    color = "#C98A62" if e.get("color") != "roja" else "#D2553A"
    partes = [figura(elipse(x, y, r, r * 0.8, n=26), f"tormenta/{i}", color)
              for i, (x, y, r) in enumerate(((-260, 30, 130), (-90, -40, 170), (110, -20, 160), (280, 40, 120),
                                             (0, 70, 190)))]
    return Dibujo("".join(partes), (-410, -190, 820, 360))


def huevo(e: dict) -> Dibujo:
    """Huevo podrido con rayitas de mal olor."""
    partes = [figura(elipse(0, 20, 90, 115, n=40), "huevo", "#F4EEDC"),
              raya([(-40, -20), (-10, 10), (-30, 40)], "huevo/grieta", NEGRO, 5)]
    for i, x in enumerate((-60, 0, 60)):
        partes.append(raya([(x + 14 * math.sin(j * 1.4), -120 - j * 22) for j in range(5)], f"huevo/olor{i}",
                           "#7DAA4C", 8))
    return Dibujo("".join(partes), (-110, -240, 220, 380))


def iman(e: dict) -> Dibujo:
    """Imán de herradura (magnetismo, escudo magnético)."""
    partes = [tubo(arco(0, 0, 110, 110, 0, 180, 20)[::-1], "iman", ROJO, 70),
              figura([(-145, -10), (-75, -10), (-75, -60), (-145, -60)], "iman/p1", GRIS),
              figura([(75, -10), (145, -10), (145, -60), (75, -60)], "iman/p2", GRIS)]
    return Dibujo("".join(partes), (-170, -80, 340, 240))


def sonda(e: dict) -> Dibujo:
    """Máquina que aterriza en otro planeta (sonda): caja con patas y antena."""
    partes = [tubo([(-80, 40), (-130, 120)], "sonda/p1", GRIS, 10), tubo([(80, 40), (130, 120)], "sonda/p2", GRIS, 10),
              figura([(-100, -40), (100, -40), (80, 50), (-80, 50)], "sonda/caja", "#D9D9D9"),
              raya([(0, -40), (0, -120)], "sonda/antena", NEGRO, 7),
              figura(arco(0, -120, 50, 26, 180, 360, 14), "sonda/plato", BLANCO)]
    return Dibujo("".join(partes), (-150, -160, 300, 300))


def banera(e: dict) -> Dibujo:
    """Bañera con agua (para «flotaría en una bañera»)."""
    partes = [figura([(-330, -40), (330, -40), (290, 120), (-290, 120)], "banera", BLANCO),
              figura([(-315, -20), (315, -20), (305, 10), (-305, 10)], "banera/agua", "#A9D6F5", amplitud=0.6),
              tubo([(-240, 120), (-250, 170)], "banera/pata1", GRIS, 14), tubo([(240, 120), (250, 170)], "banera/pata2", GRIS, 14)]
    return Dibujo("".join(partes), (-350, -60, 700, 250))


def estirado(e: dict) -> Dibujo:
    """El Calvo estirado como un fideo (agujero negro). estado {cuanto: 1-3} = cuánto se estira a lo alto."""
    k = max(1.0, min(3.0, float(e.get("cuanto", 2))))
    svg = P.personaje("asustado", "abiertos", "susto")
    ancho = 1 / math.sqrt(k)
    return Dibujo(f'<g transform="scale({ancho:.3f},{k:.3f})">{svg}</g>',
                  (-240 * ancho, -620 * k, 480 * ancho, 650 * k))


PIEZAS.update({"planeta": planeta, "estrellas": estrellas, "cohete": cohete, "termometro": termometro,
               "medidor": medidor, "viento": viento, "burbujas": burbujas, "vapor": vapor, "fuego": fuego,
               "diamante": diamante, "hexagono": hexagono, "lago": lago, "lluvia": lluvia, "alas": alas,
               "tanque": tanque, "huella": huella, "tormenta": tormenta, "huevo": huevo, "iman": iman,
               "sonda": sonda, "banera": banera, "estirado": estirado})
