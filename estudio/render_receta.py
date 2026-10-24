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


# ------------------------------------------------------------------ cuadro de comentario (17-10)

COLOR_AVATAR = {"apuesta": (229, 57, 53), "experiencia": (251, 140, 0), "debate": (94, 53, 177),
                "pais": (0, 137, 123), "cierre": (30, 136, 229)}
ANCHO_COMENTARIO = 900


def _fuente_comentario(tam: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(Path(__file__).parent / "fuentes" / "Fredoka-SemiBold.ttf"), tam)
    except OSError:
        return _r()._fuente(tam)


def _tam_texto(texto: str, ancho: int) -> int:
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for tam in range(48, 29, -2):
        if d.textlength(texto, font=_fuente_comentario(tam)) <= ancho:
            return tam
    return 30


def _tarjeta_comentario(texto: str, visibles: int, tipo: str, cursor: bool, corazon: float) -> Image.Image:
    """Un comentario como los de YouTube: avatar, nombre, el texto escribiéndose y el corazón al final."""
    w, h = ANCHO_COMENTARIO, 210
    m = 16                                                       # margen para la sombra
    im = Image.new("RGBA", (w + 2 * m, h + 2 * m + 26), (0, 0, 0, 0))
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((m + 4, m + 10, m + w + 4, m + h + 10), radius=34, fill=(0, 0, 0, 90))
    im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(9)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((m, m, m + w, m + h), radius=34, fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=4)
    d.polygon([(m + 70, m + h - 2), (m + 70, m + h + 30), (m + 120, m + h - 2)], fill=(255, 255, 255, 255))
    d.line([(m + 70, m + h - 1), (m + 70, m + h + 30), (m + 120, m + h - 1)], fill=(30, 30, 30, 255), width=4)
    # avatar con la inicial
    cx, cy, r = m + 78, m + 78, 46
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=COLOR_AVATAR.get(tipo, (229, 57, 53)) + (255,))
    f_av = _fuente_comentario(48)
    d.text((cx, cy + 2), "T", font=f_av, fill=(255, 255, 255), anchor="mm")
    # nombre y hace cuánto
    x0 = m + 148
    f_nom = _fuente_comentario(30)
    d.text((x0, m + 30), "@tú", font=f_nom, fill=(20, 20, 20))
    d.text((x0 + d.textlength("@tú", font=f_nom) + 16, m + 30), "hace un momento", font=f_nom, fill=(150, 150, 150))
    # el texto que se escribe
    tam = _tam_texto(texto, w - (x0 - m) - 40)
    f = _fuente_comentario(tam)
    parte = texto[:visibles]
    d.text((x0, m + 82), parte, font=f, fill=(15, 15, 15))
    if cursor:
        xc = x0 + d.textlength(parte, font=f) + 4
        d.rectangle((xc, m + 86, xc + 4, m + 86 + tam), fill=(30, 136, 229))
    # pulgar, «Responder» y el corazón del creador cuando termina
    f_pie = _fuente_comentario(28)
    yb = m + h - 52
    d.text((x0, yb), "Me gusta", font=f_pie, fill=(110, 110, 110))
    d.text((x0 + 170, yb), "Responder", font=f_pie, fill=(110, 110, 110))
    if corazon > 0:
        k = 1 + 0.35 * math.sin(min(1.0, corazon) * math.pi)
        hx, hy, hr = m + w - 70, m + h - 40, 18 * k
        rojo = (229, 57, 53, 255)
        d.ellipse((hx - hr, hy - hr, hx, hy), fill=rojo)
        d.ellipse((hx, hy - hr, hx + hr, hy), fill=rojo)
        d.polygon([(hx - hr, hy - hr / 2 + 2), (hx + hr, hy - hr / 2 + 2), (hx, hy + hr * 0.95)], fill=rojo)
    return im


def comentario(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    """Sale desde abajo con rebote, el comentario se escribe letra por letra, el corazón late y se va."""
    texto = str(ef.get("texto") or "")
    dur = float(ef["dur"])
    escribir = min(max(0.6, 0.055 * len(texto)), max(0.6, dur - 1.2))
    p = max(0.0, min(1.0, (loc - 0.4) / escribir))
    visibles = int(round(len(texto) * p))
    escrito = p >= 1
    cursor = not escrito or int(loc * 3) % 2 == 0
    corazon = max(0.0, (loc - 0.4 - escribir - 0.25) / 0.35) if escrito else 0.0
    clave = ("com", texto, visibles, cursor, round(min(corazon, 1.0), 1), ef.get("tipo"))
    if clave not in _CACHE:
        _CACHE[clave] = _tarjeta_comentario(texto, visibles, ef.get("tipo", ""), cursor, min(corazon, 1.0))
        if len(_CACHE) > 600:
            for k in [k for k in _CACHE if k[0] == "com"][:300]:
                _CACHE.pop(k, None)
    t = _CACHE[clave]
    entra = _rebote(loc, 0.4, 0.12)
    sale = max(0.0, min(1.0, (dur - loc) / 0.3))
    y = H - 330 + (1 - entra) * 420 + (1 - sale) * 420
    return _pegar(img, t, 80 + t.width / 2, y, 0.85 + 0.15 * entra)


# ------------------------------------------------------------------ (23-10) más dopamina

def _palabra(texto: str, cifra: bool) -> Image.Image:
    R = _r()
    color = AMARILLO if cifra else (255, 255, 255)
    im = R._texto_img(texto, 140, 13, color=color)
    if im.width > 1300:                                       # que quepa siempre en el ancho
        f = 1300 / im.width
        im = im.resize((int(im.width * f), int(im.height * f)), Image.Resampling.LANCZOS)
    sombra = Image.new("RGBA", (im.width + 80, im.height + 80), (0, 0, 0, 0))
    sombra.alpha_composite(Image.fromarray(np.dstack([np.zeros(im.size[::-1] + (3,), np.uint8),
                                                      (np.asarray(im)[..., 3] * 0.55).astype(np.uint8)]), "RGBA"),
                           (52, 56))
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    sombra.alpha_composite(im, (40, 40))
    return sombra


def palabra_golpe(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    """La palabra fuerte salta arriba (entra pasada de tamaño y se asienta) y se va rápido. (24-10, el dueño: no debe
    tapar la imagen) va en la franja de arriba, donde va el título, nunca encima del animal."""
    clave = ("pg", ef["texto"], ef.get("cifra", False), ef.get("giro", 0))
    if clave not in _CACHE:
        _CACHE[clave] = _palabra(ef["texto"], ef.get("cifra", False)).rotate(ef.get("giro", 0), expand=True,
                                                                              resample=Image.Resampling.BICUBIC)
    capa = _CACHE[clave]
    queda = ef["dur"] - loc
    esc = (1.35 - 0.35 * _rebote(loc, 0.18, 0.12)) if loc < 0.18 else _rebote(loc, 0.18, 0.12)
    if queda < 0.14:                                          # sale encogiéndose
        esc *= max(0.0, queda / 0.14)
    return _pegar(img, capa, W / 2, H * 0.17, esc)


def _cinta(texto: str, alto: bool) -> Image.Image:
    R = _r()
    letras = R._texto_img(texto, 92, 6)
    lado = 70
    w, h = letras.width + lado + 110, max(letras.height, lado) + 46
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((22, 26, w + 22, h + 26), radius=26, fill=(0, 0, 0, 120))
    im = im.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(im)
    color = (215, 25, 25, 255) if alto else (245, 140, 10, 255)
    d.rounded_rectangle((10, 10, w + 10, h + 10), radius=26, fill=color, outline=(255, 255, 255, 255), width=6)
    cx, cy = 10 + 40 + lado // 2, 10 + h // 2                  # flecha hacia arriba
    d.polygon([(cx, cy - lado // 2), (cx - lado // 2, cy + lado // 3), (cx + lado // 2, cy + lado // 3)],
              fill=(255, 255, 255, 255))
    im.alpha_composite(letras, (10 + 40 + lado + 30, 10 + (h - letras.height) // 2))
    return im


def sube_nivel(img: Image.Image, ef: dict, loc: float) -> Image.Image:
    """Cinta «▲ SUBE EL PELIGRO» que entra desde abajo con rebote, se queda un momento y sale hacia arriba."""
    clave = ("sube", ef["texto"], ef.get("alto", False))
    if clave not in _CACHE:
        _CACHE[clave] = _cinta(ef["texto"], ef.get("alto", False))
    capa = _CACHE[clave]
    destino = H * 0.80
    y = H + capa.height - (H + capa.height - destino) * _rebote(loc, 0.3, 0.15)
    queda = ef["dur"] - loc
    if queda < 0.22:                                          # se va hacia arriba, rápido
        y -= (1 - queda / 0.22) ** 2 * (destino + capa.height)
    return _pegar(img, capa, W / 2, y)


def ilustrativa(img: Image.Image) -> Image.Image:
    """(24-10) Etiqueta pequeña «Imagen ilustrativa» arriba a la izquierda: la foto parece real pero es de IA."""
    if "ilus" not in _CACHE:
        R = _r()
        letras = R._texto_img("Imagen ilustrativa", 34, 0)
        caja = Image.new("RGBA", (letras.width + 36, letras.height + 18), (0, 0, 0, 0))
        ImageDraw.Draw(caja).rounded_rectangle((0, 0, caja.width - 1, caja.height - 1), radius=12, fill=(0, 0, 0, 150))
        caja.alpha_composite(letras, (18, 9))
        _CACHE["ilus"] = caja
    capa = _CACHE["ilus"]
    return _pegar(img, capa, 40 + capa.width / 2, 34 + capa.height / 2)
