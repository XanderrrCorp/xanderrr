import copy

import pytest
from PIL import Image
from pydantic import ValidationError

from estudio.esquemas import EscenasV2
from estudio.tira import armar_tira, clip_tira, pixelar, quitar_fondo_liso


def _doc(n=4, villanos=(4,)):
    assets = [{"id": f"tira_{i}", "tipo": "animal", "archivo": f"assets/tira_{i}.png"} for i in range(1, n + 1)]
    return {"video": "v", "canal": "c", "assets": assets,
            "niveles": [{"numero": i, "nombre": f"Bicho {i}", "asset": f"tira_{i}", "villano": i in villanos}
                        for i in range(1, n + 1)],
            "escenas": [{"id": 1, "seccion": "s", "narracion": "hola", "intencion": "gancho", "intensidad": 3,
                         "visual": {"accion": "solo_edicion"}}]}


def test_niveles_validos():
    EscenasV2.model_validate(_doc())


@pytest.mark.parametrize("cambio", [
    dict(n=3, villanos=(3,)),         # menos de 4
    dict(n=9, villanos=(9,)),         # más de 8
    dict(n=4, villanos=()),           # sin villano
    dict(n=4, villanos=(3, 4)),       # dos villanos
])
def test_niveles_invalidos(cambio):
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(_doc(**cambio))


def _sujetos(carpeta, n):
    (carpeta / "assets").mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        im = Image.new("RGB", (400, 240), (128, 128, 128))
        for x in range(150, 250):
            for y in range(80, 160):
                im.putpixel((x, y), (40 * i % 255, 30, 20))
        im.save(carpeta / "assets" / f"tira_{i}.png")


def test_quitar_fondo_gris():
    im = Image.new("RGB", (100, 60), (128, 128, 128))
    for x in range(40, 60):
        for y in range(20, 40):
            im.putpixel((x, y), (200, 30, 30))
    rgba = quitar_fondo_liso(im)
    assert rgba.getpixel((2, 2))[3] == 0 and rgba.getpixel((50, 30))[3] == 255


def test_armar_tira_y_regla_del_villano(tmp_path, estilo):
    esc = EscenasV2.model_validate(_doc())
    _sujetos(tmp_path, 4)
    armada = armar_tira(esc, estilo, tmp_path)
    t = estilo.tira_niveles
    salida = tmp_path / "assets" / "tira"
    for f in ["tira_niveles.png", "tira_niveles_pixelada.png", "vista_tira.png"] + \
             [f"tarjeta_{i}{s}.png" for i in range(1, 5) for s in ("", "_pixelada")]:
        assert (salida / f).exists(), f
    assert armada.normal.size == (4 * t.tarjeta_ancho + 5 * t.separacion, t.alto_lienzo)
    # la tarjeta del villano está pixelada en la versión pixelada y no en la normal
    x0, y0, x1, y1 = armada.caja_villano
    g = t.borde_grosor
    zona_n = armada.normal.crop((x0 + g, y0 + g, x1 - g, y1 - g))
    zona_p = armada.pixelada.crop((x0 + g, y0 + g, x1 - g, y1 - g))
    assert zona_n.tobytes() != zona_p.tobytes()
    assert pixelar(zona_n, t.pixel_bloque).tobytes() != zona_n.tobytes()
    # las otras tarjetas son idénticas en las dos versiones
    xa = armada.centros_x[0] - t.tarjeta_ancho // 2
    caja = (xa, y0, xa + t.tarjeta_ancho, y1)
    assert armada.normal.crop(caja).tobytes() == armada.pixelada.crop(caja).tobytes()


def test_clip_de_prueba(tmp_path, estilo):
    imageio_ffmpeg = pytest.importorskip("imageio_ffmpeg")
    esc = EscenasV2.model_validate(_doc())
    _sujetos(tmp_path, 4)
    armada = armar_tira(esc, estilo, tmp_path)
    destino = clip_tira(armada, tmp_path / "clip.mp4", imageio_ffmpeg.get_ffmpeg_exe(), fps=10, tam=(320, 180))
    assert destino.exists() and destino.stat().st_size > 1000


def test_tarjeta_nunca_queda_vacia(tmp_path, estilo):
    """Si el recorte del fondo se come al sujeto, la tarjeta usa la imagen entera; si falta la imagen, avisa."""
    esc = EscenasV2.model_validate(_doc())
    _sujetos(tmp_path, 4)
    Image.new("RGB", (400, 240), (128, 128, 128)).save(tmp_path / "assets" / "tira_2.png")   # todo «fondo»
    armada = armar_tira(esc, estilo, tmp_path)
    t = estilo.tira_niveles
    x = armada.centros_x[1] - t.tarjeta_ancho // 2
    tarjeta = armada.normal.crop((x + 20, t.y_tarjeta + 20, x + t.tarjeta_ancho - 20, t.y_tarjeta + t.tarjeta_alto - 20))
    assert tarjeta.getbbox() is not None                                  # no es un hueco
    (tmp_path / "assets" / "tira_3.png").unlink()
    import shutil

    shutil.rmtree(tmp_path / "assets" / "sin_fondo")
    with pytest.raises(ValueError, match="Bicho 3"):
        armar_tira(esc, estilo, tmp_path)
