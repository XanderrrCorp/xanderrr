"""Asistente de personaje, sin gasto: imágenes simuladas y Claude falso."""
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from estudio import personajes as ps
from estudio.config import ConfigCostos
from estudio.imagenes.proveedores import ProveedorSimulado


def claude_falso(pedidos):
    def ejecutar(pedido, **_):
        pedidos.append(pedido)
        extra = ", wearing a tiny red bow tie" if "Aplícale este cambio" in pedido else ""
        return json.dumps({"bloqueo": f"a small round green frog with big yellow eyes and a white belly{extra}"}), {}
    return ejecutar


def test_de_la_descripcion_al_personaje_fijo(tmp_path):
    ruta = tmp_path / "sapiens"
    ps.crear(ruta, "Sapiens", "enciclopedia_mascota", "Una rana verde, redonda y curiosa")
    prov, pedidos = ProveedorSimulado(ConfigCostos.cargar()), []
    ejecutar = claude_falso(pedidos)

    hechas = ps.variantes(ruta, 3, proveedor=prov, ejecutar=ejecutar, avisar=lambda *_: None)
    assert len(hechas) == 3 and prov.llamadas == 3 and ps.cargar(ruta).paso == "elegir"
    assert "green frog" in ps.cargar(ruta).bloqueo
    with pytest.raises(ValueError):
        ps.elegir(ruta, "imagenes/otra.png")
    ps.elegir(ruta, hechas[1])

    afinada = ps.afinar(ruta, "con un corbatín rojo", proveedor=prov, ejecutar=ejecutar, avisar=lambda *_: None)
    e = ps.cargar(ruta)
    assert e.elegida == afinada and "bow tie" in e.bloqueo and e.variantes[-1].nota == "con un corbatín rojo"

    ps.hoja(ruta, proveedor=prov, avisar=lambda *_: None)
    e = ps.cargar(ruta)
    assert set(e.hoja) == {"frente", "perfil", "tres_cuartos", "hoja"} and e.paso == "probar"
    hoja = Image.open(ruta / e.hoja["hoja"])
    assert hoja.width > 3 * hoja.height / 2                          # las tres vistas lado a lado

    ps.probar(ruta, proveedor=prov, avisar=lambda *_: None)
    e = ps.cargar(ruta)
    assert len(e.pruebas) == 3 and e.paso == "listo"
    assert prov.llamadas == 3 + 1 + 3 + 3 and ps.gastado_usd(ruta) > 0   # cada imagen queda en su libro

    # elegir otra base obliga a rehacer la hoja y las pruebas
    ps.elegir(ruta, hechas[0])
    assert ps.cargar(ruta).paso == "afinar" and not ps.cargar(ruta).pruebas


def test_el_video_del_canal_usa_el_personaje_sin_las_poses_de_otro(tmp_path):
    ruta = tmp_path / "p"
    ps.crear(ruta, "P", "enciclopedia_mascota", "Un búho con gafas")
    prov = ProveedorSimulado(ConfigCostos.cargar())
    ps.variantes(ruta, 1, proveedor=prov, ejecutar=claude_falso([]), avisar=lambda *_: None)
    e = ps.cargar(ruta)
    ps.elegir(ruta, e.variantes[0].archivo)
    video = tmp_path / "video"
    (video / "assets" / "poses").mkdir(parents=True)
    (video / "assets" / "poses" / "susto.png").write_bytes(b"x")
    assert ps.usar_en_video(ruta, video)
    assert (video / "assets" / "mascota_base.png").read_bytes() == (ruta / e.variantes[0].archivo).read_bytes()
    assert not (video / "assets" / "poses").exists()
    from estudio.config import leer_json

    assert "green frog" in leer_json(video / "perfil_canal.json")["personaje"]["bloqueo"]


def test_sin_descripcion_ni_referencia_no_se_crea(tmp_path):
    with pytest.raises(ValueError):
        ps.crear(tmp_path / "x", "X", "enciclopedia_mascota", "")


def _esperar(cli, pid):
    for _ in range(200):
        d = cli.get(f"/api/v2/personajes/{pid}").json()
        if not (d["trabajo"] or {}).get("activo"):
            return d
        time.sleep(0.05)
    raise AssertionError("el trabajo no terminó")


def test_api_del_asistente_y_asignacion_al_canal(monkeypatch):
    from estudio import app as modulo_app
    from estudio import claude_cli
    from estudio.plataforma import db
    from estudio.plataforma.cuentas import cuenta_local
    from estudio.plataforma.modelos import Canal

    monkeypatch.setattr(ps, "_proveedor", lambda config: ProveedorSimulado(config))
    monkeypatch.setattr(claude_cli, "ejecutar", claude_falso([]))
    cli = TestClient(modulo_app.app)
    cli.get("/api/v2/cuenta")
    with db.sesion() as s:
        _, esp = cuenta_local(s)
        s.add(Canal(espacio_id=esp.id, clave="paradoja", nombre="Paradoja Sapiens"))

    assert cli.post("/api/v2/personajes", data={"nombre": "X", "estilo": "no_existe", "descripcion": "algo largo"}).status_code == 400
    ref = Image.new("RGB", (64, 64), (0, 200, 0))
    import io

    b = io.BytesIO(); ref.save(b, "PNG")
    d = cli.post("/api/v2/personajes", data={"nombre": "Sapiens", "estilo": "enciclopedia_mascota",
                                             "descripcion": "Un neandertal simpático"},
                 files={"referencia": ("ref.png", b.getvalue(), "image/png")}).json()
    pid = d["id"]
    assert d["paso"] == "describir" and d["referencia"] == "referencia.png"
    assert cli.get(f"/api/v2/personajes/{pid}/archivos/referencia/referencia.png").status_code == 200

    cli.post(f"/api/v2/personajes/{pid}/variantes", json={"n": 2})
    d = _esperar(cli, pid)
    assert d["paso"] == "elegir" and len(d["variantes"]) == 2 and d["trabajo"]["error"] is None
    nombre = d["variantes"][0]["archivo"].split("/")[-1]
    assert cli.get(f"/api/v2/personajes/{pid}/archivos/imagenes/{nombre}").status_code == 200
    assert cli.get(f"/api/v2/personajes/{pid}/archivos/imagenes/..%2Fpersonaje.json").status_code == 404
    r = cli.post(f"/api/v2/personajes/{pid}/elegir", json={"archivo": d["variantes"][0]["archivo"]})
    assert r.status_code == 200 and r.json()["paso"] == "afinar", r.text
    canal = next(c for c in d["canales"] if c["nombre"] == "Paradoja Sapiens")
    assert cli.post(f"/api/v2/personajes/{pid}/canal", json={"canal_id": canal["id"]}).status_code == 400   # sin hoja
    r = cli.post(f"/api/v2/personajes/{pid}/hoja", json={})
    assert r.status_code == 200, r.text
    d = _esperar(cli, pid)
    assert d["paso"] == "probar", d["trabajo"]
    d = cli.post(f"/api/v2/personajes/{pid}/canal", json={"canal_id": canal["id"]}).json()
    assert next(c for c in d["canales"] if c["id"] == canal["id"])["asignado"]
    assert cli.put(f"/api/v2/personajes/{pid}", json={"bloqueo": "corto"}).status_code == 400

    lista = cli.get("/api/v2/personajes").json()
    assert any(x["id"] == pid and x["asistente"] and x["paso"] == "probar" for x in lista)

    # un video nuevo del canal usa el personaje
    from estudio import pipeline
    from estudio.plataforma import contexto

    contexto.fijar_espacio(esp.id)
    c = pipeline.crear_video("Paradojas del tiempo", "", "", 6, canal="paradoja", estilo_id="enciclopedia_mascota")
    assert (c.ruta / "assets" / "personaje_hoja.png").exists()
    assert "neandertal" not in (c.ruta / "perfil_canal.json").read_text() and "green frog" in (c.ruta / "perfil_canal.json").read_text()


def test_poses_propias_del_personaje_para_el_canal(tmp_path):
    """(24-10) El personaje nuevo del canal tiene sus propias poses (señalando, susto, asco): se hacen una vez y cada
    video del canal las usa en el like, junto a las fotos y en el cierre."""
    ruta = tmp_path / "streetwear"
    ps.crear(ruta, "Streetwear", "enciclopedia_mascota", "El de siempre pero con hoodie y gorro de pescador rojo")
    prov = ProveedorSimulado(ConfigCostos.cargar())
    ps.variantes(ruta, 1, proveedor=prov, ejecutar=claude_falso([]), avisar=lambda *_: None)
    ps.elegir(ruta, ps.cargar(ruta).variantes[0].archivo)
    hechas = ps.poses(ruta, proveedor=prov, avisar=lambda *_: None)
    ids = [x.id for x in ps.poses_del_canal("enciclopedia_mascota")]
    assert hechas == ids and prov.llamadas == 1 + len(ids)
    assert ps.poses(ruta, proveedor=prov, avisar=lambda *_: None) == ids and prov.llamadas == 1 + len(ids)  # no repaga
    video = tmp_path / "video"
    (video / "assets" / "poses").mkdir(parents=True)
    (video / "assets" / "poses" / "senalando_susto.png").write_bytes(b"del granjero")
    assert ps.usar_en_video(ruta, video)
    nuevas = sorted(p.stem for p in (video / "assets" / "poses").glob("*.png"))
    assert nuevas == sorted(ids)
    assert (video / "assets" / "poses" / "senalando_susto.png").read_bytes() != b"del granjero"


def test_si_google_esta_ocupado_espera_y_no_repaga_lo_hecho(tmp_path, monkeypatch):
    """(26-10) El dueño vio «HTTP 429 RESOURCE_EXHAUSTED» al hacer la hoja: ahora espera y reintenta solo, y si
    Google sigue ocupado da un mensaje claro; lo ya dibujado no se vuelve a pagar."""
    from estudio.imagenes.proveedores import ErrorProveedor

    esperas = []
    monkeypatch.setattr(ps, "_dormir", esperas.append)
    ruta = tmp_path / "p"
    ps.crear(ruta, "P", "enciclopedia_mascota", "Un búho con gafas")
    prov = ProveedorSimulado(ConfigCostos.cargar())
    ps.variantes(ruta, 1, proveedor=prov, ejecutar=claude_falso([]), avisar=lambda *_: None)
    ps.elegir(ruta, ps.cargar(ruta).variantes[0].archivo)

    original, fallos = prov.generar, {"n": 0}

    def ocupado(prompt, refs):
        if prov.llamadas == 2 and fallos["n"] < 10:       # la segunda vista de la hoja: Google ocupado un rato largo
            fallos["n"] += 1
            raise ErrorProveedor("HTTP 429: RESOURCE_EXHAUSTED", limite=True)
        return original(prompt, refs)

    monkeypatch.setattr(prov, "generar", ocupado)
    avisos = []
    with pytest.raises(ps.GoogleOcupado, match="No se cobró nada"):
        ps.hoja(ruta, proveedor=prov, avisar=avisos.append)
    assert esperas == list(ps.ESPERAS_429_S) and any("Google está ocupado" in a for a in avisos)
    assert prov.llamadas == 2                                  # la variante + la primera vista

    ps.hoja(ruta, proveedor=prov, avisar=lambda *_: None)      # al volver a darle: Google ya responde
    assert prov.llamadas == 2 + 2 and set(ps.cargar(ruta).hoja) == {"frente", "perfil", "tres_cuartos", "hoja"}
    assert not (ruta / "hoja_parcial.json").exists()
