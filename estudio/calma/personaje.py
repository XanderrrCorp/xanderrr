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
}

OJOS = ("abiertos", "cerrados", "lado")
CARAS = ("neutral", "susto", "alivio", "concentrado")


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


def cuerpo(nombre: str, color: str = AMARILLO, mochila: bool = True) -> str:
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
        _brazo(hom, p["brazo_frente"], s + "/bf", p.get("dedo", False), color),
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
        dx = 9 if estado == "lado" else 3
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
    else:  # concentrado
        cejas = [[(-38, -50), (-6, -40)], [(14, -40), (46, -50)]]
        boca = raya([(0, 48), (10, 45), (22, 47)], "boca/concentrado")
    return "".join(raya(c, f"ceja/{gesto}/{i}") for i, c in enumerate(cejas)) + boca


def personaje(pose: str = "de_pie", ojo: str = "abiertos", gesto: str = "neutral", color: str = AMARILLO,
              mochila: bool = True) -> str:
    """El personaje completo: cuerpo + cabeza + ojos + cara."""
    cx, cy = centro_cabeza(POSES[pose])
    return (cuerpo(pose, color, mochila) + f'<g transform="translate({cx:.1f},{cy:.1f})">'
            + cabeza() + ojos(ojo) + cara(gesto) + "</g>")
