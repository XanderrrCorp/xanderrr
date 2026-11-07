"""Lo que dibuja la v4 de Peligro Tropical (receta_v4.py). Todo por código (Pillow), sin imágenes pagadas:

- la escala de niveles en otras dos formas, que rotan entre videos: «vertical» (columna a la izquierda, del verde al
  rojo, y el animal grande a la derecha) y «cartas» (cartas numeradas que suben; la actual brilla). Los que todavía
  no han salido van en silueta negra con «?»;
- el letrero del animal en tres formas (lo usa render._presentacion): «etiqueta» (la de siempre), «color» (caja del
  color del nivel) y «tarjeta» (letras rojas sobre tarjeta blanca con borde negro);
- pantalla dividida «VS», silueta del último con «?», globo de pensamiento, pantalla negra, glitch e íconos.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1920, 1080
AMARILLO = (255, 214, 0)
ROJO = (226, 38, 38)
_CACHE: dict = {}


def _r():
    from . import render as R

    return R


def _rebote(loc: float, dur: float = 0.4, sobre: float = 0.22) -> float:
    if loc <= 0:
        return 0.0
    p = min(1.0, loc / dur)
    return (1 - (1 - p) ** 3) * (1 + sobre * math.exp(-loc * 8) * math.cos(loc * 14))


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def color_nivel(i: int, n: int) -> tuple[int, int, int]:
    """del verde (el primero) al rojo (el último), pasando por amarillo y naranja"""
    paleta = [(46, 170, 70), (150, 200, 40), (250, 200, 30), (245, 130, 30), (225, 50, 40), (150, 20, 30)]
    x = i / max(1, n - 1) * (len(paleta) - 1)
    a, b = paleta[int(math.floor(x))], paleta[min(len(paleta) - 1, int(math.floor(x)) + 1)]
    f = x - math.floor(x)
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


# ------------------------------------------------------------------ recortes de cada animal

def recortes(raiz: Path, esc) -> dict[int, dict]:
    """{numero: {"img": RGBA recortado, "nombre", "villano"}} con el mismo recorte que la tira de niveles"""
    clave = ("rec", str(raiz), tuple(n.numero for n in esc.niveles))
    if clave in _CACHE:
        return _CACHE[clave]
    from .tira import quitar_fondo_liso, recorte_valido

    assets = {a.id: a for a in esc.assets}
    salida = {}
    for n in esc.niveles:
        a = assets.get(n.asset)
        if not a:
            continue
        sujeto = None
        sin_fondo = raiz / "assets" / "sin_fondo" / Path(a.archivo).name
        original = raiz / a.archivo
        if sin_fondo.exists():
            sujeto = Image.open(sin_fondo).convert("RGBA")
            if not recorte_valido(sujeto):
                sujeto = None
        if sujeto is None and original.exists():
            sujeto = quitar_fondo_liso(Image.open(original))
            if not recorte_valido(sujeto):
                sujeto = Image.open(original).convert("RGBA")
        if sujeto is None:
            continue
        caja = sujeto.getbbox()
        if caja:
            sujeto = sujeto.crop(caja)
        salida[n.numero] = {"img": sujeto, "nombre": n.nombre, "villano": bool(n.villano)}
    _CACHE[clave] = salida
    return salida


def _encajar(img: Image.Image, w: int, h: int) -> Image.Image:
    k = min(w / img.width, h / img.height)
    return img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.Resampling.LANCZOS)


def silueta(img: Image.Image, color=(8, 8, 10)) -> Image.Image:
    """el animal todo negro (misma forma) con un borde claro finito para que se lea sobre fondo oscuro"""
    a = img.getchannel("A")
    negro = Image.new("RGBA", img.size, color + (0,))
    negro.putalpha(a)
    borde = Image.new("RGBA", img.size, (255, 255, 255, 0))
    borde.putalpha(a.filter(ImageFilter.MaxFilter(7)).point(lambda v: int(v * 0.55)))
    capa = Image.new("RGBA", (img.width + 20, img.height + 20), (0, 0, 0, 0))
    capa.alpha_composite(borde, (10, 10))
    capa.alpha_composite(negro, (10, 10))
    return capa


def _signo(tam: int) -> Image.Image:
    clave = ("signo", tam)
    if clave not in _CACHE:
        _CACHE[clave] = _r()._texto_img("?", tam, max(3, tam // 12), color=AMARILLO)
    return _CACHE[clave]


def _fondo() -> Image.Image:
    if "fondo" not in _CACHE:
        from .render_receta import papel_oscuro

        _CACHE["fondo"] = papel_oscuro(semilla=11)
    return _CACHE["fondo"]


def _caja_animal(rec: dict | None, w: int, h: int, oculto: bool, color, grosor: int = 8) -> Image.Image:
    """casilla cuadrada con borde del color del nivel: el animal, o su silueta con «?» si todavía no ha salido"""
    clave = ("caja", id(rec), w, h, oculto, color, grosor)
    if clave in _CACHE:
        return _CACHE[clave]
    caja = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(caja)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=max(8, w // 10), fill=(34, 34, 40, 255) if oculto else (245, 240, 228, 255),
                        outline=color + (255,), width=grosor)
    if rec:
        s = _encajar(rec["img"], int(w * 0.8), int(h * 0.78))
        if oculto:
            s = silueta(s)
        caja.alpha_composite(s, ((w - s.width) // 2, (h - s.height) // 2))
    if oculto:
        sg = _encajar(_signo(160), int(w * 0.5), int(h * 0.55))
        caja.alpha_composite(sg, ((w - sg.width) // 2, (h - sg.height) // 2))
    _CACHE[clave] = caja
    return caja


# ------------------------------------------------------------------ escala vertical y en cartas

def escala(raiz: Path, esc, ef: dict, loc: float, dur: float) -> Image.Image:
    rec = recortes(raiz, esc)
    numeros = sorted(n.numero for n in esc.niveles)
    n = len(numeros)
    actual = int(ef["hasta"])
    if ef.get("variante") == "cartas":
        return _cartas(rec, numeros, n, actual, loc, dur)
    return _vertical(rec, numeros, n, actual, loc, dur)


def _vertical(rec, numeros, n, actual, loc, dur):
    R = _r()
    img = _fondo().convert("RGBA")
    lado = int(min(150, (H - 80) / n - 14))
    x0, y0 = 70, (H - (n * (lado + 14) - 14)) // 2
    for i, k in enumerate(numeros):
        entra = _rebote(loc - 0.05 * i, 0.3, 0.1)
        if entra <= 0.02:
            continue
        oculto = k > actual
        color = color_nivel(i, n)
        es = k == actual
        caja = _caja_animal(rec.get(k), lado, lado, oculto, color, 10 if es else 6)
        if k < actual:
            caja = caja.copy()
            caja.putalpha(caja.getchannel("A").point(lambda v: int(v * 0.6)))
        esc_k = entra * (1.0 + (0.18 * _suave((loc - 0.35) / 0.3) if es else 0))
        cy = y0 + i * (lado + 14) + lado / 2
        cx = x0 + lado / 2 + (16 if es else 0)
        if es and loc > 0.35:                                     # halo del color del nivel detrás de la actual
            halo = Image.new("RGBA", (lado + 80, lado + 80), (0, 0, 0, 0))
            ImageDraw.Draw(halo).rounded_rectangle((20, 20, lado + 60, lado + 60), radius=lado // 6, fill=color + (200,))
            halo = halo.filter(ImageFilter.GaussianBlur(16))
            img.alpha_composite(halo, (int(cx - halo.width / 2), int(cy - halo.height / 2)))
        c = caja.resize((max(1, int(caja.width * esc_k)), max(1, int(caja.height * esc_k))), Image.Resampling.BICUBIC)
        img.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))
        num = R._texto_img(str(k), 54, 6)
        img.alpha_composite(num, (int(x0 + lado + 34 + (16 if es else 0)), int(cy - num.height / 2)))
    # el animal actual, grande a la derecha, entra deslizándose
    r = rec.get(actual)
    if r:
        clave = ("grande", id(r))
        if clave not in _CACHE:
            g = _encajar(r["img"], 1100, 760)
            sombra = Image.new("RGBA", (g.width + 80, g.height + 80), (0, 0, 0, 0))
            sombra.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", g.size, (0, 0, 0)).split(),
                                                       g.getchannel("A").point(lambda v: int(v * 0.6)))), (52, 56))
            sombra = sombra.filter(ImageFilter.GaussianBlur(18))
            sombra.alpha_composite(g, (40, 40))
            _CACHE[clave] = sombra
        g = _CACHE[clave]
        p = _suave((loc - 0.15) / 0.45)
        cx = 1180 + (1 - p) * 900
        img.alpha_composite(g, (int(cx - g.width / 2), int(560 - g.height / 2)))
    return img.convert("RGB")


def _cartas(rec, numeros, n, actual, loc, dur):
    R = _r()
    img = _fondo().convert("RGBA")
    sep = 26
    w = int(min(300, (W - 160 - (n - 1) * sep) / n))
    h = int(w * 1.35)
    x0 = (W - (n * w + (n - 1) * sep)) / 2
    for i, k in enumerate(numeros):
        llega = _suave((loc - 0.07 * i) / 0.35)
        if llega <= 0:
            continue
        oculto = k > actual
        color = color_nivel(i, n)
        es = k == actual
        clave = ("carta", id(rec.get(k)), w, h, oculto, color)
        if clave not in _CACHE:
            carta = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            caja = _caja_animal(rec.get(k), w, w, oculto, color, 8)
            d = ImageDraw.Draw(carta)
            d.rounded_rectangle((0, 0, w - 1, h - 1), radius=w // 9, fill=color + (255,), outline=(0, 0, 0, 255), width=6)
            carta.alpha_composite(caja.resize((w - 28, w - 28), Image.Resampling.LANCZOS), (14, 14))
            num = R._texto_img(str(k), int((h - w) * 0.7), 7)
            carta.alpha_composite(num, ((w - num.width) // 2, int(w + (h - w - num.height) / 2)))
            _CACHE[clave] = carta
        carta = _CACHE[clave]
        sube = 60 * _suave((loc - 0.45) / 0.3) if es else 0
        esc_k = 1 + 0.14 * _suave((loc - 0.45) / 0.3) if es else (0.92 if k < actual else 1.0)
        cx = x0 + i * (w + sep) + w / 2
        cy = H * 0.52 + (1 - llega) * H * 0.7 - sube
        if es and loc > 0.45:
            halo = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
            ImageDraw.Draw(halo).rounded_rectangle((30, 30, w + 90, h + 90), radius=w // 7, fill=(255, 236, 140, 210))
            halo = halo.filter(ImageFilter.GaussianBlur(22))
            img.alpha_composite(halo, (int(cx - halo.width / 2), int(cy - halo.height / 2)))
        c = carta if abs(esc_k - 1) < 0.005 else carta.resize((int(w * esc_k), int(h * esc_k)), Image.Resampling.BICUBIC)
        if k < actual:
            c = c.copy()
            c.putalpha(c.getchannel("A").point(lambda v: int(v * 0.55)))
        img.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))
    return img.convert("RGB")


# ------------------------------------------------------------------ letrero del animal (3 formas)

def letrero(texto: str, forma: str, color=(226, 38, 38)) -> Image.Image:
    R = _r()
    if forma == "color":
        t = R._texto_img(texto, 92, 0)
        caja = Image.new("RGBA", (t.width + 90, t.height + 50), (0, 0, 0, 0))
        ImageDraw.Draw(caja).rounded_rectangle((0, 0, caja.width - 1, caja.height - 1), radius=22, fill=color + (255,),
                                               outline=(0, 0, 0, 255), width=7)
        caja.alpha_composite(t, (45, 25))
        return caja
    if forma == "tarjeta":
        t = R._texto_img(texto, 92, 0, color=ROJO)
        caja = Image.new("RGBA", (t.width + 90, t.height + 50), (0, 0, 0, 0))
        ImageDraw.Draw(caja).rounded_rectangle((0, 0, caja.width - 1, caja.height - 1), radius=14, fill=(255, 255, 255, 255),
                                               outline=(0, 0, 0, 255), width=8)
        caja.alpha_composite(t, (45, 25))
        return caja
    return R._texto_img(texto, 100, 10)


# ------------------------------------------------------------------ recursos

def vs(raiz: Path, esc, ef: dict, loc: float) -> Image.Image:
    """pantalla dividida: el animal anterior contra el actual, con «VS» que salta en el medio"""
    rec = recortes(raiz, esc)
    R = _r()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    abre = _suave(loc / 0.3)
    mitad = W // 2
    d.polygon([(0, 0), (mitad + 60, 0), (mitad - 60, H), (0, H)], fill=(36, 116, 200, 255))
    d.polygon([(mitad + 60, 0), (W, 0), (W, H), (mitad - 60, H)], fill=(196, 34, 40, 255))
    for lado, k in (("izq", ef["izq"]), ("der", ef["der"])):
        r = rec.get(k)
        if not r:
            continue
        g = _encajar(r["img"], 760, 640)
        if lado == "der":
            g = g.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        cx = (mitad / 2 if lado == "izq" else mitad + mitad / 2) + (1 - abre) * (-700 if lado == "izq" else 700)
        img.alpha_composite(g, (int(cx - g.width / 2), int(520 - g.height / 2)))
        nom = R._texto_img(r["nombre"].upper(), 70, 8)
        if nom.width > mitad - 120:
            nom = _encajar(nom, mitad - 120, nom.height)
        img.alpha_composite(nom, (int(cx - nom.width / 2), H - 190))
    clave = ("vs_txt",)
    if clave not in _CACHE:
        _CACHE[clave] = R._texto_img("VS", 210, 16, color=AMARILLO)
    t = _CACHE[clave]
    e = _rebote(loc - 0.25, 0.3, 0.3)
    if e > 0.03:
        t2 = t.resize((max(1, int(t.width * e)), max(1, int(t.height * e))), Image.Resampling.BICUBIC)
        img.alpha_composite(t2, (int(mitad - t2.width / 2), int(H * 0.45 - t2.height / 2)))
    return img.convert("RGB")


def silueta_misterio(raiz: Path, esc, ef: dict, loc: float) -> Image.Image:
    """el último de la lista en silueta negra con un «?» amarillo que late (misterio del gancho)"""
    rec = recortes(raiz, esc)
    r = rec.get(ef["nivel"])
    img = _fondo().convert("RGBA")
    if r:
        clave = ("sil_grande", id(r))
        if clave not in _CACHE:
            _CACHE[clave] = silueta(_encajar(r["img"], 1100, 780))
        s = _CACHE[clave]
        z = 1 + 0.05 * loc / max(0.5, ef["dur"])
        s2 = s.resize((int(s.width * z), int(s.height * z)), Image.Resampling.BICUBIC)
        img.alpha_composite(s2, (int(W / 2 - s2.width / 2), int(H * 0.52 - s2.height / 2)))
    late = _rebote(loc - 0.3, 0.3, 0.25) * (1 + 0.06 * math.sin(loc * 9))
    if late > 0.03:
        sg = _signo(300)
        sg = sg.resize((int(sg.width * late), int(sg.height * late)), Image.Resampling.BICUBIC)
        img.alpha_composite(sg, (int(W / 2 - sg.width / 2), int(H * 0.45 - sg.height / 2)))
    return img.convert("RGB")


def _nube(texto: str) -> Image.Image:
    R = _r()
    t = R._texto_img(texto, 72, 0, color=(20, 20, 24))
    if t.width > 760:
        t = _encajar(t, 760, t.height)
    w, h = t.width + 140, t.height + 100                  # el óvalo central
    m = int(h * 0.55)                                      # margen para las burbujas de arriba y los puntitos
    k = 3
    ancho, alto = w + 2 * m, h + 2 * m
    nube = Image.new("RGBA", (ancho * k, alto * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(nube)
    for fill, extra in (((0, 0, 0, 255), 7), ((255, 255, 255, 255), 0)):
        e = extra * k
        d.ellipse((m * k - e, m * k - e, (m + w) * k + e, (m + h) * k + e), fill=fill)
        for bx, by, br in ((0.2, 0.12, 0.34), (0.5, 0.0, 0.4), (0.8, 0.14, 0.32), (0.06, 0.6, 0.3), (0.94, 0.55, 0.3)):
            cx, cy, rr = (m + w * bx) * k, (m + h * by) * k, h * br * k
            d.ellipse((cx - rr - e, cy - rr - e, cx + rr + e, cy + rr + e), fill=fill)
        for bx, by, br in ((0.16, 1.18, 0.11), (0.08, 1.4, 0.07)):           # puntitos hacia el personaje
            cx, cy, rr = (m + w * bx) * k, (m + h * by) * k, h * br * k
            d.ellipse((cx - rr - e, cy - rr - e, cx + rr + e, cy + rr + e), fill=fill)
    nube = nube.resize((ancho, alto), Image.Resampling.LANCZOS)
    nube.alpha_composite(t, (m + (w - t.width) // 2, m + (h - t.height) // 2))
    return nube


def globo(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    clave = ("nube", ef["texto"])
    if clave not in _CACHE:
        _CACHE[clave] = _nube(ef["texto"])
    n = _CACHE[clave]
    e = _rebote(loc, 0.3, 0.18)
    queda = ef["dur"] - loc
    if queda < 0.15:
        e *= max(0.0, queda / 0.15)
    if e < 0.03:
        return img
    n2 = n.resize((max(1, int(n.width * e)), max(1, int(n.height * e))), Image.Resampling.BICUBIC)
    base = img.convert("RGBA")
    cx, cy = ef.get("x", 0.27) * W, ef.get("y", 0.2) * H
    base.alpha_composite(n2, (int(cx - n2.width / 2), int(cy - n2.height / 2)))
    return base.convert("RGB")


def negro(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    k = min(1.0, loc / 0.12)
    return Image.blend(img.convert("RGB"), Image.new("RGB", img.size, (0, 0, 0)), k)


def glitch(img: Image.Image, ef: dict, loc: float, cuadro: int) -> Image.Image:
    """separación de colores y franjas corridas, a golpes (más fuerte al inicio)"""
    fuerza = max(0.0, 1 - loc / max(0.1, ef["dur"]))
    if (cuadro // 2) % 3 == 2 and loc > 0.12:
        return img
    rng = np.random.default_rng(cuadro)
    a = np.asarray(img.convert("RGB")).copy()
    dx = int(18 * fuerza) + 2
    a[..., 0] = np.roll(a[..., 0], dx, axis=1)
    a[..., 2] = np.roll(a[..., 2], -dx, axis=1)
    for _ in range(int(3 + 6 * fuerza)):
        y = int(rng.integers(0, H - 40))
        alto = int(rng.integers(8, 60))
        a[y:y + alto] = np.roll(a[y:y + alto], int(rng.integers(-80, 80) * fuerza), axis=1)
    return Image.fromarray(a)


def _icono(tipo: str, tam: int = 190) -> Image.Image:
    clave = ("ico", tipo, tam)
    if clave in _CACHE:
        return _CACHE[clave]
    k = 4
    s = tam * k
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = s / 100
    negro_ = (0, 0, 0, 255)
    if tipo == "x":
        for (a, b), (c, e) in (((18, 18), (82, 82)), ((82, 18), (18, 82))):
            d.line((a * u, b * u, c * u, e * u), fill=negro_, width=int(26 * u))
        for (a, b), (c, e) in (((18, 18), (82, 82)), ((82, 18), (18, 82))):
            d.line((a * u, b * u, c * u, e * u), fill=ROJO + (255,), width=int(16 * u))
    elif tipo == "corona":
        pts = [(10, 78), (14, 30), (32, 52), (50, 18), (68, 52), (86, 30), (90, 78)]
        d.polygon([(x * u, y * u) for x, y in pts], fill=AMARILLO + (255,), outline=negro_, width=int(5 * u))
        d.rectangle((10 * u, 76 * u, 90 * u, 88 * u), fill=(230, 170, 0, 255), outline=negro_, width=int(5 * u))
        for x, y in ((14, 30), (50, 18), (86, 30)):
            d.ellipse(((x - 6) * u, (y - 6) * u, (x + 6) * u, (y + 6) * u), fill=ROJO + (255,), outline=negro_, width=int(3 * u))
    elif tipo == "pulgar_abajo":
        d.ellipse((0, 0, s - 1, s - 1), fill=ROJO + (255,), outline=negro_, width=int(6 * u))
        d.rounded_rectangle((24 * u, 24 * u, 36 * u, 54 * u), radius=3 * u, fill=(255, 255, 255, 255))
        d.rounded_rectangle((40 * u, 24 * u, 74 * u, 56 * u), radius=8 * u, fill=(255, 255, 255, 255))
        d.polygon([(40 * u, 52 * u), (52 * u, 76 * u), (60 * u, 74 * u), (58 * u, 54 * u)], fill=(255, 255, 255, 255))
    else:                                                          # alerta
        pts = [(50, 6), (96, 90), (4, 90)]
        d.polygon([(x * u, y * u) for x, y in pts], fill=negro_)
        pts = [(50, 16), (88, 84), (12, 84)]
        d.polygon([(x * u, y * u) for x, y in pts], fill=AMARILLO + (255,))
        d.rounded_rectangle((45 * u, 34 * u, 55 * u, 64 * u), radius=4 * u, fill=negro_)
        d.ellipse((44 * u, 69 * u, 56 * u, 80 * u), fill=negro_)
    im = im.resize((tam, tam), Image.Resampling.LANCZOS)
    _CACHE[clave] = im
    return im


def icono(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    e = _rebote(loc, 0.3, 0.28)
    queda = ef["dur"] - loc
    if queda < 0.15:
        e *= max(0.0, queda / 0.15)
    if e < 0.03:
        return img
    ic = _icono(ef["tipo"])
    ic = ic.rotate(ef.get("giro", 0) + 8 * math.sin(loc * 6), expand=True, resample=Image.Resampling.BICUBIC)
    ic = ic.resize((max(1, int(ic.width * e)), max(1, int(ic.height * e))), Image.Resampling.BICUBIC)
    base = img.convert("RGBA")
    base.alpha_composite(ic, (int(ef["x"] * W - ic.width / 2), int(ef["y"] * H - ic.height / 2)))
    return base.convert("RGB")
