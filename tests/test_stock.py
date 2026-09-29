"""Fotos y videos reales: solo lo verificado se usa, con su registro de origen y licencia."""
import io
import json

import pytest
from PIL import Image

from estudio import stock


class Resp:
    def __init__(self, datos=None, contenido=b""):
        self._d, self.content, self.status_code = datos, contenido, 200

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


def _png():
    b = io.BytesIO()
    Image.new("RGB", (64, 40), (120, 80, 40)).save(b, "PNG")
    return b.getvalue()


class SesionFalsa:
    def __init__(self):
        self.pedidos = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.pedidos.append(url)
        if url == stock.API_FOTOS:
            assert headers["Authorization"] == "clave-prueba"          # Pexels usa la clave tal cual
            return Resp({"photos": [{"id": i, "url": f"https://www.pexels.com/photo/{i}/", "photographer": "Ana",
                                     "photographer_url": "https://www.pexels.com/@ana",
                                     "src": {"medium": f"m{i}", "large": f"l{i}", "large2x": f"L{i}"}} for i in (1, 2, 3)]})
        if url == stock.API_VIDEOS:
            return Resp({"videos": [{"id": 9, "url": "https://www.pexels.com/video/9/", "duration": 8, "image": "mv",
                                     "user": {"name": "Luis", "url": "u"},
                                     "video_files": [{"file_type": "video/mp4", "width": 1920, "link": "V9"}]}]})
        return Resp(contenido=_png())


def test_solo_se_baja_lo_verificado(tmp_path, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    (tmp_path / "escenas.json").write_text(json.dumps({"niveles": [{"numero": 1, "nombre": "Cucaracha americana",
                                                                     "asset": "a", "villano": False}]}), "utf-8")

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return '{"1": "american cockroach"}', {}
        assert "Read" in (herramientas or []) and "hoja_nivel_1.png" in prompt
        return '{"aprobados": [{"numero": 2, "razon": "cucaracha americana clara"}, {"numero": 4, "razon": "video claro"}]}', {}

    sesion = SesionFalsa()
    idx = stock.preparar_stock(tmp_path, ejecutar=claude, avisar=lambda *_: None, sesion=sesion)
    tipos = sorted(a["tipo"] for a in idx["archivos"])
    assert tipos == ["foto", "video"]                                   # la 1 y la 3 no se aprobaron
    foto = next(a for a in idx["archivos"] if a["tipo"] == "foto")
    assert foto["url_origen"] == "https://www.pexels.com/photo/2/" and foto["verificado"] and "Pexels" in foto["licencia"]
    assert "L1" not in sesion.pedidos and "L3" not in sesion.pedidos    # lo no aprobado ni se descarga
    assert (tmp_path / foto["archivo"]).exists()
    # reanudable: no vuelve a buscar
    n = len(sesion.pedidos)
    stock.preparar_stock(tmp_path, ejecutar=claude, avisar=lambda *_: None, sesion=sesion)
    assert len(sesion.pedidos) == n


def test_sin_clave_avisa(tmp_path, monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    monkeypatch.setattr(stock, "clave_api", lambda _: None)
    (tmp_path / "escenas.json").write_text(json.dumps({"niveles": [{"numero": 1, "nombre": "x", "asset": "a"}]}), "utf-8")
    with pytest.raises(stock.SinClavePexels):
        stock.preparar_stock(tmp_path, ejecutar=lambda *a, **k: ("{}", {}), avisar=lambda *_: None)


def test_sin_fotos_en_pexels_gemini_hace_una_recreacion_revisada(tmp_path, monkeypatch):
    from estudio.config import ConfigCostos
    from estudio.imagenes.proveedores import ProveedorSimulado

    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    (tmp_path / "escenas.json").write_text(json.dumps({"niveles": [{"numero": 1, "nombre": "Chinche besucona",
                                                                     "asset": "a", "villano": False}]}), "utf-8")

    class SinResultados(SesionFalsa):
        def get(self, url, params=None, headers=None, timeout=None):
            return Resp({"photos": [], "videos": []})

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return '{"1": "kissing bug triatoma"}', {}
        assert "nivel_1_foto_ia.png" in prompt and "Read" in herramientas
        return '{"aprobada": true, "razon": "triatoma con anatomía correcta"}', {}

    idx = stock.preparar_stock(tmp_path, ejecutar=claude, avisar=lambda *_: None, sesion=SinResultados(),
                               proveedor=ProveedorSimulado(ConfigCostos.cargar()))
    (a,) = idx["archivos"]
    assert a["sintetica"] and a["verificado"] and "no es una foto real" in a["licencia"]
    assert (tmp_path / a["archivo"]).exists()
    assert stock.creditos(tmp_path) == ""                       # no se acredita como foto de Pexels


def test_pexels_como_escena_y_ajuste_al_presupuesto(monkeypatch):
    """Antes de generar: las escenas que solo muestran al animal usan tomas reales verificadas;
    las demás reusan imágenes cercanas hasta caber en el máximo. El texto no cambia."""
    from estudio import pipeline
    from estudio.proyecto import CarpetaProyecto

    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    c = CarpetaProyecto.crear("Peces", "animales-peligrosos", "enciclopedia_mascota", 540)
    nombres = ["Delfín rosado", "Piraña", "Anaconda", "Candirú"]
    niveles = [{"numero": k, "nombre": n, "asset": f"tira_{k}", "villano": k == 4} for k, n in enumerate(nombres, 1)]
    assets = [{"id": f"tira_{k}", "tipo": "tarjeta", "archivo": f"assets/tira/tira_{k}.png"} for k in range(1, 5)]
    escenas, i = [], 0
    for k, n in enumerate(nombres, 1):
        for j in range(12):
            i += 1
            tipo = "animal_fondo_gris" if j % 2 else "escena_cartoon_completa"
            texto = f"La {n.lower()} vive en el río y hace algo raro número {j}." if j % 2 else f"Dato suelto {i}."
            escenas.append({"id": i, "seccion": f"Nivel {k} · {n}", "narracion": texto,
                            "intencion": "explicacion" if j else "transicion_de_seccion", "intensidad": 2,
                            "visual": {"accion": "generar", "tipo": tipo, "prompt": "x"}})
    escribir = __import__("estudio.config", fromlist=["escribir_json"]).escribir_json
    escribir(c.archivo_escenas, {"version": 2, "video": "peces", "canal": "animales-peligrosos",
                                 "estilo": "enciclopedia_mascota", "assets": assets, "niveles": niveles,
                                 "escenas": escenas})
    escribir(c.ruta / "direccion.json", {"villano_revelacion": 40})

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return json.dumps({str(k): f"animal {k}" for k in range(1, 5)}), {}
        return '{"aprobados": [{"numero": 1, "razon": "sí"}, {"numero": 4, "razon": "video"}]}', {}

    monkeypatch.setattr(stock.requests, "get", SesionFalsa().get)
    monkeypatch.setattr(pipeline, "_cuadro_de_video", lambda raiz, archivo: archivo.replace(".mp4", ".jpg"))
    antes = pipeline.estimar_imagenes(c)["faltan"]
    r = pipeline.ajustar_al_presupuesto(c, ejecutar_claude=claude)
    esc = c.cargar_escenas()
    assert r["pexels"] > 0 and r["faltan"] < antes
    assert [e.narracion for e in esc.escenas] == [e["narracion"] for e in escenas]          # el texto no cambia
    reales = [e for e in esc.escenas if isinstance(e.visual.reusar_de, str) and e.visual.reusar_de.startswith("pexels_")]
    # el villano (nivel 4) no aparece real antes de su revelación (escena 40)
    assert all(not e.seccion.startswith("Nivel 4") or e.id > 40 for e in reales)
    ids = sorted(e.id for e in reales)
    assert all(b - a >= 2 for a, b in zip(ids, ids[1:]))                                      # nunca seguidas


def test_dar_dos_veces_a_pexels_no_repite_de_mas(monkeypatch):
    """La segunda vez cuenta lo que ya puso la primera: cada toma sale como mucho 2 veces en todo el
    video y nunca en escenas seguidas."""
    from collections import Counter

    from estudio import pipeline

    test_pexels_como_escena_y_ajuste_al_presupuesto(monkeypatch)
    from estudio.proyecto import CarpetaProyecto
    from estudio.config import ruta_proyectos

    c = CarpetaProyecto(next(p for p in ruta_proyectos().iterdir() if p.is_dir()))

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return json.dumps({str(k): f"animal {k}" for k in range(1, 5)}), {}
        return '{"aprobados": [{"numero": 1, "razon": "sí"}, {"numero": 4, "razon": "video"}]}', {}

    pipeline.usar_pexels_en_escenas(c, ejecutar_claude=claude)
    esc = c.cargar_escenas()
    reales = [e for e in esc.escenas if isinstance(e.visual.reusar_de, str) and e.visual.reusar_de.startswith("pexels_")]
    assert max(Counter(e.visual.reusar_de for e in reales).values()) <= pipeline.USOS_POR_TOMA
    pos = sorted(k for k, e in enumerate(esc.escenas) if e in reales)
    assert all(b - a >= 2 for a, b in zip(pos, pos[1:]))
