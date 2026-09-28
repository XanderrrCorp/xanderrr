"""Miniaturas escala 2x3: plan validado, generación por sujeto, composición y control de calidad."""
import json

import pytest
from PIL import Image

from estudio.miniaturas import composicion, plantilla as plantillas
from estudio.miniaturas.plan import Plan, planificar

CELDAS = [{"name": n, "label": n, "scene": f"a {n}", "is_hero": k == 0}
          for k, n in enumerate(["Candirú", "Piraña", "Anaconda", "Caimán", "Raya", "Nutria"])]
PLAN = {"scale_type": "peligro", "hook_mode": "isolated", "hook_visual": None, "cells": CELDAS,
        "hero_text": "¡no te metas al agua!", "hero_icon": "advertencia", "hero_glow_color": "#ff1a1a",
        "hero_censor": False}


def test_plan_cumple_la_formula():
    p = Plan.model_validate(PLAN)
    assert p.hero_text == "¡NO TE METAS AL AGUA!" and p.hero_glow_color == "#FF1A1A"
    with pytest.raises(ValueError):
        Plan.model_validate({**PLAN, "cells": CELDAS[:5]})                  # tienen que ser 6
    with pytest.raises(ValueError):
        Plan.model_validate({**PLAN, "cells": [dict(c, name="Piraña") for c in CELDAS]})   # sin repetir
    with pytest.raises(ValueError):
        Plan.model_validate({**PLAN, "hook_mode": "scene"})                  # scene sin gancho
    assert len(Plan.model_validate({**PLAN, "cells": [dict(CELDAS[0], label="x" * 40)] + CELDAS[1:]}).cells[0].label) == 20


def test_planificar_pone_al_protagonista_primero_y_corrige_errores():
    respuestas = iter([
        json.dumps({**PLAN, "hero_text": "UNA SOLA"[:3]}),                   # 1 palabra: no sirve
        json.dumps({**PLAN, "cells": CELDAS[1:] + [dict(CELDAS[0])], "hero_icon": "no-existe"}),
    ])
    pedidos = []

    def claude(prompt, cwd=None, **kw):
        pedidos.append(prompt)
        return next(respuestas), {}

    p = planificar("peces del Amazonas", plantillas.cargar("animales-peligrosos"), ejecutar=claude)
    assert p.cells[0].name == "Candirú" and p.cells[0].is_hero
    assert p.hero_icon == "advertencia"                                     # ícono fuera de la lista: el primero
    assert "no sirvió" in pedidos[1]


def _sujeto(color):
    img = Image.new("RGB", (1024, 1024), (255, 255, 255))
    from PIL import ImageDraw

    ImageDraw.Draw(img).ellipse((120, 160, 900, 980), fill=color)
    return img


def test_composicion_nunca_tapa_textos(tmp_path):
    (tmp_path / "sujetos").mkdir()
    datos = json.loads(json.dumps(PLAN))
    for k, c in enumerate(datos["cells"]):
        _sujeto((40 * k, 90, 160)).save(tmp_path / f"sujetos/s{k}.png")
        c["archivo"] = f"sujetos/s{k}.png"
    datos["cells"][3]["ajuste"] = {"escala": 2.5, "dx": 0, "dy": 200}      # el usuario lo agranda encima del texto
    plan = Plan.model_validate(datos)
    img, mapa = composicion.componer(tmp_path, plan, plantillas.cargar("animales-peligrosos"))
    assert img.size == (1280, 720)
    for t in mapa["textos"]:
        x0, y0, x1, y1 = t["caja"]
        zona = img.crop((max(0, x0), max(0, y0), min(1280, x1), min(720, y1))).convert("RGB")
        # dentro de la caja de un texto no aparece el color de ningún sujeto
        pix = set(zona.get_flattened_data() if hasattr(zona, "get_flattened_data") else zona.getdata())
        sujetos = [(40 * k, 90, 160) for k in range(6)]
        assert not any(max(abs(a - b) for a, b in zip(p, s)) < 12 for p in pix for s in sujetos), t["texto"]
    ruta = composicion.guardar_jpg(img, tmp_path / "m.jpg")
    assert ruta.stat().st_size < 2_000_000


def test_produccion_completa_con_control_de_calidad(tmp_path, monkeypatch):
    from estudio.config import ConfigCostos
    from estudio.imagenes.proveedores import ProveedorSimulado
    from estudio.miniaturas import servicio
    from estudio.pipeline import Trabajo
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Peces del Amazonas", "animales-peligrosos", "enciclopedia_mascota", 540)
    rondas = []

    def claude(prompt, cwd=None, herramientas=None):
        if "Planifica" in prompt:
            return json.dumps(PLAN), {}
        rondas.append(prompt)
        falla = len(rondas) == 1
        return json.dumps({"sujetos": [{"numero": 3, "ok": not falla, "problemas": ["parece un banco de sardinas"],
                                        "arreglo": "A single big anaconda"}], "protagonista_destaca": True,
                           "estilo_coherente": True, "resumen": "bien"}), {}

    class Blanco(ProveedorSimulado):
        def generar(self, prompt, referencias):
            import io
            r = super().generar(prompt, referencias)
            b = io.BytesIO()
            _sujeto((200, 60, 30)).save(b, "PNG")
            r.png = b.getvalue()
            assert len(referencias) <= 3
            return r

    prov = Blanco(ConfigCostos.cargar())
    t = Trabajo("miniatura")
    final = servicio.producir(c, t, ejecutar=claude, proveedor=prov)
    assert final.exists()
    plan = servicio._plan(c)
    assert len(plan.cells[2].variantes) == 2 and plan.cells[2].intentos_qa == 1   # la anaconda se regeneró
    assert prov.llamadas == 7
    informe = json.loads((servicio.carpeta(c) / "qa.json").read_text("utf-8"))
    assert informe["aprobada"] and len(informe["rondas"]) == 2
    # editar textos no regenera nada
    servicio.editar(c, {"labels": {"1": "Casi del 0 %"}, "hero_text": "TE ENGAÑA", "orden": [0, 2, 1, 3, 4, 5]})
    assert prov.llamadas == 7 and servicio._plan(c).cells[1].name == "Anaconda"


def test_api_editar_y_plantilla(tmp_path, monkeypatch):
    import shutil

    from fastapi.testclient import TestClient

    from estudio import app as modulo_app
    from estudio.miniaturas import servicio
    from estudio.proyecto import CarpetaProyecto

    base = tmp_path / "canales"
    shutil.copytree(plantillas.carpeta_canales() / "animales-peligrosos", base / "animales-peligrosos")
    monkeypatch.setenv("XANDART_CANALES", str(base))
    c = CarpetaProyecto.crear("Peces", "animales-peligrosos", "enciclopedia_mascota", 540)
    carpeta = servicio.carpeta(c)
    (carpeta / "sujetos").mkdir(parents=True)
    datos = json.loads(json.dumps(PLAN))
    for k, celda in enumerate(datos["cells"]):
        _sujeto((30 * k, 80, 150)).save(carpeta / f"sujetos/s{k}.png")
        celda["archivo"] = f"sujetos/s{k}.png"
        celda["variantes"] = [celda["archivo"]]
    servicio._guardar_plan(c, Plan.model_validate(datos))
    cli = TestClient(modulo_app.app)
    r = cli.put(f"/api/videos/{c.ruta.name}/miniatura", json={"hero_text": "una"})
    assert r.status_code == 400 and "2 a 5 palabras" in r.json()["detail"]
    r = cli.put(f"/api/videos/{c.ruta.name}/miniatura", json={"orden": [1, 0, 2, 3, 4, 5], "labels": {"5": "Casi del 0 %"}})
    plan = r.json()["plan"]
    assert r.status_code == 200 and plan["cells"][0]["name"] == "Piraña" and plan["cells"][0]["is_hero"]
    assert plan["cells"][5]["label"] == "Casi del 0 %" and r.json()["miniatura"]
    # referencias de estilo: subir, apagar y borrar
    import io
    b = io.BytesIO()
    _sujeto((10, 200, 10)).save(b, "PNG")
    r = cli.post("/api/canales/animales-peligrosos/miniatura/referencias", files={"archivo": ("nueva.png", b.getvalue())})
    assert any(x["archivo"] == "nueva.jpg" for x in r.json()["referencias"])
    r = cli.put("/api/canales/animales-peligrosos/miniatura/referencias/nueva.jpg", json={"activa": False})
    assert not next(x for x in r.json()["referencias"] if x["archivo"] == "nueva.jpg")["activa"]
    r = cli.delete("/api/canales/animales-peligrosos/miniatura/referencias/nueva.jpg")
    assert all(x["archivo"] != "nueva.jpg" for x in r.json()["referencias"])
    assert cli.get("/canales/..%2F..%2Fetc/referencias/passwd").status_code in (400, 404, 422, 500)


def test_medidas_del_armado(tmp_path):
    """Protagonista ≥ 1,3× el mayor, encimado ≤ 5 %, ícono libre y cabezas sin cortar; y en modo
    scene la escena no se recorta: va completa con bordes redondeados."""
    (tmp_path / "sujetos").mkdir()
    datos = json.loads(json.dumps(PLAN))
    for k, c in enumerate(datos["cells"]):
        _sujeto((40 * k, 90, 160)).save(tmp_path / f"sujetos/s{k}.png")
        c["archivo"] = f"sujetos/s{k}.png"
    _, mapa = composicion.componer(tmp_path, Plan.model_validate(datos), plantillas.cargar("animales-peligrosos"))
    m = mapa["medidas"]
    assert m["protagonista_vs_mayor"] >= 1.3 and m["protagonista_ok"]
    assert m["solape_max"] <= 0.05 and m["icono_libre"] and m["cabeza_sin_cortar"]
    escena = composicion.cargar_escena(tmp_path, "sujetos/s1.png", 1.5)
    assert escena.getpixel((0, 0))[3] == 0                                  # esquina redondeada
    assert escena.getpixel((60, 60))[:3] == (255, 255, 255)                 # el fondo blanco NO se quita
