"""Mascota disfrazada del animal del video (idea del dueño, opción A).

Una sola imagen por video: la mascota del canal con un hoodie de capota del animal del tema
(misma cara, mismo trazo). Esa imagen reemplaza a la mascota SOLO en este video, así que todas las
escenas nuevas con la mascota salen disfrazadas. Las reacciones guardadas del canal quedan igual.
Se prepara antes de la primera imagen del video (el costo, ~1 imagen, pasa por el mismo freno).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import ConfigCostos, escribir_json, leer_json
from .proyecto import CarpetaProyecto

MARCA = "assets/disfraz.json"


def _tema(c: CarpetaProyecto, ejecutar) -> str:
    """El animal del disfraz, en inglés y corto (lo decide Claude con la suscripción: no cuesta)."""
    from . import claude_cli

    p = c.cargar()
    esc = c.cargar_escenas() if c.archivo_escenas.exists() else None
    niveles = ", ".join(n.nombre for n in esc.niveles) if esc and esc.niveles else ""
    pedido = (f"Video de YouTube: «{p.titulo}». Niveles: {niveles or 'no hay'}.\n"
              "¿De qué animal debería ser el disfraz (un hoodie con capota) de la mascota? Si el video trata de "
              "un solo tipo de animal, ese; si mezcla varios, el más representativo del título. Responde SOLO un "
              'JSON: {"animal": "<2 a 4 palabras en inglés, p. ej. poison dart frog>"}')
    texto, _ = (ejecutar or claude_cli.ejecutar)(pedido, tiempo_max_s=180)
    datos = claude_cli.extraer_json(texto) or {}
    animal = str(datos.get("animal") or "").strip()
    if not animal or len(animal) > 40:
        raise RuntimeError("Claude no dijo de qué animal hacer el disfraz")
    return animal


def descripcion(animal: str) -> str:
    return (f"The same character wearing an oversized cozy {animal} hoodie with the hood up: the hood is shaped like "
            f"a cute {animal} head with its eyes on top, with the colors and markings of the {animal}; the rest of the "
            "hoodie in the same colors, dark pants. The face, head shape, proportions, outlines and drawing style of "
            "the character stay exactly the same as the reference. Full body, front view, friendly expression.")


def preparar(c: CarpetaProyecto, proveedor, config: ConfigCostos | None = None, permiso: bool = False,
             ejecutar=None, avisar=print) -> dict | None:
    """Hace el disfraz si el video lo pide y todavía no está. Idempotente: la segunda vez no gasta."""
    p = c.cargar()
    if not p.disfraz_mascota:
        return None
    marca = c.ruta / MARCA
    if marca.exists():
        return leer_json(marca)
    from .estilos import cargar_estilo
    from .imagenes import prompts

    config = config or ConfigCostos.cargar()
    estilo = cargar_estilo(p.estilo)
    base = c.ruta / "assets" / "mascota_base.png"
    original = c.ruta / "assets" / "mascota_original.png"
    if not base.exists() and not original.exists():
        avisar("Este video no tiene mascota: sin disfraz")
        return None
    if not original.exists():
        shutil.copy(base, original)                      # la del canal queda guardada al lado
    animal = p.disfraz_tema or _tema(c, ejecutar)
    avisar(f"Vistiendo a la mascota con un hoodie de {animal}…")
    personaje = prompts.personaje_del_proyecto(c.ruta, estilo)
    plantilla = estilo.plantillas_assets.get("pose") or estilo.plantillas_assets.get("personaje") or "{personaje}. {descripcion}"
    prompt = prompts.armar(plantilla, estilo, personaje, descripcion(animal))
    libro = c.libro(config)
    libro.autorizar(proveedor.estimar_usd(prompt, [original]), permiso=permiso)
    r = proveedor.generar(prompt, [original])
    libro.registrar(modulo="disfraz", proveedor=r.proveedor, modelo=r.modelo, unidades={"imagenes": 1},
                    costo_usd=r.uso.costo_usd, detalle=animal)
    base.write_bytes(r.png)
    # el personaje del video lleva el hoodie (las escenas lo piden así) y la mascota nueva se adopta
    # como referencia sin volver a pagarla
    perfil_ruta = c.ruta / "perfil_canal.json"
    perfil = leer_json(perfil_ruta) if perfil_ruta.exists() else {}
    bloqueo = ((perfil.get("personaje") or {}).get("bloqueo") or personaje).rstrip(". ")
    perfil.setdefault("personaje", {})["bloqueo"] = (f"{bloqueo}, wearing a {animal} hoodie with the hood up "
                                                     f"(the hood shaped like a {animal} head)")
    escribir_json(perfil_ruta, perfil)
    man_ruta = c.ruta / "imagenes" / "manifiesto.json"
    if man_ruta.exists():
        man = leer_json(man_ruta)
        man.pop("asset:mascota_base", None)
        escribir_json(man_ruta, man)
    if not p.disfraz_tema:
        p = c.cargar()
        p.disfraz_tema = animal
        c.guardar(p)
    info = {"animal": animal, "costo_usd": r.uso.costo_usd, "original": str(original.relative_to(c.ruta))}
    marca.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    avisar(f"Mascota disfrazada de {animal}: las escenas con la mascota la usan en este video")
    return info
