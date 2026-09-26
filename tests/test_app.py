"""La página local: estado, crear un video (sin gastar) y seguridad de rutas."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTUDIO_PROYECTOS", str(tmp_path / "proy"))
    monkeypatch.setenv("HOME", str(tmp_path))
    from estudio import app as modulo, pipeline

    # el guion no se escribe de verdad: no hay Claude en las pruebas
    monkeypatch.setattr(pipeline, "lanzar", lambda slug, paso, f: None)
    return TestClient(modulo.app)


def test_portada_y_estado(cliente):
    assert "Xandart" in cliente.get("/").text
    assert cliente.get("/web/xandart.js").status_code == 200
    e = cliente.get("/api/estado").json()
    assert set(e["claves"]) == {"together", "minimax", "pexels"} and e["videos"] == []


def test_crear_video_y_verlo(cliente):
    r = cliente.post("/api/videos", json={"tema": "Arañas de la casa", "giro": "g", "villano": "v", "minutos": 9})
    assert r.status_code == 200
    v = r.json()
    assert v["minutos"] == 9 and v["video"] is None
    assert cliente.get(f"/api/videos/{v['slug']}").json()["titulo"]
    assert [x["slug"] for x in cliente.get("/api/estado").json()["videos"]] == [v["slug"]]
    # la mascota del canal se copia sin pagar
    assert cliente.get(f"/archivos/{v['slug']}/assets/mascota_base.png").status_code == 200


def test_rutas_no_salen_del_proyecto(cliente):
    v = cliente.post("/api/videos", json={"tema": "Escorpiones", "minutos": 8}).json()
    assert cliente.get(f"/archivos/{v['slug']}/../../etc/passwd").status_code == 404
    assert cliente.get("/web/..%2Fapp.py").status_code == 404
    assert cliente.get("/api/videos/no-existe").status_code == 404


def test_importar_zip_y_probar_10_escenas(cliente, monkeypatch):
    """Punto 4: el escenas.json de alacranes (en .zip) entra por la página y la
    prueba de las primeras escenas deja costo, proyección y hoja de contacto."""
    import io
    import zipfile
    from pathlib import Path

    from estudio import pipeline
    from estudio.config import RAIZ
    from estudio.imagenes import generador

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("video_alacranes/escenas.json", (Path(__file__).parent / "fixtures" / "escenas_v1_sintetico.json").read_text("utf-8"))
        z.writestr("video_alacranes/guion.md", "# guion")
    r = cliente.post("/api/importar", files={"archivo": ("video_alacranes.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["pasos"]["guionista"] == "completo" and v["escenas"]
    assert v["estimacion_imagenes"]["prueba"] >= 1

    original = generador.crear_proveedor
    monkeypatch.setattr(generador, "crear_proveedor", lambda config, ajustes, nombre=None: original(config, ajustes, "simulado"))
    c = pipeline.CarpetaProyecto.abrir(v["slug"])
    datos = pipeline.paso_prueba(c, pipeline.Trabajo("prueba"), 10)
    assert datos["generadas"] >= 1 and datos["proyeccion"] and datos["hoja"]
    assert (c.ruta / datos["hoja"]).exists()
    assert cliente.get(f"/api/videos/{v['slug']}").json()["prueba"]["escenas"] == 10
    # la prueba no da por terminadas las imágenes del video
    assert c.cargar().pasos["assets"].estado != "completo"
    assert RAIZ  # (sin gasto real: proveedor simulado)


def test_importar_rechaza_basura(cliente):
    r = cliente.post("/api/importar", files={"archivo": ("x.json", b"no es json", "application/json")})
    assert r.status_code == 400
