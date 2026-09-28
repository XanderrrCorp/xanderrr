"""Cobro en créditos de lo que produce el motor de video.

El motor sigue midiendo el gasto real en el libro de costos de cada proyecto
(logs/costos.jsonl). Aquí se aparta el precio ANTES de gastar y al terminar se cobra lo
real; si algo falla por el sistema o el proveedor, se devuelve lo apartado.

- Video completo: se aparta al empezar las imágenes (minutos objetivo) y se cobra al terminar
  el render (minutos reales). Si un paso falla la reserva queda abierta para reintentar; si el
  video se descarta, `descartar_video` la devuelve.
- Acciones sueltas (prueba de escenas, short, miniatura…): `accion` aparta, corre y cobra.

Sin espacio de trabajo (versión de un usuario, pruebas) no hace nada.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import func, select

from ..config import ConfigCostos
from . import contexto, creditos, db
from .modelos import Espacio, Movimiento, Reserva, Video

VIDEO = "video_minuto"


def _costo_usd(carpeta: Path) -> float:
    from ..costos import LibroCostos

    libro = LibroCostos(carpeta, ConfigCostos.cargar())
    return sum(e["costo_usd"] for e in libro.entradas())


def _video(s, espacio_id: str, carpeta: Path) -> Video | None:
    v = s.scalar(select(Video).where(Video.espacio_id == espacio_id, Video.slug == carpeta.name))
    if v is None:                                  # un video hecho por fuera (short, importado a mano)
        from ..proyecto import CarpetaProyecto

        try:
            p = CarpetaProyecto(carpeta).cargar()
        except Exception:  # noqa: BLE001
            return None
        v = Video(espacio_id=espacio_id, slug=carpeta.name, titulo=p.titulo, carpeta=str(carpeta),
                  minutos=round(p.duracion_objetivo_seg / 60, 1))
        s.add(v)
        s.flush()
    return v


def _ya_cobrado_usd(s, video_id: str) -> float:
    return float(s.scalar(select(func.coalesce(func.sum(Movimiento.costo_real_usd), 0.0))
                          .where(Movimiento.video_id == video_id, Movimiento.tipo == "consumo")) or 0.0)


def _abierta(s, video_id: str, accion: str) -> Reserva | None:
    return s.scalar(select(Reserva).where(Reserva.video_id == video_id, Reserva.accion == accion,
                                          Reserva.estado == "abierta"))


def abrir_video(carpeta: Path, minutos: float) -> dict | None:
    """Aparta el precio del video completo (una sola vez). SaldoInsuficiente si no alcanza."""
    esp = contexto.espacio_actual()
    if not esp:
        return None
    with db.sesion() as s:
        v = _video(s, esp, carpeta)
        if v is None:
            return None
        r = _abierta(s, v.id, VIDEO)
        if r is None:
            r = creditos.reservar(s, s.get(Espacio, esp), VIDEO, minutos, video_id=v.id)
        v.estado = "en_proceso"
        return {"reserva": r.id, "creditos": r.creditos}


def cerrar_video(carpeta: Path, minutos_reales: float) -> dict | None:
    """Cobra lo real del video terminado: minutos reales y gasto real que no se cobró aparte."""
    esp = contexto.espacio_actual()
    if not esp:
        return None
    with db.sesion() as s:
        v = _video(s, esp, carpeta)
        if v is None:
            return None
        v.estado, v.minutos = "listo", round(minutos_reales, 2)
        r = _abierta(s, v.id, VIDEO)
        if r is None:           # render repetido de un video ya cobrado: no se cobra otra vez
            return None
        costo = max(0.0, _costo_usd(carpeta) - _ya_cobrado_usd(s, v.id))
        movs = creditos.cerrar(s, r, minutos_reales, costo, nota=f"Video «{v.titulo}»")
        salida = {"cobrado": -sum(m.creditos for m in movs), "costo_real_usd": round(costo, 4)}
    _avisar_proveedores()
    return salida


def descartar_video(carpeta: Path, motivo: str = "Video descartado sin terminar") -> None:
    esp = contexto.espacio_actual()
    if not esp:
        return
    with db.sesion() as s:
        v = s.scalar(select(Video).where(Video.espacio_id == esp, Video.slug == carpeta.name))
        if v is None:
            return
        r = _abierta(s, v.id, VIDEO)
        if r is not None:
            creditos.cancelar(s, r, motivo, costo_real_usd=max(0.0, _costo_usd(carpeta) - _ya_cobrado_usd(s, v.id)))


class _Medida:
    """Carpetas cuyo gasto real cuenta para la acción (el short, por ejemplo, gasta en la suya)."""

    def __init__(self, carpeta: Path):
        self.carpetas = [carpeta]
        self._antes = {carpeta: _costo_usd(carpeta)}

    def sumar(self, carpeta: Path) -> None:
        if carpeta not in self._antes:
            self.carpetas.append(carpeta)
            self._antes[carpeta] = _costo_usd(carpeta)

    def gasto(self) -> float:
        return max(0.0, sum(_costo_usd(c) - self._antes[c] for c in self.carpetas))


@contextmanager
def accion(carpeta: Path, clave: str, cantidad: float = 1.0):
    """Acción suelta: aparta antes, cobra el gasto real de lo que hizo; si falla, devuelve."""
    medida = _Medida(carpeta)
    esp = contexto.espacio_actual()
    if not esp:
        yield medida
        return
    with db.sesion() as s:
        v = _video(s, esp, carpeta)
        r = creditos.reservar(s, s.get(Espacio, esp), clave, cantidad, video_id=v.id if v else None)
        reserva_id = r.id
    try:
        yield medida
    except BaseException as ex:
        with db.sesion() as s:
            creditos.cancelar(s, s.get(Reserva, reserva_id), f"falló: {str(ex)[:150] or ex.__class__.__name__}",
                              costo_real_usd=medida.gasto())
        raise
    with db.sesion() as s:
        creditos.cerrar(s, s.get(Reserva, reserva_id), cantidad, medida.gasto())
    _avisar_proveedores()


def _avisar_proveedores() -> None:
    """Tras cada gasto: si el saldo estimado de un proveedor bajó del aviso, correo al dueño."""
    try:
        from . import proveedores

        with db.sesion() as s:
            proveedores.revisar_y_avisar(s)
    except Exception:  # noqa: BLE001 — un aviso que no sale nunca frena la producción
        pass
