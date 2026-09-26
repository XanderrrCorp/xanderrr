"""Rutas y lectura de configuración. Las claves de API solo viven en `.env`."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent


def ruta_proyectos() -> Path:
    return Path(os.environ.get("ESTUDIO_PROYECTOS") or RAIZ / "proyectos")


def _leer_env() -> dict[str, str]:
    """Lee `.env` de la raíz sin dependencias. Las variables del sistema mandan."""
    valores: dict[str, str] = {}
    ruta = RAIZ / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            valores[k.strip()] = v.strip().strip('"').strip("'")
    return valores


def clave_api(nombre: str) -> str | None:
    """Clave de un proveedor: primero el entorno, luego `.env`. Nunca del código."""
    return os.environ.get(nombre) or _leer_env().get(nombre) or None


def leer_config(nombre: str) -> dict[str, Any]:
    return leer_json(RAIZ / "config" / nombre)


def leer_json(ruta: Path) -> Any:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta: Path, datos: Any) -> None:
    """Escritura atómica: nunca deja un JSON a medias si el proceso se corta."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, ruta)


class ConfigCostos:
    """Envoltorio de `config/costos.json`. Nunca inventa precios: si faltan, lo dice."""

    def __init__(self, datos: dict[str, Any]):
        self.datos = datos
        self.trm: float = datos["trm_cop_por_usd"]
        self.objetivo_cop: float = datos["presupuesto_objetivo_cop"]
        self.maximo_cop: float = datos["presupuesto_maximo_cop"]
        self.precios: dict[str, Any] = datos["precios_usd"]
        self.modelos: dict[str, str] = datos.get("modelo_claude_por_modulo", {})
        self.consumo: dict[str, Any] = datos["consumo_estimado"]
        self.ajustes: dict[str, Any] = datos.get("ajustes_presupuesto", {})

    @classmethod
    def cargar(cls, ruta: Path | None = None) -> "ConfigCostos":
        return cls(leer_json(ruta or RAIZ / "config" / "costos.json"))

    def a_cop(self, usd: float) -> float:
        return usd * self.trm

    def precio_claude(self, modelo: str) -> tuple[float, float] | None:
        p = self.precios.get("claude_por_millon_tokens", {}).get(modelo)
        if not p or p.get("input") is None or p.get("output") is None:
            return None
        return p["input"], p["output"]

    def costo_claude(self, modelo: str, tokens_in: float, tokens_out: float) -> float:
        p = self.precio_claude(modelo)
        if p is None:
            raise PrecioFaltante(f"claude:{modelo}")
        return tokens_in / 1e6 * p[0] + tokens_out / 1e6 * p[1]

    def precio(self, clave: str) -> float:
        v = self.precios.get(clave)
        if v is None:
            raise PrecioFaltante(clave)
        return v


class PrecioFaltante(Exception):
    """Un precio necesario está en null en config/costos.json."""


def formato_cop(valor: float) -> str:
    return f"{round(valor):,}".replace(",", ".") + " COP"


def formato_usd(valor: float) -> str:
    return f"{valor:.2f} USD".replace(".", ",")
