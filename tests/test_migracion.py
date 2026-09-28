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
