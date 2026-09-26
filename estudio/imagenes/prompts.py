"""Armado del prompt de cada imagen a partir del estilo (sección 5.2 y 12).

Aquí no hay ningún tipo de escena ni texto de prompt: todo sale de `estilo.json`.
El código solo rellena las variables de la plantilla y limpia la puntuación que
queda cuando una variable viene vacía.
"""
from __future__ import annotations

import re
import string
from pathlib import Path

from ..config import leer_json
from ..esquemas import AssetDef, Escena, Estilo


class _Faltantes(dict):
    def __missing__(self, clave: str) -> str:
        return ""


def variables_de(plantilla: str) -> set[str]:
    return {c for _, c, _, _ in string.Formatter().parse(plantilla) if c}


def _limpiar(texto: str) -> str:
    t = re.sub(r"\s+", " ", texto)
    t = re.sub(r"\s+([.,])", r"\1", t)
    t = re.sub(r"([.,])(?:\s*[.,])+", r"\1", t)
    return t.strip(" ,.") + "."


def personaje_del_proyecto(carpeta: Path, estilo: Estilo) -> str:
    """Bloqueo literal del personaje: perfil del canal > estilo por defecto."""
    perfil = carpeta / "perfil_canal.json"
    if perfil.exists():
        bloqueo = ((leer_json(perfil).get("personaje") or {}).get("bloqueo") or "").strip()
        if bloqueo:
            return bloqueo
    return (estilo.personaje_por_defecto or "").strip()


def armar(plantilla: str, estilo: Estilo, personaje: str, descripcion: str, **campos: str) -> str:
    valores = _Faltantes(bloque_estilo=estilo.bloque_estilo, personaje=personaje,
                         descripcion=(descripcion or "").strip().rstrip("."), **campos)
    return _limpiar(plantilla.format_map(valores))


def prompt_de_escena(escena: Escena, estilo: Estilo, personaje: str) -> str:
    tipo = estilo.tipo(escena.visual.tipo)
    if tipo is None:
        raise ValueError(f"escena {escena.id}: el tipo '{escena.visual.tipo}' no existe en el estilo '{estilo.id}'")
    return armar(tipo.plantilla_prompt, estilo, personaje, escena.visual.prompt or escena.narracion)


def usa_personaje(escena: Escena, estilo: Estilo) -> bool:
    tipo = estilo.tipo(escena.visual.tipo)
    return bool(tipo) and "personaje" in variables_de(tipo.plantilla_prompt)


def prompt_de_asset(asset: AssetDef, estilo: Estilo, personaje: str) -> str:
    plantilla = estilo.plantillas_assets.get(asset.tipo) or estilo.plantillas_assets.get("_defecto")
    if not plantilla:
        raise ValueError(f"el estilo '{estilo.id}' no tiene plantilla para assets de tipo '{asset.tipo}'")
    return armar(plantilla, estilo, personaje, asset.prompt or "")
