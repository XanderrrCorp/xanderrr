"""API v2: cuenta, precios, cotizar, historial y administración (precios, ajustes, proveedores, correo)."""
import json

import pytest
from fastapi.testclient import TestClient

from estudio import app as modulo_app
from estudio.config import ConfigCostos
from estudio.plataforma import correo, db, proveedores
from estudio.plataforma.modelos import Video


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.delenv("XANDART_SMTP_USUARIO", raising=False)
    monkeypatch.delenv("XANDART_SMTP_CLAVE", raising=False)
    monkeypatch.setattr(correo, "clave_api", lambda n: {"XANDART_SMTP_USUARIO": None}.get(n))
    return TestClient(modulo_app.app)


def test_cuenta_y_precios(cli):
    c = cli.get("/api/v2/cuenta").json()
    assert c["usuario"]["admin"] and c["usuario"]["a_costo"] and c["saldo"]["creditos"] == 0
    p = cli.get("/api/v2/precios").json()
    assert p["valor_credito_usd"] == 0.01
    assert [x["clave"] for x in p["planes"]] == ["lite", "starter", "creator"]
    assert {"clave": "video_minuto", "creditos": 145} .items() <= next(x for x in p["precios"]
                                                                       if x["clave"] == "video_minuto").items()
    assert p["paquetes"][0]["minutos"] == pytest.approx(1000 / 145, abs=0.1)


def test_cotizar_muestra_lo_que_pagaria_un_cliente(cli):
    r = cli.post("/api/v2/cotizar", json={"accion": "video_minuto", "cantidad": 9}).json()
    assert r["a_costo"] and r["alcanza"]                       # el dueño no se frena por saldo
    assert r["precio_cliente"]["creditos"] == 1305 and r["precio_cliente"]["usd"] == 13.05
    assert cli.post("/api/v2/cotizar", json={"accion": "no_existe"}).status_code == 404


def test_admin_edita_precio_y_ajusta_creditos_con_razon(cli):
    d = cli.get("/api/v2/admin/resumen").json()
    esp = d["espacios"][0]["id"]
    assert cli.put("/api/v2/admin/precios/video_minuto", json={"creditos": 150}).json()["ok"]
    r = cli.post("/api/v2/cotizar", json={"accion": "video_minuto", "cantidad": 1}).json()
    assert r["precio_cliente"]["creditos"] == 150
    assert cli.post("/api/v2/admin/creditos", json={"espacio_id": esp, "creditos": 500, "nota": ""}).status_code == 400
    assert cli.post("/api/v2/admin/creditos", json={"espacio_id": esp, "creditos": 500,
                                                    "nota": "Recarga de Together"}).json()["saldo"] == 500
    h = cli.get("/api/v2/creditos/historial").json()
    assert h[0]["tipo"] == "ajuste" and h[0]["nota"] == "Recarga de Together" and "costo_real_usd" in h[0]
    assert cli.put("/api/v2/admin/ajustes/bienvenida", json={"valor": {"creditos": 400}}).json()["ok"]
    assert cli.get("/api/v2/admin/resumen").json()["ajustes"]["bienvenida"]["creditos"] == 400


def test_saldo_de_proveedor_se_estima_y_avisa_una_vez(cli, tmp_path, monkeypatch):
    enviados = []
    monkeypatch.setattr(correo, "enviar", lambda para, asunto, texto: enviados.append((para, asunto)) or True)
    monkeypatch.setattr(correo, "para_avisos", lambda email: "dueno@gmail.com")
    cli.put("/api/v2/admin/proveedores/together", json={"saldo_usd": 4.0, "umbral_usd": 3.0})
    carpeta = tmp_path / "video"
    from estudio.costos import LibroCostos

    LibroCostos(carpeta, ConfigCostos.cargar()).registrar(modulo="imagenes", proveedor="together", modelo="x",
                                                          unidades={"imagenes": 30}, costo_usd=1.5)
    esp = cli.get("/api/v2/cuenta").json()["espacio"]["id"]
    with db.sesion() as s:
        s.add(Video(espacio_id=esp, slug="v", titulo="V", carpeta=str(carpeta)))
    est = cli.get("/api/v2/admin/resumen").json()["proveedores"][0]
    assert est["estimado_usd"] == 2.5 and est["bajo"]
    with db.sesion() as s:
        assert proveedores.revisar_y_avisar(s) == ["together"]
        assert proveedores.revisar_y_avisar(s) == []           # no repite el mismo aviso
    assert enviados == [("dueno@gmail.com", "Xandart: queda poco saldo en together")]


def test_correo_de_prueba_sin_configurar_explica_que_falta(cli):
    r = cli.post("/api/v2/admin/correo/prueba")
    assert r.status_code == 400 and "contraseña de aplicación" in r.json()["detail"]


def test_la_pagina_de_administracion_abre(cli):
    r = cli.get("/admin")
    assert r.status_code == 200 and "admin.js" in r.text
    assert cli.get("/web/admin.js").status_code == 200


def test_interfaz_nueva_se_sirve_en_app(cli):
    r = cli.get("/app/")
    assert r.status_code == 200 and '<div id="raiz">' in r.text
    assert cli.get("/app/planes").text == r.text                       # las páginas las resuelve el navegador
    js = next(p for p in (modulo_app.APP / "assets").iterdir() if p.suffix == ".js")
    assert cli.get(f"/app/assets/{js.name}").status_code == 200
    assert cli.get("/app/../app.py").status_code in (200, 404)          # nunca sale de la carpeta
    assert "def " not in cli.get("/app/..%2Fapp.py").text


def test_lista_de_videos_con_portada_y_estado(cli):
    from estudio import pipeline

    c = pipeline.crear_video("Ranas venenosas", "", "", 9)
    v = cli.get("/api/v2/videos").json()
    assert v[0]["slug"] == c.ruta.name and v[0]["estado"] == "borrador" and v[0]["portada"] is None
