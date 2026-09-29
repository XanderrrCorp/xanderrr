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


def test_musica_suave_solo_cc0(tmp_path, monkeypatch):
    monkeypatch.setenv("XANDART_BIBLIOTECA", str(tmp_path / "bib"))
    monkeypatch.setenv("FREESOUND_API_KEY", "clave")
    assert freesound.llenar_musica(sesion=Sesion(), avisar=lambda *_: None) == {"suave": 3}
    pistas = biblioteca.utilizables("musica", "suave")
    assert len(pistas) == 3 and all(a["licencia"] == "cc0" for a in biblioteca.indice())
    assert freesound.llenar_musica(sesion=Sesion(), avisar=lambda *_: None) == {"suave": 0}


def test_musica_suave_de_fondo_en_todo_el_video(tmp_path, monkeypatch):
    import random

    from estudio import edicion

    clips = [{"inicio": 0.0, "fin": 5.0}, {"inicio": 5.0, "fin": 12.0}]

    class E:
        def __init__(self, i): self.id = i

    m = edicion._musica_suave(["musica/suave/a.mp3"], [E(1), E(2)], clips, 2, 12.0, random.Random(1))
    assert len(m) == 1 and m[0]["inicio"] == 0 and m[0]["fin"] == 12.0 and m[0]["volumen"] < 0.2
    assert m[0]["caidas"][0][1] == 5.55                      # se apaga justo antes de la revelación


def test_efectos_con_volumen_parejo():
    import numpy as np

    from estudio.render import _igualar

    bajito, fuerte = np.full(1000, 0.01, np.float32), np.full(1000, 0.9, np.float32)
    a, b = _igualar(bajito, 0.2), _igualar(fuerte, 0.2)
    assert abs(float(np.sqrt(np.mean(a ** 2))) - 0.2) < 1e-3 and abs(float(np.sqrt(np.mean(b ** 2))) - 0.2) < 1e-3
    pico = np.zeros(1000, np.float32); pico[10] = 0.5; pico[20:] = 0.002
    assert float(np.max(np.abs(_igualar(pico, 0.2)))) <= 0.98 + 1e-6   # nunca satura
