"""Fase 4 (preparada, sin enganchar todavía): dónde va cada plantilla animada en un video de Peligro Tropical.

Entra lo mismo que la capa de audio: las frases del guion con su sección/intención y sus tiempos en la voz (y, si hay,
las palabras de Whisper). Sale la lista de clips a renderizar con Remotion, cada uno con su segundo exacto en el video
y las claves (segundos dentro del clip) de las palabras a las que reacciona:
  INTRO al empezar (30-60 s), un ENCUENTRO por animal (5-10 s, desde «Imagina que…»), TRANSICIÓN entre capítulos
  (3-5 s) y CIERRE al final (10-15 s). Meta: ~3-4 min animados en un video de 12-15 min.
El escenario y la luz salen de las palabras del guion (casa / río / selva / finca; noche / amanecer / día).
"""
from __future__ import annotations

import re

from .audio.capa import MORDIDA, _norm, palabras_estimadas

ESCENARIOS = [("casa", r"\b(casa|cocina|cuarto|bano|cama|sala|zapato|ropa|techo)"),
              ("rio", r"\b(rio|quebrada|agua|orilla|cienaga|laguna|pantano|nadar)"),
              ("selva", r"\b(selva|monte|bosque|amazon|arbol|hojarasca|tronco)"),
              ("finca", r"\b(finca|potrero|campo|cafetal|pasto|cultivo|trocha|camino)")]
LUCES = [("noche", r"\b(noche|oscur|madrugada oscura|linterna)"), ("amanecer", r"\b(amanecer|madrugada|alba)")]
ANIMAL = r"\b(serpiente|culebra|vibora|mapana|equis|aran|alacran|escorpi|rana|sapo|avispa|abeja|hormiga|oruga|gusano|cienpies|ciempies|murcielago|caiman|cocodrilo|pez|raya|tiburon|zancud|mosquit|garrapata|chinche|tarantula|anaconda|boa|jaguar|puma)"


def _buscar(palabras, patron, desde, hasta):
    for p in palabras:
        if desde <= p["ini"] < hasta and re.match(patron, _norm(p["w"])):
            return p["ini"]
    return None


def _lugar_y_luz(texto: str) -> tuple[str, str]:
    t = _norm(texto)
    escenario = next((n for n, pat in ESCENARIOS if re.search(pat, t)), "finca")
    luz = next((n for n, pat in LUCES if re.search(pat, t)), "dia")
    return escenario, luz


def _capitulos(frases):
    """grupos de frases por sección (en orden): [(seccion, [frases])]"""
    caps = []
    for f in frases:
        if caps and caps[-1][0] == f.get("seccion"):
            caps[-1][1].append(f)
        else:
            caps.append((f.get("seccion"), [f]))
    return caps


def planear(frases: list[dict], palabras: list[dict] | None = None, duracion: float | None = None) -> list[dict]:
    palabras = palabras or palabras_estimadas(frases)
    dur = duracion or frases[-1]["fin"]
    caps = _capitulos(frases)
    clips: list[dict] = []
    rel = lambda t, a: round(max(0.0, t - a), 2)
    # INTRO: el gancho (mín. 30 s si el video da, máx. 60)
    g_fin = caps[0][1][-1]["fin"]
    i_fin = min(60.0, max(g_fin, min(30.0, dur * 0.25)))
    esc, luz = _lugar_y_luz(" ".join(f["texto"] for f in frases if f["ini"] < i_fin))
    primera = frases[0]["fin"]
    claves = {"fin": round(i_fin, 2), "gancho_fin": round(primera, 2)}
    for nombre, patron, frac in (("botas", r"(bota|pisa|camin|paso)", 0.45), ("revela", ANIMAL, 0.64), ("susto", MORDIDA, 0.8)):
        t = _buscar(palabras, patron, primera, i_fin)
        claves[nombre] = round(t if t is not None else i_fin * frac, 2)
    claves["revela"] = max(claves["revela"], claves["botas"] + 1.0)
    claves["susto"] = max(claves["susto"], claves["revela"] + 1.0)
    clips.append({"plantilla": "intro", "inicio": 0.0, "fin": round(i_fin, 2), "escenario": esc, "luz": luz, "claves": claves})
    # un ENCUENTRO por capítulo de animal + TRANSICIÓN entre capítulos
    cuerpo = [c for c in caps[1:] if not (c[0] or "").lower().startswith(("cierre", "final"))]
    for k, (sec, fr) in enumerate(cuerpo):
        a0, a1 = fr[0]["ini"], fr[-1]["fin"]
        if a0 < i_fin:
            continue
        imagina = next((f for f in fr if _norm(f["texto"]).startswith("imagina")), fr[min(1, len(fr) - 1)])
        e0 = max(imagina["ini"], clips[-1]["fin"])     # nunca encima del clip anterior
        e1 = min(a1, e0 + 10.0)
        if e1 - e0 >= 5.0:
            esc, luz = _lugar_y_luz(" ".join(f["texto"] for f in fr))
            ap = _buscar(palabras, ANIMAL, e0, e1)
            mu = _buscar(palabras, MORDIDA, e0, e1)
            cl = {"fin": round(e1 - e0, 2), "aparece": rel(ap if ap is not None else e0 + 2.0, e0)}
            cl["reaccion"] = round(min(cl["fin"] - 1.0, cl["aparece"] + 1.6), 2)
            cl["muerde"] = rel(mu, e0) if mu is not None else round(min(cl["fin"] - 0.5, cl["reaccion"] + 2.0), 2)
            clips.append({"plantilla": "encuentro", "inicio": round(e0, 2), "fin": round(e1, 2), "escenario": esc, "luz": luz,
                          "claves": cl, "capitulo": sec})
        if k + 1 < len(cuerpo):                       # transición en el borde con el siguiente capítulo
            sig = cuerpo[k + 1][1][0]["ini"]
            t0 = max(a1 - 2.0, (clips[-1]["fin"] if clips else 0))
            t1 = min(t0 + 4.0, sig + 2.0)
            if t1 - t0 >= 3.0:
                esc2, luz2 = _lugar_y_luz(" ".join(f["texto"] for f in cuerpo[k + 1][1]))
                clips.append({"plantilla": "transicion", "inicio": round(t0, 2), "fin": round(t1, 2), "escenario": esc2, "luz": luz2,
                              "claves": {"fin": round(t1 - t0, 2)}, "nivel": min(10, 3 + k)})
    # CIERRE: los últimos 10-15 s
    c1 = dur
    c0 = max(clips[-1]["fin"], c1 - 13.0)
    if c1 - c0 >= 8.0:
        texto_final = " ".join(f["texto"] for f in frases if f["fin"] > c0)
        esc, luz = _lugar_y_luz(texto_final)
        com = _buscar(palabras, r"(coment|escrib|cuent)", c0, c1)
        cl = {"fin": round(c1 - c0, 2), "remate": 1.0}
        cl["comenta"] = rel(com, c0) if com is not None else round((c1 - c0) * 0.55, 2)
        clips.append({"plantilla": "cierre", "inicio": round(c0, 2), "fin": round(c1, 2), "escenario": esc, "luz": luz, "claves": cl})
    return clips


def minutos_animados(clips: list[dict]) -> float:
    return round(sum(c["fin"] - c["inicio"] for c in clips) / 60, 2)
