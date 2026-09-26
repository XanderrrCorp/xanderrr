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
                  nombre_proveedor: str | None = None, avisar=print, rehacer: list[str] | None = None) -> dict:
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
        if archivo.exists() and pose.id in idx and not (rehacer and pose.id in rehacer):
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


# ------------------------------------------------------------------ presentador realista

def carpeta_presentador(estilo_id: str) -> Path:
    return carpeta_estilos() / estilo_id / "assets" / "presentador"


def generar_presentador(estilo_id: str, ids: list[str] | None = None, *, permiso: bool = False,
                        nombre_proveedor: str | None = None, avisar=print, cara: Path | None = None,
                        rehacer: list[str] | None = None) -> dict:
    """Poses del presentador (persona inventada), una sola vez. La primera pose fija la
    cara, la ropa y el lugar; las demás la llevan como referencia para ser la MISMA
    persona en el mismo sitio. El logo del canal va siempre como referencia."""
    estilo = cargar_estilo(estilo_id)
    pr = estilo.presentador
    if pr is None:
        raise ValueError(f"el estilo '{estilo_id}' no tiene presentador")
    plantilla = estilo.plantillas_assets.get("presentador")
    if not plantilla:
        raise ValueError("falta plantillas_assets.presentador en el estilo")
    logo = carpeta_estilos() / estilo_id / "assets" / pr.logo
    if not logo.exists():
        raise FileNotFoundError(f"falta el logo del canal ({pr.logo})")
    config = ConfigCostos.cargar()
    proveedor = crear_proveedor(config, leer_config("proveedores.json")["imagenes"], nombre_proveedor)
    destino = carpeta_presentador(estilo_id)
    destino.mkdir(parents=True, exist_ok=True)
    libro = LibroCostos(destino, config)
    ruta_idx = destino / "poses.json"
    idx = leer_json(ruta_idx) if ruta_idx.exists() else {}
    salida = {"generadas": [], "ya_estaban": [], "fallidas": {}, "costo_cop": 0.0}
    primera = pr.poses[0].id if pr.poses else None
    for pose in pr.poses:
        if ids and pose.id not in ids:
            continue
        refs = [logo]
        descripcion = pose.descripcion
        if pose.id == primera and cara is not None:
            # rehacer la primera pose conservando una cara ya aprobada
            refs.append(cara)
            descripcion = "The same face as the man in the second reference image, with the new clothes. " + descripcion
        if pose.id != primera:
            base = destino / f"{primera}.png"
            if not base.exists():
                salida["fallidas"][pose.id] = f"primero hay que generar y aprobar «{primera}»"
                continue
            refs.append(base)
            descripcion = ("The exact same man as in the second reference image: same face, same beard, same hair, "
                           "same clothes and the same room, sign and microphone. " + descripcion)
        prompt = prompts.armar(plantilla, estilo, "", descripcion, persona=pr.persona, escenario=pr.escenario)
        h = hashlib.sha256(f"{proveedor.modelo}|{prompt}".encode())
        for r in refs:
            h.update(hashlib.sha256(r.read_bytes()).digest())
        huella = h.hexdigest()[:16]
        archivo = destino / f"{pose.id}.png"
        # una pose ya hecha (y aprobada) nunca se rehace sola: solo si se pide con rehacer
        if archivo.exists() and pose.id in idx and not (rehacer and pose.id in rehacer):
            salida["ya_estaban"].append(pose.id)
            continue
        try:
            libro.autorizar(proveedor.estimar_usd(prompt, refs), permiso=permiso)
        except FrenoPresupuesto as ex:
            salida["fallidas"][pose.id] = str(ex)
            break
        avisar(f"Generando al presentador: «{pose.id}»…")
        try:
            res = proveedor.generar(prompt, refs)
        except ErrorProveedor as ex:
            salida["fallidas"][pose.id] = str(ex)
            continue
        libro.registrar(modulo="presentador", proveedor=res.proveedor, modelo=res.modelo,
                        unidades={**res.uso.unidades(), "referencias": len(refs)}, costo_usd=res.uso.costo_usd,
                        detalle=pose.id)
        archivo.write_bytes(res.png)
        idx[pose.id] = {"archivo": archivo.name, "huella": huella, "prompt": prompt, "uso": pose.uso,
                        "proveedor": res.proveedor, "modelo": res.modelo, "costo_usd": res.uso.costo_usd,
                        "generada": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        escribir_json(ruta_idx, idx)
        salida["generadas"].append(pose.id)
        salida["costo_cop"] += config.a_cop(res.uso.costo_usd)
        avisar(f"  {pose.id}: lista · {formato_cop(config.a_cop(res.uso.costo_usd))}")
    return salida
