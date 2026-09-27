"""Miniaturas para YouTube (1280×720), sin gastar: se arman con lo que el canal ya tiene.

Tres versiones para «Probar y comparar» de YouTube:
  1. el presentador en shock + el villano con brillo y círculo rojo
  2. la mascota asustada señalando al villano, fondo de color fuerte
  3. el villano en primer plano sobre fondo oscuro, con flecha roja
El texto (2 a 4 palabras) lo propone Claude y se pinta con letra limpia: la IA de
imágenes deforma las letras, por eso nunca se le pide texto.
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
FUENTE = Path(__file__).parent / "fuentes" / "Fredoka-SemiBold.ttf"
AMARILLO, ROJO, BLANCO, NEGRO = (255, 222, 40), (230, 28, 28), (255, 255, 255), (15, 12, 10)


def _fuente(tam: int):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(str(FUENTE), tam)
    except OSError:
        return ImageFont.load_default()


def _recorte(ruta: Path) -> Image.Image:
    img = quitar_fondo_liso(Image.open(ruta).convert("RGB"))
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
        "Escribe 3 textos DISTINTOS para la miniatura, en español, de 2 a 4 palabras cada uno, que den muchas ganas "
        "de hacer clic sin mentir (curiosidad, peligro, sorpresa). Sin emojis ni comillas. No repitas el título.\n"
        'Responde SOLO un JSON: {"textos": ["...", "...", "..."]}', cwd=carpeta)
    datos = claude_cli.extraer_json(texto) or {}
    textos = [str(t).strip()[:40] for t in datos.get("textos", []) if str(t).strip()]
    return (textos + ["NO TE LE ACERQUES", "TE PICA DORMIDO", "EL MÁS PELIGROSO"])[:3]


def generar(carpeta: Path, textos: list[str] | None = None, ejecutar=claude_cli.ejecutar) -> list[Path]:
    esc = leer_json(carpeta / "escenas.json")
    proyecto = leer_json(carpeta / "proyecto.json")
    estilo = cargar_estilo(proyecto["estilo"])
    nivel = next((n for n in esc["niveles"] if n.get("villano")), esc["niveles"][-1])
    asset = next(a for a in esc["assets"] if a["id"] == nivel["asset"])
    villano = _recorte(carpeta / asset["archivo"])
    textos = textos or textos_para(esc.get("video", ""), nivel["nombre"], ejecutar, carpeta)
    base_estilo = carpeta_estilos() / estilo.id / "assets"
    salida = []
    destino = carpeta / "render" / "miniaturas"
    destino.mkdir(parents=True, exist_ok=True)

    # 0) cuadrícula de todos los niveles sobre blanco; el villano arriba a la izquierda con brillo rojo
    niveles = sorted(esc["niveles"], key=lambda n: (not n.get("villano"), -n["numero"]))[:6]
    por_asset = {a["id"]: a for a in esc["assets"]}
    if len(niveles) >= 4:
        lienzo = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        cols, filas = 3, 2
        cw, ch = W // cols, H // filas
        for k, n in enumerate(niveles):
            cx, cy = (k % cols) * cw, (k // cols) * ch
            ruta = carpeta / por_asset[n["asset"]]["archivo"]
            if not ruta.exists():
                continue
            bicho = _encajar(_recorte(ruta), int(cw * 0.94), int(ch * 0.74))
            if n.get("villano"):
                bicho = _brillo(bicho, (255, 40, 40), 18, 3)
            lienzo.alpha_composite(bicho, (int(cx + (cw - bicho.width) / 2), int(cy + ch * 0.40 - bicho.height / 2)))
            etiqueta = ("¡" + textos[0].upper().strip("¡!") + "!") if n.get("villano") else n["nombre"]
            color = (225, 20, 20) if n.get("villano") else (20, 16, 12)
            d = ImageDraw.Draw(lienzo)
            for tam in range(52, 22, -2):
                f = _fuente(tam)
                caja = d.textbbox((0, 0), etiqueta, font=f, stroke_width=3 if n.get("villano") else 0)
                if caja[2] - caja[0] <= cw - 24:
                    break
            tx = cx + (cw - (caja[2] - caja[0])) / 2 - caja[0]
            d.text((tx, cy + ch * 0.83 - (caja[3] - caja[1]) / 2 - caja[1]), etiqueta, font=f, fill=color,
                   stroke_width=3 if n.get("villano") else 0, stroke_fill=(255, 255, 255))
        salida.append(lienzo)

    # 1) presentador en shock + villano
    shock = base_estilo / "presentador" / "shock.png"
    if shock.exists():
        lienzo = _fondo((60, 10, 10), (8, 4, 4))
        foto = Image.open(shock).convert("RGB")
        k = H / foto.height
        foto = foto.resize((int(foto.width * k), H), Image.Resampling.LANCZOS)
        franja = foto.crop((int(foto.width * 0.24), 0, int(foto.width * 0.24) + int(W * 0.5), H)).convert("RGBA")
        mascara = Image.new("L", franja.size, 255)
        dm = ImageDraw.Draw(mascara)
        for i in range(90):                                      # funde el borde derecho de la foto
            dm.line([(franja.width - 90 + i, 0), (franja.width - 90 + i, H)], fill=int(255 * (1 - i / 90)))
        lienzo.paste(franja, (0, 0), mascara)
        v = _brillo(_encajar(villano, int(W * 0.46), int(H * 0.62)), ROJO)
        vx, vy = int(W * 0.76 - v.width / 2), int(H * 0.60 - v.height / 2)
        lienzo.alpha_composite(v, (vx, vy))
        _circulo(lienzo, (vx + 10, vy + 10, vx + v.width - 10, vy + v.height - 10))
        _texto(lienzo, textos[0], (int(W * 0.47), 18, W - 24, int(H * 0.30)))
        salida.append(lienzo)

    # 2) mascota asustada señalando al villano
    pose = base_estilo / "poses" / "senalando_susto.png"
    lienzo = _fondo((255, 196, 0), (230, 60, 0))
    if pose.exists():
        m = _encajar(_recorte(pose), int(W * 0.40), int(H * 0.86))
        lienzo.alpha_composite(_brillo(m, BLANCO, 10, 4), (-10, H - m.height - 30))
    v = _brillo(_encajar(villano, int(W * 0.50), int(H * 0.66)), NEGRO, 16, 3)
    vx, vy = int(W * 0.70 - v.width / 2), int(H * 0.60 - v.height / 2)
    lienzo.alpha_composite(v, (vx, vy))
    _texto(lienzo, textos[1], (int(W * 0.30), 14, W - 20, int(H * 0.30)), color=BLANCO)
    salida.append(lienzo)

    # 3) villano en primer plano, fondo oscuro, flecha
    lienzo = _fondo((70, 12, 12), (0, 0, 0))
    v = _brillo(_encajar(villano, int(W * 0.62), int(H * 0.80)), ROJO, 28, 3)
    vx, vy = int(W * 0.60 - v.width / 2), int(H * 0.56 - v.height / 2)
    lienzo.alpha_composite(v, (vx, vy))
    _flecha(lienzo, (W * 0.10, H * 0.86), (vx + v.width * 0.22, vy + v.height * 0.62))
    _texto(lienzo, textos[2], (24, 16, int(W * 0.62), int(H * 0.34)))
    salida.append(lienzo)

    rutas = []
    for i, img in enumerate(salida, 1):
        ruta = destino / f"miniatura_{i}.jpg"
        img.convert("RGB").save(ruta, quality=92, optimize=True)
        rutas.append(ruta)
    return rutas
