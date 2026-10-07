"""Video híbrido de Peligro Tropical (07-10): algunas escenas que explican algo van animadas por código (motor de
El Calvo Explica) sobre el papel del canal; el guion no cambia y esas escenas no pagan imagen."""
import json
import wave

import numpy as np
from PIL import Image


def _proyecto(estilo, n=12, por_escena=3.0):
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Híbrido", "animales-peligrosos", estilo.id, n * por_escena, slug="hibrido")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    escenas = []
    for i in range(1, n + 1):
        Image.new("RGB", (640, 360), (90, 120 + 5 * i, 60)).save(c.ruta / "imagenes" / f"escena_{i:03d}.png")
        t = (i - 1) * por_escena
        escenas.append({"id": i, "seccion": "Uno", "intensidad": 3, "intencion": "explicacion",
                        "narracion": f"Su veneno ataca los nervios y el dolor dura tres horas, frase {i}.",
                        "visual": {"accion": "generar", "tipo": "animal_fondo_gris", "prompt": "x",
                                   "archivo": f"imagenes/escena_{i:03d}.png"},
                        "tiempo": {"real_inicio": t, "real_fin": t + por_escena - 0.3}})
    c.guardar_escenas(EscenasV2.model_validate({"video": "Híbrido", "canal": "animales-peligrosos",
                                                "estilo": estilo.id, "escenas": escenas}))
    (c.ruta / "direccion.json").write_text("{}", "utf-8")
    (c.ruta / "audio").mkdir(exist_ok=True)
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(np.zeros(48000 * int(n * por_escena + 2), "<i2").tobytes())
    return c


def _claude_falso(elegidas):
    def ejecutar(prompt, cwd=None, herramientas=None, **_):
        assert "PIEZAS" in prompt and "\n- personaje:" not in prompt        # sin el Calvo en otro canal
        anims = [{"escena": i, "elementos": [
            {"id": "m", "pieza": "medidor", "estado": {"nivel": 0.9}, "posicion": [700, 480], "tamano": 1.0,
             "palabra": "veneno", "movimiento": ["aparecer"]},
            {"id": "t", "pieza": "texto", "estado": {"texto": "TRES HORAS", "color": "rojo"}, "posicion": [1300, 480],
             "palabra": "tres", "movimiento": ["aparecer"]},
            {"id": "p", "pieza": "personaje", "estado": {}, "posicion": [300, 990], "palabra": "dolor"}],
            "empujon": [{"palabra": "nervios", "foco": [700, 480]}]} for i in elegidas]
        return json.dumps({"animaciones": anims}), {}
    return ejecutar


def test_estilo_de_peligro_tropical_pide_animaciones(estilo):
    assert estilo.animaciones_codigo == 0.25


def test_disenar_elige_escenas_que_ya_no_pagan_imagen(estilo):
    from estudio.animaciones_codigo import DISENOS, candidatas, disenar

    c = _proyecto(estilo)
    ids = [e.id for e in candidatas(c.cargar_escenas())]
    assert ids and min(ids) >= 4                                          # el arranque del video queda con imágenes
    d = disenar(c, ejecutar=_claude_falso([5, 9]), avisar=lambda *_: None)
    assert set(d["escenas"]) == {"5", "9"}
    piezas = [x["pieza"] for x in d["escenas"]["5"]["escena"]["elementos"]]
    assert "personaje" not in piezas and "medidor" in piezas
    esc = {e.id: e for e in c.cargar_escenas().escenas}
    assert esc[5].visual.accion == "reusar" and esc[5].visual.reusar_de == 4
    assert esc[9].visual.reusar_de == 8 and esc[6].visual.accion == "generar"
    assert (c.ruta / DISENOS).exists()
    assert disenar(c, ejecutar=lambda *a, **k: (_ for _ in ()).throw(AssertionError("no repite")),
                   avisar=lambda *_: None) == d


def test_animacion_en_la_edicion_y_en_el_video(estilo):
    from estudio.animaciones_codigo import deshacer, disenar, renderizar
    from estudio.edicion import construir_edl
    from estudio.pipeline import ffmpeg

    c = _proyecto(estilo)
    disenar(c, ejecutar=_claude_falso([6]), avisar=lambda *_: None)
    assert renderizar(c, ffmpeg(), avisar=lambda *_: None) == 1
    a = json.loads((c.ruta / "direccion.json").read_text("utf-8"))["animacion_escena"]["6"]
    assert (c.ruta / a["archivo"]).exists() and a["efectos"]
    edl = construir_edl(c)
    clip = next(x for x in edl["pistas"]["escenas"] if x["escena"] == 6)
    assert [x["efecto"] for x in clip["efectos"]] == ["animacion"]
    assert not [t for t in edl["pistas"]["textos"] if clip["inicio"] <= t["inicio"] < clip["fin"]]
    # se puede volver atrás: la escena recupera su imagen y la edición ya no la anima
    assert deshacer(c) == 1
    assert c.cargar_escenas().escenas[5].visual.accion == "generar"
    renderizar(c, ffmpeg(), avisar=lambda *_: None)
    edl = construir_edl(c)
    assert not [x for x in edl["pistas"]["escenas"] if any(e["efecto"] == "animacion" for e in x["efectos"])]
