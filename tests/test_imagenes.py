import json
import re
from pathlib import Path

import pytest

from estudio.config import RAIZ, ConfigCostos, leer_json
from estudio.estilos import cargar_estilo
from estudio.imagenes import prompts
from estudio.imagenes.generador import generar_imagenes, proyectar, tope_llamadas
from estudio.imagenes.proveedores import ErrorProveedor, ProveedorSimulado
from estudio.importar_v1 import convertir
from estudio.proyecto import CarpetaProyecto

V1 = Path(__file__).parent / "fixtures" / "escenas_v1_sintetico.json"


@pytest.fixture
def proyecto(estilo):
    esc = convertir(leer_json(V1), estilo).escenas
    c = CarpetaProyecto.crear(esc.video, esc.canal, estilo.id, 60, slug="img")
    c.guardar_escenas(esc)
    return c


def silencio(_):
    pass


def test_genera_reusa_y_reanuda(proyecto, config):
    prov = ProveedorSimulado(config)
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.fallidas == {}
    assert "asset:mascota_base" in r.generadas          # el personaje va primero
    assert "escena:5" in r.reusadas                      # accion reusar: no se paga
    assert len(r.generadas) == 6 and prov.llamadas == 6
    libro = proyecto.libro(config)
    assert len(libro.entradas()) == 6 and libro.total_cop() > 0
    # segunda corrida: nada que pagar
    r2 = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r2.llamadas == 0 and len(r2.ya_estaban) == 6


def test_cambiar_el_prompt_regenera_solo_esa(proyecto, config):
    prov = ProveedorSimulado(config)
    generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    esc = proyecto.cargar_escenas()
    esc.escenas[1].visual.prompt = "otro detalle de la cola"
    proyecto.guardar_escenas(esc)
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.generadas == ["escena:2"]


def test_referencia_del_personaje(proyecto, config):
    generar_imagenes(proyecto, primeras=10, proveedor=ProveedorSimulado(config), config=config, avisar=silencio)
    m = json.loads((proyecto.ruta / "imagenes" / "manifiesto.json").read_text())
    assert m["escena:4"]["referencias"] == ["mascota_base.png"]   # tipo con {personaje}
    assert m["escena:1"]["referencias"] == []                     # animal solo


def test_freno_en_pesos_para_antes_de_gastar(proyecto):
    datos = dict(ConfigCostos.cargar().datos)
    datos["presupuesto_maximo_cop"] = 250           # alcanza para dos imágenes
    config = ConfigCostos(datos)
    prov = ProveedorSimulado(config)
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.frenado and "máximo" in r.frenado
    assert proyecto.libro(config).total_cop() <= 250
    assert prov.llamadas == 2
    # con permiso explícito sigue
    r2 = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, permiso=True, avisar=silencio)
    assert not r2.frenado and not r2.fallidas


def test_reintentos_registran_lo_cobrado(proyecto, config):
    prov = ProveedorSimulado(config, fallar_cada=2)     # falla una de cada dos llamadas
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.fallidas == {}
    fallidos = [x for x in proyecto.libro(config).entradas() if "fallido" in x.get("detalle", "")]
    assert fallidos, "los intentos fallidos que la API cobra también van al libro"


def test_error_no_reintentable_queda_como_fallida(proyecto, config):
    class Roto(ProveedorSimulado):
        def generar(self, prompt, referencias):
            raise ErrorProveedor("HTTP 400: prompt rechazado", reintentable=False)
    r = generar_imagenes(proyecto, primeras=3, proveedor=Roto(config), config=config, avisar=silencio)
    assert r.fallidas and not r.generadas


def test_tope_de_llamadas(proyecto, config):
    esc = proyecto.cargar_escenas()
    assert tope_llamadas(esc, config, 2) >= 6


def test_proyeccion_con_costo_medido(proyecto, config):
    generar_imagenes(proyecto, primeras=2, proveedor=ProveedorSimulado(config), config=config, avisar=silencio)
    pr = proyectar(proyecto, config)
    assert pr.imagenes_video == 6 and pr.total_cop > 0 and "SIMULADO" in pr.base


def test_prompts_salen_del_estilo(tmp_path, monkeypatch, estilo):
    """Punto 6: cambiar estilo.json cambia el prompt sin tocar código."""
    esc = convertir(leer_json(V1), estilo).escenas
    e1 = esc.escenas[0]
    # una descripción escrita por el Director visual (no un prompt importado tal cual)
    e1 = e1.model_copy(update={"visual": e1.visual.model_copy(update={"prompt_literal": False})})
    p1 = prompts.prompt_de_escena(e1, estilo, "MASCOTA")
    inicio = estilo.tipo(e1.visual.tipo).plantilla_prompt.split("{")[0]
    assert inicio and p1.startswith(inicio)
    datos = json.loads((RAIZ / "estilos/enciclopedia_mascota/estilo.json").read_text())
    for t in datos["tipos_de_escena"]:
        if t["id"] == e1.visual.tipo:
            t["plantilla_prompt"] = "PLANTILLA NUEVA {descripcion}. 16:9, no text."
    from estudio.esquemas import Estilo
    otro = Estilo.model_validate(datos)
    assert prompts.prompt_de_escena(e1, otro, "MASCOTA").startswith("PLANTILLA NUEVA")


def test_ningun_tipo_de_escena_escrito_en_el_codigo(estilo):
    codigo = "\n".join(p.read_text() for p in (RAIZ / "estudio").rglob("*.py"))
    for tipo in estilo.ids_tipos | set(estilo.modos_de_montaje_permitidos):
        assert not re.search(rf"['\"]{tipo}['\"]", codigo), f"'{tipo}' está escrito en el código"


class _Resp:
    def __init__(self, status, datos, headers=None):
        self.status_code, self._d, self.headers = status, datos, headers or {}
        self.text = json.dumps(datos)

    def json(self):
        return self._d


class _Sesion:
    def __init__(self, respuestas):
        self.respuestas, self.pedidos = list(respuestas), []

    def post(self, url, headers, data, timeout):
        self.pedidos.append((url, headers, json.loads(data)))
        return self.respuestas.pop(0)


def _png():
    import base64, io
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (1344, 768), (9, 9, 9)).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def test_gemini_peticion_y_costo_real(tmp_path, config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorGemini
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    ref = tmp_path / "ref.png"; ref.write_bytes(b"\x89PNG fake")
    ok = _Resp(200, {
        "candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": _png()}}]},
                        "finishReason": "STOP"}],
        "usageMetadata": {"promptTokenCount": 1300, "candidatesTokenCount": 1290,
                          "promptTokensDetails": [{"modality": "TEXT", "tokenCount": 268},
                                                  {"modality": "IMAGE", "tokenCount": 1032}]}})
    sesion = _Sesion([ok])
    prov = ProveedorGemini(config, "gemini-2.5-flash-image", sesion=sesion)
    res = prov.generar("un alacrán. 16:9, no text.", [ref])
    url, cab, cuerpo = sesion.pedidos[0]
    assert url.endswith("/models/gemini-2.5-flash-image:generateContent")
    assert cab["x-goog-api-key"] == "clave-de-prueba"
    partes = cuerpo["contents"][0]["parts"]
    assert "inline_data" in partes[0] and partes[-1]["text"].startswith("un alacrán")
    assert cuerpo["generationConfig"]["responseModalities"] == ["IMAGE"]
    assert cuerpo["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9"
    # 1300 * 0,30/M + 1290 * 30/M
    assert res.uso.costo_usd == pytest.approx(1300 * 0.30e-6 + 1290 * 30e-6)
    assert res.uso.tokens_entrada_imagen == 1032


def test_gemini_sin_imagen_es_reintentable_y_trae_lo_cobrado(config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorGemini
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    vacio = _Resp(200, {"candidates": [{"content": {"parts": [{"text": "no puedo"}]}, "finishReason": "OTHER"}],
                        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 5}})
    prov = ProveedorGemini(config, "gemini-2.5-flash-image", sesion=_Sesion([vacio]))
    with pytest.raises(ErrorProveedor) as ex:
        prov.generar("x. no text.", [])
    assert ex.value.reintentable and ex.value.uso.costo_usd > 0


def test_gemini_sin_clave(config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorGemini
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("estudio.imagenes.proveedores.clave_api", lambda n: None)
    with pytest.raises(ErrorProveedor):
        ProveedorGemini(config, "gemini-2.5-flash-image", sesion=object())


def test_together_peticion_y_costo(tmp_path, config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorTogether
    monkeypatch.setenv("TOGETHER_API_KEY", "clave-de-prueba")
    ref = tmp_path / "mascota.png"; ref.write_bytes(b"\x89PNG fake")
    sesion = _Sesion([_Resp(200, {"data": [{"b64_json": _png()}]})])
    prov = ProveedorTogether(config, "google/flash-image-2.5", sesion=sesion)
    res = prov.generar("un alacrán. 16:9, no text.", [ref])
    url, cab, cuerpo = sesion.pedidos[0]
    assert url == "https://api.together.xyz/v1/images/generations"
    assert cab["Authorization"] == "Bearer clave-de-prueba"
    assert cuerpo["model"] == "google/flash-image-2.5" and cuerpo["response_format"] == "base64"
    assert cuerpo["reference_images"][0].startswith("data:image/png;base64,")
    assert res.uso.costo_usd == pytest.approx(0.0403) and prov.estimar_usd("x", [ref]) == pytest.approx(0.0403)


def test_proveedor_por_defecto_es_together(config, monkeypatch):
    from estudio.config import leer_config
    from estudio.imagenes.proveedores import ProveedorTogether, crear_proveedor
    monkeypatch.setenv("TOGETHER_API_KEY", "x")
    assert isinstance(crear_proveedor(config, leer_config("proveedores.json")["imagenes"]), ProveedorTogether)


def test_together_sin_clave_local_deja_que_el_proxy_la_ponga(config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorTogether
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    monkeypatch.setattr("estudio.imagenes.proveedores.clave_api", lambda n: None)
    sesion = _Sesion([_Resp(200, {"data": [{"b64_json": _png()}]})])
    ProveedorTogether(config, "google/flash-image-2.5", sesion=sesion).generar("x. no text.", [])
    assert "Authorization" not in sesion.pedidos[0][1]


def test_together_clave_rechazada_no_se_reintenta(config, monkeypatch):
    from estudio.imagenes.proveedores import ProveedorTogether
    monkeypatch.setenv("TOGETHER_API_KEY", "mala")
    sesion = _Sesion([_Resp(401, {"error": "invalid"})])
    with pytest.raises(ErrorProveedor) as ex:
        ProveedorTogether(config, "google/flash-image-2.5", sesion=sesion).generar("x. no text.", [])
    assert not ex.value.reintentable


def test_asset_existente_se_adopta_sin_pagar(proyecto, config):
    destino = proyecto.ruta / "assets" / "mascota_base.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image
    Image.new("RGB", (1344, 768)).save(destino)
    prov = ProveedorSimulado(config)
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert "asset:mascota_base" in r.ya_estaban and "asset:mascota_base" not in r.generadas
    assert prov.llamadas == 5
