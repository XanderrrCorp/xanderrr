"""El personaje de Hazlo con Calma, por piezas: cuerpo (6 poses), ojos (3) y cejas+boca (4).

Cabeza redonda color crema, calvo, cejas preocupadas, ojos grandes; cuerpo de palitos amarillo,
mochila roja y tenis negros. Todo en SVG con el mismo trazo de marcador (trazo.py).

Coordenadas propias: los pies tocan y=0, el personaje mide ~520 de alto y mira a la derecha (+x).
"""
from __future__ import annotations

import math

from .trazo import AMARILLO, BLANCO, CREMA, LINEA, NEGRO, ROJO, arco, elipse, figura, raya, tubo

RADIO_CABEZA = 92
GROSOR_BRAZO = 15
GROSOR_PIERNA = 17
GROSOR_TORSO = 44

# Cada pose: cadera, cuello, hombro y las extremidades (codo, mano) / (rodilla, pie).
# «atras» se dibuja detrás del torso, «frente» delante.
POSES: dict[str, dict] = {
    "de_pie": {
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-40, -240), (-50, -168)], "brazo_frente": [(40, -240), (52, -168)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
    },
    "senalando": {
        "cadera": (0, -190), "cuello": (-4, -322), "hombro": (-3, -300),
        "brazo_atras": [(-46, -248), (-14, -206)], "brazo_frente": [(70, -322), (148, -350)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "dedo": True,
    },
    "asustado": {
        "cadera": (0, -184), "cuello": (0, -318), "hombro": (0, -300),
        "brazo_atras": [(-74, -340), (-128, -400)], "brazo_frente": [(74, -340), (128, -400)],
        "pierna_atras": [(-38, -98), (-46, -8)], "pierna_frente": [(38, -98), (46, -8)],
        "temblor": True,
    },
    "corriendo": {
        "cadera": (0, -196), "cuello": (36, -322), "hombro": (32, -300),
        "brazo_atras": [(-20, -262), (-68, -228)], "brazo_frente": [(84, -262), (118, -306)],
        "pierna_atras": [(-44, -122), (-104, -64)], "pierna_frente": [(66, -146), (58, -52)],
        "suelo": False,
    },
    "agachado": {
        "cadera": (-34, -84), "cuello": (30, -196), "hombro": (24, -176),
        "brazo_atras": [(46, -118), (82, -96)], "brazo_frente": [(70, -128), (104, -100)],
        "pierna_atras": [(30, -112), (6, -8)], "pierna_frente": [(52, -118), (34, -8)],
    },
    "sentado": {
        "cadera": (-10, -36), "cuello": (-2, -168), "hombro": (-3, -146),
        "brazo_atras": [(-46, -90), (-62, -22)], "brazo_frente": [(50, -112), (88, -98)],
        "pierna_atras": [(58, -96), (118, -8)], "pierna_frente": [(74, -100), (140, -8)],
    },
    # ---- poses nuevas (El Calvo Explica) ----
    "tablero": {                       # frente a un tablero (a su derecha), señalándolo hacia arriba
        "cadera": (0, -190), "cuello": (-4, -322), "hombro": (-3, -300),
        "brazo_atras": [(-44, -244), (-52, -172)], "brazo_frente": [(62, -350), (118, -410)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "dedo": True,
    },
    "pensando": {                      # la mano en el mentón, el otro brazo cruzado
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-36, -236), (40, -238)], "brazo_frente": [(66, -262), (40, -334)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "mano_encima": True,           # la mano va por delante de la cabeza
    },
    "confundido": {                    # se rasca la cabeza, con signos de pregunta
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-44, -240), (-58, -170)], "brazo_frente": [(108, -336), (84, -438)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "signos": True, "mano_encima": True,
    },
    "hombros": {                       # encogido de hombros, palmas arriba
        "cadera": (0, -190), "cuello": (0, -312), "hombro": (0, -306),
        "brazo_atras": [(-72, -252), (-112, -300)], "brazo_frente": [(72, -252), (112, -300)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
    },
    "sorprendido": {                   # se echa un poco atrás, manos abiertas a los lados
        "cadera": (0, -190), "cuello": (-14, -320), "hombro": (-12, -298),
        "brazo_atras": [(-70, -270), (-110, -318)], "brazo_frente": [(50, -268), (96, -312)],
        "pierna_atras": [(-22, -96), (-34, -8)], "pierna_frente": [(20, -96), (30, -8)],
    },
    "aliviado": {                      # la mano en el pecho
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-40, -240), (-50, -168)], "brazo_frente": [(58, -240), (12, -268)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
    },
    "idea": {                          # dedo arriba junto a la cabeza y un bombillo
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-40, -240), (-50, -168)], "brazo_frente": [(84, -318), (110, -400)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "dedo": True, "bombillo": True,
    },
    "rechazo": {                       # cara girada, mano abierta levantada hacia lo que le disgusta (a la derecha)
        "cadera": (0, -190), "cuello": (-10, -322), "hombro": (-8, -300),
        "brazo_atras": [(-46, -244), (-56, -172)], "brazo_frente": [(72, -296), (126, -340)],
        "pierna_atras": [(-20, -96), (-30, -8)], "pierna_frente": [(14, -96), (20, -8)],
        "mano_abierta": True, "cara_girada": -1,
    },
    "senalando_contento": {            # sonríe y señala hacia un lado con el índice
        "cadera": (0, -190), "cuello": (0, -322), "hombro": (0, -300),
        "brazo_atras": [(-40, -240), (-50, -168)], "brazo_frente": [(76, -296), (156, -300)],
        "pierna_atras": [(-16, -96), (-24, -8)], "pierna_frente": [(16, -96), (24, -8)],
        "dedo": True,
    },
}
POSES["acostado"] = {**POSES["de_pie"], "acostado": True}    # en la cama: solo la cabeza en la almohada

OJOS = ("abiertos", "cerrados", "lado")
CARAS = ("neutral", "susto", "alivio", "concentrado")
CARAS_NUEVAS = ("sorpresa", "duda", "pensativo", "amable", "seguro", "aliviado", "contento", "disgusto")
OJOS_NUEVOS = ("otro_lado",)           # mira hacia la izquierda (cara girada)


def _menos(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _unit(v):
    d = math.hypot(*v) or 1.0
    return (v[0] / d, v[1] / d)


def centro_cabeza(pose: dict) -> tuple[float, float]:
    u = _unit(_menos(pose["cuello"], pose["cadera"]))
    return (pose["cuello"][0] + u[0] * (RADIO_CABEZA - 6), pose["cuello"][1] + u[1] * (RADIO_CABEZA - 6))


def _tenis(rodilla, pie, semilla: str, en_suelo: bool) -> str:
    """Tenis negro con suela blanca; la punta mira hacia delante (+x)."""
    s = _unit(_menos(pie, rodilla))
    f = (-s[1], s[0]) if -s[1] >= 0 else (s[1], -s[0])
    if en_suelo:
        f, s = (1.0, 0.0), (0.0, 1.0)
    px, py = pie
    talon = (px - f[0] * 16 + s[0] * 10, py - f[1] * 16 + s[1] * 10)
    punta = (px + f[0] * 44 + s[0] * 10, py + f[1] * 44 + s[1] * 10)
    nariz = (px + f[0] * 46 - s[0] * 6, py + f[1] * 46 - s[1] * 6)
    tobillo = (px - f[0] * 10 - s[0] * 12, py - f[1] * 10 - s[1] * 12)
    empeine = (px + f[0] * 18 - s[0] * 18, py + f[1] * 18 - s[1] * 18)
    zapato = figura([talon, punta, nariz, empeine, tobillo], semilla, NEGRO)
    suela = raya([(talon[0] + f[0] * 6 - s[0] * 5, talon[1] + f[1] * 6 - s[1] * 5),
                  (punta[0] - f[0] * 6 - s[0] * 5, punta[1] - f[1] * 6 - s[1] * 5)],
                 semilla + "s", BLANCO, 4)
    return zapato + suela


def _pierna(cadera, lado, semilla, pose, color=AMARILLO) -> str:
    rodilla, pie = lado
    return tubo([cadera, rodilla, pie], semilla, color, GROSOR_PIERNA) + \
        _tenis(rodilla, pie, semilla + "t", pose.get("suelo", True) and pie[1] > -20)


def _brazo(hombro, lado, semilla, dedo=False, color=AMARILLO) -> str:
    codo, mano = lado
    salida = tubo([hombro, codo, mano], semilla, color, GROSOR_BRAZO)
    if dedo:
        u = _unit(_menos(mano, codo))
        punta = (mano[0] + u[0] * 26, mano[1] + u[1] * 26)
        salida += tubo([mano, punta], semilla + "d", color, 7)
    return salida


def _mochila(pose, semilla) -> str:
    """Mochila roja detrás de la espalda (lado -x), alineada con el torso."""
    cad, cue = pose["cadera"], pose["cuello"]
    u = _unit(_menos(cue, cad))                    # hacia arriba por el torso
    n = (u[1], -u[0])                              # hacia la espalda
    if n[0] > 0:
        n = (-n[0], -n[1])
    m = ((cad[0] + cue[0]) / 2 + u[0] * 14 + n[0] * 30, (cad[1] + cue[1]) / 2 + u[1] * 14 + n[1] * 30)
    alto, ancho = 54, 34
    esquinas = [(-ancho, -alto), (ancho, -alto), (ancho + 3, alto), (-ancho - 3, alto)]
    pts = []
    for i, (x, y) in enumerate(esquinas):          # rectángulo redondeado
        x2, y2 = esquinas[(i + 1) % 4]
        for t in (0.18, 0.82):
            pts.append((x + (x2 - x) * t, y + (y2 - y) * t))
    mundo = [(m[0] + n[0] * -x + u[0] * -y, m[1] + n[1] * -x + u[1] * -y) for x, y in pts]
    bolsillo = [(m[0] + n[0] * -x + u[0] * -y, m[1] + n[1] * -x + u[1] * -y)
                for x, y in [(-20, 16), (20, 16), (22, 40), (-22, 40)]]
    return figura(mundo, semilla, ROJO) + figura(bolsillo, semilla + "b", ROJO)


def _correa(pose, semilla) -> str:
    """La correa roja que cruza el hombro (se ve por delante)."""
    cad, cue = pose["cadera"], pose["cuello"]
    a = (cue[0] * 0.92 + cad[0] * 0.08, cue[1] * 0.92 + cad[1] * 0.08)
    b = (cue[0] * 0.45 + cad[0] * 0.55, cue[1] * 0.45 + cad[1] * 0.55)
    u = _unit(_menos(cue, cad))
    n = (u[1], -u[0]) if u[1] < 0 else (-u[1], u[0])
    a = (a[0] - n[0] * 6, a[1] - n[1] * 6)
    b = (b[0] - n[0] * 20, b[1] - n[1] * 20)
    return tubo([a, b], semilla, ROJO, 8)


def cuerpo(nombre: str, color: str = AMARILLO, mochila: bool = True, brazo_frente: bool = True) -> str:
    """El cuerpo SIN cabeza en una pose (la cabeza va aparte para cambiar cara y ojos).
    Con otro color y sin mochila sirve para «otra persona» (un vecino, la gente)."""
    p = POSES[nombre]
    cad, cue, hom = p["cadera"], p["cuello"], p["hombro"]
    s = f"cuerpo/{nombre}"
    partes = [
        _brazo(hom, p["brazo_atras"], s + "/ba", color=color),
        _mochila(p, s + "/mo") if mochila else "",
        _pierna(cad, p["pierna_atras"], s + "/pa", p, color),
        _pierna(cad, p["pierna_frente"], s + "/pf", p, color),
        tubo([cad, cue], s + "/to", color, GROSOR_TORSO),
        _correa(p, s + "/co") if mochila else "",
        _brazo(hom, p["brazo_frente"], s + "/bf", p.get("dedo", False), color) if brazo_frente else "",
    ]
    return "".join(partes)


# ------------------------------------------------------------------ cabeza y cara
# La cara se dibuja con el centro de la cabeza en (0, 0); mira un poco a la derecha.

def cabeza() -> str:
    return figura(elipse(0, 0, RADIO_CABEZA, RADIO_CABEZA * 0.97, n=60), "cabeza", CREMA)


OJO_X = (-20, 30)          # el ojo derecho (pantalla) un poco más afuera: mira hacia +x
OJO_Y = -4


def ojos(estado: str) -> str:
    salida = []
    for i, x in enumerate(OJO_X):
        s = f"ojo/{estado}/{i}"
        if estado == "cerrados":
            salida.append(raya(arco(x, OJO_Y + 2, 18, 10, 20, 160), s))
            continue
        salida.append(figura(elipse(x, OJO_Y, 19, 25, n=30), s, BLANCO, amplitud=0.8))
        dx = 9 if estado == "lado" else -7 if estado == "otro_lado" else 3
        salida.append(f'<circle cx="{x + dx}" cy="{OJO_Y + 4}" r="10" fill="{NEGRO}"/>'
                      f'<circle cx="{x + dx + 3}" cy="{OJO_Y}" r="3.2" fill="{BLANCO}"/>')
    return "".join(salida)


def cara(gesto: str) -> str:
    """Cejas + boca. Las cejas siempre algo preocupadas (así es el personaje)."""
    if gesto == "neutral":
        cejas = [[(-38, -44), (-6, -50)], [(14, -50), (46, -44)]]
        boca = raya([(-2, 46), (12, 44), (26, 46)], "boca/neutral")
    elif gesto == "susto":
        cejas = [[(-40, -42), (-8, -60)], [(16, -60), (48, -42)]]
        boca = figura(elipse(10, 50, 13, 18, n=22), "boca/susto", NEGRO, amplitud=0.7)
    elif gesto == "alivio":
        cejas = [[(-38, -48), (-6, -56)], [(14, -56), (46, -48)]]
        boca = raya(arco(10, 30, 24, 18, 25, 155), "boca/alivio")
    elif gesto == "sorpresa":          # cejas muy altas y redondas, boca en «o» chiquita
        return (raya(arco(-22, -44, 18, 10, 200, 340, 8), "ceja/sorpresa/0")
                + raya(arco(30, -44, 18, 10, 200, 340, 8), "ceja/sorpresa/1")
                + figura(elipse(8, 50, 9, 12, n=18), "boca/sorpresa", NEGRO, amplitud=0.6))
    elif gesto == "duda":              # cejas preocupadas, una más alta, boca torcida
        cejas = [[(-38, -46), (-6, -54)], [(14, -64), (46, -52)]]
        boca = raya([(-4, 50), (6, 44), (16, 50), (26, 44)], "boca/duda")
    elif gesto == "pensativo":         # cejas rectas, la boca chiquita a un lado
        cejas = [[(-38, -48), (-6, -48)], [(14, -50), (46, -46)]]
        boca = raya([(14, 46), (30, 44)], "boca/pensativo")
    elif gesto == "amable":            # cejas neutras un poco curvas, sonrisa leve
        return (raya(arco(-22, -42, 18, 7, 200, 340, 8), "ceja/amable/0")
                + raya(arco(30, -42, 18, 7, 200, 340, 8), "ceja/amable/1")
                + raya(arco(10, 34, 18, 12, 35, 145, 10), "boca/amable"))
    elif gesto == "seguro":            # cejas rectas y firmes, media sonrisa
        cejas = [[(-38, -46), (-6, -48)], [(14, -48), (46, -46)]]
        boca = raya(arco(14, 32, 20, 13, 25, 140, 10), "boca/seguro")
    elif gesto == "aliviado":          # cejas relajadas, sonrisa
        return (raya(arco(-22, -42, 18, 8, 200, 340, 8), "ceja/aliviado/0")
                + raya(arco(30, -42, 18, 8, 200, 340, 8), "ceja/aliviado/1")
                + raya(arco(10, 30, 24, 18, 25, 155, 12), "boca/aliviado"))
    elif gesto == "contento":          # cejas altas y curvas, sonrisa abierta
        return (raya(arco(-22, -46, 18, 10, 200, 340, 8), "ceja/contento/0")
                + raya(arco(30, -46, 18, 10, 200, 340, 8), "ceja/contento/1")
                + figura(arco(10, 34, 26, 20, 0, 180, 14), "boca/contento", ROJO, amplitud=0.6))
    elif gesto == "disgusto":          # cejas bajas hacia el centro, boca ondulada hacia abajo
        cejas = [[(-38, -52), (-6, -42)], [(14, -42), (46, -52)]]
        boca = raya([(-6, 52), (4, 44), (14, 50), (24, 44), (32, 52)], "boca/disgusto")
    else:  # concentrado
        cejas = [[(-38, -50), (-6, -40)], [(14, -40), (46, -50)]]
        boca = raya([(0, 48), (10, 45), (22, 47)], "boca/concentrado")
    return "".join(raya(c, f"ceja/{gesto}/{i}") for i, c in enumerate(cejas)) + boca


def personaje(pose: str = "de_pie", ojo: str = "abiertos", gesto: str = "neutral", color: str = AMARILLO,
              mochila: bool = True) -> str:
    """El personaje completo: cuerpo + cabeza + ojos + cara."""
    p = POSES[pose]
    if p.get("acostado"):
        return _en_la_cama(ojo, gesto)
    cx, cy = centro_cabeza(p)
    extra = ""
    if p.get("signos"):
        extra += _signos(cx, cy)
    if p.get("bombillo"):
        extra += _bombillo(cx + 120, cy - 120)
    encima = p.get("mano_encima", False)
    if encima:
        extra = _brazo(p["hombro"], p["brazo_frente"], f"cuerpo/{pose}/bf", p.get("dedo", False), color) + extra
    if p.get("mano_abierta"):
        extra += _mano_abierta(p["brazo_frente"], color)
    # cara girada: los rasgos se corren hacia un lado de la cabeza (la cabeza sigue siendo el mismo círculo)
    giro = float(p.get("cara_girada", 0)) * 34
    rasgos = f'<g transform="translate({giro:.1f},0)">' + ojos(ojo) + cara(gesto) + "</g>" if giro else ojos(ojo) + cara(gesto)
    return (cuerpo(pose, color, mochila, not encima) + f'<g transform="translate({cx:.1f},{cy:.1f})">'
            + cabeza() + rasgos + "</g>" + extra)


def _mano_abierta(brazo, color: str) -> str:
    """Palma abierta al final del brazo, con cuatro dedos y el pulgar (gesto de «alto» o rechazo)."""
    codo, mano = brazo
    u = _unit(_menos(mano, codo))
    n = (-u[1], u[0])
    c = (mano[0] + u[0] * 16, mano[1] + u[1] * 16)
    salida = []
    for i, k in enumerate((-1.5, -0.5, 0.5, 1.5)):
        base = (c[0] + u[0] * 10 + n[0] * k * 13, c[1] + u[1] * 10 + n[1] * k * 13)
        largo = 40 - abs(k) * 7
        punta = (base[0] + (u[0] + n[0] * k * 0.18) * largo, base[1] + (u[1] + n[1] * k * 0.18) * largo)
        salida.append(tubo([base, punta], f"mano/d{i}", color, 10))
    pulgar = (c[0] + n[0] * 40 - u[0] * 4, c[1] + n[1] * 40 - u[1] * 4)
    salida.append(tubo([c, pulgar], "mano/p", color, 10))
    salida.append(figura(elipse(c[0], c[1], 25, 25, n=22), "mano/palma", color))
    return "".join(salida)


def _signos(cx: float, cy: float) -> str:
    """Dos signos de pregunta junto a la cabeza (dibujados, no letras)."""
    salida = []
    for i, (dx, dy, k) in enumerate(((-150, -70, 1.0), (-120, -160, 0.75))):
        x, y = cx + dx, cy + dy
        gancho = arco(x, y - 18 * k, 22 * k, 22 * k, 200, 400, 10) + [(x + 2 * k, y + 22 * k)]
        salida.append(raya(gancho, f"signo/{i}", NEGRO, 10))
        salida.append(f'<circle cx="{x + 2 * k:.1f}" cy="{y + 44 * k:.1f}" r="{7 * k:.1f}" fill="{NEGRO}"/>')
    return "".join(salida)


def _bombillo(x: float, y: float) -> str:
    rayos = "".join(raya([(x + math.cos(a) * 64, y + math.sin(a) * 64), (x + math.cos(a) * 86, y + math.sin(a) * 86)],
                         f"bombillo/r{i}", NEGRO, 6) for i, a in enumerate(math.radians(d) for d in (-150, -110, -70, -30, 10, 170)))
    return (figura(elipse(x, y, 42, 44, n=30), "bombillo", AMARILLO)
            + figura([(x - 18, y + 38), (x + 18, y + 38), (x + 16, y + 68), (x - 16, y + 68)], "bombillo/base", "#9A9A9A")
            + rayos)


def _en_la_cama(ojo: str, gesto: str) -> str:
    """Acostado: cama vista de lado, la cabeza en la almohada y el cuerpo bajo la cobija (pies a la derecha)."""
    gris = "#9A9A9A"
    partes = [
        figura([(-300, -60), (-300, -230), (-262, -230), (-262, -60)], "cama/cabecera", gris),
        figura([(-290, -60), (330, -60), (330, 0), (-290, 0)], "cama/base", gris),
        tubo([(-270, 0), (-270, 30)], "cama/pata1", gris, 16),
        tubo([(300, 0), (300, 30)], "cama/pata2", gris, 16),
        figura([(-250, -120), (-110, -126), (-100, -70), (-250, -64)], "cama/almohada", BLANCO),
        figura([(-130, -70), (-90, -150), (60, -168), (230, -150), (322, -104), (330, -60), (-130, -60)],
               "cama/cobija", ROJO),
        raya([(-60, -150), (-20, -90)], "cama/pliegue1", NEGRO, 5, 0.5),
        raya([(140, -160), (170, -96)], "cama/pliegue2", NEGRO, 5, 0.5),
    ]
    cabeza_g = (f'<g transform="translate(-175,-180) rotate(-12) scale(0.9)">' + cabeza() + ojos(ojo) + cara(gesto)
                + "</g>")
    return "".join(partes[:5]) + cabeza_g + "".join(partes[5:])
