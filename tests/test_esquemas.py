import copy

import pytest
from pydantic import ValidationError

from estudio.config import RAIZ, leer_json
from estudio.esquemas import EDL, Estilo, EscenasV2

ESCENA = {
    "id": 17, "seccion": "Gancho", "narracion": "Pero aquí viene el primer giro:",
    "intencion": "giro", "intensidad": 4,
    "tiempo": {"estimado_inicio": 41.2, "estimado_duracion": 2.5},
    "visual": {"accion": "generar", "tipo": "diagrama_fondo_blanco", "prompt": "...",
               "archivo": "imagenes/escena_017.png", "quitar_fondo": True},
    "efectos_sugeridos": [{"efecto": "corte_seco"}, {"efecto": "zoom_golpe", "intensidad": 0.08},
                          {"efecto": "sfx", "sonido": "golpe_grave"}],
}


def doc(**cambios):
    d = {"video": "v", "canal": "c", "escenas": [copy.deepcopy(ESCENA)]}
    d["escenas"][0].update(cambios)
    return d


def test_ejemplo_de_la_especificacion_valida(estilo):
    esc = EscenasV2.model_validate(doc())
    assert esc.errores_contra_estilo(estilo) == []


def test_intencion_fuera_de_lista():
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(intencion="drama"))


def test_efecto_fuera_de_catalogo():
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(efectos_sugeridos=[{"efecto": "explosion_3d"}]))


def test_intensidad_rango():
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(intensidad=6))


def test_tipo_que_no_es_del_estilo(estilo):
    d = doc()
    d["escenas"][0]["visual"]["tipo"] = "personaje_escena"
    assert EscenasV2.model_validate(d).errores_contra_estilo(estilo)


def test_reusar_de_inexistente():
    d = doc()
    d["escenas"][0]["visual"] = {"accion": "reusar", "tipo": "animal_fondo_gris", "reusar_de": 99}
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(d)


def test_estilo_enciclopedia_carga():
    e = Estilo.model_validate(leer_json(RAIZ / "estilos/enciclopedia_mascota/estilo.json"))
    assert e.con_personaje is True and "pov_personaje" in e.ids_tipos and len(e.tipos_de_escena) == 7


def test_estilo_rechaza_plantilla_con_texto():
    d = leer_json(RAIZ / "estilos/enciclopedia_mascota/estilo.json")
    d["tipos_de_escena"][0]["plantilla_prompt"] = "{bloque_estilo} a scorpion"
    with pytest.raises(ValidationError):
        Estilo.model_validate(d)


def test_estilo_rechaza_modo_no_permitido():
    d = leer_json(RAIZ / "estilos/enciclopedia_mascota/estilo.json")
    d["tipos_de_escena"][0]["modo_montaje"] = "pantalla_completa"
    with pytest.raises(ValidationError):
        Estilo.model_validate(d)


EDL_EJEMPLO = {
    "version": 3, "duracion_total": 1062.4,
    "pistas": {
        "fondo": [{"id": "f1", "inicio": 0, "fin": 1062.4, "tipo": "textura", "archivo": "assets/papel_arrugado.png"}],
        "escenas": [{"id": "c17", "escena": 17, "inicio": 41.2, "fin": 43.9,
                     "archivo": "imagenes/sin_fondo/escena_017.png", "modo": "recorte_sobre_papel",
                     "movimiento": {"tipo": "zoom_lento", "de": 1.0, "a": 1.04},
                     "transicion_entrada": "corte", "razon": "Giro del gancho"}],
        "elementos": [{"id": "e5", "inicio": 41.3, "fin": 43.9, "tipo": "icono", "valor": "advertencia",
                       "posicion": "arriba_izquierda"}],
        "textos": [{"id": "t2", "inicio": 41.2, "fin": 43.0, "texto": "EL PRIMER GIRO", "estilo": "titulo_contorno"}],
        "subtitulos": [{"inicio": 41.2, "fin": 43.9, "texto": "Pero aquí viene el primer giro:"}],
        "voz": [{"inicio": 0, "archivo": "audio/voz.wav"}],
        "musica": [{"id": "m2", "inicio": 38.0, "fin": 120.0, "archivo": "musica/tension_02.mp3",
                    "volumen": 0.18, "ducking": True}],
        "sfx": [{"id": "s9", "inicio": 41.2, "archivo": "sfx/golpe_grave.wav", "volumen": 0.7}],
    },
    "historial": [{"version": 2, "autor": "director_edicion", "cambio": "...", "razon": "..."}],
}


def test_edl_ejemplo_valida():
    EDL.model_validate(EDL_EJEMPLO)


def test_edl_ids_repetidos():
    d = copy.deepcopy(EDL_EJEMPLO)
    d["pistas"]["textos"][0]["id"] = "c17"
    with pytest.raises(ValidationError):
        EDL.model_validate(d)


def test_edl_tramo_invertido():
    d = copy.deepcopy(EDL_EJEMPLO)
    d["pistas"]["textos"][0]["fin"] = 40.0
    with pytest.raises(ValidationError):
        EDL.model_validate(d)


# ---- 14.1 · sensación humana

def test_palabra_clave_debe_estar_en_la_narracion():
    EscenasV2.model_validate(doc(palabra_clave="giro"))
    EscenasV2.model_validate(doc(palabra_clave="Aqui"))  # sin tilde ni mayúscula
    EscenasV2.model_validate(doc(palabra_clave="primer giro"))
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(palabra_clave="alacrán"))
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(palabra_clave="gir"))  # palabra completa, no fragmento


def test_pausa_por_defecto_y_rango():
    assert EscenasV2.model_validate(doc()).escenas[0].pausa_despues_seg == 0
    with pytest.raises(ValidationError):
        EscenasV2.model_validate(doc(pausa_despues_seg=-1))


def test_movimiento_curva_y_foco():
    d = copy.deepcopy(EDL_EJEMPLO)
    edl = EDL.model_validate(d)
    mov = edl.pistas.escenas[0].movimiento
    assert mov.curva == "ease_in_out" and mov.punto_foco is None
    assert edl.pistas.escenas[0].respiro is False
    d["pistas"]["escenas"][0]["movimiento"].update(curva="lineal")
    with pytest.raises(ValidationError):
        EDL.model_validate(d)
    d["pistas"]["escenas"][0]["movimiento"].update(curva="ease_out", punto_foco=[0.7, 1.2])
    with pytest.raises(ValidationError):
        EDL.model_validate(d)
    d["pistas"]["escenas"][0]["movimiento"]["punto_foco"] = [0.7, 0.35]
    EDL.model_validate(d)


def test_sfx_variante_y_tono():
    d = copy.deepcopy(EDL_EJEMPLO)
    d["pistas"]["sfx"][0].update(variante="golpe_grave_03", tono=1.04)
    EDL.model_validate(d)
    d["pistas"]["sfx"][0]["tono"] = 1.2
    with pytest.raises(ValidationError):
        EDL.model_validate(d)


def test_perfil_edicion_campos_nuevos(perfil):
    assert perfil.variacion_minima_duracion == 0.3
    assert perfil.respiros_max_por_minuto == 1
    assert perfil.uso_maximo_por_recurso == 0.35
    assert "corte" in perfil.recursos_exentos_de_uso_maximo
