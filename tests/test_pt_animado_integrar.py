"""Fase 4 de Peligro Tropical animado: partes animadas (Remotion) dentro del video normal, sin Remotion ni Google de
verdad (render y proveedor simulados)."""
import io
import json
import wave
from types import SimpleNamespace

import numpy as np
from PIL import Image


def _proyecto(estilo, canal="animales-peligrosos"):
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Granja", canal, estilo.id, 90, slug="granja")
    for carpeta in ("imagenes", "assets", "audio"):
        (c.ruta / carpeta).mkdir(exist_ok=True)
    escenas, t, eid = [], 0.0, 1
    secciones = [("Gancho", ["En una granja hay un animal que manda gente al hospital.", "Casi todos lo hemos acariciado.",
                             "Vamos de la gallina hasta él.", "Caminas por el potrero con tus botas.",
                             "Y de pronto algo se mueve.", "Te da un susto enorme."])]
    nombres = ["Gallina", "Ganso", "Toro", "Caballo"]
    for i, n in enumerate(nombres, 1):
        secciones.append((f"Nivel {i} · {n}", [f"Nivel {i}: {n.lower()}.", f"Imagina que te encuentras un {n.lower()}.",
                                                "Se acerca despacio.", "Y te ataca de repente."]))
    secciones.append(("Cierre", ["El más peligroso es el que más confianza nos da.", "Nadie lo espera.",
                               "Ahora ya lo sabes.", "Cuéntamelo en los comentarios."]))
    for sec, frases in secciones:
        for narr in frases:
            Image.new("RGB", (640, 360), (90, 120, 160)).save(c.ruta / "imagenes" / f"e{eid}.png")
            escenas.append({"id": eid, "seccion": sec, "narracion": narr, "intencion": "explicacion", "intensidad": 3,
                            "visual": {"accion": "generar", "tipo": "escena_cartoon_completa", "prompt": "x",
                                       "archivo": f"imagenes/e{eid}.png"},
                            "tiempo": {"real_inicio": t, "real_fin": t + 2.6}})
            t, eid = t + 3.0, eid + 1
    for i in range(1, 5):
        Image.new("RGB", (64, 64)).save(c.ruta / "assets" / f"tira_{i}.png")
    doc = {"video": "Granja", "canal": canal, "estilo": estilo.id,
           "assets": [{"id": f"tira_{i}", "tipo": "animal", "archivo": f"assets/tira_{i}.png"} for i in range(1, 5)],
           "niveles": [{"numero": i, "nombre": n, "asset": f"tira_{i}", "villano": i == 4} for i, n in enumerate(nombres, 1)],
           "escenas": escenas}
    c.guardar_escenas(EscenasV2.model_validate(doc))
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes(np.zeros(int(48000 * (t + 2)), "<i2").tobytes())
    return c


class _Prov:
    def __init__(self):
        self.pedidos = []

    def estimar_usd(self, prompt, refs):
        return 0.03

    def generar(self, prompt, refs):
        self.pedidos.append(prompt)
        im = Image.new("RGB", (256, 256), (255, 255, 255))
        im.paste((200, 80, 40), (60, 60, 200, 200))
        b = io.BytesIO(); im.save(b, "PNG")
        return SimpleNamespace(png=b.getvalue(), proveedor="simulado", modelo="x",
                               uso=SimpleNamespace(unidades=lambda: 1, costo_usd=0.03))


def _render_falso(hechos):
    def render(pedidos, salida, avisar):
        for p in pedidos:
            hechos.append(p)
            (salida / f"{p['nombre']}.mp4").write_bytes(b"0")
    return render


def test_solo_en_peligro_tropical():
    from estudio.pt_animado import integrar

    assert integrar.activa("animales-peligrosos", {})
    assert not integrar.activa("animales-peligrosos", {"animado": False})
    assert not integrar.activa("tracy-principal", {"animado": True})


def test_intro_encuentros_y_cierre_marcados_en_las_escenas(estilo):
    from estudio.edicion import construir_edl
    from estudio.pt_animado import integrar

    c = _proyecto(estilo)
    hechos, prov = [], _Prov()
    n = integrar.preparar(c, avisar=lambda *_: None, permiso=True, render=_render_falso(hechos), proveedor=prov)
    assert n > 0
    comps = [h["comp"] for h in hechos]
    assert comps[0] == "Intro" and comps[-1] == "Cierre" and "Encuentro" in comps
    assert len(prov.pedidos) == 4                                  # un dibujo por animal, nada más
    grandes = [h["props"]["altoAnimal"] for h in hechos if h["comp"] == "Encuentro"]
    assert max(grandes) > 1.4 and min(grandes) < 1.0               # el toro y el caballo más grandes que la gallina
    d = json.loads((c.ruta / "direccion.json").read_text("utf-8"))["animacion_escena"]
    assert all(v["origen"] == "pt_animado" for v in d.values())
    assert any(v["desde"] > 0 for v in d.values())                 # las escenas siguientes arrancan más adentro del clip
    edl = construir_edl(c)
    animadas = [x for cl in edl["pistas"]["escenas"] for x in cl["efectos"] if x["efecto"] == "animacion"]
    assert len(animadas) == n
    assert edl["pistas"]["subtitulos"]                             # los subtítulos siguen encima
    # la segunda vez no se repite nada (ni Google ni Remotion)
    integrar.preparar(c, avisar=lambda *_: None, permiso=True, render=_render_falso(hechos), proveedor=prov)
    assert len(prov.pedidos) == 4 and len(hechos) == len(comps)


def test_sin_permiso_de_gasto_los_animales_quedan_fuera(estilo, monkeypatch):
    from estudio.costos import LibroCostos, FrenoPresupuesto
    from estudio.pt_animado import integrar

    def frenar(self, costo, permiso=False, categoria="base"):
        raise FrenoPresupuesto("Se pasaría del máximo.")
    monkeypatch.setattr(LibroCostos, "autorizar", frenar)
    c = _proyecto(estilo)
    hechos = []
    integrar.preparar(c, avisar=lambda *_: None, render=_render_falso(hechos), proveedor=_Prov())
    assert "Encuentro" not in [h["comp"] for h in hechos]           # sin dibujo no hay encuentro animado
    assert [h["comp"] for h in hechos].count("Cierre") == 1


def test_otro_canal_no_cambia(estilo):
    from estudio.pt_animado import integrar

    c = _proyecto(estilo, canal="tracy-principal")
    hechos = []
    assert integrar.preparar(c, avisar=lambda *_: None, render=_render_falso(hechos), proveedor=_Prov()) == 0
    assert not hechos
