"""API de la cola de la semana (/api/cola): ver, agregar guiones de Tracy o ideas de Peligro Tropical, quitar y
reintentar. Ver estudio/cola.py."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import cola

rutas = APIRouter(prefix="/api/cola")
_RECUPERADA = {"si": False}


def _recuperar() -> None:
    if not _RECUPERADA["si"]:                 # la primera vez que se abre Xandart: sigue lo que quedó pendiente
        _RECUPERADA["si"] = True
        cola.recuperar()


def recuperar_al_abrir() -> None:
    """(Paso B) Al abrir Xandart, sin esperar a la página: la cola no depende de haber iniciado sesión. Corre en el
    espacio del dueño (la cola es suya), cuando termine de prepararse."""
    import threading

    def seguir():
        from .plataforma import contexto, local

        try:
            espacio = local.espacio(True)
        except Exception:  # noqa: BLE001 — si la plataforma no se preparó, la cola corre como siempre
            espacio = None
        with contexto.usar_espacio(espacio):
            _recuperar()

    threading.Thread(target=seguir, daemon=True, name="cola-al-abrir").start()


@rutas.get("")
def ver():
    _recuperar()
    return cola.estado()


class GuionTracy(BaseModel):
    titulo: str = ""
    guion: str = ""


class LoteTracy(BaseModel):
    guiones: list[GuionTracy] = Field(min_length=1, max_length=30)
    etiqueta: str = ""                 # el canal de YouTube al que van (para organizarse)
    permiso: bool = False


class IdeaPeligro(BaseModel):
    tema: str = ""
    notas: str = ""
    minutos: float | None = Field(None, ge=4, le=25)


class LotePeligro(BaseModel):
    ideas: list[IdeaPeligro] = Field(min_length=1, max_length=30)
    canal: str | None = None
    minutos: float = Field(9, ge=4, le=25)
    permiso: bool = False


class LoteExplica(BaseModel):
    ideas: list[IdeaPeligro] = Field(min_length=1, max_length=30)
    temas: int = Field(9, ge=3, le=15)
    permiso: bool = False


@rutas.post("/tracy")
def agregar_tracy(lote: LoteTracy):
    try:
        cola.agregar_tracy([g.model_dump() for g in lote.guiones], lote.permiso, lote.etiqueta)
    except (ValueError, RuntimeError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return cola.estado()


@rutas.post("/peligro")
def agregar_peligro(lote: LotePeligro):
    try:
        cola.agregar_peligro([i.model_dump() for i in lote.ideas], lote.permiso, lote.canal, lote.minutos)
    except (ValueError, RuntimeError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return cola.estado()


@rutas.post("/explica")
def agregar_explica(lote: LoteExplica):
    try:
        cola.agregar_explica([i.model_dump() for i in lote.ideas], lote.permiso, lote.temas)
    except (ValueError, RuntimeError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return cola.estado()


@rutas.post("/{id_}/quitar")
def quitar(id_: str):
    try:
        cola.quitar(id_)
    except KeyError as ex:
        raise HTTPException(404) from ex
    except ValueError as ex:
        raise HTTPException(409, str(ex)) from ex
    return cola.estado()


class Reintento(BaseModel):
    permiso: bool = False


@rutas.post("/{id_}/reintentar")
def reintentar(id_: str, r: Reintento = Reintento()):
    cola.reintentar(id_, r.permiso)
    return cola.estado()


@rutas.post("/limpiar")
def limpiar():
    cola.limpiar_terminados()
    return cola.estado()
