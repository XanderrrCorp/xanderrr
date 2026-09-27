import json

from PIL import Image

from estudio import render
from estudio.config import escribir_json, leer_json
from estudio.short import crear_short


def _largo(tmp_path):
    raiz = tmp_path / "largo"
    raiz.mkdir()
    niveles = [{"numero": k, "nombre": n, "asset": f"tira_{k}", "villano": k == 4}
               for k, n in enumerate(["Hormiga", "Pulga", "Mosca", "Chinche besucona"], 1)]
    assets = [{"id": f"tira_{k}", "tipo": "tarjeta", "archivo": f"assets/tira/tira_{k}.png"} for k in range(1, 5)]
    assets += [{"id": "img1", "tipo": "animal", "archivo": "assets/catalogo/a.png"},
               {"id": "img2", "tipo": "animal", "archivo": "assets/catalogo/b.png"}]

    def esc(i, texto, visual, seccion="Nivel 4 · Chinche besucona"):
        return {"id": i, "seccion": seccion, "narracion": texto, "intencion": "explicacion", "intensidad": 2,
                "visual": visual}

    escenas = [esc(1, "Hola.", {"accion": "reusar", "reusar_de": "img1"}, "Gancho"),
               esc(2, "Nivel cuatro.", {"accion": "reusar", "reusar_de": "tira_4"}),
               esc(3, "Pica en la cara.", {"accion": "reusar", "reusar_de": "img1"}),
               esc(4, "No la sientes.", {"accion": "reusar", "reusar_de": 3}),
               esc(5, "Trae un parásito.", {"accion": "reusar", "reusar_de": "img2"})]
    escribir_json(raiz / "escenas.json", {"version": 2, "video": "largo", "canal": "c", "estilo": "enciclopedia_mascota",
                                          "assets": assets, "niveles": niveles, "escenas": escenas})
    escribir_json(raiz / "direccion.json", {"focos": {"4": {"tipo": "nombre", "palabra": "chinche",
                                                             "caja": [0.1, 0.1, 0.5, 0.9]}}})
    escribir_json(raiz / "proyecto.json", {"slug": "largo", "titulo": "Video largo", "canal": "c",
                                           "estilo": "enciclopedia_mascota", "duracion_objetivo_seg": 540,
                                           "creado": "2026-01-01T00:00:00+00:00"})
    (raiz / "assets" / "catalogo").mkdir(parents=True)
    return raiz


def test_short_reusa_imagenes_del_nivel_y_sin_tira(tmp_path):
    frase = "La chinche te pica dormido y no sientes nada de nada"          # 11 palabras
    pedidos = []

    def ejecutar(prompt, cwd=None, **kw):
        pedidos.append(prompt)
        filas = [{"fuente": 4 if k % 2 else 3, "narracion": frase, "intencion": "dato_impactante"} for k in range(13)]
        return json.dumps({"titulo": "te besa dormido", "titulo_youtube": "La chinche que te besa #shorts",
                           "escenas": filas}), {}

    c = crear_short(_largo(tmp_path), tmp_path / "shorts", ejecutar=ejecutar, avisar=lambda m: None)
    assert "Chinche besucona" in pedidos[0] and "Nivel cuatro" not in pedidos[0]     # sin la escena de la tira
    esc = c.cargar_escenas()
    assert esc.relacion_aspecto == "9:16" and esc.niveles == []
    assert [e.id for e in esc.escenas] == list(range(1, 14))
    # la escena 4 del largo reusaba la 3: en el short apunta directo a la imagen
    assert {e.visual.reusar_de for e in esc.escenas} == {"img1"}
    direccion = leer_json(c.ruta / "direccion.json")
    assert direccion["short"]["titulo"] == "TE BESA DORMIDO"
    assert direccion["focos"]["2"]["palabra"] == "chinche" and "1" not in direccion["focos"]
    assert c.cargar().titulo.endswith("#shorts")


def test_cuadro_vertical_1080x1920_con_titulo():
    img = Image.new("RGB", (render.W, render.H), (200, 30, 30))
    titulo = render._titulo_vertical("EL BICHO QUE TE BESA MIENTRAS DUERMES PROFUNDAMENTE")
    assert titulo.width <= render.VW - 40
    cuadro = render._cuadro_vertical(img, 0.95, titulo)
    assert cuadro.size == (render.VW, render.VH)
    assert cuadro.getpixel((540, 1000))[0] > 150              # la ventana muestra la escena


def test_dibujo_chiquito_sobre_blanco_se_agranda():
    from PIL import ImageDraw

    img = Image.new("RGB", (1344, 768), (255, 255, 255))
    ImageDraw.Draw(img).rectangle((520, 260, 820, 510), fill=(150, 20, 20))      # objeto chico en medio del blanco
    caja = render._caja_contenido(img)
    grande = render._encajar(img.crop(caja), (int(render.W * 0.84), int(render.H * 0.72)))
    assert grande.height >= render.H * 0.6          # llena el cuadro en vez de quedar como una manchita
