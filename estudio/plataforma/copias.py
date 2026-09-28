"""Copias de seguridad completas: base de datos, proyectos (guiones, imágenes, audios, videos),
biblioteca de sonidos, configuración y los estilos y canales de la instalación.

Regla del dueño: antes de tocar la base de datos o la estructura se hace una copia completa.
La copia nunca se borra sola. Las claves (.env) no se copian: se quedan donde están.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import RAIZ, raiz_origen, ruta_proyectos


class CopiaFallida(Exception):
    pass


def carpeta_copias() -> Path:
    """Documentos › «Xandart copias» (o la carpeta de XANDART_COPIAS)."""
    if os.environ.get("XANDART_COPIAS"):
        return Path(os.environ["XANDART_COPIAS"])
    docs = Path.home() / "Documents"
    return (docs if docs.exists() else Path.home()) / "Xandart copias"


def _tamano(ruta: Path) -> tuple[int, int]:
    if not ruta.exists():
        return 0, 0
    if ruta.is_file():
        return 1, ruta.stat().st_size
    n = b = 0
    for f in ruta.rglob("*"):
        if f.is_file():
            n += 1
            b += f.stat().st_size
    return n, b


def _base_de_datos() -> Path | None:
    from . import db

    u = db.url()
    if not u.startswith("sqlite:///"):
        return None
    ruta = Path(u.removeprefix("sqlite:///"))
    return ruta if ruta.exists() else None


def que_se_copia() -> dict[str, Path]:
    from ..biblioteca import raiz as carpeta_biblioteca

    origen = raiz_origen()
    return {"proyectos": ruta_proyectos(), "biblioteca": carpeta_biblioteca(), "config": origen / "config",
            "estilos": origen / "estilos", "canales": origen / "canales", "perfiles": origen / "perfiles",
            "espacios": Path(os.environ.get("XANDART_DATOS") or RAIZ / "datos") / "espacios"}


def hacer_copia(motivo: str, solo_base: bool = False) -> dict:
    """Copia y verifica (misma cantidad de archivos y bytes). Si no hay espacio o algo no cuadra,
    lanza CopiaFallida y no se sigue con lo que iba a cambiar."""
    fecha = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = carpeta_copias() / f"{fecha}_{motivo}"
    n = 2
    while destino.exists():                     # nunca se escribe encima de otra copia
        destino = carpeta_copias() / f"{fecha}_{motivo}_{n}"
        n += 1
    fuentes = {} if solo_base else {k: v for k, v in que_se_copia().items() if v.exists()}
    base = _base_de_datos()
    total = sum(_tamano(v)[1] for v in fuentes.values()) + (base.stat().st_size if base else 0)
    carpeta_copias().mkdir(parents=True, exist_ok=True)
    libre = shutil.disk_usage(carpeta_copias()).free
    if total * 1.05 + 200 * 2**20 > libre:
        raise CopiaFallida(f"No hay espacio para la copia de seguridad: necesita {total / 2**30:.1f} GB y hay "
                           f"{libre / 2**30:.1f} GB libres en {carpeta_copias()}. Libera espacio y abre Xandart otra vez.")
    destino.mkdir(parents=True)
    informe = {"fecha": fecha, "motivo": motivo, "carpeta": str(destino), "partes": {}}
    try:
        if base:
            (destino / "datos").mkdir()
            with sqlite3.connect(base) as origen, sqlite3.connect(destino / "datos" / base.name) as copia:
                origen.backup(copia)          # copia consistente aunque Xandart esté abierto
            informe["partes"]["base_de_datos"] = {"archivos": 1, "bytes": (destino / "datos" / base.name).stat().st_size}
        for nombre, origen in fuentes.items():
            n0, b0 = _tamano(origen)
            if origen.is_dir():
                shutil.copytree(origen, destino / nombre)
            else:
                shutil.copy2(origen, destino / nombre)
            n1, b1 = _tamano(destino / nombre)
            if (n0, b0) != (n1, b1):
                raise CopiaFallida(f"La copia de «{nombre}» no quedó completa ({n1} de {n0} archivos)")
            informe["partes"][nombre] = {"origen": str(origen), "archivos": n1, "bytes": b1}
    except CopiaFallida:
        raise
    except Exception as ex:  # noqa: BLE001
        raise CopiaFallida(f"No se pudo terminar la copia de seguridad: {ex}") from ex
    informe["total_bytes"] = sum(p["bytes"] for p in informe["partes"].values())
    (destino / "copia.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    return informe


def listar() -> list[dict]:
    salida = []
    base = carpeta_copias()
    for c in sorted(base.glob("*/copia.json"), reverse=True) if base.exists() else []:
        try:
            salida.append(json.loads(c.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            continue
    return salida
