"""Miniaturas para YouTube (1280×720), sin gastar: se arman con las tarjetas de los niveles.

Estilo del canal (referencias del dueño): fondo blanco, cuadrícula 3×2 con los animales
grandes; arriba a la izquierda el más peligroso, más grande que los demás, con brillo rojo,
ícono de advertencia y su frase en ROJO; los demás con su nombre en negro, del más peligroso
al más inofensivo. Tres versiones para «Probar y comparar» de YouTube: misma cuadrícula,
distinta frase del villano (la propone Claude). El texto se pinta con letra limpia: la IA
de imágenes deforma las letras, por eso nunca se le pide texto.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import claude_cli
from .config import leer_json
from .estilos import cargar_estilo, carpeta_estilos
from .tira import quitar_fondo_liso

W, H = 1280, 720
# Mali: redondeada, de trazo a mano, como las miniaturas de referencia del canal (OFL)
FUENTE = Path(__file__).parent / "fuentes" / "Mali-SemiBold.ttf"
FUENTE_FUERTE = Path(__file__).parent / "fuentes" / "Mali-Bold.ttf"
AMARILLO, ROJO, BLANCO, NEGRO = (255, 222, 40), (230, 28, 28), (255, 255, 255), (15, 12, 10)


def _fuente(tam: int, fuerte: bool = False):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(FUENTE_FUERTE if fuerte else FUENTE), tam)
    except OSError:
        return ImageFont.load_default()


def _recorte(ruta: Path) -> Image.Image:
    """Recorte limpio: además del fondo que toca los bordes, quita los huecos del mismo gris
    que quedan encerrados (entre patas y antenas), que el recorte normal no alcanza."""
    original = Image.open(ruta).convert("RGB")
    img = quitar_fondo_liso(original)
    arr = np.asarray(img).copy()
    rgb = np.asarray(original, np.int16)
    esquinas = np.array([rgb[2, 2], rgb[2, -3], rgb[-3, 2], rgb[-3, -3]]).mean(axis=0)
    cerca = np.abs(rgb - esquinas).max(axis=2) <= 10
    gris = (rgb.max(axis=2) - rgb.min(axis=2)) <= 10
    arr[cerca & gris, 3] = 0
    img = Image.fromarray(arr, "RGBA")
    caja = img.getbbox()
    return img.crop(caja) if caja else img


def _encajar(img: Image.Image, ancho: int, alto: int) -> Image.Image:
    img = img.copy()
    k = min(ancho / img.width, alto / img.height)
    return img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.Resampling.LANCZOS)


def _brillo(obj: Image.Image, color, radio: int = 22, fuerza: int = 3) -> Image.Image:
    """Contorno luminoso alrededor de un recorte (resalta sobre cualquier fondo)."""
    a = obj.split()[-1]
    m = 2 * radio
    capa = Image.new("RGBA", (obj.width + 2 * m, obj.height + 2 * m), (0, 0, 0, 0))
    base = Image.new("RGBA", obj.size, color + (255,))
    capa.paste(base, (m, m), a)
    capa = capa.filter(ImageFilter.GaussianBlur(radio))
    arr = np.asarray(capa).astype(np.float32)
    arr[..., 3] = np.clip(arr[..., 3] * fuerza, 0, 255)
    capa = Image.fromarray(arr.astype("uint8"), "RGBA")
    capa.alpha_composite(obj, (m, m))
    return capa


def _texto(lienzo: Image.Image, texto: str, zona: tuple[int, int, int, int], color=AMARILLO) -> None:
    """Texto enorme con borde negro grueso, en 1 o 2 líneas, ajustado a la zona."""
    x0, y0, x1, y1 = zona
    d = ImageDraw.Draw(lienzo)
    palabras = texto.upper().split()
    opciones = [[" ".join(palabras)]]
    if len(palabras) > 1:
        corte = max(range(1, len(palabras)), key=lambda k: -abs(len(" ".join(palabras[:k])) - len(" ".join(palabras[k:]))))
        opciones.append([" ".join(palabras[:corte]), " ".join(palabras[corte:])])
    mejor = None
    for lineas in opciones:
        for tam in range(170, 50, -6):
            f = _fuente(tam)
            borde = max(6, tam // 11)
            cajas = [d.textbbox((0, 0), l, font=f, stroke_width=borde) for l in lineas]
            ancho = max(c[2] - c[0] for c in cajas)
            alto = sum(c[3] - c[1] for c in cajas) + (len(lineas) - 1) * tam * 0.05
            if ancho <= x1 - x0 and alto <= y1 - y0:
                if not mejor or tam > mejor[0]:
                    mejor = (tam, lineas, f, borde, cajas, alto)
                break
    if not mejor:
        return
    tam, lineas, f, borde, cajas, alto = mejor
    y = y0 + ((y1 - y0) - alto) / 2
    for linea, c in zip(lineas, cajas):
        ancho = c[2] - c[0]
        x = x0 + ((x1 - x0) - ancho) / 2
        sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
        ImageDraw.Draw(sombra).text((x - c[0] + 6, y - c[1] + 8), linea, font=f, fill=(0, 0, 0, 170),
                                    stroke_width=borde, stroke_fill=(0, 0, 0, 170))
        lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(4)))
        d.text((x - c[0], y - c[1]), linea, font=f, fill=color, stroke_width=borde, stroke_fill=NEGRO)
        y += (c[3] - c[1]) + tam * 0.05


def _circulo(lienzo: Image.Image, caja: tuple[float, float, float, float], grosor: int = 12) -> None:
    d = ImageDraw.Draw(lienzo)
    x0, y0, x1, y1 = caja
    d.ellipse((x0, y0, x1, y1), outline=BLANCO + (220,), width=grosor + 8)
    d.ellipse((x0, y0, x1, y1), outline=ROJO + (255,), width=grosor)


def _flecha(lienzo: Image.Image, cola: tuple[float, float], punta: tuple[float, float], grosor: int = 30) -> None:
    d = ImageDraw.Draw(lienzo)
    v = np.array(punta) - np.array(cola)
    n = v / (np.linalg.norm(v) + 1e-6)
    p = np.array([-n[1], n[0]])
    base = np.array(punta) - n * grosor * 2.4
    for g, c in ((grosor + 12, BLANCO + (255,)), (grosor, ROJO + (255,))):
        extra = 8 if g > grosor else 0
        d.line([tuple(cola), tuple(base)], fill=c, width=g)
        d.polygon([tuple(np.array(punta) + n * extra), tuple(base + p * (g * 1.25)), tuple(base - p * (g * 1.25))], fill=c)


def _fondo(c1, c2) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W * 0.62) / W) ** 2 + ((yy - H * 0.5) / H) ** 2)
    t = np.clip(r / 0.75, 0, 1)[..., None]
    arr = np.array(c1, np.float32) * (1 - t) + np.array(c2, np.float32) * t
    return Image.fromarray(arr.astype("uint8"), "RGB").convert("RGBA")


def textos_para(titulo: str, villano: str, ejecutar=claude_cli.ejecutar, carpeta: Path | None = None) -> list[str]:
    texto, _ = ejecutar(
        f"Video de YouTube: «{titulo}». El animal más peligroso (el villano) es: {villano}.\n"
        "En la miniatura, debajo del villano va una frase corta en rojo, estilo «¡JAMÁS LO TOQUES!» o «¡NO TE LE "
        "ACERQUES!», o un apodo que dé miedo («BÚHO DEMONIO»). Escribe 3 frases DISTINTAS, en español, de 2 a 4 "
        "palabras, que den muchas ganas de hacer clic sin mentir. Sin emojis ni comillas.\n"
        'Responde SOLO un JSON: {"textos": ["...", "...", "..."]}', cwd=carpeta)
    datos = claude_cli.extraer_json(texto) or {}
    textos = [str(t).strip()[:40] for t in datos.get("textos", []) if str(t).strip()]
    return (textos + ["NO TE LE ACERQUES", "TE PICA DORMIDO", "EL MÁS PELIGROSO"])[:3]


def _advertencia(tam: int) -> Image.Image:
    im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = tam * 0.05
    d.polygon([(tam / 2, m), (tam - m, tam - m * 1.5), (m, tam - m * 1.5)], fill=NEGRO + (255,))
    k = tam * 0.09
    d.polygon([(tam / 2, m + k * 1.7), (tam - m - k * 1.6, tam - m * 1.5 - k), (m + k * 1.6, tam - m * 1.5 - k)],
              fill=(255, 210, 30, 255))
    f = _fuente(int(tam * 0.55))
    c = d.textbbox((0, 0), "!", font=f)
    d.text(((tam - (c[2] - c[0])) / 2 - c[0], tam * 0.60 - (c[3] - c[1]) / 2 - c[1]), "!", font=f, fill=NEGRO + (255,))
    return im


def _letrero(d: ImageDraw.ImageDraw, texto: str, centro: tuple[float, float], ancho_max: int, villano: bool) -> None:
    for tam in range(62 if villano else 50, 20, -2):
        f = _fuente(tam, fuerte=villano)
        borde = 5 if villano else 0
        caja = d.textbbox((0, 0), texto, font=f, stroke_width=borde)
        if caja[2] - caja[0] <= min(ancho_max, W - 28):
            break
    ancho = caja[2] - caja[0]
    x = min(max(14, centro[0] - ancho / 2), W - 14 - ancho) - caja[0]      # nunca se corta en el borde
    y = centro[1] - (caja[3] - caja[1]) / 2 - caja[1]
    d.text((x, y), texto, font=f, fill=(226, 20, 20) if villano else NEGRO, stroke_width=borde,
           stroke_fill=(255, 255, 255))


def cuadricula(carpeta: Path, frase: str, advertencia: bool = True) -> Image.Image:
    esc = leer_json(carpeta / "escenas.json")
    por_asset = {a["id"]: a for a in esc["assets"]}
    # del más peligroso (villano) al más inofensivo
    niveles = sorted(esc["niveles"], key=lambda n: (not n.get("villano"), -n["numero"]))[:6]
    lienzo = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(lienzo)
    cols, cw, ch = 3, W / 3, H / 2
    for k, n in enumerate(niveles):
        cx, cy = (k % cols) * cw, (k // cols) * ch
        ruta = carpeta / por_asset[n["asset"]]["archivo"]
        villano = bool(n.get("villano"))
        if ruta.exists():
            escala = 1.18 if villano else 1.0
            bicho = _encajar(_recorte(ruta), int(cw * 0.98 * escala), int(ch * 0.80 * escala))
            if villano:
                bicho = _brillo(bicho, (255, 70, 70), 28, 1.6)          # brillo rojo suave, no mancha
            bx = int(cx + cw / 2 - bicho.width / 2)
            by = int(cy + ch * 0.42 - bicho.height / 2)
            lienzo.alpha_composite(bicho, (max(0, bx), max(0, by)))
            if villano and advertencia:
                icono = _advertencia(92)
                lienzo.alpha_composite(icono, (int(min(cx + cw - 100, bx + bicho.width - 60)), int(max(8, by + 6))))
        etiqueta = ("¡" + frase.upper().strip("¡!¿? ") + "!") if villano else n["nombre"]
        _letrero(d, etiqueta, (cx + cw / 2, cy + ch * 0.88), int(cw * (1.02 if villano else 0.94)), villano)
    return lienzo


def generar(carpeta: Path, textos: list[str] | None = None, ejecutar=claude_cli.ejecutar) -> list[Path]:
    """Tres miniaturas en el estilo del canal, con tres frases distintas para el villano."""
    esc = leer_json(carpeta / "escenas.json")
    nivel = next((n for n in esc["niveles"] if n.get("villano")), esc["niveles"][-1])
    textos = textos or textos_para(esc.get("video", ""), nivel["nombre"], ejecutar, carpeta)
    destino = carpeta / "render" / "miniaturas"
    destino.mkdir(parents=True, exist_ok=True)
    for viejo in destino.glob("miniatura_*.jpg"):
        viejo.unlink()
    rutas = []
    for i, frase in enumerate(textos[:3], 1):
        ruta = destino / f"miniatura_{i}.jpg"
        cuadricula(carpeta, frase, advertencia=(i != 2)).convert("RGB").save(ruta, quality=92, optimize=True)
        rutas.append(ruta)
    return rutas
