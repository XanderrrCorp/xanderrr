"""Escala de peligro 0–10 dibujada con código (sin gastar imágenes)."""
from PIL import Image

from estudio import escala_peligro as ep
from estudio.render import _cuadro_escala


def test_valor_por_posicion_del_nivel():
    assert [ep.valor_por_posicion(n, 6) for n in range(1, 7)] == [0, 2, 4, 6, 8, 10]
    assert ep.valor_por_posicion(1, 1) == 10


def test_etiqueta_y_color_segun_el_valor():
    assert ep.etiqueta(0) == "INOFENSIVO" and ep.etiqueta(5) == "MODERADO" and ep.etiqueta(10) == "MORTAL"
    assert len(ep.COLORES) == 11


def test_la_flecha_viaja_y_el_texto_aparece_al_llegar():
    inicio, final = ep.dibujar(10, 0.0), ep.dibujar(10, 2.0)
    # abajo a la derecha (donde llega la flecha al 10) solo hay dibujo al final
    zona = (1500, 640, 1760, 820)
    assert inicio.crop(zona).getbbox() is None and final.crop(zona).getbbox() is not None
    # la palabra y el puntaje salen cuando la flecha llega
    assert inicio.crop((0, 150, 1920, 350)).getbbox() is None
    assert final.crop((0, 150, 1920, 350)).getbbox() is not None


def test_el_render_reusa_el_cuadro_quieto():
    papel = Image.new("RGB", (1920, 1080), (230, 225, 210))
    a = _cuadro_escala(papel, 7, 2.0)
    b = _cuadro_escala(papel, 7, 3.0)
    assert a.size == (1920, 1080) and a.tobytes() == b.tobytes()
    assert _cuadro_escala(papel, 7, 0.3).tobytes() != a.tobytes()        # mientras se mueve, cambia


def test_la_edicion_pone_la_escala_en_cada_nivel(estilo):
    """Cuando la tira se detiene en un nivel, sale la escala; si la tira dura poco, abre la escena siguiente."""
    from estudio.edicion import construir_edl
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Bichos", "animales-peligrosos", estilo.id, 60, slug="bichos")
    escenas, t = [], 0.0
    for i in range(1, 5):
        largo = 4.0 if i != 2 else 2.0                       # el nivel 2 pasa rápido
        escenas.append({"id": 2 * i - 1, "seccion": f"Nivel {i}", "narracion": f"Nivel {i}: el bicho {i}.",
                        "intencion": "transicion_de_seccion", "intensidad": 3,
                        "visual": {"accion": "reusar", "reusar_de": f"tira_{i}"},
                        "tiempo": {"real_inicio": t, "real_fin": t + largo - 0.3}})
        t += largo
        escenas.append({"id": 2 * i, "seccion": f"Nivel {i}", "narracion": "Mira cómo se mueve.",
                        "intencion": "explicacion", "intensidad": 2,
                        "visual": {"accion": "generar", "tipo": "animal_fondo_gris", "prompt": "a bug",
                                   "archivo": f"imagenes/escena_{2 * i:03d}.png"},
                        "tiempo": {"real_inicio": t, "real_fin": t + 2.7}})
        t += 3.0
    doc = {"video": "Bichos", "canal": "animales-peligrosos", "estilo": estilo.id,
           "assets": [{"id": f"tira_{i}", "tipo": "animal", "archivo": f"assets/tira_{i}.png"} for i in range(1, 5)],
           "niveles": [{"numero": i, "nombre": f"Bicho {i}", "asset": f"tira_{i}", "villano": i == 4,
                        **({"peligro": 3} if i == 2 else {})} for i in range(1, 5)],
           "escenas": escenas}
    c.guardar_escenas(EscenasV2.model_validate(doc))
    edl = construir_edl(c)
    escalas = {c_["escena"]: next(e for e in c_["efectos"] if e["efecto"] == "escala_peligro")
               for c_ in edl["pistas"]["escenas"] if any(e["efecto"] == "escala_peligro" for e in c_["efectos"])}
    assert escalas[1]["valor"] == 0 and escalas[5]["valor"] == 7
    assert escalas[7]["valor"] == 10 and escalas[7]["villano"] is True
    assert escalas[4]["valor"] == 3                           # nivel 2: tira corta, va en la escena siguiente
    assert 3 not in escalas
    assert escalas[1]["en"] > edl["pistas"]["escenas"][0]["inicio"]   # después de que la tira se detiene
