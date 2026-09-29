"""API del asistente de personaje (/api/v2/personajes).

Cada paso que dibuja corre como trabajo en segundo plano (mismo mecanismo que los videos) y se
cobra por imagen en créditos; pasar el máximo pide permiso igual que en un video.
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import personajes as ps
from . import almacen, recursos
from .api import Quien, sesion, usuario_actual
from .cuentas import SinPermiso
from .modelos import Canal, Estilo, Personaje

rutas = APIRouter(prefix="/api/v2/personajes")

NOMBRES_PASO = {"variantes": "Dibujando variantes", "afinar": "Afinando el personaje",
                "hoja": "Haciendo la hoja de referencia", "probar": "Probando en 3 escenas"}


def _clave_trabajo(p: Personaje) -> str:
    return f"personaje~{p.id}"


def _obtener(s: Session, q: Quien, personaje_id: str) -> Personaje:
    try:
        p = recursos.obtener(s, Personaje, personaje_id, q.espacio)
    except SinPermiso as ex:
        raise HTTPException(404, str(ex)) from ex
    if not (p.datos or {}).get("asistente") or p.espacio_id != q.espacio.id:
        raise HTTPException(404, "Ese personaje no se hizo con el asistente")
    return p


def _ruta(q: Quien, p: Personaje):
    return almacen.ruta(q.espacio.id, "personajes", p.clave)


def _detalle(s: Session, q: Quien, p: Personaje) -> dict:
    from .. import pipeline

    ruta = _ruta(q, p)
    # primero el trabajo y después el archivo: si termina entre las dos lecturas, la página ve
    # «en marcha» y vuelve a preguntar, en vez de ver «listo» con la última imagen sin guardar
    t = pipeline.TRABAJOS.get(_clave_trabajo(p))
    trabajo = None if t is None else {
        "paso": t.paso, "nombre": NOMBRES_PASO.get(t.paso, t.paso), "mensaje": t.mensaje,
        "progreso": round(t.progreso, 3), "activo": t.activo, "error": t.error,
        "segundos": int(time.time() - t.inicio)}
    e = ps.cargar(ruta)
    canales = s.scalars(select(Canal).where(Canal.espacio_id == q.espacio.id, Canal.archivado.is_(False))).all()
    return {"id": p.id, **e.model_dump(), "paso": e.paso, "gastado_usd": round(ps.gastado_usd(ruta), 3),
            "imagenes_por_paso": ps.imagenes_por_paso(),
            "canales": [{"id": c.id, "nombre": c.nombre, "asignado": c.personaje_id == p.id} for c in canales],
            "trabajo": trabajo}


@rutas.get("")
def listar(q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    """Los personajes del espacio: los del asistente (con su avance) y los que venían del estilo."""
    salida = []
    for p in recursos.listar(s, Personaje, q.espacio, incluir_publicos=False):
        d = p.datos or {}
        fila = {"id": p.id, "clave": p.clave, "nombre": p.nombre, "tipo": d.get("tipo", "mascota"),
                "asistente": bool(d.get("asistente")), "imagen": None, "paso": None}
        if fila["asistente"]:
            try:
                e = ps.cargar(_ruta(q, p))
                fila["paso"] = e.paso
                fila["imagen"] = e.elegida or (e.variantes[-1].archivo if e.variantes else None)
            except FileNotFoundError:
                continue
        salida.append(fila)
    return salida


@rutas.post("")
async def crear(nombre: str = Form(...), estilo: str = Form(...), descripcion: str = Form(""),
                tipo: str = Form("mascota"), referencia: UploadFile | None = File(None),
                q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    if tipo not in ("mascota", "presentador"):
        raise HTTPException(400, "tipo no válido")
    est = s.scalar(select(Estilo).where(Estilo.clave == estilo, (Estilo.espacio_id == q.espacio.id) | Estilo.espacio_id.is_(None))
                   .order_by(Estilo.espacio_id.is_(None)))           # el del espacio antes que el del catálogo
    clave = recursos.clave_libre(s, Personaje, q.espacio.id, ps.clave_de(nombre))
    ref = (await referencia.read(), referencia.filename or "ref.png") if referencia and referencia.filename else None
    try:
        ps.crear(almacen.ruta(q.espacio.id, "personajes", clave), nombre, estilo, descripcion, tipo, ref)
    except (ValueError, OSError) as ex:           # estilo que no existe, imagen rota…
        raise HTTPException(400, f"No se pudo crear: {ex}") from ex
    p = Personaje(espacio_id=q.espacio.id, clave=clave, nombre=nombre.strip() or clave, descripcion=descripcion.strip(),
                  estilo_id=est.id if est else None, datos={"asistente": True, "tipo": tipo, "estilo": estilo},
                  origen={"asistente": "personaje"})
    s.add(p)
    s.flush()
    return _detalle(s, q, p)


@rutas.get("/{personaje_id}")
def ver(personaje_id: str, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    return _detalle(s, q, _obtener(s, q, personaje_id))


@rutas.get("/{personaje_id}/archivos/{carpeta}/{archivo}")
def archivo(personaje_id: str, carpeta: str, archivo: str, q: Quien = Depends(usuario_actual),
            s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    if carpeta not in ("imagenes", "referencia"):
        raise HTTPException(404)
    base = _ruta(q, p)
    r = (base / archivo) if carpeta == "referencia" else (base / "imagenes" / archivo)
    if archivo.startswith(".") or "/" in archivo or "\\" in archivo or not r.is_file():
        raise HTTPException(404)
    return FileResponse(r)


class Pedido(BaseModel):
    permiso: bool = False
    instruccion: str = ""
    n: int = Field(3, ge=1, le=4)


def _lanzar(s: Session, q: Quien, p: Personaje, paso: str, imagenes: int, funcion) -> dict:
    from .. import pipeline
    from . import cobro

    ruta = _ruta(q, p)

    def trabajo(t):
        with cobro.accion(ruta, "personaje_imagen", imagenes):
            funcion(ruta, t)

    try:
        pipeline.lanzar(_clave_trabajo(p), paso, trabajo)
    except RuntimeError as ex:
        raise HTTPException(409, "Ya hay un paso en marcha para este personaje") from ex
    return _detalle(s, q, p)


@rutas.post("/{personaje_id}/variantes")
def variantes(personaje_id: str, d: Pedido = Pedido(), q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    return _lanzar(s, q, p, "variantes", d.n,
                   lambda r, t: ps.variantes(r, d.n, permiso=d.permiso, avisar=t.avisar))


@rutas.post("/{personaje_id}/afinar")
def afinar(personaje_id: str, d: Pedido, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    if len(d.instruccion.strip()) < 3:
        raise HTTPException(400, "Escribe qué quieres cambiar")
    return _lanzar(s, q, p, "afinar", 1, lambda r, t: ps.afinar(r, d.instruccion, permiso=d.permiso, avisar=t.avisar))


@rutas.post("/{personaje_id}/hoja")
def hoja(personaje_id: str, d: Pedido = Pedido(), q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    return _lanzar(s, q, p, "hoja", len(ps.VISTAS), lambda r, t: ps.hoja(r, permiso=d.permiso, avisar=t.avisar))


@rutas.post("/{personaje_id}/probar")
def probar(personaje_id: str, d: Pedido = Pedido(), q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    return _lanzar(s, q, p, "probar", len(ps.ESCENAS_DE_PRUEBA),
                   lambda r, t: ps.probar(r, permiso=d.permiso, avisar=t.avisar))


class Elegir(BaseModel):
    archivo: str


@rutas.post("/{personaje_id}/elegir")
def elegir(personaje_id: str, d: Elegir, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    try:
        ps.elegir(_ruta(q, p), d.archivo)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    return _detalle(s, q, p)


class Editar(BaseModel):
    nombre: str | None = None
    bloqueo: str | None = None


@rutas.put("/{personaje_id}")
def editar(personaje_id: str, d: Editar, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    p = _obtener(s, q, personaje_id)
    ruta = _ruta(q, p)
    try:
        if d.bloqueo is not None:
            ps.editar_bloqueo(ruta, d.bloqueo)
        if d.nombre and d.nombre.strip():
            e = ps.cargar(ruta)
            e.nombre = p.nombre = d.nombre.strip()[:120]
            ps.guardar(ruta, e)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    return _detalle(s, q, p)


class Asignar(BaseModel):
    canal_id: str
    usar: bool = True


@rutas.post("/{personaje_id}/canal")
def asignar(personaje_id: str, d: Asignar, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    """El canal usa este personaje en sus videos nuevos (los que ya existen no cambian)."""
    p = _obtener(s, q, personaje_id)
    c = s.get(Canal, d.canal_id)
    if c is None or c.espacio_id != q.espacio.id:
        raise HTTPException(404, "Ese canal no existe")
    if d.usar:
        e = ps.cargar(_ruta(q, p))
        if not e.hoja.get("hoja"):
            raise HTTPException(400, "Termina la hoja de referencia antes de usarlo en un canal")
        if c.personaje_id != p.id:           # el de antes se recuerda para poder volver a él
            c.ajustes = {**(c.ajustes or {}), "personaje_anterior": c.personaje_id}
        c.personaje_id = p.id
    elif c.personaje_id == p.id:
        c.personaje_id = (c.ajustes or {}).get("personaje_anterior")
    s.flush()
    return _detalle(s, q, p)
