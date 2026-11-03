"""El Profesor animado (reutilizable para cualquier video del canal).
Capas de profesor/ (lienzo 1200x1200, orden: fondo > cuerpo > cabeza_base > ojos > rasgos > boca > bigote > brazo).
- Boca: la de Rhubarb (bocas.json: [[t, "A".."H"/"X"], ...] en tiempo absoluto).
- Parpadeo cada 3-4 s, balanceo suave de cabeza (≈4 px y 1-2°).
- Brazo a la sien solo en las ventanas de «gesto»; pose «apuntar» (brazo extendido a la derecha) para la pantalla final."""
import bisect
import json
import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent.parent
CAPAS = AQUI / "profesor"
SUIT, SUIT_D, SKIN, SKIN_D = (44, 59, 87), (24, 33, 58), (237, 183, 140), (214, 154, 110)

_BOCAS = None


def bocas():
    global _BOCAS
    if _BOCAS is None:
        datos = json.loads((AQUI / "bocas.json").read_text())
        _BOCAS = ([x[0] for x in datos], [x[1] for x in datos])
    return _BOCAS


def boca_en(T):
    ts, vs = bocas()
    k = bisect.bisect_right(ts, T) - 1
    return vs[k] if k >= 0 else "X"


def parpadea(T):
    """Ojos cerrados ~0,13 s, a intervalos de 3-4 s (deterministas)."""
    rng = random.Random(11)
    t = rng.uniform(1.0, 2.5)
    while t < T + 1:
        if t <= T < t + 0.13:
            return True
        t += rng.uniform(3.0, 4.0)
        if t > T + 5:
            break
    return False


@lru_cache(maxsize=None)
def _capa(nombre, tam):
    if nombre == "brazo_apunta":
        return _brazo_apunta(tam)
    im = Image.open(CAPAS / f"{nombre}.png").convert("RGBA")
    return im.resize((tam, tam), Image.Resampling.LANCZOS)


@lru_cache(maxsize=None)
def _brazo_apunta(tam):
    """Pose nueva con el mismo estilo: brazo extendido hacia la derecha, índice apuntando (dibujado a 2x)."""
    s = 2400 / 600
    im = Image.new("RGBA", (2400, 2400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def P(x, y): return (x * s, y * s)
    pts = [P(392, 470), P(470, 420), P(540, 392)]
    d.line(pts, fill=SUIT, width=int(64 * s), joint="curve")
    for p in (pts[0], pts[-1]):
        r = 32 * s; d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=SUIT)
    d.line([P(410, 500), P(480, 452), P(536, 428)], fill=SUIT_D, width=int(12 * s))
    hx, hy = P(566, 384)
    d.ellipse([hx - 29 * s, hy - 25 * s, hx + 29 * s, hy + 25 * s], fill=SKIN)
    d.line([P(586, 374), P(640, 362)], fill=SKIN, width=int(15 * s))
    d.line([P(556, 378), P(574, 392)], fill=SKIN_D, width=int(4 * s))
    mask = Image.new("L", (2400, 2400), 0)
    ImageDraw.Draw(mask).ellipse([P(10, 10), P(590, 590)], fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), Image.new("L", im.size, 0), mask))
    return im.resize((tam, tam), Image.Resampling.LANCZOS)


def dibujar(lienzo, cx, cy, tam, T, gesto=0.0, apuntar=False, entrada=1.0):
    """Pega al Profesor (medallón circular) centrado en (cx, cy) con diámetro ≈ tam. gesto 0..1 sube el brazo;
    entrada 0..1 para aparecer (escala con rebote)."""
    if entrada <= 0.01:
        return
    tam = int(tam * (0.6 + 0.4 * min(1.0, entrada)))
    capa = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    capa.alpha_composite(_capa("fondo", tam))
    capa.alpha_composite(_capa("cuerpo", tam))
    # cabeza: balanceo (rotación sobre el cuello y unos px de vaivén)
    cabeza = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    for n in ("cabeza_base", "ojos_cerrados" if parpadea(T) else "ojos_abiertos", "rasgos", f"boca_{boca_en(T)}", "bigote"):
        cabeza.alpha_composite(_capa(n, tam))
    ang = 1.6 * math.sin(T * 1.3) + 0.6 * math.sin(T * 2.9)
    dx = 4 * tam / 600 * math.sin(T * 1.1)
    dy = 2 * tam / 600 * math.sin(T * 2.1 + 1)
    cabeza = cabeza.rotate(ang, resample=Image.Resampling.BICUBIC, center=(tam * 0.5, tam * 0.7), translate=(dx, dy))
    capa.alpha_composite(cabeza)
    if apuntar:
        capa.alpha_composite(_capa("brazo_apunta", tam))
    elif gesto > 0.01:
        brazo = _capa("brazo_sien", tam)
        off = int((1 - gesto) * tam * 0.55)
        tmp = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        tmp.alpha_composite(brazo, (0, off))
        mask = Image.new("L", (tam, tam), 0)                     # el brazo no sale del círculo
        ImageDraw.Draw(mask).ellipse([tam * 0.017, tam * 0.017, tam * 0.983, tam * 0.983], fill=255)
        tmp.putalpha(Image.composite(tmp.getchannel("A"), Image.new("L", (tam, tam), 0), mask))
        capa.alpha_composite(tmp)
    # aro dorado y sombra
    d = ImageDraw.Draw(lienzo, "RGBA")
    r = tam * 0.49
    d.ellipse([cx - r + 10, cy - r + 16, cx + r + 10, cy + r + 16], fill=(0, 0, 0, 90))
    lienzo.paste(capa, (int(cx - tam / 2), int(cy - tam / 2)), capa)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(214, 172, 92, 255), width=max(3, int(tam / 90)))
