"""Imágenes POR LOTES en Google Cloud (20-10, pedido del dueño: «imágenes en masa»).

Todas las escenas que faltan van a Google en UN solo pedido (batch prediction): no chocan con el límite de imágenes
por minuto y Google las cobra a mitad de precio, pero las entrega cuando puede (minutos u horas; promete máximo 24 h).
Necesita la cuenta de servicio (google_cloud.py) y un depósito de Cloud Storage propio, que se crea solo y borra lo
que tenga más de 7 días (para no pagar almacenamiento).

Es reanudable: el pedido queda en imagenes/lote.json; si Xandart se cierra, al volver se sigue esperando el mismo
lote en vez de mandarlo otra vez. Lo que llega se guarda en imagenes/lote/ antes de usarse. Si Google no acepta el
lote (modelo sin lotes, sin permisos…), se avisa y las imágenes se hacen de la forma normal.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import quote

from ..config import escribir_json, leer_json
from . import google_cloud
from .proveedores import ErrorProveedor, ResultadoImagen, Uso

DESCUENTO = 0.5                 # Google cobra los lotes a mitad de precio
ESPERA_SONDEO_S = 60.0
ESPERA_MAX_S = 26 * 3600        # promete 24 h; un margen y luego se sigue de la forma normal
DIAS_DEPOSITO = 7
STORAGE = "https://storage.googleapis.com/storage/v1"
SUBIR = "https://storage.googleapis.com/upload/storage/v1"
TERMINADOS = {"JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED",
              "JOB_STATE_EXPIRED"}
ESTADOS = {"JOB_STATE_QUEUED": "en fila", "JOB_STATE_PENDING": "esperando turno",
           "JOB_STATE_RUNNING": "haciéndolas", "JOB_STATE_SUCCEEDED": "listas"}
dormir = time.sleep
reloj = time.monotonic


class LoteNoDisponible(RuntimeError):
    """Google no aceptó el lote: las imágenes se hacen de la forma normal."""


def activado() -> bool:
    from ..config import clave_api

    return (clave_api("XANDART_IMAGENES_LOTES") or "").strip() == "1"


def disponible(proveedor) -> bool:
    return activado() and getattr(proveedor, "nombre", "") == "vertex" and google_cloud.leer() is not None


def huella(prompt: str) -> str:
    return hashlib.sha1(prompt.encode()).hexdigest()[:16]


def _texto(peticion: dict) -> str:
    partes = ((peticion.get("contents") or [{}])[0]).get("parts") or []
    return "".join(p.get("text", "") for p in partes if isinstance(p, dict))


def _host(ubicacion: str) -> str:
    return "aiplatform.googleapis.com" if ubicacion == "global" else f"{ubicacion}-aiplatform.googleapis.com"


def _deposito(sesion) -> str:
    """El depósito de Xandart en el proyecto (se crea la primera vez, con borrado a los 7 días)."""
    p = google_cloud.proyecto()
    base = re.sub(r"[^a-z0-9-]", "-", f"xandart-lotes-{p}".lower())[:56].strip("-")
    for nombre in (base, f"{base}-{hashlib.sha1(p.encode()).hexdigest()[:6]}"):
        r = sesion.get(f"{STORAGE}/b/{nombre}", headers=google_cloud.cabeceras(), timeout=30)
        if r.status_code == 200:
            return nombre
        if r.status_code == 404:
            r = sesion.post(f"{STORAGE}/b", params={"project": p}, headers=google_cloud.cabeceras(), timeout=30,
                            json={"name": nombre, "location": "US", "lifecycle": {"rule": [
                                {"action": {"type": "Delete"}, "condition": {"age": DIAS_DEPOSITO}}]}})
            if r.status_code in (200, 201):
                return nombre
            if r.status_code != 409:
                raise LoteNoDisponible(f"no se pudo crear el depósito de Cloud Storage (HTTP {r.status_code}: "
                                       f"{r.text[:200]})")
    raise LoteNoDisponible("no hay permiso para el depósito de Cloud Storage: dale a la cuenta de servicio el rol "
                           "«Administrador de almacenamiento»")


def _subir(sesion, deposito: str, objeto: str, datos: bytes) -> None:
    r = sesion.post(f"{SUBIR}/b/{deposito}/o", params={"uploadType": "media", "name": objeto},
                    headers={**google_cloud.cabeceras(), "Content-Type": "application/octet-stream"},
                    data=datos, timeout=600)
    if r.status_code not in (200, 201):
        raise LoteNoDisponible(f"no se pudo subir el lote (HTTP {r.status_code}: {r.text[:200]})")


def _crear(sesion, proveedor, cuerpos: list[dict], nombre: str) -> dict:
    deposito = _deposito(sesion)
    carpeta = f"lotes/{nombre}-{int(time.time())}"
    lineas = "\n".join(json.dumps({"request": c}) for c in cuerpos).encode()
    _subir(sesion, deposito, f"{carpeta}/entrada.jsonl", lineas)
    ultimo = ""
    for ubicacion in (google_cloud.UBICACION, "us-central1"):
        r = sesion.post(f"https://{_host(ubicacion)}/v1/projects/{google_cloud.proyecto()}/locations/{ubicacion}/"
                        "batchPredictionJobs", headers=google_cloud.cabeceras(), timeout=60, json={
                            "displayName": f"xandart-{nombre}"[:120],
                            "model": f"publishers/google/models/{proveedor.modelo}",
                            "inputConfig": {"instancesFormat": "jsonl",
                                            "gcsSource": {"uris": [f"gs://{deposito}/{carpeta}/entrada.jsonl"]}},
                            "outputConfig": {"predictionsFormat": "jsonl", "gcsDestination": {
                                "outputUriPrefix": f"gs://{deposito}/{carpeta}/salida"}}})
        if r.status_code == 200:
            return {"trabajo": r.json()["name"], "ubicacion": ubicacion, "deposito": deposito, "carpeta": carpeta}
        ultimo = f"HTTP {r.status_code}: {r.text[:300]}"
    raise LoteNoDisponible(f"Google no aceptó el lote ({ultimo})")


def _consultar(sesion, info: dict) -> dict:
    r = sesion.get(f"https://{_host(info['ubicacion'])}/v1/{info['trabajo']}", headers=google_cloud.cabeceras(),
                   timeout=60)
    if r.status_code != 200:
        raise ErrorProveedor(f"no se pudo ver el lote (HTTP {r.status_code})", reintentable=True)
    return r.json()


def _salidas(sesion, info: dict, trabajo: dict) -> list[dict]:
    """Las líneas de respuesta que dejó Google en el depósito."""
    destino = ((trabajo.get("outputInfo") or {}).get("gcsOutputDirectory") or
               f"gs://{info['deposito']}/{info['carpeta']}/salida")
    deposito, _, prefijo = destino.removeprefix("gs://").partition("/")
    r = sesion.get(f"{STORAGE}/b/{deposito}/o", params={"prefix": prefijo}, headers=google_cloud.cabeceras(),
                   timeout=60)
    r.raise_for_status()
    lineas = []
    for obj in r.json().get("items", []):
        if not obj["name"].endswith(".jsonl"):
            continue
        d = sesion.get(f"{STORAGE}/b/{deposito}/o/{quote(obj['name'], safe='')}", params={"alt": "media"},
                       headers=google_cloud.cabeceras(), timeout=600)
        d.raise_for_status()
        lineas += [json.loads(x) for x in d.text.splitlines() if x.strip()]
    return lineas


def hacer(carpeta: Path, proveedor, pedidos: list[tuple[str, list[Path]]], avisar=print, sesion=None,
          nombre: str = "video") -> int:
    """Manda en un lote los (prompt, referencias) y guarda lo que vuelva en imagenes/lote/. Devuelve cuántas
    llegaron. Lanza LoteNoDisponible si Google no lo acepta (el que llama sigue de la forma normal)."""
    import requests

    sesion = sesion or requests.Session()
    dir_lote = carpeta / "imagenes" / "lote"
    dir_lote.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "imagenes" / "lote.json"
    faltan = {huella(p): (p, refs) for p, refs in pedidos if not (dir_lote / f"{huella(p)}.png").exists()}
    if not faltan:
        return 0
    info = leer_json(ruta) if ruta.exists() else {}
    if not info.get("trabajo") or info.get("recogido") or not set(faltan) <= set(info.get("huellas", [])):
        cuerpos = [proveedor._cuerpo(p, refs) for p, refs in faltan.values()]
        try:
            info = {**_crear(sesion, proveedor, cuerpos, nombre), "huellas": sorted(faltan), "recogido": False}
        except requests.RequestException as ex:
            raise LoteNoDisponible(f"sin conexión con Google ({ex})") from ex
        escribir_json(ruta, info)
        avisar(f"Mandé {len(faltan)} imágenes a Google por lotes (mitad de precio). Google las entrega cuando "
               "puede: a veces minutos, a veces horas. Puedes dejar Xandart abierto y hacer otra cosa.")
    else:
        avisar(f"Sigo esperando el lote de {len(info['huellas'])} imágenes que ya estaba en Google…")
    inicio, estado = reloj(), ""
    while True:
        try:
            trabajo = _consultar(sesion, info)
        except (ErrorProveedor, requests.RequestException):
            trabajo = {"state": estado or "JOB_STATE_PENDING"}       # un tropiezo de red: se pregunta otra vez
        estado = trabajo.get("state", "")
        if estado in TERMINADOS:
            break
        minutos = int((reloj() - inicio) / 60)
        avisar(f"Google está haciendo las imágenes por lotes ({ESTADOS.get(estado, estado.lower())}) · "
               f"{minutos} min esperando")
        if reloj() - inicio > ESPERA_MAX_S:
            raise LoteNoDisponible("Google no entregó el lote a tiempo")
        dormir(ESPERA_SONDEO_S)
    if estado not in ("JOB_STATE_SUCCEEDED", "JOB_STATE_PARTIALLY_SUCCEEDED"):
        info["recogido"] = True
        escribir_json(ruta, info)
        error = (trabajo.get("error") or {}).get("message", "")
        raise LoteNoDisponible(f"el lote terminó sin imágenes ({estado.lower()}{': ' + error[:200] if error else ''})")
    por_texto = {p: h for h, (p, _) in faltan.items()}
    llegaron = 0
    for linea in _salidas(sesion, info, trabajo):
        h = por_texto.get(_texto(linea.get("request") or {}))
        if not h or not linea.get("response"):
            continue
        try:
            res = proveedor.desde_respuesta(linea["response"])
        except ErrorProveedor:
            continue                                    # esa no trajo imagen: se hace de la forma normal
        (dir_lote / f"{h}.png").write_bytes(res.png)
        escribir_json(dir_lote / f"{h}.json", {**res.uso.unidades(), "costo_usd": res.uso.costo_usd * DESCUENTO})
        llegaron += 1
    info["recogido"] = True
    escribir_json(ruta, info)
    avisar(f"Llegaron {llegaron} de {len(faltan)} imágenes del lote"
           + ("" if llegaron == len(faltan) else "; las demás se hacen de la forma normal"))
    return llegaron


class ConLote:
    """El proveedor de siempre, pero las imágenes que ya llegaron en el lote se entregan sin llamar a Google
    (con el costo del lote). Lo que no llegó va por el camino normal."""

    def __init__(self, proveedor, carpeta: Path):
        self.base, self.dir = proveedor, carpeta / "imagenes" / "lote"
        self.nombre, self.modelo = proveedor.nombre, proveedor.modelo

    def estimar_usd(self, prompt: str, referencias: list[Path]) -> float:
        if (self.dir / f"{huella(prompt)}.png").exists():
            return self.base.estimar_usd(prompt, referencias) * DESCUENTO
        return self.base.estimar_usd(prompt, referencias)

    def tiene(self, prompt: str) -> bool:
        return (self.dir / f"{huella(prompt)}.png").exists()

    def generar(self, prompt: str, referencias: list[Path]) -> ResultadoImagen:
        h = huella(prompt)
        png = self.dir / f"{h}.png"
        if not png.exists():
            return self.base.generar(prompt, referencias)
        u = leer_json(self.dir / f"{h}.json") if (self.dir / f"{h}.json").exists() else {}
        uso = Uso(int(u.get("tokens_entrada", 0)), int(u.get("tokens_entrada_imagen", 0)),
                  int(u.get("tokens_salida", 0)), float(u.get("costo_usd", 0.0)))
        datos = png.read_bytes()
        png.unlink()                   # se usa una vez: si la imagen no sirve, el reintento va por el camino normal
        return ResultadoImagen(datos, uso, self.modelo, self.nombre, {"lote": True})
