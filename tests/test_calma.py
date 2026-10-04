"""Hazlo con Calma: piezas SVG, movimientos con rebote, escenas atadas a la voz y el video de punta a punta
(voz y Whisper simulados: sin gastar)."""
import json
import subprocess

import pytest

from estudio.calma import escenas as E
from estudio.calma import movimientos as M
from estudio.calma.personaje import CARAS, OJOS, POSES
from estudio.calma.piezas import PIEZAS
from estudio.calma.raster import sprite

EJEMPLO = E.__file__.replace("escenas.py", "ejemplos/garrapata_60s")


def _ejemplo():
    datos = json.load(open(EJEMPLO + ".json", encoding="utf-8"))
    texto = open(EJEMPLO + ".txt", encoding="utf-8").read()
    return datos, texto


def test_personaje_completo_por_piezas():
    assert {"de_pie", "senalando", "asustado", "corriendo", "agachado", "sentado"} <= set(POSES)
    assert len(OJOS) == 3 and len(CARAS) == 4
    for pose in POSES:
        img, ancla = sprite("personaje", {"pose": pose, "ojos": "cerrados", "gesto": "susto"}, 0.5)
        assert img.shape[2] == 4 and img[:, :, 3].max() == 255


def test_todas_las_piezas_se_dibujan():
    for nombre in PIEZAS:
        img, _ = sprite(nombre, {"texto": "PRUEBA", "valor": "3"} if nombre in ("rotulo", "numero") else {}, 0.4)
        assert (img[:, :, 3] > 0).mean() > 0.01, nombre


def test_el_trazo_es_el_mismo_en_cada_cuadro():
    from estudio.calma.piezas import dibujar

    assert dibujar("garrapata", {}).svg == dibujar("garrapata", {}).svg     # no «hierve» entre cuadros


def test_movimientos_no_lineales_con_rebote_leve():
    valores = [M.resorte(i / 100) for i in range(101)]
    assert valores[0] == 0 and valores[-1] == 1
    assert 1.05 < max(valores) <= M.PASADA_MAX                            # se pasa un poco y vuelve
    assert M.suave(0.1) < 0.1 and M.suave(0.9) > 0.9                      # arranca y frena suave
    assert max(M.rebote(i / 100, 1.1) for i in range(101)) > 1.0


def test_el_personaje_siempre_parpadea():
    el = {"id": "yo", "pieza": "personaje", "entra": 0.0, "estado": {"pose": "de_pie"}, "movimiento": []}
    cerrados = [t / 30 for t in range(300) if M.estado_en(el, t / 30, 10).estado.get("ojos") == "cerrados"]
    assert cerrados
    huecos = [b - a for a, b in zip(cerrados, cerrados[1:]) if b - a > 0.2]
    assert all(h <= 4.1 for h in huecos)


def test_elementos_entran_con_la_palabra_y_respetan_el_ritmo():
    datos, texto = _ejemplo()
    palabras, dur = E.tiempos_estimados(texto)
    E.fijar_tiempos(datos, palabras, dur)
    assert E.revisar(datos) == []
    garr = next(x for x in datos["escenas"][0]["elementos"] if x["id"] == "garrapata")
    esta = next(w for w in palabras if w["n"] == "esta")
    assert garr["entra"] == esta["inicio"]
    for a, b in zip(datos["escenas"], datos["escenas"][1:]):
        assert a["fin"] == b["inicio"]                                    # cortes secos, sin huecos


def test_revisar_avisa_si_algo_tarda_mucho():
    datos = {"video": {"duracion": 6.0}, "escenas": [{"id": 1, "inicio": 0, "fin": 6, "fondo": "blanco",
             "elementos": [{"id": "a", "pieza": "chulo", "entra": 0.5}]}]}
    assert any("no aparece ni cambia nada" in x for x in E.revisar(datos))


def test_palabra_que_no_esta_da_error_claro():
    datos, texto = _ejemplo()
    datos["escenas"][0]["elementos"][0]["palabra"] = "elefante"
    with pytest.raises(ValueError, match="elefante"):
        E.fijar_tiempos(datos, *E.tiempos_estimados(texto))


def test_video_de_prueba_completo_simulado(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))                             # la copia final no va a la carpeta real
    from estudio.calma import flujo
    from estudio.pipeline import Trabajo, ffmpeg

    flujo.guardar_ajustes({"segundos": 6.0})
    c = flujo.preparar()
    t = Trabajo("calma")
    destino = flujo.producir(c, t, proveedor="simulado")
    info = json.loads((c.ruta / "informe.json").read_text(encoding="utf-8"))
    assert destino.exists() and info["duracion"] <= 6.5 and info["render"]["cuadros"] > 100
    r = subprocess.run([ffmpeg(), "-i", str(destino)], capture_output=True, text=True)
    assert "Video: h264" in r.stderr and "1920x1080" in r.stderr and "Audio: aac" in r.stderr
    assert "30 fps" in r.stderr
    destino.unlink()


def test_sin_voz_del_canal_no_gasta_y_avisa():
    from estudio.calma import flujo
    from estudio.pipeline import Trabajo

    with pytest.raises(RuntimeError, match="código de la voz"):
        flujo.producir(flujo.preparar(), Trabajo("calma"))


def test_pagina_guarda_la_voz_y_no_arranca_sin_ella(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import estudio.app as modulo

    cliente = TestClient(modulo.app)
    e = cliente.get("/api/calma").json()
    assert e["ajustes"]["voz_id"] is None and e["costo_voz"]["caracteres"] > 900
    assert cliente.post("/api/calma/prueba", json={}).status_code == 400
    e = cliente.post("/api/calma/ajustes", json={"voz_id": "  moss_audio_prueba  ", "volumen_musica_db": -30}).json()
    assert e["ajustes"]["voz_id"] == "moss_audio_prueba" and e["ajustes"]["volumen_musica_db"] == -30
    assert cliente.post("/api/calma/ajustes", json={"musica": "C:/no/existe.mp3"}).status_code == 400
    assert cliente.get("/api/calma/video").status_code == 404


def test_elige_la_musica_de_ritmo_bajo_y_sin_melodia(tmp_path, monkeypatch):
    import io
    import wave

    import numpy as np

    from estudio import biblioteca
    from estudio.calma.musica import elegir
    from estudio.pipeline import ffmpeg

    monkeypatch.setenv("XANDART_BIBLIOTECA", str(tmp_path / "bib"))
    sr = 22050
    t = np.arange(sr * 20) / sr
    rng = np.random.default_rng(1)
    colchon = 0.2 * np.convolve(rng.standard_normal(len(t)), np.ones(40) / 40, "same") * (1 + 0.3 * np.sin(t * 0.5))
    melodia = 0.5 * np.sin(2 * np.pi * np.repeat([440, 660, 550, 880], len(t) // 4 + 1)[: len(t)] * t)
    golpes = np.zeros_like(t)
    for k in range(0, len(t), sr // 4):                                    # 4 golpes por segundo
        golpes[k:k + 300] = 0.9 * np.exp(-np.arange(min(300, len(t) - k)) / 60)

    def wav(x):
        b = io.BytesIO()
        with wave.open(b, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
        return b.getvalue()

    biblioteca.registrar(wav(melodia + golpes), "ritmo_con_melodia.wav", "musica", "tension", "propia", "propia")
    biblioteca.registrar(wav(colchon), "colchon_tenso.wav", "musica", "tension", "propia", "propia")
    elegida = elegir(ffmpeg(), avisar=lambda *_: None)
    assert elegida["nombre_original"] == "colchon_tenso.wav" and elegida["de"] == 2


def test_poses_y_caras_nuevas_de_el_calvo_explica():
    from estudio.calma.personaje import CARAS_NUEVAS

    nuevas = ("tablero", "pensando", "confundido", "hombros", "sorprendido", "aliviado", "idea", "acostado")
    assert set(nuevas) <= set(POSES) and len(CARAS_NUEVAS) == 8
    for pose in nuevas:
        img, _ = sprite("personaje", {"pose": pose, "gesto": "sorpresa"}, 0.4)
        assert (img[:, :, 3] > 0).mean() > 0.05, pose
    img, _ = sprite("tablero", {}, 0.4)
    assert img[:, :, 3].max() == 255


def test_canal_el_calvo_explica_por_defecto():
    from estudio.config import leer_config
    from estudio.explica.canal import ajustes_voz, completar

    p = completar({"velocidad": 1.1, "cosa_rara": 1})
    assert p["velocidad"] == 1.1 and "cosa_rara" not in p
    assert p["max_ilustraciones"] == 60 and p["fondo"] == "blanco" and p["efectos_sonido"] is False
    assert ajustes_voz(completar(None))["voz_id"] == leer_config("proveedores.json")["voz"]["voz_id"]   # la de PT
    assert "Sin texto" in p["estilo_ilustracion"]


def test_caras_por_defecto_de_el_calvo_explica():
    from estudio.explica.canal import GESTO_POR_POSE, OJOS_POR_POSE

    preocupadas = {"neutral", "duda"}
    assert {p for p, g in GESTO_POR_POSE.items() if g in preocupadas} == {"confundido", "hombros", "acostado"}
    assert GESTO_POR_POSE["tablero"] == "seguro" and OJOS_POR_POSE["acostado"] == "cerrados"
    assert {"rechazo", "senalando_contento"} <= set(POSES)
    from estudio.calma.piezas import dibujar

    # ojos y cara siguen siendo piezas aparte: cambiar los ojos no cambia el cuerpo
    a = dibujar("personaje", {"pose": "rechazo", "ojos": "abiertos"}).svg
    b = dibujar("personaje", {"pose": "rechazo", "ojos": "cerrados"}).svg
    assert a != b and a.split("<g")[0] == b.split("<g")[0]
    assert "tab/linea" not in dibujar("tablero", {}).svg                    # tablero vacío


def test_muestras_con_proveedor_simulado():
    from estudio.config import ConfigCostos
    from estudio.explica import ilustraciones as I
    from estudio.imagenes.proveedores import ProveedorSimulado
    from estudio.pipeline import Trabajo

    p = ProveedorSimulado(ConfigCostos.cargar())
    assert I.costo_muestras(p)["usd"] > 0
    hechas = I.generar_muestras(Trabajo("muestras"), proveedor=p)
    assert hechas == ["cama.png", "escalon.png", "brinco.png"]
    assert all((I.carpeta() / h).exists() for h in hechas)
    assert I.estado_muestras()["archivos"] == hechas
    assert "Sin texto" in I.prompt("algo") and (I.carpeta() / "referencia_personaje.png").exists()
