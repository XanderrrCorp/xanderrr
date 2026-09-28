"""Tabla de precios, planes, paquetes y bonos: datos en la base, editables desde la
administración. config/precios.json es solo la semilla de la primera vez."""
from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import leer_config
from .modelos import Ajuste, Paquete, Plan, Precio

VALOR_CREDITO_USD = 0.01          # 1 crédito = 0,01 USD al cliente (decisión del dueño)


def sembrar(s: Session) -> None:
    """Copia la semilla a la base solo si esa tabla está vacía (nunca pisa lo editado)."""
    semilla = leer_config("precios.json")
    if not s.scalar(select(Precio).limit(1)):
        s.add_all(Precio(**p) for p in semilla["precios"])
    if not s.scalar(select(Plan).limit(1)):
        s.add_all(Plan(**p) for p in semilla["planes"])
    if not s.scalar(select(Paquete).limit(1)):
        s.add_all(Paquete(**p) for p in semilla["paquetes"])
    for clave, valor in semilla["ajustes"].items():
        if s.get(Ajuste, clave) is None:
            s.add(Ajuste(clave=clave, valor=valor))
    s.flush()


def precio(s: Session, clave: str) -> Precio:
    p = s.get(Precio, clave)
    if p is None or not p.activo:
        raise KeyError(f"no hay precio para «{clave}» (revísalo en la administración)")
    return p


def ajuste(s: Session, clave: str, por_defecto=None):
    a = s.get(Ajuste, clave)
    return a.valor if a else por_defecto


def creditos_de_usd(usd: float) -> int:
    """Créditos equivalentes a un monto en dólares (se redondea hacia arriba)."""
    return int(math.ceil(round(usd / VALOR_CREDITO_USD, 6))) if usd > 0 else 0


def minutos_equivalentes(s: Session, creditos: int) -> float:
    """Cuántos minutos de video (720p) alcanzan con esos créditos."""
    return round(creditos / precio(s, "video_minuto").creditos, 1)
