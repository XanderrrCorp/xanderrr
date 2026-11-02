"""Plantilla de miniatura «texto_izquierda_retrato_derecha» (canal Mentalidad Imparable)."""
import io
import json

import numpy as np
import pytest
from PIL import Image, ImageDraw

from estudio.miniaturas import texto_retrato as tr

EJEMPLO = "ENFÓCATE EN / *EMPEZAR* / NO EN TENER GANAS"


@pytest.fixture
def canales(tmp_path, monkeypatch):
    monkeypatch.setenv("XANDART_CANALES", str(tmp_path / "canales"))
    return tmp_path / "canales"


def _retrato_png() -> bytes:
    """Silueta de cabeza y hombros (de prueba, no es una persona)."""
    s = Image.new("RGBA", (800, 1000), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.ellipse((260, 120, 540, 460), fill=(205, 170, 140, 255))
    d.rounded_rectangle((60, 520, 740, 1000), radius=180, fill=(30, 34, 48, 255))
    b = io.BytesIO()
    s.save(b, "PNG")
    return b.getvalue()


def test_texto_por_lineas_y_color_por_linea_completa():
    assert tr.parsear(EJEMPLO) == [("ENFÓCATE EN", False), ("EMPEZAR", True), ("NO EN TENER GANAS", False)]
    assert tr.parsear("enfócate en / *empezar*")[0] == ("ENFÓCATE EN", False)      # siempre mayúsculas
    with pytest.raises(ValueError, match="línea completa"):
        tr.parsear("ENFÓCATE EN *EMPEZAR* YA / OTRA / MÁS")
    assert tr.formatear(tr.parsear(EJEMPLO)) == EJEMPLO


def test_reglas_del_texto():
    assert tr.revisar("ENFÓCATE EN / *EMPEZAR* / NO EN GANAS", "Cómo dejar de procrastinar") == []
    p = tr.revisar(EJEMPLO, "")
    assert any("más de 3 palabras" in x for x in p)
    assert any("repite palabras del título" in x for x in tr.revisar("DEJA DE / *PROCRASTINAR* / HOY MISMO",
                                                                      "Cómo dejar de procrastinar"))
    assert any("faltan tildes" in x for x in tr.revisar("ENFOCATE EN / *EMPEZAR* / NO EN GANAS"))
    assert any("en color" in x for x in tr.revisar("ENFÓCATE EN / EMPEZAR / NO EN GANAS"))
    assert tr.corregir_tildes("VUELVETE IMPARABLE EN 30 DIAS")[0] == "VUÉLVETE IMPARABLE EN 30 DÍAS"


def test_paletas_segun_el_fondo():
    assert tr.paleta_del_fondo(tr.fondo_neuronal(1, "azul")) == "fria"
    assert tr.paleta_del_fondo(tr.fondo_neuronal(2, "morado")) == "fria"
    assert tr.paleta_del_fondo(tr.fondo_neuronal(3, "dorado")) == "calida"
    assert tr.paleta_del_fondo(Image.new("RGB", (1280, 720), (5, 5, 5))) == "calida"           # negro


def test_canal_con_fondos_que_rotan_sin_repetir(canales):
    cfg = tr.crear_canal()
    assert cfg.layout == tr.LAYOUT and cfg.acento == "#19D3C5" and cfg.acento_calido == "#FFD400"
    assert tr.es_de_texto("mentalidad-imparable")
    assert len(tr.fondos_disponibles(cfg)) == 3
    vistos = [tr.siguiente_fondo(cfg).name for _ in range(7)]
    assert all(a != b for a, b in zip(vistos, vistos[1:]))
    # crear de nuevo no pisa lo configurado
    tr.cambiar_config("mentalidad-imparable", {"rotulo": "MI CANAL", "paleta": "calida"})
    assert tr.crear_canal().rotulo == "MI CANAL"
    with pytest.raises(ValueError):
        tr.cambiar_config("mentalidad-imparable", {"acento": "rojo"})


def test_composicion_capas_y_jpg_liviano(canales, tmp_path):
    cfg = tr.crear_canal()
    with pytest.raises(ValueError, match="sin fondo"):
        tr.subir_retrato("mentalidad-imparable", (lambda b: (Image.new("RGB", (50, 50)).save(b, "PNG"), b.getvalue())[1])(io.BytesIO()))
    cfg = tr.subir_retrato("mentalidad-imparable", _retrato_png())
    fondo = tr.fondo_neuronal(1, "azul")
    _, acento = tr.color_de_acento(cfg, fondo)
    img = tr.componer(fondo, "ENFÓCATE EN / *EMPEZAR* / NO EN GANAS", cfg, tr.cargar_retrato(cfg), acento)
    assert img.size == (1280, 720)
    a = np.asarray(img)
    # el retrato llega al borde derecho y ocupa del 45 % al 50 % del ancho
    piel = np.argwhere((np.abs(a[:, :, 0].astype(int) - 205) < 6) & (np.abs(a[:, :, 1].astype(int) - 170) < 6))
    assert 1280 * 0.50 <= piel[:, 1].min() and piel[:, 1].max() <= 1280
    # hay texto en color turquesa en la zona izquierda
    turquesa = (np.abs(a[:, :720, 0].astype(int) - 0x19) < 30) & (np.abs(a[:, :720, 1].astype(int) - 0xD3) < 30) \
        & (np.abs(a[:, :720, 2].astype(int) - 0xC5) < 30)
    assert turquesa.sum() > 2000
    f = tr.guardar_jpg(img, tmp_path / "m.jpg")
    assert f.stat().st_size < 2 * 1024 * 1024


class ClaudeFalso:
    def __init__(self, respuestas):
        self.respuestas, self.pedidos = list(respuestas), []

    def __call__(self, prompt, cwd=None):
        self.pedidos.append(prompt)
        return json.dumps(self.respuestas.pop(0)), {}


def test_planificador_una_opcion_por_formula_y_tildes():
    primera = {"opciones": [
        {"formula": 1, "texto": "ENFOCATE EN / *EMPEZAR* / NO EN GANAS"},       # sin tilde: se arregla
        {"formula": 2, "texto": "VUÉLVETE / *IMPARABLE* / EN 9 MINUTOS"},
        {"formula": 3, "texto": "DE LA EXCUSA A LA ACCIÓN / *YA*"},                   # no cumple
        {"formula": 4, "texto": "OBLÍGATE A / *EMPEZAR* / HOY"}]}
    segunda = {"opciones": [{"formula": 3, "texto": "DE LA EXCUSA / *A LA ACCIÓN* / HOY"}]}
    claude = ClaudeFalso([primera, segunda])
    ops = tr.planificar("Cómo dejar de procrastinar", "9 MINUTOS", ejecutar=claude)
    assert [o["formula"] for o in ops] == [1, 2, 3, 4]
    assert ops[0]["texto"].startswith("ENFÓCATE") and ops[2]["avisos"] == []
    assert "9 MINUTOS" in claude.pedidos[0] and "fórmula 3" in claude.pedidos[1]
    assert "ENFÓCATE EN X / NO EN Y" in claude.pedidos[0] and "OBLÍGATE A X" in claude.pedidos[0]


def test_video_opciones_editar_sin_cambiar_fondo_y_api(canales):
    from fastapi.testclient import TestClient

    from estudio import app as modulo_app
    from estudio.miniaturas import servicio_texto as st
    from estudio.pipeline import Trabajo
    from estudio.proyecto import CarpetaProyecto

    tr.crear_canal()
    tr.subir_retrato("mentalidad-imparable", _retrato_png())
    c = CarpetaProyecto.crear("Cómo dejar de procrastinar", "mentalidad-imparable", "paradoja_sapiens", 540)
    claude = ClaudeFalso([{"opciones": [
        {"formula": 1, "texto": "ENFÓCATE EN / *EMPEZAR* / NO EN GANAS"},
        {"formula": 2, "texto": "VUÉLVETE / *IMPARABLE* / EN 9 MINUTOS"},
        {"formula": 3, "texto": "DE LA EXCUSA / *A LA ACCIÓN* / HOY"},
        {"formula": 4, "texto": "OBLÍGATE A / *EMPEZAR* / HOY"}]}])
    st._producir(c, Trabajo(c.ruta.name, "miniatura"), ejecutar=claude)
    e = st._estado(c)
    assert len(e["opciones"]) == 4 and all((st.carpeta(c) / o["archivo"]).exists() for o in e["opciones"])
    fondo_antes = (st.carpeta(c) / "fondo.jpg").read_bytes()
    cli = TestClient(modulo_app.app)
    slug = c.ruta.name
    r = cli.get(f"/api/videos/{slug}/miniatura")
    assert r.status_code == 200 and r.json()["layout"] == tr.LAYOUT and r.json()["tiene_retrato"]
    r = cli.put(f"/api/videos/{slug}/miniatura/texto/opciones/1", json={"texto": "vuélvete / *imparable* / en 9 minutos ya"})
    assert r.status_code == 200 and r.json()["opciones"][1]["texto"] == "VUÉLVETE / *IMPARABLE* / EN 9 MINUTOS YA"
    assert r.json()["opciones"][1]["avisos"]                                       # 4 palabras en una línea
    assert (st.carpeta(c) / "fondo.jpg").read_bytes() == fondo_antes               # el fondo no cambia
    r = cli.put(f"/api/videos/{slug}/miniatura/texto/opciones/1", json={"texto": "UNA *MAL* MARCADA"})
    assert r.status_code == 400
    r = cli.post(f"/api/videos/{slug}/miniatura/texto/elegir/2")
    assert r.status_code == 200 and r.json()["elegida"] == 2 and r.json()["miniatura"]
    r = cli.put(f"/api/videos/{slug}/miniatura/texto/paleta", json={"paleta": "calida"})
    assert r.json()["acento"] == "#FFD400"
    r = cli.get("/api/canales/mentalidad-imparable/miniatura")
    assert r.json()["layout"] == tr.LAYOUT and len(r.json()["fondos"]) == 3
    assert cli.get("/canales/mentalidad-imparable/miniatura/retrato.png").status_code == 200
    assert cli.get("/canales/mentalidad-imparable/miniatura/..%2F..%2Fsecreto.png").status_code == 404


def test_peligro_tropical_sigue_con_su_plantilla():
    from estudio.miniaturas import plantilla

    assert not tr.es_de_texto("animales-peligrosos")
    assert plantilla.cargar("animales-peligrosos").layout == "escala_2x3"


def test_al_arrancar_el_canal_se_crea_en_el_espacio_y_no_en_el_programa(tmp_path):
    import shutil

    from sqlalchemy import select

    from estudio.config import RAIZ
    from estudio.plataforma import almacen, db, local
    from estudio.plataforma.migrar import migrar_instalacion
    from estudio.plataforma.modelos import Canal

    raiz = tmp_path / "instalacion"
    shutil.copytree(RAIZ / "estilos", raiz / "estilos")
    shutil.copytree(RAIZ / "canales", raiz / "canales")
    shutil.copytree(RAIZ / "perfiles", raiz / "perfiles")
    (tmp_path / "proyectos").mkdir()
    r = migrar_instalacion(raiz, tmp_path / "proyectos")
    local._canales_nuevos(None)                                   # sin espacio: no hace nada
    local._canales_nuevos(r["espacio"])
    local._canales_nuevos(r["espacio"])                           # dos veces: no duplica
    assert not (RAIZ / "canales" / "mentalidad-imparable").exists()
    propia = almacen.raiz_espacio(r["espacio"]) / "plantillas_miniatura" / "mentalidad-imparable"
    assert json.loads((propia / "plantilla.json").read_text("utf-8"))["layout"] == tr.LAYOUT
    assert len(list((propia / "fondos").glob("*.jpg"))) == 3
    with db.sesion() as s:
        canales = s.scalars(select(Canal).where(Canal.clave == "mentalidad-imparable")).all()
        assert len(canales) == 1 and canales[0].nombre == "Mentalidad Imparable"
        assert canales[0].plantilla_miniatura_id


def test_retrato_con_fondo_blanco_se_recorta_solo(canales):
    tr.crear_canal()
    foto = Image.new("RGB", (800, 800), (255, 255, 255))
    d = ImageDraw.Draw(foto)
    d.ellipse((300, 150, 500, 400), fill=(200, 160, 130))
    d.rounded_rectangle((150, 420, 650, 800), radius=120, fill=(25, 25, 30))
    b = io.BytesIO()
    foto.save(b, "JPEG")
    cfg = tr.subir_retrato("mentalidad-imparable", b.getvalue())
    r = tr.cargar_retrato(cfg)
    assert r.mode == "RGBA" and r.getpixel((0, 0))[3] == 0                 # el blanco de la esquina se fue
    assert r.getpixel((r.width // 2, r.height - 5))[3] == 255               # el traje sigue
    ruido = Image.fromarray((np.random.default_rng(1).random((300, 300, 3)) * 255).astype("uint8"))
    b = io.BytesIO()
    ruido.save(b, "PNG")
    with pytest.raises(ValueError, match="fondo blanco liso"):
        tr.subir_retrato("mentalidad-imparable", b.getvalue())


def test_canal_tracy_con_la_plantilla_brian_tracy_y_su_presentador(tmp_path):
    import shutil

    from estudio.config import RAIZ
    from estudio.plataforma import contexto, local
    from estudio.plataforma.migrar import migrar_instalacion
    from estudio.tracy.preset import CLAVE_CANAL, crear_canal_tracy

    raiz = tmp_path / "instalacion"
    for d in ("estilos", "canales", "perfiles"):
        shutil.copytree(RAIZ / d, raiz / d)
    (tmp_path / "proyectos").mkdir()
    r = migrar_instalacion(raiz, tmp_path / "proyectos")
    foto = Image.new("RGB", (600, 600), (255, 255, 255))
    ImageDraw.Draw(foto).rounded_rectangle((100, 150, 500, 600), radius=90, fill=(20, 20, 25))
    foto.save(tmp_path / "presentador tracy.png")
    local._canales_nuevos(r["espacio"])
    with contexto.usar_espacio(r["espacio"]):
        crear_canal_tracy(presentador=str(tmp_path / "presentador tracy.png"))
        cfg = tr.cargar_config(CLAVE_CANAL)
        assert cfg.rotulo == "BRIAN TRACY" and cfg.layout == tr.LAYOUT
        retrato = tr.cargar_retrato(cfg)                     # sin retrato propio: el presentador, recortado
        assert retrato is not None and retrato.getpixel((0, 0))[3] == 0
        tr.cambiar_config(CLAVE_CANAL, {"rotulo": "OTRO"})
        local._canales_nuevos(r["espacio"])                  # al volver a arrancar no se pisa
        assert tr.cargar_config(CLAVE_CANAL).rotulo == "OTRO"


def test_el_planificador_lee_el_guion_y_el_titulo_automatico_no_bloquea_el_tema(canales):
    from estudio.miniaturas import servicio_texto as st
    from estudio.pipeline import Trabajo
    from estudio.tracy.flujo import crear_proyecto

    tr.crear_canal()
    guion = ("La disciplina es el puente entre tus metas y tus logros. " * 3
             + "Hoy vas a aprender a levantarte temprano y a cumplir tu palabra contigo mismo.")
    c = crear_proyecto(guion, canal="mentalidad-imparable")                 # sin título: sale de la 1.ª frase
    assert st.titulo_real(c) == ""
    claude = ClaudeFalso([{"opciones": [
        {"formula": 1, "texto": "ENFÓCATE EN / *DISCIPLINA* / NO EN GANAS"},
        {"formula": 2, "texto": "VUÉLVETE / *DISCIPLINADO* / EN 1 MINUTO"},
        {"formula": 3, "texto": "DE LA PEREZA / *A LA DISCIPLINA*"},
        {"formula": 4, "texto": "OBLÍGATE A / *CUMPLIR* / TU PALABRA"}]}] * 2)
    st._producir(c, Trabajo(c.ruta.name, "miniatura"), ejecutar=claude)
    assert "levantarte temprano" in claude.pedidos[0] and "GUION DEL VIDEO" in claude.pedidos[0]
    assert "No repitas las palabras principales del título" not in claude.pedidos[0]
    assert not any("repite palabras del título" in a for o in st._estado(c)["opciones"] for a in o["avisos"])


# ------------------------------------------------------------------ (02-11) Código del Éxito Mujeres

def _foto_16x9(tono: int) -> bytes:
    im = Image.new("RGB", (1280, 720), (tono, tono // 2, 30))
    ImageDraw.Draw(im).ellipse((850, 120, 1150, 600), fill=(200, 180, 160))
    b = io.BytesIO()
    im.save(b, "JPEG")
    return b.getvalue()


def _mujeres():
    return tr.crear_canal("codigo-del-exito-mujeres", "Código del Éxito Mujeres", modo_foto="foto_completa",
                          estilo_texto="limpio", blanco_negro=True, paleta="calida", acento_calido="#FFD84D")


def test_mujeres_fotos_que_rotan_sin_repetir_y_sin_fondos_de_codigo(canales):
    cfg = _mujeres()
    assert tr.fondos_disponibles(cfg) == []                 # no deja los fondos de red neuronal
    with pytest.raises(ValueError, match="fotos"):
        tr.siguiente_foto(cfg)
    cfg = tr.subir_foto(cfg.canal, _foto_16x9(200), "base.jpg")
    assert cfg.foto_base == "base.jpg"
    for k in range(3):
        tr.subir_foto(cfg.canal, _foto_16x9(60 + k * 40), f"pose{k}.jpg")
    cfg = tr.cargar_config(cfg.canal)
    assert cfg.foto_base == "base.jpg"                      # la base no cambia al subir más
    vistas = [tr.siguiente_foto(cfg).name for _ in range(9)]
    assert all(a != b for a, b in zip(vistas, vistas[1:]))
    assert set(vistas) == set(tr.fotos_disponibles(cfg))


def test_mujeres_texto_limpio_blanco_y_negro_y_sin_firma(canales):
    cfg = _mujeres()
    assert cfg.rotulo == ""
    fondo = Image.open(io.BytesIO(_foto_16x9(200)))
    img = tr.componer(fondo, "MUJER / SEMANA 1 / PRIMERO TÚ", cfg, None, cfg.acento_calido)
    a = np.asarray(img).astype(int)
    # la foto queda en blanco y negro: fuera del texto (a la derecha) no hay color
    derecha = a[:, 900:]
    assert np.abs(derecha[..., 0] - derecha[..., 2]).max() < 6
    # sin asteriscos se alternan: amarillo, blanco, amarillo (hay amarillo y hay blanco a la izquierda)
    izq = a[:, :800].reshape(-1, 3)
    amarillo = ((izq[:, 0] > 230) & (izq[:, 1] > 190) & (izq[:, 2] < 120)).sum()
    blanco = ((izq > 240).all(axis=1)).sum()
    assert amarillo > 5000 and blanco > 5000
    # la configuración de siempre no cambia
    viejo = tr.crear_canal()
    assert viejo.modo_foto == "retrato" and viejo.estilo_texto == "borde" and not viejo.blanco_negro


class _Google:
    def __init__(self):
        self.pedidos = []

    def estimar_usd(self, prompt, refs):
        return 0.04

    def generar(self, prompt, refs):
        from types import SimpleNamespace

        self.pedidos.append((prompt, [p.name for p in refs]))
        b = io.BytesIO()
        Image.new("RGB", (1024, 576), (120, 60, 30)).save(b, "PNG")
        return SimpleNamespace(png=b.getvalue(), proveedor="simulado", modelo="x",
                               uso=SimpleNamespace(costo_usd=0.04))


def test_mujeres_poses_con_la_foto_base_y_sin_repetir_lo_pagado(canales):
    cfg = _mujeres()
    with pytest.raises(ValueError, match="foto base"):
        tr.generar_poses(cfg.canal, proveedor=_Google())
    tr.subir_foto(cfg.canal, _foto_16x9(200), "base.jpg")
    g = _Google()
    nuevas = tr.generar_poses(cfg.canal, proveedor=g, avisar=lambda *_: None, cuantas=2)
    assert len(nuevas) == 2 and all(refs == ["base.jpg"] for _, refs in g.pedidos)
    assert "no text" in g.pedidos[0][0]
    foto = Image.open(tr.carpeta_fotos(cfg) / nuevas[0])
    assert foto.size == (1280, 720)
    a = np.asarray(foto.convert("RGB")).astype(int)
    assert np.abs(a[..., 0] - a[..., 2]).max() < 6           # en blanco y negro, como la base
    g2 = _Google()
    tr.generar_poses(cfg.canal, proveedor=g2, avisar=lambda *_: None)
    assert len(g2.pedidos) == len(tr.POSES_FOTO) - 2         # lo ya hecho no se vuelve a pedir
    assert tr.poses_que_faltan(tr.cargar_config(cfg.canal)) == []
