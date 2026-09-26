"""Foco sobre lo que nombra la voz (círculo rojo con el resto oscurecido) y flechas.

1. `candidatos` busca, sin IA, las escenas donde la narración nombra a un animal de
   la tira de niveles (por su nombre completo o lo que lo distingue de los demás) y las
   escenas de explicación, que suelen hablar de un detalle concreto.
2. `ubicar_focos` le pide a Claude (suscripción, herramienta Read) que mire esas
   imágenes y devuelva la palabra exacta y la caja de lo nombrado. Si no se ve con
   claridad, no hay foco: nunca se encierra algo que no está.
3. El Director de edición decide cuándo usarlo (con frecuencia limitada) y el motor
   de render lo dibuja. El villano pixelado nunca recibe foco antes de su revelación.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

from . import claude_cli
from .config import escribir_json, leer_json

VACIAS = {"para", "como", "sobre", "entre", "desde", "hasta", "este", "esta", "estos", "estas", "del", "los", "las",
          "comun", "gigante", "grande", "pequeno", "negro", "negra", "rojo", "roja"}
POR_LLAMADA = 20


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if not unicodedata.combining(c))


def _variantes(w: str) -> set[str]:
    return {w, w + "s", w + "es", w[:-1] + "ces" if w.endswith("z") else w}


def claves_de_nombre(niveles: list[dict]) -> dict[int, dict]:
    """Por nivel: su palabra principal y las palabras que lo distinguen de los demás.
    «Mosquito del dengue» → principal mosquito (no «mosquitero»); «Chinche de cama» →
    como «chinche» la comparten dos niveles, hay que decir «chinche(s) de cama»."""
    toks = {n["numero"]: [w for w in re.findall(r"[a-zñ]+", _norm(n["nombre"])) if len(w) >= 4 and w not in VACIAS]
            for n in niveles}
    cuenta = Counter(w for ws in toks.values() for w in set(ws))
    salida = {}
    for k, ws in toks.items():
        if ws:
            salida[k] = {"principal": ws[0], "unica": cuenta[ws[0]] == 1,
                         "distintivas": [w for w in ws[1:] if cuenta[w] == 1]}
    return salida


def palabra_en(narracion: str, clave: dict) -> str | None:
    """La palabra tal como está en la narración que nombra a ese animal, o None."""
    palabras = re.findall(r"[\wáéíóúñü]+", narracion)
    norm = [_norm(w) for w in palabras]
    principal = _variantes(clave["principal"])
    for i, w in enumerate(norm):
        if w not in principal:
            continue
        if clave["unica"]:
            return palabras[i]
        siguientes = set(norm[i + 1:i + 4])
        if any(_variantes(d) & siguientes for d in clave["distintivas"]):
            return palabras[i]
    return None


def candidatos(escenas: dict, direccion: dict, maximo: int = 80) -> list[dict]:
    niveles = escenas.get("niveles", [])
    claves = claves_de_nombre(niveles)
    villano = next((n["numero"] for n in niveles if n.get("villano")), None)
    revelacion = int(direccion.get("villano_revelacion", 0)) or None
    salida = []
    for e in escenas["escenas"]:
        v = e.get("visual", {})
        if v.get("accion") != "generar" or not v.get("archivo"):
            continue
        oculto = revelacion is None or e["id"] < revelacion
        hallado = None
        for n in niveles:
            if n["numero"] == villano and oculto:
                continue
            p = palabra_en(e["narracion"], claves[n["numero"]]) if n["numero"] in claves else None
            if p:
                hallado = {"escena": e["id"], "tipo": "nombre", "palabra": p, "que": n["nombre"],
                           "archivo": v["archivo"], "narracion": e["narracion"]}
                break
        if hallado is None and e.get("intencion") == "explicacion":
            hallado = {"escena": e["id"], "tipo": "detalle", "palabra": None, "que": None,
                       "archivo": v["archivo"], "narracion": e["narracion"]}
        if hallado and str(e["id"]) not in (direccion.get("pixelar") or {}):
            salida.append(hallado)
    return salida[:maximo]


def _instruccion(lote: list[dict]) -> str:
    filas = []
    for c in lote:
        busca = (f"busca: {c['que']} (la narración lo nombra como «{c['palabra']}»)" if c["tipo"] == "nombre"
                 else "busca: el detalle concreto y visible que nombra la narración (una parte del cuerpo, un objeto, un lugar)")
        filas.append(f"- escena {c['escena']}: {c['archivo']}\n  narración: «{c['narracion']}»\n  {busca}")
    return ("Mira cada imagen con la herramienta Read (rutas relativas a esta carpeta):\n" + "\n".join(filas) + "\n\n"
            "Para cada escena devuelve dónde está lo que se busca. Responde SOLO un JSON así:\n"
            '{"<numero de escena>": {"palabra": "<la palabra EXACTA de la narración que lo nombra>", '
            '"caja": [x0, y0, x1, y1]}}\n'
            "con la caja en coordenadas normalizadas de 0 a 1 (x a la derecha, y hacia abajo), ajustada a lo que se "
            "busca con un margen del 5 %. Pon null si no se ve con claridad o si la narración no nombra nada visible. "
            "No encierres a la mascota salvo que la narración hable de ella.")


def ubicar_focos(carpeta: Path, ejecutar=claude_cli.ejecutar, avisar=print) -> dict:
    """Llena direccion.json["focos"] con {escena: {tipo, palabra, caja}}. Reanudable:
    las escenas ya revisadas no se vuelven a preguntar."""
    ruta = carpeta / "direccion.json"
    direccion = leer_json(ruta) if ruta.exists() else {}
    escenas = leer_json(carpeta / "escenas.json")
    revisadas = set(direccion.get("focos_revisados", []))
    todos = candidatos(escenas, direccion)
    pendientes = [c for c in todos if c["escena"] not in revisadas]
    # si el guion cambió, un foco viejo que ya no corresponde se descarta
    vigentes = {str(c["escena"]): c["tipo"] for c in todos}
    focos = {k: v for k, v in (direccion.get("focos") or {}).items() if vigentes.get(k) == v.get("tipo")}
    if focos != (direccion.get("focos") or {}):
        direccion["focos"] = focos
        escribir_json(ruta, direccion)
    for i in range(0, len(pendientes), POR_LLAMADA):
        lote = pendientes[i:i + POR_LLAMADA]
        avisar(f"Claude está mirando {len(lote)} imágenes para el círculo y las flechas…")
        texto, _ = ejecutar(_instruccion(lote), cwd=carpeta, herramientas=["Read"])
        datos = claude_cli.extraer_json(texto) or {}
        por_id = {c["escena"]: c for c in lote}
        for k, v in datos.items():
            c = por_id.get(int(k)) if str(k).isdigit() else None
            if not c or not isinstance(v, dict) or not v.get("caja") or len(v["caja"]) != 4:
                continue
            x0, y0, x1, y1 = (min(max(float(z), 0.0), 1.0) for z in v["caja"])
            if x1 - x0 < 0.03 or y1 - y0 < 0.03:
                continue
            palabra = c["palabra"] if c["tipo"] == "nombre" else (v.get("palabra") or "")
            if palabra and _norm(palabra) not in _norm(c["narracion"]):
                palabra = c["palabra"] or ""
            focos[str(c["escena"])] = {"tipo": c["tipo"], "palabra": palabra,
                                       "caja": [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]}
        revisadas |= {c["escena"] for c in lote}
        direccion["focos"], direccion["focos_revisados"] = focos, sorted(revisadas)
        escribir_json(ruta, direccion)
    return direccion
