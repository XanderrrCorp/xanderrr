"""Escenas del primer video de El Calvo Explica («Partes de tu cuerpo que YA NO SIRVEN para nada»).

Corre:  python -m estudio.explica.guiones.partes_que_no_sirven_escenas
Escribe estudio/explica/ejemplos/partes_que_no_sirven.json (el tema 1 sale de tema1_muneca.json).
Cada elemento entra con su «palabra»; los tiempos los pone Whisper (o las frases de la voz) al armar el video.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..escenas import cuadricula

AQUI = Path(__file__).resolve().parent
EJEMPLOS = AQUI.parent / "ejemplos"
A = "aparecer"


def DIB(d=0.5):
    return {"tipo": "dibujar", "duracion": d}


def DESDE(x, y, d=0.6):
    return {"tipo": "deslizar", "desde": [x, y], "duracion": d}


def POSE(palabra, **estado):
    return {"tipo": "cambiar_pose", "palabra": palabra, "estado": estado}


def TEMB(palabra, f=10):
    return {"tipo": "temblor", "palabra": palabra, "fuerza": f}


def el(id, pieza, pos, tam=1.0, palabra=None, mov=None, estado=None, **kw):
    d = {"id": id, "pieza": pieza, "estado": estado or {}, "posicion": list(pos), "tamano": tam,
         "movimiento": mov if mov is not None else [A]}
    if palabra:
        d["palabra"] = palabra
    d.update(kw)
    return d


def ya(id, pieza, pos, tam=1.0, estado=None, mov=None):
    return el(id, pieza, pos, tam, None, mov or [], estado, ya_estaba=True)


GESTO = {"de_pie": "amable", "asustado": "susto", "sorprendido": "sorpresa", "tablero": "seguro", "idea": "contento",
         "sentado": "amable", "pensando": "pensativo", "confundido": "duda", "hombros": "neutral", "aliviado": "aliviado",
         "senalando_contento": "contento", "rechazo": "disgusto", "senalando": "amable", "corriendo": "concentrado",
         "agachado": "concentrado", "acostado": "neutral"}


def P(pose, **e):
    d = {"pose": pose, "gesto": GESTO.get(pose, "amable")}
    d.update(e)
    return d


def T(id, texto, pos, palabra, tam=1.0, rojo=False, **kw):
    return el(id, "texto", pos, tam, palabra, estado={"texto": texto, "color": "rojo" if rojo else "negro"}, **kw)


ESCENAS: list[dict] = []


def S(tipo, inicio, *elementos, temblor=(), empujon=()):
    ESCENAS.append({"tipo": tipo, "palabra_inicio": inicio, "fondo": "blanco",
                    "temblor": [{"palabra": p} for p in temblor],
                    "empujon": [{"palabra": p, "foco": f} for p, f in empujon], "elementos": list(elementos)})


NOMBRES = ["Músculo de la muñeca", "Bultico de la oreja", "Mover las orejas", "Piel de gallina", "Tercer párpado",
           "Muelas del juicio", "La cola que tuviste", "Tetillas en los hombres", "Sensor de la nariz",
           "Músculo de la pantorrilla", "Agarre del bebé", "Apéndice"]
ICONOS = [("muneca", {"dedos": "pinza", "tendon": True}), ("oreja", {"bulto": True}), ("gato", {}),
          ("piel", {"parados": True}), ("ojo", {}), ("boca", {"torcida": True, "resaltar": True}),
          ("columna", {"resaltar": True}), ("plano", {}), ("nariz", {"sensor": True}), ("pierna", {}),
          ("bebe", {"agarra": True}), ("intestino", {"resaltar": True})]
TEMAS = [{"etiqueta": n, "icono": {"pieza": p, "estado": e}} for n, (p, e) in zip(NOMBRES, ICONOS)]


def grid(i, inicio, fin, nombre, rojo):
    ESCENAS.append(cuadricula(TEMAS, i, inicio, fin, nombre, rojo))


def _cabe(texto: str, alto: float, ancho: float, maximo: float) -> float:
    """Tamaño para que el texto quepa en `ancho` px (el tablero mide ~700 px por dentro)."""
    from ...calma.piezas import ancho_texto

    return round(min(maximo, ancho / (ancho_texto(texto.upper(), alto) + 30)), 3)


def bautizo(inicio, titulo, rojo, texto, palabra_titulo, palabra_texto, empuje):
    S("personaje", inicio, el("yo", "personaje", (430, 990), 1.05, inicio.split()[0], [A], P("tablero")),
      el("tab", "tablero", (1180, 480), 1.45, inicio.split()[0]),
      el("n", "titulo_tema", (1180, 430), _cabe(titulo, 110, 660, 0.66), palabra_titulo,
         estado={"texto": titulo, "rojo": rojo}),
      T("t", texto, (1180, 620), palabra_texto, _cabe(texto, 72, 660, 0.8), True), empujon=[(empuje, (1180, 430))])


# ------------------------------------------------------------------ 2. bultico de la oreja
grid(1, "Bultico", "oreja", "Bultico de la oreja", "BULTICO")
S("ilustracion", "Estás frente al espejo",
  el("yo", "personaje", (700, 990), 1.15, "Estás", [A], P("de_pie")),
  el("esp", "tablero", (1300, 470), 1.1, "espejo"),
  el("yo2", "personaje", (1300, 640), 0.55, "baño", [A], P("de_pie", gesto="pensativo")))
S("ilustracion", "Sube un dedo",
  el("or", "oreja", (960, 560), 1.5, "Sube", [DESDE(960, 1300)]),
  el("f", "flecha", (1250, 260), 1.0, "borde", [DIB(0.5)], estado={"curva": 0.3}, rotacion=150))
S("ilustracion", "Recórrelo despacio",
  ya("or", "oreja", (960, 560), 1.5),
  el("c", "circulo_rojo", (960, 380), 1.0, "Recórrelo", [{"tipo": "dibujar", "duracion": 1.0}],
     estado={"ancho": 380, "alto": 300}),
  T("t", "despacio", (1500, 300), "despacio", 0.9))
S("ilustracion", "En algunas personas",
  ya("or", "oreja", (960, 560), 1.5, {}, [POSE("tropieza", bulto=True), TEMB("algo", 8)]),
  el("f", "flecha", (1320, 320), 1.0, "tropieza", [DIB(0.4)], rotacion=200, estado={"curva": 0.2}),
  T("t", "¡algo!", (1500, 200), "algo", 1.2, True), empujon=[("algo", (1100, 380))])
S("ilustracion", "Un engrosamiento",
  ya("or", "oreja", (960, 560), 1.5, {"bulto": True}),
  T("t1", "muy pequeño", (1450, 300), "pequeño", 1.0, True),
  T("t2", "no duele", (1450, 460), "duele", 1.0))
S("ilustracion", "Si lo encuentras",
  el("yo", "personaje", (960, 990), 1.2, "Si", [A], P("aliviado")),
  T("t", "tranquilo", (1450, 400), "asustes", 1.0))
S("ilustracion", "Ahora prueba también",
  el("o1", "oreja", (640, 560), 1.1, "Ahora", estado={"bulto": True}),
  el("o2", "oreja", (1280, 560), 1.1, "otra", [DESDE(2100, 560)]),
  T("t", "¿y la otra?", (1280, 160), "oreja", 0.9))
bautizo("Eso se llama tubérculo", "tubérculo auricular", "TUBÉRCULO", "no todo el mundo lo tiene",
        "tubérculo", "todo", "tubérculo")
S("codigo", "Se cree que es el resto",
  T("t", "se cree que…", (960, 90), "cree", 0.8),
  el("o", "oreja", (960, 560), 1.4, "punta", [A], estado={"punta": True}),
  T("t2", "una punta", (1450, 400), "punta", 1.1, True, retraso=0.2))
S("codigo", "Muchos mamíferos todavía",
  el("g", "gato", (960, 520), 1.4, "mamíferos"),
  el("f", "flecha", (1060, 160), 1.0, "punta", [DIB(0.4)], rotacion=200, estado={"curva": 0.2}),
  T("t", "en punta", (1500, 200), "punta", 1.0, True))
S("codigo", "En la nuestra",
  el("o", "oreja", (960, 560), 1.4, "En"),
  el("x", "x_roja", (1300, 260), 0.6, "ya", [DIB(0.3)]))
S("codigo", "Pero en algunas personas quedó",
  ya("o", "oreja", (960, 560), 1.4, {}, [POSE("marca", bulto=True)]),
  el("c", "circulo_rojo", (1095, 390), 1.0, "marca", [DIB(0.4)], estado={"ancho": 150, "alto": 130}),
  T("t", "una marca", (1500, 300), "borde", 1.0, True))
S("codigo", "Por eso se ve",
  ya("o", "oreja", (960, 560), 1.4, {"bulto": True}, [TEMB("piquito", 8)]),
  T("t", "un piquito", (1500, 300), "piquito", 1.2, True), empujon=[("piquito", (1095, 390))])
S("codigo", "Hoy no cumple",
  el("yo", "personaje", (700, 990), 1.15, "Hoy", [A], P("hombros")),
  T("t", "ninguna función conocida", (1300, 400), "función", 0.9, True))
S("codigo", "Y qué tan común",
  el("g", "grafica_barras", (960, 520), 1.1, "común"),
  T("t", "cambia mucho", (960, 880), "cambia", 1.0, True))
S("personaje", "No es un granito",
  el("yo", "personaje", (640, 990), 1.15, "No", [A], P("rechazo")),
  el("x", "x_roja", (1330, 450), 0.8, "defecto", [DIB(0.35)]))
S("personaje", "Es un pedacito",
  ya("yo", "personaje", (640, 990), 1.15, P("rechazo"), [POSE("pedacito", **P("senalando_contento"))]),
  el("o", "oreja", (1330, 520), 0.9, "oreja", estado={"bulto": True}),
  T("t", "una oreja antigua", (1330, 880), "antigua", 0.9, True))

# ------------------------------------------------------------------ 3. mover las orejas
grid(2, "Mover", "orejas", "Mover las orejas", "OREJAS")
S("ilustracion", "Estás quieto",
  el("yo", "personaje", (960, 990), 1.3, "Estás", [A], P("de_pie", gesto="concentrado")))
S("ilustracion", "Intenta mover",
  ya("yo", "personaje", (960, 990), 1.3, P("de_pie", gesto="concentrado"), [TEMB("mover", 6)]),
  el("o1", "ondas", (1130, 430), 0.8, "mover", [DIB(0.4)]),
  T("t", "sin tocarlas", (1450, 250), "tocarlas", 0.9))
S("ilustracion", "Arrugas la frente",
  el("yo", "personaje", (960, 990), 1.3, "Arrugas", [A, POSE("cejas", gesto="concentrado"), TEMB("dientes", 10)],
     P("de_pie", gesto="pensativo")),
  T("t1", "frente", (1450, 250), "frente", 0.8), T("t2", "cejas", (1450, 400), "cejas", 0.8),
  T("t3", "dientes", (1450, 550), "dientes", 0.8))
S("ilustracion", "Nada",
  el("yo", "personaje", (960, 990), 1.3, "Nada", [A], P("hombros")),
  T("t", "nada", (960, 180), "Nada", 1.4, True))
S("ilustracion", "Como mucho",
  el("o", "oreja", (960, 560), 1.4, "Como", [A, TEMB("tirón", 12)]),
  T("t", "un tirón", (1450, 300), "tirón", 1.0, True))
S("ilustracion", "Las orejas se quedan",
  ya("o", "oreja", (960, 560), 1.4),
  T("t", "quietas", (1450, 300), "estaban", 1.0))
S("ilustracion", "Ahora piensa en un gato",
  el("g", "gato", (960, 560), 1.4, "gato"),
  el("on", "ondas", (1350, 420), 1.0, "ruido", [DIB(0.4)], estado={"color": "rojo"}))
S("ilustracion", "Sus orejas giran",
  ya("g", "gato", (960, 560), 1.4, {}, [{"tipo": "cambiar_pose", "palabra": "giran", "estado": {"giro_orejas": 22}}]),
  el("on", "ondas", (1350, 420), 1.0, "sonido", [DIB(0.3)], estado={"color": "rojo"}),
  T("t", "antenas", (960, 950), "antenas", 1.0, True))
bautizo("Eso se llama músculos", "músculos auriculares", "AURICULARES", "casi nadie los controla",
        "auriculares", "nadie", "auriculares")
S("codigo", "Lo más probable",
  T("t", "lo más probable…", (960, 90), "probable", 0.8),
  el("o", "oreja", (760, 560), 1.2, "orientar", [{"tipo": "girar", "grados": -15, "palabra": "orientar", "duracion": 0.5}]),
  el("on", "ondas", (1250, 520), 1.2, "sonido", [DIB(0.4)], estado={"color": "rojo"}))
S("codigo", "Igual que hace un gato",
  el("g", "gato", (960, 560), 1.3, "gato", [A, {"tipo": "cambiar_pose", "palabra": "oye", "estado": {"giro_orejas": -25}}]),
  el("on", "ondas", (520, 500), 1.0, "detrás", [DIB(0.3)], rotacion=180))
S("codigo", "En nosotros casi",
  el("yo", "personaje", (960, 990), 1.2, "nosotros", [A], P("hombros")),
  T("t", "casi no se usan", (960, 200), "usan", 1.0, True))
S("codigo", "Pero hay algo curioso",
  el("yo", "personaje", (960, 990), 1.2, "Pero", [A], P("idea")),
  T("t", "algo curioso", (960, 200), "curioso", 1.2, True), empujon=[("curioso", (960, 300))])
S("codigo", "Estudios recientes",
  el("doc", "documento", (700, 560), 1.2, "Estudios", estado={"titulo": "ESTUDIO"}),
  T("t", "estudios recientes", (960, 950), "recientes", 0.9),
  el("on", "ondas", (1250, 480), 1.2, "escuchar", [DIB(0.4)]))
S("codigo", "Y vieron que todavía",
  el("o", "oreja", (760, 560), 1.2, "vieron", [A, TEMB("activan", 8)]),
  el("b", "barra", (1350, 520), 0.9, "activan", [A, {"tipo": "llenar_barra", "hasta": 0.25, "duracion": 0.6}],
     estado={"etiqueta": "actividad", "color": "rojo"}),
  T("t", "un poco", (1350, 720), "poco", 1.0, True))
S("codigo", "Como si tu cuerpo",
  el("yo", "personaje", (960, 990), 1.2, "Como", [A, TEMB("girar", 6)], P("de_pie", gesto="concentrado")),
  el("on", "ondas", (1180, 440), 0.9, "girar", [DIB(0.4)]),
  T("t", "ya no giran", (1450, 220), "giran", 1.0, True))
S("personaje", "Tus orejas no se mueven",
  el("yo", "personaje", (640, 990), 1.15, "Tus", [A], P("hombros")),
  el("x", "x_roja", (1330, 450), 0.7, "mueven", [DIB(0.3)]))
S("personaje", "Pero cuando prestas",
  ya("yo", "personaje", (640, 990), 1.15, P("hombros"), [POSE("atención", **P("idea"))]),
  el("on", "ondas", (1250, 420), 1.0, "atención", [DIB(0.4)], estado={"color": "rojo"}),
  T("t", "todavía lo intentan", (1330, 800), "intentan", 0.9, True))

# ------------------------------------------------------------------ 4. piel de gallina
grid(3, "Piel", "gallina", "Piel de gallina", "GALLINA")
S("ilustracion", "Estás en la parada",
  el("yo", "personaje", (700, 990), 1.15, "Estás", [A, TEMB("frío", 10)], P("asustado", gesto="concentrado")),
  el("nv", "nieve", (1250, 420), 1.4, "viento"),
  T("t", "frío", (1450, 800), "frío", 1.1, True))
S("ilustracion", "O ves una película",
  el("yo", "personaje", (700, 990), 1.15, "ves", [A], P("sorprendido")),
  el("tv", "tablero", (1300, 470), 1.0, "película"),
  T("t", "miedo", (1300, 430), "miedo", 1.0, True))
S("ilustracion", "O suena esa canción",
  el("yo", "personaje", (700, 990), 1.15, "suena", [A], P("aliviado", ojos="cerrados")),
  el("on", "ondas", (1250, 420), 1.4, "canción", [DIB(0.5)]))
S("ilustracion", "Y de pronto",
  el("p", "piel", (960, 560), 1.4, "pronto", [A, POSE("levantan", parados=True), TEMB("levantan", 8)]),
  T("t", "se levantan", (960, 180), "levantan", 1.0, True), empujon=[("levantan", (960, 560))])
S("ilustracion", "La piel se llena",
  ya("p", "piel", (960, 560), 1.4, {"parados": True}),
  T("t", "puntitos", (960, 880), "puntitos", 1.1, True))
S("ilustracion", "Pasa solo",
  el("yo", "personaje", (960, 990), 1.2, "Pasa", [A], P("confundido")),
  T("t", "sin que lo decidas", (1450, 300), "decidas", 0.9))
S("ilustracion", "Te frotas el brazo",
  el("p", "piel", (960, 560), 1.4, "frotas", [A, TEMB("frotas", 14)], estado={"parados": True}),
  T("t", "sigue ahí", (960, 880), "sigue", 1.0, True))
bautizo("Eso se llama piel", "piel de gallina", "GALLINA", "viene de muy atrás", "gallina", "atrás", "gallina")
S("codigo", "Cada pelo de tu cuerpo",
  el("p", "piel", (960, 560), 1.4, "pelo"),
  el("c", "circulo_rojo", (700, 520), 1.0, "músculo", [DIB(0.4)], estado={"ancho": 160, "alto": 160}),
  T("t", "un músculo diminuto", (960, 880), "diminuto", 1.0, True))
S("codigo", "Cuando se contrae",
  ya("p", "piel", (960, 560), 1.4, {}, [POSE("levanta", parados=True)]),
  el("f", "flecha", (1450, 520), 1.0, "levanta", [DIB(0.4)], rotacion=-90, estado={"curva": 0.05}))
S("codigo", "Lo más probable es que eso",
  T("t", "lo más probable…", (960, 90), "probable", 0.8),
  el("g", "gato", (960, 560), 1.3, "pelaje"),
  T("t2", "pelaje", (1450, 800), "pelaje", 1.0, True))
S("codigo", "Con mucho pelo parado",
  el("g", "gato", (760, 560), 1.3, "Con", estado={"erizado": True}),
  el("f", "flecha", (1250, 560), 0.9, "atrapada", [DIB(0.4)], rotacion=180, estado={"curva": 0.2}),
  T("t", "aire caliente", (1450, 400), "caliente", 1.0, True))
S("codigo", "Y además el animal",
  el("g", "gato", (960, 560), 1.2, "animal", [A, {"tipo": "crecer", "hasta": 1.3, "palabra": "grande", "duracion": 0.6},
                                                 TEMB("asustado", 10)], estado={"erizado": True}),
  T("t", "más grande", (1500, 250), "grande", 1.0, True))
S("codigo", "Con tan poco pelo",
  el("yo", "personaje", (700, 990), 1.15, "Con", [A, TEMB("abriga", 10)], P("asustado", gesto="concentrado")),
  el("x", "x_roja", (1350, 450), 0.7, "abriga", [DIB(0.3)]),
  T("t", "no abriga", (1350, 750), "abriga", 1.0, True))
S("codigo", "Ni te hace ver",
  ya("yo", "personaje", (700, 990), 1.15, P("asustado", gesto="concentrado"), [POSE("Ni", **P("hombros"))]),
  T("t", "ni asusta", (1350, 450), "grande", 1.0))
S("personaje", "Cada vez que se te eriza",
  el("p", "piel", (1330, 450), 0.8, "eriza", [A], estado={"parados": True}),
  el("yo", "personaje", (600, 990), 1.15, "esponja", [A], P("senalando_contento")),
  T("t", "un abrigo que ya no tienes", (1330, 820), "abrigo", 0.8, True))

# ------------------------------------------------------------------ 5. tercer párpado
grid(4, "Tercer", "párpado", "Tercer párpado", "PÁRPADO")
S("ilustracion", "Estás frente al espejo",
  el("yo", "personaje", (700, 990), 1.15, "Estás", [A], P("de_pie", gesto="concentrado")),
  el("esp", "tablero", (1300, 470), 1.1, "espejo"),
  T("t", "muy cerca", (1300, 900), "cerca", 0.9))
S("ilustracion", "Mírate un ojo",
  el("ojo", "ojo", (960, 540), 1.8, "ojo"),
  el("f", "flecha", (300, 300), 1.0, "esquina", [DIB(0.4)], rotacion=40, estado={"curva": 0.2}),
  T("t", "junto a la nariz", (480, 860), "nariz", 0.9))
S("ilustracion", "Ahí hay un pliegue",
  ya("ojo", "ojo", (960, 540), 1.8),
  el("c", "circulo_rojo", (546, 540), 1.0, "pliegue", [DIB(0.4)], estado={"ancho": 170, "alto": 260}),
  T("t", "rosado", (480, 860), "rosado", 1.1, True), empujon=[("pliegue", (546, 540))])
S("ilustracion", "Parece un pedacito",
  ya("ojo", "ojo", (960, 540), 1.8),
  T("t", "¿sin importancia?", (1300, 900), "importancia", 0.9))
S("ilustracion", "Te acercas más",
  el("ojo", "ojo", (1100, 540), 2.2, "acercas", [A, {"tipo": "crecer", "hasta": 1.12, "palabra": "verlo", "duracion": 1.0}]))
S("ilustracion", "Es suave y brilla",
  ya("ojo", "ojo", (1100, 540), 2.4),
  T("t", "brilla", (1500, 900), "brilla", 1.0, True))
S("ilustracion", "Siempre estuvo ahí",
  el("yo", "personaje", (960, 990), 1.2, "Siempre", [A], P("sorprendido")),
  T("t", "siempre estuvo ahí", (960, 180), "ahí", 1.0, True))
bautizo("Eso se llama pliegue", "pliegue semilunar", "SEMILUNAR", "un tercer párpado", "semilunar", "tercer",
        "semilunar")
S("codigo", "Muchas aves",
  el("g", "gato", (960, 540), 1.2, "gatos"),
  T("t1", "aves", (400, 300), "aves", 1.0), T("t2", "reptiles", (400, 500), "reptiles", 1.0),
  T("t3", "tercer párpado", (1450, 880), "verdad", 0.9, True))
S("codigo", "Es una tela delgada",
  el("ojo", "ojo", (960, 540), 1.6, "tela", estado={"animal": True}),
  el("f", "flecha", (960, 860), 1.2, "cruza", [DIB(0.6)], estado={"curva": 0.0}),
  T("t", "de lado", (960, 980), "lado", 0.9, True))
S("codigo", "Se piensa que nuestro",
  T("t", "se piensa que…", (960, 90), "piensa", 0.8),
  el("o1", "ojo", (560, 540), 0.9, "nuestro"),
  el("o2", "ojo", (1360, 540), 0.9, "resto", estado={"animal": True}),
  el("f", "flecha", (960, 540), 0.8, "resto", [DIB(0.4)], rotacion=180, estado={"curva": 0.1}))
S("codigo", "Con el tiempo",
  el("ojo", "ojo", (960, 540), 1.6, "tiempo", [A, {"tipo": "crecer", "hasta": 0.8, "palabra": "reducido", "duracion": 0.8}]),
  T("t", "reducido", (960, 900), "reducido", 1.1, True))
S("codigo", "Ya no cruza",
  ya("ojo", "ojo", (960, 540), 1.3),
  el("x", "x_roja", (960, 540), 1.0, "cruza", [DIB(0.4)]))
S("codigo", "Se queda quieto",
  ya("ojo", "ojo", (960, 540), 1.6),
  el("c", "circulo_rojo", (546, 540), 1.0, "esquina", [DIB(0.4)], estado={"ancho": 170, "alto": 260}),
  T("t", "en su esquina", (480, 860), "nariz", 0.9, True))
S("personaje", "Cada vez que te miras",
  el("yo", "personaje", (640, 990), 1.15, "Cada", [A], P("senalando_contento")),
  el("ojo", "ojo", (1330, 480), 0.9, "párpado"),
  T("t", "ya no se cierra", (1330, 820), "cierra", 1.0, True))

# ------------------------------------------------------------------ 6. muelas del juicio
grid(5, "Muelas", "juicio", "Muelas del juicio", "JUICIO")
S("ilustracion", "Estás en la silla",
  el("yo", "personaje", (960, 990), 1.2, "Estás", [A], P("sentado", gesto="concentrado")),
  T("t", "el dentista", (1450, 300), "dentista", 1.0))
S("ilustracion", "Te duele el fondo",
  el("b", "boca", (960, 560), 1.4, "duele", [A, TEMB("duele", 8)]),
  el("c", "circulo_rojo", (1170, 470), 1.0, "fondo", [DIB(0.4)], estado={"ancho": 200, "alto": 200}),
  T("t", "hace días", (960, 900), "días", 0.9))
S("ilustracion", "Tienes la mejilla",
  el("yo", "personaje", (960, 990), 1.2, "mejilla", [A, TEMB("hinchada", 10)], P("asustado", gesto="concentrado")),
  T("t", "hinchada", (1450, 300), "hinchada", 1.1, True))
S("ilustracion", "El dentista mira",
  el("doc", "documento", (960, 540), 1.3, "radiografía", estado={"titulo": "RAYOS"}),
  el("f", "flecha", (1350, 380), 1.0, "señala", [DIB(0.4)], rotacion=200, estado={"curva": 0.2}))
S("ilustracion", "Una muela que viene",
  el("b", "boca", (960, 560), 1.4, "muela", [A, POSE("torcida", torcida=True, resaltar=True)]),
  T("t", "torcida", (1450, 250), "torcida", 1.1, True), empujon=[("torcida", (1200, 500))])
S("ilustracion", "No tiene espacio",
  ya("b", "boca", (960, 560), 1.4, {"torcida": True, "resaltar": True}, [TEMB("espacio", 10)]),
  T("t", "sin espacio", (960, 880), "espacio", 1.1, True))
S("ilustracion", "Empuja a las demás",
  ya("b", "boca", (960, 560), 1.4, {"torcida": True, "resaltar": True}, [TEMB("Empuja", 14)]),
  el("f", "flecha", (900, 300), 1.0, "Empuja", [DIB(0.4)], rotacion=180, estado={"curva": 0.1}),
  T("t", "bus lleno", (1450, 880), "lleno", 0.9))
bautizo("Eso es una muela", "muela del juicio", "JUICIO", "la última en salir", "juicio", "última", "juicio")
S("codigo", "La explicación más aceptada tiene",
  T("t", "la más aceptada", (960, 90), "aceptada", 0.8),
  el("b", "boca", (960, 560), 1.3, "mandíbula"),
  T("t2", "la mandíbula", (960, 880), "mandíbula", 1.0, True))
S("codigo", "Nuestros antepasados tenían",
  el("b", "boca", (960, 560), 1.2, "antepasados", estado={"grande": True}),
  T("t", "más grandes", (960, 880), "grandes", 1.0, True))
S("codigo", "Y comían cosas",
  el("rama", "rama", (960, 450), 1.0, "comían"),
  T("t", "más duras", (960, 800), "duras", 1.0, True))
S("codigo", "En una boca así",
  el("b", "boca", (960, 560), 1.2, "boca", [A, POSE("extra", resaltar=True)], estado={"grande": True}),
  el("ok", "chulo", (1500, 300), 0.8, "cabía", [DIB(0.3)]))
S("codigo", "Hoy nuestras mandíbulas",
  el("b", "boca", (960, 560), 1.2, "mandíbulas"),
  T("t1", "más pequeñas", (960, 880), "pequeñas", 1.0, True),
  T("t2", "comida blanda", (960, 200), "blanda", 0.9))
S("codigo", "Por eso muchas veces",
  el("b", "boca", (960, 560), 1.3, "eso", [A, TEMB("cabe", 10)], estado={"torcida": True, "resaltar": True}),
  el("x", "x_roja", (1300, 330), 0.6, "cabe", [DIB(0.3)]))
S("codigo", "Llega tarde",
  el("yo", "personaje", (960, 990), 1.2, "Llega", [A], P("corriendo")),
  T("t", "llega tarde", (960, 200), "tarde", 1.1, True))
S("personaje", "Y hay un dato raro",
  el("yo", "personaje", (640, 990), 1.15, "dato", [A], P("sorprendido")),
  el("fila", "fila_personas", (1330, 650), 0.95, "cinco", [A, POSE("nace", destacada=2)], estado={"cuantas": 5}),
  T("t", "1 de cada 5", (1330, 260), "cinco", 1.1, True), empujon=[("nace", (1330, 600))])

# ------------------------------------------------------------------ 7. la cola que tuviste
grid(6, "La", "tuviste", "La cola que tuviste", "COLA")
S("ilustracion", "Estás sentado",
  el("yo", "personaje", (960, 990), 1.3, "Estás", [A, TEMB("mueves", 8)], P("sentado")),
  T("t", "silla dura", (1450, 300), "dura", 0.9))
S("ilustracion", "Al final de tu espalda",
  el("col", "columna", (960, 560), 1.1, "espalda", [A, POSE("hueso", resaltar=True)]),
  el("f", "flecha", (1250, 900), 1.0, "hueso", [DIB(0.4)], rotacion=180, estado={"curva": 0.2}))
S("ilustracion", "Ahí, donde termina",
  ya("col", "columna", (960, 560), 1.1, {"resaltar": True}),
  T("t", "fin de la columna", (1450, 400), "columna", 0.9, True), empujon=[("termina", (960, 900))])
S("ilustracion", "Si alguna vez",
  el("yo", "personaje", (960, 990), 1.3, "alguna", [A, POSE("caíste", **P("sentado", gesto="susto")), TEMB("caíste", 16)],
     P("asustado")))
S("ilustracion", "Ese dolor",
  el("yo", "personaje", (960, 990), 1.3, "dolor", [A], P("sentado", gesto="concentrado")),
  T("t", "¡ay!", (1450, 300), "dolor", 1.4, True))
S("ilustracion", "Pasaste días",
  el("yo", "personaje", (960, 990), 1.3, "Pasaste", [A, {"tipo": "girar", "grados": 12, "palabra": "lado"}],
     P("sentado", gesto="concentrado")),
  T("t", "de lado", (1450, 300), "lado", 1.0))
S("ilustracion", "Duele solo",
  el("yo", "personaje", (960, 990), 1.3, "Duele", [A], P("confundido")))
bautizo("Ese hueso se llama", "coxis", "COXIS", "lo que queda de una cola", "coxis", "cola", "coxis")
S("codigo", "En las primeras semanas",
  el("e", "embrion", (960, 560), 1.4, "embrión"),
  el("c", "circulo_rojo", (1080, 770), 1.0, "cola", [DIB(0.4)], estado={"ancho": 170, "alto": 200}))
S("codigo", "Una cola de verdad",
  ya("e", "embrion", (960, 560), 1.4),
  T("t", "una cola de verdad", (960, 120), "verdad", 1.0, True))
S("codigo", "Tú también",
  el("yo", "personaje", (960, 990), 1.2, "Tú", [A], P("sorprendido")),
  T("t", "tú también", (960, 200), "tuviste", 1.1, True))
S("codigo", "Después se reabsorbió",
  el("e", "embrion", (960, 560), 1.4, "Después", [A, POSE("reabsorbió", cola=False)]),
  T("t", "desapareció", (960, 950), "desapareció", 1.0, True))
S("codigo", "Lo que quedó",
  el("col", "columna", (960, 560), 1.1, "quedó", [A, POSE("huesitos", resaltar=True)]),
  T("t", "huesitos", (1400, 900), "huesitos", 1.0, True))
S("codigo", "Se cree que el coxis",
  T("t", "se cree que…", (960, 90), "cree", 0.8),
  el("e", "embrion", (640, 560), 0.9, "coxis"),
  el("col", "columna", (1300, 560), 0.9, "queda", estado={"resaltar": True}))
S("codigo", "Por eso mucha gente",
  el("g", "gente", (960, 900), 1.0, "gente"),
  T("t", "«no sirve»", (960, 250), "sirve", 1.1, True))
S("personaje", "Pero no es inútil",
  el("yo", "personaje", (640, 990), 1.15, "Pero", [A], P("idea")),
  el("x", "x_roja", (1330, 450), 0.7, "inútil", [DIB(0.3)]))
S("personaje", "Ahí se sujetan",
  el("col", "columna", (1330, 540), 0.9, "sujetan", [A], estado={"resaltar": True}),
  el("yo", "personaje", (640, 990), 1.15, "Ahí", [A, POSE("sientas", **P("sentado"))], P("senalando_contento")),
  T("t", "músculos y ligamentos", (1330, 980), "ligamentos", 0.8, True))

# ------------------------------------------------------------------ 8. tetillas en los hombres
grid(7, "Tetillas", "hombres", "Tetillas en los hombres", "TETILLAS")
S("ilustracion", "Estás en la piscina",
  el("yo", "personaje", (700, 990), 1.15, "Estás", [A], P("de_pie")),
  T("t", "un día de sol", (1450, 300), "sol", 1.0, True))
S("ilustracion", "Hay gente nadando",
  el("g", "gente", (960, 900), 1.0, "gente"),
  T("t", "en la orilla", (960, 220), "orilla", 0.9))
S("ilustracion", "Un señor sale del agua",
  el("v", "vecino", (960, 990), 1.2, "señor", [DESDE(960, 1400, 0.6)], P("de_pie")),
  T("t", "camiseta en la mano", (1450, 300), "camiseta", 0.8))
S("ilustracion", "Tiene tetillas",
  el("tor", "torso", (960, 540), 1.3, "Tiene"),
  T("t", "como cualquier persona", (960, 950), "persona", 0.9))
S("ilustracion", "Y entonces te surge",
  el("yo", "personaje", (960, 990), 1.2, "entonces", [A], P("confundido")),
  T("t", "¿por qué?", (1450, 300), "pregunta", 1.2, True))
S("ilustracion", "Si en los hombres",
  ya("yo", "personaje", (960, 990), 1.2, P("confundido"), [POSE("función", **P("pensando"))]),
  T("t", "ninguna función", (1450, 250), "función", 0.9),
  T("t2", "¿para qué?", (1450, 450), "qué", 1.1, True))
bautizo("Eso es un rastro", "un rastro", "RASTRO", "de antes de nacer", "rastro", "nacer", "rastro")
S("codigo", "En las primeras semanas, todos",
  el("e1", "embrion", (640, 560), 1.0, "embriones", estado={"cola": False}),
  el("e2", "embrion", (1280, 560), 1.0, "embriones", estado={"cola": False}, retraso=0.15),
  T("t", "el mismo plano", (960, 950), "plano", 1.0, True))
S("codigo", "Todavía no se nota",
  ya("e1", "embrion", (640, 560), 1.0, {"cola": False}), ya("e2", "embrion", (1280, 560), 1.0, {"cola": False}),
  T("t1", "¿hombre?", (640, 150), "hombre", 1.0), T("t2", "¿mujer?", (1280, 150), "mujer", 1.0))
S("codigo", "En esas semanas ya",
  el("pl", "plano", (960, 540), 1.3, "semanas"),
  T("t", "ya aparecen", (1450, 880), "aparecen", 1.0, True))
S("codigo", "Después, el cuerpo sigue",
  el("p1", "personaje", (640, 990), 1.1, "cuerpo", [A], P("de_pie")),
  el("p2", "vecino", (1280, 990), 1.1, "camino", [A], P("de_pie")),
  el("f", "flecha", (960, 500), 0.9, "camino", [DIB(0.4)], estado={"curva": 0.2}))
S("codigo", "Una de las ideas",
  T("t", "una idea aceptada", (960, 90), "aceptadas", 0.8),
  el("pl", "plano", (960, 560), 1.2, "entonces"),
  el("ok", "chulo", (1400, 300), 0.8, "hechas", [DIB(0.3)]))
S("codigo", "Y se quedan",
  ya("pl", "plano", (960, 560), 1.2),
  T("t", "se quedan", (960, 950), "quedan", 1.1, True))
S("codigo", "En los hombres no cumplen",
  el("tor", "torso", (960, 540), 1.2, "hombres"),
  T("t", "sin función", (1450, 880), "función", 1.0, True))
S("personaje", "No son un error",
  el("yo", "personaje", (640, 990), 1.15, "No", [A], P("rechazo")),
  el("x", "x_roja", (1330, 450), 0.7, "error", [DIB(0.3)]))
S("personaje", "Son la marca",
  ya("yo", "personaje", (640, 990), 1.15, P("rechazo"), [POSE("marca", **P("senalando_contento"))]),
  el("pl", "plano", (1330, 520), 0.9, "plano"),
  T("t", "el mismo plano", (1330, 950), "plano", 0.9, True, retraso=0.2))

# ------------------------------------------------------------------ 9. sensor de la nariz
grid(8, "Sensor", "nariz", "Sensor de la nariz", "SENSOR")
S("ilustracion", "Estás en la sala",
  el("g", "gato", (960, 560), 1.4, "gato", [A, {"tipo": "deslizar", "hasta": [960, 520], "palabra": "levanta", "duracion": 0.4}]))
S("ilustracion", "Olfatea el aire",
  ya("g", "gato", (960, 540), 1.4, {}, [POSE("boca", oliendo=True)]),
  T("t", "una mueca rara", (1450, 880), "mueca", 0.9, True), empujon=[("mueca", (960, 640))])
S("ilustracion", "Como si estuviera",
  ya("g", "gato", (960, 540), 1.4, {"oliendo": True}),
  el("on", "ondas", (1350, 420), 1.0, "mensaje", [DIB(0.5)], estado={"color": "rojo"}),
  T("t", "un mensaje invisible", (960, 950), "invisible", 0.9, True))
S("ilustracion", "Huele la esquina",
  el("g", "gato", (760, 540), 1.2, "Huele", [A, TEMB("vez", 6)], estado={"oliendo": True}),
  T("t", "una y otra vez", (1450, 400), "vez", 0.9))
S("ilustracion", "Tú respiras hondo",
  el("yo", "personaje", (960, 990), 1.2, "respiras", [A], P("hombros")),
  T("t", "nada", (1450, 300), "nada", 1.2, True))
S("ilustracion", "Para ti, en la sala",
  ya("yo", "personaje", (960, 990), 1.2, P("hombros")),
  T("t", "no pasa nada", (960, 200), "pasa", 1.0))
S("ilustracion", "Para él, alguien",
  el("g", "gato", (960, 540), 1.4, "él", estado={"oliendo": True}),
  el("on", "ondas", (1350, 420), 1.0, "señal", [DIB(0.4)], estado={"color": "rojo"}),
  T("t", "una señal", (960, 950), "señal", 1.0, True))
bautizo("Eso se llama órgano", "órgano vomeronasal", "VOMERONASAL", "un sensor en la nariz", "vomeronasal",
        "sensor", "vomeronasal")
S("codigo", "En muchos animales",
  el("g", "gato", (700, 540), 1.1, "animales"),
  el("on", "ondas", (1100, 480), 1.0, "señales", [DIB(0.4)], estado={"color": "rojo"}),
  T("t", "señales químicas", (1400, 880), "químicas", 0.9, True))
S("codigo", "Es como leer mensajes",
  el("doc", "documento", (960, 540), 1.2, "mensajes", estado={"titulo": "SEÑAL"}),
  T("t", "en el aire", (1450, 880), "aire", 1.0))
S("codigo", "En parte de los adultos",
  el("n", "nariz", (960, 560), 1.4, "adultos", [A, POSE("resto", sensor=True)]),
  el("c", "circulo_rojo", (1275, 625), 1.0, "tabique", [DIB(0.4)], estado={"ancho": 150, "alto": 130}),
  T("t", "un pequeño resto", (960, 120), "resto", 1.0, True))
S("codigo", "Se piensa que es lo que queda",
  T("t", "se piensa que…", (960, 90), "piensa", 0.8),
  el("n", "nariz", (960, 560), 1.4, "queda", estado={"sensor": True}))
S("codigo", "Pero los estudios",
  el("doc", "documento", (700, 540), 1.1, "estudios", estado={"titulo": "ESTUDIO"}),
  el("x", "x_roja", (1300, 520), 0.8, "demostrado", [DIB(0.3)]),
  T("t", "no demostrado", (1300, 880), "funcione", 0.9, True))
S("codigo", "Ni que esté conectado",
  el("cab", "cable", (960, 540), 1.4, "conectado", [A, TEMB("cerebro", 8)]),
  T("t", "¿conectado?", (960, 850), "cerebro", 1.1, True))
S("personaje", "Tu gato lee",
  el("g", "gato", (1330, 480), 0.9, "gato"),
  el("yo", "personaje", (640, 990), 1.15, "lee", [A], P("senalando_contento")),
  el("on", "ondas", (1600, 420), 0.8, "aire", [DIB(0.3)], estado={"color": "rojo"}))
S("personaje", "Tú tienes el sensor",
  el("yo", "personaje", (640, 990), 1.15, "Tú", [A], P("hombros")),
  el("cab", "cable", (1330, 520), 0.9, "sensor"),
  T("t", "quizá desconectado", (1330, 820), "desconectado", 0.9, True))

# ------------------------------------------------------------------ 10. músculo de la pantorrilla
grid(9, "Músculo", "pantorrilla", "Músculo de la pantorrilla", "PANTORRILLA")
S("ilustracion", "Estás de pie",
  el("yo", "personaje", (960, 990), 1.3, "Estás", [A, {"tipo": "deslizar", "hasta": [960, 950], "palabra": "puntas", "duracion": 0.4}],
     P("asustado", gesto="concentrado")),
  T("t", "algo alto", (1450, 250), "alto", 0.9))
S("ilustracion", "Sientes cómo se endurece",
  el("pi", "pierna", (960, 900), 1.4, "Sientes", [A, TEMB("endurece", 8)]),
  T("t", "pantorrilla", (1450, 300), "pantorrilla", 1.0, True))
S("ilustracion", "Ahí atrás",
  ya("pi", "pierna", (960, 900), 1.4),
  T("t1", "rodilla", (500, 300), "rodilla", 0.9), T("t2", "talón", (500, 850), "talón", 0.9),
  T("t3", "varios músculos", (1450, 500), "músculos", 0.9, True))
S("ilustracion", "Uno de ellos",
  ya("pi", "pierna", (960, 900), 1.4),
  el("cor", "cordon", (900, 560), 1.0, "delgado", [DIB(0.6)], rotacion=88),
  T("t", "tendón larguísimo", (1450, 400), "larguísimo", 0.9, True))
S("ilustracion", "Y es posible",
  el("yo", "personaje", (960, 990), 1.2, "posible", [A], P("sorprendido")),
  T("t", "¿lo tienes?", (1450, 300), "tengas", 1.2, True))
S("ilustracion", "No lo notarías",
  ya("yo", "personaje", (960, 990), 1.2, P("sorprendido"), [POSE("notarías", **P("hombros"))]),
  T("t", "nunca", (1450, 300), "nunca", 1.1))
S("ilustracion", "Te bajas",
  el("yo", "personaje", (960, 990), 1.2, "bajas", [A], P("de_pie")),
  el("ok", "chulo", (1450, 400), 0.7, "distinto", [DIB(0.3)]))
bautizo("Ese músculo se llama", "plantar", "PLANTAR", "a algunos les falta", "plantar", "falta", "plantar")
S("codigo", "La hipótesis principal es que viene",
  T("t", "hipótesis principal", (960, 90), "principal", 0.8),
  el("rama", "rama", (960, 320), 1.2, "primates"),
  el("yo", "personaje", (960, 720), 1.0, "primates", [DESDE(960, 1300)], P("asustado", gesto="contento")))
S("codigo", "En ellos, este músculo",
  ya("rama", "rama", (960, 320), 1.2),
  ya("yo", "personaje", (960, 720), 1.0, P("asustado", gesto="contento"), [TEMB("agarrar", 8)]),
  T("t", "agarrar con los pies", (1450, 800), "pies", 0.9, True))
S("codigo", "Pueden sujetarse",
  el("rama", "rama", (960, 320), 1.2, "rama", [A, TEMB("mano", 6)]),
  el("m", "muneca", (1500, 650), 0.4, "mano"))
S("codigo", "Nosotros caminamos",
  el("yo", "personaje", (960, 990), 1.3, "caminamos", [A], P("corriendo")),
  el("x", "x_roja", (1450, 400), 0.6, "agarramos", [DIB(0.3)]))
S("codigo", "Hoy, alrededor",
  el("fila", "fila_personas", (960, 650), 1.1, "Hoy", [A, POSE("tiene", destacada=4)], estado={"cuantas": 10}),
  T("t", "1 de cada 10", (960, 230), "diez", 1.2, True), empujon=[("tiene", (960, 600))])
S("codigo", "Y no nota",
  ya("fila", "fila_personas", (960, 650), 1.1, {"cuantas": 10, "destacada": 4}),
  el("ok", "chulo", (1700, 300), 0.7, "diferencia", [DIB(0.3)]),
  T("t", "ni lo nota", (960, 950), "diferencia", 1.0, True))
S("personaje", "Tu pie dejó",
  el("yo", "personaje", (640, 990), 1.15, "pie", [A], P("senalando_contento")),
  el("rama", "rama", (1330, 450), 0.7, "ramas"))
S("personaje", "Este músculo todavía",
  ya("yo", "personaje", (640, 990), 1.15, P("senalando_contento"), [POSE("enterado", **P("hombros"))]),
  el("cor", "cordon", (1330, 520), 1.0, "músculo", [DIB(0.4)]),
  T("t", "no se ha enterado", (1330, 800), "enterado", 0.9, True))

# ------------------------------------------------------------------ 11. agarre del bebé
grid(10, "Agarre", "bebé", "Agarre del bebé", "BEBÉ")
S("ilustracion", "Estás de visita",
  el("yo", "personaje", (640, 990), 1.15, "Estás", [A], P("de_pie")),
  el("bb", "bebe", (1250, 560), 1.1, "bebé", [DESDE(2000, 560)]))
S("ilustracion", "Es pequeñito",
  el("bb", "bebe", (960, 560), 1.5, "pequeñito"),
  T("t", "recién nacido", (1450, 880), "ojos", 0.9))
S("ilustracion", "Le acercas un dedo",
  ya("bb", "bebe", (960, 560), 1.5),
  el("d", "brazo", (1450, 640), 0.8, "dedo", [DESDE(2100, 640)]))
S("ilustracion", "Y de pronto lo agarra",
  el("bb", "bebe", (960, 560), 1.5, "pronto", [A, TEMB("agarra", 10)], estado={"agarra": True}),
  T("t", "¡lo agarra!", (960, 160), "agarra", 1.2, True), empujon=[("agarra", (1150, 640))])
S("ilustracion", "Te aprieta",
  ya("bb", "bebe", (960, 560), 1.5, {"agarra": True}, [TEMB("fuerza", 12)]),
  T("t", "¡qué fuerza!", (960, 160), "fuerza", 1.2, True))
S("ilustracion", "No te quiere",
  ya("bb", "bebe", (960, 560), 1.5, {"agarra": True}),
  T("t", "no te suelta", (960, 160), "soltar", 1.1))
S("ilustracion", "Todos en la sala",
  el("g", "gente", (960, 900), 1.0, "Todos"),
  T("t", "ja ja", (960, 260), "ríen", 1.1))
bautizo("Eso se llama reflejo", "reflejo de prensión", "PRENSIÓN", "no lo hace a propósito", "prensión",
        "propósito", "prensión")
S("codigo", "Una de las ideas más aceptadas es que viene",
  T("t", "una idea aceptada", (960, 90), "aceptadas", 0.8),
  el("rama", "rama", (960, 320), 1.2, "primates"))
S("codigo", "Las crías de muchos",
  ya("rama", "rama", (960, 320), 1.2),
  el("yo", "personaje", (960, 720), 1.0, "crías", [DESDE(960, 1300)], P("asustado", gesto="contento")),
  T("t", "colgadas", (1500, 700), "colgadas", 1.0, True))
S("codigo", "Se agarran fuerte",
  ya("rama", "rama", (960, 320), 1.2, {}, [TEMB("agarran", 8)]),
  ya("yo", "personaje", (960, 720), 1.0, P("asustado", gesto="contento")),
  T("t", "para no caerse", (1500, 700), "caerse", 0.9, True))
S("codigo", "Para ellas",
  el("cor", "corazon", (960, 540), 1.3, "apretón", [A, {"tipo": "crecer", "hasta": 1.15, "palabra": "importante", "duracion": 0.4}]),
  T("t", "muy importante", (960, 880), "importante", 1.0, True))
S("codigo", "El bebé humano",
  el("bb", "bebe", (760, 560), 1.2, "bebé", estado={"agarra": True}),
  T("t", "heredó el reflejo", (1350, 300), "heredó", 0.9, True),
  el("x", "x_roja", (1500, 700), 0.5, "pelaje", [DIB(0.3)]))
S("codigo", "Lo hace sin pensarlo",
  el("cer", "cerebro", (960, 540), 1.2, "pensarlo"),
  el("x", "x_roja", (960, 540), 0.8, "sin", [DIB(0.3)]))
S("codigo", "Por eso aprieta",
  el("bb", "bebe", (960, 560), 1.5, "aprieta", [A, TEMB("mano", 10)], estado={"agarra": True}),
  T("t", "lo que le pongas", (960, 160), "pongas", 1.0, True))
S("personaje", "Y desaparece solo",
  el("yo", "personaje", (640, 990), 1.15, "desaparece", [A], P("idea")),
  el("cal", "calendario", (1330, 520), 1.1, "meses", estado={"texto": "6 MESES"}),
  T("t", "5 a 6 meses", (1330, 850), "seis", 1.0, True))
S("personaje", "Ya no tiene",
  ya("yo", "personaje", (640, 990), 1.15, P("idea"), [POSE("colgarse", **P("senalando_contento"))]),
  el("rama", "rama", (1330, 450), 0.7, "colgarse"))

# ------------------------------------------------------------------ 12. el apéndice
grid(11, "El", "apéndice", "El apéndice", "APÉNDICE")
S("ilustracion", "Estás en clase",
  el("yo", "personaje", (430, 990), 1.05, "Estás", [A], P("sentado")),
  el("tab", "tablero", (1180, 480), 1.45, "dibujo"),
  el("int", "intestino", (1180, 460), 0.55, "dentro"))
S("ilustracion", "Sigues el intestino",
  el("int", "intestino", (960, 540), 1.3, "intestino"),
  el("f", "flecha", (960, 150), 1.0, "curva", [DIB(0.8)], estado={"curva": 0.3}))
S("ilustracion", "Abajo, a la derecha",
  el("int", "intestino", (960, 540), 1.3, "Abajo", [A, POSE("cuelga", resaltar=True)]),
  el("c", "circulo_rojo", (690, 870), 1.0, "cuelga", [DIB(0.4)], estado={"ancho": 170, "alto": 230}),
  T("t", "un gusanito", (1450, 880), "gusanito", 1.0, True), empujon=[("gusanito", (690, 870))])
S("ilustracion", "La profe lo señala",
  el("yo", "personaje", (640, 990), 1.15, "profe", [A], P("tablero")),
  T("t", "«no sirve para nada»", (1300, 400), "sirve", 0.9, True))
S("ilustracion", "Todos lo anotan",
  el("g", "gente", (960, 900), 1.0, "Todos"),
  el("doc", "documento", (1500, 450), 0.8, "anotan"))
S("ilustracion", "Nadie pregunta",
  el("yo", "personaje", (960, 990), 1.2, "Nadie", [A], P("pensando")),
  T("t", "¿por qué está ahí?", (1450, 300), "ahí", 0.9, True))
S("ilustracion", "Lo has oído",
  el("yo", "personaje", (960, 990), 1.2, "oído", [A], P("hombros")),
  T("t", "toda la vida", (1450, 300), "vida", 1.0))
bautizo("Eso es el apéndice", "el apéndice", "APÉNDICE", "famoso por no servir", "apéndice", "servir", "apéndice")
S("codigo", "Siempre se dijo",
  el("int", "intestino", (960, 540), 1.2, "intestino", [A, {"tipo": "crecer", "hasta": 1.15, "palabra": "grande", "duracion": 0.5}]),
  T("t", "«un resto»", (960, 90), "resto", 0.9))
S("codigo", "Uno que servía",
  el("rama", "rama", (960, 450), 1.0, "plantas"),
  T("t", "digerir plantas", (960, 800), "plantas", 1.0, True))
S("codigo", "Pero hoy hay",
  el("yo", "personaje", (960, 990), 1.2, "Pero", [A], P("idea")),
  T("t", "una propuesta distinta", (960, 200), "distinta", 1.0, True), empujon=[("distinta", (960, 300))])
S("codigo", "La hipótesis principal es que podría",
  T("t", "hipótesis principal", (960, 90), "principal", 0.8),
  el("casa", "casa", (760, 560), 1.1, "refugio"),
  el("bac", "bacterias", (1300, 560), 1.3, "bacterias", [DESDE(1800, 560)]),
  T("t2", "refugio", (760, 880), "refugio", 1.0, True))
S("codigo", "Si una infección fuerte",
  el("int", "intestino", (960, 540), 1.2, "infección", [A, TEMB("vacía", 12)]),
  el("bac", "bacterias", (690, 880), 0.6, "salvo", estado={}),
  T("t", "a salvo", (1450, 880), "salvo", 1.0, True))
S("codigo", "Y después podrían",
  el("int", "intestino", (960, 540), 1.2, "después", [A, POSE("poblarlo", bacterias=True)], estado={"resaltar": True}),
  el("f", "flecha", (960, 300), 1.0, "volver", [DIB(0.5)], rotacion=-30, estado={"curva": 0.3}),
  T("t", "repoblar", (1450, 880), "poblarlo", 1.0, True))
S("codigo", "Todavía es una hipótesis",
  el("yo", "personaje", (600, 990), 1.2, "Todavía", [A], P("pensando")),
  T("t", "hipótesis", (1450, 300), "hipótesis", 1.1, True),
  T("t2", "no un hecho cerrado", (1450, 500), "cerrado", 0.8))
S("personaje", "La parte más famosa",
  el("yo", "personaje", (640, 990), 1.15, "parte", [A], P("sorprendido")),
  el("int", "intestino", (1330, 520), 0.8, "famosa", estado={"resaltar": True}),
  T("t", "quizá sí sirve", (1330, 880), "sirve", 1.0, True), empujon=[("sirve", (1330, 600))])
S("personaje", "Quizá solo estaba",
  ya("yo", "personaje", (640, 990), 1.15, P("sorprendido"), [POSE("guardando", **P("senalando_contento"))]),
  el("bac", "bacterias", (1330, 520), 1.2, "guardando"),
  T("t", "guardando algo", (1330, 820), "algo", 1.0, True))

# ------------------------------------------------------------------ cierre del video (5 s)
S("personaje", "Y ahora ya sabes",
  el("yo", "personaje", (640, 990), 1.15, "ahora", [A], P("senalando_contento")),
  T("t", "ya sabes un poco más", (1330, 300), "sabes", 0.9),
  el("r", "rotulo", (1330, 560), 1.2, "suscríbete", estado={"texto": "SUSCRÍBETE", "color": "rojo"}),
  empujon=[("suscríbete", (1330, 560))])


def armar() -> dict:
    tema1 = json.loads((EJEMPLOS / "tema1_muneca.json").read_text(encoding="utf-8"))["escenas"]
    tema1[0] = cuadricula(TEMAS, 0, "Músculo", "muñeca", "Músculo de la muñeca", "MUÑECA")
    escenas = tema1 + ESCENAS
    for i, e in enumerate(escenas, 1):
        e["id"] = i
    return {"video": {"ancho": 1920, "alto": 1080, "fps": 30, "guion": "partes_que_no_sirven.txt"}, "escenas": escenas}


if __name__ == "__main__":
    datos = armar()
    (EJEMPLOS / "partes_que_no_sirven.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(datos["escenas"]), "escenas")
