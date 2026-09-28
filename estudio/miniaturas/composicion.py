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
LLENADO = 1.05           # los sujetos se pasan un poco de su zona a los lados: se ven grandes
LLENADO_HERO = 1.3
MIN_HERO_VS_MAYOR = 1.3  # el área visible del protagonista, al menos 30 % mayor que la del mayor de los otros
MAX_SOLAPE = 0.05        # máximo ~5 % de encimado entre dos sujetos
OPACIDAD_AURA = 0.6
HERO_BORDE_DERECHO = 560 # hasta dónde puede llegar el protagonista hacia la derecha
RADIO_ESCENA = 0.08      # bordes redondeados de las escenas en modo «scene»
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


def _texto_que_cabe(texto: str, fuente: str, tam_max: int, tam_min: int, ancho: int, trazo: int = 0):
    """Una sola línea: si no cabe se reduce la letra, nunca se parte."""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    for tam in range(tam_max, tam_min - 1, -2):
        f = _fuente(fuente, tam)
        caja = d.textbbox((0, 0), texto, font=f, stroke_width=trazo)
        if caja[2] - caja[0] <= ancho:
            return f, caja
    f = _fuente(fuente, tam_min)
    return f, d.textbbox((0, 0), texto, font=f, stroke_width=trazo)


def _rgb(hexa: str) -> tuple[int, int, int]:
    return tuple(int(hexa[k:k + 2], 16) for k in (1, 3, 5))


def textos(plan: Plan, plantilla: Plantilla) -> list[dict]:
    """Dónde va cada texto (se calcula antes que los sujetos: los textos mandan). El del protagonista
    usa la MISMA fuente cómic de las etiquetas, en rojo y con trazo más grueso."""
    salida = []
    for i, c in enumerate(plan.cells):
        x0, y0, x1, y1 = _celda(i)
        if c.is_hero:
            texto, tam, banda, color, trazo = plan.hero_text, 62, BANDA_HERO, plantilla.color_hero_text, plantilla.grosor_hero
        else:
            texto, tam, banda, color, trazo = c.label, 44, BANDA_ETIQUETA, plantilla.color_etiquetas, 0
        f, caja = _texto_que_cabe(texto, plantilla.fuente_etiquetas, tam, 20, x1 - x0 - 24, trazo)
        ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
        cx, cy = (x0 + x1) / 2, y1 - banda / 2
        tx, ty = cx - ancho / 2 - caja[0], cy - alto / 2 - caja[1]
        salida.append({"indice": i, "texto": texto, "fuente": f, "color": _rgb(color), "pos": (tx, ty), "trazo": trazo,
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


def cargar_escena(carpeta: Path, archivo: str, aspecto: float, censura: list[float] | None = None) -> Image.Image:
    """Modo «scene»: NO se quita el fondo; la escena se recorta al centro con la proporción de su
    zona y con bordes redondeados."""
    img = Image.open(carpeta / archivo).convert("RGB")
    if censura:
        img = _pixelar_zona(img, censura)
    w, h = img.size
    if w / h > aspecto:
        nw = int(h * aspecto)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / aspecto)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    radio = int(min(img.size) * RADIO_ESCENA)
    alfa = Image.new("L", img.size, 0)
    ImageDraw.Draw(alfa).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=radio, fill=255)
    salida = img.convert("RGBA")
    salida.putalpha(alfa)
    return salida


def _mascara(im: Image.Image) -> np.ndarray:
    return np.asarray(im.split()[-1]) > 40


def _en_lienzo(col: Colocado) -> np.ndarray:
    """Máscara del sujeto sobre el lienzo (lo que se sale del borde no cuenta)."""
    m = np.zeros((H, W), bool)
    a0, b0 = max(0, -col.x), max(0, -col.y)
    a1, b1 = min(col.img.width, W - col.x), min(col.img.height, H - col.y)
    if a1 > a0 and b1 > b0:
        m[max(0, col.y):max(0, col.y) + (b1 - b0), max(0, col.x):max(0, col.x) + (a1 - a0)] = \
            _mascara(col.img)[b0:b1, a0:a1]
    return m


def area_visible(col: Colocado) -> int:
    """Área de la caja visible del recorte (lo que queda dentro del lienzo)."""
    x0, y0, x1, y1 = max(0, col.x), max(0, col.y), min(W, col.x + col.img.width), min(H, col.y + col.img.height)
    return max(0, x1 - x0) * max(0, y1 - y0)


def solape(a: np.ndarray, b: np.ndarray) -> float:
    """Proporción del sujeto más pequeño que queda tapada por el otro."""
    menor = min(int(a.sum()), int(b.sum()))
    return float((a & b).sum() / menor) if menor else 0.0


def _pisa(col: Colocado, cajas: list[tuple[int, int, int, int]]) -> bool:
    m = _mascara(col.img)
    for a, b, c, d in cajas:
        x0, y0 = max(a, col.x), max(b, col.y)
        x1, y1 = min(c, col.x + col.img.width), min(d, col.y + col.img.height)
        if x1 > x0 and y1 > y0 and m[y0 - col.y:y1 - col.y, x0 - col.x:x1 - col.x].any():
            return True
    return False


def colocar(i: int, rec: Image.Image, plan: Plan, cajas_texto: list, banda: int, s: float | None = None,
            factor: float = 1.0) -> Colocado:
    """Lo más grande posible en su zona, apoyado sobre su texto, SIN salirse por arriba (ahí van la
    cabeza y las antenas): solo se puede salir por los bordes laterales del lienzo. Si pisa un texto
    (propio o ajeno), primero se sube y luego se achica."""
    x0, y0, x1, y1 = _celda(i)
    zw, zh = x1 - x0, (y1 - banda) - y0
    c = plan.cells[i]
    if s is None:
        s = min(zw / rec.width, zh / rec.height) * (LLENADO_HERO if c.is_hero else LLENADO) * factor
    s *= c.ajuste.escala
    col = None
    for _ in range(60):
        img = rec.resize((max(1, int(rec.width * s)), max(1, int(rec.height * s))), Image.Resampling.LANCZOS)
        apoyado = int(y1 - banda - img.height + 6)
        if apoyado < y0 and i < 3:
            s *= 0.96                           # no cabe sin cortarle la cabeza: más pequeño
            continue
        x = int((x0 + x1) / 2 - img.width / 2) + c.ajuste.dx
        if c.is_hero:
            # el protagonista se apoya a la izquierda y, si es muy ancho, se sale por el borde izquierdo
            x = min(x0 + 10, HERO_BORDE_DERECHO - img.width) + c.ajuste.dx
        candidatos = [apoyado + c.ajuste.dy] if c.ajuste.dy <= 0 else [apoyado]
        candidatos += [apoyado - 10, apoyado - 22]
        for y in candidatos:
            if i < 3 and y < y0:
                continue
            col = Colocado(i, img, x, y)
            if not _pisa(col, cajas_texto):
                return col
        s *= 0.95
    return col


def _separar(colocados: dict[int, Colocado], recs: dict, plan: Plan, cajas: list, bandas: dict,
             escalas: dict[int, float]) -> None:
    """Máximo ~5 % de encimado entre dos sujetos: si se pasa, se achica el que no es protagonista
    (el de más abajo en la escala)."""
    for _ in range(40):
        mascaras = {i: _en_lienzo(c) for i, c in colocados.items()}
        peor, par = 0.0, None
        ids = sorted(colocados)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                v = solape(mascaras[ids[a]], mascaras[ids[b]])
                if v > peor:
                    peor, par = v, (ids[a], ids[b])
        if peor <= MAX_SOLAPE or par is None:
            return
        cual = next((k for k in reversed(par) if not plan.cells[k].is_hero), par[1])
        escalas[cual] *= 0.94
        colocados[cual] = colocar(cual, recs[cual], plan, cajas, bandas[cual], s=escalas[cual])


def _aura(img: Image.Image, color: tuple[int, int, int], radio: int = 26) -> Image.Image:
    """Resplandor suave SOLO alrededor de la silueta, hecho por código: desenfoque amplio del contorno,
    ~60 % de opacidad pegado al cuerpo y desvaneciéndose hacia afuera. Va DETRÁS del sujeto."""
    pad = radio * 3
    alfa = Image.new("L", (img.width + 2 * pad, img.height + 2 * pad), 0)
    alfa.paste(img.split()[-1], (pad, pad))
    alfa = alfa.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(radio))
    tope = int(255 * OPACIDAD_AURA)
    alfa = alfa.point(lambda v: min(tope, int(v * 1.25)))
    capa = Image.new("RGBA", alfa.size, color + (0,))
    capa.putalpha(alfa)
    return capa


def _poner_icono(icono_img: Image.Image, hero: Colocado, ocupado: np.ndarray, cajas: list, plantilla_dir,
                 nombre: str) -> tuple[Image.Image, int, int, bool]:
    """En la esquina superior derecha del área del protagonista, sin tocar su cuerpo ni a otro sujeto
    ni un texto. Si choca se mueve y, si hace falta, se achica."""
    x0, y0, x1, y1 = hero.caja
    objetivo = (min(x1, HERO_BORDE_DERECHO), max(0, y0))
    libre_de = np.asarray(Image.fromarray(ocupado.astype("uint8") * 255).filter(ImageFilter.MaxFilter(9))) > 0
    for tam in (104, 92, 80, 68, 58):
        ico = iconos.icono(nombre, tam, plantilla_dir)
        m = _mascara(ico)
        opciones = [(x, y) for x in range(0, HERO_BORDE_DERECHO + 60 - tam, 8)
                    for y in range(4, FILAS[1] - BANDA_HERO - tam, 8)]
        opciones.sort(key=lambda p: (p[0] + tam - objetivo[0]) ** 2 + (p[1] - objetivo[1]) ** 2)
        for x, y in opciones:
            if libre_de[y:y + tam, x:x + tam][m].any():
                continue
            if any(x < c and x + tam > a and y < d and y + tam > b for a, b, c, d in cajas):
                continue
            return ico, x, y, True
    ico = iconos.icono(nombre, 58, plantilla_dir)
    return ico, max(4, objetivo[0] - 58), objetivo[1] + 4, False


def componer(carpeta: Path, plan: Plan, plantilla: Plantilla) -> tuple[Image.Image, dict]:
    """La miniatura final, su mapa (dónde cayó cada sujeto y cada texto, para la interfaz) y las
    medidas que se comprueban por código."""
    lienzo = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    pos_textos = textos(plan, plantilla)
    cajas = [t["caja"] for t in pos_textos]
    bandas = {t["indice"]: t["banda"] for t in pos_textos}
    escena = plan.hook_mode == "scene"
    recs = {}
    for i, c in enumerate(plan.cells):
        if not c.archivo or not (carpeta / c.archivo).exists():
            continue
        censura = plan.hero_censor_box if (c.is_hero and plan.hero_censor) else None
        if escena:
            x0, y0, x1, y1 = _celda(i)
            recs[i] = cargar_escena(carpeta, c.archivo, (x1 - x0) / ((y1 - bandas[i]) - y0), censura)
        else:
            recs[i] = cargar_recorte(carpeta, c.archivo, censura)
    hero_i = next((i for i in recs if plan.cells[i].is_hero), None)
    otros = [i for i in recs if i != hero_i]
    factor, colocados, escalas = 1.0, {}, {}
    for _ in range(16):
        colocados, escalas = {}, {}
        for i in otros:
            x0, y0, x1, y1 = _celda(i)
            base = min((x1 - x0) / recs[i].width, ((y1 - bandas[i]) - y0) / recs[i].height) * LLENADO * factor
            escalas[i] = base
            colocados[i] = colocar(i, recs[i], plan, cajas, bandas[i], s=base)
        mayor = max((area_visible(k) for k in colocados.values()), default=0)
        if hero_i is not None:
            rec = recs[hero_i]
            objetivo = mayor * MIN_HERO_VS_MAYOR * 1.03
            s_obj = (objetivo / (rec.width * rec.height)) ** 0.5 if mayor else LLENADO_HERO
            s_alto = (FILAS[1] - BANDA_HERO + 6) / rec.height
            escalas[hero_i] = min(max(s_obj, 0.01), s_alto)
            colocados[hero_i] = colocar(hero_i, rec, plan, cajas, bandas[hero_i], s=escalas[hero_i])
        _separar(colocados, recs, plan, cajas, bandas, escalas)
        mayor = max((area_visible(colocados[i]) for i in otros if i in colocados), default=0)
        razon = (area_visible(colocados[hero_i]) / mayor) if (hero_i is not None and mayor) else 99.0
        if razon >= MIN_HERO_VS_MAYOR or any(plan.cells[i].ajuste.escala != 1.0 for i in recs):
            break
        factor *= 0.93                            # el protagonista no cabe más grande: se achican los demás
    # aura (detrás de todo), luego los demás, y el protagonista completo encima, sin teñirse
    if hero_i is not None:
        h = colocados[hero_i]
        aura = _aura(h.img, _rgb(plan.hero_glow_color))
        pad = (aura.width - h.img.width) // 2
        _pegar(lienzo, aura, h.x - pad, h.y - pad)
    for i in otros:
        _pegar(lienzo, colocados[i].img, colocados[i].x, colocados[i].y)
    if hero_i is not None:
        _pegar(lienzo, colocados[hero_i].img, colocados[hero_i].x, colocados[hero_i].y)
    mascaras = {i: _en_lienzo(c) for i, c in colocados.items()}
    ocupado = np.zeros((H, W), bool)
    for m in mascaras.values():
        ocupado |= m
    icono_libre, icono_tam = None, None
    if hero_i is not None:
        ico, ix, iy, icono_libre = _poner_icono(None, colocados[hero_i], ocupado, cajas,
                                                ruta_plantilla(plantilla.canal), plan.hero_icon)
        icono_tam = ico.width
        _pegar(lienzo, ico, ix, iy)
    d = ImageDraw.Draw(lienzo)
    for t in pos_textos:                       # los textos van al final: nada los tapa
        d.text(t["pos"], t["texto"], font=t["fuente"], fill=t["color"], stroke_width=t["trazo"],
               stroke_fill=t["color"])
    pares = [(a, b, solape(mascaras[a], mascaras[b])) for a in mascaras for b in mascaras if a < b]
    peor = max(pares, key=lambda p: p[2], default=(None, None, 0.0))
    mayor = max((area_visible(colocados[i]) for i in otros if i in colocados), default=0)
    medidas = {
        "protagonista_vs_mayor": round(area_visible(colocados[hero_i]) / mayor, 2) if hero_i is not None and mayor else None,
        "protagonista_ok": (hero_i is None or not mayor
                            or area_visible(colocados[hero_i]) / mayor >= MIN_HERO_VS_MAYOR - 1e-6),
        "solape_max": round(peor[2], 3), "par_solape": [peor[0], peor[1]] if peor[0] is not None else None,
        "solape_ok": peor[2] <= MAX_SOLAPE + 1e-6,
        "icono_libre": icono_libre, "icono_tam": icono_tam,
        "cabeza_sin_cortar": all(c.y >= 0 for i, c in colocados.items() if i < 3),
    }
    mapa = {"ancho": W, "alto": H,
            "sujetos": [{"indice": k.indice, "caja": [max(0, k.caja[0]), max(0, k.caja[1]), min(W, k.caja[2]),
                                                       min(H, k.caja[3])]} for k in colocados.values()],
            "textos": [{"indice": t["indice"], "texto": t["texto"], "caja": list(t["caja"])} for t in pos_textos],
            "medidas": medidas}
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
