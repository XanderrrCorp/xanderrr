"""Tablas de la plataforma. Todo recurso lleva espacio_id: NULL = catálogo público de Xandart.

Los datos «de configuración» de cada recurso (el estilo con sus plantillas de prompt, la
plantilla de miniatura, la fórmula del guion…) van en una columna JSON validada por los
esquemas de Pydantic que ya usa el motor: así el motor de video no cambia de forma.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def nuevo_id() -> str:
    return uuid.uuid4().hex


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class ConFechas:
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    actualizado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, onupdate=ahora)


# ------------------------------------------------------------------ cuentas

class Usuario(ConFechas, Base):
    __tablename__ = "usuarios"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    nombre: Mapped[str] = mapped_column(String(120), default="")
    # ceo: dueño de Xandart (paga a costo real y ve la administración); cliente: usuario normal
    rol: Mapped[str] = mapped_column(String(20), default="cliente")
    # «a costo»: se le cobra el costo real del proveedor, sin margen (la cuenta del dueño)
    a_costo: Mapped[bool] = mapped_column(Boolean, default=False)
    # preparado para login: proveedor externo (google…) e identificador; hoy vacío
    proveedor_login: Mapped[str | None] = mapped_column(String(30), nullable=True)
    id_externo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Espacio(ConFechas, Base):
    """Espacio de trabajo: la unidad dueña de todo y la que tiene saldo de créditos."""
    __tablename__ = "espacios"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    nombre: Mapped[str] = mapped_column(String(120))
    dueno_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    # moneda para mostrar precios de referencia al usuario (los créditos siempre valen 0,01 USD)
    moneda_vista: Mapped[str] = mapped_column(String(3), default="USD")
    # numero de registro (para la promo de los primeros N) y onboarding
    numero_registro: Mapped[int] = mapped_column(Integer, default=0)
    onboarding_hecho: Mapped[bool] = mapped_column(Boolean, default=False)
    dueno: Mapped[Usuario] = relationship()


class Miembro(Base):
    __tablename__ = "miembros"
    __table_args__ = (UniqueConstraint("espacio_id", "usuario_id"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"))
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    rol: Mapped[str] = mapped_column(String(20), default="dueno")     # dueno | editor | lector


# ------------------------------------------------------------------ recursos creativos

class Recurso(ConFechas):
    """Campos comunes: dueño (NULL = catálogo público), nombre, descripción y datos JSON."""
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str | None] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), nullable=True,
                                                   index=True)
    clave: Mapped[str] = mapped_column(String(80))            # nombre corto estable (ej. enciclopedia_mascota)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    datos: Mapped[dict] = mapped_column(JSON, default=dict)
    # de dónde salió (duplicado de otro recurso, creado con un asistente, migrado…)
    origen: Mapped[dict] = mapped_column(JSON, default=dict)
    archivado: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def publico(self) -> bool:
        return self.espacio_id is None


class Estilo(Recurso, Base):
    """datos = el estilo.json de siempre (tipos de escena, plantillas de prompt, montaje…)."""
    __tablename__ = "estilos"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)


class Personaje(Recurso, Base):
    """datos = descripción fija (character lock), poses, hoja de referencia y reacciones."""
    __tablename__ = "personajes"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)
    estilo_id: Mapped[str | None] = mapped_column(ForeignKey("estilos.id"), nullable=True)


class PlantillaMiniatura(Recurso, Base):
    __tablename__ = "plantillas_miniatura"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)


class FormulaGuion(Recurso, Base):
    """La estructura del guion como dato (ej. «escala de peligro», «Si X pasa, NO hagas Y»)."""
    __tablename__ = "formulas_guion"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)


class Voz(Recurso, Base):
    """datos = proveedor, id de voz, velocidad, idioma y muestra de audio."""
    __tablename__ = "voces"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)


class PerfilEdicion(Recurso, Base):
    __tablename__ = "perfiles_edicion"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)


class Canal(ConFechas, Base):
    __tablename__ = "canales"
    __table_args__ = (UniqueConstraint("espacio_id", "clave"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), index=True)
    clave: Mapped[str] = mapped_column(String(80))
    nombre: Mapped[str] = mapped_column(String(120))
    idioma: Mapped[str] = mapped_column(String(10), default="es")
    estilo_id: Mapped[str | None] = mapped_column(ForeignKey("estilos.id"), nullable=True)
    personaje_id: Mapped[str | None] = mapped_column(ForeignKey("personajes.id"), nullable=True)
    voz_id: Mapped[str | None] = mapped_column(ForeignKey("voces.id"), nullable=True)
    formula_id: Mapped[str | None] = mapped_column(ForeignKey("formulas_guion.id"), nullable=True)
    plantilla_miniatura_id: Mapped[str | None] = mapped_column(ForeignKey("plantillas_miniatura.id"), nullable=True)
    perfil_edicion_id: Mapped[str | None] = mapped_column(ForeignKey("perfiles_edicion.id"), nullable=True)
    # duración objetivo, segundos por escena, presentador, logo… (lo que el asistente de canal pide)
    ajustes: Mapped[dict] = mapped_column(JSON, default=dict)
    archivado: Mapped[bool] = mapped_column(Boolean, default=False)


class Video(ConFechas, Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("espacio_id", "slug"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), index=True)
    canal_id: Mapped[str | None] = mapped_column(ForeignKey("canales.id"), nullable=True)
    slug: Mapped[str] = mapped_column(String(80))
    titulo: Mapped[str] = mapped_column(String(300))
    formato: Mapped[str] = mapped_column(String(10), default="16:9")       # 16:9 | 9:16
    estado: Mapped[str] = mapped_column(String(30), default="borrador")
    # carpeta del proyecto dentro del almacén del espacio (el motor sigue trabajando con carpetas)
    carpeta: Mapped[str] = mapped_column(String(300))
    minutos: Mapped[float | None] = mapped_column(Float, nullable=True)
    archivado: Mapped[bool] = mapped_column(Boolean, default=False)


class Asset(ConFechas, Base):
    """Archivo reutilizable de la biblioteca (personaje secundario, referencia, logo, música…)."""
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str | None] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), nullable=True,
                                                   index=True)
    tipo: Mapped[str] = mapped_column(String(30))                 # imagen | audio | video | fuente
    nombre: Mapped[str] = mapped_column(String(200))
    ruta: Mapped[str] = mapped_column(String(400))                # relativa al almacén del espacio
    meta: Mapped[dict] = mapped_column(JSON, default=dict)        # licencia, origen, etiquetas, video…


# ------------------------------------------------------------------ créditos

class Movimiento(Base):
    """Libro de créditos (solo se agregan filas; el saldo es la suma, nunca se edita).

    creditos: con signo (+ entra, − sale). Una reserva resta al crear y se compensa al
    cerrarse con una «liberacion» (+) y el «consumo» real (−).
    """
    __tablename__ = "movimientos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20))   # recarga|bono|consumo|reserva|liberacion|devolucion|ajuste|vencimiento
    creditos: Mapped[int] = mapped_column(Integer)
    # bolsa de donde entra o sale: plan (se renueva cada mes, con tope), bono (regalos) o recarga
    # (comprada: nunca vence). Se gasta primero plan, luego bono, luego recarga.
    bolsa: Mapped[str] = mapped_column(String(10), default="recarga")
    accion: Mapped[str | None] = mapped_column(String(60), nullable=True)      # clave de la tabla de precios
    cantidad: Mapped[float | None] = mapped_column(Float, nullable=True)       # minutos, imágenes…
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"), nullable=True,
                                                 index=True)
    reserva_id: Mapped[str | None] = mapped_column(ForeignKey("reservas.id"), nullable=True, index=True)
    # lo que le costó a Xandart (proveedores) y lo que habría pagado un cliente a precio de lista
    costo_real_usd: Mapped[float] = mapped_column(Float, default=0.0)
    precio_cliente_usd: Mapped[float] = mapped_column(Float, default=0.0)
    # recargas pagadas: referencia de la pasarela (hoy vacía) y del pedido
    pedido_id: Mapped[str | None] = mapped_column(ForeignKey("pedidos.id"), nullable=True)
    nota: Mapped[str] = mapped_column(Text, default="")
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, index=True)


class Reserva(Base):
    __tablename__ = "reservas"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[str | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(60))
    video_id: Mapped[str | None] = mapped_column(ForeignKey("videos.id", ondelete="SET NULL"), nullable=True)
    creditos: Mapped[int] = mapped_column(Integer)                  # lo reservado
    costo_estimado_usd: Mapped[float] = mapped_column(Float, default=0.0)
    estado: Mapped[str] = mapped_column(String(20), default="abierta")   # abierta | cerrada | cancelada
    detalle: Mapped[dict] = mapped_column(JSON, default=dict)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    cerrado: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Precio(ConFechas, Base):
    """Tabla de precios editable desde la administración: créditos por unidad de cada acción."""
    __tablename__ = "precios"
    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(30))                # minuto | imagen | miniatura | …
    creditos: Mapped[int] = mapped_column(Integer)
    costo_ref_usd: Mapped[float] = mapped_column(Float, default=0.0)   # costo real de referencia por unidad
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Plan(ConFechas, Base):
    __tablename__ = "planes"
    clave: Mapped[str] = mapped_column(String(30), primary_key=True)    # lite | starter | creator
    nombre: Mapped[str] = mapped_column(String(60))
    precio_usd_mes: Mapped[float] = mapped_column(Float)
    minutos_mes: Mapped[float] = mapped_column(Float)
    creditos_mes: Mapped[int] = mapped_column(Integer)
    # los créditos que sobran se acumulan hasta este múltiplo de los créditos del mes
    tope_acumulado_meses: Mapped[float] = mapped_column(Float, default=2.0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Suscripcion(ConFechas, Base):
    """Plan de un espacio. Sin cobro real todavía: la pasarela la actualizará después."""
    __tablename__ = "suscripciones"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), unique=True)
    plan_clave: Mapped[str] = mapped_column(ForeignKey("planes.clave"))
    estado: Mapped[str] = mapped_column(String(20), default="prueba")    # prueba | activa | vencida | cancelada
    periodo_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    periodo_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    referencia_externa: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Paquete(ConFechas, Base):
    """Recarga suelta, además del plan."""
    __tablename__ = "paquetes"
    clave: Mapped[str] = mapped_column(String(30), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    precio_usd: Mapped[float] = mapped_column(Float)
    creditos: Mapped[int] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Pedido(ConFechas, Base):
    """Pedido de recarga o de plan: el punto donde se conectará la pasarela de pago.
    Hoy solo se crean a mano (ajustes) o en pruebas; nunca se cobra nada real."""
    __tablename__ = "pedidos"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=nuevo_id)
    espacio_id: Mapped[str] = mapped_column(ForeignKey("espacios.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))              # paquete | plan
    referencia: Mapped[str] = mapped_column(String(30))        # clave del paquete o del plan
    precio_usd: Mapped[float] = mapped_column(Float)
    creditos: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")   # pendiente | pagado | fallido | reembolsado
    pasarela: Mapped[str | None] = mapped_column(String(30), nullable=True)
    referencia_externa: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Ajuste(Base):
    """Configuración global editable (bono de bienvenida, promo de los primeros N, avisos…)."""
    __tablename__ = "ajustes"
    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[dict] = mapped_column(JSON)
