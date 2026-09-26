"""Libro de costos por proyecto (`logs/costos.jsonl`) y freno duro de presupuesto."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .config import ConfigCostos, formato_cop

# La animación nunca cuenta contra el presupuesto base (regla 2.7).
Categoria = Literal["base", "animacion"]


class FrenoPresupuesto(Exception):
    """Se llegaría al máximo: el sistema se pausa y pregunta (regla 2.6)."""


class LibroCostos:
    def __init__(self, carpeta_proyecto: Path, config: ConfigCostos):
        self.ruta = carpeta_proyecto / "logs" / "costos.jsonl"
        self.config = config

    def entradas(self) -> list[dict[str, Any]]:
        if not self.ruta.exists():
            return []
        with open(self.ruta, encoding="utf-8") as f:
            return [json.loads(linea) for linea in f if linea.strip()]

    def total_usd(self, categoria: Categoria = "base") -> float:
        return sum(e["costo_usd"] for e in self.entradas() if e.get("categoria", "base") == categoria)

    def total_cop(self, categoria: Categoria = "base") -> float:
        return sum(e["costo_cop"] for e in self.entradas() if e.get("categoria", "base") == categoria)

    def por_modulo(self) -> dict[str, float]:
        tot: dict[str, float] = {}
        for e in self.entradas():
            tot[e["modulo"]] = tot.get(e["modulo"], 0.0) + e["costo_cop"]
        return tot

    def autorizar(self, costo_usd: float, *, permiso: bool = False, categoria: Categoria = "base") -> None:
        """Llamar ANTES de cada gasto. Lanza FrenoPresupuesto si se pasaría del máximo."""
        if categoria != "base" or permiso:
            return
        proyectado = self.total_cop() + self.config.a_cop(costo_usd)
        if proyectado > self.config.maximo_cop:
            raise FrenoPresupuesto(
                f"El gasto llegaría a {formato_cop(proyectado)}, por encima del máximo "
                f"de {formato_cop(self.config.maximo_cop)}. Se necesita permiso explícito."
            )

    def registrar(
        self,
        *,
        modulo: str,
        proveedor: str,
        modelo: str,
        unidades: dict[str, float],
        costo_usd: float,
        categoria: Categoria = "base",
        detalle: str | None = None,
    ) -> dict[str, Any]:
        entrada = {
            "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "modulo": modulo,
            "proveedor": proveedor,
            "modelo": modelo,
            "unidades": unidades,
            "costo_usd": round(costo_usd, 6),
            "costo_cop": round(self.config.a_cop(costo_usd), 2),
            "trm": self.config.trm,
            "categoria": categoria,
        }
        if detalle:
            entrada["detalle"] = detalle
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return entrada
