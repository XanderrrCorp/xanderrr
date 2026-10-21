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
    assert u.rol == "owner" and u.a_costo and e.dueno_id == u.id
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


def test_migracion_0005_respaldo_completo_y_nada_se_pierde(tmp_path, monkeypatch):
    """(21-10) Una base con datos en 0004: antes de migrar se hace la copia COMPLETA (base + proyectos) y la
    migración solo agrega: roles traducidos, todo lo del dueño privado, catálogo público, lista negra inicial."""
    import json

    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    monkeypatch.delenv("XANDART_ORIGEN", raising=False)       # otra prueba pudo dejar fijada otra instalación
    proyecto = tmp_path / "proyectos" / "mi-video"
    proyecto.mkdir(parents=True)
    (proyecto / "guion.md").write_text("hola", encoding="utf-8")
    db.motor()                                          # crea la carpeta de datos
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(db.__file__).with_name("migraciones")))
    cfg.set_main_option("sqlalchemy.url", db.url())
    command.upgrade(cfg, "0004")
    with db.motor().begin() as c:
        c.execute(sa.text("INSERT INTO usuarios (id, email, nombre, rol, a_costo, activo, creado, actualizado) VALUES "
                          "('u1', 'yo@x', 'Yo', 'ceo', 1, 1, '2026-01-01', '2026-01-01'), "
                          "('u2', 'otro@x', 'Otro', 'cliente', 0, 1, '2026-01-01', '2026-01-01')"))
        c.execute(sa.text("INSERT INTO espacios (id, nombre, dueno_id, moneda_vista, numero_registro, onboarding_hecho, "
                          "creado, actualizado) VALUES ('e1', 'Xandart', 'u1', 'USD', 1, 1, '2026-01-01', '2026-01-01')"))
        for id_, esp in (("s1", "'e1'"), ("s2", "NULL")):
            c.execute(sa.text(f"INSERT INTO estilos (id, espacio_id, clave, nombre, descripcion, datos, origen, archivado, "
                              f"creado, actualizado) VALUES ('{id_}', {esp}, 'k{id_}', 'N', '', '{{}}', '{{}}', 0, "
                              "'2026-01-01', '2026-01-01')"))
        c.execute(sa.text("INSERT INTO canales (id, espacio_id, clave, nombre, idioma, ajustes, archivado, creado, "
                          "actualizado) VALUES ('c1', 'e1', 'tracy', 'Tracy', 'es', '{}', 0, '2026-01-01', '2026-01-01')"))
    db._PREPARADAS.clear()
    db.preparar()
    info = json.loads((db.carpeta_datos() / "ultima_copia_migracion.json").read_text(encoding="utf-8"))
    copia = Path(info["carpeta"])
    assert info["migracion"] == "0005" and copia.parent == tmp_path / "copias"
    # (22-10) liviana: lo necesario para producir (base, configuración, estilos, módulos…) y NADA de los proyectos
    assert not (copia / "proyectos").exists() and (copia / "config").exists() and (copia / "modulo_tracy").exists()
    assert info["total_bytes"] < 200 * 2**20
    assert (copia / "datos" / "xandart.db").exists()
    with db.motor().connect() as c:
        roles = dict(c.execute(sa.text("SELECT email, rol FROM usuarios")).all())
        vis = dict(c.execute(sa.text("SELECT id, visibilidad FROM estilos")).all())
        canal = c.execute(sa.text("SELECT visibilidad FROM canales WHERE id = 'c1'")).scalar()
        negra = c.execute(sa.text("SELECT valor FROM lista_negra")).scalars().all()
        n_usuarios = c.execute(sa.text("SELECT count(*) FROM usuarios")).scalar()
    assert roles == {"yo@x": "owner", "otro@x": "beta"} and n_usuarios == 2
    assert vis == {"s1": "privado", "s2": "publico"} and canal == "privado"
    assert negra == ["@codigodelexito22"]
