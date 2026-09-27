"""Paso 3b: la miniatura la arma el CÓDIGO, así el layout, la alineación y los textos
siempre salen perfectos.

Lienzo 1280x720 blanco puro, sin celdas, marcos ni sombras. 6 sujetos recortados en
2x3, enormes, que pueden salirse del lienzo y acercarse entre sí, pero NUNCA tapar
un texto: si un sujeto pisa una etiqueta se sube o se achica hasta que no la toque.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import iconos
from .plan import Plan
from .plantilla import Plantilla, ruta_plantilla
from .recorte import recortar

W, H = 1280, 720
FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
# columnas de arriba: el protagonista tiene más espacio; abajo, tres iguales
COLUMNAS_ARRIBA = (0, 500, 890, W)
COLUMNAS_ABAJO = (0, 427, 853, W)
FILAS = (0, 360, H)
BANDA_ETIQUETA = 54
BANDA_HERO = 76
LLENADO = 1.1            # los sujetos se pasan un poco de su zona: se ven grandes
LLENADO_HERO = 1.3       # ~30 % más grande que los demás
MAX_BYTES = 1_900_000    # YouTube pide menos de 2 MB


@dataclass
class Colocado:
    indice: int
    img: Image.Image
    x: int
    y: int

    @property
    def caja(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.x + self.img.width, self.y + self.img.height


def _celda(i: int) -> tuple[int, int, int, int]:
    fila, col = divmod(i, 3)
    cols = COLUMNAS_ARRIBA if fila == 0 else COLUMNAS_ABAJO
    return cols[col], FILAS[fila], cols[col + 1], FILAS[fila + 1]


def _fuente(nombre: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FUENTES / nombre), tam)


def _texto_que_cabe(texto: str, fuente: str, tam_max: int, tam_min: int, ancho: int):
    """Una sola línea: si no cabe se reduce la letra, nunca se parte."""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    for tam in range(tam_max, tam_min - 1, -2):
        f = _fuente(fuente, tam)
        caja = d.textbbox((0, 0), texto, font=f)
        if caja[2] - caja[0] <= ancho:
            return f, caja
    f = _fuente(fuente, tam_min)
    return f, d.textbbox((0, 0), texto, font=f)


def _rgb(hexa: str) -> tuple[int, int, int]:
    return tuple(int(hexa[k:k + 2], 16) for k in (1, 3, 5))


def textos(plan: Plan, plantilla: Plantilla) -> list[dict]:
    """Dónde va cada texto (se calcula antes que los sujetos: los textos mandan)."""
    salida = []
    for i, c in enumerate(plan.cells):
        x0, y0, x1, y1 = _celda(i)
        if c.is_hero:
            texto, fuente, tam, banda, color = plan.hero_text, plantilla.fuente_hero, 58, BANDA_HERO, plantilla.color_hero_text
        else:
            texto, fuente, tam, banda, color = c.label, plantilla.fuente_etiquetas, 44, BANDA_ETIQUETA, plantilla.color_etiquetas
        f, caja = _texto_que_cabe(texto, fuente, tam, 20, x1 - x0 - 24)
        ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
        cx, cy = (x0 + x1) / 2, y1 - banda / 2
        tx, ty = cx - ancho / 2 - caja[0], cy - alto / 2 - caja[1]
        salida.append({"indice": i, "texto": texto, "fuente": f, "color": _rgb(color), "pos": (tx, ty),
                       "caja": (int(cx - ancho / 2) - 8, int(cy - alto / 2) - 6, int(cx + ancho / 2) + 8,
                                int(cy + alto / 2) + 6), "banda": banda})
    return salida


def _pixelar_zona(img: Image.Image, caja: list[float], bloque_rel: float = 0.035) -> Image.Image:
    x0, y0, x1, y1 = (int(v * s) for v, s in zip(caja, (img.width, img.height, img.width, img.height)))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return img
    zona = img.crop((x0, y0, x1, y1))
    b = max(4, int(img.width * bloque_rel))
    zona = zona.resize((max(1, zona.width // b), max(1, zona.height // b)), Image.Resampling.BILINEAR)
    img = img.copy()
    img.paste(zona.resize((x1 - x0, y1 - y0), Image.Resampling.NEAREST), (x0, y0))
    return img


def cargar_recorte(carpeta: Path, archivo: str, censura: list[float] | None = None) -> Image.Image:
    """Recorte en caché (el recorte con rembg tarda unos segundos por imagen)."""
    clave = hashlib.sha256(f"{archivo}|{censura}".encode()).hexdigest()[:12]
    cache = carpeta / "recortes" / f"{Path(archivo).stem}_{clave}.png"
    if cache.exists():
        return Image.open(cache).convert("RGBA")
    img = Image.open(carpeta / archivo).convert("RGB")
    if censura:
        img = _pixelar_zona(img, censura)       # la censura la pone el código, no la IA
    rec, _ = recortar(img)
    cache.parent.mkdir(parents=True, exist_ok=True)
    rec.save(cache)
    return rec


def _mascara(im: Image.Image) -> np.ndarray:
    return np.asarray(im.split()[-1]) > 40


def _pisa(col: Colocado, cajas: list[tuple[int, int, int, int]]) -> bool:
    m = _mascara(col.img)
    for a, b, c, d in cajas:
        x0, y0 = max(a, col.x), max(b, col.y)
        x1, y1 = min(c, col.x + col.img.width), min(d, col.y + col.img.height)
        if x1 > x0 and y1 > y0 and m[y0 - col.y:y1 - col.y, x0 - col.x:x1 - col.x].any():
            return True
    return False


def colocar(i: int, rec: Image.Image, plan: Plan, cajas_texto: list, banda: int) -> Colocado:
    x0, y0, x1, y1 = _celda(i)
    zw, zh = x1 - x0, (y1 - banda) - y0
    c = plan.cells[i]
    s = min(zw / rec.width, zh / rec.height) * (LLENADO_HERO if c.is_hero else LLENADO) * c.ajuste.escala
    for _ in range(30):
        img = rec.resize((max(1, int(rec.width * s)), max(1, int(rec.height * s))), Image.Resampling.LANCZOS)
        # apoyado sobre su texto y centrado en su columna; lo que sobra se sale por arriba o por los lados
        x = int((x0 + x1) / 2 - img.width / 2) + c.ajuste.dx
        y = int(y1 - banda - img.height + 6) + c.ajuste.dy
        if c.is_hero:
            x = min(x, x0 + 10 + c.ajuste.dx) if img.width > zw else x
        col = Colocado(i, img, x, y)
        if not _pisa(col, cajas_texto):
            return col
        # primero se intenta subirlo un poco; si igual pisa, se achica
        for sube in (8, 16, 28):
            col2 = Colocado(i, img, x, y - sube)
            if not _pisa(col2, cajas_texto) and (i < 3 or y - sube + img.height * 0.5 > FILAS[1]):
                return col2
        s *= 0.95
    return col


def _aura(img: Image.Image, color: tuple[int, int, int], radio: int = 12) -> Image.Image:
    """Brillo SOLO alrededor de la silueta, hecho por código (siempre limpio)."""
    pad = radio * 3
    alfa = Image.new("L", (img.width + 2 * pad, img.height + 2 * pad), 0)
    alfa.paste(img.split()[-1], (pad, pad))
    alfa = alfa.filter(ImageFilter.MaxFilter(radio // 2 * 2 + 1)).filter(ImageFilter.GaussianBlur(radio))
    alfa = alfa.point(lambda v: min(235, int(v * 1.5)))
    capa = Image.new("RGBA", alfa.size, color + (0,))
    capa.putalpha(alfa)
    return capa


def componer(carpeta: Path, plan: Plan, plantilla: Plantilla) -> tuple[Image.Image, dict]:
    """La miniatura final y su mapa (dónde cayó cada sujeto y cada texto, para la interfaz)."""
    lienzo = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    pos_textos = textos(plan, plantilla)
    cajas = [t["caja"] for t in pos_textos]
    colocados = []
    for i, c in enumerate(plan.cells):
        if not c.archivo or not (carpeta / c.archivo).exists():
            continue
        rec = cargar_recorte(carpeta, c.archivo, plan.hero_censor_box if (c.is_hero and plan.hero_censor) else None)
        colocados.append(colocar(i, rec, plan, cajas, pos_textos[i]["banda"]))
    # el protagonista va encima de los demás, con su aura debajo
    for col in sorted(colocados, key=lambda k: plan.cells[k.indice].is_hero):
        if plan.cells[col.indice].is_hero:
            aura = _aura(col.img, _rgb(plan.hero_glow_color))
            pad = (aura.width - col.img.width) // 2
            _pegar(lienzo, aura, col.x - pad, col.y - pad)
        _pegar(lienzo, col.img, col.x, col.y)
    hero = next((k for k in colocados if plan.cells[k.indice].is_hero), None)
    if hero is not None:
        tam = 104
        ico = iconos.icono(plan.hero_icon, tam, ruta_plantilla(plantilla.canal))
        x0, y0, x1, y1 = hero.caja
        derecha = min(x1, _celda(hero.indice)[2])       # esquina superior derecha del protagonista, en su zona
        ix = min(max(10, derecha - tam - 6), W - tam - 8)
        iy = min(max(8, y0 + 4), FILAS[1] - BANDA_HERO - tam)
        _pegar(lienzo, ico, ix, iy)
    d = ImageDraw.Draw(lienzo)
    for t in pos_textos:                       # los textos van al final: nada los tapa
        d.text(t["pos"], t["texto"], font=t["fuente"], fill=t["color"])
    mapa = {"ancho": W, "alto": H,
            "sujetos": [{"indice": k.indice, "caja": [max(0, k.caja[0]), max(0, k.caja[1]), min(W, k.caja[2]),
                                                       min(H, k.caja[3])]} for k in colocados],
            "textos": [{"indice": t["indice"], "texto": t["texto"], "caja": list(t["caja"])} for t in pos_textos]}
    return lienzo.convert("RGB"), mapa


def _pegar(lienzo: Image.Image, img: Image.Image, x: int, y: int) -> None:
    """alpha_composite que admite posiciones fuera del lienzo (el sujeto se sale por el borde)."""
    a0, b0 = max(0, -x), max(0, -y)
    a1, b1 = min(img.width, W - x), min(img.height, H - y)
    if a1 <= a0 or b1 <= b0:
        return
    lienzo.alpha_composite(img.crop((a0, b0, a1, b1)), (max(0, x), max(0, y)))


def guardar_jpg(img: Image.Image, ruta: Path) -> Path:
    """JPG 1280x720 de menos de 2 MB (requisito de YouTube)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    for calidad in (95, 92, 88, 84, 80, 75, 70):
        b = io.BytesIO()
        img.save(b, "JPEG", quality=calidad, optimize=True, progressive=True)
        if b.tell() <= MAX_BYTES:
            break
    ruta.write_bytes(b.getvalue())
    return ruta


def vista_feed(img: Image.Image, ruta: Path) -> Path:
    """Cómo se ve en el feed de YouTube en el celular (~ 360 px de ancho)."""
    peq = img.resize((360, 203), Image.Resampling.LANCZOS)
    peq.save(ruta, quality=90)
    return ruta
