"""Catálogo de estilos (sección 12). Todo se lee de `estilos/<id>/estilo.json`."""
from __future__ import annotations

from pathlib import Path

from .config import RAIZ, leer_json
from .esquemas import Estilo, PerfilEdicion


def carpeta_estilos() -> Path:
    return RAIZ / "estilos"


def listar_estilos() -> list[Estilo]:
    return [Estilo.model_validate(leer_json(p)) for p in sorted(carpeta_estilos().glob("*/estilo.json"))]


def cargar_estilo(id_estilo: str) -> Estilo:
    ruta = carpeta_estilos() / id_estilo / "estilo.json"
    if not ruta.exists():
        disponibles = ", ".join(e.id for e in listar_estilos()) or "ninguno"
        raise FileNotFoundError(f"No existe el estilo '{id_estilo}'. Disponibles: {disponibles}")
    estilo = Estilo.model_validate(leer_json(ruta))
    if estilo.id != id_estilo:
        raise ValueError(f"{ruta}: el id interno '{estilo.id}' no coincide con la carpeta")
    return estilo


def cargar_perfil_edicion(estilo: Estilo, ruta: str | None = None) -> PerfilEdicion:
    """El perfil del canal (si existe) manda sobre el del estilo."""
    return PerfilEdicion.model_validate(leer_json(RAIZ / (ruta or estilo.perfil_edicion)))


def cargar_gramatica(estilo: Estilo) -> dict:
    return leer_json(RAIZ / estilo.gramatica_edicion)
