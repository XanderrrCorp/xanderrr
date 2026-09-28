"""Paso 2: Gemini dibuja CADA sujeto por separado, sobre blanco, con 2-3 referencias
de estilo del canal.

Gemini 2.5 Flash Image funciona mejor con máximo 3 imágenes de entrada (documentación
de Google). En Together se cobra por imagen generada (~0,039 USD de lista; la factura
da ~0,044 con referencias: cada imagen de entrada son unos pocos tokens a 0,30 USD el
millón). El modelo entrega ~1 megapíxel: el protagonista no puede salir a más resolución,
por eso se escala desde 1024x1024 igual que los demás.
"""
from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .plan import Celda, Plan
from .plantilla import Plantilla, referencias_activas

CIERRE = ("Single subject, huge, fills the frame, centered, isolated on a pure flat white background, NO text, "
          "NO letters, NO borders, NO frames, NO shadows on the background.")
CIERRE_ESCENA = ("Single subject, huge, fills the frame, centered, the scene fills the whole image edge to edge (no "
                 "white background), NO text, NO letters, NO borders, NO frames.")
CON_REFERENCIAS = ("Match the illustration style, line art, shading and color palette of the reference images. "
                   "Do NOT copy their composition, animals or any text.")
LADO = 1024
_CERROJO = threading.Lock()


def prompt(plan: Plan, celda: Celda, plantilla: Plantilla, extra: str = "", con_referencias: bool = True) -> str:
    partes = [plantilla.bloque_estilo, celda.scene.strip().rstrip(".") + "."]
    if plan.hook_mode == "scene" and plan.hook_visual:
        partes.append(f"The same visual hook is part of the subject and must be fully visible: {plan.hook_visual}.")
    if celda.is_hero and plan.hero_censor:
        partes.append("Show a visible fresh bite wound or bloody mark near the animal's mouth or on its prey.")
    if extra.strip():
        partes.append(extra.strip())
    partes.append(CIERRE_ESCENA if plan.hook_mode == "scene" else CIERRE)
    if con_referencias:
        partes.append(CON_REFERENCIAS)
    return " ".join(partes)


def _nombre(celda: Celda) -> str:
    return re.sub(r"[^a-z0-9]+", "_", celda.name.lower()).strip("_")[:30] or "sujeto"


def crear_proveedor():
    from ..config import ConfigCostos, leer_config
    from ..imagenes.proveedores import crear_proveedor as crear

    p = crear(ConfigCostos.cargar(), leer_config("proveedores.json")["imagenes"])
    if hasattr(p, "ancho"):
        p.ancho = p.alto = LADO                 # sujetos cuadrados: se recortan mejor que en 16:9
    return p


def costo_por_imagen(proveedor=None) -> float:
    proveedor = proveedor or crear_proveedor()
    return float(proveedor.estimar_usd("x", []))


def generar(carpeta: Path, plan: Plan, plantilla: Plantilla, indices: list[int], libro, proveedor=None,
            extras: dict[int, str] | None = None, permiso: bool = False, avisar=print,
            elegir: bool = True) -> dict[int, str]:
    """Genera (en paralelo) una imagen nueva para cada celda pedida. Frena ANTES de gastar si el
    total pasa el máximo del video. Devuelve {indice: archivo}."""
    from ..imagenes.proveedores import ErrorProveedor

    proveedor = proveedor or crear_proveedor()
    refs = referencias_activas(plantilla)
    extras = extras or {}
    pedidos = {i: prompt(plan, plan.cells[i], plantilla, extras.get(i, ""), bool(refs)) for i in indices}
    libro.autorizar(sum(proveedor.estimar_usd(p, refs) for p in pedidos.values()), permiso=permiso)
    (carpeta / "sujetos").mkdir(parents=True, exist_ok=True)

    def uno(i: int) -> tuple[int, str]:
        celda = plan.cells[i]
        for intento in range(3):
            try:
                r = proveedor.generar(pedidos[i], refs)
                break
            except ErrorProveedor as ex:
                if not ex.reintentable or intento == 2:
                    raise
                time.sleep(3 * (intento + 1))
        with _CERROJO:
            libro.registrar(modulo="miniatura", proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                            costo_usd=r.uso.costo_usd, detalle=f"miniatura escala · {celda.name}")
            k = len(celda.variantes) + 1
            archivo = f"sujetos/{_nombre(celda)}_{k}.png"
            while (carpeta / archivo).exists():
                k += 1
                archivo = f"sujetos/{_nombre(celda)}_{k}.png"
            (carpeta / archivo).write_bytes(r.png)
            celda.variantes.append(archivo)
            if elegir:
                celda.archivo = archivo
        avisar(f"  listo: {celda.name}")
        return i, archivo

    with ThreadPoolExecutor(max_workers=min(6, len(indices)) or 1) as ex:
        return dict(ex.map(uno, indices))
