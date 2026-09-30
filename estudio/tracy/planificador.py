"""Planificador visual del modo Tracy: qué se ve en cada segmento.

Claude (el modelo más económico, por la suscripción) lee los segmentos y devuelve por cada uno
`type` («seminar» | «stock»), 2-3 `keywords` en inglés para buscar stock según lo que dice el
texto, y `mood`. Después unas reglas fijas garantizan lo que no se deja al azar:

- la proporción seminario/stock del preset (p. ej. 40/60), redondeada al segmento más cercano;
- nunca más de 2 segmentos «seminar» seguidos.

Si Claude falla o no está, el plan sale solo de las reglas (palabras clave sacadas del texto),
para que el video igual se pueda armar. El plan queda en `plan_visual.json`; si los segmentos no
cambian, no se vuelve a pedir.
"""
from __future__ import annotations

import hashlib
import json
import re

from .. import claude_cli
from ..config import escribir_json, leer_config, leer_json
from ..proyecto import CarpetaProyecto

MAX_SEMINARIO_SEGUIDOS = 2
MOODS = ("inspiring", "calm", "energetic", "serious", "hopeful", "reflective", "tense", "triumphant")
GENERICAS = ["success", "business", "motivation", "city", "nature", "people working", "sunrise", "office"]


def _instruccion(segmentos: list[dict], proporcion: float) -> str:
    lista = "\n".join(f'{s["id"]}: {s["texto"][:400]}' for s in segmentos)
    n = len(segmentos)
    return (
        "Eres el editor visual de un video narrado de desarrollo personal (estilo seminario de Brian Tracy). "
        "Cada segmento se cubre con UNO de dos tipos de imagen:\n"
        '- "seminar": el video de un conferencista en un escenario (sirve para frases de consejo directo, '
        "reflexiones, llamados a la acción o cuando se habla al espectador).\n"
        '- "stock": un clip de banco de video que muestra lo que dice el texto (ejemplos concretos, personas, '
        "lugares, objetos, acciones).\n\n"
        f"Hay {n} segmentos. Usa \"seminar\" en unos {round(n * proporcion)} ({proporcion:.0%}) y nunca más de "
        f"{MAX_SEMINARIO_SEGUIDOS} seguidos.\n"
        "Para cada segmento da también 2 o 3 keywords EN INGLÉS para buscar el clip de stock (cosas que se "
        "puedan filmar: 'man running at sunrise', 'handshake office', no ideas abstractas) aunque sea seminar, "
        f"y un mood en inglés de esta lista: {', '.join(MOODS)}.\n\n"
        f"Segmentos (id: texto):\n{lista}\n\n"
        'Responde SOLO un JSON: {"segmentos": [{"id": 0, "type": "stock", "keywords": ["...", "..."], '
        '"mood": "inspiring"}, ...]} con todos los ids en orden.'
    )


def _palabras_clave(texto: str) -> list[str]:
    """Respaldo sin Claude: nada que traducir, así que se usan búsquedas genéricas que siempre dan."""
    h = int(hashlib.sha256(texto.encode()).hexdigest(), 16)
    return [GENERICAS[h % len(GENERICAS)], GENERICAS[(h // 7) % len(GENERICAS)]]


def _limpiar(item: dict, texto: str) -> dict:
    tipo = str(item.get("type", "stock")).strip().lower()
    tipo = "seminar" if tipo.startswith("semin") else "stock"
    kws = item.get("keywords") or []
    if isinstance(kws, str):
        kws = re.split(r"[,;]", kws)
    kws = [re.sub(r"\s+", " ", str(k)).strip()[:40] for k in kws if str(k).strip()][:3]
    if len(kws) < 2:
        kws = (kws + _palabras_clave(texto))[:2]
    mood = str(item.get("mood") or "inspiring").strip().lower()
    return {"type": tipo, "keywords": kws, "mood": mood if mood in MOODS else "inspiring"}


def _racha(tipos: list[str], i: int) -> int:
    """Largo de la racha de «seminar» que contendría la posición i si fuera seminar."""
    a = i
    while a - 1 >= 0 and tipos[a - 1] == "seminar":
        a -= 1
    b = i
    while b + 1 < len(tipos) and tipos[b + 1] == "seminar":
        b += 1
    return b - a + 1


def ajustar(plan: list[dict], proporcion: float) -> list[dict]:
    """Aplica las reglas fijas sobre lo que propuso Claude (cambiando lo mínimo)."""
    n = len(plan)
    tipos = [p["type"] for p in plan]
    # 1) romper rachas de más de 2 seminar (el tercero de cada racha pasa a stock)
    seguidos = 0
    for i in range(n):
        seguidos = seguidos + 1 if tipos[i] == "seminar" else 0
        if seguidos > MAX_SEMINARIO_SEGUIDOS:
            tipos[i], seguidos = "stock", 0
    # 2) la proporción del preset
    meta = round(n * proporcion)
    # el máximo posible con rachas de 2 es 2 de cada 3
    meta = min(meta, n - n // (MAX_SEMINARIO_SEGUIDOS + 1))
    actuales = [i for i in range(n) if tipos[i] == "seminar"]
    if len(actuales) > meta:
        # sobran: se quitan primero los que están en rachas (más «pegados»), de atrás hacia adelante
        for i in sorted(actuales, key=lambda i: (-_racha(tipos, i), -i))[: len(actuales) - meta]:
            tipos[i] = "stock"
    elif len(actuales) < meta:
        # faltan: se agregan repartidos a lo largo del video, donde no formen racha de 3
        faltan = meta - len(actuales)
        candidatos = [i for i in range(n) if tipos[i] == "stock"]
        paso = max(1, len(candidatos) // max(1, faltan))
        orden = candidatos[::paso] + [c for c in candidatos if c not in candidatos[::paso]]
        for i in orden:
            if faltan == 0:
                break
            tipos[i] = "seminar"
            if _racha(tipos, i) > MAX_SEMINARIO_SEGUIDOS:
                tipos[i] = "stock"
                continue
            faltan -= 1
    return [{**p, "type": t} for p, t in zip(plan, tipos)]


def _huella(segmentos: list[dict], proporcion: float) -> str:
    base = json.dumps([(s["id"], s["texto"]) for s in segmentos], ensure_ascii=False) + f"|{proporcion}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def planificar(carpeta: CarpetaProyecto, preset: dict, ejecutar=None, avisar=print, config=None) -> list[dict]:
    """Escribe y devuelve `plan_visual.json`: por segmento id, inicio, fin, type, keywords, mood."""
    datos = leer_json(carpeta.ruta / "segmentos.json")
    segmentos = datos["segmentos"]
    proporcion = float(preset["proporcion_seminario"])
    ruta = carpeta.ruta / "plan_visual.json"
    huella = _huella(segmentos, proporcion)
    if ruta.exists():
        previo = leer_json(ruta)
        if previo.get("huella") == huella:
            return previo["plan"]
    propuesto: dict[int, dict] = {}
    origen = "reglas"
    if ejecutar is None:
        modelo = (leer_config("proveedores.json").get("claude") or {}).get("modelo_tracy", "haiku")

        def ejecutar(prompt, cwd=None):
            return claude_cli.ejecutar(prompt, cwd=cwd, modelo=modelo, pensamiento=0, tiempo_max_s=600)
    try:
        avisar("Planificando qué se ve en cada segmento (Claude)…")
        texto, sobre = ejecutar(_instruccion(segmentos, proporcion), cwd=carpeta.ruta)
        for item in (claude_cli.extraer_json(texto) or {}).get("segmentos", []):
            try:
                propuesto[int(item.get("id"))] = item
            except (TypeError, ValueError):
                continue
        origen = "claude"
        _registrar_costo(carpeta, sobre, config)
    except Exception as ex:  # noqa: BLE001 — sin Claude el plan sale de las reglas
        avisar(f"  Claude no pudo planificar ({ex}); uso el plan por reglas")
    plan = [{"id": s["id"], "inicio": s["inicio"], "fin": s["fin"], "duracion": s["duracion"],
             **_limpiar(propuesto.get(s["id"], {}), s["texto"])} for s in segmentos]
    if origen == "reglas":
        # sin Claude: seminario repartido de forma pareja (la proporción la fija `ajustar`)
        for p in plan:
            p["type"] = "stock"
    plan = ajustar(plan, proporcion)
    escribir_json(ruta, {"huella": huella, "origen": origen, "proporcion": proporcion, "plan": plan})
    sem = sum(1 for p in plan if p["type"] == "seminar")
    avisar(f"  plan: {sem} de seminario y {len(plan) - sem} de stock ({origen})")
    return plan


def _registrar_costo(carpeta: CarpetaProyecto, sobre: dict, config) -> None:
    """Claude va por la suscripción (0 pesos); se anotan los tokens para saber cuánto se usó."""
    from ..config import ConfigCostos

    uso = (sobre or {}).get("usage") or {}
    unidades = {k: float(uso.get(k, 0) or 0) for k in ("input_tokens", "output_tokens")}
    carpeta.libro(config or ConfigCostos.cargar()).registrar(
        modulo="tracy_planificador", proveedor="claude", modelo=str((sobre or {}).get("model") or "haiku"),
        unidades=unidades, costo_usd=0.0,
        detalle=f"plan visual por la suscripción (equivale a ~{float((sobre or {}).get('total_cost_usd') or 0):.4f} USD)")


def marcar_final(plan: list[dict], duracion: float, desde: float, proporcion: float) -> list[dict]:
    """Los segmentos que empiezan desde `desde` (fracción del video) pasan a la escena final fija; la
    proporción seminario/stock se vuelve a cuadrar solo en la parte de antes."""
    if desde >= 1 or not plan:
        return plan
    corte = duracion * desde
    antes = [p for p in plan if p["inicio"] < corte - 1e-6]
    if not antes:                    # siempre queda al menos un segmento de clips al comienzo
        antes = plan[:1]
    ids_antes = {p["id"] for p in antes}
    antes = ajustar([{**p, "type": "stock" if p["type"] == "final" else p["type"]} for p in antes], proporcion)
    return antes + [{**p, "type": "final"} for p in plan if p["id"] not in ids_antes]
