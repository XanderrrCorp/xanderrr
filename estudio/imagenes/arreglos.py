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


# Cambios que el dueño pidió y que SÍ cambian cómo se ve la imagen (no cuentan como «la misma de antes»).
CAMBIOS_DE_ESTILO: list[tuple[str, str]] = [
    # Paradoja Sapiens (30-09): no quiso el fondo turquesa, papel claro como el de los peces del Amazonas
    ("Dark flat teal-blue background with a few pale sketchy pencil lines",
     "Light cream paper background with a few faint sketchy pencil lines"),
]
# Ajustes de campos por estilo (se aplican a la copia de cada espacio y a la de la base)
# (01-10) los dos canales stickman pasan a la hoja blanca cuadriculada, como los ejemplos del dueño
CUADRICULA = {"tipo": "cuadricula", "valor": "assets/papel_arrugado.png"}
CAMPOS: dict[str, dict] = {
    # (03-10) logo de Peligro Tropical abajo a la derecha en todo el video, como la competencia
    # y la edición de la competencia: entradas deslizándose, sin vaivén, títulos negros (perfil propio)
    "enciclopedia_mascota": {"fondo_montaje": CUADRICULA, "marca_agua": "assets/canal/marca_agua.png",
                             "perfil_edicion": "perfiles/peligro_tropical.json", "titulo": "negro"},
    "paradoja_sapiens": {"fondo_montaje": CUADRICULA,
                         # (04-10) edición de historia: pantalla completa con zoom, capítulos y viñeta
                         "movimiento_maximo": 0.05, "perfil_edicion": "perfiles/paradoja_historia.json"},
}


def texto_corregido(texto: str) -> str:
    for viejo, nuevo in REEMPLAZOS + CAMBIOS_DE_ESTILO:
        texto = texto.replace(viejo, nuevo)
    return texto


def _con_campos(clave: str, datos: dict) -> dict:
    return _con_tipos_nuevos(clave, {**datos, **CAMPOS.get(clave, {})})


def _con_tipos_nuevos(clave: str, datos: dict) -> dict:
    """Los tipos de escena que el estilo del código ganó después (p. ej. la pizarra y los rayos X de
    Peligro Tropical, 03-10) se agregan a la copia del espacio, con su modo de montaje. Nunca se
    cambia ni se borra un tipo que ya estaba."""
    from ..config import RAIZ

    ruta = RAIZ / "estilos" / clave / "estilo.json"
    if not clave or not ruta.exists() or "tipos_de_escena" not in datos:
        return datos
    codigo = json.loads(ruta.read_text(encoding="utf-8"))
    ids = {t.get("id") for t in datos["tipos_de_escena"]}
    nuevos = [t for t in codigo.get("tipos_de_escena", []) if t.get("id") not in ids]
    if not nuevos:
        return datos
    salida = {**datos, "tipos_de_escena": datos["tipos_de_escena"] + nuevos}
    modos = list(datos.get("modos_de_montaje_permitidos") or [])
    comp = dict(datos.get("comportamiento_montaje") or {})
    for t in nuevos:
        m = t.get("modo_montaje")
        if m and m not in modos:
            modos.append(m)
        if m and m not in comp and m in (codigo.get("comportamiento_montaje") or {}):
            comp[m] = codigo["comportamiento_montaje"][m]
    salida["modos_de_montaje_permitidos"], salida["comportamiento_montaje"] = modos, comp
    return salida


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
        datos = json.loads(nuevo)                          # que siga siendo JSON válido
        con_campos = _con_campos(f.parent.name, datos)
        if con_campos != datos:
            nuevo = json.dumps(con_campos, ensure_ascii=False, indent=2) + "\n"
        if nuevo == texto:
            continue
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
        nuevo = json.loads(texto_corregido(texto))
        nuevo = _con_campos(getattr(e, "clave", "") or nuevo.get("id", ""), nuevo)
        if nuevo != (e.datos or {}):
            e.datos = nuevo
            n += 1
    return n
