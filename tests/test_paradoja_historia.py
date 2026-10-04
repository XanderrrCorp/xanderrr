"""Paradoja Sapiens como historia (04-10): pantalla completa con zoom de documental, fundidos, tarjetas
de capítulo y viñeta; identidad distinta de Peligro Tropical."""
import json
import wave

import numpy as np
from PIL import Image


def _proyecto():
    from estudio.edicion import construir_edl
    from estudio.esquemas import EscenasV2
    from estudio.estilos import cargar_estilo
    from estudio.proyecto import CarpetaProyecto

    estilo = cargar_estilo("paradoja_sapiens")
    c = CarpetaProyecto.crear("Por qué el Congo", "paradoja", estilo.id, 60, slug="congo")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    (c.ruta / "audio").mkdir(exist_ok=True)
    secciones = [("Gancho", 3), ("El río que no se cruza", 4), ("La selva que no deja pasar", 4), ("Cierre", 2)]
    escenas, t, eid = [], 0.0, 1
    for sec, n in secciones:
        for k in range(n):
            tipo = "animal_fondo_gris" if k == 2 else "escena_cartoon_completa"
            im = Image.new("RGB", (640, 360), (128, 128, 128) if tipo == "animal_fondo_gris" else (40 + 15 * eid, 120, 90))
            if tipo == "animal_fondo_gris":
                im.paste((200, 90, 40), (220, 90, 420, 270))
            im.save(c.ruta / "imagenes" / f"e{eid}.png")
            intencion = "gancho" if (sec == "Gancho" and k == 0) else "explicacion"
            escenas.append({"id": eid, "seccion": sec, "narracion": f"Frase {eid} de la historia del río.",
                            "intencion": intencion, "intensidad": 3,
                            "visual": {"accion": "generar", "tipo": tipo, "prompt": "x", "archivo": f"imagenes/e{eid}.png"},
                            "tiempo": {"real_inicio": t, "real_fin": t + 3.7}})
            t, eid = t + 4.0, eid + 1
    c.guardar_escenas(EscenasV2.model_validate({"video": "Congo", "canal": "paradoja", "estilo": estilo.id,
                                                "escenas": escenas}))
    (c.ruta / "direccion.json").write_text(json.dumps({"terminos": {"6": "historia"}}), "utf-8")
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(np.zeros(int(48000 * (t + 2)), "<i2").tobytes())
    return c, construir_edl(c)


def _ef(clip, nombre):
    return next((x for x in clip["efectos"] if x["efecto"] == nombre), None)


def test_perfil_historia_de_paradoja():
    from estudio.estilos import cargar_estilo, cargar_perfil_edicion

    e = cargar_estilo("paradoja_sapiens")
    assert e.perfil_edicion == "perfiles/paradoja_historia.json"
    assert cargar_perfil_edicion(e).movimiento == "historia"


def test_historia_pantalla_completa_zoom_variado_capitulos_y_vineta():
    _, edl = _proyecto()
    clips = edl["pistas"]["escenas"]
    completas = [c for c in clips if c["modo"] == "pantalla_completa"]
    assert len(completas) >= 9                                         # todas las escenas completas, gancho incluido
    assert all(_ef(c, "vineta") for c in completas)
    tipos = [(c["movimiento"] or {}).get("tipo") for c in completas]
    assert {"zoom_lento", "alejamiento_lento", "paneo_lento"} & set(tipos)
    seguidos = [(a, b) for a, b in zip(tipos, tipos[1:]) if a == b and a != "zoom_golpe"]
    assert len(seguidos) <= 2                     # casi nunca el mismo movimiento dos veces seguidas
    assert {c["transicion_entrada"] for c in clips} & {"fundido_corto", "barrido"}
    caps = [_ef(c, "capitulo") for c in clips if _ef(c, "capitulo")]
    assert [(x["numero"], x["titulo"]) for x in caps] == [(1, "El río que no se cruza"), (2, "La selva que no deja pasar")]
    assert not any(_ef(c, x) for c in clips for x in ("vaiven", "temblor_leve", "pila_fotos"))
    term = next(_ef(c, "palabra_completa") for c in clips if _ef(c, "palabra_completa"))
    assert term["fondo"] == "papel"
    # el recorte sigue sobre el papel y entra deslizándose
    recortes = [c for c in clips if c["modo"] == "recorte_sobre_papel"]
    assert recortes and any(_ef(c, "entrada_lado") or _ef(c, "entrada_abajo") for c in recortes)


def test_render_historia():
    from estudio.pipeline import ffmpeg
    from estudio.render import renderizar

    c, _ = _proyecto()
    f = renderizar(c, ffmpeg(), c.ruta / "render" / "h.mp4", avisar=lambda _: None, salida=(320, 180, 3), procesos=1)
    assert f.exists() and f.stat().st_size > 0


def test_estela_y_barrido():
    from estudio.render import H, W, barrido, estela

    capa = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    capa.paste((200, 80, 40, 255), (50, 20, 150, 80))
    quieta, movida = estela(capa, 0, 0), estela(capa, 60, 0)
    assert quieta is capa                                               # sin movimiento no se toca
    a = np.asarray(movida)[:, :, 3]
    assert a[50, 40] > 0 and a[50, 160] > 0 and a[50, 100] == 255       # el rastro sale a los lados, el centro sigue
    assert np.asarray(movida)[50, 45, :3].tolist()[0] > 150             # sin bordes oscuros (alfa premultiplicado)
    sale = Image.new("RGB", (W, H), (255, 0, 0))
    entra = Image.new("RGB", (W, H), (0, 0, 255))
    medio = np.asarray(barrido(sale, entra, 0.15, "derecha"))
    assert medio[H // 2, 5, 0] > 100 and medio[H // 2, W - 5, 2] > 100  # se ven las dos escenas a la vez
    final = np.asarray(barrido(sale, entra, 1.0))
    assert final[H // 2, W // 2].tolist() == [0, 0, 255]                # al terminar, solo la nueva y nítida


def test_barridos_entre_escenas_grandes_con_swoosh():
    _, edl = _proyecto()
    clips = edl["pistas"]["escenas"]
    con_barrido = [c for c in clips if c["transicion_entrada"] == "barrido"]
    assert con_barrido and all(c["modo"] == "pantalla_completa" for c in con_barrido)
    swoosh = {round(s["inicio"], 2) for s in edl["pistas"]["sfx"] if s["tipo"] == "barrido"}
    assert all(round(c["inicio"], 2) in swoosh for c in con_barrido)


def _escena_con_sujeto(ruta):
    from PIL import ImageDraw

    im = Image.new("RGB", (1280, 720), (60, 110, 160))
    d = ImageDraw.Draw(im)
    for x in range(0, 1280, 80):                                    # fondo con rayas (para ver el movimiento)
        d.rectangle((x, 0, x + 40, 720), fill=(70, 125, 175))
    d.ellipse((520, 180, 760, 600), fill=(230, 160, 40))           # el sujeto
    im.save(ruta)


def test_profundidad_separa_y_mueve_fondo_y_frente(tmp_path, monkeypatch):
    import estudio.render as r

    _escena_con_sujeto(tmp_path / "e.png")
    img = Image.open(tmp_path / "e.png").resize((r.W, r.H))
    a = np.asarray(img)
    monkeypatch.setattr(r, "mascara_sujeto",
                        lambda im: (((np.asarray(im)[:, :, 0] > 200) & (np.asarray(im)[:, :, 2] < 90)) * 255).astype("uint8"))
    capas = r.capas_de_profundidad(img, tmp_path, "imagenes/e.png")
    assert capas is not None and (tmp_path / "assets" / "capas").exists()
    fondo, frente = capas
    centro = np.asarray(fondo)[r.H // 2, r.W // 2]
    assert centro[0] < 150                                          # el hueco del sujeto quedó rellenado con fondo
    assert np.asarray(frente)[r.H // 2, r.W // 2, 3] > 200 and np.asarray(frente)[10, 10, 3] == 0
    ini, fin = r.con_profundidad(capas, 1.0, (0.5, 0.5), 0.0), r.con_profundidad(capas, 1.08, (0.5, 0.5), 1.0)
    assert ini.size == (r.W, r.H) and np.asarray(ini).tobytes() != np.asarray(fin).tobytes()
    assert r.capas_de_profundidad(img, tmp_path, "imagenes/e.png") is not None      # segunda vez: del disco
    # sujeto que llena casi todo: no se separa (queda el zoom normal) y no se vuelve a intentar
    monkeypatch.setattr(r, "mascara_sujeto", lambda im: np.full((r.H, r.W), 255, np.uint8))
    assert r.capas_de_profundidad(img, tmp_path, "imagenes/otra.png") is None
    assert list((tmp_path / "assets" / "capas").glob("*.no"))


def test_escenas_grandes_llevan_profundidad():
    _, edl = _proyecto()
    completas = [c for c in edl["pistas"]["escenas"] if c["modo"] == "pantalla_completa"]
    assert completas and all(_ef(c, "profundidad") for c in completas)
