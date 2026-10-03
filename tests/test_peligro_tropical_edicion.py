"""Edición de Peligro Tropical como la competencia (03-10): nada se mece ni tiembla, casi todo entra
deslizándose de lado con swoosh y se acerca despacio, flechas rojas curvas, elementos escalonados y
títulos negros sin borde."""
import json
import wave

import numpy as np
from PIL import Image


def _proyecto(estilo, n=14, por_escena=4.0):
    from estudio.edicion import construir_edl
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Desliza", "animales-peligrosos", estilo.id, n * por_escena, slug="desliza")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    escenas, textos, datos, focos = [], {}, {}, {}
    for i in range(1, n + 1):
        im = Image.new("RGB", (640, 360), (128, 128, 128))
        im.paste((40 + 12 * i, 120, 60), (200, 80, 440, 280))
        im.save(c.ruta / "imagenes" / f"escena_{i:03d}.png")
        t = (i - 1) * por_escena
        intencion = ("amenaza", "explicacion", "pregunta_al_espectador", "advertencia")[i % 4]
        narr = f"La frase número {i} habla del aguijón" + ("?" if intencion == "pregunta_al_espectador" else ".")
        escenas.append({"id": i, "seccion": "Uno", "narracion": narr, "intencion": intencion,
                        "intensidad": 3, "visual": {"accion": "generar", "tipo": "animal_fondo_gris", "prompt": "x",
                                                    "archivo": f"imagenes/escena_{i:03d}.png"},
                        "tiempo": {"real_inicio": t, "real_fin": t + por_escena - 0.3}})
        textos[str(i)] = {"texto": "Muy aterrador", "palabra": "número"}
        if i % 3 == 0:
            datos[str(i)] = {"texto": "No muerde", "icono": "no"}
        focos[str(i)] = {"tipo": "detalle", "caja": [0.4, 0.3, 0.6, 0.6], "palabra": "aguijón"}
    c.guardar_escenas(EscenasV2.model_validate({"video": "Desliza", "canal": "animales-peligrosos",
                                                "estilo": estilo.id, "escenas": escenas}))
    (c.ruta / "direccion.json").write_text(json.dumps({"textos": textos, "datos": datos, "focos": focos}), "utf-8")
    (c.ruta / "audio").mkdir(exist_ok=True)
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(np.zeros(48000 * int(n * por_escena + 2), "<i2").tobytes())
    return c, construir_edl(c)


def test_perfil_de_peligro_tropical_es_deslizar(estilo, perfil):
    assert estilo.perfil_edicion == "perfiles/peligro_tropical.json"
    assert perfil.movimiento == "deslizar" and estilo.titulo == "negro"


def test_sin_vaiven_ni_temblor_y_entradas_de_lado_suaves(estilo):
    _, edl = _proyecto(estilo)
    clips = edl["pistas"]["escenas"]
    efectos = [x for c in clips for x in c["efectos"]]
    assert not [x for x in efectos if x["efecto"] in ("vaiven", "temblor_leve", "entrada_rebote")]
    lados = [x for x in efectos if x["efecto"] == "entrada_lado"]
    assert len(lados) >= len(clips) // 2
    assert all(x.get("curva") == "suave" and x["dur"] >= 0.5 for x in lados)
    assert {x["desde"] for x in lados} == {"izquierda", "derecha"}
    # después de entrar, se acerca despacio
    movs = [c["movimiento"]["tipo"] for c in clips if c.get("movimiento")]
    assert movs.count("zoom_lento") >= len(clips) // 2
    # y suena el swoosh en las entradas de lado (no se recorta por repetirse)
    swoosh = [s for s in edl["pistas"]["sfx"] if s["variante"].startswith("barrido")]
    assert len(swoosh) >= len(lados) * 0.7


def test_flecha_curva_y_elementos_uno_tras_otro(estilo):
    _, edl = _proyecto(estilo)
    clips = edl["pistas"]["escenas"]
    flechas = [x for c in clips for x in c["efectos"] if x["efecto"] == "flecha"]
    assert flechas and all(x.get("curva") for x in flechas)
    assert all(x.get("vivo") for c in clips for x in c["efectos"] if x["efecto"] == "dato")
    titulos = {int(t["id"][1:]): t for t in edl["pistas"]["textos"]}
    for c in clips:
        entrada = next((x for x in c["efectos"] if x["efecto"].startswith("entrada_")), None)
        tiempos = sorted({x["en"] for x in c["efectos"] if x["efecto"] in ("flecha", "lupa", "dato", "signos_pregunta",
                                                                           "circulo_rojo", "etiqueta")}
                         | ({titulos[c["escena"]]["inicio"]} if c["escena"] in titulos else set()))
        for a, b in zip(tiempos, tiempos[1:]):
            if b <= c["fin"] - 0.7:
                assert b - a >= 0.44, (c["id"], tiempos)
        if entrada and tiempos and tiempos[0] <= c["fin"] - 0.7:
            assert tiempos[0] >= c["inicio"] + entrada["dur"]


def test_titulos_negros_con_triangulo_en_peligro(estilo):
    _, edl = _proyecto(estilo)
    estilos = {t["estilo"] for t in edl["pistas"]["textos"]}
    assert estilos == {"titulo_negro", "titulo_negro_alerta"}


def test_render_de_un_tramo_con_todo(estilo):
    from estudio.pipeline import ffmpeg
    from estudio.render import renderizar

    c, _ = _proyecto(estilo, n=3)
    f = renderizar(c, ffmpeg(), c.ruta / "render" / "t.mp4", avisar=lambda _: None, salida=(320, 180, 3), procesos=1)
    assert f.exists() and f.stat().st_size > 0
