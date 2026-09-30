"""Modo Tracy, fase 1: números en palabras, bloques de TTS, alineación con Whisper y segmentos."""
import json

import pytest

from estudio.tracy.alineacion import emparejar, normalizar
from estudio.tracy.audio import bloques, oraciones
from estudio.tracy.numeros import a_palabras, numeros_a_palabras
from estudio.tracy.preset import completar, preset_por_defecto
from estudio.tracy.segmentos import segmentar


# ------------------------------------------------------------------ números

@pytest.mark.parametrize("n,esperado", [
    (0, "cero"), (1, "uno"), (15, "quince"), (21, "veintiuno"), (45, "cuarenta y cinco"), (100, "cien"),
    (101, "ciento uno"), (500, "quinientos"), (1000, "mil"), (1990, "mil novecientos noventa"),
    (2024, "dos mil veinticuatro"), (21000, "veintiún mil"), (1_000_000, "un millón"),
    (2_500_000, "dos millones quinientos mil"),
])
def test_enteros_en_palabras(n, esperado):
    assert a_palabras(n) == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("Tengo 5 perros y 1 casa.", "Tengo cinco perros y una casa."),
    ("el 80% de los resultados", "el ochenta por ciento de los resultados"),
    ("ganó $1.500 en 1 día", "ganó mil quinientos dólares en un día"),
    ("200 personas y 200.000 personas", "doscientas personas y doscientas mil personas"),
    ("3,5 veces", "tres coma cinco veces"),
    ("el 1.º paso y la 2ª regla", "el primer paso y la segunda regla"),
    ("de 1 a 10.", "de uno a diez."),
    ("En 2021 la gente", "En dos mil veintiuno la gente"),
    ("un archivo MP3", "un archivo MP3"),
    ("30 millones de personas", "treinta millones de personas"),
])
def test_numeros_en_el_guion(texto, esperado):
    assert numeros_a_palabras(texto) == esperado


def test_despues_de_normalizar_no_quedan_cifras():
    t = "En 1985 tenía 3 empleos, 2 hijos y $400. Hoy el 97% de mis 12 empresas crece 15,5% al año."
    assert not any(ch.isdigit() for ch in numeros_a_palabras(t))


# ------------------------------------------------------------------ bloques de TTS

def test_bloques_de_2500_terminan_en_oracion():
    guion = " ".join(f"Esta es la oración número {i} del guion, con algo de relleno para que pese." for i in range(400))
    bs = bloques(guion, 2500)
    assert len(bs) > 5
    assert all(len(b) <= 2500 for b in bs)
    assert all(b.endswith(".") for b in bs)
    assert " ".join(bs) == " ".join(guion.split())            # no se pierde ni se repite nada


def test_oracion_gigante_se_parte_sin_pasar_el_maximo():
    larga = ", ".join(["una frase que sigue y sigue"] * 200) + "."
    bs = bloques(larga, 2500)
    assert all(len(b) <= 2500 for b in bs) and len(bs) >= 2


def test_parrafos_cierran_oracion():
    assert oraciones("Hola mundo\n\nSegundo párrafo. Otra. ¿Pregunta? ¡Sí!") == \
        ["Hola mundo", "Segundo párrafo.", "Otra.", "¿Pregunta?", "¡Sí!"]


# ------------------------------------------------------------------ emparejado con Whisper

def _oido(palabras, paso=0.5):
    return [{"palabra": p, "inicio": i * paso, "fin": i * paso + 0.4} for i, p in enumerate(palabras)]


def test_emparejado_exacto():
    guion = "Hoy vamos a hablar del éxito.".split()
    tiempos, frac = emparejar(guion, _oido(["hoy", "vamos", "a", "hablar", "del", "exito"]), 3.0)
    assert frac == 1.0
    assert tiempos[5] == (2.5, 2.9)


def test_emparejado_con_errores_de_whisper():
    guion = "La disciplina es la llave que abre todas las puertas.".split()
    # Whisper oye «yave», se come «que» y mete una palabra de más
    oido = _oido(["la", "disciplina", "es", "la", "yave", "abre", "eh", "todas", "las", "puertas"])
    tiempos, frac = emparejar(guion, oido, 5.0)
    assert all(t is not None for t in tiempos)
    assert all(a <= b for a, b in tiempos)
    assert all(tiempos[i][0] >= tiempos[i - 1][0] for i in range(1, len(tiempos)))   # en orden
    assert tiempos[-1] == (4.5, 4.9)                    # «puertas» con su tiempo real
    # «llave que» (Whisper oyó solo «yave») se reparten el tramo de «yave»
    assert tiempos[4][0] == 2.0 and tiempos[5][1] == pytest.approx(2.4)
    assert 0.7 < frac < 1.0


def test_whisper_con_cifras_empareja_con_el_guion_en_palabras():
    guion = "Lo hice en mil novecientos noventa.".split()
    tiempos, frac = emparejar(guion, _oido(["Lo", "hice", "en", "1990."]), 2.0)
    assert frac == 1.0 and tiempos[0] == (0.0, 0.4)


def test_normalizar():
    assert normalizar("¡Éxito!") == "exito"


# ------------------------------------------------------------------ segmentos

def _oraciones_con(duraciones, pausa=0.4):
    salida, t = [], 0.1
    for i, d in enumerate(duraciones):
        n = max(2, int(d * 3))
        palabras = [{"p": f"p{i}_{k}" + ("," if k == n // 2 - 1 else ""), "inicio": t + k * d / n,
                     "fin": t + (k + 1) * d / n - 0.05} for k in range(n)]
        salida.append({"id": i, "texto": f"Oración {i}.", "inicio": t, "fin": t + d, "palabras": palabras})
        t += d + pausa
    return salida, t


def test_segmentos_en_rango_y_cortados_en_oracion():
    ors, dur = _oraciones_con([3, 4, 2.5, 6, 5, 3.5, 4, 7, 2, 3, 5, 4.5, 3, 6, 2.5, 4])
    segs = segmentar(ors, dur, (8, 20), 30)
    assert segs[0]["inicio"] == 0 and segs[-1]["fin"] == pytest.approx(dur)
    for a, b in zip(segs, segs[1:]):
        assert a["fin"] == b["inicio"]                                    # sin huecos
        assert a["fin"] in [round(o["inicio"], 3) for o in ors]           # el corte es inicio de oración
    assert all(8 <= s["duracion"] <= 20 for s in segs)
    assert sorted(i for s in segs for i in s["oraciones"]) == list(range(len(ors)))   # todas, una vez


def test_nunca_pasa_de_30_segundos():
    ors, dur = _oraciones_con([12, 12, 12, 12, 29, 1, 1])
    segs = segmentar(ors, dur, (8, 20), 30)
    assert all(s["duracion"] <= 30 for s in segs)
    assert not any(s["oracion_partida"] for s in segs)


def test_oracion_de_mas_de_30_se_parte_en_una_pausa():
    ors, dur = _oraciones_con([5, 45, 6])
    segs = segmentar(ors, dur, (8, 20), 30)
    assert all(s["duracion"] <= 30 for s in segs)
    assert any(s["oracion_partida"] for s in segs)


def test_guion_cortisimo_da_un_segmento():
    ors, dur = _oraciones_con([2, 1.5])
    segs = segmentar(ors, dur, (8, 20), 30)
    assert len(segs) == 1 and segs[0]["duracion"] == pytest.approx(dur)


# ------------------------------------------------------------------ preset

def test_preset_por_defecto_y_validacion():
    p = completar(None)
    assert p == {**preset_por_defecto(), "clip_objetivo_s": [8.0, 20.0]}
    assert p["proporcion_seminario"] == 0.4 and p["clip_max_s"] == 30
    assert completar({"proporcion_seminario": 0.5})["proporcion_seminario"] == 0.5
    with pytest.raises(ValueError):
        completar({"clip_objetivo_s": [8, 40]})
    with pytest.raises(ValueError):
        completar({"proporcion_seminario": 1.5})


def test_canal_tracy_en_la_base_y_los_demas_siguen_generated():
    from estudio.plataforma import contexto, db
    from estudio.plataforma.cuentas import cuenta_local
    from estudio.tracy.preset import cargar_preset, crear_canal_tracy, visual_mode

    db.preparar()
    with db.sesion() as s:
        _, e = cuenta_local(s)
        esp = e.id
    contexto.fijar_espacio(esp)
    crear_canal_tracy(clip_base="D:/seminario.mp4", proporcion_seminario=0.3)
    assert visual_mode("tracy") == "stock"
    assert visual_mode("animales-peligrosos") == "generated"
    p = cargar_preset("tracy")
    assert p["clip_base"] == "D:/seminario.mp4" and p["proporcion_seminario"] == 0.3
    crear_canal_tracy(voz_id="otra_voz")                          # ajustar no borra lo anterior
    p = cargar_preset("tracy")
    assert p["voz_id"] == "otra_voz" and p["clip_base"] == "D:/seminario.mp4"


# ------------------------------------------------------------------ de punta a punta (simulado)

def test_ensayo_simulado_de_punta_a_punta_y_reanudable():
    from estudio.tracy.flujo import crear_proyecto, paso_audio

    guion = ("Hace 30 años descubrí algo. " * 3 + "\n\n" + "El 80% de tus resultados viene del 20% de lo que haces. " * 6
             + "Empieza hoy.")
    c = crear_proyecto(guion, titulo="Prueba Tracy")
    assert c.cargar().visual_mode == "stock"
    r = paso_audio(c, proveedor="simulado", avisar=lambda *_: None)
    assert r["confianza"] == 1.0 and r["segmentos"]
    assert "30" not in (c.ruta / "guion_tts.txt").read_text(encoding="utf-8")
    datos = json.loads((c.ruta / "segmentos.json").read_text(encoding="utf-8"))
    assert all(s["duracion"] <= 30 for s in datos["segmentos"])
    assert datos["segmentos"][-1]["fin"] == pytest.approx(r["duracion"], abs=0.05)

    class Contadora:
        nombre = "simulado"

        def __init__(self):
            from estudio.tracy.audio import VozSimulada
            self.v, self.llamadas, self.modelo, self.tarifa_mil = VozSimulada(), 0, "simulado", 0.0

        def huella(self, t):
            return self.v.huella(t)

        def estimar_usd(self, t):
            return 0.0

        def sintetizar(self, t):
            self.llamadas += 1
            return self.v.sintetizar(t)

    voz = Contadora()
    paso_audio(c, proveedor="simulado", voz=voz, avisar=lambda *_: None)
    assert voz.llamadas == 0                                      # lo ya hecho no se vuelve a pedir


def test_proyectos_de_siempre_siguen_siendo_generated():
    from estudio.esquemas import Proyecto

    p = Proyecto.model_validate({"slug": "x", "titulo": "x", "canal": "c", "estilo": "e",
                                 "duracion_objetivo_seg": 60, "creado": "2026-01-01"})
    assert p.visual_mode == "generated"
