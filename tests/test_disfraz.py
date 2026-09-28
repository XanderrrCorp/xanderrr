"""Mascota disfrazada del animal del video (opción A): una sola imagen, con proveedor simulado."""
import json

from PIL import Image

from estudio import disfraz
from estudio.config import ConfigCostos, escribir_json, leer_json
from estudio.imagenes.proveedores import ProveedorSimulado
from estudio.proyecto import CarpetaProyecto


def _video(estilo, con_disfraz=True):
    c = CarpetaProyecto.crear("Ranas venenosas", "animales-peligrosos", estilo.id, 60, slug="ranas")
    p = c.cargar()
    p.disfraz_mascota = con_disfraz
    c.guardar(p)
    (c.ruta / "assets").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 64), (200, 200, 200)).save(c.ruta / "assets" / "mascota_base.png")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    escribir_json(c.ruta / "imagenes" / "manifiesto.json", {"asset:mascota_base": {"archivo": "x"}})
    return c


def test_disfraz_una_sola_vez_y_guarda_la_original(estilo):
    c = _video(estilo)
    config = ConfigCostos.cargar()
    prov = ProveedorSimulado(config)
    pedidos = []

    def claude(pedido, **_):
        pedidos.append(pedido)
        return json.dumps({"animal": "poison dart frog"}), None

    original = (c.ruta / "assets" / "mascota_base.png").read_bytes()
    info = disfraz.preparar(c, prov, config, permiso=True, ejecutar=claude, avisar=lambda *_: None)
    assert info["animal"] == "poison dart frog" and prov.llamadas == 1
    assert (c.ruta / "assets" / "mascota_original.png").read_bytes() == original
    assert (c.ruta / "assets" / "mascota_base.png").read_bytes() != original
    assert "asset:mascota_base" not in leer_json(c.ruta / "imagenes" / "manifiesto.json")
    assert "poison dart frog hoodie" in leer_json(c.ruta / "perfil_canal.json")["personaje"]["bloqueo"]
    assert c.cargar().disfraz_tema == "poison dart frog"
    # la segunda vez no gasta ni pregunta
    assert disfraz.preparar(c, prov, config, permiso=True, ejecutar=claude, avisar=lambda *_: None)["animal"]
    assert prov.llamadas == 1 and len(pedidos) == 1


def test_sin_disfraz_no_hace_nada(estilo):
    c = _video(estilo, con_disfraz=False)
    prov = ProveedorSimulado(ConfigCostos.cargar())
    assert disfraz.preparar(c, prov, permiso=True, ejecutar=lambda *a, **k: 1 / 0) is None
    assert prov.llamadas == 0 and not (c.ruta / "assets" / "mascota_original.png").exists()
