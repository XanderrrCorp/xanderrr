"""Acceso a recursos creativos con dueño: cada espacio ve el catálogo público de Xandart
(solo lectura) y lo suyo (privado). Para cambiar algo del catálogo, primero se duplica."""
from __future__ import annotations

import copy
import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .cuentas import SinPermiso
from .modelos import Espacio


def listar(s: Session, modelo, espacio: Espacio, incluir_publicos: bool = True, buscar: str = "") -> list:
    cond = modelo.espacio_id == espacio.id
    if incluir_publicos:
        cond = or_(cond, modelo.espacio_id.is_(None))
    q = select(modelo).where(cond, modelo.archivado.is_(False)).order_by(modelo.nombre)
    if buscar.strip():
        patron = f"%{buscar.strip()}%"
        q = q.where(or_(modelo.nombre.ilike(patron), modelo.descripcion.ilike(patron)))
    return list(s.scalars(q))


def obtener(s: Session, modelo, recurso_id: str, espacio: Espacio, para_editar: bool = False):
    r = s.get(modelo, recurso_id)
    if r is None or (r.espacio_id not in (None, espacio.id)):
        raise SinPermiso("ese recurso no existe o no es tuyo")
    if para_editar and r.espacio_id is None:
        raise SinPermiso("los recursos del catálogo de Xandart no se editan: duplícalo y edita tu copia")
    return r


def clave_libre(s: Session, modelo, espacio_id: str | None, base: str) -> str:
    base = re.sub(r"[^a-z0-9_]+", "_", base.lower()).strip("_")[:60] or "recurso"
    clave, k = base, 2
    while s.scalar(select(modelo).where(modelo.espacio_id == espacio_id, modelo.clave == clave)):
        clave, k = f"{base}_{k}", k + 1
    return clave


def duplicar(s: Session, original, espacio: Espacio, nombre: str | None = None):
    """Copia privada (de algo del catálogo o de lo propio)."""
    modelo = type(original)
    copia = modelo(espacio_id=espacio.id, clave=clave_libre(s, modelo, espacio.id, original.clave),
                   nombre=nombre or f"{original.nombre} (copia)", descripcion=original.descripcion,
                   datos=copy.deepcopy(original.datos), origen={"duplicado_de": original.id})
    for extra in ("estilo_id",):
        if hasattr(original, extra):
            setattr(copia, extra, getattr(original, extra))
    s.add(copia)
    s.flush()
    return copia


def borrar(s: Session, modelo, recurso_id: str, espacio: Espacio) -> None:
    """Se archiva (no se borra de verdad): videos viejos pueden seguir usándolo."""
    r = obtener(s, modelo, recurso_id, espacio, para_editar=True)
    if r.espacio_id != espacio.id:
        raise SinPermiso("no es tuyo")
    r.archivado = True
