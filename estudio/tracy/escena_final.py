"""Escena final fija del modo Tracy (desde un % del video hasta el final).

- Fondo: un video de naturaleza de Pexels en blanco y negro, en bucle, un poco oscurecido.
- Partículas lentas que brillan (un bucle de 20 s hecho aquí mismo, sin costo, se guarda en caché).
- El presentador recortado a la izquierda (imagen que sube el dueño; se pasa a blanco y negro).
- Botón «Suscríbete» con la manito que hace clic, de vez en cuando, arriba a la derecha.
- Ondas de audio que se mueven con la voz, abajo a la derecha.
Los subtítulos (amarillos en todo el video) los pone `ensamblar` igual que en los demás tramos.
"""
from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
BUCLE_PARTICULAS_S = 20
FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
VERSION_PARTICULAS = 2
BUSQUEDAS_FONDO = ["starry night sky", "night forest", "milky way", "misty forest", "mountain landscape",
                   "calm ocean", "clouds timelapse", "nature landscape", "forest trees", "night sky"]


def carpeta_cache() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "cache" / "tracy"
    c.mkdir(parents=True, exist_ok=True)
    return c


# ------------------------------------------------------------------ partículas

def _brillo(radio: int) -> np.ndarray:
    """Un punto de luz con halo suave (se suma sobre el cuadro)."""
    lado = radio * 8 + 1
    y, x = np.mgrid[:lado, :lado] - lado // 2
    d = np.sqrt(x * x + y * y)
    nucleo = np.clip(1.2 - d / max(1.0, radio), 0, 1)
    halo = np.exp(-(d / (radio * 2.2)) ** 2) * 0.55
    return np.clip(nucleo + halo, 0, 1).astype(np.float32)


def particulas(ffmpeg: str, destino: Path | None = None, n: int = 150, semilla: int = 7) -> Path:
    """Video de 20 s en bucle perfecto (todo se mueve en ciclos que cierran a los 20 s), fondo negro:
    se mezcla en modo «pantalla», así que lo negro no cambia nada."""
    destino = destino or carpeta_cache() / f"particulas_v{VERSION_PARTICULAS}.mp4"
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    r = random.Random(semilla)
    sprites = {k: _brillo(k) for k in (1, 2, 3, 4)}
    ps = []
    for _ in range(n):
        ps.append({"x": r.uniform(0, W), "y": r.uniform(0, H), "ax": r.uniform(20, 90), "ay": r.uniform(30, 140),
                   "cx": r.choice((1, 1, 2)), "cy": r.choice((1, 1, 2)), "fx": r.uniform(0, 2 * math.pi),
                   "fy": r.uniform(0, 2 * math.pi), "tw": r.choice((1, 2, 3)), "ft": r.uniform(0, 2 * math.pi),
                   "radio": r.choice((1, 2, 2, 3, 3, 4)), "luz": r.uniform(0.5, 1.0)})
    total = BUCLE_PARTICULAS_S * FPS
    tmp = destino.with_suffix(".part.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                             "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    try:
        for f in range(total):
            fase = 2 * math.pi * f / total
            cuadro = np.zeros((H, W), np.float32)
            for p in ps:
                x = p["x"] + p["ax"] * math.sin(p["cx"] * fase + p["fx"])
                y = p["y"] + p["ay"] * math.sin(p["cy"] * fase + p["fy"])
                brillo = p["luz"] * (0.55 + 0.45 * math.sin(p["tw"] * fase + p["ft"]))
                s = sprites[p["radio"]]
                m = s.shape[0] // 2
                x0, y0 = int(x) - m, int(y) - m
                xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + s.shape[1]), min(H, y0 + s.shape[0])
                if xa >= xb or ya >= yb:
                    continue
                cuadro[ya:yb, xa:xb] += s[ya - y0:yb - y0, xa - x0:xb - x0] * brillo
            proc.stdin.write((np.clip(cuadro, 0, 1) * 255).astype(np.uint8).tobytes())
    finally:
        proc.stdin.close()
        proc.wait()
    tmp.replace(destino)
    return destino


# ------------------------------------------------------------------ botón «Suscríbete»

# manito del cursor (pixel art): X borde negro, o relleno blanco
_MANO = """
......XX
.....XooX
.....XooX
.....XooX
.....XooX
.....XooXXX
.....XooXooXXX
.....XooXooXooXX
.XX..XooXooXooXoX
XooX.XooooooooXoX
XoooXXoooooooooooX
.XoooXoooooooooooX
..XooooooooooooooX
...XoooooooooooooX
...XooooooooooooX
....XoooooooooooX
.....XoooooooooX
.....XoooooooooX
......XXXXXXXXX
"""


def _mano(escala: int = 5) -> Image.Image:
    filas = [f for f in _MANO.strip("\n").split("\n")]
    ancho = max(len(f) for f in filas)
    im = Image.new("RGBA", (ancho, len(filas)), (0, 0, 0, 0))
    for y, fila in enumerate(filas):
        for x, ch in enumerate(fila):
            if ch == "X":
                im.putpixel((x, y), (0, 0, 0, 255))
            elif ch == "o":
                im.putpixel((x, y), (255, 255, 255, 255))
    return im.resize((ancho * escala, len(filas) * escala), Image.Resampling.NEAREST)


def _boton(suscrito: bool, escala: float = 1.0) -> Image.Image:
    w, h = int(380 * escala), int(96 * escala)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    color = (96, 96, 96, 255) if suscrito else (230, 33, 23, 255)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=int(14 * escala), fill=color, outline=(255, 255, 255, 230),
                        width=max(1, int(3 * escala)))
    # el logo de «play» a la izquierda
    px, py, lado = int(22 * escala), int(24 * escala), int(48 * escala)
    d.rounded_rectangle((px, py, px + int(lado * 1.4), py + lado), radius=int(12 * escala), fill=(255, 255, 255, 255))
    cx, cy = px + int(lado * 0.7), py + lado // 2
    t = int(lado * 0.28)
    d.polygon([(cx - t // 2, cy - t), (cx - t // 2, cy + t), (cx + t, cy)], fill=color)
    fuente = ImageFont.truetype(str(FUENTES / "ArchivoBlack-Regular.ttf"), max(8, int(36 * escala)))
    texto = "SUSCRITO" if suscrito else "SUSCRÍBETE"
    tx = px + int(lado * 1.4) + int(18 * escala)
    caja = d.textbbox((0, 0), texto, font=fuente)
    d.text((tx, (h - (caja[3] - caja[1])) // 2 - caja[1]), texto, font=fuente, fill=(255, 255, 255, 255))
    return im


def cuadros_suscribete(destino_dir: Path | None = None) -> Path:
    """3,5 s de animación como secuencia PNG: aparece, la manito llega, hace clic (pasa a «SUSCRITO»)
    y se va. Se hace una vez y queda en caché."""
    dirp = destino_dir or carpeta_cache() / "suscribete_v1"
    if (dirp / "listo").exists():
        return dirp
    dirp.mkdir(parents=True, exist_ok=True)
    mano = _mano(5)
    lienzo_w, lienzo_h = 560, 300
    bx, by = 60, 40
    n = int(3.5 * FPS)
    for f in range(n):
        t = f / FPS
        im = Image.new("RGBA", (lienzo_w, lienzo_h), (0, 0, 0, 0))
        entra = min(1.0, t / 0.35)
        esc = 0.6 + 0.4 * (1 - (1 - entra) ** 3) + (0.06 * math.sin(entra * math.pi) if entra < 1 else 0)
        clic = 1.45 <= t < 1.6
        boton = _boton(t >= 1.5, esc * (0.94 if clic else 1.0))
        im.alpha_composite(boton, (bx + (380 - boton.width) // 2, by + (96 - boton.height) // 2))
        # la manito entra desde abajo a la derecha y se posa sobre el botón
        viaje = min(1.0, max(0.0, (t - 0.4) / 0.9))
        viaje = 1 - (1 - viaje) ** 3
        mx = int(lienzo_w - 40 + (bx + 250 - (lienzo_w - 40)) * viaje)
        my = int(lienzo_h - 20 + (by + 50 - (lienzo_h - 20)) * viaje) + (4 if clic else 0)
        if t >= 0.4:
            im.alpha_composite(mano, (min(lienzo_w - mano.width, mx), min(lienzo_h - mano.height, my)))
        sale = max(0.0, (t - 3.0) / 0.5)
        if sale > 0:
            a = np.asarray(im).copy()
            a[..., 3] = (a[..., 3] * (1 - min(1.0, sale))).astype(np.uint8)
            im = Image.fromarray(a, "RGBA")
        im.save(dirp / f"s_{f:03d}.png")
    (dirp / "listo").write_text("ok")
    return dirp


DUR_SUSCRIBETE = 3.5


def momentos_suscribete(segmentos: list[dict], cada_s: float) -> dict[int, float]:
    """En qué segmentos aparece el botón (y a cuántos segundos de su inicio): cada ~`cada_s` segundos,
    siempre entero dentro de un segmento (nunca queda partido en un corte)."""
    salida: dict[int, float] = {}
    ultimo = -1e9
    for s in segmentos:
        dur = s["fin"] - s["inicio"]
        if dur < DUR_SUSCRIBETE + 3 or s["inicio"] - ultimo < cada_s:
            continue
        salida[s["id"]] = 2.0
        ultimo = s["inicio"]
    return salida


# ------------------------------------------------------------------ presentador

def preparar_presentador(origen: str | None, destino: Path) -> Path | None:
    """La imagen del presentador en blanco y negro, a 1000 px de alto, con el fondo quitado si trae
    (rembg si está instalado) y un desvanecido suave a la derecha para que se funda con el fondo."""
    if not origen or not Path(origen).is_file():
        return None
    im = Image.open(origen)
    im.load()
    tiene_alfa = im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 250
    im = im.convert("RGBA")
    if not tiene_alfa:
        try:
            from rembg import remove

            im = remove(im).convert("RGBA")
            tiene_alfa = True
        except Exception:  # noqa: BLE001 — sin rembg: se desvanece el borde
            pass
    k = 1000 / im.height
    im = im.resize((max(1, int(im.width * k)), 1000), Image.Resampling.LANCZOS)
    gris = im.convert("L")
    alfa = np.asarray(im.getchannel("A"), np.float32)
    ancho = im.width
    # desvanecido a la derecha y abajo (sin corte duro contra el fondo)
    rampa = np.clip((ancho - np.arange(ancho)) / (ancho * 0.28), 0, 1)[None, :]
    if not tiene_alfa:
        rampa = rampa * np.clip(np.arange(ancho) / (ancho * 0.08), 0, 1)[None, :]
    abajo = np.clip((im.height - np.arange(im.height)) / (im.height * 0.12), 0, 1)[:, None]
    alfa = alfa * rampa * np.maximum(abajo, 0.0 if not tiene_alfa else 1.0)
    salida = Image.merge("RGBA", (gris, gris, gris, Image.fromarray(alfa.astype(np.uint8)).filter(ImageFilter.GaussianBlur(1))))
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida.save(destino)
    return destino
