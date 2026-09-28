"""Saldo que queda en cada proveedor (Together, MiniMax…) y aviso por correo cuando baja.

Ninguno de los proveedores que usa Xandart tiene hoy una consulta de saldo confiable, así que
el saldo se estima: el dueño anota el saldo que ve en la página del proveedor (por ejemplo
«Together: 12,91 USD») y Xandart le va restando el gasto real que registra en el libro de
costos de cada video desde ese momento. Al anotar un saldo nuevo, la estimación se corrige.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import correo, precios
from .modelos import Ajuste, Usuario, Video

CLAVE = "saldos_proveedores"


def _datos(s: Session) -> dict:
    return dict(precios.ajuste(s, CLAVE) or {})


def _guardar(s: Session, datos: dict) -> None:
    a = s.get(Ajuste, CLAVE)
    if a is None:
        s.add(Ajuste(clave=CLAVE, valor=datos))
    else:
        a.valor = datos
    s.flush()


def anotar(s: Session, proveedor: str, saldo_usd: float, umbral_usd: float | None = None) -> dict:
    """El dueño anota el saldo que ve hoy en la página del proveedor."""
    datos = _datos(s)
    anterior = datos.get(proveedor, {})
    datos[proveedor] = {"saldo_usd": float(saldo_usd),
                        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "umbral_usd": float(umbral_usd if umbral_usd is not None else anterior.get("umbral_usd", 3.0)),
                        "avisado": False}
    _guardar(s, datos)
    return datos[proveedor]


def _gasto_desde(s: Session, desde: str) -> dict[str, float]:
    """Gasto real por proveedor registrado en los libros de costos de todos los videos."""
    from ..config import ConfigCostos
    from ..costos import LibroCostos

    config, gasto, vistas = ConfigCostos.cargar(), {}, set()
    for carpeta in s.scalars(select(Video.carpeta)):
        ruta = Path(carpeta)
        if ruta in vistas:
            continue
        vistas.add(ruta)
        for e in LibroCostos(ruta, config).entradas():
            if e.get("fecha", "") >= desde:
                gasto[e.get("proveedor", "?")] = gasto.get(e.get("proveedor", "?"), 0.0) + float(e.get("costo_usd", 0))
    return gasto


def estado(s: Session) -> list[dict]:
    salida = []
    for nombre, d in sorted(_datos(s).items()):
        gastado = _gasto_desde(s, d["fecha"]).get(nombre, 0.0)
        queda = round(d["saldo_usd"] - gastado, 2)
        salida.append({"proveedor": nombre, "anotado_usd": d["saldo_usd"], "fecha": d["fecha"],
                       "gastado_desde_usd": round(gastado, 2), "estimado_usd": queda,
                       "umbral_usd": d["umbral_usd"], "bajo": queda < d["umbral_usd"], "avisado": d.get("avisado", False)})
    return salida


def revisar_y_avisar(s: Session) -> list[str]:
    """Manda un correo por cada proveedor que bajó del umbral (una vez por saldo anotado)."""
    avisados, datos = [], _datos(s)
    bajos = [e for e in estado(s) if e["bajo"] and not e["avisado"]]
    if not bajos:
        return []
    ceo = s.scalar(select(Usuario).where(Usuario.rol == "ceo").order_by(Usuario.creado))
    for e in bajos:
        texto = (f"El saldo estimado de {e['proveedor']} es {e['estimado_usd']:.2f} USD "
                 f"(anotaste {e['anotado_usd']:.2f} USD el {e['fecha'][:10]} y desde entonces se gastaron "
                 f"{e['gastado_desde_usd']:.2f} USD). Está por debajo del aviso de {e['umbral_usd']:.2f} USD.\n\n"
                 "Recarga en la página del proveedor y anota el saldo nuevo en Xandart › Administración.")
        try:
            para = correo.para_avisos(ceo.email if ceo else None)
            enviado = bool(para) and correo.enviar(para, f"Xandart: queda poco saldo en {e['proveedor']}", texto)
        except Exception:  # noqa: BLE001 — si el correo falla, el aviso sigue visible en la administración
            enviado = False
        if enviado:
            datos[e["proveedor"]]["avisado"] = True
            avisados.append(e["proveedor"])
    _guardar(s, datos)
    return avisados
