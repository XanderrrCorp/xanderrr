"""Motor de render (sección 6): ejecuta edl.json con Pillow + FFmpeg.

La EDL es la única fuente de verdad: aquí no se decide nada, solo se dibuja lo
que dice. El audio se mezcla SIEMPRE completo (voz + efectos) y se normaliza.
"""
from __future__ import annotations

import io
import math
import json
import os
import random
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .config import RAIZ, leer_json
from .esquemas import EDL
from .estilos import cargar_estilo
from .proyecto import CarpetaProyecto
from .tira import _barrido, _golpe, _zumbido, armar_tira, niebla, pixelar, quitar_fondo_liso

W, H, FPS, SR = 1920, 1080, 30, 48000
# Fredoka (OFL, incluida en estudio/fuentes): redondeada, de YouTube; las demás son respaldo
FUENTES = [str(Path(__file__).parent / "fuentes" / "Fredoka-SemiBold.ttf"), "C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"]


def _fuente(tam: int):
    for f in FUENTES:
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _atras(x: float) -> float:
    """Sale rápido, se pasa un poquito y se asienta (entrada con rebote)."""
    x = min(max(x, 0.0), 1.0)
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _sale(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ recursos

def fondo_liso(w: int, h: int, color: str, semilla: int = 5) -> Image.Image:
    """Fondo de un color con trazos de lápiz suaves (estilo doodle): unas líneas un poco más claras,
    sueltas y torcidas, que dan textura sin distraer."""
    rng = np.random.default_rng(semilla)
    c = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (w, h), c)
    d = ImageDraw.Draw(img)
    claro = tuple(min(255, int(v + (255 - v) * 0.12)) for v in c)
    for _ in range(14):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        largo, ang = rng.uniform(120, 420), rng.uniform(-0.25, 0.25) + (0 if rng.random() < 0.6 else math.pi / 2)
        pts = [(x + k / 6 * largo * math.cos(ang) + rng.normal(0, 3), y + k / 6 * largo * math.sin(ang) + rng.normal(0, 3))
               for k in range(7)]
        d.line(pts, fill=claro, width=3, joint="curve")
    return img


def fondo_de_estilo(estilo, w: int, h: int, semilla: int) -> Image.Image:
    f = getattr(estilo, "fondo_montaje", None)
    if f is not None and f.tipo == "color":
        return fondo_liso(w, h, f.valor, semilla)
    if f is not None and f.tipo == "cuadricula":
        return papel_cuadriculado(w, h, semilla)
    return papel_arrugado(w, h, semilla)


def papel_cuadriculado(w: int, h: int, semilla: int = 5, paso: int = 72) -> Image.Image:
    """Hoja blanca de cuaderno cuadriculado, un poco arrugada: los pliegues del papel de siempre pasados
    a gris muy claro y una cuadrícula gris suave encima."""
    arrugas = np.asarray(papel_arrugado(w, h, semilla).convert("L"), np.float32)
    claro = 244 + (arrugas - arrugas.mean()) * 0.55                  # casi blanco, con sus pliegues
    img = Image.fromarray(np.clip(np.stack([claro, claro, claro + 2], -1), 0, 255).astype("uint8"), "RGB")
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for x in range(paso // 2, w, paso):
        d.line([(x, 0), (x, h)], fill=(150, 156, 168, 70), width=2)
    for y in range(paso // 2, h, paso):
        d.line([(0, y), (w, y)], fill=(150, 156, 168, 70), width=2)
    img = img.convert("RGBA")
    img.alpha_composite(capa)
    return img.convert("RGB")


def asegurar_fondo(raiz: Path, estilo, semilla: int) -> Path:
    """assets/papel_arrugado.png del proyecto: se hace una vez y se rehace si el estilo cambió de fondo
    (p. ej. de color liso a papel), para que un video viejo no se quede con el fondo de antes."""
    ruta = raiz / "assets" / "papel_arrugado.png"
    f = getattr(estilo, "fondo_montaje", None)
    firma = json.dumps(f.model_dump() if f is not None else None, sort_keys=True)
    marca = ruta.with_suffix(".fondo.json")
    if not ruta.exists() or not marca.exists() or marca.read_text(encoding="utf-8") != firma:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fondo_de_estilo(estilo, W, H, semilla).save(ruta)
        marca.write_text(firma, encoding="utf-8")
    return ruta


def papel_arrugado(w: int, h: int, semilla: int = 5) -> Image.Image:
    rng = np.random.default_rng(semilla)
    base = np.array([236, 227, 207], np.float32)
    grano = rng.normal(0, 5, (h, w, 1)).astype(np.float32)
    manchas = np.asarray(Image.fromarray((rng.random((h // 60 + 2, w // 60 + 2)) * 255).astype("uint8"))
                         .resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(30)),
                         np.float32)[:, :, None] / 255 - 0.5
    img = np.clip(base + grano + manchas * 26, 0, 255).astype("uint8")
    papel = Image.fromarray(img, "RGB")
    # pliegues: líneas claras y oscuras muy suaves
    capa = Image.new("L", (w, h), 128)
    d = ImageDraw.Draw(capa)
    r = random.Random(semilla)
    for _ in range(18):
        x0, y0 = r.randint(-200, w), r.randint(-200, h)
        ang = r.uniform(0, math.pi)
        largo = r.randint(400, 1400)
        pts = [(x0, y0)]
        for _ in range(4):
            ang += r.uniform(-0.35, 0.35)
            x0 += int(math.cos(ang) * largo / 4)
            y0 += int(math.sin(ang) * largo / 4)
            pts.append((x0, y0))
        d.line(pts, fill=r.choice([140, 116]), width=r.randint(1, 3))
    capa = capa.filter(ImageFilter.GaussianBlur(2.2))
    luz = np.asarray(capa, np.float32)[:, :, None] / 128
    img = np.clip(np.asarray(papel, np.float32) * luz, 0, 255)
    # viñeta suave
    yy, xx = np.mgrid[0:h, 0:w]
    v = 1 - 0.18 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return Image.fromarray(np.clip(img * v[:, :, None], 0, 255).astype("uint8"), "RGB")


def _sombra(rgba: Image.Image, radio: int = 16, alfa: int = 120, desplaz=(10, 14)) -> tuple[Image.Image, tuple]:
    a = rgba.split()[-1]
    m = 2 * radio
    s = Image.new("RGBA", (rgba.width + 2 * m, rgba.height + 2 * m), (0, 0, 0, 0))
    negro = Image.new("RGBA", rgba.size, (0, 0, 0, alfa))
    s.paste(negro, (m, m), a)
    return s.filter(ImageFilter.GaussianBlur(radio)), (desplaz[0] - m, desplaz[1] - m)


def _pixelar_zonas(img: Image.Image, zonas: list, bloque: int) -> Image.Image:
    img = img.copy()
    for x0, y0, x1, y1 in zonas:
        caja = (int(x0 * img.width), int(y0 * img.height), int(x1 * img.width), int(y1 * img.height))
        img.paste(pixelar(img.crop(caja), bloque), caja[:2])
    return img


class Escenario:
    """Compone el cuadro estático de cada clip (papel + recorte o recuadro)."""

    def __init__(self, raiz: Path, papel: Image.Image, comportamiento: dict[str, str]):
        self.raiz = raiz
        self.papel = papel
        self.comportamiento = comportamiento     # modo del estilo -> recorte | recuadro
        self.cache: dict = {}
        # clip -> (x, y, ancho, alto): dónde cae la imagen ORIGINAL completa en el cuadro,
        # para llevar cajas normalizadas de la imagen (focos, flechas) a píxeles
        self.ubicacion: dict[str, tuple[float, float, float, float]] = {}
        # clip -> capas sueltas (sombra y objeto con su posición) para animar entradas y vaivén
        self.capas: dict[str, tuple] = {}

    def animado(self, clip: dict, dx: float = 0.0, dy: float = 0.0, escala: float = 1.0) -> Image.Image | None:
        """El papel con el objeto (recorte o recuadro) movido o escalado; None si no tiene capas."""
        capas = self.capas.get(clip["id"])
        if capas is None:
            return None
        (sombra, (sx, sy)), (obj, (x, y)) = capas
        if getattr(self, "_papel_rgba", None) is None:
            self._papel_rgba = self.papel.convert("RGBA")      # una vez, no en cada cuadro
        lienzo = self._papel_rgba.copy()
        if abs(escala - 1) > 0.002:
            cx, cy = x + obj.width / 2, y + obj.height / 2
            obj = _escalar(obj, (max(1, int(obj.width * escala)), max(1, int(obj.height * escala))))
            sombra = _escalar(sombra, (max(1, int(sombra.width * escala)), max(1, int(sombra.height * escala))))
            x, y = cx - obj.width / 2, cy - obj.height / 2
            sx, sy = x + (sx - capas[1][1][0]) * escala, y + (sy - capas[1][1][1]) * escala
        lienzo.alpha_composite(sombra, (int(max(-sombra.width + 1, min(W - 1, sx + dx))), int(max(-sombra.height + 1, min(H - 1, sy + dy)))))
        ox, oy = int(x + dx), int(y + dy)
        if ox < W and oy < H and ox + obj.width > 0 and oy + obj.height > 0:
            recorte = (max(0, -ox), max(0, -oy), min(obj.width, W - ox), min(obj.height, H - oy))
            lienzo.alpha_composite(obj.crop(recorte), (max(0, ox), max(0, oy)))
        return lienzo.convert("RGB")

    def cuadro(self, clip: dict) -> Image.Image:
        zonas = next((e["zonas"] for e in clip["efectos"] if e["efecto"] == "pixelar"), None)
        clave = (clip["archivo"], clip["modo"], str(zonas), clip["id"])
        if clave in self.cache:
            return self.cache[clave]
        img = Image.open(self.raiz / clip["archivo"]).convert("RGB")
        if zonas:
            img = _pixelar_zonas(img, zonas, next(e.get("bloque", 26) for e in clip["efectos"] if e["efecto"] == "pixelar"))
        if clip["modo"] == "pantalla_completa":
            # sin papel: la imagen llena el cuadro (recortando lo que sobre del centro)
            k = max(W / img.width, H / img.height)
            d = img.resize((max(W, round(img.width * k)), max(H, round(img.height * k))), Image.Resampling.LANCZOS)
            x0, y0 = (d.width - W) // 2, (d.height - H) // 2
            self.ubicacion[clip["id"]] = (-x0, -y0, d.width, d.height)
            final = d.crop((x0, y0, x0 + W, y0 + H))
            self.cache[clave] = final
            if len(self.cache) > 6:
                self.cache.pop(next(iter(self.cache)))
            return final
        lienzo = self.papel.copy().convert("RGBA")
        # con un «dato» (texto + ícono a la izquierda) el objeto se corre a la derecha para dejarle sitio
        a_un_lado = any(e.get("efecto") == "dato" for e in clip.get("efectos", []))

        def _x(ancho: int) -> int:
            return int(W * 0.68 - ancho / 2) if a_un_lado else (W - ancho) // 2

        if self.comportamiento.get(clip["modo"], "recuadro") == "recorte":
            esquina = np.asarray(img.resize((40, 24)), np.float32)
            blanco = np.mean([esquina[0, 0], esquina[0, -1], esquina[-1, 0], esquina[-1, -1]]) > 232
            caja_max = (int(W * 0.46), int(H * 0.62)) if a_un_lado else (int(W * 0.84), int(H * 0.72))
            if blanco:
                # dibujo sobre fondo blanco: se «imprime» en el papel (multiplicar). Se recorta el
                # margen blanco y el dibujo se agranda hasta llenar el cuadro: un objeto chiquito en
                # medio de una hoja en blanco no le dice nada al espectador
                caja = _caja_contenido(img)
                d = _encajar(img.crop(caja), caja_max)
                k = d.width / (caja[2] - caja[0])
                x, y = _x(d.width), int(H * 0.50 - d.height / 2)
                self.ubicacion[clip["id"]] = (x - caja[0] * k, y - caja[1] * k, img.width * k, img.height * k)
                zona = np.asarray(lienzo.crop((x, y, x + d.width, y + d.height)).convert("RGB"), np.float32)
                mult = zona * np.asarray(d, np.float32) / 255
                lienzo.paste(Image.fromarray(mult.astype("uint8")), (x, y))
            else:
                rec = quitar_fondo_liso(img)
                caja = rec.getbbox() or (0, 0, img.width, img.height)
                rec = rec.crop(caja)
                ancho0 = rec.width
                rec = _encajar(rec, caja_max)
                x, y = _x(rec.width), int(H * 0.50 - rec.height / 2)
                k = rec.width / ancho0
                self.ubicacion[clip["id"]] = (x - caja[0] * k, y - caja[1] * k, img.width * k, img.height * k)
                s, (dx, dy) = _sombra(rec, 18, 110)
                lienzo.alpha_composite(s, (max(0, x + dx), max(0, y + dy)))
                lienzo.alpha_composite(rec, (x, y))
                self.capas[clip["id"]] = ((s, (x + dx, y + dy)), (rec, (x, y)))
        else:
            r = random.Random(clip["id"])
            ancho = W * (0.42 if a_un_lado else 0.56)
            d = img.resize((int(ancho), int(ancho * img.height / img.width)), Image.Resampling.LANCZOS)
            if d.height > H * 0.74:                     # imágenes altas: que la pila quepa
                k = H * 0.74 / d.height
                d = d.resize((int(d.width * k), int(d.height * k)), Image.Resampling.LANCZOS)
            conmarco, (gx, gy) = _foto_vieja(d, r)
            x, y = _x(conmarco.width), int(H * 0.48 - conmarco.height / 2)
            self.ubicacion[clip["id"]] = (x + gx, y + gy, d.width, d.height)
            s, (dx, dy) = _sombra(conmarco, 20, 130)
            lienzo.alpha_composite(s, (max(0, x + dx), max(0, y + dy)))
            lienzo.alpha_composite(conmarco, (x, y))
            self.capas[clip["id"]] = ((s, (x + dx, y + dy)), (conmarco, (x, y)))
        final = lienzo.convert("RGB")
        self.cache[clave] = final
        if len(self.cache) > 6:
            self.cache.pop(next(iter(self.cache)))
        return final


def _tarjeta(w: int, h: int, color: tuple, r: random.Random) -> Image.Image:
    """Cartulina de foto vieja: color crema con grano y bordes un poco más oscuros y gastados."""
    base = np.ones((h, w, 3), np.float32) * np.array(color, np.float32)
    rng = np.random.default_rng(r.randint(0, 10 ** 6))
    base += rng.normal(0, 3.5, (h, w, 1))
    yy, xx = np.mgrid[:h, :w]
    borde = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)).astype(np.float32)
    base *= (0.80 + 0.20 * np.clip(borde / 26, 0, 1))[..., None]          # orillas gastadas
    im = Image.fromarray(np.clip(base, 0, 255).astype("uint8"), "RGB").convert("RGBA")
    mascara = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, w - 1, h - 1), radius=10, fill=255)
    im.putalpha(mascara)
    return im


def _foto_vieja(foto: Image.Image, r: random.Random) -> tuple[Image.Image, tuple[float, float]]:
    """La imagen como foto vieja con borde crema, encima de otras dos tarjetas un poco giradas (como
    una pila de fotos sobre la mesa). Devuelve la pila y dónde quedó la foto dentro de ella."""
    marco = 24
    tw, th = foto.width + 2 * marco, foto.height + 2 * marco
    pad = 90
    pila = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
    for k, (dx, dy, giro, tono) in enumerate(((-26, 14, r.uniform(-5, -2.5), (226, 214, 188)),
                                               (30, -10, r.uniform(2.5, 5), (232, 221, 197)))):
        atras = _tarjeta(tw, th, tono, r).rotate(giro, expand=True, resample=Image.Resampling.BICUBIC)
        pila.alpha_composite(atras, (int(pad + dx + (tw - atras.width) / 2), int(pad + dy + (th - atras.height) / 2)))
    frente = _tarjeta(tw, th, (241, 233, 213), r)
    frente.paste(foto.convert("RGB"), (marco, marco))
    ImageDraw.Draw(frente).rectangle((marco - 1, marco - 1, marco + foto.width, marco + foto.height),
                                     outline=(120, 104, 80, 255), width=2)
    giro = r.uniform(-1.5, 1.5)
    frente = frente.rotate(giro, expand=True, resample=Image.Resampling.BICUBIC)
    fx, fy = pad + (tw - frente.width) / 2, pad + (th - frente.height) / 2
    pila.alpha_composite(frente, (int(fx), int(fy)))
    return pila, (fx + (frente.width - foto.width) / 2, fy + (frente.height - foto.height) / 2)


AGRANDAR_MAXIMO = 3.0      # más de eso ya se ve borroso


def _caja_contenido(img: Image.Image, umbral: int = 228, margen: float = 0.04) -> tuple[int, int, int, int]:
    """Caja de lo dibujado en una imagen de fondo blanco (con un poco de aire alrededor)."""
    a = np.asarray(img.convert("L").resize((img.width // 4 or 1, img.height // 4 or 1)))
    ys, xs = np.nonzero(a < umbral)
    if len(xs) < 20:
        return 0, 0, img.width, img.height
    x0, x1 = np.percentile(xs, [0.5, 99.5]) * 4
    y0, y1 = np.percentile(ys, [0.5, 99.5]) * 4
    mx, my = (x1 - x0) * margen + 8, (y1 - y0) * margen + 8
    return (int(max(0, x0 - mx)), int(max(0, y0 - my)), int(min(img.width, x1 + mx)), int(min(img.height, y1 + my)))


def _encajar(im: Image.Image, caja_max: tuple[int, int]) -> Image.Image:
    """Escala para llenar la caja sin salirse (agranda también, hasta AGRANDAR_MAXIMO)."""
    k = min(caja_max[0] / im.width, caja_max[1] / im.height, AGRANDAR_MAXIMO)
    if abs(k - 1) < 0.01:
        return im.copy()
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.Resampling.LANCZOS)


try:                        # OpenCV hace el zoom y el escalado de cada cuadro varias veces más rápido
    import cv2 as _cv2           # que Pillow; si no está instalado, se usa Pillow (mismo resultado)
    _cv2.setNumThreads(1)        # cada tramo ya corre en su propio proceso
except Exception:  # noqa: BLE001
    _cv2 = None


def _escalar(im: Image.Image, tam: tuple[int, int]) -> Image.Image:
    """Cambio de tamaño bilineal de cada cuadro (objetos que respiran o rebotan)."""
    if _cv2 is None:
        return im.resize(tam, Image.Resampling.BILINEAR)
    return Image.fromarray(_cv2.resize(np.asarray(im), tam, interpolation=_cv2.INTER_LINEAR), im.mode)


def _camara(img: Image.Image, s: float, foco: tuple[float, float], dx: float = 0, dy: float = 0) -> Image.Image:
    if s <= 1.0005 and not dx and not dy:
        return img
    s = max(s, 1.0 + (0.012 if (dx or dy) else 0))
    w, h = W / s, H / s
    cx = min(max(foco[0] * W + dx, w / 2), W - w / 2)
    cy = min(max(foco[1] * H + dy, h / 2), H - h / 2)
    x0, y0 = cx - w / 2, cy - h / 2
    if _cv2 is not None and img.size == (W, H):
        # la misma ventana que el box de Pillow (centros de píxel alineados), en una sola pasada
        kx, ky = w / W, h / H
        m = np.float32([[kx, 0, x0 + 0.5 * kx - 0.5], [0, ky, y0 + 0.5 * ky - 0.5]])
        out = _cv2.warpAffine(np.asarray(img), m, (W, H), flags=_cv2.INTER_LINEAR | _cv2.WARP_INVERSE_MAP,
                              borderMode=_cv2.BORDER_REPLICATE)
        return Image.fromarray(out, img.mode)
    return img.resize((W, H), Image.Resampling.BILINEAR, box=(x0, y0, x0 + w, y0 + h))


# ------------------------------------------------------------------ foco y flechas

ROJO = (226, 30, 30)


def _caja_px(ubic: tuple, caja: list) -> tuple[float, float, float, float]:
    ox, oy, sw, sh = ubic
    return ox + caja[0] * sw, oy + caja[1] * sh, ox + caja[2] * sw, oy + caja[3] * sh


def _elipse(caja_px: tuple, margen: int = 22) -> tuple[float, float, float, float]:
    """Elipse que abraza la caja, siempre dentro del cuadro y lejos de los subtítulos."""
    x0, y0, x1, y1 = caja_px
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = max(80, (x1 - x0) * 0.6), max(70, (y1 - y0) * 0.62)
    rx, ry = min(rx, W / 2 - margen), min(ry, (H - 190) / 2 - margen)
    cx = min(max(cx, margen + rx), W - margen - rx)
    cy = min(max(cy, margen + ry), H - 190 - margen - ry)
    return cx - rx, cy - ry, cx + rx, cy + ry


class Foco:
    """Oscurece todo menos lo nombrado y lo encierra en un círculo rojo trazado a mano."""

    def __init__(self):
        self.mascaras: dict = {}

    def mascara(self, clave, elipse) -> np.ndarray:
        if clave not in self.mascaras:
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).ellipse(elipse, fill=255)
            self.mascaras[clave] = np.asarray(m.filter(ImageFilter.GaussianBlur(28)), np.float32)[:, :, None] / 255
            if len(self.mascaras) > 4:
                self.mascaras.pop(next(iter(self.mascaras)))
        return self.mascaras[clave]

    def aplicar(self, img: Image.Image, clip: dict, ef: dict, ubic: tuple, tt: float) -> Image.Image:
        o, c = ef.get("oscurecer_fondo"), ef.get("circulo_rojo")
        if not ubic or not (o or c):
            return img
        caja = (o or c)["caja"]
        elipse = _elipse(_caja_px(ubic, caja))
        if o and tt >= o["en"]:
            a = _suave((tt - o["en"]) / 0.28) * o.get("nivel", 0.62)
            m = self.mascara((clip["id"], tuple(caja)), elipse)
            arr = np.asarray(img, np.float32)
            img = Image.fromarray((arr * (1 - a * (1 - m))).astype("uint8"))
        if c and tt >= c["en"]:
            p = _sale((tt - c["en"]) / c.get("trazo", 0.4))
            ini = -110 + c.get("giro", 0)
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(capa)
            fin = ini + 372 * p
            d.arc(elipse, ini, fin, fill=(255, 255, 255, 170), width=16)
            d.arc(elipse, ini, fin, fill=ROJO + (255,), width=10)
            # segundo trazo más fino y un poco corrido: se ve dibujado a mano
            e2 = (elipse[0] + 7, elipse[1] - 5, elipse[2] + 4, elipse[3] - 2)
            if p > 0.25:
                d.arc(e2, ini + 25, ini + 25 + 330 * (p - 0.25) / 0.75, fill=ROJO + (230,), width=5)
            img = img.convert("RGBA")
            img.alpha_composite(capa)
            img = img.convert("RGB")
        return img


def _flecha(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    if not ubic or tt < ef["en"]:
        return img
    x0, y0, x1, y1 = _caja_px(ubic, ef["caja"])
    cy = (y0 + y1) / 2
    izq = ef.get("desde", "izquierda") == "izquierda"
    punta = np.array([x0 - 14 if izq else x1 + 14, cy])
    direc = np.array([1.0, 0.35]) if izq else np.array([-1.0, 0.35])
    direc /= np.linalg.norm(direc)
    loc = tt - ef["en"]
    largo = 340 * _sale(loc / 0.26)
    punta = punta + direc * 5 * math.sin(loc * 7) * (loc > 0.3)      # vaivén suave
    cola = punta - direc * largo
    if largo < 20:
        return img
    normal = np.array([-direc[1], direc[0]])
    cab = 70
    base = punta - direc * cab
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for grosor, color in ((32, (255, 255, 255, 210)), (20, ROJO + (255,))):
        d.line([tuple(cola), tuple(base)], fill=color, width=grosor)
        extra = 7 if grosor > 25 else 0
        tri = [tuple(punta + direc * extra), tuple(base + normal * (40 + extra)), tuple(base - normal * (40 + extra))]
        d.polygon(tri, fill=color)
    img = img.convert("RGBA")
    img.alpha_composite(capa)
    return img.convert("RGB")


def _icono_advertencia(tam: int) -> Image.Image:
    im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = tam * 0.06
    tri = [(tam / 2, m), (tam - m, tam - m * 1.4), (m, tam - m * 1.4)]
    d.polygon(tri, fill=(20, 16, 12, 255))
    k = tam * 0.07
    d.polygon([(tam / 2, m + k * 1.6), (tam - m - k * 1.5, tam - m * 1.4 - k), (m + k * 1.5, tam - m * 1.4 - k)],
              fill=(255, 205, 40, 255))
    f = _fuente(int(tam * 0.5))
    caja = d.textbbox((0, 0), "!", font=f)
    d.text(((tam - (caja[2] - caja[0])) / 2 - caja[0], tam * 0.60 - (caja[3] - caja[1]) / 2 - caja[1]), "!",
           font=f, fill=(20, 16, 12, 255))
    return im


_ICONO = {}


def _poner_icono(img: Image.Image, ef: dict, tt: float) -> Image.Image:
    loc = tt - ef["en"]
    if loc < 0:
        return img
    if "base" not in _ICONO:
        _ICONO["base"] = _icono_advertencia(200)
    esc = 1.0 + 0.35 * math.exp(-loc * 9) * math.cos(loc * 16) if loc < 0.8 else 1.0
    esc *= _sale(loc / 0.12)
    if esc < 0.05:
        return img
    ic = _ICONO["base"].resize((max(1, int(200 * esc)),) * 2, Image.Resampling.BICUBIC)
    cx = W * (0.13 if ef.get("lado") == "izquierda" else 0.87)
    img = img.copy()
    img.paste(ic, (int(cx - ic.width / 2), int(H * 0.30 - ic.height / 2)), ic)
    return img


def _etiqueta_img(texto: str) -> Image.Image:
    """Etiqueta tipo sticker: fondo blanco, borde negro grueso, letra negra en negrita."""
    f = _fuente(64)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = d0.textbbox((0, 0), texto, font=f)
    tw, th = caja[2] - caja[0], caja[3] - caja[1]
    pad_x, pad_y, borde = 34, 20, 7
    im = Image.new("RGBA", (tw + 2 * pad_x + 16, th + 2 * pad_y + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 12, im.width - 4, im.height - 2), radius=22, fill=(0, 0, 0, 90))      # sombra
    d.rounded_rectangle((4, 4, im.width - 10, im.height - 10), radius=22, fill=(255, 255, 255, 255),
                        outline=(20, 16, 12, 255), width=borde)
    d.text((4 + pad_x - caja[0], 4 + pad_y - caja[1]), texto, font=f, fill=(20, 16, 12, 255))
    return im


def _poner_etiqueta(img: Image.Image, ef: dict, tt: float, fin: float) -> Image.Image:
    loc = tt - ef["en"]
    if loc < 0:
        return img
    clave = ("etq", ef["texto"])
    if clave not in _ICONO:
        _ICONO[clave] = _etiqueta_img(ef["texto"])
    base = _ICONO[clave]
    esc = _sale(loc / 0.1) * (1.0 + 0.22 * math.exp(-loc * 9) * math.cos(loc * 17))
    if tt > fin - 0.2:
        esc *= max(0.0, (fin - tt) / 0.2)
    if esc < 0.05:
        return img
    im = base.resize((max(1, int(base.width * esc)), max(1, int(base.height * esc))), Image.Resampling.BICUBIC)
    im = im.rotate(ef.get("giro", 0), expand=True, resample=Image.Resampling.BICUBIC)
    cx = W * (0.2 if ef.get("lado") == "izquierda" else 0.8)
    img = img.copy()
    img.paste(im, (int(cx - im.width / 2), int(H * 0.2 - im.height / 2)), im)
    return img


def _icono_si_no(tam: int, si: bool) -> Image.Image:
    """Círculo rojo con ✕ blanca (no) o verde con ✓ (sí), con borde blanco y sombra suave."""
    im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6, 10, tam - 2, tam - 2), fill=(0, 0, 0, 70))
    d.ellipse((2, 2, tam - 6, tam - 6), fill=(255, 255, 255, 255))
    color = (46, 184, 92, 255) if si else (226, 38, 38, 255)
    m = tam * 0.09
    d.ellipse((2 + m, 2 + m, tam - 6 - m, tam - 6 - m), fill=color)
    c, g = (tam - 4) / 2, max(4, int(tam * 0.11))
    if si:
        d.line([(c - tam * 0.2, c + tam * 0.01), (c - tam * 0.05, c + tam * 0.16), (c + tam * 0.22, c - tam * 0.15)],
               fill=(255, 255, 255, 255), width=g, joint="curve")
    else:
        k = tam * 0.16
        d.line([(c - k, c - k), (c + k, c + k)], fill=(255, 255, 255, 255), width=g)
        d.line([(c - k, c + k), (c + k, c - k)], fill=(255, 255, 255, 255), width=g)
    return im


def _texto_dato(texto: str) -> Image.Image:
    """El dato escrito grande en negro redondeado (como a mano en el cuaderno), sin caja."""
    f = _fuente(118)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = d0.textbbox((0, 0), texto, font=f)
    im = Image.new("RGBA", (caja[2] - caja[0] + 20, caja[3] - caja[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - caja[0], 10 - caja[1]), texto, font=f, fill=(20, 16, 12, 255))
    if im.width > W * 0.42:
        k = W * 0.42 / im.width
        im = im.resize((int(im.width * k), int(im.height * k)), Image.Resampling.LANCZOS)
    return im


def _poner_dato(img: Image.Image, ef: dict, tt: float, fin: float) -> Image.Image:
    """Un dato clave a la izquierda (ícono ✕/✓/⚠ arriba y el texto grande debajo) y una flecha curva
    negra que sale del objeto (a la derecha) y apunta al texto. Todo entra con rebote."""
    loc = tt - ef["en"]
    if loc < 0:
        return img
    salida = max(0.0, min(1.0, (fin - tt) / 0.2)) if tt > fin - 0.2 else 1.0
    img = img.convert("RGBA")
    cx = W * 0.27
    # la flecha se dibuja primero (queda debajo del texto)
    avance = _sale(max(0.0, loc - 0.15) / 0.35)
    if avance > 0.02:
        p0, p1, p2 = np.array([W * 0.53, H * 0.34]), np.array([W * 0.47, H * 0.17]), np.array([W * 0.41, H * 0.31])
        ts = np.linspace(0, avance, 40)
        pts = [tuple((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2) for t in ts]
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        d.line(pts, fill=(20, 16, 12, int(255 * salida)), width=9, joint="curve")
        if avance > 0.9:
            a, b = np.array(pts[-2]), np.array(pts[-1])
            u = (b - a) / (np.linalg.norm(b - a) + 1e-6)
            n = np.array([-u[1], u[0]])
            d.polygon([tuple(b + u * 22), tuple(b - u * 18 + n * 20), tuple(b - u * 18 - n * 20)],
                      fill=(20, 16, 12, int(255 * salida)))
        img.alpha_composite(capa)
    clave = ("dato", ef["texto"], ef.get("icono", "no"))
    if clave not in _ICONO:
        icono = _icono_advertencia(170) if ef.get("icono") == "alerta" else _icono_si_no(150, ef.get("icono") == "si")
        _ICONO[clave] = (icono, _texto_dato(ef["texto"]))
    icono, texto = _ICONO[clave]
    for k, (pieza, y, retraso) in enumerate(((icono, H * 0.33, 0.0), (texto, H * 0.53, 0.08))):
        l = loc - retraso
        if l < 0:
            continue
        esc = _sale(l / 0.12) * (1.0 + 0.25 * math.exp(-l * 9) * math.cos(l * 16)) * salida
        if esc < 0.05:
            continue
        im = pieza.resize((max(1, int(pieza.width * esc)), max(1, int(pieza.height * esc))), Image.Resampling.BICUBIC)
        img.alpha_composite(im, (int(cx - im.width / 2), int(y - im.height / 2)))
    return img.convert("RGB")


def _signo(tam: int, color) -> Image.Image:
    f = _fuente(tam)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = d0.textbbox((0, 0), "?", font=f, stroke_width=max(4, tam // 14))
    im = Image.new("RGBA", (caja[2] - caja[0] + 20, caja[3] - caja[1] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - caja[0], 10 - caja[1]), "?", font=f, fill=color,
                            stroke_width=max(4, tam // 14), stroke_fill=(20, 16, 12))
    return im


def _signos_pregunta(img: Image.Image, ef: dict, tt: float, fin: float) -> Image.Image:
    """2 o 3 «?» grandes que aparecen escalonados con rebote, se mecen y se van al final."""
    r = random.Random(ef.get("semilla", 0))
    colores = [(255, 214, 51), (255, 255, 255), (255, 94, 94)]
    lugares = [(0.31, 0.27), (0.69, 0.23), (0.34, 0.56), (0.66, 0.53)]
    r.shuffle(lugares)
    if ef.get("centro"):                      # un solo «?» blanco grande encima de la foto
        colores, lugares = [(255, 255, 255)], [(0.5, 0.47)]
    img = img.copy()
    for k in range(ef.get("cantidad", 2)):
        loc = tt - ef["en"] - 0.14 * k
        if loc < 0:
            continue
        tam = 300 if ef.get("centro") else r.randint(210, 290)
        clave = ("?", tam, k % 3)
        if clave not in _ICONO:
            _ICONO[clave] = _signo(tam, colores[k % 3])
        base = _ICONO[clave]
        esc = _sale(loc / 0.12) * (1.0 + 0.3 * math.exp(-loc * 8) * math.cos(loc * 15))
        esc *= 1 - _suave((tt - (fin - 0.25)) / 0.25) if tt > fin - 0.25 else 1
        if esc < 0.05:
            continue
        giro = (2 * math.sin(loc * 2.2)) if ef.get("centro") else r.uniform(-16, 16) + 7 * math.sin(loc * 3.2 + k)
        im = base.resize((max(1, int(base.width * esc)), max(1, int(base.height * esc))), Image.Resampling.BICUBIC)
        im = im.rotate(giro, expand=True, resample=Image.Resampling.BICUBIC)
        x, y = lugares[k]
        img.paste(im, (int(x * W - im.width / 2), int(y * H - im.height / 2 + 6 * math.sin(loc * 2.5 + k))), im)
    return img


def _globo_pregunta(img: Image.Image, loc: float) -> Image.Image:
    """Globo de pensamiento con «?» sobre el presentador, que entra con rebote."""
    if "globo" not in _ICONO:
        g = Image.new("RGBA", (420, 360), (0, 0, 0, 0))
        d = ImageDraw.Draw(g)
        nubes = [(60, 40, 250, 200), (160, 20, 360, 190), (40, 110, 220, 250), (170, 100, 380, 250), (110, 60, 300, 240)]
        for caja in nubes:                                     # borde negro
            d.ellipse((caja[0] - 6, caja[1] - 6, caja[2] + 6, caja[3] + 6), fill=(20, 16, 12, 255))
        for caja in nubes:
            d.ellipse(caja, fill=(255, 255, 255, 255))
        for cx, cy, r in ((300, 290, 26), (345, 335, 15)):     # burbujitas hacia la cabeza
            d.ellipse((cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5), fill=(20, 16, 12, 255))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 255))
        f = _fuente(150)
        c = d.textbbox((0, 0), "?", font=f)
        d.text((210 - (c[0] + c[2]) / 2, 140 - (c[1] + c[3]) / 2), "?", font=f, fill=(20, 16, 12, 255))
        _ICONO["globo"] = g
    esc = _sale(loc / 0.12) * (1 + 0.18 * math.exp(-loc * 8) * math.cos(loc * 15))
    if esc < 0.05:
        return img
    g = _ICONO["globo"]
    im = g.resize((max(1, int(g.width * esc)), max(1, int(g.height * esc))), Image.Resampling.BICUBIC)
    img = img.copy()
    img.paste(im, (int(W * 0.30 - im.width / 2), int(H * 0.25 - im.height / 2 + 4 * math.sin(loc * 3))), im)
    return img


_MONTAJE: dict = {}


_ESCALA_QUIETA: dict[tuple[int, int, int], Image.Image] = {}


def _cuadro_escala(papel: Image.Image, valor: int, loc: float) -> Image.Image:
    """Escala de peligro 0–10 sobre el papel. Mientras la flecha se mueve se dibuja cada cuadro; ya
    quieta (desde 1,3 s) el cuadro se reutiliza."""
    from .escala_peligro import dibujar

    clave = (valor, papel.width, papel.height)
    if loc >= 1.3 and clave in _ESCALA_QUIETA:
        return _ESCALA_QUIETA[clave].copy()
    img = papel.copy().convert("RGBA")
    img.alpha_composite(dibujar(valor, loc, papel.width, papel.height))
    img = img.convert("RGB")
    if loc >= 1.3:
        _ESCALA_QUIETA[clave] = img.copy()
    return img


def _montaje_foto(raiz: Path, papel: Image.Image, ef: dict, loc: float) -> Image.Image:
    """Foto REAL en marco rojo sobre el papel, con la mascota señalándola desde la izquierda."""
    clave = (ef["archivo"], ef.get("pose"))
    if clave not in _MONTAJE:
        foto = Image.open(raiz / ef["archivo"]).convert("RGB")
        ancho = int(W * 0.58)
        foto = foto.resize((ancho, int(ancho * foto.height / foto.width)), Image.Resampling.LANCZOS)
        if foto.height > H * 0.74:                                  # fotos altas: se recortan al centro
            alto = int(H * 0.74)
            y0 = (foto.height - alto) // 2
            foto = foto.crop((0, y0, ancho, y0 + alto))
        borde = 12
        marco = Image.new("RGB", (foto.width + 2 * borde, foto.height + 2 * borde), (226, 30, 30))
        marco.paste(foto, (borde, borde))
        if ef.get("sintetica"):
            # nunca se presenta como foto real: etiqueta visible en la esquina
            et = _texto_img("Recreación IA", 30, 5)
            marco.paste(et, (marco.width - et.width - borde - 10, marco.height - et.height - borde - 8), et)
        pose = None
        if ef.get("pose") and (raiz / ef["pose"]).exists():
            pose = quitar_fondo_liso(Image.open(raiz / ef["pose"]).convert("RGB"))
            caja = pose.getbbox()
            if caja:
                pose = pose.crop(caja)
            pose.thumbnail((int(W * 0.34), int(H * 0.78)), Image.Resampling.LANCZOS)
        _MONTAJE.clear()
        _MONTAJE[clave] = (marco, pose)
    marco, pose = _MONTAJE[clave]
    img = papel.copy().convert("RGBA")
    # la foto entra con un pequeño rebote y se acerca muy despacio
    esc = (0.92 + 0.08 * _sale(loc / 0.2)) * (1 + 0.025 * _suave(loc / 3.5))
    m = marco.resize((int(marco.width * esc), int(marco.height * esc)), Image.Resampling.BILINEAR).convert("RGBA")
    mx, my = int(W * 0.62 - m.width / 2), int(H * 0.46 - m.height / 2)
    sombra, (sx, sy) = _sombra(m, 18, 110)
    img.alpha_composite(sombra, (max(0, mx + sx), max(0, my + sy)))
    img.alpha_composite(m, (mx, my))
    if pose is not None:
        entra = _sale(loc / 0.28)
        px = int(-pose.width + (W * 0.02 + pose.width) * entra)
        img.alpha_composite(pose, (max(-pose.width + 1, px), int(H * 0.52 - pose.height / 2)))
    return img.convert("RGB")


class LectorClips:
    """Lee cuadro a cuadro los clips del presentador con FFmpeg (sin cargarlos enteros en memoria)."""

    def __init__(self, raiz: Path, ffmpeg: str):
        self.raiz, self.ffmpeg = raiz, ffmpeg
        self.clave, self.proc, self.leidos, self.ultimo = None, None, 0, None

    def cuadro(self, ef: dict, loc: float) -> Image.Image | None:
        clave = (ef["archivo"], ef["en"])
        if clave != self.clave:
            self.cerrar()
            filtro = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
            self.proc = subprocess.Popen([self.ffmpeg, "-v", "error", "-ss", str(ef.get("desde", 0)), "-i",
                                          str(self.raiz / ef["archivo"]), "-t", str(ef["dur"] + 0.5), "-vf", filtro,
                                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
            self.clave, self.leidos, self.ultimo = clave, 0, None
        quiero = int(loc * FPS)
        while self.leidos <= quiero:
            datos = self.proc.stdout.read(W * H * 3)
            if len(datos) < W * H * 3:
                break                                    # el clip se acabó: se repite el último cuadro
            self.ultimo = Image.frombytes("RGB", (W, H), datos)
            self.leidos += 1
        return self.ultimo

    def cerrar(self):
        if self.proc:
            self.proc.stdout.close()
            self.proc.kill()
            self.proc.wait()
        self.proc = None


def _lupa(img: Image.Image, ef: dict, ubic: tuple, tt: float) -> Image.Image:
    """Círculo con el detalle ampliado, unido con una línea al lugar exacto, y una flecha roja."""
    loc = tt - ef["en"]
    if not ubic or loc < 0:
        return img
    x0, y0, x1, y1 = _caja_px(ubic, ef["caja"])
    dx, dy = (x0 + x1) / 2, (y0 + y1) / 2
    lado = max(90, max(x1 - x0, y1 - y0) * 1.25)
    R = 190
    hacia = -1 if dx > W / 2 else 1
    lx = min(max(dx + hacia * 560, R + 60), W - R - 60)
    ly = min(max(dy - 170, R + 120), H - 210 - R)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    # 1) aro pequeño sobre el detalle
    r0 = max(26, lado * 0.35) * _sale(loc / 0.18)
    d.ellipse((dx - r0, dy - r0, dx + r0, dy + r0), outline=(90, 90, 90, 255), width=4)
    # 2) línea que sale hacia la lupa
    p = _sale((loc - 0.1) / 0.22)
    if p > 0:
        v = np.array([lx - dx, ly - dy])
        n = v / (np.linalg.norm(v) + 1e-6)
        a = np.array([dx, dy]) + n * r0
        b = np.array([lx, ly]) - n * R
        d.line([tuple(a), tuple(a + (b - a) * p)], fill=(90, 90, 90, 255), width=4)
    img = img.convert("RGBA")
    img.alpha_composite(capa)
    # 3) la lupa con el zoom
    esc = _sale((loc - 0.25) / 0.14) * (1 + 0.12 * math.exp(-max(0, loc - 0.25) * 8) * math.cos(max(0, loc - 0.25) * 16))
    if esc > 0.05:
        zona = img.convert("RGB").crop((int(dx - lado / 2), int(dy - lado / 2), int(dx + lado / 2), int(dy + lado / 2)))
        rr = max(4, int(R * esc))
        zoom = zona.resize((2 * rr, 2 * rr), Image.Resampling.LANCZOS)
        m = Image.new("L", zoom.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, 2 * rr - 1, 2 * rr - 1), fill=255)
        lupa = Image.new("RGBA", (2 * rr + 20, 2 * rr + 20), (0, 0, 0, 0))
        ImageDraw.Draw(lupa).ellipse((0, 0, 2 * rr + 19, 2 * rr + 19), fill=(255, 255, 255, 255))
        lupa.paste(zoom, (10, 10), m)
        ImageDraw.Draw(lupa).ellipse((1, 1, 2 * rr + 18, 2 * rr + 18), outline=(90, 90, 90, 255), width=4)
        img.alpha_composite(lupa, (int(lx - rr - 10), int(ly - rr - 10)))
    img = img.convert("RGB")
    # 4) flecha roja hacia la lupa
    caja_lupa = [(lx - R) / W, (ly - R) / H, (lx + R) / W, (ly + R) / H]
    return _flecha(img, {"en": ef["en"] + 0.45, "caja": caja_lupa, "desde": "izquierda" if hacia < 0 else "derecha"},
                   (0, 0, W, H), tt)


# ------------------------------------------------------------------ textos

def _texto_img(texto: str, tam: int, contorno: int, color=(255, 255, 255)) -> Image.Image:
    f = _fuente(tam)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = d0.textbbox((0, 0), texto, font=f, stroke_width=contorno)
    im = Image.new("RGBA", (caja[2] - caja[0] + 8, caja[3] - caja[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - caja[0], 4 - caja[1]), texto, font=f, fill=color, stroke_width=contorno,
                            stroke_fill=(0, 0, 0))
    return im


# ------------------------------------------------------------------ sonido

NOMBRES_VIEJOS = {"golpe": "golpe_grave", "golpe_suave": "golpe_grave"}


def _sfx(tipo: str, variante: int) -> np.ndarray:
    """Efectos PROVISIONALES sintetizados: se usan solo si la biblioteca no tiene
    archivos de ese tipo. Cada variante suena un poco distinta."""
    tipo = NOMBRES_VIEJOS.get(tipo, tipo)
    rng = np.random.default_rng(100 + variante)
    if tipo == "barrido":
        return _barrido(SR, 0.45 + 0.08 * variante, rng)
    if tipo == "golpe_grave":
        return _golpe(SR, 1.2 + 0.15 * variante)
    if tipo == "zumbido":
        return _zumbido(SR, 1.2)
    t = lambda d: np.arange(int(SR * d)) / SR
    if tipo == "latido":
        x = t(0.42)
        golpe = lambda t0: np.sin(2 * math.pi * (52 + 4 * variante) * (x - t0)) * np.exp(-np.clip(x - t0, 0, None) * 22) * (x >= t0)
        return (golpe(0) + 0.6 * golpe(0.17)) * 0.8
    if tipo == "subida_tension":
        x = t(1.6)
        f = 110 * (1 + 2.2 * (x / 1.6) ** 2) * (1 + 0.02 * variante)
        ruido = rng.normal(0, 0.25, len(x))
        return (np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.4 + ruido * 0.3) * (x / 1.6) ** 2
    if tipo == "alerta":
        x = t(0.36)
        f = np.where(x < 0.18, 880, 660) * (1 + 0.03 * variante)
        return np.sign(np.sin(2 * math.pi * np.cumsum(f) / SR)) * 0.12 * np.exp(-((x % 0.18) * 9))
    if tipo == "comico":
        x = t(0.3)
        f = 500 * (1 + 1.5 * np.sin(x * 40)) * (1 + 0.05 * variante)
        return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-x * 7) * 0.35
    if tipo == "piano_miedo":
        # nota grave de piano con un semitono encima (disonante) que queda sonando
        x = t(3.2)
        base = 55 * (1 + 0.02 * variante)
        nota = sum(a * np.sin(2 * math.pi * base * r * x) * np.exp(-x * (1.1 + 0.6 * k))
                   for k, (r, a) in enumerate([(1, 1.0), (2, 0.5), (3, 0.25), (16 / 15, 0.7), (32 / 15, 0.3)]))
        golpe = rng.normal(0, 1, len(x)) * np.exp(-x * 60) * 0.3
        return (nota * 0.35 + golpe) * np.minimum(1, x / 0.004)
    if tipo == "stinger_terror":
        # golpe de terror: impacto grave + chillido disonante de cuerdas que se apaga
        x = t(2.4)
        boom = np.sin(2 * math.pi * (48 * np.exp(-x * 2) + 28) * x) * np.exp(-x * 2.5)
        chillido = sum(np.sin(2 * math.pi * f * x * (1 + 0.004 * np.sin(2 * math.pi * 6 * x)))
                       for f in (880 * (1 + 0.01 * variante), 932, 1245)) * np.exp(-x * 1.8) * 0.12
        ruido = rng.normal(0, 1, len(x)) * np.exp(-x * 25) * 0.4
        return (boom * 0.7 + chillido + ruido) * 0.8
    if tipo == "camara":
        # disparo de cámara: dos clics secos (obturador que abre y cierra) con un soplo de ruido
        x = t(0.16)
        clic = lambda t0, f0: np.sin(2 * math.pi * f0 * (x - t0)) * np.exp(-np.clip(x - t0, 0, None) * 160) * (x >= t0)
        ruido = rng.normal(0, 1, len(x)) * np.exp(-x * 45) * 0.25
        return (clic(0, 3200 + 120 * variante) + 0.8 * clic(0.07, 2600) + ruido) * 0.5
    if tipo == "ruleta":
        # ruleta de premios: clics que se van frenando y un último «clac» al detenerse
        largo = 5.0
        x = t(largo)
        salida = np.zeros(len(x))
        clic = lambda n: np.sin(2 * math.pi * (2300 + 90 * variante) * np.arange(n) / SR) * np.exp(-np.arange(n) / SR * 380)
        ts, paso = [], 0.035
        tt = 0.0
        while tt < largo - 0.2:
            ts.append(tt)
            tt += paso
            paso *= 1.045                                   # cada clic un poco más lento
        for k, t0 in enumerate(ts):
            i = int(t0 * SR)
            n = min(int(0.03 * SR), len(x) - i)
            salida[i:i + n] += clic(n) * (0.5 + 0.5 * k / len(ts))
        i = int((ts[-1] + 0.02) * SR)
        n = min(int(0.12 * SR), len(x) - i)
        salida[i:i + n] += np.sin(2 * math.pi * 420 * np.arange(n) / SR) * np.exp(-np.arange(n) / SR * 40) * 0.8
        return salida * 0.45
    x = t(0.12)
    f0 = 620 + 70 * variante
    return np.sin(2 * math.pi * f0 * x * (1 + 1.5 * x)) * np.exp(-x * 40) * 0.5   # pop


def _sonido(tipo: str, variante: int, ffmpeg: str | None) -> tuple[np.ndarray, str | None]:
    """El archivo de la biblioteca (con licencia registrada) o, si no hay, el provisional."""
    from . import biblioteca

    tipo = NOMBRES_VIEJOS.get(tipo, tipo)
    if ffmpeg:
        archivos = sorted(biblioteca.utilizables("sfx", tipo))
        if archivos:
            ruta = archivos[(variante - 1) % len(archivos)]
            return biblioteca.leer_audio(ruta, ffmpeg, SR), ruta.relative_to(biblioteca.raiz()).as_posix()
    return _sfx(tipo, variante).astype(np.float32), None


def _igualar(x: np.ndarray, rms_objetivo: float) -> np.ndarray:
    """Lleva un sonido a una fuerza pareja (los archivos de Freesound vienen muy distintos: unos casi
    mudos, otros saturados), sin pasar del pico 0,98."""
    if not len(x):
        return x
    activo = x[np.abs(x) > 1e-3]
    rms = float(np.sqrt(np.mean(activo ** 2))) if len(activo) else 0.0
    if rms < 1e-5:
        return x
    ganancia = min(rms_objetivo / rms, 0.98 / max(float(np.max(np.abs(x))), 1e-6))
    return (x * ganancia).astype(np.float32)


def _envolvente(x: np.ndarray, ventana_s: float = 0.25) -> np.ndarray:
    """Qué tan fuerte suena la voz, suavizado (para bajar la música debajo de ella)."""
    n = max(1, int(SR * ventana_s))
    e = np.sqrt(np.convolve(x * x, np.ones(n) / n, mode="same"))
    return np.clip(e / (np.percentile(e[e > 1e-4], 90) if np.any(e > 1e-4) else 1), 0, 1)


def _mezclar_musica(musica: list, voz: np.ndarray, total: int, ffmpeg: str, usados: list) -> np.ndarray:
    from . import biblioteca

    pista = np.zeros(total, np.float32)
    fundido = int(SR * 0.6)
    for m in musica:
        ruta = biblioteca.raiz() / m["archivo"]
        if not ruta.exists():
            continue
        x = biblioteca.leer_audio(ruta, ffmpeg, SR)
        i0, i1 = int(m["inicio"] * SR), min(total, int(m["fin"] * SR))
        largo = i1 - i0
        seg = x[int(m.get("desde", 0) * SR):]
        if len(seg) < largo:                   # pista corta: se une consigo misma con un fundido largo
            reps = [seg]
            while sum(len(r) for r in reps) < largo + fundido:
                reps.append(seg)
            unido = reps[0]
            for r in reps[1:]:
                f = min(fundido * 3, len(r) // 2, len(unido) // 2)
                cruz = unido[-f:] * np.linspace(1, 0, f) + r[:f] * np.linspace(0, 1, f)
                unido = np.concatenate([unido[:-f], cruz, r[f:]])
            seg = unido
        seg = _igualar(seg[:largo].astype(np.float32), 0.12).copy()     # cada pista suena parecido de fuerte
        f = min(fundido, len(seg) // 2)
        if f:
            seg[:f] *= np.linspace(0, 1, f)
            seg[-f:] *= np.linspace(1, 0, f)
        ganancia = np.full(len(seg), m.get("volumen", 0.2), np.float32)
        for a, b in m.get("caidas", []):           # la música se cae antes de la revelación
            ca, cb = int(a * SR) - i0, int(b * SR) - i0
            if 0 <= ca < len(seg):
                ganancia[ca:max(ca, min(len(seg), cb + int(SR * 0.9)))] *= 0.08
        pista[i0:i0 + len(seg)] += seg * ganancia
        usados.append(m["archivo"])
    # ducking: la música baja cuando habla la voz
    return pista * (1 - 0.6 * _envolvente(voz[:total]))


def mezclar_audio(raiz: Path, edl: dict, ffmpeg: str | None = None) -> np.ndarray:
    total = int(edl["duracion_total"] * SR) + SR
    mezcla = np.zeros(total, np.float32)
    for v in edl["pistas"]["voz"]:
        with wave.open(str(raiz / v["archivo"])) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        i = int(v["inicio"] * SR)
        mezcla[i:i + len(x)] += x[: total - i]
    usados = []
    voz = mezcla.copy()
    musica = edl["pistas"].get("musica") or []
    if musica and ffmpeg:
        mezcla += _mezclar_musica(musica, voz, total, ffmpeg, usados)
    for s in edl["pistas"]["sfx"]:
        tipo, var = s["variante"].rsplit("_", 1)
        x, archivo = _sonido(s.get("tipo") or tipo, int(var), ffmpeg)
        if archivo:
            usados.append(archivo)
        tono = s.get("tono", 1.0)
        idx = np.arange(0, len(x) - 1, tono)
        x = np.interp(idx, np.arange(len(x)), x)
        if (edl.get("audio") or {}).get("igualar"):
            x = _igualar(x, 0.2)
        x = x * s.get("volumen", 0.7) * 0.6
        if s.get("duracion_max") and len(x) > s["duracion_max"] * SR:
            n = int(s["duracion_max"] * SR)
            x = (x[-n:] if s.get("termina_en") is not None else x[:n]).copy()
            f = min(len(x), int(0.03 * SR))                   # sin chasquido en el corte
            if s.get("termina_en") is not None:
                x[:f] *= np.linspace(0, 1, f)
            else:
                x[-f:] *= np.linspace(1, 0, f)
        # 14.7: la subida de tensión termina justo en el corte que anuncia
        i = int((s["termina_en"] * SR - len(x)) if s.get("termina_en") is not None else s["inicio"] * SR)
        if i < 0:
            x, i = x[-i:], 0
        mezcla[i:i + len(x)] += x[: max(0, total - i)]
    mezclar_audio.usados = usados
    return mezcla


# ------------------------------------------------------------------ render

# calidad del archivo final: «normal» es rápida; «maxima» comprime menos y tarda más (para subir a YouTube)
# «slow» apenas mejoraba sobre «medium» y le sumaba tiempo a PCs lentos; CRF 16 sigue muy por encima
# de lo que YouTube conserva al recomprimir
CALIDADES = {"normal": ("veryfast", "19", "192k"), "maxima": ("medium", "16", "320k")}


# ------------------------------------------------------------------ short vertical (9:16)

VW, VH = 1080, 1920
V_RECORTE = (864, 1080)          # ventana 4:5 que se toma del cuadro de 1920×1080 (se agranda 1,25×)
V_Y = 300                        # dónde empieza la ventana; arriba queda el título fijo
V_SUB_Y = 1440                   # centro de los subtítulos, sobre la parte baja de la ventana


def _fondo_vertical(img: Image.Image) -> Image.Image:
    """El mismo cuadro, borroso y oscuro, llenando la pantalla vertical (barato: se
    desenfoca en miniatura)."""
    chico = img.resize((96, 54), Image.Resampling.BILINEAR).crop((33, 0, 63, 54)).filter(ImageFilter.GaussianBlur(2.5))
    return ImageEnhance.Brightness(chico.resize((VW, VH), Image.Resampling.BILINEAR)).enhance(0.42)


def _titulo_vertical(texto: str) -> Image.Image:
    """Título fijo de arriba: amarillo con borde negro, en una o dos líneas."""
    palabras = texto.split()
    lineas = [texto]
    if len(palabras) > 1 and _texto_img(texto, 84, 12).width > VW - 60:
        corte = min(range(1, len(palabras)), key=lambda k: abs(len(" ".join(palabras[:k])) - len(" ".join(palabras[k:]))))
        lineas = [" ".join(palabras[:corte]), " ".join(palabras[corte:])]
    imgs = [_texto_img(l, 84, 12, (255, 214, 0)) for l in lineas]
    ancho = max(i.width for i in imgs)
    alto = sum(i.height for i in imgs) - 14 * (len(imgs) - 1)
    salida = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
    y = 0
    for i in imgs:
        salida.alpha_composite(i, ((ancho - i.width) // 2, y))
        y += i.height - 14
    if salida.width > VW - 40:
        k = (VW - 40) / salida.width
        salida = salida.resize((int(salida.width * k), int(salida.height * k)), Image.Resampling.LANCZOS)
    return salida


def _cuadro_vertical(img: Image.Image, cx: float, titulo: Image.Image | None) -> Image.Image:
    lienzo = _fondo_vertical(img)
    rw, rh = V_RECORTE
    x0 = int(min(max(cx * W - rw / 2, 0), W - rw))
    ventana = img.resize((VW, int(VW * rh / rw)), Image.Resampling.BICUBIC, box=(x0, 0, x0 + rw, rh))
    lienzo.paste(ventana, (0, V_Y))
    if titulo is not None:
        lienzo.paste(titulo, ((VW - titulo.width) // 2, max(40, (V_Y - titulo.height) // 2 + 10)), titulo)
    return lienzo


def _centro_x(c: dict, ef: dict, focos: dict, escenario: "Escenario", camara: tuple | None) -> float:
    """Dónde está lo importante del cuadro (0..1 en x) para centrar la ventana vertical:
    el foco del animal si Claude lo ubicó, si no el punto de la cámara, si no el medio."""
    x = None
    foco = focos.get(str(c.get("escena")))
    ubic = escenario.ubicacion.get(c["id"])
    if foco and ubic and foco.get("caja"):
        a, _, b, _ = _caja_px(ubic, foco["caja"])
        x = (a + b) / 2
    elif ubic:
        x = ubic[0] + ubic[2] / 2
    if x is None:
        return 0.5
    if camara:
        s, fx = camara
        if s > 1.0005:
            w = W / s
            cam = min(max(fx * W, w / 2), W - w / 2)
            x = (x - (cam - w / 2)) * s
    return min(max(x / W, 0.0), 1.0)


def _salida() -> tuple[int, int, int]:
    """Resolución y cuadros por segundo del archivo final (config/render.json); se dibuja
    siempre en 1920×1080 y FFmpeg escala al tamaño pedido."""
    from .config import RAIZ

    ruta = RAIZ / "config" / "render.json"
    datos = leer_json(ruta) if ruta.exists() else {}
    return int(datos.get("ancho", 1920)), int(datos.get("alto", 1080)), int(datos.get("fps", 30))


def renderizar(carpeta: CarpetaProyecto, ffmpeg: str, destino: Path | None = None, desde: float = 0.0,
               hasta: float | None = None, avisar=print, calidad: str = "normal",
               salida: tuple[int, int, int] | None = None, vertical: bool = False,
               procesos: int | None = None, solo_video: bool = False) -> Path:
    """vertical=True arma el short 9:16 (1080×1920): la escena de 1920×1080 se dibuja
    igual y se toma una ventana 4:5 que sigue al animal, con fondo borroso, título fijo
    arriba y subtítulos grandes.

    Un video completo se parte en tramos (siempre en un corte entre escenas) que se dibujan a la
    vez en varios núcleos y se unen al final: el mismo resultado, varias veces más rápido."""
    global FPS
    ancho, alto, fps = salida or _salida()
    if vertical:
        ancho, alto = VW, VH
    if not solo_video and codificador(ffmpeg) == "h264_nvenc":
        avisar("Codificando con la tarjeta NVIDIA (el procesador queda libre para dibujar)")
    if not solo_video and desde == 0 and hasta is None:
        n = _procesos(procesos)
        if n > 1:
            hecho = _renderizar_paralelo(carpeta, ffmpeg, destino, avisar, calidad, (ancho, alto, fps), vertical, n)
            if hecho is not None:
                return hecho
    anterior, FPS = FPS, fps
    try:
        return _renderizar(carpeta, ffmpeg, destino, desde, hasta, avisar, calidad, ancho, alto, vertical, solo_video)
    finally:
        FPS = anterior


_CODIFICADOR: dict[str, str] = {}


def codificador(ffmpeg: str) -> str:
    """«h264_nvenc» si hay una tarjeta NVIDIA que codifique (se prueba una vez con un video mínimo);
    si no, «libx264» (el procesador). XANDART_CODIFICADOR=cpu obliga a usar el procesador."""
    if ffmpeg in _CODIFICADOR:
        return _CODIFICADOR[ffmpeg]
    elegido = "libx264"
    if os.environ.get("XANDART_CODIFICADOR", "").lower() not in ("cpu", "libx264"):
        try:
            r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                                "color=c=black:s=320x240:r=30:d=0.5", "-c:v", "h264_nvenc", "-f", "null", "-"],
                               capture_output=True, timeout=30)
            if r.returncode == 0:
                elegido = "h264_nvenc"
        except Exception:  # noqa: BLE001 — sin NVIDIA (o sin driver): el procesador
            pass
    _CODIFICADOR[ffmpeg] = elegido
    return elegido


def _argumentos_codificador(ffmpeg: str, preset: str, crf: str, hilos_x264: str | None) -> list[str]:
    if codificador(ffmpeg) == "h264_nvenc":
        # la tarjeta de video codifica y el procesador queda libre para dibujar los cuadros;
        # cq ≈ crf + 3 da una calidad parecida a la de x264
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", str(int(crf) + 3),
                "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", preset, "-crf", crf, *(["-threads", hilos_x264] if hilos_x264 else [])]


def _procesos(pedidos: int | None) -> int:
    """Cuántos tramos a la vez. Por defecto la mitad de los núcleos (hasta 4) y solo los que quepan
    en la memoria libre: con más, el PC se traba y el render hasta va más lento."""
    if pedidos:
        return max(1, int(pedidos))
    try:
        conf = int(leer_json(RAIZ / "config" / "render.json").get("procesos") or 0)
    except Exception:  # noqa: BLE001
        conf = 0
    if conf:
        return max(1, conf)
    n = min(4, (os.cpu_count() or 2) // 2)
    libre = memoria_libre_gb()
    if libre is not None:
        n = min(n, int((libre - 1.0) // 1.2))          # ~1,2 GB por tramo y 1 GB para el resto del PC
    return max(1, n)


def memoria_libre_gb() -> float | None:
    """Memoria RAM libre ahora mismo (None si no se puede saber)."""
    try:
        if os.name == "nt":
            import ctypes

            class _Estado(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            e = _Estado()
            e.dwLength = ctypes.sizeof(_Estado)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(e)):
                return e.ullAvailPhys / 1024 ** 3
            return None
        with open("/proc/meminfo", encoding="ascii") as f:
            for linea in f:
                if linea.startswith("MemAvailable:"):
                    return int(linea.split()[1]) / 1024 ** 2
    except Exception:  # noqa: BLE001
        return None
    return None


def tramos(edl: dict, n: int, minimo_s: float = 25.0) -> list[tuple[float, float]]:
    """Parte el video en n tramos parecidos, cortando siempre donde empieza una escena con corte
    seco (nunca en medio de un fundido). Tramos muy cortos no valen la pena: se juntan."""
    total = float(edl["duracion_total"])
    cortes = sorted({float(c["inicio"]) for c in edl["pistas"]["escenas"]
                     if c["inicio"] > 0 and c.get("transicion_entrada", "corte") == "corte"})
    limites = [0.0]
    for k in range(1, n):
        objetivo = total * k / n
        if not cortes:
            break
        mejor = min(cortes, key=lambda x: abs(x - objetivo))
        if mejor - limites[-1] >= minimo_s and total - mejor >= minimo_s:
            limites.append(mejor)
    limites.append(total)
    return list(zip(limites[:-1], limites[1:]))


def _renderizar_paralelo(carpeta: CarpetaProyecto, ffmpeg: str, destino: Path | None, avisar, calidad: str,
                         salida: tuple[int, int, int], vertical: bool, n: int) -> Path | None:
    import concurrent.futures as cf
    import sys

    from .editor import edl_con_ediciones

    raiz = carpeta.ruta
    edl = edl_con_ediciones(raiz)
    partes = tramos(edl, n)
    if len(partes) < 2:
        return None                                   # video corto: en uno solo
    destino = destino or raiz / "render" / "final.mp4"
    destino.parent.mkdir(parents=True, exist_ok=True)
    # lo que los tramos leen se prepara una vez aquí (así ninguno escribe a la vez que otro)
    proyecto = carpeta.cargar()
    asegurar_fondo(raiz, cargar_estilo(proyecto.estilo), proyecto.semilla % 1000)
    esc = carpeta.cargar_escenas()
    if esc.niveles:
        armar_tira(esc, cargar_estilo(proyecto.estilo), raiz, seed=proyecto.semilla)
    carpeta_tramos = destino.parent / "tramos"
    shutil.rmtree(carpeta_tramos, ignore_errors=True)
    carpeta_tramos.mkdir(parents=True)
    avisar(f"  render en {len(partes)} tramos a la vez ({n} núcleos)")
    procs, registros = [], []
    # en Windows: sin ventanas negras y con prioridad baja, para que el PC siga usable mientras tanto
    sin_ventana = (0x08000000 | 0x00004000) if os.name == "nt" else 0
    from .plataforma import contexto

    entorno = {**os.environ, "XANDART_ESPACIO": contexto.espacio_actual() or ""}   # mismo estilo que aquí
    for k, (a, b) in enumerate(partes):
        cmd = [sys.executable, "-m", "estudio.render_tramo", str(raiz), str(carpeta_tramos / f"t{k:02d}.mp4"),
               f"{a:.6f}", f"{b:.6f}", calidad, str(salida[0]), str(salida[1]), str(salida[2]),
               "1" if vertical else "0", str(max(1, (os.cpu_count() or 2) // (2 * len(partes))))]
        # lo que el tramo diga va a un archivo: un tubo lleno lo dejaría colgado
        registro = open(carpeta_tramos / f"t{k:02d}.log", "wb")  # noqa: SIM115 — se cierra al terminar
        procs.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=registro, creationflags=sin_ventana,
                                      env=entorno))
        registros.append(registro)
    # mientras dibujan: se mezcla el audio y se informa el avance
    with cf.ThreadPoolExecutor(1) as ex:
        audio = ex.submit(mezclar_audio, raiz, edl, ffmpeg)
        total = edl["duracion_total"]
        import time

        while any(p.poll() is None for p in procs):
            hecho = sum(_avance(carpeta_tramos / f"t{k:02d}.mp4") for k in range(len(partes)))
            avisar(f"  render {min(hecho, total) / 60:.1f} / {total / 60:.1f} min")
            time.sleep(5)
        mezcla = audio.result()
    for r in registros:
        r.close()
    fallidos = [k for k, p in enumerate(procs) if p.returncode != 0]
    if fallidos:
        # no se pierde el video: se guarda por qué falló y se hace en un solo proceso, como antes
        detalle = (carpeta_tramos / f"t{fallidos[0]:02d}.log").read_text("utf-8", "replace")[-1500:]
        (destino.parent / "render_paralelo_error.txt").write_text(detalle, encoding="utf-8")
        avisar("  un tramo del render falló: sigo en un solo proceso (más lento, mismo resultado)")
        shutil.rmtree(carpeta_tramos, ignore_errors=True)
        return None
    # unir los tramos (sin volver a comprimir) y ponerles el audio
    lista = carpeta_tramos / "lista.txt"
    lista.write_text("".join(f"file '{(carpeta_tramos / f't{k:02d}.mp4').as_posix()}'\n" for k in range(len(partes))),
                     encoding="utf-8")
    video_tmp = destino.with_suffix(".video.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", str(video_tmp)], check=True)
    _mezclar_y_unir(raiz, edl, ffmpeg, destino, video_tmp, mezcla, calidad)
    shutil.rmtree(carpeta_tramos, ignore_errors=True)
    return destino


def _avance(archivo: Path) -> float:
    """Segundos ya dibujados de un tramo (lo escribe el propio tramo al lado del video)."""
    try:
        return float(archivo.with_suffix(".avance").read_text() or 0)
    except (OSError, ValueError):
        return 0.0


def _renderizar(carpeta: CarpetaProyecto, ffmpeg: str, destino: Path | None, desde: float, hasta: float | None,
                avisar, calidad: str, ancho: int, alto: int, vertical: bool = False, solo_video: bool = False) -> Path:
    preset, crf, audio_kbps = CALIDADES.get(calidad, CALIDADES["normal"])
    raiz = carpeta.ruta
    from .editor import edl_con_ediciones

    edl = edl_con_ediciones(raiz)           # la edición automática + los cambios hechos en el editor
    EDL.model_validate(edl)
    proyecto = carpeta.cargar()
    estilo = cargar_estilo(proyecto.estilo)
    esc = carpeta.cargar_escenas()
    destino = destino or raiz / "render" / "final.mp4"
    destino.parent.mkdir(parents=True, exist_ok=True)
    papel_ruta = asegurar_fondo(raiz, estilo, proyecto.semilla % 1000)
    papel = Image.open(papel_ruta).convert("RGB").resize((W, H))
    escenario = Escenario(raiz, papel, estilo.comportamiento_montaje)
    hilos_x264 = os.environ.get("XANDART_HILOS_X264")

    # tira (15): bases a 1080 de alto, con niebla a los lados para centrar cualquier nivel
    tira = None
    if esc.niveles:
        armada = armar_tira(esc, estilo, raiz, seed=proyecto.semilla, guardar=not solo_video)
        t = armada.t
        esc_f = H / armada.normal.height
        pad = W // 2
        fondo = niebla(int(armada.normal.width * esc_f) + 2 * pad, H, t).convert("RGBA")
        bases = {}
        for nombre, img in (("n", armada.normal), ("p", armada.pixelada)):
            b = fondo.copy()
            b.alpha_composite(img.resize((int(img.width * esc_f), H), Image.Resampling.LANCZOS), (pad, 0))
            bases[nombre] = b.convert("RGB")
        cx = [int(c * esc_f) + pad for c in armada.centros_x]
        vx0, vy0, vx1, vy1 = (int(v * esc_f) for v in armada.caja_villano)
        tira = {"bases": bases, "cx": cx, "caja": (vx0 + pad, vy0, vx1 + pad, vy1),
                "g": int(t.borde_grosor * esc_f), "bloque": int(t.pixel_bloque * esc_f), "color": t.brillo_villano}

    def cuadro_tira(centro: float, pixelado: bool, bloque_revelar: int | None = None) -> Image.Image:
        base = tira["bases"]["p" if pixelado else "n"]
        x0 = int(min(max(centro - W / 2, 0), base.width - W))
        im = base.crop((x0, 0, x0 + W, H))
        if bloque_revelar and bloque_revelar > 1:
            a, b, c, d = tira["caja"]
            g = tira["g"]
            zona = im.crop((a + g - x0, b + g, c - g - x0, d - g))
            im.paste(pixelar(zona, bloque_revelar), (a + g - x0, b + g))
        return im

    subs = edl["pistas"]["subtitulos"]
    textos = edl["pistas"]["textos"]
    cache_txt: dict = {}
    clips = edl["pistas"]["escenas"]
    total = edl["duracion_total"] if hasta is None else min(hasta, edl["duracion_total"])
    n0, n1 = int(desde * FPS), int(total * FPS)

    direccion = leer_json(raiz / "direccion.json") if (raiz / "direccion.json").exists() else {}
    focos = direccion.get("focos") or {}
    titulo_v = _titulo_vertical(direccion["short"]["titulo"]) if vertical and direccion.get("short") else None
    cx_suave, clip_previo = 0.5, None
    lado = (VW, VH) if vertical else (W, H)
    video_tmp = destino.with_suffix(".video.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{lado[0]}x{lado[1]}", "-r", str(FPS), "-i", "-",
                             *(["-vf", f"scale={ancho}:{alto}:flags=lanczos"] if (ancho, alto) != lado else []),
                             *_argumentos_codificador(ffmpeg, preset, crf, hilos_x264),
                             "-profile:v", "high", "-g", str(FPS * 2), "-bf", "2",
                             "-pix_fmt", "yuv420p", str(video_tmp)], stdin=subprocess.PIPE,
                            stderr=(registro_ffmpeg := open(destino.with_suffix(".ffmpeg.log"), "wb")))  # noqa: SIM115

    def _ffmpeg_cayo(ex: Exception) -> RuntimeError:
        """ffmpeg se cerró a mitad: se dice por qué (su mensaje), no solo «Invalid argument»."""
        proc.kill()
        registro_ffmpeg.close()
        dijo = destino.with_suffix(".ffmpeg.log").read_text("utf-8", "replace").strip()[-400:]
        libre = memoria_libre_gb()
        memoria = f" (memoria libre: {libre:.1f} GB)" if libre is not None else ""
        return RuntimeError(f"el programa que arma el video (ffmpeg) se cerró{memoria}: {dijo or ex}")

    temblor = random.Random(proyecto.semilla)
    capa_foco = Foco()
    lector = LectorClips(raiz, ffmpeg)
    ultimo: Image.Image | None = None
    ci = 0
    for n in range(n0, n1):
        tt = n / FPS
        while ci + 1 < len(clips) and clips[ci + 1]["inicio"] <= tt:
            ci += 1
        c = clips[ci]
        loc = tt - c["inicio"]
        dur = c["fin"] - c["inicio"]
        ef = {e["efecto"]: e for e in c["efectos"]}
        camara = None
        # --- imagen base del clip
        if c["modo"] == "tira" and tira:
            e = ef["tira_deslizar_a_nivel"]
            if e.get("pasar"):
                cen = tira["cx"][0] + (tira["cx"][-1] - tira["cx"][0]) * _suave(loc / max(0.5, dur))
            else:
                d0, d1 = e["desde"] - 1, e["hasta"] - 1
                cen = tira["cx"][d0] + (tira["cx"][d1] - tira["cx"][d0]) * _suave(loc / min(0.8, dur * 0.5))
            img = cuadro_tira(cen, e.get("villano_pixelado", True))
            if e.get("temblor") and loc > 0.8:
                amp = 5 * min(1, (loc - 0.8) / 1.5)
                img = _camara(img, 1.02, (0.5, 0.5), temblor.uniform(-amp, amp), temblor.uniform(-amp, amp))
        elif "revelar_pixelado" in ef and tira and loc < ef["revelar_pixelado"]["duracion"]:
            niv = ef["revelar_pixelado"]["nivel"] - 1
            if loc < 0.55:
                img = cuadro_tira(tira["cx"][niv], True)
            else:
                b = int(round(tira["bloque"] * (1 - _suave((loc - 0.55) / 0.4)))) or 1
                img = cuadro_tira(tira["cx"][niv], False, b if b > 1 else None)
        else:
            base = escenario.cuadro(c)
            entrada = next((ef[k] for k in ("entrada_abajo", "entrada_lado", "entrada_rebote") if k in ef), None)
            vaiven = ef.get("vaiven")
            if entrada or vaiven:
                ddx = ddy = 0.0
                esc_obj = 1.0
                if entrada and loc < entrada.get("dur", 0.42):
                    p = loc / entrada.get("dur", 0.42)
                    if "entrada_abajo" in ef:
                        ddy = (1 - _atras(p)) * H * 0.75
                    elif "entrada_lado" in ef:
                        ddx = (1 - _atras(p)) * W * 0.7 * (-1 if entrada.get("desde") == "izquierda" else 1)
                    else:
                        esc_obj = 0.5 + 0.5 * _atras(p)
                if vaiven:
                    ddy += math.sin(2 * math.pi * vaiven.get("hz", 0.7) * loc + vaiven.get("fase", 0)) * vaiven.get("px", 6)
                    esc_obj *= 1 + 0.008 * math.sin(2 * math.pi * vaiven.get("hz", 0.7) * 2 * loc)
                movido = escenario.animado(c, ddx, ddy, esc_obj)
                if movido is not None:
                    base = movido
            off = ef["revelar_pixelado"]["duracion"] if "revelar_pixelado" in ef else 0.0
            p = (loc - off) / max(0.3, dur - off)
            mov = c.get("movimiento")
            s, foco = 1.0, (0.5, 0.5)
            if mov:
                foco = tuple(mov.get("punto_foco") or (0.5, 0.5))
                if mov["tipo"] == "zoom_golpe":
                    golpe = ef.get("zoom_golpe", {}).get("en", c["inicio"] + dur * 0.35) - c["inicio"]
                    s = 1.0 + (mov["a"] - 1.0) * _sale((loc - golpe) / 0.16) if loc >= golpe else 1.0
                elif mov["tipo"] == "entrada_rebote":
                    # leve rebote al entrar: se asienta en medio segundo
                    s = 1.0 + (mov["de"] - 1.0) * math.exp(-loc * 6.5) * abs(math.cos(loc * 11))
                else:
                    s = mov["de"] + (mov["a"] - mov["de"]) * _suave(p)
                if mov["tipo"] == "paneo_lento" and "paneo_lento" in ef:
                    h2 = ef["paneo_lento"]["hasta"]
                    foco = (foco[0] + (h2[0] - foco[0]) * _suave(p), foco[1] + (h2[1] - foco[1]) * _suave(p))
            if "reencuadre" in ef and tt >= ef["reencuadre"]["en"]:
                r = ef["reencuadre"]
                s = r["escala"] + 0.015 * _suave((tt - r["en"]) / max(0.5, c["fin"] - r["en"]))
                foco = tuple(r["punto_foco"])
            if "rafaga" in ef:
                r = ef["rafaga"]
                s, foco_r = 1.0, tuple(r.get("punto_foco") or (0.5, 0.5))
                for t_k, esc_k in zip(r["tiempos"], r["escalas"]):
                    if tt >= t_k:
                        s = s + (esc_k - s) * _sale((tt - t_k) / 0.07)
                foco = foco_r
            if "oscurecer_fondo" in ef or "circulo_rojo" in ef or "flecha" in ef or "lupa" in ef:
                ubic = escenario.ubicacion.get(c["id"])
                base = capa_foco.aplicar(base, c, ef, ubic, tt)
                if "flecha" in ef:
                    base = _flecha(base, ef["flecha"], ubic, tt)
                if "lupa" in ef:
                    base = _lupa(base, ef["lupa"], ubic, tt)
            dx = dy = 0.0
            if "temblor_leve" in ef:
                a = ef["temblor_leve"].get("amplitud", 3)
                dx, dy = temblor.uniform(-a, a), temblor.uniform(-a, a)
            img = _camara(base, s, foco, dx, dy)
            camara = (s, foco[0])
        # --- transición y destellos
        if c["transicion_entrada"] == "fundido_corto" and loc < 0.25 and ultimo is not None:
            img = Image.blend(ultimo, img, _suave(loc / 0.25))
        if "destello_rojo" in ef:
            dt = tt - ef["destello_rojo"]["en"]
            if 0 <= dt < 0.6:
                img = Image.blend(img, Image.new("RGB", (W, H), (255, 42, 42)), 0.55 * math.exp(-dt * 6))
        if any(img is v for v in escenario.cache.values()):
            img = img.copy()           # nunca escribir sobre el cuadro guardado en caché
        r = ef.get("reaccion_presentador")
        en_reaccion = bool(r and r["en"] <= tt < r["en"] + r["dur"])
        if en_reaccion:
            cuadro = lector.cuadro(r, tt - r["en"])
            if cuadro is not None:
                img = cuadro.copy()
                if r.get("globo"):
                    img = _globo_pregunta(img, tt - r["en"] - 0.25)
        v_real, f_real = ef.get("video_real"), ef.get("foto_real")
        if not en_reaccion and v_real and v_real["en"] <= tt < v_real["en"] + v_real["dur"]:
            cuadro = lector.cuadro(v_real, tt - v_real["en"])
            if cuadro is not None:
                img, en_reaccion = cuadro.copy(), True
        if not en_reaccion and f_real and f_real["en"] <= tt < f_real["en"] + f_real["dur"]:
            img, en_reaccion = _montaje_foto(raiz, papel, f_real, tt - f_real["en"]), True
        esc_p = ef.get("escala_peligro")
        if not en_reaccion and esc_p and esc_p["en"] <= tt < esc_p["en"] + esc_p["dur"]:
            img, en_reaccion = _cuadro_escala(papel, esc_p["valor"], tt - esc_p["en"]), True
        if "icono_advertencia" in ef and not en_reaccion:
            img = _poner_icono(img, ef["icono_advertencia"], tt)
        if "etiqueta" in ef and not en_reaccion:
            img = _poner_etiqueta(img, ef["etiqueta"], tt, c["fin"])
        if "signos_pregunta" in ef and not en_reaccion:
            img = _signos_pregunta(img, ef["signos_pregunta"], tt, c["fin"])
        if "dato" in ef and not en_reaccion:
            img = _poner_dato(img, ef["dato"], tt, c["fin"])
        if vertical:
            if en_reaccion or c["modo"] == "tira" or camara is None:
                objetivo = 0.5
            else:
                objetivo = _centro_x(c, ef, focos, escenario, camara)
            if clip_previo != c["id"]:
                cx_suave = objetivo                 # en el corte se salta directo
            else:
                cx_suave += (objetivo - cx_suave) * min(1.0, 4.0 / FPS)
            clip_previo = c["id"]
            horizontal = img                        # los fundidos mezclan cuadros de 1920×1080
            img = _cuadro_vertical(img, cx_suave, titulo_v)
        # --- textos en pantalla
        for t in textos if not vertical else ():
            if t["inicio"] <= tt < t["fin"]:
                k = ("T", t["texto"])
                if k not in cache_txt:
                    titulo = t["texto"].capitalize() if t["texto"].isupper() else t["texto"]
                    cache_txt[k] = _texto_img(titulo, 92, 11)          # título arriba: blanco con borde negro
                ti = cache_txt[k]
                a = _suave((tt - t["inicio"]) / 0.12)
                if a < 1:
                    ti2 = ti.copy()
                    ti2.putalpha(ti.split()[-1].point(lambda v: int(v * a)))
                else:
                    ti2 = ti
                img.paste(ti2, ((W - ti.width) // 2, 26), ti2)
        # --- subtítulo
        for sb in subs:
            if sb["inicio"] <= tt < sb["fin"]:
                k = ("S", sb["texto"])
                if k not in cache_txt:
                    cache_txt[k] = _texto_img(sb["texto"], 66, 8)
                si = cache_txt[k]
                if vertical:
                    k = ("V", sb["texto"])
                    if k not in cache_txt:
                        sv = _texto_img(sb["texto"], 88, 11)
                        if sv.width > VW - 60:
                            f = (VW - 60) / sv.width
                            sv = sv.resize((int(sv.width * f), int(sv.height * f)), Image.Resampling.LANCZOS)
                        cache_txt[k] = sv
                    sv = cache_txt[k]
                    pop = 1.0 + 0.12 * max(0.0, 1 - (tt - sb["inicio"]) / 0.12)     # entra con un pequeño pop
                    if pop > 1.001:
                        sv = sv.resize((int(sv.width * pop), int(sv.height * pop)), Image.Resampling.BILINEAR)
                    img.paste(sv, ((VW - sv.width) // 2, V_SUB_Y - sv.height // 2), sv)
                else:
                    img.paste(si, ((W - si.width) // 2, H - 150 - si.height // 2), si)
                break
        try:
            proc.stdin.write(img.tobytes())
        except OSError as ex:            # en Windows un tubo roto llega como «Invalid argument»
            raise _ffmpeg_cayo(ex) from ex
        ultimo = horizontal if vertical else img
        if n % (FPS * 30) == 0:
            avisar(f"  render {tt / 60:.1f} / {total / 60:.1f} min")
        if solo_video and n % (FPS * 3) == 0:
            destino.with_suffix(".avance").write_text(f"{tt - desde:.1f}")
    lector.cerrar()
    try:
        proc.stdin.close()
    except OSError as ex:
        raise _ffmpeg_cayo(ex) from ex
    proc.wait()
    registro_ffmpeg.close()
    destino.with_suffix(".ffmpeg.log").unlink(missing_ok=True)
    if solo_video:                      # un tramo del render en paralelo: el audio lo pone quien une
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg terminó con error ({proc.returncode})")
        video_tmp.replace(destino)
        return destino
    mezcla = mezclar_audio(raiz, edl, ffmpeg)[int(desde * SR):int(total * SR)]
    return _mezclar_y_unir(raiz, edl, ffmpeg, destino, video_tmp, mezcla, calidad)


def _mezclar_y_unir(raiz: Path, edl: dict, ffmpeg: str, destino: Path, video_tmp: Path, mezcla, calidad: str) -> Path:
    """Audio completo normalizado + video, subtítulos SRT y créditos de audio."""
    _, _, audio_kbps = CALIDADES.get(calidad, CALIDADES["normal"])
    subs = edl["pistas"]["subtitulos"]
    from . import biblioteca

    creditos = biblioteca.atribuciones(getattr(mezclar_audio, "usados", []))
    (destino.parent / "creditos_audio.txt").write_text(
        ("Créditos de audio para la descripción del video:\n" + "\n".join(creditos) + "\n") if creditos
        else "Este video no usa audio que pida atribución.\n", encoding="utf-8")
    wav = destino.with_suffix(".mezcla.wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mezcla, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video_tmp), "-i", str(wav),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", audio_kbps,
                    "-movflags", "+faststart",
                    "-ar", "48000", "-shortest", str(destino)], check=True)
    video_tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    # subtítulos también como SRT
    srt = destino.with_suffix(".srt")
    with open(srt, "w", encoding="utf-8") as f:
        for i, sb in enumerate(subs, 1):
            f.write(f"{i}\n{_srt(sb['inicio'])} --> {_srt(sb['fin'])}\n{sb['texto']}\n\n")
    return destino


def _srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
