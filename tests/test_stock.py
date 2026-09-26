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
