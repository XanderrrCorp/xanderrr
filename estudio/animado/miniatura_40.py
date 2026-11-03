"""Miniaturas del video de los 40: candado dorado ABIERTO sobre terciopelo (por código; sin foto ni firma)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import miniatura as M  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
W, H = M.W, M.H


def candado(img, cx, cy, s, acento):
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa, "RGBA")
    for r, a in ((s * 2.0, 40), (s * 1.4, 70)):
        d.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r * 0.9], fill=acento + (a,))
    img.alpha_composite(capa.filter(ImageFilter.GaussianBlur(s * 0.3)))
    d = ImageDraw.Draw(img, "RGBA")
    oro, oro_d, oro_l = (226, 182, 96), (170, 126, 52), (250, 222, 150)
    # arco abierto (levantado y girado)
    d.arc([cx - s * 0.55, cy - s * 1.35, cx + s * 0.55, cy - s * 0.15], 180, 360, fill=oro_d, width=int(s * 0.2))
    d.line([(cx - s * 0.45, cy - s * 0.75), (cx - s * 0.45, cy - s * 0.35)], fill=oro_d, width=int(s * 0.2))
    d.rounded_rectangle([cx - s * 0.8, cy - s * 0.2, cx + s * 0.8, cy + s * 0.95], int(s * 0.18), fill=oro)
    d.rounded_rectangle([cx - s * 0.8, cy - s * 0.2, cx - s * 0.5, cy + s * 0.95], int(s * 0.12), fill=oro_l)
    d.ellipse([cx - s * 0.13, cy + s * 0.2, cx + s * 0.13, cy + s * 0.46], fill=(60, 40, 20))
    d.polygon([(cx - s * 0.07, cy + s * 0.4), (cx + s * 0.07, cy + s * 0.4), (cx + s * 0.04, cy + s * 0.7), (cx - s * 0.04, cy + s * 0.7)], fill=(60, 40, 20))
    for gx, gy, L in ((cx + s * 0.5, cy - s * 0.05, s * 0.3), (cx - s * 0.6, cy + s * 0.6, s * 0.2)):
        d.line([(gx - L, gy), (gx + L, gy)], fill=(255, 255, 255, 230), width=4)
        d.line([(gx, gy - L), (gx, gy + L)], fill=(255, 255, 255, 230), width=4)


BLANCO = (255, 255, 255)
VARIANTES = {
    "A": dict(tono=(16, 10, 14), acento=(214, 172, 92), color=(240, 196, 104), obj=(1000, 400, 190), texto=(60, 360, 720, "izq")),
    "B": dict(tono=(26, 8, 16), acento=(150, 34, 60), color=(255, 255, 255), obj=(640, 190, 120), texto=(140, 480, 1000, "centro")),
    "C": dict(tono=(12, 10, 16), acento=(230, 160, 170), color=(246, 200, 140), obj=(300, 400, 180), texto=(560, 360, 680, "der")),
}


def hacer(nombre, v):
    img = M.terciopelo(v["tono"], semilla=ord(nombre) + 7).convert("RGBA")
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-200, -160, W + 200, H + 160], fill=255)
    img = Image.composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), vig.filter(ImageFilter.GaussianBlur(160)))
    cx, cy, s = v["obj"]
    candado(img, cx, cy, s, v["acento"])
    x, yc, ancho, al = v["texto"]
    if nombre == "B":     # el número en grande, frase en dorado debajo (otra disposición y otro color)
        lineas = [("LOS 40", (232, 190, 96), 0.42), ("FIN DEL PERMISO", BLANCO, 0.8)]
    else:
        lineas = [("LOS 40:", BLANCO, 0.55), ("FIN DEL", v["color"], 0.75), ("PERMISO", v["color"], 1.0)]
    M.texto(img, lineas, x, yc, ancho, al)
    destino = AQUI / f"miniatura{'' if nombre == 'A' else '_' + nombre}.png"
    img.convert("RGB").save(destino)
    return destino


if __name__ == "__main__":
    for k, v in VARIANTES.items():
        hacer(k, v)
    ims = [Image.open(AQUI / f) for f in ("miniatura.png", "miniatura_B.png", "miniatura_C.png")]
    h = Image.new("RGB", (W, 3 * H)); [h.paste(im, (0, k * H)) for k, im in enumerate(ims)]; h.save(AQUI / "miniaturas_3.jpg", quality=85)
