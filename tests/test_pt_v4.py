"""(07-11) Peligro Tropical v4: fórmula escala_peligro_v3 (guion con apodo, pudor, calma y 6 animales) + perfil v4
(escala y letrero que rotan entre videos, VS, silueta, globos, pantalla negra, glitch e íconos). Los videos de antes
(v2, v1 o sin fórmula) siguen igual."""
import json
import random
import wave

import numpy as np
from PIL import Image

from estudio import guionista


def _proyecto_v4(estilo, formula="escala_peligro_v3", slug="v4"):
    from estudio.edicion import construir_edl
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("V4", "animales-peligrosos", estilo.id, 120, slug=slug)
    for carpeta in ("imagenes", "assets", "audio"):
        (c.ruta / carpeta).mkdir(exist_ok=True)
    for i in range(1, 5):
        im = Image.new("RGB", (640, 480), (128, 128, 128))
        im.paste((180, 60 + 40 * i, 40), (180, 120, 460, 380))
        im.save(c.ruta / "assets" / f"tira_{i}.png")
    escenas, t, eid = [], 0.0, 1

    def escena(seccion, narr, intencion, dur=3.0, visual=None):
        nonlocal t, eid
        if visual is None:
            Image.new("RGB", (640, 360), (40 + 9 * eid % 200, 90, 160)).save(c.ruta / "imagenes" / f"e{eid}.png")
            visual = {"accion": "generar", "tipo": "escena_cartoon_completa", "prompt": "x",
                      "archivo": f"imagenes/e{eid}.png"}
        escenas.append({"id": eid, "seccion": seccion, "narracion": narr, "intencion": intencion, "intensidad": 3,
                        "visual": visual, "tiempo": {"real_inicio": t, "real_fin": t + dur - 0.3}})
        t, eid = t + dur, eid + 1

    escena("Gancho", "Seguro has visto uno en el parque.", "gancho")
    escena("Gancho", "Pero hay algo que casi nadie sabe.", "giro")
    escena("Gancho", "Y el último de la lista, mejor verlo desde muy lejos.", "tension_creciente")
    escena("Gancho", "Hoy arrancamos con uno que no asusta a nadie.", "gancho")
    for i in range(1, 5):
        escena(f"Nivel {i}", f"El bicho {i}.", "transicion_de_seccion", 4.0,
               {"accion": "reusar", "reusar_de": f"tira_{i}"})
        escena(f"Nivel {i}", f"Es mucho más grande que el bicho {max(1, i - 1)}.", "explicacion")
        escena(f"Nivel {i}", "¿Estás en peligro?", "pregunta_al_espectador")
        escena(f"Nivel {i}", "Cuidado con su veneno, es mortal.", "advertencia")
        escena(f"Nivel {i}", "Y entonces pasa algo que nadie esperaba.", "explicacion")
        escena(f"Nivel {i}", "Te muerde en un segundo.", "revelacion")
    escena("Cierre", "Y eso es todo por hoy.", "cierre")
    escena("Cierre", "¿Cuál te dio más miedo?", "cierre")
    doc = {"video": "V4", "canal": "animales-peligrosos", "estilo": estilo.id,
           "assets": [{"id": f"tira_{i}", "tipo": "animal", "archivo": f"assets/tira_{i}.png"} for i in range(1, 5)],
           "niveles": [{"numero": i, "nombre": f"Bicho {i}", "asset": f"tira_{i}", "villano": i == 4}
                       for i in range(1, 5)],
           "escenas": escenas}
    c.guardar_escenas(EscenasV2.model_validate(doc))
    (c.ruta / "direccion.json").write_text(json.dumps({}), "utf-8")
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(np.zeros(int(48000 * (t + 2)), "<i2").tobytes())
    p = c.cargar()
    p.formula = formula
    c.guardar(p)
    return c, construir_edl(c)


def _efectos(edl):
    return [x for cl in edl["pistas"]["escenas"] for x in cl["efectos"]]


def test_formula_v3_guion_con_apodo_pudor_y_calma():
    f = guionista.cargar_formula("escala_peligro_v3")
    e = f["estructura"]
    assert "APODO propio" in e and "no te lo voy a contar todo de una vez" in e and "calma con medida" in e
    assert "(en un video de 8 minutos o más, 6)" in e and "Nada de sangre" in e
    assert f["perfiles"] == {"peligro_tropical_v2": "peligro_tropical_v4"}
    assert guionista.FORMULA_PELIGRO == "escala_peligro_v3"
    # la v2 no cambia (videos hechos con ella)
    v2 = guionista.cargar_formula("escala_peligro_v2")
    assert v2["perfiles"] == {"peligro_tropical_v2": "peligro_tropical_v3"} and "APODO" not in v2["estructura"]


def test_estilo_rota_sin_repetir_los_ultimos_3(tmp_path, monkeypatch):
    from estudio import receta_v4 as R

    monkeypatch.setattr(R, "_historial", lambda: tmp_path / "pt_estilos.json")
    rng = random.Random(3)
    elegidos = []
    for k in range(12):
        raiz = tmp_path / f"video{k}"
        raiz.mkdir()
        d = R.elegir_estilo(raiz, rng)
        assert R.elegir_estilo(raiz, random.Random(99)) == d           # rehacer el video no lo cambia
        combo = (d["escala"], d["letrero"])
        assert combo not in elegidos[-3:]
        if elegidos:
            assert combo[0] != elegidos[-1][0] and combo[1] != elegidos[-1][1]
        elegidos.append(combo)
    assert len({e for e, _ in elegidos}) == 3 and len({l for _, l in elegidos}) == 3


def test_recursos_nuevos_solo_con_la_v3(estilo):
    nuevos = {"vs", "silueta", "globo", "negro", "glitch", "icono_v4"}
    _, edl = _proyecto_v4(estilo, formula="escala_peligro_v2", slug="v2")
    assert not nuevos & {x["efecto"] for x in _efectos(edl)}
    assert not any("variante" in x or "letrero" in x for x in _efectos(edl))
    c, edl = _proyecto_v4(estilo)
    ef = _efectos(edl)
    nombres = [x["efecto"] for x in ef]
    assert nuevos <= set(nombres), set(nombres)
    assert nombres.count("silueta") == 1
    sil = next(x for x in ef if x["efecto"] == "silueta")
    assert sil["nivel"] == 4
    for x in ef:
        if x["efecto"] == "vs":
            assert x["izq"] == x["der"] - 1
        if x["efecto"] == "icono_v4":
            assert x["tipo"] in ("x", "corona", "pulgar_abajo", "alerta")
    estilo_video = json.loads((c.ruta / "estilo_video.json").read_text("utf-8"))
    tiras = [x for x in ef if x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar")]
    assert all(x.get("variante", "horizontal") == estilo_video["escala"] for x in tiras)
    assert all(x["letrero"] == estilo_video["letrero"] for x in ef if x["efecto"] == "presentacion_especie")


def test_se_dibujan_las_escalas_letreros_y_recursos(estilo):
    from estudio import render_v4 as RV

    c, _ = _proyecto_v4(estilo)
    esc = c.cargar_escenas()
    for variante in ("vertical", "cartas"):
        for loc in (0.0, 0.3, 1.0):
            im = RV.escala(c.ruta, esc, {"hasta": 3, "variante": variante}, loc, 2.0)
            assert im.size == (1920, 1080)
    base = Image.new("RGB", (1920, 1080), (120, 160, 90))
    assert RV.vs(c.ruta, esc, {"izq": 1, "der": 2, "dur": 2}, 0.5).size == (1920, 1080)
    assert RV.silueta_misterio(c.ruta, esc, {"nivel": 4, "dur": 2}, 0.6).size == (1920, 1080)
    assert RV.globo(base, {"texto": "¿Estás en peligro?", "dur": 2}, 0.4).size == (1920, 1080)
    for tipo in ("x", "corona", "pulgar_abajo", "alerta"):
        assert RV.icono(base, {"tipo": tipo, "x": 0.12, "y": 0.3, "dur": 1.5}, 0.4).size == (1920, 1080)
    assert RV.glitch(base, {"dur": 0.42}, 0.1, 3).size == (1920, 1080)
    assert np.asarray(RV.negro(base, {"dur": 0.45}, 0.3)).max() == 0
    for forma in ("etiqueta", "color", "tarjeta"):
        assert RV.letrero("2- Bicho 2", forma).width > 100


def test_render_de_un_video_v4(estilo):
    from estudio.pipeline import ffmpeg
    from estudio.render import renderizar

    c, _ = _proyecto_v4(estilo)
    f = renderizar(c, ffmpeg(), c.ruta / "render" / "t.mp4", avisar=lambda _: None, salida=(320, 180, 3), procesos=1)
    assert f.exists() and f.stat().st_size > 0


# ---------------------------------------------------------------- ropa del muñeco que rota (vestuario.py)

def _video_ropa(estilo, slug, formula="escala_peligro_v3", color=(200, 200, 200)):
    from estudio.config import escribir_json
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Ropa", "animales-peligrosos", estilo.id, 60, slug=slug)
    p = c.cargar()
    p.formula = formula
    c.guardar(p)
    (c.ruta / "assets").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), color).save(c.ruta / "assets" / "mascota_base.png")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    escribir_json(c.ruta / "imagenes" / "manifiesto.json", {"asset:mascota_base": {"archivo": "x"}})
    return c


def test_ropa_rota_y_cada_una_se_paga_una_sola_vez(estilo, tmp_path, monkeypatch):
    from estudio import vestuario as V
    from estudio.config import ConfigCostos, leer_json
    from estudio.imagenes.proveedores import ProveedorSimulado

    monkeypatch.setattr(V, "_historial", lambda: tmp_path / "pt_vestuarios.json")
    monkeypatch.setattr(V, "_cache", lambda base: tmp_path / "cache")
    config = ConfigCostos.cargar()
    prov = ProveedorSimulado(config)
    usados = []
    for k in range(10):
        c = _video_ropa(estilo, f"ropa{k}")
        info = V.preparar(c, prov, config, permiso=True, avisar=lambda *_: None)
        assert info["vestuario"] in V.VESTUARIOS
        assert info["vestuario"] not in usados[-3:]
        usados.append(info["vestuario"])
        assert V.preparar(c, prov, config, permiso=True, avisar=lambda *_: None) == info   # la segunda vez, nada
        if info["vestuario"] != "clasico":
            assert "IN THIS VIDEO he wears instead" in leer_json(c.ruta / "perfil_canal.json")["personaje"]["bloqueo"]
            assert (c.ruta / "assets" / "mascota_original.png").exists()
            assert "asset:mascota_base" not in leer_json(c.ruta / "imagenes" / "manifiesto.json")
        assert json.loads((c.ruta / "estilo_video.json").read_text("utf-8"))["vestuario"] == info["vestuario"]
    # cada ropa (menos la de siempre) se dibujó UNA sola vez aunque se repitiera en varios videos
    assert prov.llamadas == len(set(usados) - {"clasico"})
    assert len(set(usados)) >= 4


def test_sin_v3_o_con_imagenes_hechas_no_cambia_la_ropa(estilo, tmp_path, monkeypatch):
    from estudio import vestuario as V
    from estudio.config import ConfigCostos, escribir_json
    from estudio.imagenes.proveedores import ProveedorSimulado

    monkeypatch.setattr(V, "_historial", lambda: tmp_path / "h.json")
    monkeypatch.setattr(V, "_cache", lambda base: tmp_path / "cache")
    prov = ProveedorSimulado(ConfigCostos.cargar())
    c = _video_ropa(estilo, "v2ropa", formula="escala_peligro_v2")
    assert V.preparar(c, prov, permiso=True, avisar=lambda *_: None) is None
    c = _video_ropa(estilo, "hechas")
    escribir_json(c.ruta / "imagenes" / "manifiesto.json", {"escena:1": {"archivo": "x"}})
    assert V.preparar(c, prov, permiso=True, avisar=lambda *_: None)["vestuario"] == "clasico"
    assert prov.llamadas == 0 and not (c.ruta / "assets" / "mascota_original.png").exists()


def test_la_ropa_no_es_la_del_personaje_de_la_competencia():
    from estudio import vestuario as V

    texto = " ".join(d for _, d in V.VESTUARIOS.values() if d).lower()
    for prohibido in ("backwards", "gold chain", "grey hoodie", "gray hoodie", "beanie", "red cap", "red jacket"):
        assert prohibido not in texto
