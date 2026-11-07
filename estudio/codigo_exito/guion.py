"""Guion etiquetado de Código del Éxito → bloques.

Cada párrafo empieza con su etiqueta en una línea propia (o al inicio del párrafo):
  [PROFESOR]                       escena animada del Profesor (gancho, inicio de cada regla, CTAs)
  [STOCK: palabras clave en inglés] clips de Pexels
  [AURA]                           fondo con visualizador del audio (pasajes reflexivos, afirmaciones, rituales)
Un texto sin etiqueta sigue con la etiqueta del párrafo anterior. Cada [PROFESOR] abre una PARTE nueva (la unidad de
render: si algo falla se repite solo esa parte).
"""
from __future__ import annotations

import re

# (07-11) también la forma del dueño: «[ 🎬 STOCK: "woman ..." / "woman ..." | TEXTO: "..."]» y notas de dirección en
# PROFESOR/AURA («[🎬 PROFESOR: dedo en la sien]»): la voz nunca las lee
ETIQUETA = re.compile(r"^\s*\[\s*[^\w\[\]]*\s*(PROFESOR|AURA|STOCK)\b\s*(?::\s*([^\]]*))?\]\s*", re.I)
COMILLAS = re.compile(r"[\"“”«]([^\"“”«»]+)[\"“”»]")


def _detalle(tipo: str, resto: str | None) -> tuple[list[str], str | None, str | None]:
    """(palabras clave de Pexels, nota de dirección, texto en pantalla) de lo que va después de «ETIQUETA:»"""
    partes = [x.strip() for x in (resto or "").split("|")]
    principal, texto_pantalla = partes[0], None
    for x in partes[1:]:
        m = re.match(r"(?i)texto[^:]*:\s*(.*)", x)
        if m:
            q = COMILLAS.findall(m.group(1))
            texto_pantalla = (q[0] if q else m.group(1)).strip() or None
    if tipo == "stock":
        q = COMILLAS.findall(principal)
        claves = q if q else re.split(r"[,/]", principal)
        return [k.strip(" \"'“”«»") for k in claves if k.strip(" \"'“”«»")][:4], None, texto_pantalla
    return [], principal or None, texto_pantalla


def leer(texto: str) -> list[dict]:
    bloques: list[dict] = []
    actual: dict | None = None
    for parrafo in re.split(r"\n\s*\n", texto.strip()):
        p = parrafo.strip()
        if not p:
            continue
        m = ETIQUETA.match(p)
        if m:
            tipo = m.group(1).lower()
            claves, nota, en_pantalla = _detalle(tipo, m.group(2))
            cuerpo = " ".join(p[m.end():].split())
            actual = {"tipo": tipo, "claves": claves, "texto": cuerpo}
            if nota:
                actual["nota"] = nota
            if en_pantalla:
                actual["texto_pantalla"] = en_pantalla
            bloques.append(actual)
        elif actual is None:
            actual = {"tipo": "profesor", "claves": [], "texto": " ".join(p.split())}
            bloques.append(actual)
        else:
            actual["texto"] = (actual["texto"] + " " + " ".join(p.split())).strip()
    bloques = [b for b in bloques if b["texto"]]
    partidos = []                                      # ningún bloque demasiado largo para la voz (MiniMax) ni para el ritmo
    for b in bloques:
        partidos += [{**b, "texto": t} for t in _partir(b["texto"])]
    bloques = partidos
    parte = 0
    for k, b in enumerate(bloques):
        if b["tipo"] == "profesor" and k > 0:
            parte += 1
        b["id"] = k + 1
        b["parte"] = parte
        if b["tipo"] == "stock" and not b["claves"]:
            raise ValueError(f"el bloque {k + 1} es [STOCK] pero no trae palabras clave")
    if not bloques:
        raise ValueError("el guion no tiene bloques")
    return bloques


# ---------------------------------------------------------------------------- guion SIN etiquetas (07-11)
# El dueño pegó un guion de 37 min sin etiquetas → un solo bloque → MiniMax «text too long». Ahora Xandart lo etiqueta
# solo (Claude liviano, gratis por la suscripción; sin Claude, por reglas) y ningún bloque pasa de MAX_LETRAS.
MAX_LETRAS = 1400
STOCK_GENERAL = ["woman walking city sunrise", "person writing in journal", "coffee morning window light",
                 "woman thinking by window", "city lights at night", "walking path in forest", "hands working on laptop",
                 "sunset over mountains", "person climbing stairs", "calm ocean waves"]


def tiene_etiquetas(texto: str) -> bool:
    return any(ETIQUETA.match(p.strip()) for p in re.split(r"\n\s*\n|\n(?=\s*\[)", texto) if p.strip())


def _parrafos(texto: str) -> list[str]:
    ps = [" ".join(p.split()) for p in re.split(r"\n\s*\n|\n", texto) if p.strip()]
    return [p for p in ps if p]


def _partir(texto: str, maximo: int = MAX_LETRAS) -> list[str]:
    """texto largo → trozos de ≤ maximo letras, siempre en un final de oración"""
    if len(texto) <= maximo:
        return [texto]
    oraciones = re.split(r"(?<=[.!?…])\s+", texto)
    trozos, actual = [], ""
    for o in oraciones:
        if actual and len(actual) + len(o) + 1 > maximo:
            trozos.append(actual); actual = o
        else:
            actual = (actual + " " + o).strip()
    if actual:
        trozos.append(actual)
    salida = []
    for t in trozos:                                   # una «oración» gigante sin puntos: se corta por comas/espacios
        while len(t) > maximo:
            corte = t.rfind(",", 0, maximo)
            corte = corte if corte > maximo // 2 else t.rfind(" ", 0, maximo)
            salida.append(t[:corte + 1].strip()); t = t[corte + 1:].strip()
        salida.append(t)
    return [s for s in salida if s]


PROFE = re.compile(r"^\s*((decisi[oó]n|regla|paso|clave|h[aá]bito|lecci[oó]n|secreto|principio)\s+(n[uú]mero\s+)?\w+|\d+\s*[.)-])", re.I)
AURA = re.compile(r"(cierra los ojos|respira|repite conmigo|imagina que|siente c[oó]mo|di en voz alta|afirmaci[oó]n)", re.I)
CTA = re.compile(r"(suscr[ií]bete|comenta|d[eé]jame en los comentarios|activa la campana|dale like|me gusta)", re.I)


def etiquetar_por_reglas(texto: str) -> list[dict]:
    """sin Claude: gancho y cada «Decisión/Regla número…» y los llamados → Profesor; ejercicios de respiración o
    afirmaciones → aura; lo demás → stock con palabras generales (se turnan para no repetir)"""
    bloques, k = [], 0
    ps = _parrafos(texto)
    for i, p in enumerate(ps):
        if i == 0 or PROFE.match(p) or (CTA.search(p) and i >= len(ps) - 3):
            tipo, claves = "profesor", []
        elif AURA.search(p):
            tipo, claves = "aura", []
        else:
            tipo, claves = "stock", [STOCK_GENERAL[k % len(STOCK_GENERAL)], STOCK_GENERAL[(k + 3) % len(STOCK_GENERAL)]]
            k += 1
        if bloques and bloques[-1]["tipo"] == tipo and tipo != "profesor" and len(bloques[-1]["texto"]) + len(p) < MAX_LETRAS:
            bloques[-1]["texto"] += " " + p
        else:
            bloques.append({"tipo": tipo, "claves": claves, "texto": p})
    return bloques


def _como_texto(bloques: list[dict]) -> str:
    salida = []
    for b in bloques:
        cab = f"[STOCK: {', '.join(b['claves'])}]" if b["tipo"] == "stock" else f"[{b['tipo'].upper()}]"
        salida.append(cab + "\n" + b["texto"])
    return "\n\n".join(salida) + "\n"


def _palabras(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower())


def etiquetar(texto: str, ejecutar=None, avisar=print) -> str:
    """Devuelve el guion con etiquetas. Claude solo PONE etiquetas y palabras clave: si cambia una palabra del texto,
    se descarta y se usan las reglas."""
    if tiene_etiquetas(texto):
        return texto
    ps = _parrafos(texto)
    try:
        from .. import claude_cli

        lista = "\n".join(f"{i}. {p}" for i, p in enumerate(ps))
        prompt = ("Eres el editor de un canal de YouTube de desarrollo personal. Este guion se va a hacer con 3 tipos de "
                  "bloque: PROFESOR (personaje animado: el gancho del inicio, el inicio de cada regla/decisión/paso y los "
                  "llamados a suscribirse o comentar), STOCK (videos de Pexels; da 2-3 palabras clave EN INGLÉS de lo que se "
                  "ve, concretas: «woman writing in journal», no «success») y AURA (pasajes de reflexión, respiración, "
                  "afirmaciones o rituales). Asigna un tipo a CADA párrafo numerado; párrafos seguidos del mismo tipo "
                  "pueden ir juntos. NO cambies ni resumas el texto.\n\nPÁRRAFOS:\n" + lista +
                  '\n\nResponde SOLO JSON: [{"desde": n, "hasta": n, "tipo": "profesor"|"stock"|"aura", "claves": ["…"]}] '
                  "cubriendo todos los párrafos en orden.")
        avisar("Claude está poniendo las etiquetas al guion…")
        respuesta, _ = (ejecutar or claude_cli.revisor)(prompt)
        datos = claude_cli.extraer_json(respuesta)
        bloques, siguiente = [], 0
        for d in datos:
            a, z, tipo = int(d["desde"]), int(d["hasta"]), str(d["tipo"]).lower()
            assert a == siguiente and z >= a and tipo in ("profesor", "stock", "aura")
            claves = [str(c).strip() for c in (d.get("claves") or []) if str(c).strip()][:3]
            if tipo == "stock" and not claves:
                claves = [STOCK_GENERAL[len(bloques) % len(STOCK_GENERAL)]]
            bloques.append({"tipo": tipo, "claves": claves, "texto": " ".join(ps[a:z + 1])})
            siguiente = z + 1
        assert siguiente == len(ps) and _palabras(" ".join(b["texto"] for b in bloques)) == _palabras(" ".join(ps))
    except Exception as ex:  # noqa: BLE001 — sin Claude (o respuesta rara): por reglas
        avisar(f"  etiquetas por reglas ({str(ex)[:100]})")
        bloques = etiquetar_por_reglas(texto)
    return _como_texto(profesor_corto(bloques))


PROFESOR_MAX = 600


def profesor_corto(bloques: list[dict]) -> list[dict]:
    """un bloque del Profesor largo (una regla entera) deja al Profesor solo al inicio (≈2-3 oraciones) y el resto
    pasa a stock: el video no se queda minutos con las mismas escenas animadas"""
    salida, k = [], 0
    for b in bloques:
        if b["tipo"] != "profesor" or len(b["texto"]) <= PROFESOR_MAX:
            salida.append(b)
            continue
        oraciones = re.split(r"(?<=[.!?…])\s+", b["texto"])
        cabeza, i = "", 0
        while i < len(oraciones) and (not cabeza or len(cabeza) + len(oraciones[i]) < 380):
            cabeza = (cabeza + " " + oraciones[i]).strip(); i += 1
        salida.append({**b, "texto": cabeza})
        resto = " ".join(oraciones[i:]).strip()
        if resto:
            salida.append({"tipo": "stock", "claves": [STOCK_GENERAL[k % len(STOCK_GENERAL)], STOCK_GENERAL[(k + 5) % len(STOCK_GENERAL)]], "texto": resto})
            k += 1
    return salida
