"""Ropa del muñeco que cambia de un video a otro (Peligro Tropical v4, aprobado por el dueño el 07-11).

Diseños PROPIOS del canal (nada de la ropa del personaje de la competencia: ni gorra negra al revés con hoodie gris, ni
gorro con cadena dorada, ni gorra y chaqueta rojas). Uno de ellos es la ropa de siempre (no cuesta nada).

Cómo funciona (igual que el disfraz del animal, disfraz.py): antes de la primera imagen del video se elige un vestuario
que no se haya usado en los últimos 3 videos; la mascota del video (assets/mascota_base.png) se cambia por la misma
mascota con esa ropa y todas las escenas nuevas con la mascota la usan. Cada vestuario se dibuja UNA sola vez por
mascota (≈ 1 imagen, con el freno de gasto) y se guarda en datos/pt_vestuarios/: los videos siguientes lo reusan gratis.
Las reacciones guardadas del canal (poses) quedan con la ropa de siempre.

Solo en videos cuya fórmula trae "vestuarios": true (escala_peligro_v3) y sin disfraz del animal. Un video que ya tiene
imágenes hechas no cambia de ropa (quedaría mezclada).
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

from .config import ConfigCostos, escribir_json, leer_json
from .proyecto import CarpetaProyecto

MARCA = "assets/vestuario.json"
RECORDAR = 3

# id → (nombre para el dueño, descripción para Google). «clasico» = la ropa de siempre.
VESTUARIOS: dict[str, tuple[str, str | None]] = {
    "clasico": ("La de siempre", None),
    "safari": ("Chaleco de safari", "an olive-green safari vest with many pockets over a cream short-sleeve shirt, an "
                                    "olive bucket hat, small binoculars hanging on a strap around the neck, beige "
                                    "cargo shorts and brown hiking boots"),
    "lluvia": ("Impermeable amarillo", "a bright yellow raincoat with the hood down, dark green rubber boots, a small "
                                       "flashlight clipped to the chest strap and dark blue pants"),
    "noche": ("Explorador de noche", "a dark navy field jacket with rolled-up sleeves, a headlamp strapped on the "
                                     "forehead, a small orange backpack, grey cargo pants and black boots"),
    "biologo": ("Bata de biólogo", "an open white lab coat over a teal t-shirt, a magnifying glass in the coat pocket, "
                                   "a clipboard under one arm, dark jeans and white sneakers"),
}


def _historial() -> Path:
    from .plataforma.db import carpeta_datos

    return carpeta_datos() / "pt_vestuarios.json"


def _cache(base: Path) -> Path:
    from .plataforma.db import carpeta_datos

    huella = hashlib.sha1(base.read_bytes()).hexdigest()[:12]      # otra mascota → otros dibujos
    return carpeta_datos() / "pt_vestuarios" / huella


def activo(c: CarpetaProyecto) -> bool:
    p = c.cargar()
    if p.disfraz_mascota or not p.formula:
        return False
    from .guionista import cargar_formula

    try:
        return bool(cargar_formula(p.formula).get("vestuarios"))
    except Exception:  # noqa: BLE001 — una fórmula que ya no existe: sin vestuario
        return False


def elegir(c: CarpetaProyecto, rng: random.Random | None = None) -> str:
    """El vestuario de ESTE video (queda en estilo_video.json junto a la escala y el letrero)."""
    propio = c.ruta / "estilo_video.json"
    d = {}
    if propio.exists():
        try:
            d = json.loads(propio.read_text("utf-8"))
        except (OSError, ValueError):
            d = {}
    if d.get("vestuario") in VESTUARIOS:
        return d["vestuario"]
    ruta = _historial()
    try:
        hist = json.loads(ruta.read_text("utf-8")) if ruta.exists() else []
    except (OSError, ValueError):
        hist = []
    recientes = [h.get("vestuario") for h in hist[-RECORDAR:]]
    opciones = [v for v in VESTUARIOS if v not in recientes] or list(VESTUARIOS)
    elegido = (rng or random.Random(c.cargar().semilla)).choice(opciones)
    d["vestuario"] = elegido
    propio.write_text(json.dumps(d, ensure_ascii=False), "utf-8")
    hist.append({"vestuario": elegido, "video": c.ruta.name})
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(hist[-30:], ensure_ascii=False, indent=1), "utf-8")
    except OSError:
        pass
    return elegido


def pendiente_de_pago(c: CarpetaProyecto) -> bool:
    """¿Este video va a pagar una imagen por la ropa? (para el costo que se muestra antes)"""
    if not activo(c) or (c.ruta / MARCA).exists():
        return False
    base = c.ruta / "assets" / "mascota_base.png"
    if not base.exists():
        return False
    v = elegir(c)
    return VESTUARIOS[v][1] is not None and not (_cache(base) / f"{v}.png").exists()


def preparar(c: CarpetaProyecto, proveedor, config: ConfigCostos | None = None, permiso: bool = False,
             avisar=print) -> dict | None:
    if not activo(c):
        return None
    marca = c.ruta / MARCA
    if marca.exists():
        return leer_json(marca)
    base = c.ruta / "assets" / "mascota_base.png"
    man_ruta = c.ruta / "imagenes" / "manifiesto.json"
    man = leer_json(man_ruta) if man_ruta.exists() else {}
    if not base.exists() or any(k.startswith("escena:") for k in man):
        info = {"vestuario": "clasico", "razon": "sin mascota o con imágenes ya hechas"}
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(json.dumps(info, ensure_ascii=False), "utf-8")
        return info
    v = elegir(c)
    nombre, ropa = VESTUARIOS[v]
    if ropa is None:
        info = {"vestuario": v, "costo_usd": 0.0}
        marca.write_text(json.dumps(info, ensure_ascii=False), "utf-8")
        avisar(f"Ropa del muñeco en este video: {nombre.lower()}")
        return info
    original = c.ruta / "assets" / "mascota_original.png"
    if not original.exists():
        shutil.copy(base, original)                      # la del canal queda guardada al lado
    guardado = _cache(original) / f"{v}.png"
    costo = 0.0
    if guardado.exists():
        base.write_bytes(guardado.read_bytes())
        avisar(f"Ropa del muñeco en este video: {nombre.lower()} (ya estaba dibujada: gratis)")
    else:
        from .estilos import cargar_estilo
        from .imagenes import prompts

        config = config or ConfigCostos.cargar()
        estilo = cargar_estilo(c.cargar().estilo)
        personaje = prompts.personaje_del_proyecto(c.ruta, estilo)
        plantilla = estilo.plantillas_assets.get("pose") or estilo.plantillas_assets.get("personaje") or "{personaje}. {descripcion}"
        descripcion = (f"The same character, but in this picture he wears: {ropa}. The face, head shape, skin color, "
                       "proportions, outlines and drawing style stay exactly the same as the reference; only the clothes "
                       "and hat change. Full body, front view, friendly expression.")
        prompt = prompts.armar(plantilla, estilo, personaje, descripcion)
        libro = c.libro(config)
        libro.autorizar(proveedor.estimar_usd(prompt, [original]), permiso=permiso)
        avisar(f"Vistiendo al muñeco: {nombre.lower()} (una imagen, solo la primera vez)…")
        r = proveedor.generar(prompt, [original])
        libro.registrar(modulo="vestuario", proveedor=r.proveedor, modelo=r.modelo, unidades={"imagenes": 1},
                        costo_usd=r.uso.costo_usd, detalle=v)
        base.write_bytes(r.png)
        guardado.parent.mkdir(parents=True, exist_ok=True)
        guardado.write_bytes(r.png)
        costo = r.uso.costo_usd
    # las escenas piden al muñeco con esta ropa y la mascota nueva es la referencia (sin volver a pagarla)
    perfil_ruta = c.ruta / "perfil_canal.json"
    perfil = leer_json(perfil_ruta) if perfil_ruta.exists() else {}
    from .estilos import cargar_estilo
    from .imagenes import prompts

    bloqueo = ((perfil.get("personaje") or {}).get("bloqueo")
               or prompts.personaje_del_proyecto(c.ruta, cargar_estilo(c.cargar().estilo))).rstrip(". ")
    perfil.setdefault("personaje", {})["bloqueo"] = (f"{bloqueo}. IN THIS VIDEO he wears instead: {ropa} (this replaces "
                                                     "any clothes or hat described before)")
    escribir_json(perfil_ruta, perfil)
    if man_ruta.exists():
        man.pop("asset:mascota_base", None)
        escribir_json(man_ruta, man)
    info = {"vestuario": v, "costo_usd": costo, "original": str(original.relative_to(c.ruta))}
    marca.write_text(json.dumps(info, ensure_ascii=False), "utf-8")
    return info
