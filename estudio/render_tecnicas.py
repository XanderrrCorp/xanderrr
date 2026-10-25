"""(24-10) Técnicas nuevas de Peligro Tropical v2, sacadas de las capturas de la competencia que mandó el dueño (solo la
técnica, con dibujo propio): la mano de caricatura que señala, el halo de luz detrás de un detalle, el detalle borroso
con «?» (misterio), los círculos de zoom con «?» y la tarjeta de mapa antiguo con nubes para hablar de historia.
Todo por código (Pillow), sin imágenes pagadas. Las llama render.py; las decide edicion.py / receta_pt.py."""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
_CACHE: dict = {}


def _r():
    from . import render as R

    return R


# ------------------------------------------------------------------ mano que señala

def _mano(tam: int) -> Image.Image:
    """Guante blanco de caricatura con el índice estirado hacia la derecha (contorno negro grueso)."""
    k = tam / 200
    im = Image.new("RGBA", (int(260 * k), int(200 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    trazo = max(3, int(9 * k))
    partes = [
        ("rr", (int(10 * k), int(60 * k), int(60 * k), int(150 * k)), int(14 * k)),        # puño de la manga
        ("rr", (int(50 * k), int(48 * k), int(160 * k), int(160 * k)), int(40 * k)),       # palma
        ("rr", (int(120 * k), int(62 * k), int(250 * k), int(98 * k)), int(18 * k)),       # índice estirado
        ("rr", (int(120 * k), int(98 * k), int(180 * k), int(128 * k)), int(15 * k)),      # dedos doblados
        ("rr", (int(118 * k), int(124 * k), int(172 * k), int(152 * k)), int(14 * k)),
        ("rr", (int(84 * k), int(20 * k), int(132 * k), int(70 * k)), int(22 * k)),        # pulgar arriba
    ]
    for _, caja, radio in partes:                     # primero todo en negro, más grueso: el contorno
        x0, y0, x1, y1 = caja
        d.rounded_rectangle((x0 - trazo, y0 - trazo, x1 + trazo, y1 + trazo), radius=radio + trazo, fill=(15, 15, 15, 255))
    for _, caja, radio in partes:
        d.rounded_rectangle(caja, radius=radio, fill=(255, 255, 255, 255))
    for y in (98, 124):                               # pliegues entre dedos
        d.line((int(128 * k), int(y * k), int(170 * k), int(y * k)), fill=(15, 15, 15, 255), width=max(2, trazo // 2))
    d.line((int(60 * k), int(52 * k), int(60 * k), int(156 * k)), fill=(15, 15, 15, 255), width=max(2, trazo // 2))
    return im


def mano(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    """Entra deslizándose desde un lado y queda señalando el detalle, con un vaivén corto (como «¡aquí!»)."""
    R = _r()
    loc = tt - ef["en"]
    if not ubic or loc < 0:
        return img
    x0, y0, x1, y1 = R._caja_px(ubic, ef["caja"])
    izq = ef.get("desde", "izquierda") == "izquierda"
    clave = ("mano", izq)
    if clave not in _CACHE:
        m = _mano(230)
        _CACHE[clave] = m if izq else m.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    m = _CACHE[clave]
    cy = (y0 + y1) / 2
    punta_x = (x0 - 10) if izq else (x1 + 10)
    entra = R._sale(loc / 0.3)
    vaiven = 14 * math.sin(loc * 9) * min(1.0, max(0.0, (loc - 0.3) / 0.2))
    x = (punta_x - m.width if izq else punta_x) + (-1 if izq else 1) * (1 - entra) * 260 + (vaiven if izq else -vaiven)
    y = cy - m.height * 0.40
    base = img.convert("RGBA")
    base.alpha_composite(m, (int(x), int(y)))
    return base.convert("RGB")


# ------------------------------------------------------------------ halo de luz detrás del detalle

def halo(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    """Un resplandor blanco suave alrededor del detalle y el resto un poco más oscuro (como un reflector)."""
    R = _r()
    loc = tt - ef["en"]
    if not ubic or loc < 0:
        return img
    x0, y0, x1, y1 = R._caja_px(ubic, ef["caja"])
    k = R._sale(loc / 0.45)
    clave = ("halo", int(x0), int(y0), int(x1), int(y1))
    if clave not in _CACHE:
        mascara = Image.new("L", (W, H), 0)
        rx, ry = (x1 - x0) * 0.75 + 40, (y1 - y0) * 0.75 + 40
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ImageDraw.Draw(mascara).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
        _CACHE[clave] = np.asarray(mascara.filter(ImageFilter.GaussianBlur(max(30, rx * 0.35))), np.float32)[..., None] / 255
    m = _CACHE[clave]
    a = np.asarray(img.convert("RGB"), np.float32)
    oscuro = a * (1 - 0.35 * k * (1 - m))                         # el resto baja un poco
    luz = 255 - (255 - oscuro) * (1 - 0.55 * k * m)              # «pantalla»: aclara sin quemar
    return Image.fromarray(np.clip(luz, 0, 255).astype("uint8"))


# ------------------------------------------------------------------ detalle borroso con «?»

def borroso(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    """El detalle queda borroso con un «?» blanco encima (misterio) y se aclara de golpe al final del corte."""
    R = _r()
    loc = tt - ef["en"]
    if not ubic or loc < 0:
        return img
    revela = ef["en"] + ef["dur"]
    nitidez = R._sale((tt - revela) / 0.18) if tt >= revela else 0.0
    if nitidez >= 1:
        return img
    x0, y0, x1, y1 = R._caja_px(ubic, ef["caja"])
    pad = 30
    caja = (max(0, int(x0 - pad)), max(0, int(y0 - pad)), min(W, int(x1 + pad)), min(H, int(y1 + pad)))
    if caja[2] - caja[0] < 10 or caja[3] - caja[1] < 10:
        return img
    base = img.convert("RGB")
    zona = base.crop(caja)
    radio = max(14, (caja[2] - caja[0]) // 12)
    borrosa = zona.filter(ImageFilter.GaussianBlur(radio))
    mascara = Image.new("L", zona.size, 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, zona.width - 1, zona.height - 1), fill=int(255 * (1 - nitidez)))
    mascara = mascara.filter(ImageFilter.GaussianBlur(pad // 2))
    base.paste(borrosa, caja[:2], mascara)
    tam = int(min(260, max(110, (caja[3] - caja[1]) * 0.6)))
    if ("?", tam) not in _CACHE:
        _CACHE[("?", tam)] = R._signo(tam, (255, 255, 255))
    s = _CACHE[("?", tam)]
    esc = R._sale(loc / 0.14) * (1 - nitidez) * (1 + 0.04 * math.sin(loc * 4))
    if esc > 0.05:
        si = s.resize((max(1, int(s.width * esc)), max(1, int(s.height * esc))), Image.Resampling.BICUBIC)
        b = base.convert("RGBA")
        b.alpha_composite(si, (int((caja[0] + caja[2]) / 2 - si.width / 2), int((caja[1] + caja[3]) / 2 - si.height / 2)))
        base = b.convert("RGB")
    return base


# ------------------------------------------------------------------ círculos de zoom con «?»

def circulos(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    """2 o 3 círculos con un pedazo de la imagen ampliado y un «?», unidos con una línea fina al lugar exacto;
    entran uno tras otro (como una ficha de investigación)."""
    R = _r()
    if not ubic or tt < ef["en"]:
        return img
    ox, oy, sw, sh = ubic
    base = img.convert("RGB")
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    radio = 118
    for k, (px, py, cx, cy) in enumerate(ef["puntos"]):
        loc = tt - ef["en"] - 0.18 * k
        if loc < 0:
            continue
        x, y = ox + px * sw, oy + py * sh
        lx, ly = cx * W, cy * H
        p = R._sale(loc / 0.2)
        d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 255, 255, 230))
        d.line((x, y, x + (lx - x) * p, y + (ly - y) * p), fill=(235, 235, 235, 230), width=4)
        esc = R._sale((loc - 0.12) / 0.16)
        if esc < 0.05:
            continue
        lado = 120
        zona = base.crop((int(x - lado / 2), int(y - lado / 2), int(x + lado / 2), int(y + lado / 2)))
        r = max(4, int(radio * esc))
        zona = zona.resize((2 * r, 2 * r), Image.Resampling.LANCZOS).convert("RGBA")
        mascara = Image.new("L", zona.size, 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        zona.putalpha(mascara)
        capa.alpha_composite(zona, (int(lx - r), int(ly - r)))
        d.ellipse((lx - r, ly - r, lx + r, ly + r), outline=(240, 240, 240, 255), width=6)
        tam = int(r * 0.9)
        if ("?c", tam) not in _CACHE:
            _CACHE[("?c", tam)] = R._signo(max(20, tam), (255, 255, 255))
        s = _CACHE[("?c", tam)]
        capa.alpha_composite(s, (int(lx - s.width / 2), int(ly - s.height / 2)))
    b = base.convert("RGBA")
    b.alpha_composite(capa)
    return b.convert("RGB")


def puntos_circulos(rng: random.Random, n: int = 3) -> list[list[float]]:
    """Dónde mirar (dentro de la imagen, cerca del centro) y dónde poner cada círculo (a los lados, sin tapar el
    centro ni los subtítulos)."""
    lugares = [(0.15, 0.30), (0.85, 0.30), (0.15, 0.66), (0.85, 0.66)]
    rng.shuffle(lugares)
    salida = []
    for k in range(n):
        cx, cy = lugares[k]
        px = rng.uniform(0.36, 0.48) if cx < 0.5 else rng.uniform(0.52, 0.64)
        py = rng.uniform(0.32, 0.48) if cy < 0.5 else rng.uniform(0.52, 0.66)
        salida.append([round(px, 3), round(py, 3), cx, cy])
    return salida


# ------------------------------------------------------------------ mapa antiguo con nubes (historia)

def _mapa_viejo(semilla: int) -> Image.Image:
    """Papel envejecido con el mapa del mundo en sepia (los mismos datos de geo/, dominio público) y manchas."""
    from .geo import mapa as G

    v = G.Vista(10.0, -12.0, 170.0)
    arr = G.base(v, colores={}).astype(np.float32)
    mar = (np.abs(arr - np.array(G.OCEANO, np.float32)).sum(axis=2, keepdims=True) < 40).astype(np.float32)
    borde = (np.abs(arr - np.array(G.BORDE, np.float32)).sum(axis=2, keepdims=True) < 90).astype(np.float32)
    rng = np.random.default_rng(semilla)
    ruido = np.asarray(Image.fromarray((rng.random((H // 24, W // 24)) * 255).astype("uint8")).resize(
        (W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(20)), np.float32)[..., None] / 255
    tierra = np.array([226, 206, 166], np.float32) * (0.88 + 0.12 * ruido)      # papel claro
    agua = np.array([196, 176, 140], np.float32) * (0.9 + 0.1 * ruido)          # papel más tostado
    tinta = np.array([110, 78, 44], np.float32)
    mezcla = tierra * (1 - mar) + agua * mar
    costa = np.asarray(Image.fromarray((mar[..., 0] * 255).astype("uint8")).filter(ImageFilter.FIND_EDGES)
                       .filter(ImageFilter.MaxFilter(3)), np.float32)[..., None] / 255
    linea = np.clip(costa + 0.6 * borde, 0, 1)
    mezcla = mezcla * (1 - linea) + tinta * linea
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    mezcla *= np.clip(1.08 - 0.45 * dist ** 2, 0.45, 1)[..., None]
    return Image.fromarray(np.clip(mezcla, 0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))


def _nubes(semilla: int) -> Image.Image:
    rng = random.Random(semilla)
    capa = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(capa)
    for _ in range(46):
        lado = rng.choice(["arriba", "abajo", "izq", "der"])
        x = rng.uniform(-100, W + 100) if lado in ("arriba", "abajo") else (rng.uniform(-150, 240) if lado == "izq"
                                                                          else rng.uniform(W - 240, W + 150))
        y = rng.uniform(-120, 200) if lado == "arriba" else (rng.uniform(H - 200, H + 120) if lado == "abajo"
                                                              else rng.uniform(-100, H + 100))
        r = rng.uniform(120, 300)
        d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=255)
    return capa.filter(ImageFilter.GaussianBlur(45))


def mapa_antiguo(ef: dict, loc: float) -> Image.Image:
    """Pantalla completa: el mapa viejo aparece mientras las nubes se abren hacia los bordes, la cámara se acerca
    despacio y la frase entra grande al centro (blanca con borde negro)."""
    R = _r()
    semilla = int(ef.get("semilla", 7))
    if ("mapa", semilla) not in _CACHE:
        _CACHE[("mapa", semilla)] = (_mapa_viejo(semilla), _nubes(semilla))
    fondo, nubes = _CACHE[("mapa", semilla)]
    zoom = 1.0 + 0.06 * min(1.0, loc / max(0.5, ef["dur"]))
    img = fondo.resize((int(W * zoom), int(H * zoom)), Image.Resampling.BILINEAR)
    img = img.crop(((img.width - W) // 2, (img.height - H) // 2, (img.width - W) // 2 + W, (img.height - H) // 2 + H))
    abre = 1.0 + 0.9 * R._sale(loc / 0.9)                      # las nubes se van hacia afuera
    n = nubes.resize((int(W * abre), int(H * abre)), Image.Resampling.BILINEAR)
    n = n.crop(((n.width - W) // 2, (n.height - H) // 2, (n.width - W) // 2 + W, (n.height - H) // 2 + H))
    cubre = Image.new("L", (W, H), int(255 * max(0.0, 1 - loc / 0.5)))
    alfa = Image.fromarray(np.maximum(np.asarray(n), np.asarray(cubre)))
    img = Image.composite(Image.new("RGB", (W, H), (250, 250, 248)), img, alfa)
    clave = ("frase", ef["texto"])
    if clave not in _CACHE:
        t = R._texto_img(ef["texto"], 120, 10)
        if t.width > W - 240:
            f = (W - 240) / t.width
            t = t.resize((int(t.width * f), int(t.height * f)), Image.Resampling.LANCZOS)
        _CACHE[clave] = t
    t = _CACHE[clave]
    esc = R._sale((loc - 0.35) / 0.2)
    if esc > 0.05:
        ti = t.resize((max(1, int(t.width * esc)), max(1, int(t.height * esc))), Image.Resampling.BICUBIC)
        b = img.convert("RGBA")
        b.alpha_composite(ti, (int((W - ti.width) / 2), int(H * 0.45 - ti.height / 2)))
        img = b.convert("RGB")
    return img
