"""(Paso B) Inicio de sesión: contraseñas, la «galleta» de sesión y la puerta que revisa cada petición.

- Contraseñas: hash scrypt con sal (solo biblioteca estándar); nunca se guardan en claro. Una contraseña temporal
  (la que el dueño da a un beta) se marca con el prefijo «temporal:» y obliga a cambiarla al entrar.
- Sesión: galleta firmada con un secreto que se crea solo en este PC (datos/secreto_sesion.key, fuera del código).
  Lleva el usuario, el vencimiento y una huella de su contraseña: si la contraseña cambia, todas sus sesiones dejan de
  servir. «Recordarme» = 30 días; sin marcar, 12 horas y se borra al cerrar el navegador.
- La puerta (PuertaDeEntrada) solo protege la PÁGINA: los trabajos que ya corren (cola, render, avisos) siguen solos
  aunque se cierre el navegador o venza la sesión.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass
from urllib.parse import quote

from . import db

GALLETA = "xandart_sesion"
DIAS_RECORDAR = 30
HORAS_SIN_RECORDAR = 12
TEMPORAL = "temporal:"
MAX_FALLOS, VENTANA_FALLOS = 5, 15 * 60          # 5 intentos fallidos → 15 minutos de espera para ese correo
LARGO_MINIMO = 8

# Solo las pruebas lo prenden (desde código, nunca desde .env): la puerta deja pasar como si fuera el dueño
EN_PRUEBAS = {"como_dueno": False}


# ------------------------------------------------------------------ contraseñas

def hash_clave(clave: str, temporal: bool = False) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(clave.encode("utf-8"), salt=sal, n=2 ** 14, r=8, p=1, dklen=32)
    return (TEMPORAL if temporal else "") + f"scrypt$16384$8$1${sal.hex()}${h.hex()}"


def verificar_clave(clave: str, guardado: str | None) -> bool:
    if not guardado or not clave:
        return False
    try:
        _, n, r, p, sal, h = guardado.removeprefix(TEMPORAL).split("$")
        nuevo = hashlib.scrypt(clave.encode("utf-8"), salt=bytes.fromhex(sal), n=int(n), r=int(r), p=int(p),
                               dklen=len(bytes.fromhex(h)))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(nuevo.hex(), h)


def es_temporal(guardado: str | None) -> bool:
    return bool(guardado) and guardado.startswith(TEMPORAL)


def problema_clave(clave: str) -> str | None:
    """Por qué una contraseña nueva no sirve (en palabras simples), o None si sirve."""
    if len(clave or "") < LARGO_MINIMO:
        return f"La contraseña debe tener al menos {LARGO_MINIMO} caracteres."
    if clave.strip() != clave:
        return "La contraseña no puede empezar ni terminar con espacios."
    return None


def clave_temporal() -> str:
    """Fácil de dictar o copiar: sin letras que se confunden (0/O, 1/l)."""
    letras = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(letras) for _ in range(4)) for _ in range(3))


# ------------------------------------------------------------------ galleta firmada

def _secreto() -> bytes:
    ruta = db.carpeta_datos() / "secreto_sesion.key"
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(ruta, "x", encoding="utf-8") as f:       # «x»: si dos peticiones llegan a la vez, gana una
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    return bytes.fromhex(ruta.read_text(encoding="utf-8").strip())


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _desb64(t: str) -> bytes:
    return base64.urlsafe_b64decode(t + "=" * (-len(t) % 4))


def huella(clave_hash: str | None) -> str:
    return hashlib.sha256((clave_hash or "").encode()).hexdigest()[:16]


def crear_token(usuario_id: str, clave_hash: str | None, recordar: bool) -> str:
    vence = time.time() + (DIAS_RECORDAR * 86400 if recordar else HORAS_SIN_RECORDAR * 3600)
    cuerpo = _b64(json.dumps({"u": usuario_id, "h": huella(clave_hash), "v": int(vence)}).encode())
    firma = _b64(hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).digest())
    return f"{cuerpo}.{firma}"


def leer_token(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    cuerpo, firma = token.rsplit(".", 1)
    esperada = _b64(hmac.new(_secreto(), cuerpo.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(firma, esperada):
        return None
    try:
        datos = json.loads(_desb64(cuerpo))
    except (ValueError, json.JSONDecodeError):
        return None
    return datos if datos.get("v", 0) > time.time() else None


def poner_galleta(respuesta, token: str, recordar: bool) -> None:
    respuesta.set_cookie(GALLETA, token, max_age=DIAS_RECORDAR * 86400 if recordar else None, httponly=True,
                         samesite="strict", path="/")


def quitar_galleta(respuesta) -> None:
    respuesta.delete_cookie(GALLETA, path="/", samesite="strict", httponly=True)


# ------------------------------------------------------------------ intentos fallidos

_FALLOS: dict[str, list[float]] = {}
_CERROJO = threading.Lock()


def bloqueado_por_intentos(email: str) -> int:
    """Minutos que faltan para poder intentar otra vez (0 = puede)."""
    with _CERROJO:
        recientes = [t for t in _FALLOS.get(email, []) if t > time.time() - VENTANA_FALLOS]
        _FALLOS[email] = recientes
        if len(recientes) < MAX_FALLOS:
            return 0
        return max(1, int((recientes[0] + VENTANA_FALLOS - time.time()) // 60) + 1)


def anotar_fallo(email: str) -> None:
    with _CERROJO:
        _FALLOS.setdefault(email, []).append(time.time())


def olvidar_fallos(email: str) -> None:
    with _CERROJO:
        _FALLOS.pop(email, None)


# ------------------------------------------------------------------ quién hace la petición

@dataclass
class Conectado:
    usuario_id: str
    rol: str
    espacio_id: str | None


_actual: ContextVar[Conectado | None] = ContextVar("usuario_conectado", default=None)
_CACHE: dict[str, tuple[float, Conectado | None]] = {}
_CACHE_SEGUNDOS = 15          # un bloqueo o un cambio de contraseña se nota en la siguiente acción (máx. 15 s)


def conectado() -> Conectado | None:
    return _actual.get()


def olvidar_sesiones() -> None:
    """Tras bloquear a alguien o cambiar una contraseña: se revisa de nuevo en la próxima petición."""
    _CACHE.clear()


def _resolver(token: str) -> Conectado | None:
    ahora = time.time()
    guardado = _CACHE.get(token)
    if guardado and guardado[0] > ahora:
        return guardado[1]
    datos = leer_token(token)
    quien = None
    if datos:
        from .cuentas import espacio_de
        from .modelos import Usuario

        db.preparar()
        with db.sesion() as s:
            u = s.get(Usuario, datos["u"])
            if u and u.activo and not u.bloqueado and u.clave_hash and huella(u.clave_hash) == datos["h"]:
                e = espacio_de(s, u)
                quien = Conectado(u.id, u.rol, e.id if e else None)
                from datetime import datetime, timedelta, timezone

                ahora_dt = datetime.now(timezone.utc)
                ultima = u.ultima_actividad
                if ultima is not None and ultima.tzinfo is None:
                    ultima = ultima.replace(tzinfo=timezone.utc)
                if ultima is None or ahora_dt - ultima > timedelta(minutes=10):
                    u.ultima_actividad = ahora_dt
    if len(_CACHE) > 500:
        _CACHE.clear()
    _CACHE[token] = (ahora + _CACHE_SEGUNDOS, quien)
    return quien


def _quien_en_pruebas() -> Conectado:
    from .cuentas import cuenta_local
    from .modelos import ROL_OWNER

    db.preparar()
    with db.sesion() as s:
        u, e = cuenta_local(s)
        return Conectado(u.id, ROL_OWNER, e.id if e else None)


# ------------------------------------------------------------------ la puerta

# Sin sesión solo se puede: ver la página (sus archivos, sin datos), entrar y preguntar si hay sesión
_LIBRES_GET = ("/app", "/web/", "/favicon.ico")
_LIBRES_API = {"/api/v2/sesion", "/api/v2/entrar", "/api/v2/salir", "/api/v2/crear-clave-dueno", "/api/version"}
# mientras se hace la copia y se actualiza la base, la página puede mostrar el avance (sin datos de nadie)
_LIBRES_PREPARANDO = {"/api/v2/estado-local", "/api/v2/respaldo"}


def _libre(metodo: str, ruta: str, cabeceras: dict[bytes, bytes]) -> bool:
    if ruta in _LIBRES_API:
        return True
    if metodo in ("GET", "HEAD") and (ruta == "/app" or ruta.startswith("/app/") or ruta.startswith("/web/")
                                      or ruta == "/favicon.ico"):
        return True
    if ruta in _LIBRES_PREPARANDO and metodo == "GET" and db.PREPARANDO:
        return True
    # el acceso directo apaga un Xandart viejo antes de abrir el nuevo (sin navegador: sin cabecera Origin)
    if ruta == "/api/apagar" and metodo == "POST" and b"origin" not in cabeceras:
        return True
    return False


def _galleta(cabeceras: dict[bytes, bytes]) -> str | None:
    crudo = cabeceras.get(b"cookie", b"").decode("latin-1")
    for parte in crudo.split(";"):
        nombre, _, valor = parte.strip().partition("=")
        if nombre == GALLETA:
            return valor
    return None


def origen_ajeno(cabeceras: dict[bytes, bytes]) -> bool:
    """Una página de OTRO sitio intentando cambiar algo aquí (además de la galleta «strict»)."""
    origen = cabeceras.get(b"origin")
    if not origen:
        return False
    host = cabeceras.get(b"host", b"").decode("latin-1")
    o = origen.decode("latin-1")
    return o not in (f"http://{host}", f"https://{host}")


def desde_este_pc(scope) -> bool:
    """La petición viene de este mismo computador y no pasó por un túnel o proxy (que dejan esas cabeceras)."""
    cliente = (scope.get("client") or ("", 0))[0]
    if cliente not in ("127.0.0.1", "::1", "localhost", "testclient"):
        return False
    cab = {k.lower() for k, _ in scope.get("headers", [])}
    return not cab & {b"x-forwarded-for", b"forwarded", b"x-real-ip", b"cf-connecting-ip", b"x-forwarded-host"}


class PuertaDeEntrada:
    """Revisa la sesión en cada petición. Sin sesión: las llamadas reciben 401 («Inicia sesión») y las páginas
    viejas (/, /admin, archivos) llevan a la pantalla de entrar y luego vuelven a donde iban."""

    def __init__(self, siguiente):
        self.siguiente = siguiente

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.siguiente(scope, receive, send)
        from starlette.concurrency import run_in_threadpool
        from starlette.responses import JSONResponse, RedirectResponse

        metodo, ruta = scope["method"], scope["path"]
        cabeceras = dict(scope.get("headers", []))
        if metodo not in ("GET", "HEAD", "OPTIONS") and origen_ajeno(cabeceras):
            return await JSONResponse({"detail": "Petición rechazada."}, status_code=403)(scope, receive, send)
        if EN_PRUEBAS["como_dueno"]:
            quien = await run_in_threadpool(_quien_en_pruebas)
        else:
            token = _galleta(cabeceras)
            quien = await run_in_threadpool(_resolver, token) if token else None
        if quien is None and not _libre(metodo, ruta, cabeceras):
            if ruta.startswith("/api/") or metodo not in ("GET", "HEAD"):
                r = JSONResponse({"detail": "Inicia sesión para continuar."}, status_code=401)
            else:
                volver = ruta + (("?" + scope["query_string"].decode("latin-1")) if scope.get("query_string") else "")
                r = RedirectResponse(f"/app/entrar?volver={quote(volver, safe='')}", status_code=303)
            return await r(scope, receive, send)
        marca = _actual.set(quien)
        try:
            await self.siguiente(scope, receive, send)
        finally:
            _actual.reset(marca)
