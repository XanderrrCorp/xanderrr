"""Escenas de mapa por código (18-10): datos, validación, dibujo, marcador, reglas de mezcla y Modo mapa."""
import json

import numpy as np


def test_paises_y_banderas_reales():
    from estudio.geo import mapa as M

    assert M.codigo("Colombia") == "COL" and M.codigo("mx") == "MEX" and M.codigo("ESPAÑA") == "ESP"
    assert M.codigo("Francia") == "FRA" and M.codigo("Atlantis") is None
    assert M.nombre("USA") == "Estados Unidos" and M.nombre("PER") == "Perú"
    assert len(M.paises()) > 230
    b = M.bandera("COL", 60)
    assert b is not None and b.size == (80, 60)
    arriba, abajo = np.asarray(b)[10, 40, :3], np.asarray(b)[55, 40, :3]
    assert arriba[0] > 200 and arriba[1] > 200 and abajo[0] > 180 and abajo[2] < 80     # amarillo arriba, rojo abajo


def test_validar_escena_de_mapa():
    from estudio.geo.escena import validar

    m, nota = validar({"map_action": "arrow", "focus_country": "Ecuador", "sentiment": "tension",
                       "timeline": [{"year": "2008", "text": "x" * 80}, {"year": "1", "text": "a"}, {"text": "b"}]})
    assert m["pais"] == "ECU" and m["origen"] == "COL" and m["region"] == "SUDAMÉRICA"     # origen: el país base
    assert len(m["linea"]) == 2 and len(m["linea"][0]["texto"]) == 50
    assert m["calvo"] == "scared" and m["calvo_lado"] == "left"
    malo, nota = validar({"map_action": "highlight", "focus_country": "Wakanda"})
    assert malo is None and "Wakanda" in nota                                             # no se dibuja a ciegas
    assert validar({"focus_country": "MEX"})[0]["region"] == "NORTEAMÉRICA"
    assert validar({"map_action": "volar", "focus_country": "PER"})[0]["accion"] == "highlight"


def _datos():
    from estudio.geo.escena import validar

    crudas = [{"map_action": "zoom_region", "focus_country": "COL", "region": "SUDAMÉRICA"},
              {"map_action": "highlight", "focus_country": "MEX", "sentiment": "very_friendly", "status_tag": "MEJORANDO",
               "timeline": [{"year": "1994", "text": "Tratado"}]},
              {"map_action": "arrow", "origin_country": "COL", "focus_country": "ECU", "sentiment": "tension"},
              {"map_action": "compare", "origin_country": "COL", "focus_country": "PER", "sentiment": "complicated",
               "calvo_position": "right"}]
    escenas = [{"id": i + 1, "tipo": "mapa", "mapa": validar(c)[0], "inicio": i * 3.0, "fin": (i + 1) * 3.0,
                "elementos": []} for i, c in enumerate(crudas)]
    return {"video": {"fps": 30, "duracion": 12.0, "pais_base": "COL"}, "escenas": escenas}


def test_marcador_suma_paises_en_orden():
    from estudio.geo.escena import preparar

    d = _datos()
    preparar(d)
    e = [x["mapa"]["_estado"] for x in d["escenas"]]
    assert not e[0]["nuevo"]                                         # Colombia es la base: no se cuenta
    assert e[1]["despues"]["very_friendly"] == 1 and e[1]["antes"]["very_friendly"] == 0
    assert e[3]["antes"]["tension"] == 1 and e[3]["despues"]["complicated"] == 1
    assert e[3]["historial"] == ["ECU", "tension"] and e[2]["previos"] == {"MEX": "very_friendly"}


def test_mapas_se_dibujan_y_se_mueven():
    from estudio.calma.render import cuadro_en

    d = _datos()
    for k, esc in enumerate(d["escenas"]):
        a = cuadro_en(d, esc["inicio"] + 0.2)
        b = cuadro_en(d, esc["inicio"] + 2.0)
        assert a.shape == (1080, 1920, 3) and np.abs(a.astype(int) - b.astype(int)).mean() > 0.5, k
    # la flecha (rojo de tensión) aparece en la escena de Ecuador
    f = cuadro_en(d, 8.5)
    rojo = (f[..., 2] > 200) & (f[..., 1] < 100) & (f[..., 0] < 100)
    assert rojo.sum() > 500


def test_reglas_de_mezcla_y_modo_mapa_en_el_calvo(tmp_path):
    from estudio.explica import autor
    from estudio.explica import canal as C

    tema = {"nombre": ["México."], "escena": ["Estás en México.", "Hace calor."], "bautizo": ["Eso es México."],
            "explicacion": ["Se cree que se llevan bien."], "cierre": ["Y ya."]}
    escenas = [{"tipo": "mapa", "mapa": {"map_action": "arrow", "focus_country": "MEX", "origin_country": "COL"},
                "elementos": [{"id": "a", "pieza": "texto", "estado": {"texto": "MÉXICO"}}]} for _ in range(5)]
    sin, _, notas = autor.validar({"escenas": escenas}, tema)                # Modo mapa apagado: todo ilustración
    assert all(e["tipo"] == "ilustracion" for e in sin)
    con, _, _ = autor.validar({"escenas": escenas}, tema, {"pais_base": "COL"})
    assert all(e["tipo"] == "mapa" for e in con) and con[0]["respaldo"]["tipo"] == "ilustracion"
    autor.reglas_mapa(con)
    assert con[0]["mapa"]["accion"] == "highlight" and con[1]["mapa"]["accion"] == "arrow"   # 1.ª vez: highlight
    assert [e["tipo"] for e in con] == ["mapa"] * 4 + ["ilustracion"]                       # máximo 4 seguidos
    assert "MODO MAPA" in autor._prompt_escenas(tema, 0, 1, {"pais_base": "COL"})
    assert "MODO MAPA" not in autor._prompt_escenas(tema, 0, 1)
    assert C.POR_DEFECTO.get("modo_mapa") is None                                           # apagado por defecto


def test_modo_mapa_se_guarda_en_el_video():
    from estudio.explica.api import crear_carpeta

    slug, c = crear_carpeta("Qué piensa cada país de Colombia", 6, "", modo_mapa=True, pais_base="Colombia")
    meta = json.loads((c / "video.json").read_text(encoding="utf-8"))
    assert meta["modo_mapa"] is True and meta["pais_base"] == "COL"
    slug2, c2 = crear_carpeta("Otro tema normal", 6)
    assert "modo_mapa" not in json.loads((c2 / "video.json").read_text(encoding="utf-8"))


def test_peligro_tropical_calcula_el_marcador_de_sus_mapas():
    from types import SimpleNamespace

    from estudio.animaciones_codigo import _marcador_mapas
    from estudio.geo.escena import validar

    disenos = {str(i): {"narracion": "x", "escena": {"tipo": "mapa", "mapa": validar(
        {"focus_country": p, "sentiment": "tension", "calvo_position": "none"})[0]}} for i, p in ((1, "AUS"), (2, "BRA"))}
    _marcador_mapas(disenos, [SimpleNamespace(id=1), SimpleNamespace(id=2)], "COL")
    assert disenos["2"]["escena"]["mapa"]["_estado"]["antes"]["tension"] == 1
    assert disenos["1"]["escena"]["mapa"]["calvo_lado"] == "none"
