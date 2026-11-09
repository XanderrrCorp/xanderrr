"""QR de compra en la venta del infoproducto (09-11, pedido del dueño: «cuando salga la venta del infoproducto pon un QR que
dirija al link de compra, para las que ven en TV»).

- El link y el nombre del producto se guardan UNA vez en datos/codigo_exito/venta.json (página Código del Éxito).
- Un bloque es «de venta» si nombra el producto (p. ej. «MI VALOR»), si su nota del guion dice VENTA o QR, o si habla
  claramente de comprar/inscribirse/el link. Ahí sale el QR abajo a la derecha (encima de los subtítulos no; al lado),
  al menos 8 s, con «Escanea con tu celular».
- El QR se hace por código (segno), sin servicios de afuera.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

MIN_S = 8.0
VENTA = re.compile(r"\b(link|enlace)s?\b.{0,30}\b(descripcion|comentario|abajo|pantalla)\b|\binscribete\b|\binscribirte\b|"
                   r"\bcompra(r|lo|la)?\b|\bprecio\b|\boferta\b|\bdescuento\b|\bacceso inmediato\b|\bunete\b.{0,40}\bprograma\b|"
                   r"\bescanea\b|\bcodigo qr\b")


def _plano(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def archivo() -> Path:
    from ..plataforma.db import carpeta_datos

    return carpeta_datos() / "codigo_exito" / "venta.json"


def leer() -> dict:
    try:
        d = json.loads(archivo().read_text("utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"link": str(d.get("link") or "").strip(), "producto": str(d.get("producto") or "").strip(),
            "texto": str(d.get("texto") or "Escanea con tu celular").strip()}


def guardar(link: str, producto: str = "", texto: str = "") -> dict:
    link = (link or "").strip()
    if link and not re.match(r"^https?://\S+\.\S+", link):
        raise ValueError("El link tiene que empezar por https:// (cópialo tal cual de la página de compra)")
    d = {"link": link, "producto": (producto or "").strip(), "texto": (texto or "").strip() or "Escanea con tu celular"}
    archivo().parent.mkdir(parents=True, exist_ok=True)
    archivo().write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    return d


def es_venta(b: dict, producto: str = "") -> bool:
    texto = _plano(b.get("texto", ""))
    nota = _plano(" ".join(str(b.get(k) or "") for k in ("nota", "texto_pantalla")))
    if re.search(r"\b(venta|qr)\b", nota):
        return True
    p = _plano(producto)
    if p and len(p) >= 3 and re.search(rf"\b{re.escape(p)}\b", texto):
        return True
    return bool(VENTA.search(texto))


def tramos(bloques: list[dict], cfg: dict | None = None) -> list[tuple[float, float]]:
    """(inicio, fin) en segundos del video donde va el QR (bloques de venta seguidos se unen)"""
    cfg = cfg or leer()
    if not cfg.get("link"):
        return []
    salida: list[list[float]] = []
    for b in bloques:
        if "inicio" not in b or not es_venta(b, cfg.get("producto", "")):
            continue
        a, z = float(b["inicio"]), float(b["inicio"]) + float(b.get("ranura", b.get("dur", 0)))
        if salida and a - salida[-1][1] < 1.0:
            salida[-1][1] = max(salida[-1][1], z)
        else:
            salida.append([a, z])
    return [(a, max(z, a + MIN_S)) for a, z in salida]


def imagen(link: str, destino: Path) -> Path:
    """PNG del QR (negro sobre blanco, con su margen) — se reusa mientras el link no cambie"""
    import segno

    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        segno.make(link, error="l", boost_error=False).save(str(destino), scale=12, border=2, dark="#111111", light="#ffffff")
    return destino
