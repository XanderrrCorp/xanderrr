"""Quién es el usuario actual y su espacio de trabajo.

Modo local (hoy): no hay login; entra solo la cuenta del dueño de Xandart (rol «ceo»,
paga a costo real). Cuando haya clientes, `usuario_actual` leerá la sesión (cookie o
token) y el resto del código no cambia: todo pide el usuario y el espacio por aquí.
"""
from __future__ import annotations

import os
import threading

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .modelos import Espacio, Miembro, Usuario


class SinPermiso(Exception):
    pass


def _email_ceo() -> str:
    # el correo real del dueño va en .env (el repositorio es público)
    return os.environ.get("XANDART_CEO_EMAIL") or "ceo@xandart.local"


def registrar(s: Session, email: str, nombre: str = "", rol: str = "cliente", a_costo: bool = False,
              nombre_espacio: str | None = None) -> tuple[Usuario, Espacio]:
    """Crea usuario + su espacio de trabajo. Los créditos de bienvenida los da creditos.bienvenida."""
    email = email.strip().lower()
    if s.scalar(select(Usuario).where(Usuario.email == email)):
        raise ValueError("ya existe una cuenta con ese correo")
    u = Usuario(email=email, nombre=nombre, rol=rol, a_costo=a_costo)
    s.add(u)
    s.flush()
    numero = (s.scalar(select(func.count()).select_from(Espacio)) or 0) + 1
    e = Espacio(nombre=nombre_espacio or (f"Espacio de {nombre}" if nombre else "Mi espacio"), dueno_id=u.id,
                numero_registro=numero)
    s.add(e)
    s.flush()
    s.add(Miembro(espacio_id=e.id, usuario_id=u.id, rol="dueno"))
    s.flush()
    return u, e


_CERROJO_DUENO = threading.Lock()


def cuenta_local(s: Session) -> tuple[Usuario, Espacio]:
    """La cuenta del dueño (se crea la primera vez). En modo local es siempre el usuario actual."""
    u = s.scalar(select(Usuario).where(Usuario.rol == "ceo").order_by(Usuario.creado))
    if u is None:
        with _CERROJO_DUENO:
            u = s.scalar(select(Usuario).where(Usuario.rol == "ceo").order_by(Usuario.creado))
            if u is None:
                # la primera vez la página y la preparación pueden llegar a la vez: se crea una sola
                # cuenta y se guarda ya, para que la otra la encuentre
                try:
                    u, e = registrar(s, _email_ceo(), "Dueño de Xandart", rol="ceo", a_costo=True,
                                     nombre_espacio="Xandart")
                    s.commit()
                    return u, e
                except IntegrityError:
                    s.rollback()
                    u = s.scalar(select(Usuario).where(Usuario.rol == "ceo").order_by(Usuario.creado))
    e = s.scalar(select(Espacio).where(Espacio.dueno_id == u.id).order_by(Espacio.creado))
    return u, e


def espacio_de(s: Session, usuario: Usuario, espacio_id: str | None = None) -> Espacio:
    """El espacio pedido si el usuario es miembro; si no se pide, el suyo propio."""
    q = select(Espacio).join(Miembro, Miembro.espacio_id == Espacio.id).where(Miembro.usuario_id == usuario.id)
    if espacio_id:
        e = s.scalar(q.where(Espacio.id == espacio_id))
        if e is None:
            raise SinPermiso("no tienes acceso a ese espacio")
        return e
    return s.scalar(q.order_by(Espacio.creado))


def es_admin(usuario: Usuario) -> bool:
    return usuario.rol in ("ceo", "admin")
