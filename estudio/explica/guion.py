"""Guion de El Calvo Explica: leer el formato de 5 partes y revisarlo contra las reglas del canal.

Formato (una frase por renglón; cada frase será una escena):

    NOMBRE
    Sacudida al dormirte.

    ESCENA
    Estás en la cama.
    ...
    BAUTIZO / EXPLICACIÓN / CIERRE

Varios temas van uno detrás de otro (empieza otro tema en cada NOMBRE).
"""
from __future__ import annotations

import re

from ..calma.escenas import normalizar
from . import canal as C

PARTES = ("nombre", "escena", "bautizo", "explicacion", "cierre")
_CABECERA = {"NOMBRE": "nombre", "ESCENA": "escena", "BAUTIZO": "bautizo", "EXPLICACION": "explicacion",
             "EXPLICACIÓN": "explicacion", "CIERRE": "cierre", "FINAL": "final", "CIERRE DEL VIDEO": "final"}

# fórmulas de hipótesis aceptadas en la explicación (pedido del dueño: variantes, no una frase fija)
FORMULAS = {
    "la explicación más aceptada": r"\bla explicaci[oó]n m[aá]s aceptada\b",
    "se cree que": r"\bse cree que\b",
    "lo más probable es que": r"\blo m[aá]s probable es que\b",
    "la hipótesis principal": r"\bla hip[oó]tesis principal\b",
    "se piensa que": r"\bse piensa que\b",
    "una de las ideas más aceptadas": r"\buna de las ideas m[aá]s aceptadas\b",
}
PROHIBIDAS = ["en este video", "quédate hasta el final", "quedate hasta el final", "sabías que", "sabias que",
              "hola a todos", "bienvenidos", "suscríbete", "vosotros", "primero,", "segundo,", "tercero,"]


def leer(texto: str) -> list[dict]:
    """Lista de temas: {"nombre": [...], "escena": [...], ...} con una frase por elemento."""
    temas: list[dict] = []
    actual, parte = None, None
    for renglon in texto.splitlines():
        r = renglon.strip()
        if not r:
            continue
        cab = _CABECERA.get(r.upper().rstrip(":"))
        if cab == "final":                         # el cierre de 5 s del video (va después del último tema)
            if actual is None:
                raise ValueError("FINAL va después de los temas")
            actual.setdefault("final", [])
            parte = "final"
            continue
        if cab:
            if cab == "nombre":
                actual = {p: [] for p in PARTES}
                temas.append(actual)
            parte = cab
            continue
        if actual is None or parte is None:
            raise ValueError(f"texto fuera de un tema: «{r[:60]}» (cada tema empieza con NOMBRE)")
        actual.setdefault(parte, []).append(r)
    return temas


def palabras(frases: list[str]) -> int:
    return sum(len([w for w in f.split() if normalizar(w)]) for f in frases)


def formula(tema: dict) -> str | None:
    texto = " ".join(tema["explicacion"]).lower()
    return next((k for k, patron in FORMULAS.items() if re.search(patron, texto)), None)


def revisar(temas: list[dict], preset: dict | None = None, video_completo: bool = False) -> list[str]:
    """Avisos (vacío = cumple). Revisa largo de cada parte, frases, números, prohibidas y fórmulas."""
    p = preset or C.cargar()
    rangos = p["palabras_por_parte"]
    avisos = []
    usos: dict[str, int] = {}
    for i, t in enumerate(temas, 1):
        nombre = " ".join(t["nombre"]) or f"tema {i}"
        for parte in PARTES:
            lo, hi = rangos[parte]
            n = palabras(t[parte])
            if not t[parte]:
                avisos.append(f"{nombre}: falta la parte {parte.upper()}")
            elif not lo <= n <= hi:
                avisos.append(f"{nombre}: {parte.upper()} tiene {n} palabras (debe tener {lo} a {hi})")
        total = sum(palabras(t[x]) for x in PARTES)
        lo, hi = p["palabras_tema"]
        if not lo <= total <= hi:
            avisos.append(f"{nombre}: el tema tiene {total} palabras (debe tener {lo} a {hi})")
        for parte in PARTES:
            for f in t[parte]:
                if palabras([f]) > p["max_palabras_frase"]:
                    avisos.append(f"{nombre}: frase de más de {p['max_palabras_frase']} palabras: «{f[:50]}…»")
                if re.search(r"\d", f):
                    avisos.append(f"{nombre}: número en cifras (van en palabras): «{f[:50]}»")
                bajo = f.lower()
                for mala in PROHIBIDAS:
                    if mala in bajo:
                        avisos.append(f"{nombre}: frase prohibida «{mala}»: «{f[:50]}»")
        if t["escena"] and not re.match(r"^(est[aá]s|vas|abres|te |tu |tienes|llegas|sientes|miras|junta)",
                                         t["escena"][0].lower()):
            avisos.append(f"{nombre}: la ESCENA debe ubicar al espectador («Estás en…», «Vas a…»)")
        if t["bautizo"] and not re.search(r"\b(eso|esto|ese|esa)\b.*\b(se llama|es)\b", " ".join(t["bautizo"]).lower()):
            avisos.append(f"{nombre}: el BAUTIZO debe decir «Eso se llama…» o «Eso es…»")
        f = formula(t)
        if not f:
            avisos.append(f"{nombre}: la EXPLICACIÓN debe presentar la idea como hipótesis («la explicación más "
                          "aceptada», «se cree que», «lo más probable es que»…)")
        else:
            usos[f] = usos.get(f, 0) + 1
    for f, n in usos.items():
        if n > p["max_misma_formula"]:
            avisos.append(f"la fórmula «{f}» se repite en {n} temas (máximo {p['max_misma_formula']})")
    if video_completo:
        lo, hi = p["temas"]
        if not lo <= len(temas) <= hi:
            avisos.append(f"el video tiene {len(temas)} temas (debe tener {lo} a {hi})")
    return avisos


def texto_para_voz(temas: list[dict]) -> str:
    """Lo que lee la voz: cada frase en orden (el nombre de cada tema, solo, abre el tema)."""
    return "\n".join(f for t in temas for parte in PARTES + ("final",) for f in t.get(parte, []))
