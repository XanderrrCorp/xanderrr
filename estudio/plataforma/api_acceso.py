"""(Paso B) Entrar y salir, la contraseña del dueño y las cuentas beta (las crea el dueño a mano; no hay registro).

Ver acceso.py para la galleta y la puerta. El dueño que olvida su contraseña la cambia desde su PC con
«Restablecer mi contraseña» (estudio/restablecer_clave.py), sin correo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import acceso, creditos, db
from .api import Quien, sesion, solo_admin, usuario_actual
from .cuentas import cuenta_local, es_admin, registrar
from .modelos import ROL_BETA, ROL_OWNER, Usuario

rutas = APIRouter(prefix="/api/v2")


def _usuario(u: Usuario) -> dict:
    return {"id": u.id, "email": u.email, "nombre": u.nombre, "rol": u.rol, "admin": es_admin(u)}


def _dueno(s: Session) -> Usuario:
    return cuenta_local(s)[0]


@rutas.get("/sesion")
def ver_sesion(request: Request):
    """Si hay alguien conectado; si no, si el dueño todavía no creó su contraseña (primera vez)."""
    if db.PREPARANDO:          # copiando y actualizando la base: la página espera y lo muestra
        return {"conectado": False, "preparando": True, "crear_clave_dueno": False}
    db.preparar()
    quien = acceso.conectado()
    with db.sesion() as s:
        if quien:
            u = s.get(Usuario, quien.usuario_id)
            return {"conectado": True, "usuario": _usuario(u), "cambiar_clave": acceso.es_temporal(u.clave_hash)}
        d = _dueno(s)
        return {"conectado": False, "crear_clave_dueno": not d.clave_hash and acceso.desde_este_pc(request.scope),
                "correo_dueno": d.email if not d.clave_hash and acceso.desde_este_pc(request.scope) else None}


class Entrar(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    clave: str = Field(min_length=1, max_length=200)
    recordar: bool = False


@rutas.post("/entrar")
def entrar(d: Entrar):
    email = d.email.strip().lower()
    espera = acceso.bloqueado_por_intentos(email)
    if espera:
        raise HTTPException(429, f"Demasiados intentos. Espera {espera} minuto{'s' if espera != 1 else ''} "
                                 "y vuelve a intentarlo.")
    db.preparar()
    with db.sesion() as s:
        u = s.scalar(select(Usuario).where(Usuario.email == email))
        if not u or not acceso.verificar_clave(d.clave, u.clave_hash):
            acceso.anotar_fallo(email)
            raise HTTPException(401, "Correo o contraseña incorrectos.")
        if u.bloqueado or not u.activo:
            raise HTTPException(403, "Tu cuenta está pausada. Escríbele al administrador de Xandart.")
        acceso.olvidar_fallos(email)
        r = JSONResponse({"conectado": True, "usuario": _usuario(u), "cambiar_clave": acceso.es_temporal(u.clave_hash)})
        acceso.poner_galleta(r, acceso.crear_token(u.id, u.clave_hash, d.recordar), d.recordar)
        return r


@rutas.post("/salir")
def salir():
    r = JSONResponse({"conectado": False})
    acceso.quitar_galleta(r)
    return r


class CrearClaveDueno(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    clave: str = Field(min_length=1, max_length=200)
    recordar: bool = True


@rutas.post("/crear-clave-dueno")
def crear_clave_dueno(d: CrearClaveDueno, request: Request):
    """Primera vez: el dueño pone su correo y su contraseña. Solo desde este PC (no por un túnel) y solo si todavía
    no tiene contraseña; después se cambia desde «Mi cuenta» o con «Restablecer mi contraseña»."""
    if not acceso.desde_este_pc(request.scope):
        raise HTTPException(403, "La contraseña del dueño solo se crea desde el computador donde está Xandart.")
    problema = acceso.problema_clave(d.clave)
    email = d.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Escribe un correo válido.")
    if problema:
        raise HTTPException(400, problema)
    db.preparar()
    with db.sesion() as s:
        u = _dueno(s)
        if u.clave_hash:
            raise HTTPException(409, "Ya tienes contraseña. Entra con ella.")
        otro = s.scalar(select(Usuario).where(Usuario.email == email, Usuario.id != u.id))
        if otro:
            raise HTTPException(409, "Ese correo ya lo usa otra cuenta.")
        u.email, u.clave_hash = email, acceso.hash_clave(d.clave)
        s.flush()
        r = JSONResponse({"conectado": True, "usuario": _usuario(u), "cambiar_clave": False})
        acceso.poner_galleta(r, acceso.crear_token(u.id, u.clave_hash, d.recordar), d.recordar)
    acceso.olvidar_sesiones()
    return r


class CambiarClave(BaseModel):
    actual: str = Field(min_length=1, max_length=200)
    nueva: str = Field(min_length=1, max_length=200)


@rutas.post("/cambiar-clave")
def cambiar_clave(d: CambiarClave, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    u = s.get(Usuario, q.usuario.id)
    if not acceso.verificar_clave(d.actual, u.clave_hash):
        raise HTTPException(400, "Tu contraseña actual no es esa.")
    problema = acceso.problema_clave(d.nueva)
    if problema:
        raise HTTPException(400, problema)
    if d.nueva == d.actual:
        raise HTTPException(400, "La contraseña nueva tiene que ser distinta de la actual.")
    u.clave_hash = acceso.hash_clave(d.nueva)
    s.commit()
    acceso.olvidar_sesiones()      # las demás sesiones de esta cuenta dejan de servir
    r = JSONResponse({"conectado": True, "usuario": _usuario(u), "cambiar_clave": False})
    acceso.poner_galleta(r, acceso.crear_token(u.id, u.clave_hash, True), True)
    return r


# ------------------------------------------------------------------ cuentas beta (las crea el dueño)

def _fila(u: Usuario) -> dict:
    return {**_usuario(u), "bloqueado": u.bloqueado, "clave_temporal": acceso.es_temporal(u.clave_hash),
            "creado": u.creado.isoformat() if u.creado else None,
            "ultima_actividad": u.ultima_actividad.isoformat() if u.ultima_actividad else None}


@rutas.get("/admin/usuarios")
def listar_usuarios(_: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    return [_fila(u) for u in s.scalars(select(Usuario).order_by(Usuario.creado))]


class NuevaCuenta(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    nombre: str = Field("", max_length=120)


@rutas.post("/admin/usuarios")
def crear_cuenta(d: NuevaCuenta, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    """Cuenta BETA con contraseña temporal (se muestra UNA vez; al entrar, la persona pone la suya)."""
    email = d.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Escribe un correo válido.")
    try:
        u, e = registrar(s, email, d.nombre.strip(), rol=ROL_BETA)
    except ValueError as ex:
        raise HTTPException(409, "Ya existe una cuenta con ese correo.") from ex
    temporal = acceso.clave_temporal()
    u.clave_hash = acceso.hash_clave(temporal, temporal=True)
    creditos.bienvenida(s, e)
    s.commit()
    return {**_fila(u), "clave_temporal_texto": temporal}


def _otro(s: Session, usuario_id: str) -> Usuario:
    u = s.get(Usuario, usuario_id)
    if not u:
        raise HTTPException(404, "Esa cuenta no existe.")
    if u.rol == ROL_OWNER:
        raise HTTPException(400, "La cuenta del dueño no se cambia desde aquí.")
    return u


class Bloqueo(BaseModel):
    bloqueado: bool


@rutas.post("/admin/usuarios/{usuario_id}/bloqueo")
def bloquear(usuario_id: str, d: Bloqueo, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    u = _otro(s, usuario_id)
    u.bloqueado = d.bloqueado
    s.commit()
    acceso.olvidar_sesiones()
    return _fila(u)


@rutas.post("/admin/usuarios/{usuario_id}/clave-temporal")
def nueva_temporal(usuario_id: str, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    """Para quien olvidó su contraseña: una temporal nueva (sus sesiones abiertas se cierran)."""
    u = _otro(s, usuario_id)
    temporal = acceso.clave_temporal()
    u.clave_hash = acceso.hash_clave(temporal, temporal=True)
    s.commit()
    acceso.olvidar_sesiones()
    return {**_fila(u), "clave_temporal_texto": temporal}
