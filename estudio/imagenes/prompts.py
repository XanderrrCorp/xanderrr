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
    """Solo arregla lo que deja una variable vacía (espacios dobles, «. .», «, ,»).
    Un prompt completo sale intacto: la plantilla del estilo es la fuente exacta."""
    t = re.sub(r"\s+", " ", texto).strip()
    t = re.sub(r"\s+([.,])", r"\1", t)
    t = re.sub(r"\.(\s*\.)+", ".", t)
    t = re.sub(r",(\s*,)+", ",", t)
    t = re.sub(r"^[\s,.]+", "", t)
    return t if t.endswith(".") else t + "."


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
                         descripcion=(descripcion or "").strip(), **campos)
    return _limpiar(plantilla.format_map(valores))


def descomponer(prompt: str, plantilla: str, estilo: Estilo, personaje: str) -> str | None:
    """Lo inverso de `armar`: si `prompt` es esta plantilla con algo en
    {descripcion}, devuelve ese algo; si no encaja EXACTO, None."""
    if plantilla.count("{descripcion}") != 1:
        return None
    pre, suf = plantilla.split("{descripcion}")
    valores = _Faltantes(bloque_estilo=estilo.bloque_estilo, personaje=personaje)
    pre, suf = pre.format_map(valores), suf.format_map(valores)
    if not (prompt.startswith(pre) and prompt.endswith(suf) and len(prompt) > len(pre) + len(suf)):
        return None
    medio = prompt[len(pre):len(prompt) - len(suf)]
    return medio if armar(plantilla, estilo, personaje, medio) == prompt else None


def prompt_de_escena(escena: Escena, estilo: Estilo, personaje: str) -> str:
    if escena.visual.prompt_literal:
        return escena.visual.prompt or ""
    tipo = estilo.tipo(escena.visual.tipo)
    if tipo is None:
        raise ValueError(f"escena {escena.id}: el tipo '{escena.visual.tipo}' no existe en el estilo '{estilo.id}'")
    descripcion = escena.visual.prompt or escena.narracion
    if HUMANO.search(descripcion) and "{personaje}" not in tipo.plantilla_prompt:
        # las plantillas de animales hablan de «placas del exoesqueleto» y brillos: con piernas o
        # manos humanas Gemini dibujaba un robot negro. Solo cambia el prompt de esas escenas.
        descripcion = descripcion.rstrip(". ") + ". " + PERSONA_NORMAL
    return armar(tipo.plantilla_prompt, estilo, personaje, descripcion)


HUMANO = re.compile(r"\b(legs?|feet|foot|ankles?|knees?|toes?|hands?|arms?|fingers?|skin|person|people|human|man|"
                    r"woman|swimmer|fisherman|child|boy|girl|bather)\b", re.IGNORECASE)
PERSONA_NORMAL = ("Any human body part is an ordinary real person with natural skin tone and normal casual clothes "
                  "(for example rolled-up jeans or shorts); never armor, never a robot, never a black suit or "
                  "shiny plates on the human.")


def usa_personaje(escena: Escena, estilo: Estilo) -> bool:
    tipo = estilo.tipo(escena.visual.tipo)
    return bool(tipo) and "personaje" in variables_de(tipo.plantilla_prompt)


def prompt_de_asset(asset: AssetDef, estilo: Estilo, personaje: str) -> str:
    if asset.prompt_literal:
        return asset.prompt or ""
    plantilla = estilo.plantillas_assets.get(asset.tipo) or estilo.plantillas_assets.get("_defecto")
    if not plantilla:
        raise ValueError(f"el estilo '{estilo.id}' no tiene plantilla para assets de tipo '{asset.tipo}'")
    return armar(plantilla, estilo, personaje, asset.prompt or "")
