"""Bloque 1 (21-10): avisos de video listo o fallido, estado de la copia de seguridad y «Reportar problema»."""
import json
import time

from fastapi.testclient import TestClient

from estudio import app as modulo_app
from estudio import avisos, pipeline
from estudio.plataforma import db


def test_video_listo_y_video_fallido_dejan_aviso(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "carpeta_videos", lambda: tmp_path / "videos")
    (tmp_path / "videos").mkdir()
    correos = []
    monkeypatch.setattr(avisos, "_correo", lambda a, para=None: correos.append(a["titulo"]))
    t = pipeline.Trabajo("video")
    assert avisos.al_terminar("mi-video", t) is None                         # sin video nuevo: nada
    (tmp_path / "videos" / "mi_video.mp4").write_bytes(b"x")
    a = avisos.al_terminar("mi-video", t)
    assert a["tipo"] == "listo" and "mi_video.mp4" in a["texto"] and a["enlace"] == "/app/videos/mi-video"
    t2 = pipeline.Trabajo("imagenes"); t2.error = "Google no respondió"
    assert avisos.al_terminar("otro", t2)["tipo"] == "error"
    assert avisos.al_terminar("personaje~abc", t2) is None                   # los del asistente se ven en su pantalla
    assert avisos.al_terminar("mi-video~miniatura", t2) is None
    assert len(correos) == 2 and len(avisos.listar()) == 2
    avisos.marcar_leidos()
    assert all(x["leido"] for x in avisos.listar())


def test_lanzar_avisa_al_terminar(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "carpeta_videos", lambda: tmp_path)
    monkeypatch.setattr(avisos, "_correo", lambda a, para=None: None)
    t = pipeline.lanzar("prueba-aviso", "video", lambda t: (tmp_path / "final.mp4").write_bytes(b"x"))
    for _ in range(100):
        if not t.activo:
            break
        time.sleep(0.05)
    time.sleep(0.1)
    assert avisos.listar()[0]["tipo"] == "listo"


def test_aviso_del_respaldo(tmp_path):
    cli = TestClient(modulo_app.app)
    assert cli.get("/api/v2/respaldo").json()["estado"] == "ninguna"
    db.carpeta_datos().mkdir(parents=True, exist_ok=True)
    nota = db.carpeta_datos() / "ultima_copia_migracion.json"
    nota.write_text(json.dumps({"carpeta": str(tmp_path), "fecha": "x", "total_bytes": 10}), encoding="utf-8")
    r = cli.get("/api/v2/respaldo").json()
    assert r["estado"] == "ok" and r["carpeta"] == str(tmp_path) and not r.get("visto")
    assert cli.post("/api/v2/respaldo/visto").json()["visto"] is True
    nota.write_text(json.dumps({"error": "No hay espacio", "migracion": "0006"}), encoding="utf-8")
    assert cli.get("/api/v2/respaldo").json()["estado"] == "error"


def test_si_la_copia_falla_no_se_migra_y_queda_anotado(monkeypatch):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    from estudio.plataforma import copias

    db.motor()
    cfg = Config()
    cfg.set_main_option("script_location", str(Path(db.__file__).with_name("migraciones")))
    cfg.set_main_option("sqlalchemy.url", db.url())
    command.upgrade(cfg, "0004")
    db._PREPARADAS.discard(db.url())

    def falla(*a, **k):
        raise copias.CopiaFallida("No hay espacio para la copia")

    monkeypatch.setattr(copias, "hacer_copia", falla)
    try:
        db.preparar()
        raise AssertionError("debía fallar")
    except copias.CopiaFallida:
        pass
    assert avisos.respaldo()["estado"] == "error"
    with db.motor().connect() as c:
        import sqlalchemy as sa
        assert c.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == "0004"   # no se tocó


def test_reportar_problema_guarda_lo_necesario_y_nada_de_claves(monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "clave-secreta-123")
    monkeypatch.setattr(avisos, "_correo", lambda a, para=None: None)
    t = pipeline.Trabajo("imagenes"); t.error = "falló Google"; t.registro = ["paso 1", "error: falló Google"]
    pipeline.TRABAJOS["video-roto"] = t
    cli = TestClient(modulo_app.app)
    assert cli.post("/api/v2/reportes", json={"texto": "se quedó cargando", "ruta": "/producir",
                                              "error": "/api/x → 500"}).status_code == 200
    (archivo,) = (db.carpeta_datos() / "reportes").glob("*.json")
    texto = archivo.read_text(encoding="utf-8")
    rep = json.loads(texto)
    assert rep["pantalla"] == "/producir" and rep["trabajos_con_error"][0]["trabajo"] == "video-roto"
    assert "clave-secreta-123" not in texto
    pipeline.TRABAJOS.pop("video-roto")
