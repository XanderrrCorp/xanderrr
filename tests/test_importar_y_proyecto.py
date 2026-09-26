from pathlib import Path

from estudio.cli import main
from estudio.config import leer_json
from estudio.importar_v1 import convertir, duracion_escenas, efectos_desde_texto
from estudio.proyecto import CarpetaProyecto

V1 = Path(__file__).parent / "fixtures" / "escenas_v1_sintetico.json"


def test_efectos_texto_a_catalogo():
    efectos, sobrantes = efectos_desde_texto("corte seco, zoom golpe, sonido de golpe")
    assert [e["efecto"] for e in efectos] == ["corte_seco", "zoom_golpe", "sfx"]
    assert sobrantes == []


def test_convierte_v1(estilo):
    res = convertir(leer_json(V1), estilo)
    assert res.errores == []
    esc = res.escenas
    assert esc.version == 2 and len(esc.escenas) == 6
    por_id = {e.id: e for e in esc.escenas}
    assert por_id[1].intencion == "pregunta_al_espectador"
    assert por_id[2].intencion == "giro"
    assert por_id[3].intencion == "amenaza"
    assert por_id[4].intencion == "transicion_de_seccion"
    assert por_id[6].intencion == "cierre"
    assert por_id[5].visual.accion == "reusar"
    assert "numeros_en_digitos" in por_id[4].revision_humana
    assert 3 in res.efectos_no_reconocidos  # "brillo mágico"
    assert por_id[2].tiempo.estimado_inicio == 3.0


def test_duracion_desde_escenas(estilo):
    esc = convertir(leer_json(V1), estilo).escenas
    dur, fuente = duracion_escenas(esc)
    assert round(dur, 1) == 18.7 and "estimada" in fuente


def test_proyecto_reanudable():
    c = CarpetaProyecto.crear("Prueba", "canal", "enciclopedia_mascota", 600)
    assert c.siguiente_paso() == "estratega"
    c.marcar("estratega", "completo", ["estrategia.json"])
    c.marcar("guionista", "error", error="se cortó")
    assert CarpetaProyecto.abrir(c.ruta.name).siguiente_paso() == "guionista"
    for sub in ("assets", "imagenes/sin_fondo", "audio", "render", "logs"):
        assert (c.ruta / sub).is_dir()


def test_cli_importar_validar_estimar(capsys):
    assert main(["importar-v1", str(V1), "--slug", "alacranes"]) == 0
    assert main(["validar", "--slug", "alacranes"]) == 0
    assert main(["estimar", "--slug", "alacranes"]) == 0
    salida = capsys.readouterr().out
    assert "OK: todos los contratos son válidos" in salida
    assert "COP" in salida and "estimada (escenas.json)" in salida


def test_semilla_fija_y_proyectos_viejos():
    import json
    c = CarpetaProyecto.crear("Semilla", "canal", "enciclopedia_mascota", 600)
    s1 = c.cargar().semilla
    assert CarpetaProyecto.abrir(c.ruta.name).cargar().semilla == s1
    # proyecto creado antes del anexo: sin semilla ni paso voz_muestra
    datos = json.loads(c.archivo_proyecto.read_text(encoding="utf-8"))
    del datos["semilla"]
    del datos["pasos"]["voz_muestra"]
    c.archivo_proyecto.write_text(json.dumps(datos), encoding="utf-8")
    s2 = c.cargar().semilla
    assert c.cargar().semilla == s2  # se fijó la primera vez
    assert c.cargar().pasos["voz_muestra"].estado == "pendiente"
