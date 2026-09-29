"""Correcciones a las plantillas de estilo que ya viven copiadas en cada espacio de trabajo.

La plantilla de animales venía del video de alacranes y pedía «visible texture on every plate of the
exoskeleton» en TODAS las imágenes: lobos, perros o tiburones salían con placas de armadura. El
arreglo cambia esa frase en los estilos del espacio (solo la frase exacta, nada más) y el generador
reconoce las imágenes ya pagadas con la frase vieja como iguales: no se vuelven a pagar.
"""
from __future__ import annotations

import json
from pathlib import Path

REEMPLAZOS: list[tuple[str, str]] = [
    ("rich painterly shading with visible texture on every plate of the exoskeleton, glossy highlights, "
     "natural anatomical proportions",
     "rich painterly shading, the real natural texture of this exact animal (fur, feathers, skin, scales or "
     "shell only where the real species has them), anatomically faithful to the real species, never armor "
     "plates or armored segments unless the real animal has them, natural anatomical proportions"),
]


def texto_corregido(texto: str) -> str:
    for viejo, nuevo in REEMPLAZOS:
        texto = texto.replace(viejo, nuevo)
    return texto


def prompt_anterior(prompt: str) -> str | None:
    """El mismo prompt como se escribía antes del arreglo (None si el arreglo no lo tocó)."""
    antes = prompt
    for viejo, nuevo in REEMPLAZOS:
        antes = antes.replace(nuevo, viejo)
    return antes if antes != prompt else None


def corregir_estilos(carpeta_datos: Path) -> list[Path]:
    """Aplica los reemplazos a cada estilo.json de los espacios (y deja copia del original)."""
    tocados = []
    for f in sorted((carpeta_datos / "espacios").glob("*/estilos/*/estilo.json")):
        texto = f.read_text(encoding="utf-8")
        nuevo = texto_corregido(texto)
        if nuevo == texto:
            continue
        json.loads(nuevo)                                  # que siga siendo JSON válido
        respaldo = f.with_name("estilo.antes_del_arreglo.json")
        if not respaldo.exists():
            respaldo.write_text(texto, encoding="utf-8")
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(nuevo, encoding="utf-8")
        tmp.replace(f)
        tocados.append(f)
    return tocados


def corregir_base(s) -> int:
    """Lo mismo en la copia de los estilos que guarda la base de datos."""
    from sqlalchemy import select

    from ..plataforma.modelos import Estilo

    n = 0
    for e in s.scalars(select(Estilo)):
        texto = json.dumps(e.datos or {}, ensure_ascii=False)
        nuevo = texto_corregido(texto)
        if nuevo != texto:
            e.datos = json.loads(nuevo)
            n += 1
    return n
