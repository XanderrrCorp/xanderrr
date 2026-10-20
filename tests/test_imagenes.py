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
    m = json.loads((proyecto.ruta / "imagenes" / "manifiesto.json").read_text(encoding="utf-8"))
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
    prov = ProveedorSimulado(config, fallar_cada=2)     # el primer intento de cada imagen falla
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


def test_limite_de_google_espera_y_sigue_sin_gastar_reintentos(proyecto, config, monkeypatch):
    esperas = []
    ahora = [0.0]

    def dormir(s):                                   # reloj de mentira: dormir hace pasar el tiempo
        esperas.append(s)
        ahora[0] += s
    monkeypatch.setattr("estudio.imagenes.generador.dormir", dormir)
    monkeypatch.setattr("estudio.imagenes.generador.reloj", lambda: ahora[0])

    class Lento(ProveedorSimulado):
        veces = 0

        def generar(self, prompt, referencias):
            Lento.veces += 1
            if Lento.veces % 4:                        # tres 429 seguidos antes de cada imagen
                raise ErrorProveedor("HTTP 429: Resource has been exhausted", limite=True)
            return super().generar(prompt, referencias)
    r = generar_imagenes(proyecto, primeras=3, proveedor=Lento(config), config=config, avisar=silencio)
    assert r.fallidas == {} and r.generadas and esperas and max(esperas) <= 20
    assert r.llamadas == len(r.generadas)             # las esperas no cuentan como llamadas pagadas
    assert sum(esperas) < 9 * 90                     # (20-10) ritmo parejo: mucho menos que las esperas crecientes


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
    datos = json.loads((RAIZ / "estilos/enciclopedia_mascota/estilo.json").read_text(encoding="utf-8"))
    for t in datos["tipos_de_escena"]:
        if t["id"] == e1.visual.tipo:
            t["plantilla_prompt"] = "PLANTILLA NUEVA {descripcion}. 16:9, no text."
    from estudio.esquemas import Estilo
    otro = Estilo.model_validate(datos)
    assert prompts.prompt_de_escena(e1, otro, "MASCOTA").startswith("PLANTILLA NUEVA")


def test_ningun_tipo_de_escena_escrito_en_el_codigo(estilo):
    codigo = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "estudio").rglob("*.py"))
    for tipo in estilo.ids_tipos | set(estilo.modos_de_montaje_permitidos):
        assert not re.search(rf"['\"]{tipo}['\"]", codigo), f"'{tipo}' está escrito en el código"


class _Resp:
    def __init__(self, status, datos, headers=None):
        self.status_code, self._d, self.headers = status, datos, headers or {}
        self.text = json.dumps(datos)

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


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
    precio = config.precios["imagenes_por_modelo"]["google/flash-image-2.5"]["precio_por_imagen"]   # el medido
    assert res.uso.costo_usd == pytest.approx(precio) and prov.estimar_usd("x", [ref]) == pytest.approx(precio)


def test_proveedor_por_defecto_es_google_cloud_aunque_quedara_together(config, monkeypatch):
    from estudio.config import leer_config
    from estudio.imagenes.proveedores import ProveedorVertex, crear_proveedor
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    ajustes = leer_config("proveedores.json")["imagenes"]
    monkeypatch.delenv("XANDART_PROVEEDOR_IMAGENES", raising=False)
    assert isinstance(crear_proveedor(config, ajustes), ProveedorVertex)
    monkeypatch.setenv("XANDART_PROVEEDOR_IMAGENES", "together")   # lo que quedó guardado de antes
    assert isinstance(crear_proveedor(config, ajustes), ProveedorVertex)


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


def test_arreglo_de_las_corazas_no_vuelve_a_pagar_imagenes(proyecto, config, estilo, monkeypatch, tmp_path):
    """La plantilla vieja pedía placas de exoesqueleto en todo animal. Al corregirla, las imágenes
    ya pagadas con la frase vieja se reconocen como las mismas (no se regeneran)."""
    from estudio.estilos import Estilo
    from estudio.imagenes import arreglos, generador

    viejo, nuevo = arreglos.REEMPLAZOS[0]
    assert viejo not in json.dumps(estilo.model_dump()) and nuevo in json.dumps(estilo.model_dump())
    estilo_viejo = Estilo.model_validate(json.loads(json.dumps(estilo.model_dump()).replace(nuevo, viejo)))
    prov = ProveedorSimulado(config)
    with monkeypatch.context() as m:
        m.setattr(generador, "cargar_estilo", lambda _id: estilo_viejo)
        r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.generadas and prov.llamadas == len(r.generadas)
    antes = prov.llamadas
    r2 = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert prov.llamadas == antes and not r2.generadas                     # nada se vuelve a pagar
    man = leer_json(proyecto.ruta / "imagenes" / "manifiesto.json")
    assert not any(viejo in (v.get("prompt") or "") for v in man.values())  # quedan con el prompt nuevo

    # el estilo copiado en el espacio también se corrige (con copia del original)
    f = tmp_path / "datos" / "espacios" / ("a" * 32) / "estilos" / "enciclopedia_mascota" / "estilo.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps(estilo_viejo.model_dump()), encoding="utf-8")
    assert arreglos.corregir_estilos(tmp_path / "datos") == [f]
    assert viejo not in f.read_text(encoding="utf-8") and nuevo in f.read_text(encoding="utf-8")
    assert viejo in (f.parent / "estilo.antes_del_arreglo.json").read_text(encoding="utf-8")
    assert arreglos.corregir_estilos(tmp_path / "datos") == []                # una sola vez


def test_seguir_con_las_imagenes_que_hay(proyecto, config, monkeypatch):
    """Si falta alguna imagen y no se quiere pagar más: la escena reusa la más cercana y el video sigue."""
    from estudio import pipeline

    generar_imagenes(proyecto, proveedor=ProveedorSimulado(config), config=config, avisar=silencio)
    esc = proyecto.cargar_escenas()
    propias = [e for e in esc.escenas if e.visual.accion == "generar"]
    faltante = propias[2]
    (proyecto.ruta / faltante.visual.archivo).unlink()                 # esta no se alcanzó a hacer
    for n in ("_ubicar_focos", "_stock"):
        monkeypatch.setattr(pipeline, n, lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "armar_tira", lambda *a, **k: None, raising=False)
    import estudio.tira as tira

    monkeypatch.setattr(tira, "armar_tira", lambda *a, **k: None)
    r = pipeline.usar_las_que_hay(proyecto, pipeline.Trabajo("imagenes"))
    esc2 = proyecto.cargar_escenas()
    e = next(x for x in esc2.escenas if x.id == faltante.id)
    assert r["escenas"] == [faltante.id] and e.visual.accion == "reusar" and e.visual.reusar_de == propias[1].id
    assert e.narracion == faltante.narracion                            # el texto no cambia
    assert all(x.visual.reusar_de != faltante.id for x in esc2.escenas)  # nadie apunta a la que no tiene imagen
    assert proyecto.cargar().pasos["assets"].estado == "completo"


def test_google_cloud_agent_platform_con_clave(config, tmp_path, monkeypatch):
    """Agent Platform (antes Vertex AI): mismo cuerpo que Gemini, la clave va en la URL."""
    import base64 as b64

    from estudio.imagenes import proveedores as pv

    monkeypatch.setenv("GEMINI_API_KEY", "clave-prueba")
    pedidos = []

    class R:
        status_code = 200
        headers = {}

        def json(self):
            return {"candidates": [{"content": {"parts": [{"inlineData": {"data": b64.b64encode(b"PNG").decode()}}]}}],
                    "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 1120}}

    class S:
        def post(self, url, params=None, headers=None, data=None, timeout=None):
            pedidos.append((url, params))
            return R()

    p = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "gemini-3.1-flash-image-preview"}}})
    p.sesion = S()
    r = p.generar("un búho", [])
    assert r.png == b"PNG" and r.proveedor == "vertex"
    assert pedidos[0][0].startswith("https://aiplatform.googleapis.com/v1/publishers/google/models/gemini-3.1-flash-image-preview")
    assert pedidos[0][1] == {"key": "clave-prueba"}
    assert 0.06 < r.uso.costo_usd < 0.08                      # ~0,067 por imagen de 1K


def test_el_dueno_elige_el_proveedor_en_ajustes(config, monkeypatch):
    from estudio.imagenes import proveedores as pv

    monkeypatch.setenv("XANDART_PROVEEDOR_IMAGENES", "simulado")
    assert pv.crear_proveedor(config, {"proveedor": "together", "opciones": {}}).nombre == "simulado"


def test_escenas_se_piden_varias_a_la_vez(proyecto, config):
    import threading
    import time as _t

    class Contador(ProveedorSimulado):
        activas = maximo = 0
        cerrojo = threading.Lock()

        def generar(self, prompt, referencias):
            with Contador.cerrojo:
                Contador.activas += 1
                Contador.maximo = max(Contador.maximo, Contador.activas)
            _t.sleep(0.05)
            try:
                return super().generar(prompt, referencias)
            finally:
                with Contador.cerrojo:
                    Contador.activas -= 1
    r = generar_imagenes(proyecto, primeras=10, proveedor=Contador(config), config=config, avisar=silencio)
    assert r.fallidas == {} and Contador.maximo > 1


def test_las_que_google_dejo_esperando_tienen_otra_vuelta_al_final(proyecto, config, monkeypatch):
    esperas = []
    monkeypatch.setattr("estudio.imagenes.generador.dormir", esperas.append)
    monkeypatch.setattr("estudio.imagenes.generador.ESPERAS_LIMITE", 1)

    class Ocupado(ProveedorSimulado):
        def __init__(self, c):
            super().__init__(c)
            self.bloqueado = True

        def generar(self, prompt, referencias):
            if self.bloqueado and self.llamadas >= 1:  # la primera (el personaje) pasa; luego Google se satura
                raise ErrorProveedor("HTTP 429: Resource has been exhausted", limite=True)
            return super().generar(prompt, referencias)

    prov = Ocupado(config)
    original = esperas.append

    def dormir(s):
        original(s)
        if s == 60.0:
            prov.bloqueado = False          # tras la pausa larga Google vuelve a tener capacidad
    monkeypatch.setattr("estudio.imagenes.generador.dormir", dormir)
    r = generar_imagenes(proyecto, primeras=3, proveedor=prov, config=config, avisar=silencio)
    assert r.fallidas == {} and r.generadas and 60.0 in esperas


def test_primera_persona_sin_el_personaje_y_sin_volver_a_pagar(proyecto, config):
    """(17-10) En «pov_personaje» Google dibujaba al personaje dentro de la escena: ya no se manda su foto y se le
    prohíbe aparecer. Las imágenes ya pagadas con la forma de antes no se vuelven a pedir."""
    from dataclasses import replace

    from estudio.imagenes import generador as G

    esc = proyecto.cargar_escenas()
    esc.escenas[3].visual.tipo = "pov_personaje"                  # la escena 4 (antes con la mascota)
    proyecto.guardar_escenas(esc)
    prov = ProveedorSimulado(config)
    generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    m = json.loads((proyecto.ruta / "imagenes" / "manifiesto.json").read_text(encoding="utf-8"))
    assert m["escena:4"]["referencias"] == [] and "must NOT appear" in m["escena:4"]["prompt"]
    # simula una imagen pagada antes del arreglo: el manifiesto tiene la huella de la forma vieja
    estilo = cargar_estilo(proyecto.cargar().estilo)
    viejo = prompts.prompt_de_escena(proyecto.cargar_escenas().escenas[3], estilo, "PERSONAJE")
    t_viejo = G.Trabajo("escena:4", viejo, [proyecto.ruta / "assets" / "mascota_base.png"],
                        proyecto.ruta / m["escena:4"]["archivo"], False)
    nuevo = replace(t_viejo, prompt=viejo + " " + prompts.POV_SIN_PERSONAJE, referencias=[], antes=t_viejo)
    assert G._misma_de_antes(nuevo, prov.modelo, {"huella": G._huella(t_viejo, prov.modelo)})


# ------------------------------------------------------------------ (20-10) cuenta de servicio y lotes

def _cuenta(monkeypatch, tmp_path):
    """Archivo de cuenta de servicio falso (sin firmar nada: el token se simula)."""
    from estudio.imagenes import google_cloud

    monkeypatch.setattr(google_cloud, "ruta", lambda: tmp_path / "credenciales_google.json")
    google_cloud.guardar(json.dumps({"type": "service_account", "project_id": "mi-proyecto", "private_key": "x",
                                     "client_email": "xandart@mi-proyecto.iam.gserviceaccount.com"}))
    monkeypatch.setattr(google_cloud, "token", lambda: "token-falso")
    return google_cloud


def _respuesta_imagen(tokens_salida=1120):
    return {"candidates": [{"content": {"parts": [{"inlineData": {"data": _png()}}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": tokens_salida}}


def test_cuenta_de_servicio_valida_el_archivo(monkeypatch, tmp_path):
    gc = _cuenta(monkeypatch, tmp_path)
    assert gc.estado() == {"conectada": True, "proyecto": "mi-proyecto",
                           "cuenta": "xandart@mi-proyecto.iam.gserviceaccount.com"}
    for malo in ("no es json", json.dumps({"type": "authorized_user"}), json.dumps(["x"])):
        with pytest.raises(ValueError):
            gc.guardar(malo)
    assert gc.leer()["project_id"] == "mi-proyecto"           # lo malo no pisa lo que ya servía
    gc.borrar()
    assert gc.estado()["conectada"] is False


def test_con_cuenta_de_servicio_entra_como_proyecto(config, monkeypatch, tmp_path):
    """Con el archivo: URL del proyecto y token, sin la clave en la URL. Si Google lo rechaza, sigue con la clave."""
    from estudio.imagenes import proveedores as pv

    _cuenta(monkeypatch, tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY", "clave-prueba")
    pedidos, codigos = [], [200, 403, 200, 200]

    class R:
        headers = {}

        def __init__(self, codigo):
            self.status_code, self.text = codigo, "x"

        def json(self):
            return _respuesta_imagen()

    class S:
        def post(self, url, params=None, headers=None, data=None, timeout=None):
            pedidos.append((url, params, headers))
            return R(codigos.pop(0))

    p = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "gemini-3.1-flash-image-preview"}}})
    p.sesion = S()
    p.generar("un búho", [])
    url, params, cab = pedidos[0]
    assert url == ("https://aiplatform.googleapis.com/v1/projects/mi-proyecto/locations/global/publishers/google/"
                   "models/gemini-3.1-flash-image-preview:generateContent")
    assert cab["Authorization"] == "Bearer token-falso" and not params
    p.generar("un búho", [])                                  # 403 con la cuenta → la clave de siempre
    assert pedidos[2][1] == {"key": "clave-prueba"}
    p.generar("un búho", [])
    assert pedidos[3][1] == {"key": "clave-prueba"}           # ya no vuelve a intentar con la cuenta


def test_cuenta_de_servicio_sin_clave_de_api(config, monkeypatch, tmp_path):
    from estudio.imagenes import proveedores as pv

    _cuenta(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(pv, "clave_api", lambda n: None)
    p = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "gemini-3.1-flash-image-preview"}}})
    assert p.cuenta and p.clave is None


class _Google:
    """Google Cloud de mentira para los lotes: depósito, subida, trabajo y salida."""

    def __init__(self, estados=("JOB_STATE_RUNNING", "JOB_STATE_SUCCEEDED"), crear_falla=False, sin_imagen=0):
        self.estados, self.crear_falla, self.sin_imagen = list(estados), crear_falla, sin_imagen
        self.creados, self.subido, self.generate = 0, b"", 0

    def get(self, url, params=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer token-falso"
        if url.endswith("/b/xandart-lotes-mi-proyecto"):
            return _Resp(404, {})
        if "batchPredictionJobs/77" in url:
            estado = self.estados.pop(0) if len(self.estados) > 1 else self.estados[0]
            return _Resp(200, {"state": estado, "outputInfo": {"gcsOutputDirectory": "gs://xandart-lotes-mi-proyecto/s/p1"}})
        if url.endswith("/b/xandart-lotes-mi-proyecto/o"):
            assert params["prefix"] == "s/p1"
            return _Resp(200, {"items": [{"name": "s/p1/predictions.jsonl"}, {"name": "s/p1/errores.txt"}]})
        if "predictions.jsonl" in url:
            lineas = []
            for k, linea in enumerate(self.subido.decode().splitlines()):
                peticion = json.loads(linea)["request"]
                lineas.append(json.dumps({"request": peticion, "status": "",
                                          "response": {"candidates": []} if k < self.sin_imagen
                                          else _respuesta_imagen()}))
            r = _Resp(200, {})
            r.text = "\n".join(lineas)
            return r
        raise AssertionError(url)

    def post(self, url, params=None, headers=None, json=None, data=None, timeout=None):
        if url.endswith("/storage/v1/b"):
            assert json["lifecycle"]["rule"][0]["condition"]["age"] == 7     # no se acumula almacenamiento
            return _Resp(200, {})
        if "/upload/" in url:
            self.subido = data
            return _Resp(200, {})
        if url.endswith("/batchPredictionJobs"):
            self.creados += 1
            if self.crear_falla:
                return _Resp(400, {"error": "el modelo no acepta lotes"})
            assert json["model"].startswith("publishers/google/models/")
            return _Resp(200, {"name": "projects/mi-proyecto/locations/global/batchPredictionJobs/77"})
        self.generate += 1
        raise AssertionError(f"no debía generar una por una: {url}")


def _lotes_listos(monkeypatch, tmp_path, config):
    from estudio.imagenes import lotes, proveedores as pv

    _cuenta(monkeypatch, tmp_path)
    monkeypatch.setattr(lotes, "activado", lambda: True)
    monkeypatch.setattr(lotes, "dormir", lambda s: None)
    monkeypatch.setenv("GEMINI_API_KEY", "clave-prueba")
    return lotes, pv


def test_imagenes_por_lotes_mitad_de_precio_y_sin_llamadas_sueltas(proyecto, config, monkeypatch, tmp_path):
    lotes, pv = _lotes_listos(monkeypatch, tmp_path, config)
    google = _Google()
    original = lotes.hacer
    monkeypatch.setattr(lotes, "hacer", lambda *a, **k: original(*a, **{**k, "sesion": google}))
    sim = ProveedorSimulado(config)
    prov = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "simulado"}}})
    prov.generar = sim.generar                       # el personaje (asset) va de la forma normal, uno por uno
    avisos = []
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=avisos.append)
    assert r.fallidas == {} and len(r.generadas) == 6
    assert sim.llamadas == 1 and google.creados == 1          # 1 asset suelto + 5 escenas en UN lote
    assert len(google.subido.decode().splitlines()) == 5
    entradas = [e for e in proyecto.libro(config).entradas() if e["detalle"].startswith("escena:")]
    normal = sim.tarifa.costo(100, 1120)
    assert all(e["costo_usd"] == pytest.approx(normal * lotes.DESCUENTO) for e in entradas)
    assert any("por lotes" in a for a in avisos)
    assert not list((proyecto.ruta / "imagenes" / "lote").glob("*.png"))   # cada una se usó una vez


def test_lote_se_retoma_sin_mandarlo_otra_vez(proyecto, config, monkeypatch, tmp_path):
    """Si Xandart se cierra esperando, al volver sigue esperando el MISMO lote."""
    lotes, pv = _lotes_listos(monkeypatch, tmp_path, config)
    sim = ProveedorSimulado(config)
    prov = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "simulado"}}})
    prov.generar = sim.generar
    google = _Google(estados=("JOB_STATE_RUNNING",))
    original = lotes.hacer

    class Cerrado(Exception):
        pass

    def cerrar(s):
        raise Cerrado()

    monkeypatch.setattr(lotes, "dormir", cerrar)
    monkeypatch.setattr(lotes, "hacer", lambda *a, **k: original(*a, **{**k, "sesion": google}))
    with pytest.raises(Cerrado):
        generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert google.creados == 1
    google.estados = ["JOB_STATE_SUCCEEDED"]
    monkeypatch.setattr(lotes, "dormir", lambda s: None)
    avisos = []
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=avisos.append)
    assert google.creados == 1 and len(r.generadas) == 5      # el personaje ya estaba
    assert any("Sigo esperando el lote" in a for a in avisos)


def test_si_google_no_acepta_el_lote_sigue_normal(proyecto, config, monkeypatch, tmp_path):
    lotes, pv = _lotes_listos(monkeypatch, tmp_path, config)
    sim = ProveedorSimulado(config)
    prov = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "simulado"}}})
    prov.generar = sim.generar
    google = _Google(crear_falla=True)
    original = lotes.hacer
    monkeypatch.setattr(lotes, "hacer", lambda *a, **k: original(*a, **{**k, "sesion": google}))
    avisos = []
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=avisos.append)
    assert google.creados == 2                                # global y us-central1
    assert r.fallidas == {} and sim.llamadas == 6             # todo de la forma normal
    assert any("Por lotes no se pudo" in a for a in avisos)


def test_lo_que_no_llega_en_el_lote_se_hace_normal(proyecto, config, monkeypatch, tmp_path):
    lotes, pv = _lotes_listos(monkeypatch, tmp_path, config)
    sim = ProveedorSimulado(config)
    prov = pv.crear_proveedor(config, {"proveedor": "vertex", "opciones": {"vertex": {"modelo": "simulado"}}})
    prov.generar = sim.generar
    google = _Google(sin_imagen=1)
    original = lotes.hacer
    monkeypatch.setattr(lotes, "hacer", lambda *a, **k: original(*a, **{**k, "sesion": google}))
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert r.fallidas == {} and len(r.generadas) == 6
    assert sim.llamadas == 2                                  # el personaje + la que el lote no trajo


def test_lotes_apagado_no_cambia_nada(proyecto, config, monkeypatch, tmp_path):
    from estudio.imagenes import lotes

    _cuenta(monkeypatch, tmp_path)
    monkeypatch.setattr(lotes, "activado", lambda: False)
    prov = ProveedorSimulado(config)
    r = generar_imagenes(proyecto, primeras=10, proveedor=prov, config=config, avisar=silencio)
    assert prov.llamadas == 6 and not (proyecto.ruta / "imagenes" / "lote.json").exists() and len(r.generadas) == 6
