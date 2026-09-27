import json

import pytest

from estudio import claude_cli
from estudio.guionista import (Encargo, a_escenas, escribir_guion, instruccion, instruccion_detalles,
                               leer_historia, ubicar_villano)

NIVELES = [{"numero": i, "nombre": f"Bicho {i}", "sujeto": f"a bug number {i}, magnified", "villano": i == 4}
           for i in range(1, 5)]


def _datos():
    esc = [
        {"seccion": "Gancho", "narracion": "De noche algo sale de la pared.", "intencion": "gancho", "intensidad": 4,
         "accion": "generar", "tipo": "escena_mixta", "descripcion": "a bug leaving a wall crack",
         "muestra_villano": True},
        {"seccion": "Gancho", "narracion": "Hoy vamos en cuatro niveles.", "intencion": "transicion_de_seccion",
         "intensidad": 3, "accion": "componer"},
    ]
    for n in range(1, 5):
        esc.append({"seccion": f"Nivel {n} · Bicho {n}", "narracion": f"Nivel {n}. Bicho.",
                    "intencion": "transicion_de_seccion", "intensidad": 3, "accion": "reusar", "reusar": f"nivel:{n}"})
        esc.append({"seccion": f"Nivel {n} · Bicho {n}", "narracion": f"Así se ve el bicho {n} de cerca.",
                    "intencion": "revelacion" if n == 4 else "explicacion", "intensidad": 3, "accion": "generar",
                    "tipo": "diagrama_fondo_blanco", "descripcion": f"bug {n} top view",
                    "revelacion_villano": n == 4, "texto_pantalla": "OJO" if n == 2 else None, "palabra": "cerca"})
    esc.append({"seccion": "Cierre", "narracion": "Recuerda lo de la pared.", "intencion": "cierre",
                "intensidad": 3, "accion": "reusar", "reusar": "escena:De noche algo sale"})
    esc.append({"seccion": "Cierre", "narracion": "Suscríbete.", "intencion": "llamado_accion", "intensidad": 2,
                "accion": "generar", "tipo": "mascota_fondo_gris", "descripcion": "thumbs up", "con_mascota": True})
    return {"titulo": "Prueba", "niveles": NIVELES, "escenas": esc}


def _historia_texto(datos):
    lineas = [f"TITULO: {datos['titulo']}"]
    for n in datos["niveles"]:
        lineas.append(f"NIVEL: {n['numero']} | {n['nombre']} | {n['sujeto']} | {'si' if n['villano'] else 'no'}")
    seccion = None
    for e in datos["escenas"]:
        if e["seccion"] != seccion:
            seccion = e["seccion"]
            lineas.append(f"SECCION: {seccion}")
        lineas.append(e["narracion"])
    return "\n".join(lineas)


def test_instruccion_usa_tipos_del_estilo_y_duracion(estilo):
    txt = instruccion(Encargo("insectos", "la cucaracha no es peligrosa", "chinche besucona", 9), estilo)
    historia = leer_historia(_historia_texto(_datos()))
    detalles = instruccion_detalles(historia, 1, estilo)
    for t in estilo.ids_tipos:
        assert t in detalles
    assert '"reusar": "nivel:1"' in detalles
    from estudio.guionista import PALABRAS_POR_SEGUNDO

    palabras = int(9 * 60 * PALABRAS_POR_SEGUNDO)                          # ritmo real de la voz configurada
    assert "chinche besucona" in txt and str(int(palabras * 0.93)) in txt and str(int(palabras * 1.07)) in txt


def test_a_escenas(estilo):
    doc, direccion, md = a_escenas(_datos(), estilo, "canal")
    assert len(doc["niveles"]) == 4 and doc["niveles"][-1]["villano"]
    por_id = {e["id"]: e for e in doc["escenas"]}
    assert por_id[3]["visual"]["reusar_de"] == "tira_1"
    assert por_id[11]["visual"]["reusar_de"] == 1                   # vuelve a la escena del gancho
    assert por_id[12]["visual"]["referencias"] == ["mascota_base"]
    assert direccion["villano_revelacion"] == 10
    assert direccion["pixelar_pendiente"] == [1]
    assert direccion["textos"]["6"]["texto"] == "OJO"
    assert "## Gancho" in md


def test_escribir_guion_en_dos_pasos_y_reintenta(tmp_path, estilo):
    datos = _datos()
    historias = ["esto no es una historia", _historia_texto(datos)]
    llamadas = []

    def falso(prompt, **kw):
        llamadas.append(prompt)
        if "Sección «" not in prompt:                         # fase 1: la historia
            return historias.pop(0), {"usage": {"output_tokens": 10}}
        seccion = prompt.split("Sección «", 1)[1].split("»", 1)[0]
        propias = [e for e in datos["escenas"] if e["seccion"] == seccion]
        return json.dumps({"escenas": [{"n": i + 1, **{k: v for k, v in e.items() if k not in ("seccion", "narracion")}}
                                       for i, e in enumerate(propias)]}), {}

    r = escribir_guion(Encargo("x"), estilo, tmp_path, "canal", ejecutar=falso, avisar=lambda _: None)
    fase1 = [p for p in llamadas if "Sección «" not in p]
    assert r["escenas"] == 12 and len(fase1) == 2 and "CORRIGE" in fase1[1]
    assert len(llamadas) - len(fase1) == 6                   # una llamada por sección (gancho, 4 niveles, cierre)
    assert (tmp_path / "escenas.json").exists() and (tmp_path / "direccion.json").exists()


def test_tipo_inventado_se_rechaza(estilo):
    d = _datos()
    d["escenas"][0]["tipo"] = "tipo_inventado"
    with pytest.raises(ValueError):
        a_escenas(d, estilo, "c")


def test_ubicar_villano(tmp_path, estilo):
    doc, direccion, _ = a_escenas(_datos(), estilo, "c")
    (tmp_path / "escenas.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "direccion.json").write_text(json.dumps(direccion), encoding="utf-8")
    falso = lambda prompt, **kw: ('{"1": [[0.6, 0.3, 0.9, 1.2]]}', {})
    d = ubicar_villano(tmp_path, ejecutar=falso)
    assert d["pixelar"] == {"1": [[0.6, 0.3, 0.9, 1.0]]}


def test_cli_quita_variables_de_pago_y_detecta_cupo(monkeypatch):
    monkeypatch.setattr(claude_cli, "ejecutable", lambda: "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-no-debe-pasar")
    visto = {}

    class R:
        returncode = 1
        stdout = json.dumps({"result": "You've hit your usage limit. Resets at 7pm", "is_error": True})
        stderr = ""

    def lanzar(cmd, **kw):
        visto["env"] = kw["env"]
        return R()

    with pytest.raises(claude_cli.SinCupo):
        claude_cli.ejecutar("hola", lanzar=lanzar)
    assert "ANTHROPIC_API_KEY" not in visto["env"]


def test_extraer_json_con_vallas():
    assert claude_cli.extraer_json('```json\n{"a": "b}"}\n```') == {"a": "b}"}
