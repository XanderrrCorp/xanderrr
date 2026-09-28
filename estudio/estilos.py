"""Estilos (sección 12). Cada estilo es una carpeta con su estilo.json y sus assets.

Dónde se busca (plataforma/contexto.py): primero en el espacio de trabajo actual (lo
privado de cada usuario), luego en el catálogo público de Xandart y por último en la
carpeta vieja `estilos/` del código (compatibilidad mientras se migra).
"""
from __future__ import annotations

from pathlib import Path

from .config import RAIZ, leer_json
from .esquemas import Estilo, PerfilEdicion
from .plataforma import contexto


def carpeta_estilos() -> Path:
    """Obsoleto: la carpeta de un estilo depende del espacio; usa carpeta_estilo(id)."""
    return RAIZ / "estilos"


def carpeta_estilo(id_estilo: str) -> Path:
    c = contexto.buscar("estilos", id_estilo)
    if c is None:
        disponibles = ", ".join(e.id for e in listar_estilos()) or "ninguno"
        raise FileNotFoundError(f"No existe el estilo '{id_estilo}'. Disponibles: {disponibles}")
    return c


def listar_estilos() -> list[Estilo]:
    return [Estilo.model_validate(leer_json(p)) for p in contexto.todas("estilos", "estilo.json")]


def cargar_estilo(id_estilo: str) -> Estilo:
    ruta = carpeta_estilo(id_estilo) / "estilo.json"
    estilo = Estilo.model_validate(leer_json(ruta))
    if estilo.id != id_estilo:
        raise ValueError(f"{ruta}: el id interno '{estilo.id}' no coincide con la carpeta")
    return estilo


def _ruta_perfil(ruta: str) -> Path:
    """«perfiles/x.json» → primero el perfil del espacio, luego el catálogo, luego el código."""
    p = Path(ruta)
    if p.parts and p.parts[0] == "perfiles" and len(p.parts) == 2:
        encontrado = contexto.buscar("perfiles", p.stem, "perfil.json")
        if encontrado:
            return encontrado
    return RAIZ / ruta


def cargar_perfil_edicion(estilo: Estilo, ruta: str | None = None) -> PerfilEdicion:
    """El perfil del canal (si existe) manda sobre el del estilo."""
    return PerfilEdicion.model_validate(leer_json(_ruta_perfil(ruta or estilo.perfil_edicion)))


def cargar_gramatica(estilo: Estilo) -> dict:
    return leer_json(RAIZ / estilo.gramatica_edicion)
