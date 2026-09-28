"""Migración de la instalación de un solo usuario a datos de la cuenta del dueño."""
import json
import shutil

from sqlalchemy import select

from estudio.config import RAIZ
from estudio.plataforma import almacen, contexto, db
from estudio.plataforma.migrar import migrar_instalacion
from estudio.plataforma.modelos import Canal, Estilo, FormulaGuion, Personaje, PlantillaMiniatura, Video


def _instalacion_vieja(tmp_path):
    raiz = tmp_path / "instalacion"
    shutil.copytree(RAIZ / "estilos", raiz / "estilos")
    shutil.copytree(RAIZ / "canales", raiz / "canales")
    (raiz / "perfiles").mkdir(parents=True)
    shutil.copy(RAIZ / "perfiles" / "enciclopedia_ritmo_alto.json", raiz / "perfiles")
    proyectos = tmp_path / "proyectos"
    (proyectos / "peces").mkdir(parents=True)
    (proyectos / "peces" / "proyecto.json").write_text(json.dumps({
        "slug": "peces", "titulo": "Peces del Amazonas", "canal": "animales-peligrosos",
        "estilo": "enciclopedia_mascota", "duracion_objetivo_seg": 540, "creado": "2026-09-28T00:00:00+00:00"}), "utf-8")
    return raiz, proyectos


def test_migra_peligro_tropical_como_datos_del_dueno(tmp_path):
    raiz, proyectos = _instalacion_vieja(tmp_path)
    r = migrar_instalacion(raiz, proyectos)
    r2 = migrar_instalacion(raiz, proyectos)                          # otra vez: no duplica
    assert r["canales"] == ["Peligro Tropical"] and r2["videos"] == 1
    with db.sesion() as s:
        canal = s.scalar(select(Canal))
        assert s.query(Canal).count() == 1 and canal.espacio_id == r["espacio"]
        assert s.get(Estilo, canal.estilo_id).clave == "enciclopedia_mascota"
        assert s.get(Estilo, canal.estilo_id).espacio_id == r["espacio"]              # privado del dueño
        assert s.get(FormulaGuion, canal.formula_id).espacio_id is None               # fórmula del catálogo
        assert s.get(PlantillaMiniatura, canal.plantilla_miniatura_id).clave == "animales-peligrosos"
        assert s.get(Personaje, canal.personaje_id).datos["tipo"] == "presentador"
        assert canal.voz_id and canal.perfil_edicion_id
        video = s.scalar(select(Video))
        assert video.canal_id == canal.id and video.carpeta.endswith("peces")
    # los archivos quedaron en el espacio del dueño y el motor los encuentra ahí
    raiz_e = almacen.raiz_espacio(r["espacio"])
    assert (raiz_e / "estilos" / "enciclopedia_mascota" / "assets" / "presentador" / "clips").exists()
    with contexto.usar_espacio(r["espacio"]):
        from estudio.estilos import carpeta_estilo
        from estudio.miniaturas.plantilla import cargar, ruta_plantilla

        assert carpeta_estilo("enciclopedia_mascota").is_relative_to(raiz_e)
        assert ruta_plantilla("animales-peligrosos").is_relative_to(raiz_e)
        assert len(cargar("animales-peligrosos").referencias) == 3


def test_modo_local_peticiones_y_trabajos_corren_en_el_espacio_del_dueno(tmp_path, monkeypatch):
    """La página migra sola la primera vez; cada petición y cada trabajo usan el espacio del dueño."""
    import threading

    from fastapi.testclient import TestClient

    from estudio import app as modulo_app, pipeline
    from estudio.plataforma import local

    monkeypatch.delenv("XANDART_SIN_MIGRAR")
    local.olvidar()
    visto = {}

    @modulo_app.app.get("/api/_prueba_espacio")
    def _espacio_de_prueba():
        visto["peticion"] = contexto.espacio_actual()
        listo = threading.Event()

        def trabajo(t):
            visto["trabajo"] = contexto.espacio_actual()
            listo.set()

        pipeline.lanzar("_prueba", "prueba", trabajo)
        listo.wait(5)
        return {}

    try:
        TestClient(modulo_app.app).get("/api/_prueba_espacio")
    finally:
        modulo_app.app.router.routes.pop()
        local.olvidar()
    assert visto["peticion"] and visto["trabajo"] == visto["peticion"]
    assert contexto.espacio_actual() is None                           # no se queda pegado fuera


def test_video_nuevo_usa_el_canal_del_espacio_y_queda_registrado(tmp_path):
    from estudio import pipeline

    raiz, proyectos = _instalacion_vieja(tmp_path)
    r = migrar_instalacion(raiz, proyectos)
    with contexto.usar_espacio(r["espacio"]):
        c = pipeline.crear_video("Ranas venenosas", "", "", 9)
    p = c.cargar()
    assert p.canal == "animales-peligrosos" and p.estilo == "enciclopedia_mascota"
    with db.sesion() as s:
        v = s.scalar(select(Video).where(Video.slug == c.ruta.name))
        assert v.espacio_id == r["espacio"] and v.canal_id and v.minutos == 9


def test_formatos_del_catalogo_y_del_canal(tmp_path):
    from fastapi.testclient import TestClient

    from estudio import app as modulo_app
    from estudio.plataforma.modelos import Formato

    raiz, proyectos = _instalacion_vieja(tmp_path)
    r = migrar_instalacion(raiz, proyectos)
    assert r["catalogo"]["formatos"] >= 1
    with db.sesion() as s:
        f = s.scalar(select(Formato).where(Formato.clave == "escala_peligro"))
        assert f.espacio_id is None and f.datos["formula"] == "escala_peligro"
        canal = s.scalar(select(Canal))
        assert canal.formato_id == f.id and s.scalar(select(Video)).formato_id == f.id
    cli = TestClient(modulo_app.app)
    lista = cli.get("/api/v2/recursos/formatos").json()
    escala = next(x for x in lista if x["clave"] == "escala_peligro")
    assert escala["publico"] and escala["datos"]["duraciones_min"] == [6, 9, 11]
    copia = cli.post(f"/api/v2/recursos/formatos/{escala['id']}/duplicar", json={"nombre": "Mi escala"}).json()
    lista = cli.get("/api/v2/recursos/formatos").json()
    mio = next(x for x in lista if x["id"] == copia["id"])
    assert not mio["publico"] and mio["nombre"] == "Mi escala"              # la copia es privada y editable
