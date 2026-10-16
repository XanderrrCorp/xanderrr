"""Lo que dibuja la receta de Peligro Tropical (ver receta_pt.py): fondo negro con humo, tarjeta de veredicto,
«PERO ESPERA», destello blanco, llamados a la acción, la mascota del cierre y los subtítulos con la palabra activa
en amarillo. Todo hecho con código (Pillow), sin imágenes pagadas."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
AMARILLO = (255, 214, 0)
_CACHE: dict = {}


def _r():
    from . import render as R

    return R


def papel_oscuro(w: int = W, h: int = H, semilla: int = 7) -> Image.Image:
    """Fondo casi negro con humo gris que se mueve poco y viñeta fuerte (niveles altos)."""
    rng = np.random.default_rng(semilla)
    capa = np.zeros((h, w), np.float32)
    for escala, peso in ((180, 0.6), (70, 0.3), (24, 0.1)):
        ruido = rng.random((max(2, h // escala), max(2, w // escala))).astype(np.float32)
        im = Image.fromarray((ruido * 255).astype("uint8")).resize((w, h), Image.Resampling.BICUBIC)
        capa += np.asarray(im.filter(ImageFilter.GaussianBlur(escala / 3)), np.float32) / 255 * peso
    humo = np.clip((capa - 0.45) * 1.8, 0, 1) ** 1.4
    base = np.array([18, 18, 22], np.float32) + humo[..., None] * np.array([70, 70, 76], np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    base *= np.clip(1.05 - 0.55 * d ** 1.5, 0.2, 1)[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "RGB")


def vineta_fuerte(img: Image.Image) -> Image.Image:
    if "vineta" not in _CACHE:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        _CACHE["vineta"] = np.clip(1 - 0.75 * np.clip(d - 0.35, 0, 1) ** 1.3, 0.15, 1)[..., None] * 0.92
    return Image.fromarray((np.asarray(img.convert("RGB"), np.float32) * _CACHE["vineta"]).astype("uint8"))


def _oscurecer(img: Image.Image, k: float) -> Image.Image:
    return Image.blend(img.convert("RGB"), Image.new("RGB", img.size, (0, 0, 0)), max(0.0, min(1.0, k)))


def _pegar(img: Image.Image, capa: Image.Image, cx: float, cy: float, esc: float = 1.0) -> Image.Image:
    if esc < 0.03:
        return img
    if abs(esc - 1) > 0.004:
        capa = capa.resize((max(1, int(capa.width * esc)), max(1, int(capa.height * esc))), Image.Resampling.BICUBIC)
    base = img.convert("RGBA")
    base.alpha_composite(capa, (int(cx - capa.width / 2), int(cy - capa.height / 2)))
    return base.convert("RGB")


def _rebote(loc: float, dur: float = 0.5, sobre: float = 0.2) -> float:
    """De 0 a 1 pasándose un poco (pop que se asienta)."""
    if loc <= 0:
        return 0.0
    p = min(1.0, loc / dur)
    return (1 - (1 - p) ** 3) * (1 + sobre * math.exp(-loc * 8) * math.cos(loc * 14))


# ------------------------------------------------------------------ veredicto

def _tarjeta_veredicto(texto: str, leve: bool) -> Image.Image:
    R = _r()
    w, h = 1250, 380
    im = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((38, 44, w + 38, h + 44), radius=40, fill=(0, 0, 0, 110))
    im = im.filter(ImageFilter.GaussianBlur(10))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, w + 20, h + 20), radius=40, fill=(255, 255, 255, 255))
    arriba = R._texto_img("Nivel de amenaza", 64, 0, color=(110, 110, 118))
    im.alpha_composite(arriba, (20 + (w - arriba.width) // 2, 60))
    color = (40, 160, 70) if leve else (220, 30, 30)
    grande = R._texto_img(texto.upper(), 150, 0, color=color)
    icono = R._icono_si_no(150, leve)
    cabe = w - 120 - icono.width - 40                                   # que quepa en la tarjeta
    if grande.width > cabe:
        f = cabe / grande.width
        grande = grande.resize((int(grande.width * f), int(grande.height * f)), Image.Resampling.LANCZOS)
    total = grande.width + 40 + icono.width
    x0 = 20 + (w - total) // 2
    im.alpha_composite(grande, (x0, 170))
    im.alpha_composite(icono, (x0 + grande.width + 40, 170 + (grande.height - icono.height) // 2))
    return im


def veredicto(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    clave = ("ver", ef["texto"], ef["leve"])
    if clave not in _CACHE:
        _CACHE[clave] = _tarjeta_veredicto(ef["texto"], ef["leve"])
    # se aleja un poco la imagen y se oscurece con viñeta; la tarjeta salta desde el centro
    k = min(1.0, loc / 0.3)
    fondo = vineta_fuerte(_oscurecer(img, 0.45 * k)) if k > 0.05 else img
    return _pegar(fondo, _CACHE[clave], W / 2, H * 0.46, _rebote(loc, 0.5, 0.18))


# ------------------------------------------------------------------ pero espera

def pero_espera(img: Image.Image, ef: dict, loc: float, cuadro: int) -> Image.Image:
    R = _r()
    if "pe" not in _CACHE:
        _CACHE["pe"] = R._texto_img("PERO ESPERA...", 170, 14)
        _CACHE["tri"] = R._icono_advertencia(230)
    texto, tri = _CACHE["pe"], _CACHE["tri"]
    p = min(1.0, loc / max(0.3, ef["dur"]))
    fondo = vineta_fuerte(_oscurecer(img, 0.55 * min(1.0, loc / 0.2)))
    esc = _rebote(loc, 0.25, 0.25) * (0.88 + 0.3 * p)               # crece mientras dura
    fondo = _pegar(fondo, texto, W / 2, H * 0.58, esc)
    vibra = (4 if cuadro % 2 else -4) if loc > 0.1 else 0           # el triángulo vibra
    return _pegar(fondo, tri, W / 2 + vibra, H * 0.28 + (-vibra if cuadro % 4 < 2 else vibra) / 2,
                  _rebote(loc - 0.08, 0.3, 0.3))


def destello_blanco(img: Image.Image, dt: float) -> Image.Image:
    if 0 <= dt < 0.45:
        return Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), 0.75 * math.exp(-dt * 8))
    return img


# ------------------------------------------------------------------ llamados a la acción

def _pose(raiz: Path, archivo: str | None, alto: int) -> Image.Image | None:
    """La pose de la mascota recortada (vienen sobre fondo liso) a cierto alto."""
    if not archivo or not (raiz / archivo).exists():
        return None
    from .tira import quitar_fondo_liso

    im = quitar_fondo_liso(Image.open(raiz / archivo).convert("RGB"))
    caja = im.getbbox()
    if caja:
        im = im.crop(caja)
    k = alto / im.height
    return im.resize((max(1, int(im.width * k)), alto), Image.Resampling.LANCZOS)


def _pulgar(tam: int) -> Image.Image:
    """Botón de like dibujado: círculo azul con un pulgar blanco."""
    k = 4
    s = tam * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, s - 1, s - 1), fill=(36, 112, 230, 255), outline=(255, 255, 255, 255), width=10 * k)
    u = s / 100
    d.rounded_rectangle((24 * u, 46 * u, 36 * u, 76 * u), radius=3 * u, fill=(255, 255, 255, 255))     # puño
    d.rounded_rectangle((40 * u, 44 * u, 74 * u, 76 * u), radius=8 * u, fill=(255, 255, 255, 255))
    d.polygon([(40 * u, 48 * u), (52 * u, 24 * u), (60 * u, 26 * u), (58 * u, 46 * u)], fill=(255, 255, 255, 255))
    return im.resize((tam, tam), Image.Resampling.LANCZOS)


def cta_like(img: Image.Image, raiz: Path, ef: dict, loc: float) -> Image.Image:
    R = _r()
    clave = ("like", ef.get("pose"), ef["texto"])
    if clave not in _CACHE:
        pose = _pose(raiz, ef.get("pose"), 430)
        _CACHE[clave] = (pose, R._etiqueta_img(ef["texto"]), _pulgar(170))
    pose, etiqueta, pulgar = _CACHE[clave]
    sale = max(0.0, min(1.0, (ef["dur"] - loc) / 0.25))
    if pose is not None:
        salto = abs(math.sin(loc * 7)) * 40 * math.exp(-loc * 1.2)
        y = H - pose.height / 2 + 20 + (1 - _rebote(loc, 0.35, 0.1)) * 500 + (1 - sale) * 500 - salto
        img = _pegar(img, pose, 260, y)
    img = _pegar(img, etiqueta, W * 0.5, H * 0.17, _rebote(loc - 0.25, 0.3) * sale)
    return _pegar(img, pulgar, W * 0.5 + etiqueta.width / 2 + 110, H * 0.17, _rebote(loc - 0.45, 0.3, 0.35) * sale)


def _boton_suscribir(suscrito: bool) -> Image.Image:
    R = _r()
    texto = R._texto_img("SUSCRITO" if suscrito else "SUSCRÍBETE", 56, 0, color=(255, 255, 255))
    w, h = texto.width + 90, texto.height + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2,
                                         fill=(120, 120, 126, 255) if suscrito else (230, 30, 30, 255))
    im.alpha_composite(texto, ((w - texto.width) // 2, (h - texto.height) // 2))
    return im


def cta_suscribir(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    suscrito = loc > ef["dur"] * 0.55
    clave = ("sus", suscrito)
    if clave not in _CACHE:
        _CACHE[clave] = _boton_suscribir(suscrito)
    b = _CACHE[clave]
    entra = 1 - (1 - min(1.0, loc / 0.3)) ** 3
    sale = max(0.0, min(1.0, (ef["dur"] - loc) / 0.3))
    x = -b.width / 2 + (60 + b.width) * entra * sale
    pulso = 1 + (0.12 * math.exp(-(loc - ef["dur"] * 0.55) * 10) if suscrito else 0)
    return _pegar(img, b, x, H - 270, pulso)


# ------------------------------------------------------------------ cierre

def final_personaje(raiz: Path, ef: dict, loc: float) -> Image.Image:
    if "oscuro" not in _CACHE:
        _CACHE["oscuro"] = papel_oscuro()
    img = _CACHE["oscuro"]
    clave = ("final", ef.get("pose"))
    if clave not in _CACHE:
        _CACHE[clave] = _pose(raiz, ef.get("pose"), 780)
    pose = _CACHE[clave]
    if pose is None:
        return img.copy()
    y = H - pose.height / 2 + 40 + (1 - _rebote(loc, 0.45, 0.08)) * 700 + math.sin(loc * 2.2) * 8
    return _pegar(img, pose, W / 2, y)


# ------------------------------------------------------------------ subtítulos

def subtitulo(sb: dict, tt: float) -> Image.Image:
    """1 a 3 palabras, blancas con borde negro; la que se está diciendo, en amarillo."""
    R = _r()
    activa = next((k for k, (_, a, b) in enumerate(sb["palabras"]) if a <= tt < b), len(sb["palabras"]) - 1)
    clave = ("sub", sb["texto"], activa)
    if clave not in _CACHE:
        partes = [R._texto_img(p, 74, 9, color=AMARILLO if k == activa else (255, 255, 255))
                  for k, (p, _, _) in enumerate(sb["palabras"])]
        espacio = 20
        ancho = sum(p.width for p in partes) + espacio * (len(partes) - 1)
        im = Image.new("RGBA", (ancho, max(p.height for p in partes)), (0, 0, 0, 0))
        x = 0
        for p in partes:
            im.alpha_composite(p, (x, im.height - p.height))
            x += p.width + espacio
        _CACHE[clave] = im
        if len(_CACHE) > 400:
            for k in [k for k in _CACHE if k[0] == "sub"][:200]:
                _CACHE.pop(k, None)
    return _CACHE[clave]
