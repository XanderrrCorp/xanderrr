"""Tira de niveles (sección 15): se arma con código a partir de los recortes de
cada sujeto y del bloque `tira_niveles` del estilo. Nada de texto dentro de
imágenes generadas: «Nivel N» se dibuja aquí.

Salidas en <proyecto>/assets/tira/:
    tira_niveles.png              la tira completa (fondo transparente)
    tira_niveles_pixelada.png     igual, con la tarjeta del villano pixelada
    tarjeta_N.png / tarjeta_N_pixelada.png   cada tarjeta suelta
    vista_tira.png                vista previa sobre el fondo del estilo
"""
from __future__ import annotations

import math
import random
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .esquemas import EscenasV2, Estilo, TiraNiveles

CARPETA = "assets/tira"


# ------------------------------------------------------------------ utilidades

def _rgb(hexa: str) -> tuple[int, int, int]:
    h = hexa.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _fuente(t: TiraNiveles) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for ruta in t.texto.fuentes + ["DejaVuSans-Bold.ttf", "arialbd.ttf"]:
        try:
            return ImageFont.truetype(ruta, t.texto.tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def quitar_fondo_liso(img: Image.Image, tolerancia: int = 38) -> Image.Image:
    """Recorte para sujetos generados sobre fondo liso (gris #808080 o blanco):
    se inunda desde los bordes el color del fondo. Si `rembg` está instalado se
    usa ese, que es mejor con bordes difíciles."""
    try:
        from rembg import remove  # opcional
        return remove(img.convert("RGBA"))
    except ImportError:
        pass
    base = img.convert("RGB")
    marca = (255, 0, 255)
    trabajo = base.copy()
    w, h = trabajo.size
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if trabajo.getpixel((x, y)) != marca:
            ImageDraw.floodfill(trabajo, (x, y), marca, thresh=tolerancia)
    a = np.array(trabajo)
    fondo = (a[:, :, 0] == 255) & (a[:, :, 1] == 0) & (a[:, :, 2] == 255)
    alfa = Image.fromarray(np.where(fondo, 0, 255).astype("uint8"))
    alfa = alfa.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    salida = base.convert("RGBA")
    salida.putalpha(alfa)
    return salida


def pixelar(img: Image.Image, bloque: int) -> Image.Image:
    if bloque <= 1:
        return img
    w, h = img.size
    peq = img.resize((max(1, w // bloque), max(1, h // bloque)), Image.Resampling.BILINEAR)
    return peq.resize((w, h), Image.Resampling.NEAREST)


def niebla(ancho: int, alto: int, t: TiraNiveles) -> Image.Image:
    """Fondo de niebla azul oscura, determinista (misma semilla, misma niebla)."""
    rng = np.random.default_rng(t.fondo.semilla)
    capa = np.zeros((alto, ancho), dtype=np.float32)
    for escala, peso in ((64, 0.55), (24, 0.3), (8, 0.15)):
        ruido = rng.random((max(2, alto // escala), max(2, ancho // escala))).astype(np.float32)
        im = Image.fromarray((ruido * 255).astype("uint8")).resize((ancho, alto), Image.Resampling.BICUBIC)
        im = im.filter(ImageFilter.GaussianBlur(escala / 2))
        capa += np.asarray(im, dtype=np.float32) / 255 * peso
    yy = np.linspace(0, 1, alto, dtype=np.float32)[:, None]
    capa = np.clip(capa * (0.55 + 0.6 * (1 - np.abs(yy - 0.55) * 1.6)), 0, 1)
    a, b = np.array(_rgb(t.fondo.color_a), np.float32), np.array(_rgb(t.fondo.color_b), np.float32)
    rgb = a + (b - a) * capa[:, :, None]
    return Image.fromarray(rgb.clip(0, 255).astype("uint8"), "RGB")


def _mascara_redondeada(w: int, h: int, r: int) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    return m


# ------------------------------------------------------------------ tarjetas

@dataclass
class TiraArmada:
    normal: Image.Image
    pixelada: Image.Image
    centros_x: list[int]            # centro de cada tarjeta en el lienzo
    caja_villano: tuple[int, int, int, int]
    t: TiraNiveles


def _tarjeta(sujeto: Image.Image | None, indice: int, total: int, t: TiraNiveles, seed: int) -> Image.Image:
    """Tarjeta sin texto: relleno de piedra, sujeto centrado con sombra, borde."""
    w, h = t.tarjeta_ancho, t.tarjeta_alto
    drama = t.drama_hacia_derecha * (indice / max(1, total - 1))
    rng = np.random.default_rng(seed + indice)
    base = np.array(_rgb(t.relleno_color), np.float32) * (1 - 0.8 * drama)
    base = base + np.array([40, -10, -18], np.float32) * drama          # se oscurece y se calienta hacia la derecha
    ruido = rng.normal(0, 255 * t.relleno_ruido, (h, w, 1)).astype(np.float32)
    manchas = np.asarray(Image.fromarray((rng.random((h // 40 + 1, w // 40 + 1)) * 255).astype("uint8"))
                         .resize((w, h), Image.Resampling.BICUBIC), np.float32)[:, :, None] / 255 - 0.5
    relleno = Image.fromarray(np.clip(base + ruido + manchas * 30, 0, 255).astype("uint8"), "RGB").convert("RGBA")
    if sujeto is not None:
        s = sujeto.copy()
        caja = s.getbbox()
        if caja:
            s = s.crop(caja)
        escala = min(w * t.sujeto_ancho / s.width, h * 0.82 / s.height)
        s = s.resize((max(1, int(s.width * escala)), max(1, int(s.height * escala))), Image.Resampling.LANCZOS)
        x, y = (w - s.width) // 2, (h - s.height) // 2
        if t.sombra_sujeto:
            sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(sombra).ellipse([x + s.width * 0.12, y + s.height * 0.86, x + s.width * 0.88,
                                            y + s.height * 1.02], fill=(0, 0, 0, 110))
            relleno.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(14)))
        relleno.alpha_composite(s, (x, y))
    tarjeta = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tarjeta.paste(relleno, (0, 0), _mascara_redondeada(w, h, t.radio))
    if t.borde_grosor:
        ImageDraw.Draw(tarjeta).rounded_rectangle([t.borde_grosor // 2, t.borde_grosor // 2,
                                                   w - 1 - t.borde_grosor // 2, h - 1 - t.borde_grosor // 2],
                                                  radius=t.radio, outline=_rgb(t.borde_color) + (255,),
                                                  width=t.borde_grosor)
    return tarjeta


def _pixelar_interior(tarjeta: Image.Image, t: TiraNiveles, bloque: int | None = None) -> Image.Image:
    """Pixela el contenido y deja el borde nítido."""
    b = bloque or t.pixel_bloque
    dentro = pixelar(tarjeta, b)
    w, h = tarjeta.size
    g = t.borde_grosor
    mascara = _mascara_redondeada(w - 2 * g, h - 2 * g, max(0, t.radio - g))
    salida = tarjeta.copy()
    salida.paste(dentro.crop((g, g, w - g, h - g)), (g, g), mascara)
    return salida


def _brillo(w: int, h: int, t: TiraNiveles, intensidad: float = 1.0) -> Image.Image:
    """Halo rojo alrededor de la tarjeta del villano (sale por fuera del borde)."""
    r = t.brillo_radio
    capa = Image.new("RGBA", (w + 4 * r, h + 4 * r), (0, 0, 0, 0))
    color = _rgb(t.brillo_villano)
    ImageDraw.Draw(capa).rounded_rectangle([2 * r - r // 2, 2 * r - r // 2, 2 * r + w + r // 2, 2 * r + h + r // 2],
                                           radius=t.radio + r // 2, fill=color + (int(255 * intensidad),))
    halo = capa.filter(ImageFilter.GaussianBlur(r / 1.8))
    halo.alpha_composite(capa.filter(ImageFilter.GaussianBlur(r / 5)))  # núcleo más intenso junto al borde
    return halo


def armar_tira(esc: EscenasV2, estilo: Estilo, carpeta: Path, seed: int = 0) -> TiraArmada:
    t = estilo.tira_niveles or TiraNiveles()
    if not esc.niveles:
        raise ValueError("escenas.json no tiene 'niveles': no es un video de formato escala")
    assets = {a.id: a for a in esc.assets}
    n = len(esc.niveles)
    ancho = n * t.tarjeta_ancho + (n + 1) * t.separacion
    lienzo = Image.new("RGBA", (ancho, t.alto_lienzo), (0, 0, 0, 0))
    lienzo_px = lienzo.copy()
    fuente = _fuente(t)
    salida = carpeta / CARPETA
    salida.mkdir(parents=True, exist_ok=True)
    centros, caja_villano = [], (0, 0, 0, 0)
    for i, nivel in enumerate(esc.niveles):
        a = assets[nivel.asset]
        sujeto = None
        sin_fondo = carpeta / "assets" / "sin_fondo" / Path(a.archivo).name
        original = carpeta / a.archivo
        if sin_fondo.exists():
            sujeto = Image.open(sin_fondo).convert("RGBA")
        elif original.exists():
            sujeto = quitar_fondo_liso(Image.open(original))
            sin_fondo.parent.mkdir(parents=True, exist_ok=True)
            sujeto.save(sin_fondo)
        tarjeta = _tarjeta(sujeto, i, n, t, seed)
        tarjeta_px = _pixelar_interior(tarjeta, t) if nivel.villano else tarjeta
        x = t.separacion + i * (t.tarjeta_ancho + t.separacion)
        y = t.y_tarjeta
        centros.append(x + t.tarjeta_ancho // 2)
        for capa, tj in ((lienzo, tarjeta), (lienzo_px, tarjeta_px)):
            if nivel.villano:
                g = _brillo(t.tarjeta_ancho, t.tarjeta_alto, t)
                capa.alpha_composite(g, (x - 2 * t.brillo_radio, y - 2 * t.brillo_radio))
            capa.alpha_composite(tj, (x, y))
            _texto(capa, t.texto.formato.format(n=nivel.numero), x + t.tarjeta_ancho // 2, y, t, fuente)
        if nivel.villano:
            caja_villano = (x, y, x + t.tarjeta_ancho, y + t.tarjeta_alto)
        tarjeta.save(salida / f"tarjeta_{nivel.numero}.png")
        _pixelar_interior(tarjeta, t).save(salida / f"tarjeta_{nivel.numero}_pixelada.png")
    lienzo.save(salida / "tira_niveles.png")
    lienzo_px.save(salida / "tira_niveles_pixelada.png")
    if t.fondo.tipo != "transparente":
        vista = niebla(*lienzo.size, t).convert("RGBA") if t.fondo.tipo == "niebla" \
            else Image.new("RGBA", lienzo.size, _rgb(t.fondo.color_a) + (255,))
        vista.alpha_composite(lienzo_px)
        vista.convert("RGB").resize((lienzo.width // 3, lienzo.height // 3), Image.Resampling.LANCZOS) \
            .save(salida / "vista_tira.png")
    return TiraArmada(lienzo, lienzo_px, centros, caja_villano, t)


def _texto(capa: Image.Image, texto: str, cx: int, y_tarjeta: int, t: TiraNiveles, fuente) -> None:
    d = ImageDraw.Draw(capa)
    caja = d.textbbox((0, 0), texto, font=fuente, stroke_width=t.texto.contorno_grosor)
    tw, th = caja[2] - caja[0], caja[3] - caja[1]
    d.text((cx - tw // 2 - caja[0], y_tarjeta - th - 36 - caja[1]), texto, font=fuente,
           fill=_rgb(t.texto.color), stroke_width=t.texto.contorno_grosor,
           stroke_fill=_rgb(t.texto.contorno_color))


# ------------------------------------------------------------------ clip de prueba

def _suave(x: float) -> float:
    """Curva ease-in-out (14.4): nunca velocidad lineal."""
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _barrido(sr: int, dur: float, rng: np.random.Generator) -> np.ndarray:
    n = int(sr * dur)
    ruido = rng.normal(0, 1, n)
    # filtro paso banda que sube: barrido
    salida = np.zeros(n)
    y1 = y2 = 0.0
    for i in range(n):
        f = 0.02 + 0.25 * (i / n)
        y1 += f * (ruido[i] - y1)
        y2 += f * (y1 - y2)
        salida[i] = y1 - y2
    env = np.sin(np.linspace(0, math.pi, n)) ** 1.5
    return salida * env / (np.abs(salida).max() + 1e-9) * 0.5


def _golpe(sr: int, dur: float) -> np.ndarray:
    tt = np.arange(int(sr * dur)) / sr
    f = 58 * np.exp(-tt * 1.8) + 32
    tono = np.sin(2 * math.pi * np.cumsum(f) / sr) * np.exp(-tt * 3.2)
    clic = np.random.default_rng(3).normal(0, 1, len(tt)) * np.exp(-tt * 40) * 0.4
    return (tono + clic) * 0.9


def _zumbido(sr: int, dur: float) -> np.ndarray:
    tt = np.arange(int(sr * dur)) / sr
    return (np.sin(2 * math.pi * 55 * tt) + 0.5 * np.sin(2 * math.pi * 82 * tt)) * np.minimum(tt / dur, 1) * 0.18


def clip_tira(armada: TiraArmada, destino: Path, ffmpeg: str, fondo: Image.Image | None = None,
              fps: int = 30, tam: tuple[int, int] = (1920, 1080), semilla: int = 11) -> Path:
    """Clip de prueba: se detiene en cada nivel, tiembla en el villano pixelado,
    silencio breve, y revelación con destello rojo y golpe grave."""
    t = armada.t
    W, H = tam
    escala = H / armada.normal.height
    tira = armada.normal.resize((int(armada.normal.width * escala), H), Image.Resampling.LANCZOS)
    # medio cuadro de niebla a cada lado: así también el primer y el último nivel
    # pueden quedar centrados en pantalla
    pad = W // 2
    base = (fondo or niebla(tira.width + 2 * pad, H, t)).resize((tira.width + 2 * pad, H)).convert("RGBA")
    base.alpha_composite(tira, (pad, 0))
    base = base.convert("RGB")
    centros = [int(c * escala) + pad for c in armada.centros_x]
    vx0, vy0, vx1, vy1 = (int(v * escala) for v in armada.caja_villano)
    vx0, vx1 = vx0 + pad, vx1 + pad
    g = int(t.borde_grosor * escala)

    # guion del movimiento: (duración, desde nivel, hasta nivel, efecto)
    tramos: list[tuple[float, int, int, str]] = [(0.8, 0, 0, "quieto")]
    for i in range(1, len(centros)):
        tramos += [(0.75, i - 1, i, "desliza"), (0.45 if i < len(centros) - 1 else 0.0, i, i, "quieto")]
    ult = len(centros) - 1
    tramos += [(1.1, ult, ult, "tiembla"), (0.35, ult, ult, "silencio"), (0.55, ult, ult, "revela"),
               (1.6, ult, ult, "final")]
    total = sum(d for d, *_ in tramos)
    sr = 48000
    audio = np.zeros(int(sr * (total + 0.5)))
    rng = np.random.default_rng(semilla)

    def poner(sonido, en):
        i = int(sr * en)
        audio[i:i + len(sonido)] += sonido[: max(0, len(audio) - i)]

    destino.parent.mkdir(parents=True, exist_ok=True)
    video_tmp = destino.with_suffix(".sinaudio.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(video_tmp)], stdin=subprocess.PIPE)
    reloj = 0.0
    temblor = random.Random(semilla)
    for dur, a, b, efecto in tramos:
        if efecto == "desliza":
            poner(_barrido(sr, dur, rng), reloj)
        if efecto == "tiembla":
            poner(_zumbido(sr, dur), reloj)
        if efecto == "revela":
            poner(_golpe(sr, 1.6), reloj)
        cuadros = int(round(dur * fps))
        for k in range(cuadros):
            p = _suave((k + 1) / cuadros) if efecto == "desliza" else 1.0
            cx = centros[a] + (centros[b] - centros[a]) * p
            dx = dy = 0
            if efecto == "tiembla":
                amp = 6 * (0.4 + 0.6 * k / max(1, cuadros))
                dx, dy = temblor.uniform(-amp, amp), temblor.uniform(-amp, amp)
            x0 = int(min(max(cx - W / 2, 0), base.width - W))
            cuadro = base.crop((x0, 0, x0 + W, H))
            # el villano va pixelado hasta la revelación (regla 15.4)
            if efecto == "revela":
                bloque = int(round(t.pixel_bloque * escala * (1 - _suave(k / cuadros)))) or 1
            elif efecto == "final":
                bloque = 1
            else:
                bloque = int(t.pixel_bloque * escala)
            if bloque > 1:
                rx0, rx1 = vx0 + g - x0, vx1 - g - x0
                if rx1 > 0 and rx0 < W:
                    zona = cuadro.crop((rx0, vy0 + g, rx1, vy1 - g))
                    m = _mascara_redondeada(zona.width, zona.height, max(0, int((t.radio - t.borde_grosor) * escala)))
                    cuadro.paste(pixelar(zona, bloque), (rx0, vy0 + g), m)
            if dx or dy:
                # temblor leve: se amplía un 2 % y se desplaza dentro de ese margen, sin bordes negros
                z = cuadro.resize((int(W * 1.02), int(H * 1.02)), Image.Resampling.BILINEAR)
                mx, my = (z.width - W) // 2, (z.height - H) // 2
                cuadro = z.crop((int(mx + dx), int(my + dy), int(mx + dx) + W, int(my + dy) + H))
            if efecto in ("revela", "final"):
                ttrans = (k / fps) if efecto == "revela" else (0.55 + k / fps)
                alfa = max(0.0, 0.6 * math.exp(-ttrans * 4.5)) if efecto == "revela" or ttrans < 1.2 else 0.0
                if alfa > 0.01:
                    rojo = Image.new("RGB", (W, H), _rgb(t.brillo_villano))
                    cuadro = Image.blend(cuadro, rojo, alfa)
            proc.stdin.write(cuadro.tobytes())
        reloj += dur
    proc.stdin.close()
    proc.wait()
    wav = destino.with_suffix(".wav")
    datos = np.clip(audio / max(1.0, np.abs(audio).max() / 0.9), -1, 1)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((datos * 32767).astype("<i2").tobytes())
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video_tmp), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(destino)], check=True)
    video_tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    return destino
