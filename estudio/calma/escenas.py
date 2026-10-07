"""El archivo de escenas de un video (escenas.json) y cómo se ata a los tiempos reales de la voz.

    {"video": {"ancho": 1920, "alto": 1080, "fps": 30},
     "escenas": [
       {"id": 1, "palabra_inicio": "Te quitas", "inicio": 0.0, "fin": 2.4, "fondo": "blanco",
        "temblor": [{"palabra": "arranques"}],
        "elementos": [
          {"id": "pie", "pieza": "pierna", "estado": {}, "posicion": [760, 900], "tamano": 1.0,
           "movimiento": ["aparecer"], "palabra": "Te", "entra": 0.0},
          ...]}]}

Cada elemento tiene pieza, posición (en px de 1920x1080), tamaño, movimiento y el segundo exacto en
que entra («entra»). «palabra» dice qué palabra del narrador lo hace entrar: `fijar_tiempos` busca
esa palabra en los tiempos reales de Whisper (en orden, avanzando por el guion) y escribe «entra».
Los movimientos también pueden llevar «palabra» (p. ej. cambiar de pose cuando dice «susto»).
Así otro paso podrá escribir este JSON a partir de un guion sin saber todavía los segundos.
"""
from __future__ import annotations

import re
import unicodedata

from .movimientos import TIPOS
from .piezas import PIEZAS

FONDOS = ("blanco", "calle", "campo")
MAX_EN_PANTALLA = 4
MAX_SIN_CAMBIO_S = 2.0
ADELANTO_CORTE_S = 0.08       # el corte de escena cae un pelín antes de la palabra (se siente a tiempo)


def normalizar(palabra: str) -> str:
    t = unicodedata.normalize("NFKD", palabra.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t)


def palabras_de(oraciones: dict) -> list[dict]:
    """Lista plana de palabras con tiempo, tal como la deja la alineación (audio/oraciones.json)."""
    return [{"p": w["p"], "n": normalizar(w["p"]), "inicio": float(w["inicio"]), "fin": float(w["fin"])}
            for o in oraciones["oraciones"] for w in o["palabras"] if normalizar(w["p"])]


def _buscar(palabras: list[dict], ancla: str, desde: int) -> int:
    objetivo = [normalizar(x) for x in ancla.split() if normalizar(x)]
    if not objetivo:
        raise ValueError(f"la palabra «{ancla}» está vacía")
    for i in range(desde, len(palabras) - len(objetivo) + 1):
        if all(palabras[i + k]["n"] == objetivo[k] for k in range(len(objetivo))):
            return i
    raise ValueError(f"no encontré «{ancla}» en la narración (después de «{palabras[desde - 1]['p'] if desde else ''}»)")


def fijar_tiempos(datos: dict, palabras: list[dict], duracion: float) -> dict:
    """Escribe «inicio»/«fin» de cada escena y «entra»/«t» de cada elemento y movimiento a partir de sus
    palabras. Se busca en orden: cada palabra se encuentra a partir de la anterior encontrada."""
    cursor = 0
    escenas = datos["escenas"]
    ritmo = float(datos.get("video", {}).get("ritmo", 1.0))
    if ritmo != 1.0:                                   # «ritmo» < 1: todas las animaciones más cortas (más ágil)
        from .movimientos import DURACION

        for esc in escenas:
            for el in esc["elementos"]:
                movs = el.get("movimiento") or []
                movs = [movs] if isinstance(movs, (str, dict)) else movs
                nuevos = []
                for m in movs:
                    m = {"tipo": m} if isinstance(m, str) else m
                    if "duracion" not in m and DURACION.get(m["tipo"]) and m["tipo"] not in ("crecer",):
                        m["duracion"] = round(DURACION[m["tipo"]] * ritmo, 3)
                    elif "duracion" in m and m["tipo"] not in ("crecer", "llenar_barra"):
                        m["duracion"] = round(float(m["duracion"]) * ritmo, 3)
                    nuevos.append(m)
                el["movimiento"] = nuevos
    for esc in escenas:
        if esc.get("palabra_inicio"):
            cursor = _buscar(palabras, esc["palabra_inicio"], cursor)
            esc["inicio"] = 0.0 if esc is escenas[0] else round(max(0.0, palabras[cursor]["inicio"] - ADELANTO_CORTE_S), 3)
        for m in esc.get("temblor", []) + esc.get("empujon", []):
            if m.get("palabra"):
                m["t"] = palabras[_buscar(palabras, m["palabra"], cursor)]["inicio"]
        for el in esc["elementos"]:
            if el.get("palabra"):
                i = _buscar(palabras, el["palabra"], cursor)
                cursor = i
                el["entra"] = round(palabras[i]["inicio"] + float(el.get("retraso", 0)), 3)
            elif "entra" not in el:
                el["entra"] = esc.get("inicio", 0.0)
            movs = el.get("movimiento") or []
            for m in movs if isinstance(movs, list) else []:
                if isinstance(m, dict) and m.get("palabra"):
                    m["t"] = round(palabras[_buscar(palabras, m["palabra"], cursor)]["inicio"]
                                   + float(m.get("retraso", 0)), 3)
                if isinstance(m, dict) and m.get("tipo") == "deslizar" and m.get("sale"):
                    # se va de la pantalla: deja de contar cuando termina de salir
                    el["sale"] = round(float(m.get("t", el["entra"])) + float(m.get("duracion", 0.55)), 3)
            if el.get("sale_palabra"):
                el["sale"] = palabras[_buscar(palabras, el["sale_palabra"], cursor)]["inicio"]
    for k, esc in enumerate(escenas):
        esc["fin"] = escenas[k + 1]["inicio"] if k + 1 < len(escenas) else round(duracion, 3)
        for el in esc["elementos"]:                   # lo que «ya estaba» entra con el corte
            if el.get("ya_estaba"):
                el["entra"] = esc["inicio"]
            movs = el.get("movimiento") or []
            for m in movs if isinstance(movs, list) else []:
                if isinstance(m, dict) and "t_rel" in m:      # relativo al corte (escalonados)
                    m["t"] = round(esc["inicio"] + float(m["t_rel"]), 3)
    datos.setdefault("video", {})["duracion"] = round(duracion, 3)
    return datos


def recortar(datos: dict, hasta: float) -> dict:
    """Deja solo lo que pasa antes de `hasta` (la prueba de 60 s corta al final de una oración)."""
    datos["escenas"] = [e for e in datos["escenas"] if e["inicio"] < hasta - 0.3]
    if datos["escenas"]:
        datos["escenas"][-1]["fin"] = round(hasta, 3)
    datos["video"]["duracion"] = round(hasta, 3)
    return datos


def revisar(datos: dict, max_sin_cambio: float = MAX_SIN_CAMBIO_S) -> list[str]:
    """Las reglas de ritmo y de forma. Devuelve avisos (vacío = todo bien)."""
    avisos = []
    momentos = []
    for esc in datos["escenas"]:
        if esc.get("fondo", "blanco") not in FONDOS:
            avisos.append(f"escena {esc['id']}: fondo «{esc.get('fondo')}» no existe ({', '.join(FONDOS)})")
        momentos.append(esc["inicio"])
        for el in esc["elementos"]:
            if el["pieza"] not in PIEZAS:
                avisos.append(f"escena {esc['id']}: la pieza «{el['pieza']}» no existe")
            movs = el.get("movimiento") or []
            movs = [movs] if isinstance(movs, (str, dict)) else movs
            for m in movs:
                tipo = m if isinstance(m, str) else m.get("tipo")
                if tipo not in TIPOS:
                    avisos.append(f"escena {esc['id']}: movimiento «{tipo}» no existe")
                elif isinstance(m, dict) and "t" in m and tipo in ("cambiar_pose", "temblor", "llenar_barra",
                                                                     "girar", "crecer", "deslizar"):
                    momentos.append(float(m["t"]))
            if not esc["inicio"] - 0.01 <= el["entra"] < esc["fin"]:
                avisos.append(f"escena {esc['id']}: «{el['id']}» entra en {el['entra']:.2f} s, fuera de la escena "
                              f"({esc['inicio']:.2f}-{esc['fin']:.2f})")
            momentos.append(el["entra"])
        for m in esc.get("temblor", []):
            momentos.append(float(m.get("t", esc["inicio"])))
        # máximo de elementos a la vez (rótulos y signos incluidos); la cuadrícula de temas es la excepción
        for el in ([] if esc.get("tipo") == "cuadricula" else esc["elementos"]):
            t = el["entra"] + 0.01
            vivos = [x for x in esc["elementos"] if x["entra"] <= t and (x.get("sale") is None or x["sale"] > t)]
            if len(vivos) > MAX_EN_PANTALLA:
                avisos.append(f"escena {esc['id']}: {len(vivos)} elementos a la vez en {t:.1f} s (máximo {MAX_EN_PANTALLA})")
                break
    momentos = sorted(set(round(m, 2) for m in momentos) | {round(datos["video"]["duracion"], 2)})
    for a, b in zip(momentos, momentos[1:]):
        if b - a > max_sin_cambio + 0.05:
            avisos.append(f"de {a:.1f} a {b:.1f} s ({b - a:.1f} s) no aparece ni cambia nada")
    return avisos


def tiempos_estimados(texto: str, palabras_por_segundo: float = 3.3) -> tuple[list[dict], float]:
    """SOLO para ensayos sin voz: tiempos inventados al ritmo dado (contando pausas), más largos en los
    puntos y comas. El video de verdad usa los tiempos de Whisper."""
    crudo, t = [], 0.0
    for p in texto.split():
        dur = 0.16 + 0.045 * len(normalizar(p))
        if normalizar(p):
            crudo.append((p, t, t + dur))
        t += dur + (0.42 if p.endswith((".", "?", "!", ":")) else 0.18 if p.endswith((",", ";")) else 0.03)
    k = (len(crudo) / palabras_por_segundo) / t if t else 1.0
    salida = [{"p": p, "n": normalizar(p), "inicio": round(0.3 + a * k, 3), "fin": round(0.3 + b * k, 3)}
              for p, a, b in crudo]
    return salida, 0.3 + t * k + 0.4
