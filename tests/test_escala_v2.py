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
