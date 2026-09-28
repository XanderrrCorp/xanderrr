"""Base multiusuario: cada cosa tiene dueño, el catálogo público es de solo lectura."""
import pytest

from estudio.plataforma import almacen, db
from estudio.plataforma.cuentas import SinPermiso, cuenta_local, espacio_de, registrar
from estudio.plataforma.modelos import Estilo
from estudio.plataforma.recursos import borrar, duplicar, listar, obtener


@pytest.fixture
def s():
    db.preparar()
    with db.sesion() as sesion:
        yield sesion


def test_la_base_se_crea_con_migraciones(s):
    import sqlalchemy as sa

    tablas = set(sa.inspect(db.motor()).get_table_names())
    assert {"usuarios", "espacios", "estilos", "canales", "videos", "movimientos", "reservas", "precios"} <= tablas
    db.preparar()                                      # correrlo dos veces no rompe nada


def test_cuenta_local_del_dueno(s):
    u, e = cuenta_local(s)
    assert u.rol == "ceo" and u.a_costo and e.dueno_id == u.id
    u2, e2 = cuenta_local(s)
    assert (u2.id, e2.id) == (u.id, e.id)             # siempre la misma


def test_catalogo_publico_solo_lectura_y_privado_por_espacio(s):
    _, mio = cuenta_local(s)
    _, otro = registrar(s, "cliente@ejemplo.com", "Cliente")
    publico = Estilo(espacio_id=None, clave="acuarela", nombre="Acuarela", datos={"a": 1})
    privado = Estilo(espacio_id=otro.id, clave="secreto", nombre="Secreto", datos={})
    s.add_all([publico, privado])
    s.flush()
    assert [x.clave for x in listar(s, Estilo, mio)] == ["acuarela"]          # lo del otro no se ve
    with pytest.raises(SinPermiso):
        obtener(s, Estilo, privado.id, mio)
    with pytest.raises(SinPermiso):
        obtener(s, Estilo, publico.id, mio, para_editar=True)                  # el catálogo no se edita
    copia = duplicar(s, publico, mio)
    assert copia.espacio_id == mio.id and copia.datos == {"a": 1} and copia.origen["duplicado_de"] == publico.id
    copia.datos["a"] = 2
    assert publico.datos == {"a": 1}                                           # la copia es independiente
    borrar(s, Estilo, copia.id, mio)
    assert [x.clave for x in listar(s, Estilo, mio)] == ["acuarela"]


def test_espacio_ajeno_no_se_puede_abrir(s):
    u, _ = cuenta_local(s)
    _, otro = registrar(s, "otra@ejemplo.com")
    with pytest.raises(SinPermiso):
        espacio_de(s, u, otro.id)


def test_almacen_no_se_sale_del_espacio(s):
    _, e = cuenta_local(s)
    assert almacen.ruta(e.id, "videos", "a.mp4").is_relative_to(almacen.raiz_espacio(e.id))
    for malo in ("..", "../x", "/etc", "a/b"):
        with pytest.raises(ValueError):
            almacen.ruta(e.id, malo)


def test_preparar_la_base_desde_varias_peticiones_a_la_vez():
    """La página nueva pide varias cosas a la vez: la base se migra una sola vez, sin chocar."""
    import threading

    from estudio.plataforma import db

    errores = []

    def preparar():
        try:
            db.preparar()
        except Exception as ex:  # noqa: BLE001
            errores.append(ex)

    hilos = [threading.Thread(target=preparar) for _ in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert errores == []


def test_cuenta_del_dueno_desde_dos_hilos_a_la_vez():
    """La página y la preparación piden la cuenta del dueño a la vez: sale una sola, sin error."""
    import threading

    from estudio.plataforma.cuentas import cuenta_local
    from estudio.plataforma.modelos import Usuario

    db.preparar()
    errores, ids = [], []

    def pedir():
        try:
            with db.sesion() as s:
                ids.append(cuenta_local(s)[1].id)
        except Exception as ex:  # noqa: BLE001
            errores.append(ex)

    hilos = [threading.Thread(target=pedir) for _ in range(6)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert errores == [] and len(set(ids)) == 1
    with db.sesion() as s:
        assert s.query(Usuario).count() == 1
