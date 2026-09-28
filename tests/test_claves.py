"""Claves de proveedores: se limpian al pegar, la guardada en Ajustes manda y «Probar» prueba lo escrito."""
from fastapi.testclient import TestClient

from estudio import app as modulo_app, config


class _Resp:
    def __init__(self, codigo):
        self.status_code = codigo


def _aislar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    monkeypatch.setattr(modulo_app, "RAIZ", tmp_path)
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)


def test_clave_pegada_con_basura_invisible_se_limpia(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text('PEXELS_API_KEY= "abc​DEF123"\n', encoding="utf-8")
    assert config.clave_api("PEXELS_API_KEY") == "abcDEF123"


def test_la_clave_de_ajustes_manda_sobre_una_vieja_de_windows(tmp_path, monkeypatch):
    _aislar(tmp_path, monkeypatch)
    monkeypatch.setenv("PEXELS_API_KEY", "vieja")
    assert config.clave_api("PEXELS_API_KEY") == "vieja"
    (tmp_path / ".env").write_text("PEXELS_API_KEY=nueva\n", encoding="utf-8")
    assert config.clave_api("PEXELS_API_KEY") == "nueva"


def test_probar_usa_la_clave_escrita_y_la_guarda_solo_si_funciona(tmp_path, monkeypatch):
    import requests

    _aislar(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text("PEXELS_API_KEY=" + "v" * 56 + "\n", encoding="utf-8")
    buena = "B" * 56
    monkeypatch.setattr(requests, "get", lambda *a, headers, **k: _Resp(200 if headers["Authorization"] == buena else 401))
    cli = TestClient(modulo_app.app)

    r = cli.post("/api/probar/pexels", json={"clave": "x" * 20}).json()
    assert not r["ok"] and "20 caracteres" in r["detalle"]
    assert config.clave_api("PEXELS_API_KEY") == "v" * 56          # la mala no reemplaza la anterior

    r = cli.post("/api/probar/pexels", json={"clave": " " + buena + "\n"}).json()
    assert r["ok"] and "guardada" in r["detalle"]
    assert config.clave_api("PEXELS_API_KEY") == buena

    r = cli.post("/api/probar/pexels", json={"clave": "https://www.pexels.com/api/"}).json()
    assert not r["ok"] and "símbolos" in r["detalle"]
