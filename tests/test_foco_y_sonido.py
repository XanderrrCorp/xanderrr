"""Foco (círculo y flechas), sonido con intención y biblioteca con licencias."""
import random

import pytest

from estudio.edicion import _recortar_sonidos, _sfx
from estudio.esquemas import PerfilEdicion
from estudio.foco import candidatos, claves_de_nombre, palabra_en

NIVELES = [{"numero": 1, "nombre": "Mosca", "asset": "a", "villano": False},
           {"numero": 2, "nombre": "Chinche de cama", "asset": "b", "villano": False},
           {"numero": 3, "nombre": "Mosquito del dengue", "asset": "c", "villano": False},
           {"numero": 4, "nombre": "Chinche besucona", "asset": "d", "villano": True}]


def test_nombra_al_animal_y_no_a_parecidos():
    k = claves_de_nombre(NIVELES)
    assert palabra_en("Los mosquitos pican de día.", k[3]) == "mosquitos"
    assert palabra_en("Pon mosquiteros en las ventanas.", k[3]) is None       # red, no mosquito
    assert palabra_en("La chinche de cama es plana.", k[2]) == "chinche"
    assert palabra_en("Revisa debajo de la cama.", k[2]) is None             # la cama, no la chinche
    assert palabra_en("Una sola mosca pone cientos de huevos.", k[1]) == "mosca"


def test_el_villano_no_recibe_foco_antes_de_su_revelacion():
    esc = {"niveles": NIVELES, "escenas": [
        {"id": 1, "narracion": "La chinche besucona pica de noche.", "intencion": "amenaza",
         "visual": {"accion": "generar", "archivo": "imagenes/escena_001.png"}},
        {"id": 5, "narracion": "Esta es la chinche besucona.", "intencion": "revelacion",
         "visual": {"accion": "generar", "archivo": "imagenes/escena_005.png"}}]}
    ids = [c["escena"] for c in candidatos(esc, {"villano_revelacion": 5})]
    assert ids == [5]


def _perfil(**kw):
    base = dict(segundos_promedio_por_imagen=3.2, interrupcion_de_patron_cada_seg=7, efectos_por_minuto=9,
                sfx_por_minuto=6, cambios_de_musica="por_seccion", texto_en_pantalla_por_minuto=3,
                densidad_primeros_30s="alta", uso_maximo_por_recurso=0.35)
    return PerfilEdicion(**{**base, **kw})


def test_sonidos_con_intencion_y_limites():
    sfx = []
    for i in range(40):                       # pop en todas las escenas: demasiado
        _sfx(sfx, "pop", i * 3.0 + 0.1, i, "prueba")
    _sfx(sfx, "golpe_grave", 60.0, 20, "revelación")
    vivos = _recortar_sonidos(sfx, 40, 120.0, _perfil(), random.Random(1))
    clips_pop = sorted({x["clip"] for x in vivos if x["tipo"] == "pop"})
    assert len(clips_pop) <= int(0.35 * 40)                          # uso máximo por recurso
    assert all(b - a > 1 for a, b in zip(clips_pop, clips_pop[1:]))   # nunca en escenas seguidas
    assert any(x["tipo"] == "golpe_grave" for x in vivos)             # lo esencial se queda
    assert len(vivos) <= 6 * 2 * 1.25                                  # sfx_por_minuto


def test_biblioteca_registra_fuente_y_licencia(tmp_path, monkeypatch):
    monkeypatch.setenv("XANDART_BIBLIOTECA", str(tmp_path / "bib"))
    from estudio import biblioteca

    with pytest.raises(ValueError):
        biblioteca.registrar(b"RIFF", "golpe.wav", "sfx", "golpe_grave", "", "cc0")            # sin fuente
    with pytest.raises(ValueError):
        biblioteca.registrar(b"RIFF", "golpe.wav", "sfx", "golpe_grave", "freesound", "cc_by")  # sin atribución
    r = biblioteca.registrar(b"RIFF1", "Golpe Grave!.wav", "sfx", "golpe_grave",
                             "https://www.youtube.com/audiolibrary", "youtube_audio_library")
    assert r["fuente"] and r["licencia"] == "youtube_audio_library"
    assert biblioteca.utilizables("sfx", "golpe_grave")
    with pytest.raises(ValueError):
        biblioteca.registrar(b"RIFF1", "otra.wav", "sfx", "pop", "x", "cc0")                  # repetido
    otro = biblioteca.registrar(b"RIFF2", "raro.mp3", "sfx", "pop", "un amigo", "otra", detalle_licencia="me lo pasó")
    assert otro["revisar_licencia"] and not biblioteca.utilizables("sfx", "pop")               # no se usa sin revisar
