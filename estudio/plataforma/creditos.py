"""Libro de créditos: cada movimiento queda escrito y el saldo es SIEMPRE la suma del libro.

Flujo de una acción que gasta:
1. `cotizar`: cuánto cuesta (créditos al cliente; costo real del proveedor).
2. `reservar`: aparta los créditos antes de empezar (con un margen). Sin saldo, no arranca.
3. `cerrar`: se cobra lo real y se libera la diferencia. Si falló por culpa del sistema o
   del proveedor, `cancelar` devuelve todo (el costo real igual queda anotado para el margen).

Bolsas: los créditos entran a «plan» (se renuevan cada mes con tope), «bono» (regalos) o
«recarga» (comprados: nunca vencen). Se gastan en ese orden.

La cuenta a costo (el dueño) paga el costo real en créditos (0,01 USD = 1 crédito) y cada
movimiento guarda también lo que le habría costado a un cliente.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import precios
from .modelos import Espacio, Movimiento, Plan, Reserva, Usuario, ahora

BOLSAS = ("plan", "bono", "recarga")      # orden en que se gastan


class SaldoInsuficiente(Exception):
    def __init__(self, faltan: int, necesita: int, cotizacion: "Cotizacion | None" = None):
        self.faltan, self.necesita, self.cotizacion = faltan, necesita, cotizacion
        super().__init__(f"No te alcanzan los créditos: esta acción necesita {necesita} y te faltan {faltan}. "
                         "Recarga créditos o elige algo más corto.")


@dataclass
class Cotizacion:
    accion: str
    cantidad: float
    creditos: int                 # lo que se cobra a este espacio
    precio_cliente_creditos: int  # lo que pagaría un cliente a precio de lista
    precio_cliente_usd: float
    costo_real_usd: float
    a_costo: bool

    def como_dict(self) -> dict:
        return asdict(self)


def _a_costo(s: Session, espacio: Espacio) -> bool:
    dueno = s.get(Usuario, espacio.dueno_id)
    return bool(dueno and dueno.a_costo)


def _mov(s: Session, espacio: Espacio, tipo: str, creditos: int, bolsa: str, **kw) -> Movimiento:
    if bolsa not in BOLSAS:
        raise ValueError(f"bolsa desconocida: {bolsa}")
    m = Movimiento(espacio_id=espacio.id, tipo=tipo, creditos=int(creditos), bolsa=bolsa, **kw)
    s.add(m)
    s.flush()
    return m


# ------------------------------------------------------------------ saldo

def saldo_por_bolsa(s: Session, espacio: Espacio) -> dict[str, int]:
    filas = s.execute(select(Movimiento.bolsa, func.coalesce(func.sum(Movimiento.creditos), 0))
                      .where(Movimiento.espacio_id == espacio.id).group_by(Movimiento.bolsa)).all()
    salida = {b: 0 for b in BOLSAS}
    salida.update({b: int(v) for b, v in filas})
    return salida


def saldo(s: Session, espacio: Espacio) -> int:
    return sum(saldo_por_bolsa(s, espacio).values())


def saldo_bajo(s: Session, espacio: Espacio) -> bool:
    minutos = (precios.ajuste(s, "aviso_saldo_bajo") or {}).get("minutos", 2)
    return saldo(s, espacio) < minutos * precios.precio(s, "video_minuto").creditos


def _repartir(s: Session, espacio: Espacio, creditos: int) -> list[tuple[str, int]]:
    """De qué bolsas sale un gasto (plan → bono → recarga)."""
    saldos, falta, reparto = saldo_por_bolsa(s, espacio), creditos, []
    for b in BOLSAS:
        toma = min(max(0, saldos[b]), falta)
        if toma:
            reparto.append((b, toma))
            falta -= toma
    if falta > 0:
        raise SaldoInsuficiente(falta, creditos)
    return reparto


# ------------------------------------------------------------------ entradas

def recargar(s: Session, espacio: Espacio, creditos: int, nota: str = "", usuario: Usuario | None = None,
             pedido_id: str | None = None) -> Movimiento:
    if creditos <= 0:
        raise ValueError("una recarga debe sumar créditos")
    return _mov(s, espacio, "recarga", creditos, "recarga", nota=nota, pedido_id=pedido_id,
                usuario_id=usuario.id if usuario else None,
                precio_cliente_usd=creditos * precios.VALOR_CREDITO_USD)


def dar_bono(s: Session, espacio: Espacio, creditos: int, nota: str, usuario: Usuario | None = None) -> Movimiento:
    if creditos <= 0:
        raise ValueError("un bono debe sumar créditos")
    return _mov(s, espacio, "bono", creditos, "bono", nota=nota, usuario_id=usuario.id if usuario else None)


def ajustar(s: Session, espacio: Espacio, creditos: int, nota: str, admin: Usuario) -> list[Movimiento]:
    """Ajuste manual de la administración (con su razón). Si resta, sale de las bolsas en orden."""
    if not nota.strip():
        raise ValueError("un ajuste manual necesita una razón")
    if creditos >= 0:
        return [_mov(s, espacio, "ajuste", creditos, "recarga", nota=nota, usuario_id=admin.id)]
    return [_mov(s, espacio, "ajuste", -n, b, nota=nota, usuario_id=admin.id)
            for b, n in _repartir(s, espacio, -creditos)]


def bienvenida(s: Session, espacio: Espacio) -> list[Movimiento]:
    """Bono de bienvenida y, para los primeros N registros, un video completo gratis."""
    dados = []
    b = precios.ajuste(s, "bienvenida") or {}
    if b.get("creditos"):
        dados.append(dar_bono(s, espacio, int(b["creditos"]), b.get("nota", "Bienvenida")))
    promo = precios.ajuste(s, "promo_primeros") or {}
    if promo.get("cupo") and 0 < espacio.numero_registro <= int(promo["cupo"]):
        creditos = int(promo["minutos"] * precios.precio(s, promo.get("precio", "video_minuto")).creditos)
        dados.append(dar_bono(s, espacio, creditos, promo.get("nota", "Promo primeros registros")))
    return dados


def renovar_plan(s: Session, espacio: Espacio, plan: Plan) -> list[Movimiento]:
    """Créditos del mes del plan; lo que sobra se acumula hasta el tope (2 meses del plan)."""
    movs = [_mov(s, espacio, "recarga", plan.creditos_mes, "plan", nota=f"Plan {plan.nombre}: créditos del mes",
                 precio_cliente_usd=plan.precio_usd_mes)]
    tope = int(plan.creditos_mes * plan.tope_acumulado_meses)
    sobra = saldo_por_bolsa(s, espacio)["plan"] - tope
    if sobra > 0:
        movs.append(_mov(s, espacio, "vencimiento", -sobra, "plan",
                         nota=f"Tope de acumulación: {plan.tope_acumulado_meses:g} meses del plan"))
    return movs


# ------------------------------------------------------------------ gastos

def cotizar(s: Session, espacio: Espacio, accion: str, cantidad: float = 1.0,
            costo_real_usd: float | None = None) -> Cotizacion:
    p = precios.precio(s, accion)
    lista = int(math.ceil(p.creditos * cantidad))
    costo = float(costo_real_usd if costo_real_usd is not None else p.costo_ref_usd * cantidad)
    a_costo = _a_costo(s, espacio)
    return Cotizacion(accion=accion, cantidad=cantidad, creditos=precios.creditos_de_usd(costo) if a_costo else lista,
                      precio_cliente_creditos=lista, precio_cliente_usd=round(lista * precios.VALOR_CREDITO_USD, 4),
                      costo_real_usd=round(costo, 6), a_costo=a_costo)


def reservar(s: Session, espacio: Espacio, accion: str, cantidad: float = 1.0, usuario: Usuario | None = None,
             video_id: str | None = None, costo_estimado_usd: float | None = None,
             con_margen: bool = True) -> Reserva:
    """Aparta los créditos ANTES de gastar. Si no alcanzan, no arranca (SaldoInsuficiente)."""
    cot = cotizar(s, espacio, accion, cantidad, costo_estimado_usd)
    factor = float((precios.ajuste(s, "margen_reserva") or {}).get("factor", 1.15)) if con_margen else 1.0
    total = int(math.ceil(cot.creditos * factor))
    try:
        reparto = _repartir(s, espacio, total)
    except SaldoInsuficiente as ex:
        raise SaldoInsuficiente(ex.faltan, total, cot) from None
    r = Reserva(espacio_id=espacio.id, usuario_id=usuario.id if usuario else None, accion=accion, video_id=video_id,
                creditos=total, costo_estimado_usd=cot.costo_real_usd,
                detalle={"reparto": reparto, "cotizacion": cot.como_dict()})
    s.add(r)
    s.flush()
    for b, n in reparto:
        _mov(s, espacio, "reserva", -n, b, accion=accion, cantidad=cantidad, video_id=video_id, reserva_id=r.id,
             usuario_id=r.usuario_id, nota="Créditos apartados antes de empezar")
    return r


def _liberar(s: Session, espacio: Espacio, r: Reserva, nota: str) -> None:
    for b, n in r.detalle.get("reparto", []):
        _mov(s, espacio, "liberacion", n, b, accion=r.accion, video_id=r.video_id, reserva_id=r.id,
             usuario_id=r.usuario_id, nota=nota)


def cerrar(s: Session, r: Reserva, cantidad_real: float, costo_real_usd: float, nota: str = "") -> list[Movimiento]:
    """Se cobra lo real y se libera lo apartado. Si lo real pasa lo reservado y no hay saldo
    para la diferencia, se cobra lo que alcance y queda anotado (nunca queda saldo negativo)."""
    if r.estado != "abierta":
        raise ValueError(f"la reserva ya está {r.estado}")
    espacio = s.get(Espacio, r.espacio_id)
    _liberar(s, espacio, r, "Se libera lo apartado para cobrar lo real")
    cot = cotizar(s, espacio, r.accion, cantidad_real, costo_real_usd)
    disponible = saldo(s, espacio)
    cobrar = min(cot.creditos, max(0, disponible))
    movs = []
    if cobrar:
        reparto = _repartir(s, espacio, cobrar)
        for b, n in reparto:
            parte = n / cobrar
            movs.append(_mov(s, espacio, "consumo", -n, b, accion=r.accion, cantidad=cantidad_real,
                             video_id=r.video_id, reserva_id=r.id, usuario_id=r.usuario_id,
                             costo_real_usd=round(cot.costo_real_usd * parte, 6),
                             precio_cliente_usd=round(cot.precio_cliente_usd * parte, 4),
                             nota=nota + (" · cobro parcial: el saldo no alcanzó para todo" if cobrar < cot.creditos
                                          else "")))
    else:
        movs.append(_mov(s, espacio, "consumo", 0, "recarga", accion=r.accion, cantidad=cantidad_real,
                         video_id=r.video_id, reserva_id=r.id, costo_real_usd=cot.costo_real_usd,
                         precio_cliente_usd=cot.precio_cliente_usd, nota="Sin saldo para cobrar"))
    r.estado, r.cerrado = "cerrada", ahora()
    r.detalle = {**r.detalle, "cobrado": cobrar, "cotizacion_real": cot.como_dict()}
    return movs


def cancelar(s: Session, r: Reserva, motivo: str, costo_real_usd: float = 0.0) -> None:
    """Falló por el sistema o por el proveedor: se devuelve todo lo apartado. Si el proveedor
    igual cobró algo, se anota como costo (0 créditos) para que el margen sea verdadero."""
    if r.estado != "abierta":
        return
    espacio = s.get(Espacio, r.espacio_id)
    _liberar(s, espacio, r, f"Devuelto: {motivo}")
    if costo_real_usd:
        _mov(s, espacio, "consumo", 0, "recarga", accion=r.accion, video_id=r.video_id, reserva_id=r.id,
             costo_real_usd=round(costo_real_usd, 6), nota=f"Costo del proveedor sin cobrar al cliente: {motivo}")
    r.estado, r.cerrado = "cancelada", ahora()
    r.detalle = {**r.detalle, "motivo": motivo}


def devolver(s: Session, espacio: Espacio, creditos: int, motivo: str, video_id: str | None = None,
             bolsa: str = "recarga") -> Movimiento:
    """Devolución después de cobrar (ej. una imagen que no se generó por error del proveedor)."""
    return _mov(s, espacio, "devolucion", creditos, bolsa, video_id=video_id, nota=motivo)


# ------------------------------------------------------------------ consultas

def historial(s: Session, espacio: Espacio, video_id: str | None = None, limite: int = 200) -> list[Movimiento]:
    q = select(Movimiento).where(Movimiento.espacio_id == espacio.id)
    if video_id:
        q = q.where(Movimiento.video_id == video_id)
    return list(s.scalars(q.order_by(Movimiento.creado.desc()).limit(limite)))


def margen(s: Session, espacio_id: str | None = None) -> dict:
    """Créditos cobrados vs costo real de los proveedores (por espacio o en total)."""
    q = select(func.coalesce(func.sum(-Movimiento.creditos), 0), func.coalesce(func.sum(Movimiento.costo_real_usd), 0),
               func.coalesce(func.sum(Movimiento.precio_cliente_usd), 0)).where(Movimiento.tipo == "consumo")
    if espacio_id:
        q = q.where(Movimiento.espacio_id == espacio_id)
    creditos, costo, lista = s.execute(q).one()
    cobrado = creditos * precios.VALOR_CREDITO_USD
    return {"creditos_cobrados": int(creditos), "cobrado_usd": round(cobrado, 2), "costo_real_usd": round(costo, 2),
            "margen_usd": round(cobrado - costo, 2), "precio_lista_usd": round(lista, 2),
            "margen_pct": round((cobrado - costo) / cobrado * 100, 1) if cobrado else None}


# ------------------------------------------------------------------ pedidos (gancho de la pasarela)

def crear_pedido(s: Session, espacio: Espacio, tipo: str, referencia: str):
    """Pedido de recarga (paquete) o de plan. La pasarela (cuando exista) cobrará este pedido y
    luego llamará a confirmar_pedido; hoy no se cobra nada real."""
    from .modelos import Paquete, Pedido

    if tipo == "paquete":
        p = s.get(Paquete, referencia)
        if p is None or not p.activo:
            raise KeyError("ese paquete no existe")
        precio_usd, creditos_ = p.precio_usd, p.creditos
    elif tipo == "plan":
        p = s.get(Plan, referencia)
        if p is None or not p.activo:
            raise KeyError("ese plan no existe")
        precio_usd, creditos_ = p.precio_usd_mes, p.creditos_mes
    else:
        raise ValueError("tipo de pedido desconocido")
    pedido = Pedido(espacio_id=espacio.id, tipo=tipo, referencia=referencia, precio_usd=precio_usd, creditos=creditos_)
    s.add(pedido)
    s.flush()
    return pedido


def confirmar_pedido(s: Session, pedido_id: str, pasarela: str, referencia_externa: str) -> list[Movimiento]:
    """El pago se confirmó. Idempotente: si la pasarela avisa dos veces, se acredita una sola."""
    from .modelos import Pedido, Suscripcion

    pedido = s.get(Pedido, pedido_id)
    if pedido is None:
        raise KeyError("pedido no encontrado")
    if pedido.estado == "pagado":
        return []
    espacio = s.get(Espacio, pedido.espacio_id)
    pedido.estado, pedido.pasarela, pedido.referencia_externa = "pagado", pasarela, referencia_externa
    if pedido.tipo == "paquete":
        return [recargar(s, espacio, pedido.creditos, f"Recarga {pedido.referencia}", pedido_id=pedido.id)]
    plan = s.get(Plan, pedido.referencia)
    sus = s.scalar(select(Suscripcion).where(Suscripcion.espacio_id == espacio.id))
    if sus is None:
        s.add(Suscripcion(espacio_id=espacio.id, plan_clave=plan.clave, estado="activa",
                          referencia_externa=referencia_externa))
    else:
        sus.plan_clave, sus.estado, sus.periodo_inicio = plan.clave, "activa", ahora()
    return renovar_plan(s, espacio, plan)
