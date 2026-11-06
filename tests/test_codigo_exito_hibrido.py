"""Código del Éxito híbrido: guion etiquetado, tramos de stock (≤30 s, sin repetir clip en el video), respiros del aura
(≤2,5 min seguidos), subtítulos en trozos cortos y la mezcla de audio (-14 LUFS)."""
import json

import numpy as np
import pytest

GUION = """[PROFESOR]
Hola. Hoy vemos la primera regla.

[STOCK: sunrise city, man running]
Piensa en la mañana. Todo empieza temprano.
Y este párrafo sigue en el mismo bloque.

[AURA]
Respira profundo. Repite conmigo.

[PROFESOR]
Regla número dos: empieza pequeño.
"""


def test_guion_etiquetado_en_bloques_y_partes():
    from estudio.codigo_exito import guion

    b = guion.leer(GUION)
    assert [x["tipo"] for x in b] == ["profesor", "stock", "aura", "profesor"]
    assert b[1]["claves"] == ["sunrise city", "man running"]
    assert "mismo bloque" in b[1]["texto"]
    assert [x["parte"] for x in b] == [0, 0, 0, 1]                 # cada [PROFESOR] abre una parte
    with pytest.raises(ValueError):
        guion.leer("[STOCK]\nsin palabras clave")


def test_tramos_de_stock_y_respiros_del_aura():
    from estudio.codigo_exito import armar, stock

    assert stock.tramos(25) == [25.0]
    t = stock.tramos(75)
    assert len(t) == 3 and max(t) <= 30 and abs(sum(t) - 75) < 0.01
    assert armar.respiros(100) == []
    r = armar.respiros(420)
    cortes = [0.0] + [x for t in r for x in (t, t + armar.RESPIRO)] + [420.0]
    assert r and all(b - a <= 150 for a, b in zip(cortes[::2], cortes[1::2]))   # ningún tramo de aura pasa de 2,5 min


def test_stock_no_repite_clips_en_el_video(tmp_path, monkeypatch):
    from estudio.codigo_exito import stock
    from estudio.tracy import clips

    vistos = iter(range(1000, 2000))
    def buscar(q, minimo, excluir, sesion=None):
        return [{"pexels_id": str(i), "duracion": 40.0, "url_origen": "u", "autor": "a", "descarga": "d", "ancho": 1920,
                 "alto": 1080, "consulta": q} for i in [next(vistos) for _ in range(2)] + ["7"] if str(i) not in excluir]
    def descargar(clip, sesion=None):
        p = tmp_path / f"c{clip['pexels_id']}.mp4"; p.write_bytes(b"0"); return p
    monkeypatch.setattr(clips, "buscar", buscar)
    monkeypatch.setattr(clips, "descargar", descargar)
    out = stock.elegir(tmp_path / "v", [{"clave": "a", "claves": ["x"], "dur": 70}, {"clave": "b", "claves": ["x"], "dur": 20}], avisar=lambda *_: None)
    ids = [c["pexels_id"] for v in out.values() for c in v]
    assert len(ids) == len(set(ids)) == 4
    reg = json.loads((tmp_path / "v" / "stock" / "usados.json").read_text())
    assert len(reg["clips"]) == 4 and {c["pedido"] for c in reg["clips"]} == {"a", "b"}
    again = stock.elegir(tmp_path / "v", [{"clave": "a", "claves": ["x"], "dur": 70}], avisar=lambda *_: None)
    assert [c["pexels_id"] for c in again["a"]] == [c["pexels_id"] for c in out["a"]]   # se reusa, no se vuelve a buscar


def test_subtitulos_en_trozos_cortos():
    from estudio.codigo_exito import voz

    z = voz.trozos([{"texto": "Hoy empiezo pequeño, y empezar pequeño también es avanzar.", "ini": 0.0, "fin": 4.0}])
    assert all(1 <= len(x["texto"].split()) <= 4 for x in z)
    assert z[0]["ini"] == 0 and abs(z[-1]["fin"] - 4.0) < 0.01


def test_mezcla_a_menos_14_lufs():
    from estudio.codigo_exito.mezcla import mezclar
    from estudio.pt_animado.audio.dsp import SR, integrated, true_peak

    t = np.arange(int(12 * SR)) / SR
    v = (0.2 * np.sin(2 * np.pi * 170 * t) * (np.sin(2 * np.pi * 0.5 * t) > 0)).astype(np.float32)
    m, info = mezclar(v, "ffmpeg")
    assert m.shape == (2, len(v))
    assert abs(integrated(m) + 14) < 0.5 and true_peak(m) <= -0.9
    assert info["musica"] == "por código"
