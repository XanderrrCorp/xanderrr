"""Carpeta de proyecto (sección 1) y estado reanudable de cada paso (principio 5)."""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from .config import ConfigCostos, escribir_json, leer_json, ruta_proyectos
from .costos import LibroCostos
from .esquemas import PASOS, EDL, EscenasV2, Proyecto
from .estilos import cargar_estilo

SUBCARPETAS = ("assets", "imagenes", "imagenes/sin_fondo", "audio", "render", "logs")


def slugificar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60] or "video"


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class CarpetaProyecto:
    def __init__(self, ruta: Path):
        self.ruta = ruta

    # ---- rutas
    @property
    def archivo_proyecto(self) -> Path:
        return self.ruta / "proyecto.json"

    @property
    def archivo_escenas(self) -> Path:
        return self.ruta / "escenas.json"

    @property
    def archivo_edl(self) -> Path:
        return self.ruta / "edl.json"

    # ---- creación y carga
    @classmethod
    def crear(cls, titulo: str, canal: str, estilo: str, duracion_objetivo_seg: float,
              slug: str | None = None, base: Path | None = None) -> "CarpetaProyecto":
        cargar_estilo(estilo)  # falla temprano si el estilo no existe
        slug = slug or slugificar(titulo)
        ruta = (base or ruta_proyectos()) / slug
        if (ruta / "proyecto.json").exists():
            raise FileExistsError(f"Ya existe el proyecto '{slug}'")
        for sub in SUBCARPETAS:
            (ruta / sub).mkdir(parents=True, exist_ok=True)
        p = Proyecto(slug=slug, titulo=titulo, canal=canal, estilo=estilo,
                     duracion_objetivo_seg=duracion_objetivo_seg, creado=_ahora())
        c = cls(ruta)
        c.guardar(p)
        return c

    @classmethod
    def abrir(cls, slug: str, base: Path | None = None) -> "CarpetaProyecto":
        ruta = (base or ruta_proyectos()) / slug
        if not (ruta / "proyecto.json").exists():
            raise FileNotFoundError(f"No existe el proyecto '{slug}' en {ruta.parent}")
        return cls(ruta)

    def cargar(self) -> Proyecto:
        return Proyecto.model_validate(leer_json(self.archivo_proyecto))

    def guardar(self, p: Proyecto) -> None:
        escribir_json(self.archivo_proyecto, p.model_dump(mode="json"))

    # ---- estado de pasos (reanudación)
    def marcar(self, paso: str, estado: str, salida: list[str] | None = None, error: str | None = None) -> None:
        if paso not in PASOS:
            raise ValueError(f"paso desconocido: {paso}")
        p = self.cargar()
        actual = p.pasos[paso]
        actual.estado = estado  # type: ignore[assignment]
        actual.actualizado = _ahora()
        actual.error = error
        if salida is not None:
            actual.salida = salida
        self.guardar(p)

    def siguiente_paso(self) -> str | None:
        """Primer paso no completo: desde ahí se reanuda sin volver a pagar lo anterior."""
        p = self.cargar()
        return next((n for n in PASOS if p.pasos[n].estado != "completo"), None)

    # ---- contratos
    def cargar_escenas(self) -> EscenasV2:
        return EscenasV2.model_validate(leer_json(self.archivo_escenas))

    def guardar_escenas(self, escenas: EscenasV2) -> None:
        escribir_json(self.archivo_escenas, escenas.model_dump(mode="json", exclude_none=False))

    def cargar_edl(self) -> EDL:
        return EDL.model_validate(leer_json(self.archivo_edl))

    def libro(self, config: ConfigCostos) -> LibroCostos:
        return LibroCostos(self.ruta, config)

    def validar(self) -> list[str]:
        """Valida todos los contratos presentes. Devuelve la lista de errores (vacía = ok)."""
        errores: list[str] = []
        try:
            p = self.cargar()
        except Exception as e:  # noqa: BLE001
            return [f"proyecto.json: {e}"]
        estilo = cargar_estilo(p.estilo)
        if self.archivo_escenas.exists():
            try:
                esc = self.cargar_escenas()
                errores += [f"escenas.json: {m}" for m in esc.errores_contra_estilo(estilo)]
            except Exception as e:  # noqa: BLE001
                errores.append(f"escenas.json: {e}")
        if self.archivo_edl.exists():
            try:
                self.cargar_edl()
            except Exception as e:  # noqa: BLE001
                errores.append(f"edl.json: {e}")
        return errores
