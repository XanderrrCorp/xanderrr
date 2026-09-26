"""Poses del personaje del canal (5.3: los assets se reutilizan).

Cada pose del catálogo `poses_canal` de estilo.json se genera UNA sola vez, con la
mascota base como referencia para que sea el mismo personaje, y queda guardada en
`estilos/<estilo>/assets/poses/`. Cada video nuevo las copia gratis a su carpeta.
El gasto queda en `estilos/<estilo>/assets/poses/logs/costos.jsonl` con el mismo
freno en pesos que los videos.
"""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config import ConfigCostos, escribir_json, formato_cop, leer_config, leer_json
from .costos import FrenoPresupuesto, LibroCostos
from .estilos import cargar_estilo, carpeta_estilos
from .imagenes import prompts
from .imagenes.proveedores import ErrorProveedor, crear_proveedor


def carpeta(estilo_id: str) -> Path:
    return carpeta_estilos() / estilo_id / "assets" / "poses"


def indice(estilo_id: str) -> dict:
    r = carpeta(estilo_id) / "poses.json"
    return leer_json(r) if r.exists() else {}


def _huella(prompt: str, modelo: str, referencia: Path) -> str:
    h = hashlib.sha256(f"{modelo}|{prompt}".encode())
    h.update(hashlib.sha256(referencia.read_bytes()).digest())
    return h.hexdigest()[:16]


def generar_poses(estilo_id: str, ids: list[str] | None = None, *, permiso: bool = False,
                  nombre_proveedor: str | None = None, avisar=print) -> dict:
    """Genera las poses que falten (o las pedidas). Las que ya están no se vuelven a pagar."""
    estilo = cargar_estilo(estilo_id)
    base = carpeta_estilos() / estilo_id / "assets" / "mascota_base.png"
    if not base.exists():
        raise FileNotFoundError("falta la mascota base del canal (assets/mascota_base.png)")
    plantilla = estilo.plantillas_assets.get("pose")
    if not plantilla:
        raise ValueError(f"el estilo '{estilo_id}' no tiene plantilla de pose (plantillas_assets.pose)")
    config = ConfigCostos.cargar()
    ajustes = leer_config("proveedores.json")["imagenes"]
    proveedor = crear_proveedor(config, ajustes, nombre_proveedor)
    destino = carpeta(estilo_id)
    destino.mkdir(parents=True, exist_ok=True)
    libro = LibroCostos(destino, config)
    idx = indice(estilo_id)
    salida = {"generadas": [], "ya_estaban": [], "fallidas": {}, "costo_cop": 0.0}
    for pose in estilo.poses_canal:
        if ids and pose.id not in ids:
            continue
        prompt = prompts.armar(plantilla, estilo, estilo.personaje_por_defecto or "", pose.descripcion)
        huella = _huella(prompt, proveedor.modelo, base)
        archivo = destino / f"{pose.id}.png"
        if idx.get(pose.id, {}).get("huella") == huella and archivo.exists():
            salida["ya_estaban"].append(pose.id)
            continue
        try:
            libro.autorizar(proveedor.estimar_usd(prompt, [base]), permiso=permiso)
        except FrenoPresupuesto as ex:
            salida["fallidas"][pose.id] = str(ex)
            break
        avisar(f"Generando la pose «{pose.id}»…")
        try:
            res = proveedor.generar(prompt, [base])
        except ErrorProveedor as ex:
            salida["fallidas"][pose.id] = str(ex)
            continue
        libro.registrar(modulo="poses_canal", proveedor=res.proveedor, modelo=res.modelo,
                        unidades={**res.uso.unidades(), "referencias": 1}, costo_usd=res.uso.costo_usd,
                        detalle=pose.id)
        archivo.write_bytes(res.png)
        idx[pose.id] = {"archivo": archivo.name, "huella": huella, "prompt": prompt, "uso": pose.uso,
                        "mira_a": pose.mira_a, "proveedor": res.proveedor, "modelo": res.modelo,
                        "costo_usd": res.uso.costo_usd,
                        "generada": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        escribir_json(destino / "poses.json", idx)
        salida["generadas"].append(pose.id)
        salida["costo_cop"] += config.a_cop(res.uso.costo_usd)
        avisar(f"  {pose.id}: lista · {formato_cop(config.a_cop(res.uso.costo_usd))}")
    return salida


def copiar_a_proyecto(estilo_id: str, carpeta_proyecto: Path) -> list[str]:
    """Copia gratis las poses ya hechas del canal a assets/poses/ del video."""
    origen = carpeta(estilo_id)
    copiadas = []
    for pid, datos in indice(estilo_id).items():
        f = origen / datos["archivo"]
        if f.exists():
            d = carpeta_proyecto / "assets" / "poses" / f.name
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, d)
            copiadas.append(pid)
    return copiadas
