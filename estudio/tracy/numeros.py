"""Números escritos en palabras (español) para que la voz los lea bien.

MiniMax lee «1.500» o «25%» de formas raras; el guion Tracy se normaliza antes del TTS:
cifras, miles con punto, decimales con coma, porcentajes, dinero ($, USD, €) y ordinales
(1.º, 2ª). Todo lo que no es número se deja igual.
"""
from __future__ import annotations

import re

_UNIDADES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
             "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve",
             "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis",
             "veintisiete", "veintiocho", "veintinueve"]
_DECENAS = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
_CENTENAS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos",
             6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}
_ORDINALES = {1: "primer", 2: "segund", 3: "tercer", 4: "cuart", 5: "quint", 6: "sext", 7: "séptim",
              8: "octav", 9: "noven", 10: "décim"}
# sustantivos terminados en -a que son masculinos («un día», no «una día»)
_MASCULINOS_EN_A = {"día", "días", "problema", "problemas", "programa", "programas", "sistema", "sistemas",
                    "tema", "temas", "mapa", "mapas", "clima", "idioma", "idiomas", "planeta", "planetas",
                    "dilema", "dilemas", "esquema", "esquemas", "poema", "poemas", "método", "sofá", "atleta",
                    "atletas", "millonarios", "millonario"}


def _menor_de_mil(n: int) -> str:
    if n < 30:
        return _UNIDADES[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DECENAS[d] + (f" y {_UNIDADES[u]}" if u else "")
    if n == 100:
        return "cien"
    c, resto = divmod(n, 100)
    return _CENTENAS[c] + (f" {_menor_de_mil(resto)}" if resto else "")


def a_palabras(n: int) -> str:
    """Entero a palabras: 1500 → «mil quinientos», 2_000_000 → «dos millones»."""
    if n < 0:
        return "menos " + a_palabras(-n)
    if n < 1000:
        return _menor_de_mil(n)
    if n < 1_000_000:
        miles, resto = divmod(n, 1000)
        cab = "mil" if miles == 1 else _apocope(_menor_de_mil(miles)) + " mil"
        return cab + (f" {_menor_de_mil(resto)}" if resto else "")
    if n < 1_000_000_000_000:
        millones, resto = divmod(n, 1_000_000)
        cab = "un millón" if millones == 1 else _apocope(a_palabras(millones)) + " millones"
        return cab + (f" {a_palabras(resto)}" if resto else "")
    billones, resto = divmod(n, 1_000_000_000_000)
    cab = "un billón" if billones == 1 else _apocope(a_palabras(billones)) + " billones"
    return cab + (f" {a_palabras(resto)}" if resto else "")


def _apocope(txt: str) -> str:
    """«uno» delante de un sustantivo o de mil/millones: veintiuno → veintiún, uno → un."""
    if txt.endswith("veintiuno"):
        return txt[:-len("veintiuno")] + "veintiún"
    if txt.endswith("uno"):
        return txt[:-3] + "un"
    return txt


def _femenino(txt: str) -> str:
    """«una», «veintiuna», «doscientas» delante de sustantivo femenino (solo la última parte)."""
    txt = re.sub(r"(uno|veintiún|veintiuno)$", lambda m: {"uno": "una"}.get(m.group(1), "veintiuna"), txt)
    txt = re.sub(r"\bun$", "una", txt)
    # los cientos concuerdan con el sustantivo, salvo los que cuentan millones o billones
    corte = max((m.end() for m in re.finditer(r"\b(millón|millones|billón|billones)\b", txt)), default=0)
    return txt[:corte] + re.sub(r"ientos\b", "ientas", txt[corte:])


_NO_SUSTANTIVOS = {"de", "del", "a", "al", "y", "e", "o", "u", "en", "por", "para", "con", "sin", "que", "más",
                   "menos", "la", "las", "el", "los", "lo", "un", "una", "su", "sus", "mi", "mis", "tu", "tus",
                   "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "es", "son", "fue", "era",
                   "hasta", "desde", "entre", "sobre", "como", "cuando", "donde", "se", "me", "te", "nos", "le",
                   "les", "ya", "no", "si", "sí", "muy", "casi", "solo", "mil", "millones", "millón"}


def _genero(siguiente: str) -> str:
    """'f' si la palabra que sigue parece femenina, 'm' si masculina, '' si no hay sustantivo."""
    s = siguiente.lower()
    if not s or not s[0].isalpha() or s in _NO_SUSTANTIVOS:
        return ""
    if s in ("vez", "veces"):
        return "f"
    if s in _MASCULINOS_EN_A:
        return "m"
    if s.endswith(("a", "as", "ión", "iones", "dad", "dades")):
        return "f"
    return "m"


_NUMERO = re.compile(
    r"(?:(?P<moneda>US\$|\$|€)\s?)?"
    r"(?P<num>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)"
    r"(?P<ordinal>\.?[ºª°]|(?:er|ro|ra|do|da|to|ta|vo|va|no|na)\b)?"
    r"(?P<pct>\s?%)?"
)


def _cardinal(entero: int, genero: str) -> str:
    txt = a_palabras(entero)
    if genero == "f":
        return _femenino(txt)
    if genero == "m":
        return _apocope(txt)
    return txt


def _decimal(texto: str, genero: str) -> str:
    sep = "," if "," in texto else "."
    ent, dec = texto.split(sep)
    parte_dec = " ".join(a_palabras(int(d)) for d in dec) if dec.startswith("0") else a_palabras(int(dec))
    return f"{_cardinal(int(ent), '')} {'coma' if sep == ',' else 'punto'} {parte_dec}"


def _reemplazar(m: re.Match, texto: str) -> str:
    num = m.group("num")
    resto = texto[m.end():]
    siguiente = re.match(r"\s*([^\s.,;:!?]+)", resto)
    sig = siguiente.group(1) if siguiente else ""
    if m.group("ordinal"):
        marca = m.group("ordinal").strip().lstrip(".")
        n = int(num.replace(".", "")) if "," not in num else None
        if n is not None and n in _ORDINALES:
            fem = marca in ("ª", "ra", "da", "ta", "va", "na")
            base = _ORDINALES[n]
            if fem:
                base = {"primer": "primera", "tercer": "tercera"}.get(base, base + "a")
            elif base not in ("primer", "tercer") or not sig or not sig[0].isalpha():
                base = {"primer": "primero", "tercer": "tercero"}.get(base, base + "o")
            return (m.group("moneda") or "") + base
        return m.group(0)                       # «11º» y similares: se dejan (rarísimos en guion)
    es_miles = re.fullmatch(r"\d{1,3}(?:\.\d{3})+", num) is not None
    if m.group("pct"):
        genero = ""
    elif m.group("moneda"):
        genero = "m"
    else:
        genero = _genero(sig)
    if es_miles:
        palabras = _cardinal(int(num.replace(".", "")), genero)
    elif "," in num or "." in num:
        num_limpio = num.replace(".", "") if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d+", num) else num
        palabras = _decimal(num_limpio, genero)
    else:
        palabras = _cardinal(int(num), genero)
    if m.group("pct"):
        palabras += " por ciento"
    moneda = m.group("moneda")
    if moneda:
        nombre = "euros" if moneda == "€" else "dólares"
        if palabras == "un":
            nombre = "euro" if moneda == "€" else "dólar"
        if palabras.endswith(("millón", "millones", "billón", "billones")):
            nombre = "de " + nombre
        palabras += " " + nombre
    return palabras


def numeros_a_palabras(texto: str) -> str:
    """Reemplaza todas las cifras del texto por palabras."""
    salida, ultimo = [], 0
    for m in _NUMERO.finditer(texto):
        # no tocar números pegados a letras (p. ej. «MP3», «B2B»)
        if m.start() > 0 and texto[m.start() - 1].isalpha() and not m.group("moneda"):
            continue
        salida.append(texto[ultimo:m.start()])
        salida.append(_reemplazar(m, texto))
        ultimo = m.end()
    salida.append(texto[ultimo:])
    out = "".join(salida)
    return re.sub(r"\bUSD\b", "dólares", out)
