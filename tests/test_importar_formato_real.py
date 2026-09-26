"""Formato real de v1 (el del proyecto de alacranes), con datos inventados."""
from estudio.imagenes import prompts
from estudio.importar_v1 import convertir


def _v1(estilo):
    t = estilo.tipo("mascota_fondo_gris").plantilla_prompt
    completo = prompts.armar(t, estilo, estilo.personaje_por_defecto, "Waving hello, happy face")
    return {
        "video": "Prueba", "idioma": "es",
        "assets": [
            {"id": "mascota_base", "archivo_salida": "assets/mascota_base.png", "quitar_fondo": True,
             "prompt": "2D cartoon character, mascot. no text."},
            {"id": "tira_1", "nombre": "Nivel 1", "archivo_salida": "assets/tira_1.png", "quitar_fondo": True,
             "prompt": "A scorpion. no text."},
        ],
        "escenas": [
            {"id": 1, "seccion": "Gancho", "inicio_seg": 0.0, "duracion_seg": 3.0, "narracion": "Hola.",
             "accion": "generar", "tipo": "mascota_fondo_gris", "prompt": completo,
             "archivo_salida": "imagenes/escena_001.png", "quitar_fondo": True,
             "imagen_referencia": ["assets/mascota_base.png"], "notas_edicion": ""},
            {"id": 2, "seccion": "Gancho", "inicio_seg": 3.0, "duracion_seg": 2.0, "narracion": "Otra vez.",
             "accion": "reusar", "reusar_imagen": "imagenes/escena_001.png", "notas_edicion": "zoom a la cara"},
            {"id": 3, "seccion": "Gancho", "inicio_seg": 5.0, "duracion_seg": 2.0, "narracion": "El primero.",
             "accion": "reusar", "reusar_imagen": "assets/tira_1.png", "notas_edicion": ""},
            {"id": 4, "seccion": "Gancho", "inicio_seg": 7.0, "duracion_seg": 2.5, "narracion": "Vamos nivel por nivel,",
             "accion": "solo_edicion", "notas_edicion": "tira deslizándose"},
            {"id": 5, "seccion": "Nivel 1", "inicio_seg": 9.5, "duracion_seg": 3.0, "narracion": "Un prompt raro.",
             "accion": "generar", "tipo": "diagrama_fondo_blanco", "prompt": "Algo que no encaja. no text.",
             "archivo_salida": "imagenes/escena_005.png", "quitar_fondo": True, "imagen_referencia": []},
        ],
    }


def test_formato_real(estilo):
    res = convertir(_v1(estilo), estilo)
    assert res.errores == []
    esc = {e.id: e for e in res.escenas.escenas}
    # referencia por ruta -> id de asset
    assert esc[1].visual.referencias == ["mascota_base"]
    # prompt que encaja en la plantilla: se guarda la descripción y sale idéntico
    assert esc[1].visual.prompt == "Waving hello, happy face" and not esc[1].visual.prompt_literal
    original = _v1(estilo)["escenas"][0]["prompt"]
    assert prompts.prompt_de_escena(esc[1], estilo, estilo.personaje_por_defecto) == original
    # reuso por ruta -> id de escena o de asset
    assert esc[2].visual.reusar_de == 1 and esc[3].visual.reusar_de == "tira_1"
    assert esc[2].notas_edicion == "zoom a la cara"
    assert esc[4].visual.accion == "solo_edicion" and esc[4].visual.tipo is None
    # prompt que no encaja: se envía tal cual, y se avisa
    assert esc[5].visual.prompt_literal
    assert prompts.prompt_de_escena(esc[5], estilo, "x") == "Algo que no encaja. no text."
    assert any("escena 5" in a for a in res.avisos)
    # assets: el de la mascota es el personaje; prompts completos, tal cual
    tipos = {a.id: (a.tipo, a.prompt_literal) for a in res.escenas.assets}
    assert tipos == {"mascota_base": ("personaje", True), "tira_1": ("animal", True)}
    assert res.escenas.escenas[0].tiempo.estimado_duracion == 3.0
