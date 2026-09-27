"""Paso 1: Claude planifica la miniatura en JSON y aquí se valida la fórmula."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .. import claude_cli
from .plantilla import Plantilla

MAX_LABEL = 20


class Ajuste(BaseModel):
    """Ajuste manual desde la interfaz: escala relativa y desplazamiento en píxeles del lienzo."""
    model_config = ConfigDict(extra="forbid")
    escala: float = Field(1.0, ge=0.4, le=2.5)
    dx: int = 0
    dy: int = 0


class Celda(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    label: str
    scene: str
    is_hero: bool = False
    # estado de producción (lo llena el código, no Claude)
    archivo: str | None = None                     # imagen generada elegida (sobre blanco)
    variantes: list[str] = []                      # todas las generadas para esta celda
    intentos_qa: int = 0
    ajuste: Ajuste = Field(default_factory=Ajuste)

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("label vacío")
        return v[:MAX_LABEL]


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scale_type: str
    hook_mode: Literal["isolated", "scene"] = "isolated"
    hook_visual: str | None = None
    cells: list[Celda]
    hero_text: str
    hero_icon: str
    hero_glow_color: str = "#FF1A1A"
    hero_censor: bool = False
    # caja de la herida en la imagen del protagonista (0..1), la ubica Claude con visión
    hero_censor_box: list[float] | None = None

    @field_validator("hero_text")
    @classmethod
    def _hero_text(cls, v: str) -> str:
        v = " ".join(v.split()).upper()
        if not 2 <= len(v.split()) <= 5:
            raise ValueError("hero_text debe tener de 2 a 5 palabras")
        return v

    @field_validator("hero_glow_color")
    @classmethod
    def _color(cls, v: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError("hero_glow_color debe ser #RRGGBB")
        return v.upper()

    @model_validator(mode="after")
    def _formula(self) -> "Plan":
        if len(self.cells) != 6:
            raise ValueError(f"la escala 2x3 lleva 6 sujetos (hay {len(self.cells)})")
        heroes = [i for i, c in enumerate(self.cells) if c.is_hero]
        if heroes != [0]:
            raise ValueError("debe haber exactamente un protagonista y va primero (arriba a la izquierda)")
        nombres = [c.name.strip().lower() for c in self.cells]
        if len(set(nombres)) != 6:
            raise ValueError("no se pueden repetir animales")
        if self.hook_mode == "scene" and not (self.hook_visual or "").strip():
            raise ValueError("en modo scene hace falta hook_visual")
        return self


def instruccion(tema: str, plantilla: Plantilla, guion: str = "", niveles: list[str] | None = None) -> str:
    iconos = ", ".join(plantilla.iconos_permitidos)
    resumen = ("Guion (resumen):\n" + guion[:3500]) if guion else ""
    lista = ("\nAnimales del video (úsalos, del más extremo al más inofensivo o sorprendente):\n- "
             + "\n- ".join(niveles)) if niveles else ""
    return f"""Planifica la miniatura de YouTube de un video de formato «escala» (6 animales ordenados en una escala).
Tema del video: {tema}{lista}
{resumen}

FÓRMULA DEL FORMATO (siempre):
- Lienzo 1280x720 en blanco, 6 sujetos recortados en 2x3. Sin marcos ni celdas. Todo en español.
- Arriba a la izquierda va el PROTAGONISTA (el extremo más impactante): más grande, con aura de color y un ícono.
  Debajo, hero_text en rojo: 2 a 5 palabras en MAYÚSCULAS que generen curiosidad («¡NO TE METAS AL AGUA!», «TE
  ENGAÑA», «NO ESCAPAS», «TE DOMINARÍA»). Puede ser una paradoja: el protagonista parece inofensivo y es el peor.
- Los otros 5 van en orden hacia el extremo contrario; el ÚLTIMO (abajo a la derecha) rompe el patrón: tierno,
  inofensivo o sorprendente.
- Sujetos ENORMES, de 3/4 o de frente mirando a la cámara, con pose o expresión amenazante (boca abierta,
  colmillos, lengua fuera, garras), salvo el último.
- Animales visualmente distintos entre sí (no tres serpientes marrones iguales). Sin repetir animales.

DECIDE:
- scale_type: qué mide la escala (peligro, engaño, inteligencia, probabilidad de sobrevivir, dolor de la
  picadura…), deducido del tema.
- hook_mode: "isolated" (animal solo; el gancho es la pose) o "scene" (el MISMO gancho visual repetido en los 6,
  ej. «biting a human forearm», «human legs dangling in murky river water»; ese elemento se recorta con el animal).
- hook_visual: el gancho en inglés si hook_mode es "scene"; si no, null.
- cells: 6 en orden (el primero es el protagonista, is_hero true; los demás false). Cada uno:
  name (nombre interno), label (texto visible, máximo {MAX_LABEL} caracteres: normalmente el nombre del animal en
  español, o una frase corta que cuente la historia si el tema lo pide, ej. «Casi del 0 %», «Nos mentiría»),
  scene (en inglés: el animal, pose, expresión y el gancho si aplica; sin fondo, sin texto).
- hero_text, hero_icon (uno de: {iconos}), hero_glow_color (#FF1A1A por defecto; amarillo o azul eléctrico si
  el tema lo pide, ej. anguila eléctrica) y hero_censor (true si el protagonista debe mostrar una herida o
  mordida que se censura con pixelado para dar curiosidad).

Responde SOLO un JSON así:
{{"scale_type": "...", "hook_mode": "isolated", "hook_visual": null, "cells": [{{"name": "...", "label": "...",
"scene": "...", "is_hero": true}}, ...], "hero_text": "...", "hero_icon": "...", "hero_glow_color": "#FF1A1A",
"hero_censor": false}}"""


def planificar(tema: str, plantilla: Plantilla, guion: str = "", niveles: list[str] | None = None,
               ejecutar=claude_cli.ejecutar, cwd=None, intentos: int = 3) -> Plan:
    """Pide el plan a Claude y lo valida; si no cumple la fórmula, le devuelve el error."""
    pedido = instruccion(tema, plantilla, guion, niveles)
    error = ""
    for _ in range(intentos):
        texto, _uso = ejecutar(pedido + (f"\n\nTu respuesta anterior no sirvió: {error}. Corrígelo." if error else ""),
                               cwd=cwd)
        datos = claude_cli.extraer_json(texto) or {}
        try:
            celdas = datos.get("cells") or []
            # el protagonista siempre primero, aunque Claude lo ponga en otro lado
            celdas.sort(key=lambda c: not (isinstance(c, dict) and c.get("is_hero")))
            if datos.get("hero_icon") not in plantilla.iconos_permitidos:
                datos["hero_icon"] = plantilla.iconos_permitidos[0]
            datos.setdefault("hero_glow_color", plantilla.color_aura_por_defecto)
            permitidos = set(Plan.model_fields)
            return Plan.model_validate({k: v for k, v in datos.items() if k in permitidos})
        except (ValueError, TypeError) as ex:
            error = str(ex)[:400]
    raise claude_cli.ErrorClaude(f"Claude no devolvió un plan válido: {error}")
