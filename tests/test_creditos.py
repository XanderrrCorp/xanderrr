"""Libro de créditos: el saldo sale del libro; reservar, cobrar lo real, devolver si falla."""
import pytest

from estudio.plataforma import creditos as cr
from estudio.plataforma import db, precios
from estudio.plataforma.cuentas import cuenta_local, registrar
from estudio.plataforma.modelos import Movimiento, Plan


@pytest.fixture
def s():
    db.preparar()
    with db.sesion() as sesion:
        precios.sembrar(sesion)
        yield sesion


@pytest.fixture
def cliente(s):
    _, e = registrar(s, "cliente@ejemplo.com", "Cliente")
    return e


def test_saldo_es_la_suma_del_libro(s, cliente):
    cr.recargar(s, cliente, 1000, "prueba")
    cr.dar_bono(s, cliente, 200, "regalo")
    assert cr.saldo(s, cliente) == 1200
    assert cr.saldo_por_bolsa(s, cliente) == {"plan": 0, "bono": 200, "recarga": 1000}


def test_bienvenida_y_promo_primeros_50(s):
    _, e = registrar(s, "uno@ejemplo.com")
    cr.bienvenida(s, e)
    video_min = precios.precio(s, "video_minuto").creditos
    assert cr.saldo(s, e) == 300 + 8 * video_min                       # bono + 1 video de 8 min gratis
    e.numero_registro = 51
    _, e2 = registrar(s, "dos@ejemplo.com")
    e2.numero_registro = 51
    cr.bienvenida(s, e2)
    assert cr.saldo(s, e2) == 300                                       # fuera del cupo: solo bienvenida


def test_reserva_cobro_real_y_liberacion(s, cliente):
    cr.recargar(s, cliente, 2000, "prueba")
    r = cr.reservar(s, cliente, "video_minuto", 9)                      # 9 min × 145 × 1,15 de margen
    assert r.creditos == 1501 and cr.saldo(s, cliente) == 2000 - 1501
    cr.cerrar(s, r, cantidad_real=8.5, costo_real_usd=4.1)
    assert cr.saldo(s, cliente) == 2000 - 1233                          # se cobró 8,5 min y se liberó el resto
    consumo = s.query(Movimiento).filter_by(tipo="consumo").one()
    assert consumo.costo_real_usd == pytest.approx(4.1) and consumo.precio_cliente_usd == pytest.approx(12.33)


def test_sin_saldo_no_arranca(s, cliente):
    cr.recargar(s, cliente, 100, "poco")
    with pytest.raises(cr.SaldoInsuficiente) as ex:
        cr.reservar(s, cliente, "video_minuto", 9)
    assert ex.value.faltan == 1501 - 100 and "Recarga" in str(ex.value)
    assert cr.saldo(s, cliente) == 100                                  # no se tocó nada


def test_falla_del_proveedor_devuelve_todo(s, cliente):
    cr.recargar(s, cliente, 500, "prueba")
    r = cr.reservar(s, cliente, "miniatura")
    cr.cancelar(s, r, "Together no respondió", costo_real_usd=0.08)
    assert cr.saldo(s, cliente) == 500 and r.estado == "cancelada"
    assert cr.margen(s, cliente.id)["costo_real_usd"] == pytest.approx(0.08)   # el costo igual se ve


def test_bolsas_se_gastan_en_orden_y_plan_acumula_hasta_2_meses(s, cliente):
    lite = s.get(Plan, "lite")
    cr.recargar(s, cliente, 100, "comprado")
    cr.renovar_plan(s, cliente, lite)
    r = cr.reservar(s, cliente, "miniatura", con_margen=False)
    cr.cerrar(s, r, 1, 0.3)
    assert cr.saldo_por_bolsa(s, cliente) == {"plan": 2900 - 60, "bono": 0, "recarga": 100}   # sale del plan
    for _ in range(3):                                                  # 3 meses sin gastar
        cr.renovar_plan(s, cliente, lite)
    assert cr.saldo_por_bolsa(s, cliente)["plan"] == 2 * 2900          # tope: 2 meses del plan
    assert cr.saldo_por_bolsa(s, cliente)["recarga"] == 100            # lo comprado nunca vence


def test_cuenta_del_dueno_paga_a_costo(s):
    _, e = cuenta_local(s)
    cr.recargar(s, e, 1600, "Recarga de Together")
    cot = cr.cotizar(s, e, "video_minuto", 9, costo_real_usd=3.6)
    assert cot.a_costo and cot.creditos == 360 and cot.precio_cliente_creditos == 1305
    r = cr.reservar(s, e, "video_minuto", 9, costo_estimado_usd=3.6)
    cr.cerrar(s, r, 9, 3.4)
    assert cr.saldo(s, e) == 1600 - 340
    m = cr.margen(s, e.id)
    assert m["costo_real_usd"] == pytest.approx(3.4) and m["precio_lista_usd"] == pytest.approx(13.05)


def test_ajuste_manual_pide_razon(s, cliente):
    admin, _ = cuenta_local(s)
    with pytest.raises(ValueError):
        cr.ajustar(s, cliente, 50, "  ", admin)
    cr.ajustar(s, cliente, 50, "compensación por error", admin)
    assert cr.saldo(s, cliente) == 50


def test_aviso_saldo_bajo(s, cliente):
    assert cr.saldo_bajo(s, cliente)
    cr.recargar(s, cliente, 1000, "x")
    assert not cr.saldo_bajo(s, cliente)


def test_pedido_de_recarga_se_acredita_una_sola_vez(s, cliente):
    pedido = cr.crear_pedido(s, cliente, "paquete", "recarga_10")
    assert pedido.estado == "pendiente" and cr.saldo(s, cliente) == 0     # sin pago no hay créditos
    cr.confirmar_pedido(s, pedido.id, "pasarela_prueba", "tx-1")
    cr.confirmar_pedido(s, pedido.id, "pasarela_prueba", "tx-1")           # la pasarela avisa dos veces
    assert cr.saldo(s, cliente) == 1000
    plan = cr.crear_pedido(s, cliente, "plan", "starter")
    cr.confirmar_pedido(s, plan.id, "pasarela_prueba", "tx-2")
    assert cr.saldo_por_bolsa(s, cliente)["plan"] == 6525
