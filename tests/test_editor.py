"""Editor tipo CapCut: los cambios van aparte de la edición automática y se aplican al exportar.
Nada aquí llama a proveedores (cero gasto)."""
import json

from fastapi.testclient import TestClient

from estudio import editor
from estudio.config import ruta_proyectos


def _video():
    raiz = ruta_proyectos() / "peces"
    (raiz / "render").mkdir(parents=True)
    (raiz / "imagenes").mkdir()
    (raiz / "proyecto.json").write_text(json.dumps({"slug": "peces", "titulo": "Peces", "canal": "animales-peligrosos",
                                                    "estilo": "enciclopedia_mascota", "duracion_objetivo_seg": 540,
                                                    "creado": "2026-09-28T00:00:00+00:00"}), "utf-8")
    escenas = [{"id": i, "narracion": f"Frase {i}.", "seccion": "Gancho", "visual": {"accion": "generar"},
                "tiempo": {"real_inicio": 3.0 * (i - 1), "real_fin": 3.0 * (i - 1) + 2.6}} for i in (1, 2, 3)]
    (raiz / "escenas.json").write_text(json.dumps({"escenas": escenas}), "utf-8")
    clips = [{"id": f"c00{i}", "escena": i, "inicio": 3.0 * (i - 1), "fin": 3.0 * i, "archivo": f"imagenes/escena_00{i}.png",
              "modo": "recorte", "efectos": [{"efecto": "etiqueta", "en": 3.0 * (i - 1) + 0.2}]} for i in (1, 2, 3)]
    subs = [{"inicio": 3.0 * (i - 1), "fin": 3.0 * (i - 1) + 2.6, "texto": f"Frase {i}.", "escena": i} for i in (1, 2, 3)]
    edl = {"version": 1, "duracion_total": 9.0,
           "pistas": {"escenas": clips, "subtitulos": subs, "voz": [{"inicio": 0, "archivo": "audio/voz.wav"}],
                      "musica": [{"id": "m1", "inicio": 0, "fin": 9, "archivo": "musica/tension/pista_1.mp3", "animo": "tension"}],
                      "sfx": [{"id": "s1", "inicio": 3.0, "archivo": "sfx/pop.wav", "tipo": "pop"}]}}
    (raiz / "edl.json").write_text(json.dumps(edl), "utf-8")
    (raiz / "render" / "final.mp4").write_bytes(b"mp4")
    return raiz


def test_mover_un_corte_no_toca_la_edicion_automatica():
    raiz = _video()
    antes = (raiz / "edl.json").read_text()
    editor.mover_corte(raiz, 2, 3.8)                          # la escena 2 empieza 0,8 s más tarde
    assert (raiz / "edl.json").read_text() == antes           # lo automático queda igual
    t = editor.linea_de_tiempo(raiz)
    e1, e2 = t["escenas"][0], t["escenas"][1]
    assert e1["fin"] == e2["inicio"] == 3.8 and e2["corte_movido"]
    assert t["ediciones"]["pendientes"]                        # falta exportar
    editor.mover_corte(raiz, 2, 50)                           # no puede comerse la escena entera
    e2 = editor.linea_de_tiempo(raiz)["escenas"][1]
    assert e2["inicio"] == 6.0 - editor.MIN_CLIP
    editor.deshacer_escena(raiz, 2, "corte")
    assert editor.linea_de_tiempo(raiz)["escenas"][1]["inicio"] == 3.0


def test_subtitulos_editados_siguen_a_su_voz_si_se_regenera():
    raiz = _video()
    editor.cambiar_subtitulos(raiz, 2, [{"inicio": 3.1, "fin": 4.5, "texto": "Frase dos"},
                                        {"inicio": 4.5, "fin": 5.6, "texto": "corregida"}])
    subs = [s for s in editor.linea_de_tiempo(raiz)["subtitulos"] if s["escena"] == 2]
    assert [s["texto"] for s in subs] == ["Frase dos", "corregida"] and all(s["editado"] for s in subs)
    # la voz de la escena 2 se regeneró y ahora empieza 1 s más tarde: los subtítulos van con ella
    esc = json.loads((raiz / "escenas.json").read_text())
    esc["escenas"][1]["tiempo"]["real_inicio"] = 4.0
    (raiz / "escenas.json").write_text(json.dumps(esc))
    subs = [s for s in editor.linea_de_tiempo(raiz)["subtitulos"] if s["escena"] == 2]
    assert subs[0]["inicio"] == 4.1


def test_animacion_se_ve_como_clip_en_la_escena():
    raiz = _video()
    (raiz / "animaciones").mkdir()
    (raiz / "animaciones" / "escena_003_v1.mp4").write_bytes(b"clip")
    ed = editor.cargar(raiz)
    ed["animaciones"]["3"] = "animaciones/escena_003_v1.mp4"
    editor.guardar(raiz, ed)
    edl = editor.edl_con_ediciones(raiz)
    ef = [x for x in edl["pistas"]["escenas"][2]["efectos"] if x["efecto"] == "video_real"]
    assert ef and ef[0]["archivo"].endswith("escena_003_v1.mp4") and ef[0]["dur"] == 3.0
    assert editor.linea_de_tiempo(raiz)["escenas"][2]["animacion"].endswith(".mp4")


def test_api_del_editor_guarda_solo():
    from estudio import app as modulo_app

    _video()
    cli = TestClient(modulo_app.app)
    t = cli.get("/api/videos/peces/editor").json()
    assert [p for p in ("escenas", "voz", "musica", "sfx", "subtitulos") if p in t] == \
        ["escenas", "voz", "musica", "sfx", "subtitulos"]
    assert t["musica"][0]["nombre"] == "pista 1" and t["sfx"][0]["tipo"] == "pop"
    t = cli.put("/api/videos/peces/editor/escenas/3/corte", json={"inicio": 5.5}).json()
    assert t["escenas"][2]["inicio"] == 5.5 and t["ediciones"]["version"] == 1
    t = cli.put("/api/videos/peces/editor/escenas/1/subtitulos",
                json={"subtitulos": [{"inicio": 0.1, "fin": 2.0, "texto": "Hola"}]}).json()
    assert any(s["texto"] == "Hola" for s in t["subtitulos"]) and t["ediciones"]["version"] == 2
    assert cli.delete("/api/videos/peces/editor/escenas/3/corte").json()["escenas"][2]["inicio"] == 6.0
    assert cli.get("/api/videos/no-existe/editor").status_code == 404
