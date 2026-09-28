"""Plantilla de miniatura de cada canal: layout, estilo, fuentes, colores, íconos y
las imágenes de referencia de estilo (animales sueltos recortados, SIN texto ni
cuadrículas: si se pasan miniaturas completas, Gemini copia la cuadrícula)."""
from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..config import RAIZ, escribir_json, leer_json

EXTENSIONES_IMAGEN = (".png", ".jpg", ".jpeg", ".webp")
MAX_REFERENCIAS_POR_LLAMADA = 3
BASE = "escala_2x3"                    # plantilla base del catálogo público        # Gemini 2.5 Flash Image: mejor con máximo 3 imágenes de entrada


def carpeta_canales() -> Path:
    import os

    return Path(os.environ.get("XANDART_CANALES") or RAIZ / "canales")


class Referencia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    archivo: str
    activa: bool = True


class Plantilla(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canal: str
    nombre: str
    layout: str = "escala_2x3"
    bloque_estilo: str
    fuente_etiquetas: str = "PatrickHand-Regular.ttf"
    fuente_hero: str | None = None           # obsoleto: el texto del protagonista usa la fuente de las etiquetas
    grosor_hero: int = Field(2, ge=0, le=8)   # trazo del texto del protagonista (su «negrita»)
    color_hero_text: str = "#E00000"
    color_etiquetas: str = "#111111"
    iconos_permitidos: list[str] = Field(default_factory=lambda: ["advertencia", "prohibido", "calavera", "rayo",
                                                                   "interrogacion", "reloj"])
    color_aura_por_defecto: str = "#FF1A1A"
    referencias: list[Referencia] = []

    @field_validator("layout")
    @classmethod
    def _layout(cls, v: str) -> str:
        if v != "escala_2x3":
            raise ValueError("por ahora solo existe el layout «escala_2x3»")
        return v

    @field_validator("color_hero_text", "color_etiquetas", "color_aura_por_defecto")
    @classmethod
    def _color(cls, v: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError(f"color no válido: {v} (usa #RRGGBB)")
        return v.upper()


def _validar(canal: str) -> None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{0,59}", canal or ""):
        raise ValueError(f"nombre de canal no válido: {canal!r}")


def ruta_plantilla(canal: str) -> Path:
    """Carpeta de la plantilla de un canal: la del espacio actual, la del catálogo o la vieja."""
    from ..plataforma import almacen, contexto

    _validar(canal)
    if os.environ.get("XANDART_CANALES"):
        return carpeta_canales() / canal / "miniatura"
    encontrada = contexto.buscar("plantillas_miniatura", canal)
    if encontrada:
        return encontrada
    esp = contexto.espacio_actual()
    return (almacen.raiz_espacio(esp) / "plantillas_miniatura" / canal) if esp else carpeta_canales() / canal / "miniatura"


def _para_escribir(canal: str) -> Path:
    """Donde se guardan los cambios: siempre en el espacio actual. Si la plantilla venía del
    catálogo o de la carpeta vieja, primero se copia (el catálogo nunca se modifica)."""
    import shutil

    from ..plataforma import almacen, contexto

    _validar(canal)
    esp = contexto.espacio_actual()
    if not esp or os.environ.get("XANDART_CANALES"):
        return ruta_plantilla(canal)
    propia = almacen.raiz_espacio(esp) / "plantillas_miniatura" / canal
    actual = ruta_plantilla(canal)
    if actual != propia and actual.exists() and not propia.exists():
        shutil.copytree(actual, propia)
    propia.mkdir(parents=True, exist_ok=True)
    return propia


def cargar(canal: str) -> Plantilla:
    ruta = ruta_plantilla(canal) / "plantilla.json"
    if not ruta.exists():
        # canal sin plantilla propia: se parte de la plantilla base del catálogo
        from ..plataforma import contexto

        base = leer_json(contexto.carpeta_catalogo() / "plantillas_miniatura" / BASE / "plantilla.json")
        base.update(canal=canal, nombre=f"{canal} · escala 2x3", referencias=[])
        return Plantilla.model_validate(base)
    return Plantilla.model_validate(leer_json(ruta))


def guardar(p: Plantilla) -> None:
    escribir_json(_para_escribir(p.canal) / "plantilla.json", p.model_dump())


def referencias_activas(p: Plantilla, maximo: int = MAX_REFERENCIAS_POR_LLAMADA) -> list[Path]:
    base = ruta_plantilla(p.canal) / "referencias"
    return [base / r.archivo for r in p.referencias if r.activa and (base / r.archivo).exists()][:maximo]


def agregar_referencia(canal: str, datos: bytes, nombre: str) -> Plantilla:
    """Guarda una imagen de referencia (se reduce a 896 px: suficiente para el estilo y
    barata de mandar en cada llamada)."""
    import io

    from PIL import Image

    p = cargar(canal)
    base = re.sub(r"[^\w\-]+", "_", Path(nombre).stem, flags=re.UNICODE).strip("_")[:40] or "ref"
    if Path(nombre).suffix.lower() not in EXTENSIONES_IMAGEN:
        raise ValueError("sube una imagen PNG, JPG o WEBP")
    img = Image.open(io.BytesIO(datos))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo
    img = img.convert("RGB")
    img.thumbnail((896, 896))
    carpeta = _para_escribir(canal) / "referencias"
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = f"{base}.jpg"
    k = 2
    while (carpeta / archivo).exists():
        archivo, k = f"{base}_{k}.jpg", k + 1
    img.save(carpeta / archivo, quality=88)
    p.referencias.append(Referencia(archivo=archivo))
    guardar(p)
    return p


def quitar_referencia(canal: str, archivo: str) -> Plantilla:
    p = cargar(canal)
    if not any(r.archivo == archivo for r in p.referencias):
        raise KeyError(archivo)
    (_para_escribir(canal) / "referencias" / Path(archivo).name).unlink(missing_ok=True)
    p.referencias = [r for r in p.referencias if r.archivo != archivo]
    guardar(p)
    return p


def marcar_referencia(canal: str, archivo: str, activa: bool) -> Plantilla:
    p = cargar(canal)
    for r in p.referencias:
        if r.archivo == archivo:
            r.activa = activa
            guardar(p)
            return p
    raise KeyError(archivo)
