"""Freesound: solo CC0, con registro de fuente, y sin repetir."""
import pytest

from estudio import biblioteca, freesound

CC0 = "http://creativecommons.org/publicdomain/zero/1.0/"


class Resp:
    def __init__(self, datos=None, contenido=b""):
        self._d, self.content = datos, contenido

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


class Sesion:
    def get(self, url, params=None, headers=None, timeout=None):
        if url == freesound.API:
            assert headers["Authorization"] == "Token clave" and "Creative Commons 0" in params["filter"]
            return Resp({"results": [
                {"id": i, "name": f"s{i}", "url": f"https://freesound.org/s/{params['query'].replace(' ', '')}{i}/",
                 "username": "ana",
                 "license": CC0 if i != 2 else "http://creativecommons.org/licenses/by/4.0/", "duration": 1.0,
                 "previews": {"preview-hq-mp3": f"https://cdn.freesound.org/{params['query']}/{i}.mp3"}}
                for i in range(1, 8)]})
        return Resp(contenido=url.encode())                  # contenido distinto por archivo


def test_llena_solo_cc0_y_registra(tmp_path, monkeypatch):
    monkeypatch.setenv("XANDART_BIBLIOTECA", str(tmp_path / "bib"))
    monkeypatch.setenv("FREESOUND_API_KEY", "clave")
    r = freesound.llenar(["pop", "stinger_terror"], sesion=Sesion(), avisar=lambda *_: None)
    assert r == {"pop": 4, "stinger_terror": 4}
    archivos = biblioteca.indice()
    assert all(a["licencia"] == "cc0" and a["fuente"].startswith("https://freesound.org/s/") for a in archivos)
    assert not any(a["fuente"].endswith("2/") for a in archivos)           # el CC BY se descartó
    assert len(biblioteca.utilizables("sfx", "pop")) == 4
    # volver a correr no repite ni baja más
    assert freesound.llenar(["pop"], sesion=Sesion(), avisar=lambda *_: None) == {"pop": 0}


def test_sin_clave(monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    monkeypatch.setattr(freesound, "clave_api", lambda _: None)
    with pytest.raises(freesound.SinClaveFreesound):
        freesound.llenar(["pop"], sesion=Sesion(), avisar=lambda *_: None)
