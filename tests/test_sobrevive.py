"""(28-10) Canal «Sobrevive Si Puedes»: preset nuevo sin tocar los demás; lo VERBATIM del dueño va literal."""
import json
from pathlib import Path

from estudio.esquemas import Escena, Estilo
from estudio.imagenes import prompts

RAIZ = Path(__file__).resolve().parent.parent
STYLE_INICIO = "STYLE: polished 2D vector cartoon, thick clean black outlines"
CIERRE = ("16:9 composition, cinematic lighting, high contrast, clean readable shapes, no text, no letters, no watermark, "
          "no blood, no gore, no visible wounds.")
MATEO = "a white stickman with a big round white head, spiky messy black hair, a bright red bandana"


def _estilo() -> Estilo:
    return Estilo.model_validate(json.loads((RAIZ / "estilos/sobrevive_si_puedes/estilo.json").read_text("utf-8")))


def _escena(tipo, narracion, descripcion):
    return Escena.model_validate({"id": 1, "seccion": "Lunes, primer día", "narracion": narracion,
                                  "intencion": "explicacion", "intensidad": 3,
                                  "visual": {"accion": "generar", "tipo": tipo, "prompt": descripcion}})


def test_lo_verbatim_va_literal_en_cada_prompt():
    e = _estilo()
    assert e.bloque_estilo.startswith(STYLE_INICIO) and e.personaje_por_defecto.startswith(MATEO)
    for t in e.tipos_de_escena:
        assert t.plantilla_prompt.endswith(CIERRE) and t.plantilla_prompt.startswith("{bloque_estilo}"), t.id
    con_mateo = prompts.prompt_de_escena(_escena("escena_mateo", "Abres el grifo y no sale agua.",
                                                 "He opens the kitchen tap, scared, at night"), e, e.personaje_por_defecto)
    assert con_mateo.startswith(STYLE_INICIO) and MATEO in con_mateo and con_mateo.endswith(CIERRE)
    sin_mateo = prompts.prompt_de_escena(_escena("lugar_dia", "El miércoles, tercer día.", "Empty supermarket aisles"),
                                         e, e.personaje_por_defecto)
    assert MATEO not in sin_mateo


def test_el_elenco_solo_aparece_cuando_la_voz_lo_nombra():
    e = _estilo()
    solo = prompts.prompt_de_escena(_escena("escena_mateo", "Te asomas al pasillo.", "He looks down the hallway"),
                                    e, e.personaje_por_defecto)
    assert "VALENTINA:" not in solo and "CANELA:" not in solo
    juntos = prompts.prompt_de_escena(_escena("escena_mateo", "Don Ruben te cuenta la leyenda y Canela gruñe.",
                                              "He listens by the fire"), e, e.personaje_por_defecto)
    assert "DON RUBÉN: an older white stickman" in juntos and "CANELA: a small cartoon street dog" in juntos
    assert "VALENTINA:" not in juntos and juntos.endswith(CIERRE)


def test_formula_y_formato_del_canal_son_privados_y_llevan_sus_reglas():
    from estudio.guionista import instruccion_detalles
    from estudio.plataforma.api import DEL_DUENO

    f = json.loads((RAIZ / "catalogo/formulas/supervivencia_por_dias/formula.json").read_text("utf-8"))
    fm = json.loads((RAIZ / "catalogo/formatos/sobrevive_si_puedes/formato.json").read_text("utf-8"))
    assert fm["formula"] == f["clave"] and fm["estilo"] == "sobrevive_si_puedes" and min(fm["duraciones_min"]) >= 12
    assert "sobrevive_si_puedes" in DEL_DUENO["formatos"] and f["clave"] in DEL_DUENO["formulas"]
    texto = json.dumps(f, ensure_ascii=False).lower()
    assert "don zombi" not in texto and "nobody gets in" not in texto          # nada de la competencia en el prompt
    historia = {"titulo": "Sobreviví 30 Días Atrapado en un Supermercado", "niveles": [],
                "secciones": [("Lunes, primer día", ["A las seis y veintitrés, tu teléfono vibra."])],
                "_imagenes": f["imagenes"]}
    pedido = instruccion_detalles(historia, 0, _estilo())
    assert "Alrededor del 50 %" in pedido and "Rota la CÁMARA" in pedido
    assert '"real"' not in pedido                                              # nada de fotos reales en un canal animado


def test_los_otros_canales_no_cambian():
    from estudio.estilos import cargar_estilo

    for clave in ("enciclopedia_mascota", "paradoja_sapiens"):
        assert cargar_estilo(clave).elenco == {}
    pt = cargar_estilo("enciclopedia_mascota")
    t = pt.tipos_de_escena[0]
    e = Escena.model_validate({"id": 1, "seccion": "Nivel 1 · Rana", "narracion": "Valentina mira la rana.",
                               "intencion": "explicacion", "intensidad": 2,
                               "visual": {"accion": "generar", "tipo": t.id, "prompt": "a frog"}})
    assert "Also in the scene" not in prompts.prompt_de_escena(e, pt, pt.personaje_por_defecto or "")


def test_la_tarjeta_del_dia_es_oscura_en_este_canal_y_de_papel_en_paradoja():
    import numpy as np
    from PIL import Image

    import estudio.render as r
    from estudio.estilos import cargar_estilo

    assert _estilo().tarjeta_capitulo == "noche" and cargar_estilo("paradoja_sapiens").tarjeta_capitulo == "papel"
    papel = Image.new("RGB", (r.W, r.H), (240, 236, 228))
    ef = {"numero": 2, "titulo": "Lunes, primer día"}
    noche = np.asarray(r._capitulo(papel, ef, 1.0, noche=True)).mean()
    claro = np.asarray(r._capitulo(papel, ef, 1.0)).mean()
    assert noche < 60 < 200 < claro
