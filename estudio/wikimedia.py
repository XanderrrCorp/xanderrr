"""Fotos REALES de Wikimedia Commons (20-10, pedido del dueño: «Pexels me falla mucho»). Gratis, sin clave.

Commons tiene millones de fotos de animales, anatomía, lugares, historia y ciencia (las de la NASA, por ejemplo).
Va junto a Pexels: sus candidatas entran en la MISMA hoja de contacto y pasan por la misma revisión de Claude.
Solo se aceptan licencias libres que permiten uso comercial (dominio público, CC0, CC BY, CC BY-SA); el autor y la
licencia de cada foto quedan en los créditos, que hay que poner en la descripción del video (CC BY lo exige).
"""
from __future__ import annotations

import re

import requests

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia pide identificarse; sin correo ni datos privados (el repositorio es público)
CABECERAS = {"User-Agent": "Xandart/1.0 (https://github.com/xanderrrcorp/xanderrr)"}
ANCHO_MIN = 800
ANCHO_DESCARGA, ANCHO_MINIATURA = 1920, 330
LICENCIAS_OK = ("public domain", "pd", "cc0", "cc by", "cc-by", "cc by-sa", "cc-by-sa")


def _texto(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()


def licencia_ok(nombre: str) -> bool:
    n = nombre.strip().lower()
    return n.startswith(LICENCIAS_OK) and not re.search(r"\b(nc|nd)\b", n)


def _miniatura(url: str) -> str:
    """La miniatura de la hoja de contacto: la misma imagen en chico (Commons arma la URL con el ancho)."""
    return re.sub(r"/\d+px-", f"/{ANCHO_MINIATURA}px-", url, count=1)


def buscar(consulta: str, sesion=requests, cuantas: int = 6) -> list[dict]:
    """Fotos de Commons para una búsqueda, en el mismo formato que stock.buscar (tipo «foto»). Si Commons no
    responde, lista vacía: nunca frena el video."""
    try:
        r = sesion.get(API, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"{consulta} filetype:bitmap", "gsrlimit": cuantas * 2, "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata", "iiurlwidth": ANCHO_DESCARGA,
            "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription"}, headers=CABECERAS, timeout=30)
        r.raise_for_status()
        paginas = sorted((r.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    except Exception:  # noqa: BLE001
        return []
    salida = []
    for p in paginas:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licencia = _texto((meta.get("LicenseShortName") or {}).get("value", ""))
        if (info.get("mime") not in ("image/jpeg", "image/png") or int(info.get("width") or 0) < ANCHO_MIN
                or not licencia_ok(licencia)):
            continue
        descarga = info.get("thumburl") or info.get("url")
        if not descarga:
            continue
        salida.append({"tipo": "foto", "fuente": "wikimedia", "pexels_id": None, "wikimedia_id": p.get("pageid"),
                       "url_origen": info.get("descriptionurl") or "",
                       "autor": _texto((meta.get("Artist") or {}).get("value", ""))[:120] or "autor desconocido",
                       "autor_url": "", "miniatura": _miniatura(descarga), "descarga": descarga,
                       "descripcion": _texto((meta.get("ImageDescription") or {}).get("value", ""))[:200],
                       "licencia": f"{licencia} (Wikimedia Commons)"})
        if len(salida) >= cuantas:
            break
    return salida


def credito(c: dict) -> str:
    """Línea de crédito para la descripción del video, según de dónde salió la foto."""
    if c.get("fuente") == "wikimedia":
        return f"Foto de {c['autor']}, {c.get('licencia', '')}: {c['url_origen']}"
    return f"{c['tipo'].capitalize()} de {c['autor']} en Pexels: {c['url_origen']}"
