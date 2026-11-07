"""Peligro Tropical v4 (07-11, aprobado por el dueño tras analizar la skill que mandó; técnicas, no copias):

1. Estilo que ROTA entre videos: la escala de niveles (horizontal = la tira de siempre, vertical, cartas) y el letrero
   del animal (etiqueta = el de siempre, color, tarjeta). Nunca la misma combinación de los últimos 3 videos
   (historial en datos/pt_estilos.json; el elegido queda en <proyecto>/estilo_video.json y no cambia al rehacer).
2. Recursos nuevos, por código y sin costo: pantalla dividida VS cuando la voz compara, la silueta negra del último con
   «?» en el gancho, globos de pensamiento con las preguntas cortas, pantalla negra justo antes de una revelación en los
   niveles altos, glitch en el dato más fuerte del último animal e íconos (X, corona, pulgar abajo, alerta).

Se activa con `recursos_v4: true` en el perfil (perfiles/peligro_tropical_v4.json, que usa la fórmula escala_peligro_v3).
Lo dibuja render_v4.py.
"""
from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

ESCALAS = ("horizontal", "vertical", "cartas")
LETREROS = ("etiqueta", "color", "tarjeta")
RECORDAR = 3

MAX_VS, CADA_VS_S = 3, 45.0
MAX_NEGRO, CADA_NEGRO_S = 3, 50.0
MAX_GLOBOS, CADA_GLOBO_S = 6, 25.0
CADA_ICONO_S = 9.0
MAX_ICONOS = 14

COMPARA = re.compile(r"\b(mas|menos) (grande|grandes|pesad\w*|larg\w*|rapid\w*|fuerte\w*|peligros\w*|venenos\w*|"
                     r"letal\w*|agresiv\w*|chiquit\w*|pequen\w*) que\b|\bcomparad\w* con\b|\ba diferencia de\b|"
                     r"\bal lado de\b|\bcontra (el|la|los|las)\b|\bmucho peor que\b")
MISTERIO = re.compile(r"\b(ultimo|al final|de la lista|lo dejo para|te lo cuento|ni en suenos|muy lejos)\b")
ICONOS = (
    ("x", re.compile(r"\b(mito|falso|no es cierto|no es verdad|en realidad no|nada de eso|error|mentira)\b")),
    ("corona", re.compile(r"\b(rey|reina|campeon\w*|record|el mas grande|la mas grande|el numero uno)\b")),
    ("pulgar_abajo", re.compile(r"\b(peor|terrible|pesim\w*|no lo hagas|mala idea|asco|asqueros\w*|horrible)\b")),
    ("alerta", re.compile(r"\b(cuidado|alerta|veneno|venenos\w*|toxic\w*|mortal|letal|peligro)\b")),
)
OCUPADO = ("veredicto", "pero_espera", "cta_like", "cta_suscribir", "comentario", "final_personaje", "dato",
           "etiqueta", "escala_peligro", "presentacion_especie", "palabra_completa", "capitulo", "mapa_antiguo",
           "vs", "silueta", "video_real", "foto_real", "animacion")


def _plano(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _libre(c: dict) -> bool:
    from .receta_pt import _libre as libre

    return libre(c)


def _ocupado(c: dict, extra: tuple = ()) -> bool:
    return any(x["efecto"] in OCUPADO + extra for x in c["efectos"])


# ------------------------------------------------------------------ 1. estilo que rota entre videos

def _historial() -> Path:
    from .plataforma.db import carpeta_datos

    return carpeta_datos() / "pt_estilos.json"


def elegir_estilo(raiz: Path, rng: random.Random) -> dict:
    """el estilo de ESTE video (se guarda: rehacer el video no lo cambia)"""
    propio = raiz / "estilo_video.json"
    if propio.exists():
        try:
            d = json.loads(propio.read_text("utf-8"))
            if d.get("escala") in ESCALAS and d.get("letrero") in LETREROS:
                return d
        except (OSError, ValueError):
            pass
    ruta = _historial()
    try:
        hist = json.loads(ruta.read_text("utf-8")) if ruta.exists() else []
    except (OSError, ValueError):
        hist = []
    recientes = [(h.get("escala"), h.get("letrero")) for h in hist[-RECORDAR:]]
    opciones = [(e, l) for e in ESCALAS for l in LETREROS if (e, l) not in recientes]
    # que cambie la escala Y el letrero respecto al video anterior, si se puede
    if recientes:
        e0, l0 = recientes[-1]
        mejores = [(e, l) for e, l in opciones if e != e0 and l != l0]
        opciones = mejores or opciones
    escala, letrero = rng.choice(opciones or [(ESCALAS[0], LETREROS[0])])
    d = {"escala": escala, "letrero": letrero}
    propio.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    hist.append({**d, "video": raiz.name})
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(hist[-30:], ensure_ascii=False, indent=1), "utf-8")
    except OSError:
        pass
    return d


# ------------------------------------------------------------------ aplicar

def aplicar(clips: list, escenas: list, sfx: list, sfx_fn, nivel: list, esc, raiz: Path, rng: random.Random) -> dict:
    estilo = elegir_estilo(raiz, rng)
    numeros = sorted(n.numero for n in esc.niveles)
    n_niv = len(numeros)
    ultimo = numeros[-1] if numeros else None
    nombres = {n.numero: n.nombre for n in esc.niveles}

    # --- escala y letrero de este video
    for c in clips:
        for x in c["efectos"]:
            if x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar") and estilo["escala"] != "horizontal":
                x["variante"] = estilo["escala"]
            elif x["efecto"] == "presentacion_especie":
                x["letrero"] = estilo["letrero"]
                x["total"] = n_niv

    primero_nivel = next((i for i, k in enumerate(nivel) if k), len(clips))      # el gancho es el nivel 0

    # --- silueta del último con «?» en el gancho (una vez)
    if ultimo is not None:
        candidatos = [i for i in range(primero_nivel) if _libre(clips[i]) and not _ocupado(clips[i])
                      and clips[i]["fin"] - clips[i]["inicio"] >= 1.6 and clips[i]["inicio"] >= 3.0]
        i = next((i for i in candidatos if MISTERIO.search(_plano(escenas[i].narracion))), None)
        if i is None and candidatos:
            i = candidatos[len(candidatos) // 2]
        if i is not None:
            c = clips[i]
            en = round(c["inicio"] + 0.05, 3)
            c["efectos"] = [x for x in c["efectos"] if x["efecto"] not in ("circulos_misterio", "signos_pregunta",
                                                                          "flechas_alrededor")]
            c["efectos"].append({"efecto": "silueta", "en": en, "dur": round(min(2.4, c["fin"] - en - 0.05), 3),
                                 "nivel": ultimo})
            sfx_fn(sfx, "latido", en + 0.3, i, "Latido: la silueta del último de la lista")

    # --- VS cuando la voz compara (el anterior contra el actual)
    hechos, ultima = 0, -99.0
    for i, (c, e) in enumerate(zip(clips, escenas)):
        k = nivel[i]
        if hechos >= MAX_VS or k is None or k <= numeros[0] or not _libre(c) or _ocupado(c):
            continue
        if c["fin"] - c["inicio"] < 1.8 or c["inicio"] - ultima < CADA_VS_S:
            continue
        if not COMPARA.search(_plano(e.narracion)):
            continue
        anterior = max(x for x in numeros if x < k)
        en = round(c["inicio"] + 0.1, 3)
        c["efectos"].append({"efecto": "vs", "en": en, "dur": round(min(2.6, c["fin"] - en - 0.05), 3),
                             "izq": anterior, "der": k, "nombres": [nombres.get(anterior), nombres.get(k)]})
        sfx_fn(sfx, "barrido", en, i, "Swoosh: pantalla dividida VS")
        sfx_fn(sfx, "golpe_grave", en + 0.3, i, "Golpe: salta el «VS»")
        hechos, ultima = hechos + 1, c["inicio"]

    # --- pantalla negra justo antes de una revelación (niveles altos)
    hechos, ultima = 0, -99.0
    for i in range(1, len(clips)):
        k = nivel[i]
        if hechos >= MAX_NEGRO or k is None or not n_niv or k <= n_niv / 2:
            continue
        if escenas[i].intencion not in ("revelacion", "giro", "dato_impactante"):
            continue
        p = clips[i - 1]
        if not _libre(p) or p["fin"] - p["inicio"] < 1.4 or p["inicio"] - ultima < CADA_NEGRO_S:
            continue
        if any(x["efecto"] in ("veredicto", "pero_espera", "cta_like", "cta_suscribir", "comentario")
               for x in p["efectos"]):
            continue
        en = round(p["fin"] - 0.45, 3)
        p["efectos"].append({"efecto": "negro", "en": en, "dur": 0.45})
        hechos, ultima = hechos + 1, p["inicio"]

    # --- glitch en el dato más fuerte del último animal (hasta 2)
    hechos = 0
    for i, (c, e) in enumerate(zip(clips, escenas)):
        if hechos >= 2 or nivel[i] != ultimo or not _libre(c) or any(
                x["efecto"] in ("negro", "vs", "cta_like", "cta_suscribir", "comentario", "final_personaje")
                for x in c["efectos"]):
            continue
        if e.intencion not in ("revelacion", "dato_impactante", "amenaza", "giro"):
            continue
        en = round(c["inicio"] + 0.08, 3)
        c["efectos"].append({"efecto": "glitch", "en": en, "dur": 0.42})
        sfx_fn(sfx, "glitch", en, i, "Glitch: el dato más fuerte del último")
        hechos += 1

    # --- globo de pensamiento con las preguntas cortas
    hechos, ultima = 0, -99.0
    for i, (c, e) in enumerate(zip(clips, escenas)):
        if hechos >= MAX_GLOBOS or not _libre(c) or _ocupado(c, ("palabra_golpe", "circulos_misterio", "glitch")):
            continue
        dur = c["fin"] - c["inicio"]
        if dur < 1.5 or c["inicio"] - ultima < CADA_GLOBO_S:
            continue
        m = re.search(r"¿([^?¿]{3,40})\?", e.narracion)
        if not m or len(m.group(1).split()) > 5:
            continue
        texto = "¿" + m.group(1).strip()[0].upper() + m.group(1).strip()[1:] + "?"
        en = round(c["inicio"] + 0.15, 3)
        c["efectos"].append({"efecto": "globo", "en": en, "dur": round(min(2.2, dur - 0.2), 3), "texto": texto,
                             "x": rng.choice((0.26, 0.74)), "y": 0.2})
        sfx_fn(sfx, "pop", en, i, f"Pop: globo de pensamiento «{texto}»")
        hechos, ultima = hechos + 1, c["inicio"]

    # --- íconos por lo que dice la voz
    hechos, ultima = 0, -99.0
    for i, (c, e) in enumerate(zip(clips, escenas)):
        if hechos >= MAX_ICONOS or nivel[i] is None or not _libre(c):
            continue
        if _ocupado(c, ("globo", "palabra_golpe", "glitch", "circulos_misterio", "flechas_alrededor")):
            continue
        dur = c["fin"] - c["inicio"]
        if dur < 1.2 or c["inicio"] - ultima < CADA_ICONO_S:
            continue
        texto = _plano(e.narracion)
        tipo = next((t for t, rx in ICONOS if rx.search(texto)), None)
        if not tipo:
            continue
        en = round(c["inicio"] + min(0.35, dur * 0.2), 3)
        lado = rng.choice((0.12, 0.88))
        c["efectos"].append({"efecto": "icono_v4", "tipo": tipo, "en": en, "dur": round(min(1.6, c["fin"] - en - 0.05), 3),
                             "x": lado, "y": 0.3, "giro": round(rng.uniform(-10, 10), 1)})
        sfx_fn(sfx, "pop", en, i, f"Pop: ícono «{tipo}»")
        hechos, ultima = hechos + 1, c["inicio"]
    return estilo
