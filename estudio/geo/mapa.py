"""Mapas dibujados por código (18-10, pedido del dueño): las IA de imagen dibujan mal fronteras y banderas, así que en
las escenas de mapa NO se usa ninguna IA. Fronteras de Natural Earth (dominio público) y banderas de flag-icons (MIT),
en estudio/geo/datos (ver preparar.py).

Proyección Miller (el mundo se ve «normal», sin los polos gigantes). Una «vista» es un rectángulo 16:9 en coordenadas
proyectadas: (cx, cy, ancho). Todo se dibuja con Pillow a doble tamaño y se reduce (bordes suaves).
"""
from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
DATOS = Path(__file__).parent / "datos"
OCEANO = (191, 227, 242)
TIERRA = (237, 230, 214)
BORDE = (74, 74, 74)
SENTIMIENTOS = {"very_friendly": (255, 111, 163), "normal": (61, 190, 107), "complicated": (242, 169, 59),
                "tension": (224, 69, 58)}
NOMBRE_SENTIMIENTO = {"very_friendly": "MUY AMIGOS", "normal": "NORMAL", "complicated": "COMPLICADO",
                      "tension": "TENSIÓN"}

# regiones para «zoom_region» y la etiqueta de región (lon0, lat0, lon1, lat1)
REGIONES = {
    "MUNDO": (-170, -56, 180, 80), "NORTEAMÉRICA": (-170, 12, -50, 75), "CENTROAMÉRICA Y CARIBE": (-118, 5, -58, 33),
    "SUDAMÉRICA": (-92, -56, -32, 14), "EUROPA": (-25, 34, 45, 71), "ASIA": (25, -10, 150, 60),
    "ÁFRICA": (-20, -36, 55, 38), "OCEANÍA": (110, -48, 180, 0), "MEDIO ORIENTE": (25, 12, 65, 42),
}


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower().strip())
                   if unicodedata.category(c) != "Mn").replace("-", " ")


@lru_cache(maxsize=1)
def paises() -> dict[str, dict]:
    return json.loads((DATOS / "paises.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _alias() -> dict[str, str]:
    """Código o nombre → clave del país (ADM0_A3)."""
    a: dict[str, str] = {}
    for clave, p in paises().items():
        for k in (p.get("a2"), p.get("iso3"), p["nombre"]):
            if k and _norm(k) not in a:
                a[_norm(k)] = clave
    for clave in paises():                       # la clave propia gana siempre
        a[_norm(clave)] = clave
    return a


def codigo(x) -> str | None:
    """«COL», «co», «Colombia» o «colombia» → «COL». None si no existe (no se dibuja a ciegas)."""
    if not x:
        return None
    return _alias().get(_norm(x))


def region(nombre) -> str | None:
    n = _norm(nombre or "")
    return next((r for r in REGIONES if _norm(r) == n), None)


# ------------------------------------------------------------------ proyección y vistas

def proyectar(lon: float, lat: float) -> tuple[float, float]:
    lat = max(-84.0, min(84.0, lat))
    y = 1.25 * math.log(math.tan(math.pi / 4 + 0.4 * math.radians(lat)))
    return lon, -math.degrees(y)                 # y hacia abajo, como la pantalla


@dataclass(frozen=True)
class Vista:
    cx: float
    cy: float
    ancho: float                                 # en unidades proyectadas (≈ grados de longitud)

    @property
    def escala(self) -> float:
        return W / self.ancho

    def a_px(self, lon: float, lat: float) -> tuple[float, float]:
        x, y = proyectar(lon, lat)
        return (x - self.cx) * self.escala + W / 2, (y - self.cy) * self.escala + H / 2

    def hacia(self, otra: "Vista", p: float) -> "Vista":
        """Interpolación suave (el ancho en escala logarítmica: el zoom se siente parejo)."""
        a = math.exp(math.log(self.ancho) + (math.log(otra.ancho) - math.log(self.ancho)) * p)
        return Vista(self.cx + (otra.cx - self.cx) * p, self.cy + (otra.cy - self.cy) * p, a)


def vista_caja(lon0, lat0, lon1, lat1, margen: float = 0.08) -> Vista:
    x0, y1 = proyectar(lon0, lat0)
    x1, y0 = proyectar(lon1, lat1)
    ancho = max(x1 - x0, (y1 - y0) * W / H) * (1 + 2 * margen)
    return Vista((x0 + x1) / 2, (y0 + y1) / 2, max(ancho, 6.0))


def vista_region(nombre: str) -> Vista:
    return vista_caja(*REGIONES.get(region(nombre) or "MUNDO", REGIONES["MUNDO"]))


def vista_paises(*claves: str, minimo: float = 22.0) -> Vista:
    """Encuadra uno o varios países con aire alrededor (se ven los vecinos)."""
    cajas = [paises()[c]["caja"] for c in claves if c in paises()]
    if not cajas:
        return vista_region("MUNDO")
    lon0, lat0 = min(c[0] for c in cajas), min(c[1] for c in cajas)
    lon1, lat1 = max(c[2] for c in cajas), max(c[3] for c in cajas)
    if lon1 - lon0 > 180:                        # países que cruzan el antimeridiano (Rusia, EE. UU.): su etiqueta
        lx, ly = paises()[claves[0]]["etiqueta"]
        lon0, lon1, lat0, lat1 = lx - 40, lx + 40, ly - 20, ly + 20
    v = vista_caja(lon0, lat0, lon1, lat1, margen=0.35)
    return Vista(v.cx, v.cy, max(v.ancho, minimo))


# ------------------------------------------------------------------ dibujo

def _anillos_px(clave: str, v: Vista, k: float = 1.0):
    for anillo in paises()[clave]["anillos"]:
        pts = [v.a_px(x, y) for x, y in anillo]
        xs = [p[0] for p in pts]
        if max(xs) < -50 or min(xs) > W + 50:
            continue
        yield [(x * k, y * k) for x, y in pts]


FUERA = {"ATA", "ATF"}                           # la Antártida y las islas australes no se dibujan (estorban abajo)


def _visible(clave: str, v: Vista) -> bool:
    if clave in FUERA:
        return False
    lon0, lat0, lon1, lat1 = paises()[clave]["caja"]
    x0, y1 = v.a_px(lon0, lat0)
    x1, y0 = v.a_px(lon1, lat1)
    return x1 > -100 and x0 < W + 100 and y1 > -100 and y0 < H + 100


def mascara(clave: str, v: Vista) -> np.ndarray:
    """Máscara 0-255 del país en la vista (para resaltar, brillar y la bandera recortada)."""
    k = 2
    im = Image.new("L", (W * k, H * k), 0)
    d = ImageDraw.Draw(im)
    for pts in _anillos_px(clave, v, k):
        d.polygon(pts, fill=255)
    return np.asarray(im.resize((W, H), Image.Resampling.LANCZOS))


def base(v: Vista, colores: dict[str, tuple] | None = None) -> np.ndarray:
    """Mapa plano: océano, tierra crema con sombra suave y fronteras finas; `colores` pinta países ya clasificados.
    Devuelve RGB."""
    colores = colores or {}
    k = 2
    sombra = Image.new("L", (W * k, H * k), 0)
    ds = ImageDraw.Draw(sombra)
    tierra = Image.new("RGB", (W * k, H * k), OCEANO)
    dt = ImageDraw.Draw(tierra)
    visibles = [c for c in paises() if _visible(c, v)]
    for c in visibles:
        for pts in _anillos_px(c, v, k):
            ds.polygon([(x + 10, y + 14) for x, y in pts], fill=110)
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    tierra.paste(Image.new("RGB", tierra.size, (60, 90, 110)), (0, 0), sombra.point(lambda a: int(a * 0.5)))
    ancho = max(2, int(round(1.4 * k)))
    for c in visibles:
        relleno = colores.get(c, TIERRA)
        for pts in _anillos_px(c, v, k):
            dt.polygon(pts, fill=relleno, outline=BORDE, width=ancho)
    return np.asarray(tierra.resize((W, H), Image.Resampling.LANCZOS))


@lru_cache(maxsize=64)
def bandera(clave: str, alto: int) -> Image.Image | None:
    """La bandera real (flag-icons) en RGBA, 4:3, con esquinas un poco redondeadas."""
    a2 = (paises().get(clave) or {}).get("a2")
    ruta = DATOS / "banderas" / f"{(a2 or '').lower()}.svg"
    if not a2 or not ruta.exists():
        return None
    import io

    import resvg_py

    ancho = int(alto * 4 / 3)
    svg = ruta.read_text(encoding="utf-8")
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=ancho, height=alto))
    im = Image.open(io.BytesIO(png)).convert("RGBA").resize((ancho, alto))
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, ancho - 1, alto - 1), radius=max(4, alto // 12), fill=255)
    im.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel("A")), np.asarray(m))))
    return im


def nombre(clave: str) -> str:
    return paises()[clave]["nombre"]


def etiqueta_px(clave: str, v: Vista) -> tuple[float, float]:
    return v.a_px(*paises()[clave]["etiqueta"])
