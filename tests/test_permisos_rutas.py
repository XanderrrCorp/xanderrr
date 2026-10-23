"""(Paso C) Permisos por ruta: todo cerrado por defecto (sin regla = solo el dueño) y cada dirección con su regla."""
import re

import pytest
from fastapi.testclient import TestClient

from estudio import app as modulo_app
from estudio.plataforma import acceso, db
from estudio.plataforma import permisos_rutas as P
from estudio.plataforma.cuentas import cuenta_local


def _ejemplo(plantilla: str) -> str:
    return re.sub(r"\{[^}]+\}", "x1", plantilla)


def test_cada_direccion_tiene_su_regla_decidida():
    """Si alguien agrega una dirección y no decide quién la usa, esta prueba falla (aunque igual quedaría cerrada)."""
    faltan = []
    for ruta, ops in modulo_app.app.openapi()["paths"].items():
        for metodo in ops:
            if P.regla(metodo.upper(), _ejemplo(ruta)) is None:
                faltan.append(f"{metodo.upper()} {ruta}")
    assert not faltan, "Direcciones sin regla en permisos_rutas.REGLAS: " + ", ".join(faltan)


def test_sin_regla_es_solo_del_dueno():
    assert P.regla("GET", "/api/algo-nuevo-que-nadie-decidio") is None
    assert P.nivel("GET", "/api/algo-nuevo-que-nadie-decidio") == P.OWNER
    assert not P.permitido("beta", P.OWNER) and not P.permitido("admin", P.OWNER) and P.permitido("owner", P.OWNER)
    assert P.permitido("admin", P.ADMIN) and not P.permitido("beta", P.ADMIN)


@pytest.fixture
def clientes():
    acceso.EN_PRUEBAS["como_dueno"] = False
    acceso._FALLOS.clear()
    db.preparar()
    with db.sesion() as s:
        cuenta_local(s)
    dueno = TestClient(modulo_app.app, follow_redirects=False)
    assert dueno.post("/api/v2/crear-clave-dueno", json={"email": "dueno@x.co", "clave": "clave-del-dueno"}).status_code == 200
    salida = {"owner": dueno}
    for rol, email in (("beta", "beta@x.co"), ("admin", "admin@x.co")):
        r = dueno.post("/api/v2/admin/usuarios", json={"email": email}).json()
        if rol == "admin":
            from estudio.plataforma.modelos import Usuario

            with db.sesion() as s:
                s.get(Usuario, r["id"]).rol = "admin"
            acceso.olvidar_sesiones()
        c = TestClient(modulo_app.app, follow_redirects=False)
        assert c.post("/api/v2/entrar", json={"email": email, "clave": r["clave_temporal_texto"]}).status_code == 200
        assert c.post("/api/v2/cambiar-clave", json={"actual": r["clave_temporal_texto"], "nueva": "clave-propia-1"}
                      ).status_code == 200
        salida[rol] = c
    return salida


SOLO_DUENO = [
    ("GET", "/api/tracy"), ("GET", "/api/explica"), ("GET", "/api/calma"), ("GET", "/api/cola"),
    ("POST", "/api/cola/peligro"), ("GET", "/api/estado"), ("POST", "/api/claves"), ("GET", "/api/google-cuenta"),
    ("GET", "/api/biblioteca"), ("GET", "/api/espacio"), ("POST", "/api/espacio/liberar"), ("POST", "/api/importar"),
    ("GET", "/api/canales/peligro/miniatura"), ("GET", "/api/videos/x/miniatura"), ("POST", "/api/videos/x/revisar"),
    ("GET", "/api/v2/estudio"), ("GET", "/api/v2/admin/copias"), ("POST", "/api/abrir-carpeta"),
    ("POST", "/api/apagar"),
]


def test_beta_no_entra_a_lo_del_dueno_ni_a_la_administracion(clientes):
    beta = clientes["beta"]
    for metodo, ruta in SOLO_DUENO + [("GET", "/api/v2/admin/usuarios"), ("PUT", "/api/v2/admin/precios/x")]:
        r = beta.request(metodo, ruta, json={})
        assert r.status_code == 403 and r.json()["detail"] == "Esto no está disponible en tu cuenta.", (metodo, ruta)
    # las páginas viejas de Ajustes y Admin lo devuelven a la página nueva
    for ruta in ("/", "/admin"):
        r = beta.get(ruta)
        assert r.status_code == 303 and r.headers["location"] == "/app/", ruta
    # lo suyo sí
    for ruta in ("/api/v2/cuenta", "/api/v2/canales", "/api/v2/personajes", "/api/v2/recursos/estilos",
                 "/api/v2/creditos/historial", "/api/v2/avisos", "/api/v2/precios"):
        assert beta.get(ruta).status_code == 200, ruta


def test_admin_administra_pero_no_ve_lo_privado(clientes):
    admin = clientes["admin"]
    assert admin.get("/api/v2/admin/usuarios").status_code == 200
    assert admin.get("/admin").status_code == 200
    for metodo, ruta in SOLO_DUENO:
        assert admin.request(metodo, ruta, json={}).status_code == 403, (metodo, ruta)


def test_el_dueno_pasa_a_todo(clientes):
    dueno = clientes["owner"]
    for metodo, ruta in SOLO_DUENO:
        if ruta in ("/api/apagar", "/api/abrir-carpeta", "/api/espacio/liberar", "/api/cola/peligro", "/api/claves"):
            continue                      # no se apaga ni se cambia nada en la prueba: basta con ver la regla
        assert dueno.request(metodo, ruta).status_code != 403, (metodo, ruta)
    assert dueno.get("/").status_code == 200 and dueno.get("/admin").status_code == 200


def test_las_pantallas_privadas_solo_le_llegan_al_dueno(clientes):
    """Los archivos de Tracy, El Calvo, Calma y la cola (aparte de la página) no se le entregan a nadie más."""
    from pathlib import Path

    assets = Path(modulo_app.__file__).parent / "web_app" / "assets"
    privados = [f.name for f in assets.glob("*.js") if P.PRIVADAS_APP.match(f"/app/assets/{f.name}")]
    publico = next(f.name for f in assets.glob("index-*.js"))
    assert privados, "la página construida debería traer las pantallas privadas en archivos aparte"
    sin_sesion = TestClient(modulo_app.app, follow_redirects=False)
    for nombre in privados:
        assert clientes["beta"].get(f"/app/assets/{nombre}").status_code == 403, nombre
        assert clientes["admin"].get(f"/app/assets/{nombre}").status_code == 403, nombre
        assert sin_sesion.get(f"/app/assets/{nombre}").status_code == 401, nombre
        assert clientes["owner"].get(f"/app/assets/{nombre}").status_code == 200, nombre
    assert sin_sesion.get(f"/app/assets/{publico}").status_code == 200
