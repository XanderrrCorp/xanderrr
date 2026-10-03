from estudio.edicion import DEBILES, trozos_subtitulo, validar
from estudio.voz import agrupar, cortes_por_pausas, pausa_despues
from estudio.esquemas import Escena

import numpy as np


def test_subtitulos_de_1_a_4_palabras_sin_colgar_articulos():
    t = "Vive en las grietas de las paredes de adobe, en los techos de palma, en la leña y en los gallineros."
    trozos = trozos_subtitulo(t)
    assert " ".join(trozos) == t
    for tr in trozos:
        palabras = tr.split()
        assert 1 <= len(palabras) <= 6
        assert palabras[-1].lower().strip(",.") not in DEBILES or tr.endswith((",", "."))


def _escena(i, texto, seccion="A", intencion="explicacion"):
    return Escena.model_validate({"id": i, "seccion": seccion, "narracion": texto, "intencion": intencion,
                                  "intensidad": 2, "visual": {"accion": "solo_edicion"}})


def test_agrupar_por_oraciones():
    e = [_escena(1, "Hola,"), _escena(2, "que tal."), _escena(3, "Otra frase."), _escena(4, "Nueva", "B")]
    grupos = agrupar(e)
    assert [[x.id for x in g.escenas] for g in grupos] == [[1, 2], [3], [4]]


def test_corte_en_la_pausa_real():
    sr = 48000
    ruido = lambda s: np.random.default_rng(1).normal(0, 0.3, int(sr * s)).astype(np.float32)
    x = np.concatenate([ruido(1.0), np.zeros(int(sr * 0.2), np.float32), ruido(1.4)])
    corte = cortes_por_pausas(x, [10, 10])[0] / sr     # por caracteres caería en 1,2 s
    assert 1.0 <= corte <= 1.2


def test_pausas_controladas():
    a, b = _escena(1, "Algo."), _escena(2, "Revela.", intencion="revelacion")
    assert pausa_despues(a, b) >= 0.5                  # silencio antes de revelar
    assert pausa_despues(a, _escena(3, "Otra", "Z")) >= 0.7


def test_validador_detecta_plano_largo_y_golpes_seguidos():
    clip = lambda i, a, b, mov=None, ef=(): {"id": f"c{i}", "inicio": a, "fin": b, "efectos": list(ef),
                                           "movimiento": {"tipo": mov} if mov else None}
    edl = {"pistas": {"escenas": [clip(1, 0, 6), clip(2, 6, 8, "zoom_golpe"), clip(3, 8, 9, "zoom_golpe")]}}
    avisos = validar(edl)
    assert any("sin cambio visual" in a for a in avisos) and any("seguidos" in a for a in avisos)


def test_paradoja_sapiens_papel_claro_y_movimiento_suave():
    from estudio.estilos import cargar_estilo, cargar_perfil_edicion

    e = cargar_estilo("paradoja_sapiens")
    assert e.fondo_montaje.tipo == "cuadricula"
    p = cargar_perfil_edicion(e)
    assert p.estilo_edicion == "clasica" and p.movimiento == "sin_vaiven"   # dopamina de la clásica, sin mecerse
    assert "teal" not in e.model_dump_json().lower()


def test_arreglo_lleva_el_papel_claro_a_la_copia_del_espacio(tmp_path):
    import json

    from estudio.imagenes.arreglos import corregir_estilos

    f = tmp_path / "espacios" / "e1" / "estilos" / "paradoja_sapiens" / "estilo.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"id": "paradoja_sapiens", "fondo_montaje": {"tipo": "color", "valor": "#2E8F8C"},
                             "movimiento_maximo": 0.05, "x": "Dark flat teal-blue background with a few pale "
                             "sketchy pencil lines, no text"}), encoding="utf-8")
    assert corregir_estilos(tmp_path) == [f]
    d = json.loads(f.read_text(encoding="utf-8"))
    assert d["fondo_montaje"]["tipo"] == "cuadricula" and d["movimiento_maximo"] == 0.05
    assert "Light cream paper" in d["x"] and d["perfil_edicion"] == "perfiles/paradoja_documental.json"
    assert corregir_estilos(tmp_path) == []                            # la segunda vez no toca nada


def test_dato_con_icono_y_flecha_y_foto_vieja_sobre_cuadricula(tmp_path):
    from PIL import Image

    from estudio.render import Escenario, _poner_dato, papel_cuadriculado

    Image.new("RGB", (800, 600), (128, 128, 128)).save(tmp_path / "a.png")
    e = Escenario(tmp_path, papel_cuadriculado(1920, 1080, 1), {"recorte_sobre_papel": "recorte",
                                                                "recuadro_sobre_papel": "recuadro"})
    c = {"id": "x", "archivo": "a.png", "modo": "recuadro_sobre_papel",
         "efectos": [{"efecto": "dato", "en": 0, "texto": "No muerde", "icono": "no"}]}
    base = e.cuadro(c)
    x, y, w, h = e.ubicacion["x"]
    assert x > 1920 * 0.4                                   # con el dato, la foto se corre a la derecha
    con = _poner_dato(base, c["efectos"][0], 1.0, 4.0)
    assert con.getpixel((518, 312))[0] > 180 and con.getpixel((518, 312))[1] < 90   # el círculo rojo de la ✕
    assert _poner_dato(base, c["efectos"][0], -1, 4.0) is base                      # antes de su momento, nada
