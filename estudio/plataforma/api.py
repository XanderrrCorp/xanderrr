"""API v2 de la plataforma: cuenta, canales, recursos, créditos, precios y administración.

Quién hace la petición lo decide `usuario_actual`: en modo local es siempre el dueño; cuando
exista el inicio de sesión (Fase 2 en adelante) solo cambia esa función.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import creditos as cr
from . import db, precios, proveedores, recursos
from .cuentas import SinPermiso, cuenta_local, es_admin
from .modelos import (Ajuste, Canal, Espacio, Estilo, FormulaGuion, Movimiento, Paquete, PerfilEdicion, Personaje,
                      Plan, PlantillaMiniatura, Precio, Usuario, Video, Voz)

api = APIRouter(prefix="/api/v2")

TIPOS = {"estilos": Estilo, "personajes": Personaje, "plantillas": PlantillaMiniatura, "formulas": FormulaGuion,
         "voces": Voz, "perfiles": PerfilEdicion}


def sesion():
    db.preparar()
    with db.sesion() as s:
        precios.sembrar(s)
        yield s


class Quien:
    def __init__(self, usuario: Usuario, espacio: Espacio):
        self.usuario, self.espacio = usuario, espacio


def usuario_actual(s: Session = Depends(sesion)) -> Quien:
    u, e = cuenta_local(s)
    return Quien(u, e)


def solo_admin(q: Quien = Depends(usuario_actual)) -> Quien:
    if not es_admin(q.usuario):
        raise HTTPException(403, "Solo la administración de Xandart puede hacer esto")
    return q


def _creditos(n: int) -> dict:
    return {"creditos": n, "usd": round(n * precios.VALOR_CREDITO_USD, 2)}


# ------------------------------------------------------------------ cuenta y saldo

@api.get("/cuenta")
def cuenta(q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    saldo = cr.saldo(s, q.espacio)
    return {"usuario": {"email": q.usuario.email, "nombre": q.usuario.nombre, "rol": q.usuario.rol,
                        "a_costo": q.usuario.a_costo, "admin": es_admin(q.usuario)},
            "espacio": {"id": q.espacio.id, "nombre": q.espacio.nombre},
            "saldo": {**_creditos(saldo), "por_bolsa": cr.saldo_por_bolsa(s, q.espacio),
                      "minutos": precios.minutos_equivalentes(s, max(0, saldo)), "bajo": cr.saldo_bajo(s, q.espacio)}}


# ------------------------------------------------------------------ canales y recursos

@api.get("/canales")
def canales(q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    filas = s.scalars(select(Canal).where(Canal.espacio_id == q.espacio.id).order_by(Canal.creado))

    def clave(modelo, id_):
        r = s.get(modelo, id_) if id_ else None
        return {"id": r.id, "clave": r.clave, "nombre": r.nombre} if r else None

    return [{"id": c.id, "clave": c.clave, "nombre": c.nombre, "idioma": c.idioma, "ajustes": c.ajustes,
             "estilo": clave(Estilo, c.estilo_id), "personaje": clave(Personaje, c.personaje_id),
             "voz": clave(Voz, c.voz_id), "formula": clave(FormulaGuion, c.formula_id),
             "plantilla_miniatura": clave(PlantillaMiniatura, c.plantilla_miniatura_id),
             "perfil_edicion": clave(PerfilEdicion, c.perfil_edicion_id),
             "videos": s.query(Video).filter(Video.canal_id == c.id).count()} for c in filas]


@api.get("/recursos/{tipo}")
def listar_recursos(tipo: str, buscar: str = "", q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    modelo = TIPOS.get(tipo)
    if modelo is None:
        raise HTTPException(404, "tipo de recurso desconocido")
    return [{"id": r.id, "clave": r.clave, "nombre": r.nombre, "descripcion": r.descripcion, "publico": r.publico}
            for r in recursos.listar(s, modelo, q.espacio, buscar=buscar)]


class Duplicar(BaseModel):
    nombre: str | None = None


@api.post("/recursos/{tipo}/{recurso_id}/duplicar")
def duplicar_recurso(tipo: str, recurso_id: str, p: Duplicar = Duplicar(), q: Quien = Depends(usuario_actual),
                     s: Session = Depends(sesion)):
    modelo = TIPOS.get(tipo)
    if modelo is None:
        raise HTTPException(404, "tipo de recurso desconocido")
    try:
        copia = recursos.duplicar(s, recursos.obtener(s, modelo, recurso_id, q.espacio), q.espacio, p.nombre)
    except SinPermiso as ex:
        raise HTTPException(404, str(ex)) from ex
    return {"id": copia.id, "clave": copia.clave, "nombre": copia.nombre}


# ------------------------------------------------------------------ precios y créditos

@api.get("/precios")
def tabla_precios(s: Session = Depends(sesion)):
    def fila(p: Precio):
        return {"clave": p.clave, "nombre": p.nombre, "unidad": p.unidad, **_creditos(p.creditos)}

    return {"valor_credito_usd": precios.VALOR_CREDITO_USD,
            "precios": [fila(p) for p in s.scalars(select(Precio).where(Precio.activo).order_by(Precio.creditos))],
            "planes": [{"clave": p.clave, "nombre": p.nombre, "precio_usd_mes": p.precio_usd_mes,
                        "minutos_mes": p.minutos_mes, "creditos_mes": p.creditos_mes,
                        "tope_acumulado_meses": p.tope_acumulado_meses}
                       for p in s.scalars(select(Plan).where(Plan.activo).order_by(Plan.precio_usd_mes))],
            "paquetes": [{"clave": p.clave, "nombre": p.nombre, "precio_usd": p.precio_usd, "creditos": p.creditos,
                          "minutos": precios.minutos_equivalentes(s, p.creditos)}
                         for p in s.scalars(select(Paquete).where(Paquete.activo).order_by(Paquete.precio_usd))]}


class Cotizar(BaseModel):
    accion: str
    cantidad: float = Field(1.0, gt=0, le=10000)


@api.post("/cotizar")
def cotizar(p: Cotizar, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    """Lo que cuesta una acción ANTES de hacerla (se muestra en cada botón)."""
    try:
        cot = cr.cotizar(s, q.espacio, p.accion, p.cantidad)
    except KeyError as ex:
        raise HTTPException(404, str(ex)) from ex
    saldo = cr.saldo(s, q.espacio)
    salida = {"accion": cot.accion, "cantidad": cot.cantidad, **_creditos(cot.creditos),
              "precio_cliente": _creditos(cot.precio_cliente_creditos), "a_costo": cot.a_costo,
              "saldo": saldo, "alcanza": cot.a_costo or saldo >= cot.creditos,
              "minutos_equivalentes": round(cot.creditos / precios.precio(s, "video_minuto").creditos, 1)}
    if cot.a_costo:
        salida["costo_real_usd"] = cot.costo_real_usd
    return salida


@api.get("/creditos/historial")
def historial(video: str | None = None, limite: int = 200, q: Quien = Depends(usuario_actual),
              s: Session = Depends(sesion)):
    video_id = None
    if video:
        v = s.scalar(select(Video).where(Video.espacio_id == q.espacio.id, Video.slug == video))
        if v is None:
            raise HTTPException(404, "Ese video no existe")
        video_id = v.id
    titulos = dict(s.execute(select(Video.id, Video.titulo).where(Video.espacio_id == q.espacio.id)).all())
    ver_costo = q.usuario.a_costo or es_admin(q.usuario)
    filas = []
    for m in cr.historial(s, q.espacio, video_id, min(max(limite, 1), 1000)):
        f = {"fecha": m.creado.isoformat(timespec="seconds"), "tipo": m.tipo, "creditos": m.creditos,
             "bolsa": m.bolsa, "accion": m.accion, "cantidad": m.cantidad, "nota": m.nota,
             "video": titulos.get(m.video_id)}
        if ver_costo:
            f["costo_real_usd"], f["precio_cliente_usd"] = m.costo_real_usd, m.precio_cliente_usd
        filas.append(f)
    return filas


class NuevoPedido(BaseModel):
    tipo: str          # paquete | plan
    referencia: str


@api.post("/pedidos")
def pedido(p: NuevoPedido, q: Quien = Depends(usuario_actual), s: Session = Depends(sesion)):
    """Deja el pedido listo para la pasarela de pago. Hoy no se cobra nada ni se acreditan créditos."""
    try:
        ped = cr.crear_pedido(s, q.espacio, p.tipo, p.referencia)
    except (KeyError, ValueError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return {"id": ped.id, "estado": ped.estado, "precio_usd": ped.precio_usd, "creditos": ped.creditos,
            "pago": "Todavía no hay pasarela de pago: el pedido queda pendiente."}


# ------------------------------------------------------------------ administración

@api.get("/admin/resumen")
def admin_resumen(_: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    espacios = []
    for e in s.scalars(select(Espacio).order_by(Espacio.creado)):
        dueno = s.get(Usuario, e.dueno_id)
        espacios.append({"id": e.id, "nombre": e.nombre, "email": dueno.email if dueno else "",
                         "a_costo": bool(dueno and dueno.a_costo), "saldo": cr.saldo(s, e),
                         "margen": cr.margen(s, e.id)})
    from . import correo

    return {"margen": cr.margen(s), "espacios": espacios, "proveedores": proveedores.estado(s),
            "correo_configurado": correo.configurado(),
            "precios": [{"clave": p.clave, "nombre": p.nombre, "unidad": p.unidad, "creditos": p.creditos,
                         "costo_ref_usd": p.costo_ref_usd, "activo": p.activo,
                         "margen_ref_pct": (round((p.creditos * precios.VALOR_CREDITO_USD - p.costo_ref_usd)
                                                  / (p.creditos * precios.VALOR_CREDITO_USD) * 100, 1)
                                            if p.creditos else None)}
                        for p in s.scalars(select(Precio).order_by(Precio.clave))],
            "planes": [{c: getattr(p, c) for c in ("clave", "nombre", "precio_usd_mes", "minutos_mes", "creditos_mes",
                                                    "tope_acumulado_meses", "activo")}
                       for p in s.scalars(select(Plan).order_by(Plan.precio_usd_mes))],
            "paquetes": [{c: getattr(p, c) for c in ("clave", "nombre", "precio_usd", "creditos", "activo")}
                         for p in s.scalars(select(Paquete).order_by(Paquete.precio_usd))],
            "ajustes": {a.clave: a.valor for a in s.scalars(select(Ajuste).order_by(Ajuste.clave))
                        if a.clave not in ("migracion_local", proveedores.CLAVE)}}


class EditarPrecio(BaseModel):
    nombre: str | None = None
    creditos: int | None = Field(None, ge=0)
    costo_ref_usd: float | None = Field(None, ge=0)
    activo: bool | None = None


@api.put("/admin/precios/{clave}")
def editar_precio(clave: str, p: EditarPrecio, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    fila = s.get(Precio, clave)
    if fila is None:
        raise HTTPException(404, "ese precio no existe")
    for k, v in p.model_dump(exclude_none=True).items():
        setattr(fila, k, v)
    return {"ok": True}


class EditarPlan(BaseModel):
    nombre: str | None = None
    precio_usd_mes: float | None = Field(None, ge=0)
    minutos_mes: float | None = Field(None, ge=0)
    creditos_mes: int | None = Field(None, ge=0)
    tope_acumulado_meses: float | None = Field(None, ge=1)
    activo: bool | None = None


@api.put("/admin/planes/{clave}")
def editar_plan(clave: str, p: EditarPlan, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    fila = s.get(Plan, clave)
    if fila is None:
        raise HTTPException(404, "ese plan no existe")
    for k, v in p.model_dump(exclude_none=True).items():
        setattr(fila, k, v)
    return {"ok": True}


class EditarPaquete(BaseModel):
    nombre: str | None = None
    precio_usd: float | None = Field(None, ge=0)
    creditos: int | None = Field(None, ge=0)
    activo: bool | None = None


@api.put("/admin/paquetes/{clave}")
def editar_paquete(clave: str, p: EditarPaquete, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    fila = s.get(Paquete, clave)
    if fila is None:
        raise HTTPException(404, "ese paquete no existe")
    for k, v in p.model_dump(exclude_none=True).items():
        setattr(fila, k, v)
    return {"ok": True}


class EditarAjuste(BaseModel):
    valor: dict


@api.put("/admin/ajustes/{clave}")
def editar_ajuste(clave: str, p: EditarAjuste, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    a = s.get(Ajuste, clave)
    if a is None or clave in ("migracion_local", proveedores.CLAVE):
        raise HTTPException(404, "ese ajuste no existe")
    a.valor = {**a.valor, **p.valor}
    return {"ok": True}


class AjusteCreditos(BaseModel):
    espacio_id: str
    creditos: int
    nota: str


@api.post("/admin/creditos")
def ajustar_creditos(p: AjusteCreditos, q: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    e = s.get(Espacio, p.espacio_id)
    if e is None:
        raise HTTPException(404, "ese espacio no existe")
    try:
        cr.ajustar(s, e, p.creditos, p.nota, q.usuario)
    except (ValueError, cr.SaldoInsuficiente) as ex:
        raise HTTPException(400, str(ex)) from ex
    return {"saldo": cr.saldo(s, e)}


class SaldoProveedor(BaseModel):
    saldo_usd: float = Field(ge=0)
    umbral_usd: float | None = Field(None, ge=0)


@api.put("/admin/proveedores/{nombre}")
def anotar_saldo(nombre: str, p: SaldoProveedor, _: Quien = Depends(solo_admin), s: Session = Depends(sesion)):
    proveedores.anotar(s, nombre.strip().lower(), p.saldo_usd, p.umbral_usd)
    return proveedores.estado(s)


@api.post("/admin/correo/prueba")
def correo_prueba(q: Quien = Depends(solo_admin)):
    from . import correo

    if not correo.configurado():
        raise HTTPException(400, "Falta configurar el correo: en ⚙ Ajustes pon tu Gmail y una contraseña de aplicación")
    para = correo.para_avisos(q.usuario.email)
    try:
        correo.enviar(para, "Xandart: correo de prueba", "Si lees esto, los avisos de Xandart ya llegan.")
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(400, f"Gmail no aceptó el envío: {str(ex)[:200]} (revisa que sea una contraseña de "
                                 "aplicación y que la verificación en dos pasos esté activa)") from ex
    return {"ok": True, "para": para}
