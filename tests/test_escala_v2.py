"""(23-10) Escala de peligro v2 para Peligro Tropical: guion más narrativo (sin «probabilidad»), 3 llamados a comentar,
voz a 1,4 con pausas más cortas y edición más movida. Solo en videos NUEVOS: los de antes siguen igual."""
from estudio import guionista, llamados as L, pipeline
from estudio.config import leer_json
from estudio.estilos import cargar_estilo, perfil_del_proyecto
from estudio.voz import pausa_despues, voz_de_la_formula


def test_la_formula_nueva_pide_3_llamados_y_no_habla_de_probabilidad():
    f = guionista.cargar_formula("escala_peligro_v2")
    assert guionista.tipos_llamados(f) == ("apuesta", "experiencia", "cierre")
    texto = L.instruccion("tortugas peligrosas", guionista.tipos_llamados(f))
    assert "EXACTAMENTE estos 3 llamados" in texto and "[COMENTA:debate]" not in texto and "[COMENTA:pais]" not in texto
    assert f"máximo {L.maximo_palabras(('apuesta', 'experiencia', 'cierre'))} palabras" in texto
    assert "NO uses la fórmula «¿cuántos ataques tiene? Cero»" in f["estructura"]
    # la de siempre no cambia: 5 llamados
    v1 = guionista.cargar_formula("escala_peligro")
    assert guionista.tipos_llamados(v1) == L.TIPOS
    assert "EXACTAMENTE estos 5 llamados" in L.instruccion("x") and "máximo 85 palabras" in L.instruccion("x")


def test_problemas_de_llamados_segun_la_version():
    historia = {"niveles": [{"nombre": "Tortuga caimán", "villano": True}],
                "secciones": [("Gancho", ["[COMENTA:apuesta] ¿Almizclera, matamata o tortuga caimán?"]),
                              ("Nivel 1", ["[COMENTA:experiencia] Si tuviste una, escribe yo"]),
                              ("Cierre", ["[COMENTA:cierre] ¿Qué animal quieres en la próxima escala?"])]}
    assert L.problemas(historia, tipos=("apuesta", "experiencia", "cierre")) == []
    assert "falta el llamado «debate»" in L.problemas(historia)          # con la de siempre faltarían 2
    historia["secciones"].append(("Nivel 2", ["[COMENTA:pais] ¿Desde qué país?"]))
    assert "sobra el llamado «pais» (quítalo)" in L.problemas(historia, tipos=("apuesta", "experiencia", "cierre"))


def test_los_videos_nuevos_de_peligro_usan_la_version_2():
    from estudio.config import RAIZ

    assert leer_json(RAIZ / "catalogo/formatos/escala_peligro/formato.json")["formula"] == "escala_peligro_v2"
    c = pipeline.crear_video("Tortugas peligrosas", "", "", 8)
    p = c.cargar()
    assert p.formula == "escala_peligro_v2"
    assert voz_de_la_formula(p) == {"velocidad": 1.4, "pausas": 0.75}
    estilo = cargar_estilo(p.estilo)
    assert perfil_del_proyecto(p, estilo).interrupcion_de_patron_cada_seg == 1.8


def test_los_videos_de_antes_quedan_igual():
    c = pipeline.crear_video("Peces del Amazonas", "", "", 8)
    p = c.cargar()
    p.formula = None                      # como los videos hechos antes del 23-10
    estilo = cargar_estilo(p.estilo)
    assert voz_de_la_formula(p) == {}
    assert perfil_del_proyecto(p, estilo).interrupcion_de_patron_cada_seg == 3.5
    p.formula = "escala_peligro"          # o hechos con la versión 1 a propósito
    assert voz_de_la_formula(p) == {} and perfil_del_proyecto(p, estilo).sfx_por_minuto == 22


def test_pausas_mas_cortas_solo_con_el_factor():
    from types import SimpleNamespace as N

    a = N(seccion="Gancho", narracion="Mira esto.", pausa_despues_seg=0.0)
    b = N(seccion="Nivel 1", intencion="normal")
    assert pausa_despues(a, b) == 0.75
    assert abs(pausa_despues(a, b, 0.75) - 0.5625) < 1e-9


def test_palabra_fuerte_cifras_remates_y_palabra_clave():
    from estudio.receta_pt import palabra_fuerte

    assert palabra_fuerte("Puede pesar más de ochenta kilos.", None, "explicacion")[0] == "OCHENTA KILOS"
    assert palabra_fuerte("Lleva aquí veinticinco millones de años.", None, "explicacion")[0] == \
        "VEINTICINCO MILLONES DE AÑOS"
    assert palabra_fuerte("Cero.", None, "explicacion") == ("CERO", 0.0)
    assert palabra_fuerte("Y entonces la aspira de golpe.", "aspira", "revelacion")[0] == "ASPIRA"
    assert palabra_fuerte("Y entonces la aspira de golpe.", "aspira", "explicacion") is None   # sin fuerza: nada
    assert palabra_fuerte("Es un animal bastante tranquilo.", None, "explicacion") is None


def test_dopamina_solo_con_la_version_2(estilo):
    """Con la versión 2: cinta «sube el peligro» al pasar de animal (y «el último de la lista»); antes: nada nuevo."""
    from test_peligro_tropical_edicion import _proyecto_niveles

    from estudio.edicion import construir_edl

    c, edl = _proyecto_niveles(estilo)
    nuevos = {"palabra_golpe", "golpe", "sube_nivel"}
    assert not [x for cl in edl["pistas"]["escenas"] for x in cl["efectos"] if x["efecto"] in nuevos]
    p = c.cargar()
    p.formula = "escala_peligro_v2"
    c.guardar(p)
    edl = construir_edl(c)
    cintas = [x["texto"] for cl in edl["pistas"]["escenas"] for x in cl["efectos"] if x["efecto"] == "sube_nivel"]
    assert cintas[-1] == "EL ÚLTIMO DE LA LISTA" and len(cintas) == 3 and cintas[0] == "SUBE EL PELIGRO"
    # el subtítulo no se repite debajo de la cinta
    ventanas = [(x["en"], x["en"] + x["dur"]) for cl in edl["pistas"]["escenas"] for x in cl["efectos"]
                if x["efecto"] == "sube_nivel"]
    for s in edl["pistas"]["subtitulos"]:
        assert not any(min(s["fin"], b) - max(s["inicio"], a) > 0.3 for a, b in ventanas), s


def test_se_dibujan_la_palabra_y_la_cinta():
    from PIL import Image

    from estudio import render_receta as RR

    base = Image.new("RGB", (RR.W, RR.H), (40, 90, 60))
    a = RR.palabra_golpe(base, {"texto": "OCHENTA KILOS", "cifra": True, "giro": 3, "dur": 1.0}, 0.3)
    b = RR.sube_nivel(base, {"texto": "SUBE EL PELIGRO", "alto": False, "dur": 1.3}, 0.5)
    arriba = (RR.W // 2, int(RR.H * 0.17))                   # va arriba: nunca encima del animal
    assert a.size == base.size and a.getpixel(arriba) != base.getpixel(arriba)
    assert a.getpixel((RR.W // 2, RR.H // 2)) == base.getpixel((RR.W // 2, RR.H // 2))
    assert b.getpixel((RR.W // 2, int(RR.H * 0.80))) != base.getpixel((RR.W // 2, int(RR.H * 0.80)))


def test_escala_de_peligro_solo_si_el_tema_es_de_peligro(estilo):
    """(24-10) La escala 0-10 y la tarjeta «Nivel de amenaza» no aplican a todos los videos: con la v2 las pide Claude
    (ESCALA_PELIGRO: si/no); los videos de antes, sin esa marca, siguen como siempre."""
    import json

    from test_peligro_tropical_edicion import _proyecto_niveles

    from estudio.edicion import construir_edl

    texto = ("TITULO: Los animales más raros\nESCALA_PELIGRO: no\n"
             + "".join(f"NIVEL: {i} | Bicho {i} | a bug | {'si' if i == 4 else 'no'}\n" for i in range(1, 5))
             + "SECCION: Gancho\nHola.\nSECCION: Nivel 1 · Bicho 1\nUno.\nSECCION: Cierre\nAdiós.\n")
    assert guionista.leer_historia(texto)["escala_peligro"] is False
    assert "escala_peligro" not in guionista.leer_historia(texto.replace("ESCALA_PELIGRO: no\n", ""))
    assert "ESCALA_PELIGRO" in guionista.instruccion(guionista.Encargo(tema="x"), estilo,
                                                     formula=guionista.cargar_formula("escala_peligro_v2"))
    assert "ESCALA_PELIGRO" not in guionista.instruccion(guionista.Encargo(tema="x"), estilo,
                                                         formula=guionista.cargar_formula("escala_peligro"))

    def efectos(edl):
        return {x["efecto"] for cl in edl["pistas"]["escenas"] for x in cl["efectos"]}

    c, edl = _proyecto_niveles(estilo)
    p = c.cargar()
    p.formula = "escala_peligro_v2"
    c.guardar(p)
    assert "escala_peligro" in efectos(construir_edl(c))              # sin marca: como siempre
    (c.ruta / "direccion.json").write_text(json.dumps({"terminos": {"3": "cantaridina"}, "escala_peligro": False}),
                                           "utf-8")
    sin = efectos(construir_edl(c))
    assert "escala_peligro" not in sin and "veredicto" not in sin and "sube_nivel" in sin


def test_flechas_que_rodean_la_imagen_de_vez_en_cuando():
    """(24-10) De vez en cuando varias flechas rojas rodean la imagen (máx. una vez cada 15 s) y se dibujan."""
    import random
    from types import SimpleNamespace as N

    from PIL import Image

    from estudio import receta_pt, render

    clips = [{"id": f"c{i}", "inicio": i * 3.0, "fin": i * 3.0 + 2.8, "modo": "recuadro", "efectos": []}
             for i in range(20)]
    escenas = [N(narracion="Mira cómo se mueve.", palabra_clave=None, intencion="amenaza",
                 tiempo=N(real_inicio=c["inicio"], real_fin=c["fin"])) for c in clips]
    sfx = []
    receta_pt.aplicar_dopamina(clips, escenas, sfx, lambda l, t, en, i, r, **k: l.append((t, en)), [1] * 20, 4,
                               random.Random(1))
    tiempos = [c["inicio"] for c in clips for x in c["efectos"] if x["efecto"] == "flechas_alrededor"]
    assert len(tiempos) >= 3 and all(b - a >= receta_pt.CADA_FLECHAS_S for a, b in zip(tiempos, tiempos[1:]))
    ef = next(x for c in clips for x in c["efectos"] if x["efecto"] == "flechas_alrededor")
    base = Image.new("RGB", (render.W, render.H), (90, 100, 140))
    img = render._flechas_alrededor(base, ef, (0, 0, render.W, render.H), ef["en"] + 1.0)
    rojos = sum(1 for p in img.resize((192, 108)).getdata() if p[0] > 180 and p[1] < 80)
    assert rojos > 20


def test_imagenes_creativas_y_casi_sin_primera_persona(estilo):
    """(24-10) Con la v2: el personaje en situación (investigación → computador), encuadres variados y la vista en
    primera persona casi nunca. La versión de siempre no cambia."""
    historia = {"titulo": "x", "niveles": [{"numero": i, "nombre": f"B{i}", "villano": i == 4} for i in range(1, 5)],
                "secciones": [("Nivel 1 · B1", ["Según los científicos, muerde fuerte."])]}
    antes = guionista.instruccion_detalles(historia, 0, estilo)
    assert "muéstrala en primera persona" in antes and "computador" not in antes
    historia["_imagenes"] = guionista.cargar_formula("escala_peligro_v2")["imagenes"]
    nueva = guionista.instruccion_detalles(historia, 0, estilo)
    assert "computador" in nueva and "NO uses la vista" in nueva and "como mucho UNA vez" in nueva
    assert "muéstrala en primera persona" not in nueva


def test_una_foto_realista_por_animal_con_etiqueta(estilo):
    """(24-10) Con la v2, una foto que parece real (IA) por animal, nunca más; en la versión de siempre, ninguna."""
    historia = {"titulo": "x", "niveles": [{"numero": i, "nombre": f"B{i}", "villano": i == 4} for i in range(1, 5)],
                "secciones": [("Gancho", ["Hola."]), ("Nivel 1 · B1", ["Uno.", "Dos.", "Tres."])]}
    assert "No uses foto_realista" in guionista.instruccion_detalles(historia, 1, estilo)
    historia["_imagenes"] = {"variedad": True}
    assert "EXACTAMENTE UNA escena" in guionista.instruccion_detalles(historia, 1, estilo)
    assert "No uses foto_realista" in guionista.instruccion_detalles(historia, 0, estilo)       # gancho: ninguna
    tres = [{"tipo": "foto_realista"} for _ in range(3)]
    quedan = [e["tipo"] for e in guionista._fotos_realistas_justas(tres, historia, estilo, 1)]
    assert quedan == ["foto_realista", "amenaza_cinematografica", "amenaza_cinematografica"]
    historia.pop("_imagenes")
    assert all(e["tipo"] != "foto_realista"
               for e in guionista._fotos_realistas_justas([{"tipo": "foto_realista"}], historia, estilo, 1))


def test_etiqueta_imagen_ilustrativa_y_aviso_de_contenido_sintetico(estilo):
    from PIL import Image

    from test_peligro_tropical_edicion import _proyecto

    from estudio import render_receta as RR
    from estudio.edicion import construir_edl

    c, _ = _proyecto(estilo, n=4)
    esc = c.cargar_escenas()
    esc.escenas[1].visual.tipo = "foto_realista"
    c.guardar_escenas(esc)
    p = c.cargar()
    p.requiere_divulgacion_contenido_sintetico = False
    c.guardar(p)
    edl = construir_edl(c)
    con = [cl["escena"] for cl in edl["pistas"]["escenas"] if any(x["efecto"] == "ilustrativa" for x in cl["efectos"])]
    assert con == [2] and c.cargar().requiere_divulgacion_contenido_sintetico is True
    base = Image.new("RGB", (RR.W, RR.H), (200, 200, 200))
    assert RR.ilustrativa(base).getpixel((60, 50)) != base.getpixel((60, 50))


def test_like_donde_la_voz_lo_pide_y_mas_avatar(estilo):
    """(24-10) Con la v2 el like sale donde la voz lo pide (pausa en el momento de más intriga) y el suscribirse justo
    después; y la fórmula pide más cortes al presentador real."""
    from test_peligro_tropical_edicion import _proyecto_niveles

    from estudio.edicion import _presentador_de_la_formula, construir_edl

    c, _ = _proyecto_niveles(estilo)
    esc = c.cargar_escenas()
    esc.escenas[6].narracion = "Pero antes, si te gusta, dale like y suscríbete."
    c.guardar_escenas(esc)
    p = c.cargar()
    p.formula = "escala_peligro_v2"
    c.guardar(p)
    edl = construir_edl(c)
    clips = edl["pistas"]["escenas"]
    like = [cl["escena"] for cl in clips if any(x["efecto"] == "cta_like" for x in cl["efectos"])]
    sus = [cl["escena"] for cl in clips if any(x["efecto"] == "cta_suscribir" for x in cl["efectos"])]
    assert like == [7] and sus and sus[0] > 7
    assert "momento de más intriga" in guionista.cargar_formula("escala_peligro_v2")["estructura"]
    pr = _presentador_de_la_formula(estilo, p).presentador
    assert pr.maximo_por_video == 14 and pr.separacion_minima_seg == 22
    p.formula = None
    assert _presentador_de_la_formula(estilo, p).presentador.maximo_por_video == estilo.presentador.maximo_por_video


def test_tecnicas_nuevas_se_dibujan():
    """(24-10) Mano que señala, halo de luz, detalle borroso con «?», círculos de zoom y mapa antiguo con nubes."""
    import random

    from PIL import Image

    from estudio import render_tecnicas as T

    base = Image.new("RGB", (T.W, T.H), (90, 140, 90))
    ubic, caja = (0, 0, T.W, T.H), [0.45, 0.3, 0.55, 0.45]
    centro = (T.W // 2, int(T.H * 0.375))
    for funcion, ef in ((T.mano, {"en": 0, "caja": caja, "desde": "izquierda"}),
                        (T.halo, {"en": 0, "caja": caja}),
                        (T.borroso, {"en": 0, "dur": 2, "caja": caja}),
                        (T.circulos, {"en": 0, "puntos": T.puntos_circulos(random.Random(1))})):
        img = funcion(base, ef, ubic, 1.0)
        assert img.size == base.size and img.tobytes() != base.tobytes(), funcion.__name__
    assert T.halo(base, {"en": 0, "caja": caja}, ubic, 1.0).getpixel(centro) > base.getpixel(centro)
    mapa = T.mapa_antiguo({"texto": "Hace cien millones de años", "dur": 2.5, "semilla": 2}, 1.5)
    assert mapa.size == (T.W, T.H)


def test_tecnicas_nuevas_en_la_edicion_v2(estilo):
    """Con la v2 el detalle se señala de formas que se turnan, el pasado sale en el mapa antiguo y las preguntas
    llevan círculos de zoom (sin repetir los «?» de siempre en el mismo corte). La versión de siempre no cambia."""
    import json

    from test_peligro_tropical_edicion import _proyecto

    from estudio.edicion import construir_edl

    c, _ = _proyecto(estilo, n=16)
    esc = c.cargar_escenas()
    esc.escenas[3].narracion = "Lleva aquí veinticinco millones de años."
    c.guardar_escenas(esc)
    d = json.loads((c.ruta / "direccion.json").read_text("utf-8"))
    d["historias"] = {"4": "veinticinco millones de años"}
    (c.ruta / "direccion.json").write_text(json.dumps(d), "utf-8")

    def efectos(edl):
        return [x["efecto"] for cl in edl["pistas"]["escenas"] for x in cl["efectos"]]

    antes = efectos(construir_edl(c))
    assert not {"mano", "halo", "borroso", "mapa_antiguo", "circulos_misterio"} & set(antes)
    p = c.cargar()
    p.formula = "escala_peligro_v2"
    c.guardar(p)
    edl = construir_edl(c)
    ahora = efectos(edl)
    assert "mapa_antiguo" in ahora
    assert {"mano", "halo", "borroso"} & set(ahora)                  # se turnan con la flecha y la lupa
    for cl in edl["pistas"]["escenas"]:
        nombres = [x["efecto"] for x in cl["efectos"]]
        assert not ("circulos_misterio" in nombres and "signos_pregunta" in nombres)


def test_frase_historia_del_guion_va_a_la_direccion(estilo):
    datos = {"titulo": "x", "niveles": [], "catalogo": [],
             "escenas": [{"seccion": "Gancho", "narracion": "Hace cien millones de años vivía aquí.",
                          "intencion": "explicacion", "intensidad": 2, "accion": "generar",
                          "tipo": "escena_cartoon_completa", "descripcion": "a forest", "con_mascota": False,
                          "frase_historia": "Hace cien millones de años"}]}
    _, direccion, _ = guionista.a_escenas(datos, estilo, "animales-peligrosos")
    assert direccion["historias"] == {"1": "Hace cien millones de años"}
    historia = {"titulo": "x", "niveles": [{"numero": i, "nombre": f"B{i}", "villano": i == 4} for i in range(1, 5)],
                "secciones": [("Nivel 1 · B1", ["Uno."])], "_imagenes": {"variedad": True}}
    texto = guionista.instruccion_detalles(historia, 0, estilo)
    assert "frase_historia" in texto and "nube de pensamiento" in texto
