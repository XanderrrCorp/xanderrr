"""Conexión «completa» con Google Cloud por cuenta de servicio (20-10, el dueño: 1 imagen cada 20 s con la clave).

Con la clave de API (modo exprés) Google da un cupo bajo y fijo. Con el archivo de la cuenta de servicio (un JSON que
el dueño baja de Google Cloud una vez) se entra como un proyecto normal: se siguen gastando los créditos del proyecto
y se puede usar la generación por LOTES (lotes.py). El archivo vive solo en el PC (credenciales_google.json en la
carpeta de Xandart, fuera del repositorio) y nunca se muestra entero.
"""
from __future__ import annotations

import calendar
import json
import threading
import time
from pathlib import Path

from ..config import RAIZ

ARCHIVO = "credenciales_google.json"
ALCANCE = "https://www.googleapis.com/auth/cloud-platform"
UBICACION = "global"           # los modelos de imagen nuevos están en «global»
CAMPOS = ("type", "project_id", "private_key", "client_email")


class SinCuentaServicio(RuntimeError):
    pass


def ruta() -> Path:
    return RAIZ / ARCHIVO


def leer() -> dict | None:
    r = ruta()
    if not r.exists():
        return None
    try:
        datos = json.loads(r.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return datos if validar(datos) is None else None


def validar(datos) -> str | None:
    """None si es un archivo de cuenta de servicio; si no, qué tiene de raro (en palabras del dueño)."""
    if not isinstance(datos, dict):
        return "Ese archivo no es el de la cuenta de servicio (debe ser un .json que bajaste de Google Cloud)."
    if datos.get("type") != "service_account" or any(not datos.get(c) for c in CAMPOS):
        return ("Ese .json no es una clave de cuenta de servicio. En Google Cloud: IAM → Cuentas de servicio → "
                "tu cuenta → Claves → Agregar clave → JSON.")
    return None


def guardar(contenido: bytes | str) -> dict:
    try:
        datos = json.loads(contenido)
    except ValueError:
        raise ValueError("Ese archivo no se pudo leer: debe ser el .json que bajaste de Google Cloud.") from None
    problema = validar(datos)
    if problema:
        raise ValueError(problema)
    ruta().write_text(json.dumps(datos), encoding="utf-8")
    _TOKEN.clear()
    return estado()


def borrar() -> None:
    ruta().unlink(missing_ok=True)
    _TOKEN.clear()


def estado() -> dict:
    d = leer()
    return {"conectada": bool(d), "proyecto": d["project_id"] if d else None,
            "cuenta": d["client_email"] if d else None}


def proyecto() -> str:
    d = leer()
    if not d:
        raise SinCuentaServicio("no hay archivo de cuenta de servicio de Google")
    return d["project_id"]


_TOKEN: dict = {}
_CANDADO = threading.Lock()


def token() -> str:
    """Token de acceso (dura ~1 h; se renueva solo unos minutos antes)."""
    with _CANDADO:
        if _TOKEN.get("valor") and _TOKEN.get("vence", 0) - time.time() > 300:
            return _TOKEN["valor"]
        d = leer()
        if not d:
            raise SinCuentaServicio("no hay archivo de cuenta de servicio de Google")
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        cred = service_account.Credentials.from_service_account_info(d, scopes=[ALCANCE])
        cred.refresh(Request())
        # google-auth da la hora de vencimiento en UTC sin zona
        vence = calendar.timegm(cred.expiry.timetuple()) if cred.expiry else time.time() + 3000
        _TOKEN.update(valor=cred.token, vence=vence)
        return cred.token


def cabeceras() -> dict:
    return {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}


def url_modelo(modelo: str, accion: str, ubicacion: str = UBICACION) -> str:
    host = "aiplatform.googleapis.com" if ubicacion == "global" else f"{ubicacion}-aiplatform.googleapis.com"
    return (f"https://{host}/v1/projects/{proyecto()}/locations/{ubicacion}/publishers/google/models/"
            f"{modelo}:{accion}")


def probar(modelo: str, sesion=None) -> dict:
    """Prueba gratis: cuenta los tokens de un «hola» con el modelo de imágenes (no genera nada)."""
    import requests

    sesion = sesion or requests
    try:
        r = sesion.post(url_modelo(modelo, "countTokens"), headers=cabeceras(),
                        json={"contents": [{"role": "user", "parts": [{"text": "hola"}]}]}, timeout=30)
    except SinCuentaServicio as ex:
        return {"ok": False, "detalle": str(ex)}
    except Exception as ex:  # noqa: BLE001 — el archivo no sirve (clave revocada, sin internet…)
        return {"ok": False, "detalle": f"Google no aceptó el archivo: {str(ex)[:200]}"}
    if r.status_code == 200:
        return {"ok": True, "detalle": f"funciona (proyecto {proyecto()}, modelo {modelo})"}
    if r.status_code in (401, 403):
        return {"ok": False, "detalle": ("La cuenta de servicio no tiene permiso (HTTP {0}). En Google Cloud → IAM, "
                                         "dale a esa cuenta los roles «Usuario de Vertex AI» (Vertex AI User) y «Administrador de "
                                         "almacenamiento».").format(r.status_code)}
    return {"ok": False, "detalle": f"Google respondió HTTP {r.status_code}: {r.text[:200]}"}
