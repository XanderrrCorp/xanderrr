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


def test_documental_usa_pexels_por_tema(monkeypatch):
    """Sin niveles: las escenas marcadas como reales usan tomas verificadas de ese tema."""
    from estudio import pipeline
    from estudio.config import escribir_json
    from estudio.proyecto import CarpetaProyecto

    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    c = CarpetaProyecto.crear("Congo", "animales-peligrosos", "enciclopedia_mascota", 600)
    escenas = [{"id": i, "seccion": f"Parte {i // 6}", "narracion": f"Frase número {i} del documental.",
                "intencion": "explicacion", "intensidad": 2,
                "visual": {"accion": "generar", "tipo": "escena_cartoon_completa", "prompt": "x"}} for i in range(1, 25)]
    escribir_json(c.archivo_escenas, {"version": 2, "video": "congo", "canal": "animales-peligrosos",
                                      "estilo": "enciclopedia_mascota", "assets": [], "niveles": [], "escenas": escenas})
    escribir_json(c.ruta / "direccion.json", {"reales": {"3": "congo river rapids", "4": "congo river rapids",
                                                         "10": "nile crocodile", "11": "nile crocodile", "12": "nile crocodile",
                                                         "20": "hippo in river"}})

    def claude(prompt, cwd=None, herramientas=None):
        if "hippo" in prompt:
            return '{"aprobados": []}', {}                      # nada bueno: esa escena se dibuja
        return '{"aprobados": [{"numero": 1, "razon": "sí"}, {"numero": 4, "razon": "video"}]}', {}

    monkeypatch.setattr(stock.requests, "get", SesionFalsa().get)
    monkeypatch.setattr(pipeline, "_cuadro_de_video", lambda raiz, archivo: archivo.replace(".mp4", ".jpg"))
    n = pipeline.usar_pexels_en_escenas(c, ejecutar_claude=claude)
    esc = c.cargar_escenas()
    reales = {e.id: e.visual.reusar_de for e in esc.escenas if e.visual.accion == "reusar"}
    assert n == len(reales) and set(reales) <= {3, 4, 10, 11, 12} and 20 not in reales
    assert not any(a + 1 in reales for a in reales)                        # nunca dos seguidas
    indice = json.loads((c.ruta / "assets" / "stock" / "stock.json").read_text(encoding="utf-8"))
    assert set(indice["temas_revisados"]) == {"congo river rapids", "nile crocodile", "hippo in river"}
    assert all(a["tema"] for a in indice["archivos"]) and not any(a.get("sintetica") for a in indice["archivos"])


def test_fondo_del_lugar_se_baja_una_vez_y_va_en_los_creditos(tmp_path, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    (tmp_path / "direccion.json").write_text(json.dumps({"lugares": {"4": "roman colosseum"}}), "utf-8")
    s = SesionFalsa()
    assert stock.fondos_de_lugar(tmp_path, sesion=s, avisar=lambda _: None) == 1
    d = json.loads((tmp_path / "direccion.json").read_text("utf-8"))
    f = d["fondos_lugar"]["4"]
    assert (tmp_path / f["archivo"]).exists() and f["origen"].startswith("https://www.pexels.com/")
    assert stock.fondos_de_lugar(tmp_path, sesion=s, avisar=lambda _: None) == 0      # ya estaba
    assert "Foto de Ana en Pexels" in stock.creditos(tmp_path)


def _commons(*paginas):
    """Respuesta de la API de Wikimedia Commons con (pageid, licencia, ancho, mime)."""
    return Resp({"query": {"pages": {str(pid): {
        "pageid": pid, "index": k, "title": f"File:F{pid}.jpg", "imageinfo": [{
            "thumburl": f"https://upload.wikimedia.org/thumb/a/F{pid}.jpg/1920px-F{pid}.jpg",
            "url": f"https://upload.wikimedia.org/a/F{pid}.jpg", "descriptionurl": f"https://commons.wikimedia.org/wiki/File:F{pid}.jpg",
            "width": ancho, "mime": mime, "extmetadata": {
                "LicenseShortName": {"value": lic}, "Artist": {"value": f'<a href="x">Autor {pid}</a>'}}}]}
        for k, (pid, lic, ancho, mime) in enumerate(paginas)}}})


def test_wikimedia_solo_licencias_libres_y_fotos_grandes():
    """(20-10) Commons: solo dominio público, CC0, CC BY y CC BY-SA; fotos de verdad (no chiquitas ni SVG)."""
    from estudio import wikimedia

    class S:
        def get(self, url, params=None, headers=None, timeout=None):
            assert url == wikimedia.API and "Xandart" in headers["User-Agent"] and "filetype:bitmap" in params["gsrsearch"]
            return _commons((1, "CC BY-SA 4.0", 3000, "image/jpeg"), (2, "CC BY-NC 2.0", 3000, "image/jpeg"),
                            (3, "Public domain", 400, "image/jpeg"), (4, "CC0", 2000, "image/tiff"),
                            (5, "Public domain", 2000, "image/png"), (6, "Fair use", 2000, "image/jpeg"))

    fotos = wikimedia.buscar("Dendrobates tinctorius", S())
    assert [f["wikimedia_id"] for f in fotos] == [1, 5]
    assert fotos[0]["autor"] == "Autor 1" and fotos[0]["miniatura"].endswith("/330px-F1.jpg")
    assert "CC BY-SA 4.0" in fotos[0]["licencia"] and "Autor 1" in wikimedia.credito(fotos[0])

    class Caida:
        def get(self, *a, **k):
            raise ConnectionError("sin internet")

    assert wikimedia.buscar("x", Caida()) == []                          # si Commons falla, el video sigue


def test_peligro_tropical_suma_fotos_de_wikimedia(tmp_path, monkeypatch):
    """(20-10) Las fotos de Commons entran en la misma hoja; la aprobada se guarda con su licencia y su crédito."""
    from estudio import wikimedia

    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    (tmp_path / "escenas.json").write_text(json.dumps({"niveles": [{"numero": 1, "nombre": "Rana dardo azul",
                                                                     "asset": "a", "villano": False}]}), "utf-8")

    class S(SesionFalsa):
        def get(self, url, params=None, headers=None, timeout=None):
            if url == wikimedia.API:
                self.pedidos.append(url)
                return _commons((77, "CC BY 3.0", 2500, "image/jpeg"))
            return super().get(url, params, headers, timeout)

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return '{"1": "blue poison dart frog"}', {}
        assert "5 candidatos" in prompt                                  # 3 fotos + 1 video de Pexels + 1 de Commons
        return '{"aprobados": [{"numero": 5, "razon": "la rana correcta"}]}', {}

    idx = stock.preparar_stock(tmp_path, ejecutar=claude, avisar=lambda *_: None, sesion=S(), recrear_faltantes=False)
    (foto,) = idx["archivos"]
    assert foto["fuente"] == "wikimedia" and "CC BY 3.0" in foto["licencia"] and (tmp_path / foto["archivo"]).exists()
    assert "Autor 77" in stock.creditos(tmp_path) and "commons.wikimedia.org" in stock.creditos(tmp_path)


# ---------------------------------------------------------------- (27-10) más videos de Pexels en la v2

class SesionVideos(SesionFalsa):
    """Pexels con 4 videos por búsqueda (y fotos como siempre); anota lo que se pidió."""

    def __init__(self):
        super().__init__()
        self.params = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.params.append((url, params))
        if url == stock.API_VIDEOS:
            self.pedidos.append(url)
            return Resp({"videos": [{"id": 20 + i, "url": f"https://www.pexels.com/video/{20 + i}/", "duration": 8,
                                     "image": f"mv{i}", "user": {"name": "Luis", "url": "u"},
                                     "video_files": [{"file_type": "video/mp4", "width": 1920, "link": f"V{20 + i}"}]}
                                    for i in range(4)]})
        return super().get(url, params, headers, timeout)


def test_la_v2_pide_mas_videos_por_animal(tmp_path, monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    (tmp_path / "escenas.json").write_text(json.dumps({"niveles": [{"numero": 1, "nombre": "Mapaná", "asset": "a",
                                                                     "villano": False}]}), "utf-8")

    def claude(prompt, cwd=None, herramientas=None):
        if "búsqueda" in prompt:
            return '{"1": "fer-de-lance snake"}', {}
        return json.dumps({"aprobados": [{"numero": n, "razon": "sí"} for n in range(1, 8)]}), {}

    sesion = SesionVideos()
    idx = stock.preparar_stock(tmp_path, ejecutar=claude, avisar=lambda *_: None, sesion=sesion,
                               pex={"videos_por_animal": 3, "buscar_videos": 15})
    assert sum(a["tipo"] == "video" for a in idx["archivos"]) == 3
    assert any(u == stock.API_VIDEOS and p["per_page"] == 15 for u, p in sesion.params)
    # sin la fórmula nueva: 1 video, como siempre
    otra = tmp_path / "antes"
    otra.mkdir()
    (otra / "escenas.json").write_text((tmp_path / "escenas.json").read_text("utf-8"), "utf-8")
    idx = stock.preparar_stock(otra, ejecutar=claude, avisar=lambda *_: None, sesion=SesionVideos())
    assert sum(a["tipo"] == "video" for a in idx["archivos"]) == 1


def _proyecto_lugares(formula, titulo="Departamentos"):
    from estudio.config import escribir_json
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear(titulo, "animales-peligrosos", "enciclopedia_mascota", 540)
    p = c.cargar()
    p.formula = formula
    c.guardar(p)
    niveles = [{"numero": k, "nombre": n, "asset": f"tira_{k}", "villano": k == 4}
               for k, n in enumerate(["Mapaná", "Caimán", "Jaguar", "Anaconda"], 1)]
    textos = ["En las costas del Caribe, entre arena y cactus.", "Dato suelto número dos.",
              "La mapaná se esconde entre hojas secas.", "Dato suelto cuatro.", "Subimos al páramo, frío y con neblina."]
    escenas = [{"id": k, "seccion": "Nivel 1 · Mapaná", "narracion": t, "intencion": "explicacion", "intensidad": 2,
                "visual": {"accion": "generar", "tipo": "animal_fondo_gris" if k == 3 else "escena_cartoon_completa",
                           "prompt": "x"}} for k, t in enumerate(textos, 1)]
    escribir_json(c.archivo_escenas, {"version": 2, "video": "dep", "canal": "animales-peligrosos",
                                      "estilo": "enciclopedia_mascota", "niveles": niveles, "escenas": escenas,
                                      "assets": [{"id": f"tira_{k}", "tipo": "tarjeta",
                                                  "archivo": f"assets/tira/tira_{k}.png"} for k in range(1, 5)]})
    escribir_json(c.ruta / "direccion.json", {})
    return c


def test_pexels_primero_usa_videos_del_animal_y_de_los_lugares(monkeypatch):
    from types import SimpleNamespace

    from estudio import pipeline
    from estudio.config import leer_json

    monkeypatch.setenv("PEXELS_API_KEY", "clave-prueba")
    monkeypatch.setattr(stock.requests, "get", SesionVideos().get)
    monkeypatch.setattr(pipeline, "_cuadro_de_video", lambda raiz, archivo: archivo.replace(".mp4", ".jpg"))
    pedidos = []

    def claude(prompt, cwd=None, herramientas=None):
        pedidos.append(prompt)
        if "LUGAR" in prompt:
            assert "1: En las costas" in prompt
            return json.dumps({"lugares": [{"busqueda": "caribbean desert coast", "escenas": [1]},
                                           {"busqueda": "andes paramo fog", "escenas": [5, 99]}]}), {}
        if "búsqueda" in prompt:
            return '{"1": "fer-de-lance snake"}', {}
        return json.dumps({"aprobados": [{"numero": n, "razon": "se ve claro"} for n in range(1, 20)]}), {}

    t = SimpleNamespace(avisar=lambda *_: None)
    c = _proyecto_lugares("escala_peligro_v2")
    pipeline.pexels_primero(c, t, claude)
    esc = {e.id: e for e in c.cargar_escenas().escenas}
    direccion = leer_json(c.ruta / "direccion.json")
    assert direccion["lugares"] == {"1": "caribbean desert coast", "5": "andes paramo fog"}   # la 99 no existe
    assert set(direccion["video_escena"]) == {"1", "3", "5"}         # dos lugares y el animal cuando la voz lo nombra
    assert esc[2].visual.accion == esc[4].visual.accion == "generar"  # lo demás lo dibuja Google
    assert all(esc[k].narracion for k in esc)                        # el texto no cambia
    # al retomar no le vuelve a preguntar a Claude
    n = len(pedidos)
    pipeline.pexels_primero(c, t, claude)
    assert not any("LUGAR" in p for p in pedidos[n:])

    # videos de antes (sin la fórmula nueva): nada cambia
    c2 = _proyecto_lugares(None, "Departamentos antes")
    pipeline.pexels_primero(c2, t, claude)
    assert all(e.visual.accion == "generar" for e in c2.cargar_escenas().escenas)


def test_en_el_montaje_el_video_real_gana_a_la_flecha(tmp_path):
    import random
    from types import SimpleNamespace as N

    from estudio import edicion
    from estudio.config import escribir_json

    (tmp_path / "assets" / "stock").mkdir(parents=True)
    (tmp_path / "assets" / "stock" / "nivel_1_video_1.mp4").write_bytes(b"x")
    escribir_json(tmp_path / "assets" / "stock" / "stock.json", {"archivos": [
        {"archivo": "assets/stock/nivel_1_video_1.mp4", "tipo": "video", "nivel": 1, "verificado": True,
         "url_origen": "https://www.pexels.com/video/1/"}]})
    nivel = N(numero=1, nombre="Mapaná", villano=False, model_dump=lambda: {"numero": 1, "nombre": "Mapaná"})
    esc = N(niveles=[nivel])
    escenas = [N(id=1, narracion="La mapaná está quieta aquí, mírala bien de cerca.", intencion="explicacion",
                 tiempo=N(real_inicio=0.0, real_fin=3.0))]

    def clips():
        return [{"modo": "imagen", "inicio": 0.0, "fin": 3.0, "razon": "", "efectos": [{"efecto": "flecha"}]}]

    antes = clips()
    assert edicion._stock(esc, escenas, antes, tmp_path, None, random.Random(1), []) == 0   # como siempre: se salta
    ahora = clips()
    assert edicion._stock(esc, escenas, ahora, tmp_path, None, random.Random(1), [], gana=True) == 1
    assert [x["efecto"] for x in ahora[0]["efectos"]] in (["video_real"], ["foto_real"])
