"""Paso 5: 3 miniaturas 1280x720 (diamante sobre terciopelo negro, todo por código; sin foto ni firma)."""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import escenas as E  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
W, H = 1280, 720


def terciopelo(tono=(14, 10, 14), semilla=1):
    rng = np.random.default_rng(semilla)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    pliegues = (np.sin(xx / 95 + np.sin(yy / 160) * 1.6) * 0.5 + np.sin((xx + yy) / 210) * 0.5)
    luz = 0.55 + 0.45 * pliegues
    ruido = rng.normal(0, 1, (H, W)).astype(np.float32)
    ruido = np.asarray(Image.fromarray(((ruido * 20) + 128).clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.8)), np.float32) - 128
    base = np.array(tono, np.float32)[None, None, :] * (0.7 + 0.9 * luz[..., None]) + ruido[..., None] * 0.35
    return Image.fromarray(base.clip(0, 255).astype("uint8"), "RGB")


def diamante(img, cx, cy, s, acento):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa, "RGBA")
    for r, a in ((s * 2.2, 40), (s * 1.6, 60), (s * 1.15, 90)):        # resplandor
        d.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r * 0.9], fill=acento + (a,))
    capa = capa.filter(ImageFilter.GaussianBlur(s * 0.35))
    img.alpha_composite(capa)
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))                  # sombra suave en la tela
    ImageDraw.Draw(sombra).ellipse([cx - s * 0.9, cy + s * 1.0, cx + s * 0.9, cy + s * 1.2], fill=(0, 0, 0, 170))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(s * 0.12)))
    d = ImageDraw.Draw(img, "RGBA")
    E.diamante_dibujo(d, cx, cy, s, 0.17)
    for gx, gy, L in ((cx - s * 0.45, cy - s * 0.62, s * 0.55), (cx + s * 0.55, cy - s * 0.2, s * 0.35), (cx + s * 0.1, cy + s * 0.3, s * 0.25)):
        d.line([(gx - L, gy), (gx + L, gy)], fill=(255, 255, 255, 230), width=4)
        d.line([(gx, gy - L), (gx, gy + L)], fill=(255, 255, 255, 230), width=4)
        d.ellipse([gx - 7, gy - 7, gx + 7, gy + 7], fill=(255, 255, 255, 255))


def texto(img, lineas, x, y_centro, ancho, alinear="izq"):
    """lineas: [(texto, color, peso)] — el peso reparte el alto. Cada línea llena el ancho dado (como la plantilla)."""
    d = ImageDraw.Draw(img, "RGBA")
    tams = []
    for t, _, peso in lineas:
        tam = 300
        while d.textlength(t, font=E.BEBAS(tam)) > ancho * peso and tam > 40:
            tam -= 4
        tams.append(tam)
    alto = sum(tm * 0.86 for tm in tams)
    y = y_centro - alto / 2
    for (t, col, _), tm in zip(lineas, tams):
        f = E.BEBAS(tm)
        w = d.textlength(t, font=f)
        xx = x if alinear == "izq" else (x + (ancho - w) / 2 if alinear == "centro" else x + ancho - w)
        caja = f.getbbox(t)
        yy = y - caja[1] + (tm * 0.86 - (caja[3] - caja[1])) / 2
        sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).text((xx + 5, yy + 8), t, font=f, fill=(0, 0, 0, 220))
        img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(8)))
        d.text((xx, yy), t, font=f, fill=col, stroke_width=2, stroke_fill=(0, 0, 0))
        y += tm * 0.86


BLANCO = (255, 255, 255)
VARIANTES = {
    # A: texto a la izquierda, diamante a la derecha, acento dorado
    "A": dict(tono=(16, 10, 14), acento=(214, 172, 92), dorado=(232, 190, 96), diamante=(960, 360, 200),
              texto=(60, 360, 700, "izq")),
    # B: diamante grande al centro-arriba con vino, texto centrado abajo
    "B": dict(tono=(26, 8, 16), acento=(150, 34, 60), dorado=(240, 196, 104), diamante=(640, 150, 105),
              texto=(140, 475, 1000, "centro")),
    # C: diamante a la izquierda, texto a la derecha, acento champaña rosado
    "C": dict(tono=(12, 10, 16), acento=(230, 160, 170), dorado=(246, 200, 140), diamante=(300, 380, 190),
              texto=(560, 360, 680, "der")),
}


def hacer(nombre, v):
    img = terciopelo(v["tono"], semilla=ord(nombre)).convert("RGBA")
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-200, -160, W + 200, H + 160], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(160))
    negro = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    img = Image.composite(img, negro, vig)
    cx, cy, s = v["diamante"]
    diamante(img, cx, cy, s, v["acento"])
    x, yc, ancho, al = v["texto"]
    lineas = [("NO BAJES", BLANCO, 0.78), ("TU PRECIO", v["dorado"], 1.0), ("MUJER", BLANCO, 0.42)]
    if nombre == "B":
        lineas = [("NO BAJES", BLANCO, 0.4), ("TU PRECIO", v["dorado"], 0.68), ("MUJER", BLANCO, 0.22)]
    texto(img, lineas, x, yc, ancho, al)
    destino = AQUI / f"miniatura{'' if nombre == 'A' else '_' + nombre}.png"
    img.convert("RGB").save(destino)
    return destino


if __name__ == "__main__":
    for k, v in VARIANTES.items():
        print(hacer(k, v))
