"""Capa de audio animada de Peligro Tropical (Fase 1): secciones, efectos, silencio en la mordida y master."""
import numpy as np

from estudio.pt_animado.audio import capa
from estudio.pt_animado.audio.dsp import SR, integrated, true_peak

FRASES = [
    {"seccion": "gancho", "intencion": "gancho", "texto": "Hay una serpiente que se esconde en el potrero.", "ini": 0.2, "fin": 3.0},
    {"seccion": "capitulo", "intencion": "explicacion", "texto": "Vas caminando tranquilo por el pasto.", "ini": 3.4, "fin": 6.0},
    {"seccion": "capitulo", "intencion": "tension_creciente", "texto": "Tu corazón se acelera.", "ini": 6.4, "fin": 8.0},
    {"seccion": "capitulo", "intencion": "revelacion", "texto": "Y cuando la pisas, muerde.", "ini": 8.5, "fin": 10.0},
    {"seccion": "capitulo", "intencion": "explicacion", "texto": "Su veneno no deja que la sangre se coagule.", "ini": 11.2, "fin": 14.0},
    {"seccion": "cierre", "intencion": "cierre", "texto": "Por eso se mira dónde se pisa.", "ini": 14.4, "fin": 16.5},
]


def _voz(dur=17.5):
    t = np.arange(int(dur * SR)) / SR
    v = np.zeros_like(t)
    for f in FRASES:
        m = (t >= f["ini"]) & (t < f["fin"])
        v[m] = 0.2 * np.sin(2 * np.pi * 180 * t[m]) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t[m]))
    return v


def test_solo_en_peligro_tropical():
    assert not capa.activa("tracy-principal", {"audio_animado": True})
    assert capa.activa(capa.CANAL_PT, {"audio_animado": True})
    assert not capa.activa(capa.CANAL_PT, {"audio_animado": False})
    assert capa.activa(capa.CANAL_PT, {}) is capa.PRENDIDA_POR_DEFECTO


def test_secciones_efectos_silencio_y_master():
    res = capa.construir(_voz(), FRASES)
    tipos = [s["tipo"] for s in res.secciones]
    assert tipos[0] == "hook" and "tranquilo" in tipos and "peligro" in tipos and "veneno" in tipos and tipos[-1] == "remate"
    efectos = {e["tipo"] for e in res.eventos}
    assert {"golpe", "pasos", "hojas", "latidos"} <= efectos
    t_golpe = next(e["t"] for e in res.eventos if e["tipo"] == "golpe")
    i = int((t_golpe + 0.2) * SR)
    assert np.abs(res.musica[:, i:i + int(0.8 * SR)]).max() < 1e-4       # la música calla en la mordida
    assert abs(integrated(res.mezcla) - capa.OBJETIVO_LUFS) < 0.5
    assert true_peak(res.mezcla) <= -1.0


def test_musica_baja_bajo_la_voz_y_sube_en_pausas():
    v = _voz()
    g = capa._agache(capa._actividad_voz(v), len(v))
    assert g[int(5.0 * SR)] < capa.AGACHE_DB + 1          # hablando: abajo
    assert g[int(11.0 * SR)] > -3                          # pausa larga: sube
    assert g[int(17.4 * SR)] > -3                          # al final, sin voz: arriba


def test_mezcla_para_render_mono_mismo_largo():
    v = _voz().astype(np.float32)
    out = capa.mezclar_para_render(v, SR, np.zeros_like(v), {"frases": FRASES})
    assert out.shape == v.shape and out.dtype == np.float32


def test_render_usa_la_capa_solo_si_la_edl_la_trae(tmp_path):
    import wave

    from estudio import render

    v = _voz()
    (tmp_path / "audio").mkdir()
    with wave.open(str(tmp_path / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((v * 32767).astype("<i2").tobytes())
    edl = {"duracion_total": 17.5, "audio": {}, "pistas": {"voz": [{"inicio": 0, "archivo": "audio/voz.wav"}],
                                                          "musica": [], "sfx": []}}
    normal = render.mezclar_audio(tmp_path, edl)
    edl["audio"]["animado"] = {"frases": FRASES}
    animado = render.mezclar_audio(tmp_path, edl)
    assert normal.shape == animado.shape
    assert np.abs(normal - animado).max() > 0.01           # con la capa cambia (música y efectos)
