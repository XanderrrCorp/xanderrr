"""(01-11) «Edición humana» del modo Tracy: que cada video se vea editado a mano y no hecho en serie.

Todo vive en el preset del canal Tracy (bloque `humano`, APAGADO por defecto): con el interruptor apagado el
video sale exactamente como siempre. Prendido:

1. Claude (modelo liviano, una sola lectura) marca cada oración con su papel (gancho, regla, frase fuerte,
   revelación, pregunta, CTA, producto, venta, cierre, reflexiva o normal), 2-3 palabras clave EN INGLÉS para el
   stock, la palabra que se resalta en amarillo y, en los momentos clave, un texto grande corto. Sin Claude, unas
   reglas sencillas hacen lo mismo de forma básica.
2. La voz: pausas de 0,4-0,8 s después de frases fuertes, revelaciones y preguntas, y el cierre un poco más lento
   (sobre el audio ya grabado: no se vuelve a pagar).
3. Los cortes: clips de 3 a 30 s que terminan siempre al final de una oración; rápidos en el gancho, las
   revelaciones y las frases fuertes, lentos en lo reflexivo.
4. El seminario (Fénix) solo en momentos de autoridad (inicio de cada regla, frases clave, CTA y cierre), sin
   patrón fijo y por debajo del máximo del preset (35 % por defecto).
5. Cada video sortea su huella (música por sección, estilo del texto grande, transiciones suaves y movimientos)
   y nunca repite la del video anterior del canal.
El montaje (movimiento, color cálido, textos, transiciones, sonidos, música por sección) lo hace ensamblar.py con
lo que queda anotado aquí en cada toma.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
import unicodedata
from pathlib import Path

from .. import claude_cli
from ..config import escribir_json, leer_config, leer_json
from ..proyecto import CarpetaProyecto

ROLES = ("gancho", "regla", "frase_fuerte", "revelacion", "pregunta", "cta", "producto", "venta", "cierre",
         "reflexiva", "normal")
FUERTES = {"frase_fuerte", "revelacion", "pregunta"}            # llevan pausa después
RAPIDOS = {"gancho", "frase_fuerte", "revelacion", "pregunta", "regla", "cta", "producto"}
LENTOS = {"reflexiva", "cierre"}
# las que empiezan un clip propio (no se pegan al final del clip anterior)
ABREN_CLIP = {"regla", "revelacion", "cta", "producto", "frase_fuerte"}
CON_TEXTO_GRANDE = {"regla", "cta", "producto"}
MOVIMIENTOS = ("acercar", "alejar", "paneo_izq", "paneo_der", "fijo")
ESTILOS_TEXTO = (1, 2, 3, 4)
POOLS_TRANSICION = (("fundido",), ("destello",), ("fundido", "destello"))

POR_DEFECTO = {
    "activo": False,               # el interruptor «Edición humana»
    "fenix_max": 0.35,             # máximo del tiempo con el seminario
    "clip_min_s": 3.0,
    "clip_max_s": 30.0,
    "gancho_s": 60.0,              # el gancho: cortes más rápidos
    "pausa_s": [0.4, 0.8],         # pausa natural después de frases fuertes y preguntas
    "velocidad_cierre": 0.94,      # el cierre emocional un poco más lento (1 = igual)
    "suaves": 0.15,                # parte de los cortes con fundido o destello (el resto, corte seco)
    "whoosh": 0.15,                # parte de los cortes secos con whoosh (los suaves siempre lo llevan)
    "riser": True,                 # sonido que sube antes de cada revelación
    "color_calido": True,          # el mismo tono cálido en todo el stock
    "escena_final_desde": 0.9,     # la escena fija solo en el cierre (1 = sin escena final)
    "carpeta_musica": "",          # pistas con licencia: gancho*.mp3, cuerpo*.mp3, venta*.mp3, cierre*.mp3
    "revisar_antes": True,         # se detiene para revisar antes de exportar
    "prueba_s": 180.0,             # «Probar 3 minutos»
}


def ajustes(preset: dict) -> dict:
    h = {**POR_DEFECTO, **(preset.get("humano") or {})}
    h["activo"] = bool(h["activo"])
    h["fenix_max"] = max(0.0, min(0.6, float(h["fenix_max"])))
    h["clip_min_s"] = max(2.0, min(10.0, float(h["clip_min_s"])))
    h["clip_max_s"] = max(h["clip_min_s"] + 2, min(30.0, float(h["clip_max_s"])))
    lo, hi = (float(x) for x in h["pausa_s"])
    h["pausa_s"] = [max(0.0, min(lo, hi)), max(0.0, min(1.5, max(lo, hi)))]
    h["velocidad_cierre"] = max(0.85, min(1.0, float(h["velocidad_cierre"])))
    h["suaves"] = max(0.0, min(0.5, float(h["suaves"])))
    h["whoosh"] = max(0.0, min(0.5, float(h["whoosh"])))
    h["escena_final_desde"] = max(0.05, min(1.0, float(h["escena_final_desde"])))
    return h


def activo(preset: dict) -> bool:
    return ajustes(preset)["activo"]


# ------------------------------------------------------------------ 1. marcas por oración

def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _instruccion(oraciones: list[dict]) -> str:
    lista = "\n".join(f'{o["id"]}: {o["texto"][:300]}' for o in oraciones)
    return (
        "Eres el editor de un video narrado de desarrollo personal en español (estilo seminario). Lee cada oración y "
        "márcala para la edición.\n"
        f"- \"rol\": uno de {', '.join(ROLES)}. gancho = lo que engancha al empezar; regla = la oración que ABRE una "
        "regla, un hábito o un paso numerado; frase_fuerte = una frase corta que pega (para citar); revelacion = un "
        "dato o giro que sorprende; pregunta = pregunta retórica al espectador; cta = pide comentar, suscribirse o "
        "dar like (incluida la frase de identidad que se pide escribir); producto = nombra el producto o curso que se "
        "vende; venta = explica la oferta; cierre = el cierre emocional del final; reflexiva = calmada, de "
        "reflexión; normal = lo demás.\n"
        "- \"keywords\": 2 o 3 búsquedas EN INGLÉS de lo que se puede FILMAR y muestra esa oración (si habla de "
        "ahorrar: 'piggy bank coins', 'saving money jar'; nunca ideas abstractas ni paisajes genéricos).\n"
        "- \"palabra\": la palabra MÁS fuerte de la oración, copiada EXACTA de la oración (solo en frase_fuerte, "
        "revelacion, regla, cta y producto; en las demás null).\n"
        "- \"grande\": SOLO en regla, cta y producto: un texto de 1 a 5 palabras para mostrar grande en pantalla "
        "(«REGLA 1: PAGA PRIMERO», «ESCRIBE: YO DECIDO», el nombre del producto). En las demás null.\n\n"
        f"Oraciones (id: texto):\n{lista}\n\n"
        'Responde SOLO un JSON: {"oraciones": [{"id": 0, "rol": "gancho", "keywords": ["...", "..."], '
        '"palabra": null, "grande": null}, ...]} con todos los ids en orden.'
    )


def _por_reglas(o: dict, gancho_s: float) -> dict:
    t = _norm(o["texto"])
    if o["inicio"] < gancho_s:
        rol = "gancho"
    elif re.search(r"\b(regla|habito|paso|leccion|ley)\b.{0,20}\b(numero|uno|dos|tres|cuatro|cinco|\d)", t) or \
            re.match(r"(primero|segundo|tercero|la primera|la segunda|la tercera)\b", t):
        rol = "regla"
    elif re.search(r"\b(comenta|comentarios|suscribete|like)\b", t):
        rol = "cta"
    elif o["texto"].strip().endswith("?"):
        rol = "pregunta"
    elif len(t.split()) <= 7 and o["texto"].strip().endswith(("!", ".")):
        rol = "frase_fuerte"
    else:
        rol = "normal"
    return {"rol": rol, "keywords": [], "palabra": None, "grande": None}


def _limpiar(item: dict, o: dict, gancho_s: float) -> dict:
    base = _por_reglas(o, gancho_s)
    rol = str(item.get("rol") or base["rol"]).strip().lower()
    rol = rol if rol in ROLES else base["rol"]
    kws = item.get("keywords") or []
    if isinstance(kws, str):
        kws = re.split(r"[,;]", kws)
    kws = [re.sub(r"\s+", " ", str(k)).strip()[:40] for k in kws if str(k).strip()][:3]
    palabra = str(item.get("palabra") or "").strip(" .,;:¡!¿?\"'«»")
    if not palabra or _norm(palabra) not in _norm(o["texto"]):
        palabra = None
    grande = str(item.get("grande") or "").strip()[:40] or None
    if rol not in CON_TEXTO_GRANDE:
        grande = None
    return {"rol": rol, "keywords": kws, "palabra": palabra, "grande": grande}


@claude_cli.en_paso("Tracy: marcar las oraciones")
def marcar(carpeta: CarpetaProyecto, oraciones: list[dict], h: dict, ejecutar=None, avisar=print) -> dict[int, dict]:
    """{id de oración: {rol, keywords, palabra, grande}} en `marcas_humano.json`. Si las oraciones no cambian, no se
    vuelve a preguntar."""
    ruta = carpeta.ruta / "marcas_humano.json"
    huella = hashlib.sha256(json.dumps([o["texto"] for o in oraciones], ensure_ascii=False).encode()).hexdigest()[:16]
    if ruta.exists():
        previo = leer_json(ruta)
        if previo.get("huella") == huella:
            return {int(k): v for k, v in previo["marcas"].items()}
    propuesto: dict[int, dict] = {}
    origen = "reglas"
    if ejecutar is None:
        modelo = (leer_config("proveedores.json").get("claude") or {}).get("modelo_revisor") or "sonnet"

        def ejecutar(prompt, cwd=None):
            return claude_cli.ejecutar(prompt, cwd=cwd, modelo=modelo, pensamiento=1500, tiempo_max_s=900)
    try:
        avisar("Claude está leyendo el guion para la edición (qué es gancho, regla, frase fuerte, venta…)…")
        texto, _ = ejecutar(_instruccion(oraciones), cwd=carpeta.ruta)
        for item in (claude_cli.extraer_json(texto) or {}).get("oraciones", []):
            try:
                propuesto[int(item.get("id"))] = item
            except (TypeError, ValueError):
                continue
        origen = "claude" if propuesto else "reglas"
    except Exception as ex:  # noqa: BLE001 — sin Claude, las reglas
        avisar(f"  Claude no pudo marcar el guion ({str(ex)[:120]}); uso las reglas")
    marcas = {o["id"]: _limpiar(propuesto.get(o["id"], {}), o, h["gancho_s"]) for o in oraciones}
    escribir_json(ruta, {"huella": huella, "origen": origen, "marcas": {str(k): v for k, v in marcas.items()}})
    return marcas


# ------------------------------------------------------------------ 2. la voz: pausas y cierre más lento

def retocar_audio(carpeta: CarpetaProyecto, marcas: dict[int, dict], h: dict, ffmpeg: str, avisar=print) -> dict:
    """Sobre `audio/voz.wav` y `audio/oraciones.json` recién hechos: guarda los originales y los reemplaza por la
    versión con pausas naturales y el cierre un poco más lento. Corre una vez por cada voz nueva."""
    import subprocess
    import tempfile

    import numpy as np

    from ..voz import SR
    from .audio import escribir_wav, leer_wav

    dir_a = carpeta.ruta / "audio"
    datos = leer_json(dir_a / "oraciones.json")
    audio = leer_wav(dir_a / "voz.wav")
    escribir_wav(dir_a / "voz_original.wav", audio)
    escribir_json(dir_a / "oraciones_original.json", datos)
    ors = datos["oraciones"]
    rng = random.Random(f"{carpeta.ruta.name}|pausas")
    lo, hi = h["pausa_s"]
    # 1) pausas: después de cada frase fuerte / revelación / pregunta, el silencio llega al menos a lo sorteado
    insertos: list[tuple[float, float]] = []          # (en qué segundo del original, cuánto silencio)
    for k, o in enumerate(ors[:-1]):
        if (marcas.get(o["id"]) or {}).get("rol") not in FUERTES:
            continue
        hueco = ors[k + 1]["inicio"] - o["fin"]
        falta = round(rng.uniform(lo, hi) - hueco, 3)
        if falta > 0.05:
            insertos.append((o["fin"] + min(0.05, hueco / 2), falta))
    piezas, cursor = [], 0
    for t, dur in insertos:
        i = int(t * SR)
        piezas += [audio[cursor:i], np.zeros(int(dur * SR), np.float32)]
        cursor = i
    piezas.append(audio[cursor:])
    nuevo = np.concatenate(piezas) if piezas else audio

    def corrido(t: float) -> float:
        return t + sum(d for x, d in insertos if x <= t)

    for o in ors:
        o["inicio"], o["fin"] = round(corrido(o["inicio"]), 3), round(corrido(o["fin"]), 3)
        for p in o.get("palabras") or []:
            p["inicio"], p["fin"] = round(corrido(p["inicio"]), 3), round(corrido(p["fin"]), 3)
    # 2) el cierre más lento (sin cambiar el tono): desde la primera oración marcada «cierre» hasta el final
    lento = None
    cierre = next((o for o in ors if (marcas.get(o["id"]) or {}).get("rol") == "cierre"), None)
    v = h["velocidad_cierre"]
    if cierre and v < 0.999:
        a = max(0.0, cierre["inicio"] - 0.05)
        i = int(a * SR)
        with tempfile.TemporaryDirectory() as tmp:
            ent, sal = Path(tmp) / "a.wav", Path(tmp) / "b.wav"
            escribir_wav(ent, nuevo[i:])
            r = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(ent), "-af", f"atempo={v}", "-ar",
                                str(SR), "-ac", "1", str(sal)], capture_output=True)
            if r.returncode == 0 and sal.exists():
                nuevo = np.concatenate([nuevo[:i], leer_wav(sal)])
                lento = round(a, 3)
        if lento is not None:
            for o in ors:
                if o["inicio"] >= a:
                    o["inicio"], o["fin"] = round(a + (o["inicio"] - a) / v, 3), round(a + (o["fin"] - a) / v, 3)
                    for p in o.get("palabras") or []:
                        p["inicio"], p["fin"] = round(a + (p["inicio"] - a) / v, 3), round(a + (p["fin"] - a) / v, 3)
    escribir_wav(dir_a / "voz.wav", nuevo)
    datos["duracion"] = round(len(nuevo) / SR, 3)
    datos["oraciones"] = ors
    escribir_json(dir_a / "oraciones.json", datos)
    info = {"pausas": len(insertos), "segundos_de_pausa": round(sum(d for _, d in insertos), 2),
            "cierre_desde": lento, "velocidad_cierre": v if lento is not None else 1.0}
    escribir_json(dir_a / "humano.json", info)
    avisar(f"  voz: {info['pausas']} pausas naturales" + (f" y el cierre al {v:.0%}" if lento is not None else ""))
    return info


# ------------------------------------------------------------------ 3. huella del video

def _archivo_huellas() -> Path:
    from ..plataforma.db import carpeta_datos

    return carpeta_datos() / "tracy_huellas.json"


def pistas_musica(carpeta: str) -> dict[str, list[str]]:
    """Las pistas de la carpeta del canal por sección, según cómo empieza su nombre."""
    salida: dict[str, list[str]] = {"gancho": [], "cuerpo": [], "venta": [], "cierre": []}
    base = Path(carpeta) if carpeta else None
    if not base or not base.is_dir():
        return salida
    from .preset import EXT_AUDIO

    for f in sorted(base.iterdir()):
        if f.suffix.lower() in EXT_AUDIO:
            n = _norm(f.stem)
            for s in salida:
                if n.startswith(s):
                    salida[s].append(str(f))
    return salida


def huella(canal: str, slug: str, h: dict) -> dict:
    """La combinación de este video (guardada en el proyecto y en el historial del canal): pista de cada sección,
    estilo del texto grande, transiciones suaves y forma de mover la cámara. Nunca igual a la del video anterior."""
    pistas = pistas_musica(h.get("carpeta_musica", ""))
    try:
        historial = leer_json(_archivo_huellas()) if _archivo_huellas().exists() else {}
    except Exception:  # noqa: BLE001
        historial = {}
    previos = [x for x in historial.get(canal, []) if x.get("slug") != slug]
    anterior = previos[-1]["combo"] if previos else None
    rng = random.Random(f"{slug}|huella")
    combo = None
    for _ in range(40):
        combo = {"musica": {s: (rng.choice(v) if v else None) for s, v in pistas.items()},
                 "estilo_texto": rng.choice(ESTILOS_TEXTO),
                 "transiciones": list(rng.choice(POOLS_TRANSICION)),
                 "movimiento": rng.choice(("suave", "variado", "quieto"))}
        if combo != anterior:
            break
    try:
        previos.append({"slug": slug, "combo": combo})
        historial[canal] = previos[-30:]
        escribir_json(_archivo_huellas(), historial)
    except Exception:  # noqa: BLE001 — sin carpeta de datos (pruebas sueltas): solo no se guarda
        pass
    return combo


# ------------------------------------------------------------------ 4. cortes de duración variable

def _rango(rol: str, en_gancho: bool, h: dict) -> tuple[float, float]:
    lo = h["clip_min_s"]
    if en_gancho or rol in RAPIDOS:
        return lo, max(lo + 1.5, 6.0)
    if rol in LENTOS:
        return max(lo, 10.0), min(h["clip_max_s"], 22.0)
    return max(lo, 5.0), min(h["clip_max_s"], 12.0)


def segmentar(oraciones: list[dict], duracion: float, marcas: dict[int, dict], h: dict, semilla: str) -> list[dict]:
    """Clips que terminan siempre al final de una oración, cada uno con una duración sorteada dentro del rango de su
    papel (así no hay cortes cada X segundos). Las oraciones que solas pasan del máximo se parten en su pausa más
    clara (como siempre)."""
    from .segmentos import _partir

    rng = random.Random(f"{semilla}|cortes")
    unidades: list[dict] = []
    for i, o in enumerate(oraciones):
        fin_cob = oraciones[i + 1]["inicio"] if i + 1 < len(oraciones) else duracion
        base = {**o, "oraciones": [o.get("id", i)], "palabras": o.get("palabras") or []}
        for u in _partir(base, fin_cob, h["clip_max_s"], 0.0 if i == 0 else None):
            u["rol"] = (marcas.get(o.get("id", i)) or {}).get("rol", "normal")
            unidades.append(u)
    if not unidades:
        return []
    ini = [0.0] + [u["inicio"] for u in unidades[1:]]
    fin = ini[1:] + [duracion]
    segmentos, j = [], 0
    while j < len(unidades):
        rol = unidades[j]["rol"]
        lo, hi = _rango(rol, ini[j] < h["gancho_s"], h)
        objetivo = rng.uniform(lo, hi)
        i = j + 1
        while i < len(unidades):
            dur = fin[i - 1] - ini[j]
            sig = fin[i] - ini[j]
            if unidades[i]["rol"] in ABREN_CLIP and dur >= h["clip_min_s"]:
                break                                         # lo que viene pide su propio clip
            if (dur >= objetivo and dur >= h["clip_min_s"]) or sig > h["clip_max_s"]:
                break
            if sig - objetivo > objetivo - dur and dur >= lo:
                break                                         # quedar cerca del objetivo
            i += 1
        grupo = unidades[j:i]
        ids: list[int] = []
        for u in grupo:
            ids += [x for x in u["oraciones"] if x not in ids]
        roles = [u["rol"] for u in grupo]
        principal = next((r for r in ("regla", "cta", "producto", "revelacion", "frase_fuerte", "cierre", "venta",
                                      "pregunta", "gancho", "reflexiva") if r in roles), "normal")
        segmentos.append({"id": len(segmentos), "inicio": round(ini[j], 3), "fin": round(fin[i - 1], 3),
                          "duracion": round(fin[i - 1] - ini[j], 3),
                          "voz_inicio": round(grupo[0]["inicio"], 3), "voz_fin": round(grupo[-1]["fin"], 3),
                          "texto": " ".join(u["texto"] for u in grupo), "oraciones": ids,
                          "rol": principal, "abre": roles[0],
                          "oracion_partida": any(u.get("partida") for u in grupo)})
        j = i
    # un clip final de menos del mínimo se junta con el anterior (si cabe)
    if len(segmentos) > 1 and segmentos[-1]["duracion"] < h["clip_min_s"] and \
            segmentos[-1]["fin"] - segmentos[-2]["inicio"] <= h["clip_max_s"]:
        a, b = segmentos[-2], segmentos.pop()
        a.update(fin=b["fin"], duracion=round(b["fin"] - a["inicio"], 3), voz_fin=b["voz_fin"],
                 texto=f"{a['texto']} {b['texto']}", oraciones=a["oraciones"] + b["oraciones"])
    return segmentos


def seccion(seg: dict, h: dict, desde_cierre: float | None) -> str:
    if desde_cierre is not None and seg["inicio"] >= desde_cierre - 1e-6:
        return "cierre"
    if seg["inicio"] < h["gancho_s"] or seg["rol"] == "gancho":
        return "gancho"
    if seg["rol"] in ("venta", "producto", "cta"):
        return "venta"
    return "cuerpo"


# ------------------------------------------------------------------ 5. el plan: qué se ve y cómo

PRIORIDAD_FENIX = {"cta": 0, "regla": 1, "cierre": 2, "frase_fuerte": 3, "revelacion": 5}
MOOD = {"gancho": "energetic", "regla": "inspiring", "frase_fuerte": "triumphant", "revelacion": "tense",
        "pregunta": "reflective", "cta": "hopeful", "producto": "inspiring", "venta": "hopeful", "cierre": "hopeful",
        "reflexiva": "calm", "normal": "inspiring"}


def planificar(segmentos: list[dict], marcas: dict[int, dict], duracion: float, h: dict, combo: dict,
               semilla: str, inicios: dict[int, float] | None = None) -> list[dict]:
    """Por clip: seminario, stock o escena final; palabras clave de lo que se dice; movimiento; transición de
    entrada; texto grande; sección (para la música) y si lleva whoosh o riser."""
    from .planificador import GENERICAS

    rng = random.Random(f"{semilla}|plan")
    corte_final = duracion * h["escena_final_desde"] if h["escena_final_desde"] < 1 else None
    desde_cierre = next((s["inicio"] for s in segmentos if s["rol"] == "cierre"), None)
    plan = []
    for s in segmentos:
        kws: list[str] = []
        for oid in s["oraciones"]:
            kws += [k for k in (marcas.get(oid) or {}).get("keywords", []) if k not in kws]
        if len(kws) < 2:
            kws += [g for g in rng.sample(GENERICAS, 2) if g not in kws]
        # el texto grande sale cuando la voz dice SU frase (aunque no sea la primera de la toma)
        con_texto = next((oid for oid in s["oraciones"] if (marcas.get(oid) or {}).get("grande")
                          and (marcas.get(oid) or {}).get("rol") in CON_TEXTO_GRANDE), None)
        en = round(max(0.0, (inicios or {}).get(con_texto, s["inicio"]) - s["inicio"]), 3) if con_texto is not None else 0.0
        tipo = "final" if corte_final is not None and s["inicio"] >= corte_final - 1e-6 and plan else "stock"
        plan.append({"id": s["id"], "inicio": s["inicio"], "fin": s["fin"], "duracion": s["duracion"],
                     "type": tipo, "keywords": kws[:3], "mood": MOOD.get(s["rol"], "inspiring"), "rol": s["rol"],
                     "seccion": seccion(s, h, desde_cierre), "oraciones": s["oraciones"],
                     "grande": marcas[con_texto]["grande"] if con_texto is not None else None,
                     "grande_en": en})
    # seminario: solo en momentos de autoridad, por prioridad, sin pasar el máximo de tiempo ni ir 3 seguidos
    clips = [p for p in plan if p["type"] != "final"]
    total = sum(p["duracion"] for p in clips) or 1.0
    candidatos = [p for p in clips if p["rol"] in PRIORIDAD_FENIX]
    candidatos.sort(key=lambda p: (PRIORIDAD_FENIX[p["rol"]], rng.random()))
    usado = 0.0
    for p in candidatos:
        if p["rol"] in ("frase_fuerte", "revelacion") and rng.random() < 0.4:
            continue                                      # no TODAS las frases fuertes: así no se vuelve fórmula
        if usado + p["duracion"] > h["fenix_max"] * total:
            continue
        k = clips.index(p)
        izq = 0
        while k - izq - 1 >= 0 and clips[k - izq - 1]["type"] == "seminar":
            izq += 1
        der = 0
        while k + der + 1 < len(clips) and clips[k + der + 1]["type"] == "seminar":
            der += 1
        if izq + der + 1 > 2:
            continue                                      # nunca 3 tomas del seminario seguidas
        p["type"] = "seminar"
        usado += p["duracion"]
    # movimiento: nunca el mismo dos veces seguidas; un poco más de acercamiento en las frases de énfasis
    pesos = {"suave": (3, 3, 2, 2, 2), "variado": (2, 2, 3, 3, 1), "quieto": (2, 2, 1, 1, 4)}[combo["movimiento"]]
    previo = None
    for p in plan:
        if p["type"] == "final":
            p["movimiento"], p["zoom"] = "fijo", 1.0
            continue
        opciones = [m for m in MOVIMIENTOS if m != previo]
        ws = [pesos[MOVIMIENTOS.index(m)] for m in opciones]
        enfasis = p["rol"] in ("frase_fuerte", "revelacion", "regla")
        m = "acercar" if enfasis and previo != "acercar" else rng.choices(opciones, weights=ws)[0]
        p["movimiento"], p["zoom"] = m, (1.10 if enfasis and m == "acercar" else 1.05)
        previo = m
    # transiciones: casi todo corte seco; de vez en cuando suave (nunca dos seguidas); sonidos escasos
    suave_previa = False
    for k, p in enumerate(plan):
        p["transicion"], p["whoosh"], p["riser"] = "corte", False, False
        if k == 0 or p["type"] == "final" and plan[k - 1]["type"] == "final":
            continue
        if not suave_previa and rng.random() < h["suaves"]:
            p["transicion"] = rng.choice(combo["transiciones"])
            p["whoosh"] = True
            suave_previa = True
        else:
            suave_previa = False
            p["whoosh"] = rng.random() < h["whoosh"] and not plan[k - 1].get("whoosh")
        p["riser"] = bool(h["riser"]) and p["rol"] == "revelacion"
    return plan


def tomas(plan: list[dict]) -> list[dict]:
    """El plan humano ya va toma por toma (un clip por segmento): solo se numera como lo espera elegir_clips."""
    return [{**p, "segmento": p["id"]} for p in plan]


def recortar_guion(guion: str, segundos: float, cps: float) -> str:
    """«Probar 3 minutos»: las primeras oraciones del guion que caben en `segundos` de voz (al menos una)."""
    from .audio import oraciones

    salida, largo = [], 0
    for o in oraciones(guion):
        if salida and (largo + len(o)) / cps > segundos:
            break
        salida.append(o)
        largo += len(o) + 1
    return " ".join(salida)


# ------------------------------------------------------------------ 6. reporte de edición

def reporte(carpeta: CarpetaProyecto) -> dict:
    clips = leer_json(carpeta.ruta / "clips.json")["clips"]
    visibles = [c for c in clips if c["tipo"] != "final"]
    duraciones = [c["fin"] - c["inicio"] for c in visibles] or [0.0]
    total = sum(c["fin"] - c["inicio"] for c in clips) or 1.0
    fenix = sum(c["fin"] - c["inicio"] for c in clips if c["tipo"] == "seminario")
    final = sum(c["fin"] - c["inicio"] for c in clips if c["tipo"] == "final")
    media = statistics.mean(duraciones)
    desviacion = statistics.pstdev(duraciones) if len(duraciones) > 1 else 0.0
    audio = carpeta.ruta / "audio" / "humano.json"
    voz = leer_json(audio) if audio.exists() else {}
    efectos = {
        "movimientos": {m: sum(1 for c in visibles if c.get("movimiento") == m) for m in MOVIMIENTOS},
        "transiciones": {t: sum(1 for c in clips if c.get("transicion") == t) for t in ("corte", "fundido", "destello")},
        "textos_grandes": sum(1 for c in clips if c.get("grande")),
        "whoosh": sum(1 for c in clips if c.get("whoosh")),
        "riser": sum(1 for c in clips if c.get("riser")),
        "pausas_naturales": voz.get("pausas", 0),
    }
    datos = {"clips": len(visibles), "duracion_media_s": round(media, 2), "desviacion_s": round(desviacion, 2),
             "variacion_pct": round(100 * desviacion / media, 1) if media else 0.0,
             "mas_corto_s": round(min(duraciones), 2), "mas_largo_s": round(max(duraciones), 2),
             "fenix_pct": round(100 * fenix / total, 1), "stock_pct": round(100 * (total - fenix - final) / total, 1),
             "escena_final_pct": round(100 * final / total, 1),
             "stock_unicos": len({c.get("pexels_id") for c in clips if c["tipo"] == "stock"}), "efectos": efectos}
    escribir_json(carpeta.ruta / "reporte_edicion.json", datos)
    return datos
