"""Copia de seguridad: completa, verificada, antes de migrar; si falla, no se migra nada."""
import json
import sqlite3

import pytest

from estudio.config import ruta_proyectos
from estudio.plataforma import copias, db, local


def _proyecto_con_archivos():
    p = ruta_proyectos() / "peces"
    (p / "imagenes").mkdir(parents=True)
    (p / "audio").mkdir()
    (p / "render").mkdir()
    (p / "proyecto.json").write_text(json.dumps({"slug": "peces", "titulo": "Peces", "canal": "animales-peligrosos",
                                                 "estilo": "enciclopedia_mascota", "duracion_objetivo_seg": 540,
                                                 "creado": "2026-09-28T00:00:00+00:00"}), "utf-8")
    (p / "imagenes" / "escena_001.png").write_bytes(b"x" * 5000)
    (p / "audio" / "voz.wav").write_bytes(b"y" * 7000)
    (p / "render" / "final.mp4").write_bytes(b"z" * 9000)
    return p


def test_copia_completa_y_verificada(tmp_path):
    _proyecto_con_archivos()
    db.preparar()
    info = copias.hacer_copia("prueba")
    d = tmp_path / "copias"
    assert info["carpeta"].startswith(str(d))
    copia = next(d.iterdir())
    for f in ("proyectos/peces/imagenes/escena_001.png", "proyectos/peces/audio/voz.wav",
              "proyectos/peces/render/final.mp4", "datos/xandart.db", "copia.json"):
        assert (copia / f).exists(), f
    assert sqlite3.connect(copia / "datos" / "xandart.db").execute("select count(*) from alembic_version").fetchone()[0] == 1
    assert info["partes"]["proyectos"]["archivos"] == 4
    assert copias.listar()[0]["motivo"] == "prueba"


def test_la_plataforma_copia_antes_de_migrar_y_no_toca_los_proyectos(tmp_path, monkeypatch):
    p = _proyecto_con_archivos()
    antes = sorted(str(f.relative_to(p)) for f in p.rglob("*"))
    monkeypatch.delenv("XANDART_SIN_MIGRAR")
    local.olvidar()
    try:
        local.preparar()
        assert local.estado()["fase"] == "listo", local.estado()
        assert local.espacio()
        assert copias.listar()[0]["motivo"] == "antes_de_la_plataforma"
        assert sorted(str(f.relative_to(p)) for f in p.rglob("*")) == antes      # nada se movió ni se borró
        local.olvidar()
        local.preparar()                                                        # otra vez: no repite la copia
        assert len(copias.listar()) == 1
    finally:
        local.olvidar()


def test_si_la_copia_falla_no_se_migra(monkeypatch):
    _proyecto_con_archivos()
    monkeypatch.delenv("XANDART_SIN_MIGRAR")
    local.olvidar()
    try:
        with pytest.MonkeyPatch.context() as sin_disco:
            sin_disco.setattr(copias.shutil, "disk_usage", lambda _: type("U", (), {"free": 0})())
            local.preparar()
        e = local.estado()
        assert e["fase"] == "error" and "espacio" in e["error"] and local.espacio() is None
        db.preparar()
        with db.sesion() as s:
            from estudio.plataforma.modelos import Canal

            assert s.query(Canal).count() == 0                                   # no se registró nada
    finally:
        local.olvidar()


def test_actualizar_una_base_con_datos_hace_copia_primero(tmp_path, monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    db.motor()
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(db.__file__).with_name("migraciones")))
    cfg.set_main_option("sqlalchemy.url", db.url())
    command.upgrade(cfg, "0002")                                                # una base «vieja»
    db._PREPARADAS.discard(db.url())
    db.preparar()
    hechas = copias.listar()
    assert len(hechas) == 1 and hechas[0]["motivo"] == "antes_de_actualizar_la_base"
    assert list(hechas[0]["partes"]) == ["base_de_datos"]


def test_la_copia_se_repite_si_cambia_la_carpeta_de_videos(tmp_path, monkeypatch):
    monkeypatch.delenv("XANDART_SIN_MIGRAR")
    local.olvidar()
    try:
        local.preparar()                                   # primera vez: carpeta de videos vacía
        assert len(copias.listar()) == 1
        otra = tmp_path / "videos_de_siempre"
        monkeypatch.setenv("ESTUDIO_PROYECTOS", str(otra))
        _proyecto_con_archivos()
        local.olvidar()
        local.preparar()                                   # ahora con los videos de verdad: copia otra vez
        hechas = copias.listar()
        assert len(hechas) == 2 and hechas[0]["partes"]["proyectos"]["archivos"] == 4
    finally:
        local.olvidar()
