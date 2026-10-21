"""(22-10) Lo privado del dueño (Tracy, sus módulos y las fórmulas de sus canales) nunca le llega a un usuario BETA:
ni en el selector de formatos, ni en el catálogo, ni por ID, ni en el código de la página."""
import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from estudio import app as modulo_app
from estudio.plataforma import api as api_v2, db
from estudio.plataforma.cuentas import cuenta_local, registrar
from estudio.plataforma.migrar import sembrar_catalogo
from estudio.plataforma.modelos import Formato

PRIVADO = re.compile(r"Brian Tracy|Tracy|El Calvo|Hazlo con Calma|escala_peligro|paradoja_documental|escala_2x3", re.I)


def _clientes():
    db.preparar()
    with db.sesion() as s:
        sembrar_catalogo(s)
        dueno, e_dueno = cuenta_local(s)
        beta, e_beta = registrar(s, "beta@prueba.co", "Beta")
        s.commit()
        quien_dueno, quien_beta = api_v2.Quien(dueno, e_dueno), api_v2.Quien(beta, e_beta)
        privado = s.query(Formato).filter(Formato.clave == "escala_peligro", Formato.espacio_id.is_(None)).one().id
    app = modulo_app.app
    cli = TestClient(app)
    return app, cli, quien_dueno, quien_beta, privado


def test_beta_no_ve_nada_privado_del_dueno():
    app, cli, quien_dueno, quien_beta, privado = _clientes()
    try:
        app.dependency_overrides[api_v2.usuario_actual] = lambda: quien_beta
        for ruta in ("/api/v2/recursos/formatos", "/api/v2/recursos/estilos", "/api/v2/recursos/plantillas",
                     "/api/v2/recursos/formulas", "/api/v2/canales", "/api/v2/cuenta"):
            r = cli.get(ruta)
            assert r.status_code == 200 and not PRIVADO.search(r.text), (ruta, r.text[:300])
        assert cli.get("/api/v2/estudio").status_code == 403
        assert cli.post(f"/api/v2/recursos/formatos/{privado}/duplicar", json={}).status_code == 404
        # el dueño sí los ve, marcados para su grupo «Tu estudio»
        app.dependency_overrides[api_v2.usuario_actual] = lambda: quien_dueno
        formatos = {f["clave"]: f for f in cli.get("/api/v2/recursos/formatos").json()}
        assert formatos["escala_peligro"]["estudio"] is True
        assert "Brian Tracy" in json.dumps(cli.get("/api/v2/estudio").json(), ensure_ascii=False)
    finally:
        app.dependency_overrides.clear()


def test_el_codigo_de_la_pagina_no_nombra_lo_privado():
    """Tracy, El Calvo y Calma solo viven en sus pantallas (archivos aparte que se cargan al abrirlas); el resto de la
    interfaz recibe sus nombres del servidor (/api/v2/estudio, solo para el dueño)."""
    src = Path(__file__).resolve().parent.parent / "interfaz" / "src"
    privadas = {"Tracy.tsx", "Explica.tsx", "ExplicaNuevo.tsx", "Calma.tsx", "Cola.tsx"}
    for f in src.rglob("*.ts*"):
        if f.name in privadas:
            continue
        texto = re.sub(r"//.*|/\*.*?\*/", "", f.read_text(encoding="utf-8"), flags=re.S)
        assert not re.search(r"Brian Tracy|Canal Tracy|El Calvo Explica|Hazlo con Calma", texto), f.name
    app = (src / "App.tsx").read_text(encoding="utf-8")
    for p in ("Tracy", "Explica", "Calma", "Cola"):
        assert f"import('./paginas/{p}')" in app                   # se cargan aparte, no van en el archivo principal


def test_la_voz_de_siempre_no_cambia_por_el_asistente_de_canal():
    from estudio.plataforma import consultas, contexto
    from estudio.plataforma.modelos import Canal, Voz

    db.preparar()
    with db.sesion() as s:
        _, e = cuenta_local(s)
        v = Voz(espacio_id=e.id, clave="voz_principal", nombre="Voz principal", datos={"voz_id": "otra", "velocidad": 0.5})
        s.add(v); s.flush()
        s.add(Canal(espacio_id=e.id, clave="animales-peligrosos", nombre="PT", voz_id=v.id))
        esp = e.id
    with contexto.usar_espacio(esp):
        assert consultas.voz_del_canal("animales-peligrosos") is None   # se sigue leyendo de proveedores.json


def test_mientras_copia_la_pagina_lo_sabe():
    from estudio import avisos

    db.PREPARANDO.update(fase="copiando", desde=0)
    try:
        assert avisos.respaldo()["estado"] == "copiando"
    finally:
        db.PREPARANDO.clear()
