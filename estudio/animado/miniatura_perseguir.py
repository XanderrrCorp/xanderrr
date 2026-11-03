"""Miniaturas: celular con un mensaje de «ÉL» sobre terciopelo (por código; sin foto ni firma). Texto: «DÍA 3: / NO LE / ESCRIBAS»."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import miniatura as M  # noqa: E402
import escenas as E  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
W, H = M.W, M.H


def celular(img, cx, cy, s, acento, rot):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa, "RGBA")
    d.ellipse([cx - s * 1.6, cy - s * 1.6, cx + s * 1.6, cy + s * 1.6], fill=acento + (60,))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(s * 0.4)))
    tel = Image.new("RGBA", (int(s * 1.3), int(s * 2.4)), (0, 0, 0, 0))
    g = ImageDraw.Draw(tel, "RGBA")
    tw, th = tel.size
    g.rounded_rectangle([0, 0, tw - 1, th - 1], int(s * 0.16), fill=(22, 20, 26), outline=(214, 172, 92), width=6)
    g.rounded_rectangle([12, 14, tw - 13, th - 15], int(s * 0.12), fill=(46, 40, 60))
    g.text((tw / 2, th * 0.14), "23:00", font=E.BEBAS(int(s * 0.38)), fill=E.CREAM, anchor="mm")
    g.rounded_rectangle([24, th * 0.32, tw - 24, th * 0.56], 20, fill=E.CREAM)
    g.text((44, th * 0.38), "ÉL", font=E.BEBAS(int(s * 0.17)), fill=E.WINE, anchor="lm")
    g.text((44, th * 0.48), "¿Todo bien?", font=E.PLAY(int(s * 0.12), 700), fill=E.INK, anchor="lm")
    tel = tel.rotate(rot, resample=Image.Resampling.BICUBIC, expand=True)
    img.alpha_composite(tel, (int(cx - tel.width / 2), int(cy - tel.height / 2)))


BLANCO = (255, 255, 255)
V = {
    "A": dict(tono=(16, 10, 16), acento=(90, 150, 230), color=(240, 196, 104), obj=(1000, 360, 200, -8), texto=(60, 360, 720, "izq")),
    "B": dict(tono=(26, 8, 16), acento=(150, 34, 60), color=(255, 255, 255), obj=(640, 210, 120, 0), texto=(140, 520, 1000, "centro")),
    "C": dict(tono=(12, 10, 18), acento=(230, 160, 170), color=(246, 200, 140), obj=(300, 380, 190, 8), texto=(560, 360, 680, "der")),
}


def hacer(n, v):
    img = M.terciopelo(v["tono"], semilla=ord(n) + 21).convert("RGBA")
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-200, -160, W + 200, H + 160], fill=255)
    img = Image.composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), vig.filter(ImageFilter.GaussianBlur(160)))
    cx, cy, s, rot = v["obj"]
    celular(img, cx, cy, s, v["acento"], rot)
    x, yc, ancho, al = v["texto"]
    if n == "B":
        lineas = [("DÍA 3: NO LE", BLANCO, 0.62), ("ESCRIBAS", (232, 190, 96), 0.72)]
    else:
        lineas = [("DÍA 3:", BLANCO, 0.5), ("NO LE", BLANCO, 0.62), ("ESCRIBAS", v["color"], 1.0)]
    M.texto(img, lineas, x, yc, ancho, al)
    img.convert("RGB").save(AQUI / f"miniatura{'' if n == 'A' else '_' + n}.png")


for k, v in V.items():
    hacer(k, v)
ims = [Image.open(AQUI / f) for f in ("miniatura.png", "miniatura_B.png", "miniatura_C.png")]
h = Image.new("RGB", (W, 3 * H)); [h.paste(im, (0, k * H)) for k, im in enumerate(ims)]; h.save(AQUI / "miniaturas_3.jpg", quality=85)
