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
