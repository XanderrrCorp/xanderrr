"""Cobro en créditos de la producción: apartar antes, cobrar lo real, devolver si falla."""
import pytest

from estudio.config import ConfigCostos
from estudio.plataforma import cobro, contexto, creditos as cr, db, precios
from estudio.plataforma.cuentas import cuenta_local, registrar
from estudio.plataforma.modelos import Espacio, Reserva
from estudio.proyecto import CarpetaProyecto


def _cliente(saldo: int) -> str:
    db.preparar()
    with db.sesion() as s:
        precios.sembrar(s)
        _, e = registrar(s, "cliente@ejemplo.com", "Cliente")
        cr.recargar(s, e, saldo - cr.saldo(s, e), "prueba")
        return e.id


def _video(tmp_path, minutos=9):
    return CarpetaProyecto.crear("Ranas venenosas", "mi-canal", "enciclopedia_mascota", minutos * 60, slug="ranas")


def _gastar(c, usd):
    c.libro(ConfigCostos.cargar()).registrar(modulo="imagenes", proveedor="x", modelo="y", unidades={"n": 1},
                                             costo_usd=usd)


def _saldo(esp):
    with db.sesion() as s:
        return cr.saldo(s, s.get(Espacio, esp))


def test_video_aparta_antes_y_cobra_los_minutos_reales(tmp_path):
    esp = _cliente(3000)
    c = _video(tmp_path)
    with contexto.usar_espacio(esp):
        apartado = cobro.abrir_video(c.ruta, 9)
        assert apartado["creditos"] == 1501                       # 9 × 145 × 1,15
        assert cobro.abrir_video(c.ruta, 9)["reserva"] == apartado["reserva"]   # no aparta dos veces
        assert _saldo(esp) == 3000 - 1501
        _gastar(c, 2.5)
        r = cobro.cerrar_video(c.ruta, 8.5)
        assert r["cobrado"] == 1233 and r["costo_real_usd"] == pytest.approx(2.5)   # 8,5 × 145
        assert cobro.cerrar_video(c.ruta, 8.5) is None           # volver a renderizar no cobra otra vez
    assert _saldo(esp) == 3000 - 1233


def test_sin_saldo_el_video_no_arranca(tmp_path):
    esp = _cliente(100)
    c = _video(tmp_path)
    with contexto.usar_espacio(esp), pytest.raises(cr.SaldoInsuficiente):
        cobro.abrir_video(c.ruta, 9)
    assert _saldo(esp) == 100


def test_accion_que_falla_devuelve_lo_apartado_y_anota_el_costo(tmp_path):
    esp = _cliente(500)
    c = _video(tmp_path)
    with contexto.usar_espacio(esp):
        with pytest.raises(RuntimeError), cobro.accion(c.ruta, "miniatura"):
            assert _saldo(esp) == 500 - 69                        # 60 × 1,15 apartados
            _gastar(c, 0.08)
            raise RuntimeError("el proveedor no respondió")
        assert _saldo(esp) == 500
        with cobro.accion(c.ruta, "imagen_regenerada"):
            _gastar(c, 0.04)
        assert _saldo(esp) == 490
    with db.sesion() as s:
        m = cr.margen(s, esp)
        assert m["costo_real_usd"] == pytest.approx(0.12)           # lo que el proveedor cobró, aunque falló
        estados = sorted(r.estado for r in s.query(Reserva))
        assert estados == ["cancelada", "cerrada"]


def test_la_cuenta_del_dueno_no_se_frena_por_saldo(tmp_path):
    db.preparar()
    with db.sesion() as s:
        precios.sembrar(s)
        esp = cuenta_local(s)[1].id
    c = _video(tmp_path)
    with contexto.usar_espacio(esp):
        cobro.abrir_video(c.ruta, 9)                               # sin créditos cargados: igual arranca
        _gastar(c, 3.0)
        cobro.cerrar_video(c.ruta, 9)
    with db.sesion() as s:
        m = cr.margen(s, esp)
        assert m["costo_real_usd"] == pytest.approx(3.0) and m["precio_lista_usd"] == pytest.approx(13.05)


def test_sin_espacio_no_cobra_nada(tmp_path):
    c = _video(tmp_path)
    assert cobro.abrir_video(c.ruta, 9) is None
    with cobro.accion(c.ruta, "miniatura"):
        pass
