"""Cola de la semana (16-10): varios videos seguidos, uno a la vez, que siguen si se cierra Xandart."""
import time

import pytest


@pytest.fixture(autouse=True)
def espacio(monkeypatch):
    from estudio.plataforma import contexto, db, local
    from estudio.plataforma.cuentas import cuenta_local

    db.preparar()
    with db.sesion() as s:
        _, e = cuenta_local(s)
        esp = e.id
    contexto.fijar_espacio(esp)
    monkeypatch.setattr(local, "espacio", lambda *a, **k: esp)      # las peticiones de la página, en ese espacio
    return esp


def _esperar(cola, maximo=20):
    fin = time.time() + maximo
    while time.time() < fin:
        e = cola.estado()
        if not e["trabajando"]:
            return e
        time.sleep(0.1)
    raise AssertionError("la cola no terminó")


def test_cola_hace_los_videos_uno_tras_otro(monkeypatch):
    from estudio import cola
    from estudio.tracy import flujo

    hechos, a_la_vez, activos = [], [], [0]

    def producir(c, t, permiso=False, **_):
        activos[0] += 1
        a_la_vez.append(activos[0])
        time.sleep(0.2)
        hechos.append(c.ruta.name)
        activos[0] -= 1
        if "falla" in c.cargar().titulo.lower():
            raise RuntimeError("Este video pasó el máximo de gasto")

    monkeypatch.setattr(flujo, "producir", producir)
    guion = "Este es un guion de prueba bastante largo para que pase el mínimo de letras. " * 2
    cola.agregar_tracy([{"titulo": "Uno", "guion": guion}, {"titulo": "Dos falla", "guion": guion},
                        {"titulo": "Tres", "guion": guion}, {"titulo": "", "guion": "corto"}], permiso=False,
                       etiqueta="Mentalidad Imparable")
    e = _esperar(cola)
    assert len(hechos) == 3 and max(a_la_vez) == 1                       # nunca dos a la vez
    estados = [(x["titulo"], x["estado"], x["etiqueta"]) for x in e["videos"]]
    assert [s for _, s, _ in estados] == ["listo", "error", "listo"]
    assert all(et == "Mentalidad Imparable" for _, _, et in estados)
    malo = next(x for x in e["videos"] if x["estado"] == "error")
    assert "máximo" in malo["error"]
    # con permiso vuelve a la cola y esta vez termina
    monkeypatch.setattr(flujo, "producir", lambda c, t, permiso=False, **_: hechos.append(("permiso", permiso)))
    cola.reintentar(malo["id"], permiso=True)
    e = _esperar(cola)
    assert ("permiso", True) in hechos and all(x["estado"] == "listo" for x in e["videos"])
    cola.limpiar_terminados()
    assert cola.leer() == []


def test_cola_sigue_si_se_cerro_xandart_y_se_puede_quitar(monkeypatch):
    from estudio import cola

    monkeypatch.setattr(cola, "arrancar", lambda: None)                  # sin trabajador: solo la lista
    guion = "Otro guion de prueba bastante largo para que pase el mínimo de letras pedido. " * 2
    a, b = cola.agregar_tracy([{"guion": guion}, {"guion": guion}], permiso=False)
    cola._cambiar(a["id"], estado="haciendo")                           # Xandart se cerró a mitad
    cola.recuperar()
    assert {x["estado"] for x in cola.leer()} == {"esperando"}
    cola.quitar(b["id"])
    assert [x["id"] for x in cola.leer()] == [a["id"]]


def test_api_de_la_cola(monkeypatch):
    from fastapi.testclient import TestClient

    from estudio import cola
    from estudio.app import app

    monkeypatch.setattr(cola, "arrancar", lambda: None)
    cliente = TestClient(app)
    r = cliente.post("/api/cola/tracy", json={"guiones": [{"titulo": "X", "guion": "corto"}]})
    assert r.status_code == 400
    guion = "Guion para la prueba de la página con suficientes letras para pasar el mínimo. " * 2
    r = cliente.post("/api/cola/tracy", json={"guiones": [{"titulo": "X", "guion": guion}], "etiqueta": "Código"})
    assert r.status_code == 200 and r.json()["esperando"] == 1
    assert cliente.get("/api/cola").json()["videos"][0]["etiqueta"] == "Código"


def test_cola_de_el_calvo_explica(monkeypatch):
    from estudio import cola
    from estudio.explica import autor
    from estudio.explica import flujo as F

    pasos = []
    monkeypatch.setattr(autor, "escribir_guion", lambda c, titulo, n, datos, avisar=None:
                        (pasos.append(("guion", titulo, n, datos)), (c / "guion.txt").write_text("x")))
    monkeypatch.setattr(autor, "armar_escenas", lambda c, avisar=None:
                        (pasos.append(("escenas",)), (c / "escenas.json").write_text("{}")))
    monkeypatch.setattr(F, "producir", lambda c, t, permiso=False, **_: pasos.append(("video", permiso)))
    cola.agregar_explica([{"tema": "Cosas raras que hace tu cuerpo", "notas": "el sobresalto"}], permiso=False, temas=8)
    e = _esperar(cola)
    assert pasos == [("guion", "Cosas raras que hace tu cuerpo", 8, "el sobresalto"), ("escenas",), ("video", False)]
    assert e["videos"][0]["estado"] == "listo" and e["videos"][0]["etiqueta"] == "El Calvo Explica"
