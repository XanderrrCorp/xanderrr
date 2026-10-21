"""(Paso B) Inicio de sesión: sin sesión no se ve nada; el dueño crea su contraseña la primera vez (solo desde su PC);
los beta los crea el dueño con contraseña temporal; bloqueo; intentos fallidos; restablecer sin correo."""
import pytest
from fastapi.testclient import TestClient

from estudio import app as modulo_app
from estudio.plataforma import acceso, db
from estudio.plataforma.cuentas import cuenta_local


@pytest.fixture
def cli():
    acceso.EN_PRUEBAS["como_dueno"] = False
    acceso._FALLOS.clear()
    db.preparar()
    with db.sesion() as s:
        cuenta_local(s)
    yield TestClient(modulo_app.app, follow_redirects=False)
    acceso._FALLOS.clear()


def _dueno_con_clave(cli, clave="clave-del-dueno"):
    r = cli.post("/api/v2/crear-clave-dueno", json={"email": "dueno@xandart.co", "clave": clave, "recordar": True})
    assert r.status_code == 200, r.text
    return r


def test_sin_sesion_no_se_ve_nada(cli):
    assert cli.get("/api/v2/cuenta").status_code == 401
    assert cli.get("/api/videos/algo").status_code == 401
    assert cli.post("/api/videos", json={}).status_code == 401
    assert cli.get("/api/cola").status_code == 401
    # las páginas viejas llevan a entrar y luego vuelven
    for ruta in ("/", "/admin", "/archivos/x/y.png"):
        r = cli.get(ruta)
        assert r.status_code == 303 and r.headers["location"].startswith("/app/entrar?volver="), ruta
    # lo libre: la página nueva (sin datos), preguntar si hay sesión y la versión
    assert cli.get("/api/version").status_code == 200
    s = cli.get("/api/v2/sesion").json()
    assert s["conectado"] is False and s["crear_clave_dueno"] is True


def test_dueno_crea_su_clave_la_primera_vez_y_entra(cli):
    r = _dueno_con_clave(cli)
    assert acceso.GALLETA in r.cookies
    assert "samesite=strict" in r.headers["set-cookie"].lower() and "httponly" in r.headers["set-cookie"].lower()
    assert "max-age=2592000" in r.headers["set-cookie"].lower()          # «Recordarme» = 30 días
    assert cli.get("/api/v2/cuenta").status_code == 200
    assert cli.get("/").status_code == 200
    # ya tiene contraseña: no se puede volver a «crear»
    assert cli.post("/api/v2/crear-clave-dueno", json={"email": "otro@x.co", "clave": "otra-clave-1"}).status_code == 409
    # salir y volver a entrar
    cli.post("/api/v2/salir")
    cli.cookies.clear()
    assert cli.get("/api/v2/cuenta").status_code == 401
    assert cli.post("/api/v2/entrar", json={"email": "dueno@xandart.co", "clave": "mala-clave"}).status_code == 401
    r = cli.post("/api/v2/entrar", json={"email": "DUENO@xandart.co ", "clave": "clave-del-dueno"})
    assert r.status_code == 200 and r.json()["usuario"]["rol"] == "owner"
    assert "max-age" not in r.headers["set-cookie"].lower()      # sin «Recordarme»: se borra al cerrar el navegador
    assert cli.get("/api/v2/cuenta").status_code == 200


def test_clave_del_dueno_solo_desde_este_pc(cli):
    r = cli.post("/api/v2/crear-clave-dueno", json={"email": "dueno@xandart.co", "clave": "clave-del-dueno"},
                 headers={"X-Forwarded-For": "8.8.8.8"})
    assert r.status_code == 403
    assert cli.get("/api/v2/sesion", headers={"CF-Connecting-IP": "8.8.8.8"}).json()["crear_clave_dueno"] is False
    assert cli.post("/api/v2/crear-clave-dueno", json={"email": "dueno@xandart.co", "clave": "corta"}).status_code == 400


def test_beta_creado_por_el_dueno_cambia_su_clave_temporal(cli):
    _dueno_con_clave(cli)
    r = cli.post("/api/v2/admin/usuarios", json={"email": "ana@correo.co", "nombre": "Ana"})
    assert r.status_code == 200, r.text
    temporal = r.json()["clave_temporal_texto"]
    assert cli.post("/api/v2/admin/usuarios", json={"email": "ana@correo.co"}).status_code == 409
    cli.post("/api/v2/salir")
    cli.cookies.clear()

    beta = TestClient(modulo_app.app, follow_redirects=False)
    r = beta.post("/api/v2/entrar", json={"email": "ana@correo.co", "clave": temporal})
    assert r.status_code == 200 and r.json()["cambiar_clave"] is True and r.json()["usuario"]["rol"] == "beta"
    # un beta no administra cuentas
    assert beta.get("/api/v2/admin/usuarios").status_code == 403
    assert beta.post("/api/v2/cambiar-clave", json={"actual": temporal, "nueva": "corta"}).status_code == 400
    r = beta.post("/api/v2/cambiar-clave", json={"actual": temporal, "nueva": "mi-clave-nueva"})
    assert r.status_code == 200 and r.json()["cambiar_clave"] is False
    assert beta.get("/api/v2/cuenta").json()["usuario"]["email"] == "ana@correo.co"
    # la temporal ya no sirve
    assert TestClient(modulo_app.app).post("/api/v2/entrar", json={"email": "ana@correo.co", "clave": temporal}
                                           ).status_code == 401


def test_bloquear_saca_al_beta_en_la_siguiente_accion(cli):
    _dueno_con_clave(cli)
    r = cli.post("/api/v2/admin/usuarios", json={"email": "leo@correo.co"}).json()
    beta = TestClient(modulo_app.app)
    assert beta.post("/api/v2/entrar", json={"email": "leo@correo.co", "clave": r["clave_temporal_texto"]}
                     ).status_code == 200
    assert beta.get("/api/v2/cuenta").status_code == 200
    assert cli.post(f"/api/v2/admin/usuarios/{r['id']}/bloqueo", json={"bloqueado": True}).status_code == 200
    assert beta.get("/api/v2/cuenta").status_code == 401
    beta.cookies.clear()
    assert beta.post("/api/v2/entrar", json={"email": "leo@correo.co", "clave": r["clave_temporal_texto"]}
                     ).status_code == 403
    # la cuenta del dueño no se bloquea desde ahí
    yo = cli.get("/api/v2/cuenta").json()
    dueno = next(u for u in cli.get("/api/v2/admin/usuarios").json() if u["rol"] == "owner")
    assert yo["usuario"]["email"] == dueno["email"]
    assert cli.post(f"/api/v2/admin/usuarios/{dueno['id']}/bloqueo", json={"bloqueado": True}).status_code == 400


def test_cinco_intentos_fallidos_hacen_esperar(cli):
    _dueno_con_clave(cli)
    otro = TestClient(modulo_app.app)
    for _ in range(acceso.MAX_FALLOS):
        assert otro.post("/api/v2/entrar", json={"email": "dueno@xandart.co", "clave": "nop"}).status_code == 401
    r = otro.post("/api/v2/entrar", json={"email": "dueno@xandart.co", "clave": "clave-del-dueno"})
    assert r.status_code == 429 and "Espera" in r.json()["detail"]


def test_restablecer_desde_el_pc_sin_correo(cli):
    from estudio.restablecer_clave import restablecer

    _dueno_con_clave(cli)
    assert cli.get("/api/v2/cuenta").status_code == 200
    with pytest.raises(ValueError):
        restablecer("corta")
    assert restablecer("una-clave-nueva") == "dueno@xandart.co"
    acceso.olvidar_sesiones()
    assert cli.get("/api/v2/cuenta").status_code == 401          # la sesión vieja ya no sirve
    assert cli.post("/api/v2/entrar", json={"email": "dueno@xandart.co", "clave": "una-clave-nueva"}).status_code == 200


def test_galleta_falsa_o_vencida_no_sirve(cli, monkeypatch):
    _dueno_con_clave(cli)
    token = cli.cookies.get(acceso.GALLETA)
    cuerpo, firma = token.rsplit(".", 1)
    falso = TestClient(modulo_app.app)
    falso.cookies.set(acceso.GALLETA, cuerpo + "." + firma[::-1])
    assert falso.get("/api/v2/cuenta").status_code == 401
    import time

    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 31 * 86400)
    acceso.olvidar_sesiones()
    assert cli.get("/api/v2/cuenta").status_code == 401


def test_otra_pagina_no_puede_cambiar_nada(cli):
    _dueno_con_clave(cli)
    r = cli.post("/api/v2/salir", headers={"Origin": "https://pagina-mala.com"})
    assert r.status_code == 403
    assert cli.post("/api/apagar", headers={"Origin": "https://pagina-mala.com"}).status_code == 403


def test_contrasena_nunca_en_claro():
    h = acceso.hash_clave("secreta-123")
    assert "secreta" not in h and acceso.verificar_clave("secreta-123", h)
    assert not acceso.verificar_clave("secreta-124", h)
    t = acceso.hash_clave("x" * 9, temporal=True)
    assert acceso.es_temporal(t) and acceso.verificar_clave("x" * 9, t)


def test_la_cola_sigue_sola_al_abrir_sin_que_nadie_entre(monkeypatch):
    """La cola de la noche no depende de la página ni de la sesión: al abrir Xandart sigue sola."""
    import threading

    from estudio import cola, cola_api
    from estudio.plataforma import contexto, local

    vistos = []
    monkeypatch.setattr(cola_api, "_RECUPERADA", {"si": False})
    monkeypatch.setattr(local, "espacio", lambda esperar=True: "espacio-del-dueno")
    monkeypatch.setattr(cola, "recuperar", lambda: vistos.append(contexto.espacio_actual()))
    cola_api.recuperar_al_abrir()
    for h in threading.enumerate():
        if h.name == "cola-al-abrir":
            h.join(5)
    assert vistos == ["espacio-del-dueno"]
