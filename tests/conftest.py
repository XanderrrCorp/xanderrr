import pytest

from estudio.config import ConfigCostos
from estudio.estilos import cargar_estilo, cargar_perfil_edicion


@pytest.fixture
def config():
    return ConfigCostos.cargar()


@pytest.fixture
def estilo():
    return cargar_estilo("enciclopedia_mascota")


@pytest.fixture
def perfil(estilo):
    return cargar_perfil_edicion(estilo)


@pytest.fixture(autouse=True)
def proyectos_temporales(tmp_path, monkeypatch):
    monkeypatch.setenv("ESTUDIO_PROYECTOS", str(tmp_path / "proyectos"))
    monkeypatch.setenv("XANDART_SIN_REMBG", "1")      # las pruebas no bajan el modelo de rembg (170 MB)
    monkeypatch.setenv("XANDART_DATOS", str(tmp_path / "datos"))   # base de datos y archivos de cada prueba aparte


@pytest.fixture(autouse=True)
def sin_espacio_fijo():
    """Cada prueba empieza sin espacio de trabajo fijado (no se contagian entre pruebas)."""
    from estudio.plataforma import contexto

    contexto.fijar_espacio(None)
    yield
    contexto.fijar_espacio(None)
