"""QR de compra en la venta del infoproducto (09-11, pedido del dueño: «cuando salga la venta del infoproducto pon un QR que
dirija al link de compra, para las que ven en TV»).

- Los programas (nombre + link: MI VALOR, MI CÓDIGO…) se guardan UNA vez en datos/codigo_exito/venta.json (página Código
  del Éxito); cada momento de venta muestra el QR del programa que se nombra.
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
    """{"productos": [{"producto", "link"}], "texto"} — (10-11) varios programas (MI VALOR, MI CÓDIGO…), cada uno con su
    link; lo guardado antes con un solo link se lee igual"""
    try:
        d = json.loads(archivo().read_text("utf-8"))
    except (OSError, ValueError):
        d = {}
    productos = d.get("productos")
    if not isinstance(productos, list):
        productos = [{"producto": d.get("producto") or "", "link": d.get("link") or ""}] if d.get("link") else []
    productos = [{"producto": str(p.get("producto") or "").strip(), "link": str(p.get("link") or "").strip()}
                 for p in productos if isinstance(p, dict)]
    return {"productos": [p for p in productos if p["link"] or p["producto"]],
            "texto": str(d.get("texto") or "Escanea con tu celular").strip()}


def guardar(productos: list[dict], texto: str = "") -> dict:
    limpios = []
    for p in productos:
        link, nombre = str(p.get("link") or "").strip(), str(p.get("producto") or "").strip()
        if not link and not nombre:
            continue
        if link and not re.match(r"^https?://\S+\.\S+", link):
            raise ValueError(f"El link de {nombre or 'tu programa'} tiene que empezar por https:// "
                             "(cópialo tal cual de la página de compra)")
        limpios.append({"producto": nombre, "link": link})
    d = {"productos": limpios, "texto": (texto or "").strip() or "Escanea con tu celular"}
    archivo().parent.mkdir(parents=True, exist_ok=True)
    archivo().write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    return d


def _nombrado(texto: str, productos: list[dict]) -> dict | None:
    """el programa que nombra este texto (el que aparece primero)"""
    t = _plano(texto)
    hallados = []
    for p in productos:
        n = _plano(p["producto"])
        m = re.search(rf"\b{re.escape(n)}\b", t) if len(n) >= 3 else None
        if m:
            hallados.append((m.start(), p))
    return min(hallados, key=lambda x: x[0])[1] if hallados else None


def es_venta(b: dict, productos: list[dict] | None = None) -> bool:
    texto = _plano(b.get("texto", ""))
    nota = _plano(" ".join(str(b.get(k) or "") for k in ("nota", "texto_pantalla")))
    if re.search(r"\b(venta|qr)\b", nota):
        return True
    if productos and _nombrado(texto, productos):
        return True
    return bool(VENTA.search(texto))


def tramos(bloques: list[dict], cfg: dict | None = None) -> list[tuple[float, float, str]]:
    """(inicio, fin, link) en segundos del video donde va el QR. Cada bloque de venta lleva el link del programa que
    nombra; si no nombra ninguno, el último nombrado en el video (o el primero guardado). Seguidos y con el mismo link
    se unen; cada tramo dura al menos MIN_S."""
    cfg = cfg or leer()
    productos = [p for p in cfg.get("productos", []) if p.get("link")]
    if not productos:
        return []
    salida: list[list] = []
    ultimo = productos[0]
    for b in bloques:
        if "inicio" not in b:
            continue
        nombrado = _nombrado(b.get("texto", "") + " " + str(b.get("texto_pantalla") or ""), productos)
        if nombrado:
            ultimo = nombrado
        if not es_venta(b, productos):
            continue
        link = (nombrado or ultimo)["link"]
        a, z = float(b["inicio"]), float(b["inicio"]) + float(b.get("ranura", b.get("dur", 0)))
        if salida and a - salida[-1][1] < 1.0 and salida[-1][2] == link:
            salida[-1][1] = max(salida[-1][1], z)
        else:
            salida.append([a, z, link])
    return [(a, max(z, a + MIN_S), l) for a, z, l in salida]


def imagen(link: str, destino: Path) -> Path:
    """PNG del QR (negro sobre blanco, con su margen) — se reusa mientras el link no cambie"""
    import segno

    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        segno.make(link, error="l", boost_error=False).save(str(destino), scale=12, border=2, dark="#111111", light="#ffffff")
    return destino
