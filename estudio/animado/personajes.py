"""Generador de personajes en el estilo de El Profesor: formas planas, trazo limpio, cabeza grande (≈ las mismas
proporciones), paleta del canal. Cada personaje sale en capas (cuerpo, cabeza, ojos abiertos/cerrados, boca, brazo)
para animarlo con parpadeo y gestos simples. Nada de caras realistas ni parecidos con personas reales.

Uso: p = Personaje(piel="#E8B48E", pelo="#5A3A2A", peinado="mono", ropa="#F2EEE6", ropa2="#2C3B57", edad=35)
     p.pegar(lienzo, cx, base_y, alto, t, hablando=False, brazo=0..1)"""
import math
import random
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw

S = 4                   # se dibuja a 4x sobre un lienzo de 600 y se reduce (bordes limpios)
INK = (42, 32, 36)


def _hex(c):
    return c if isinstance(c, tuple) else tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _osc(c, k):
    return tuple(max(0, int(v * k)) for v in c)


@dataclass(frozen=True)
class Personaje:
    piel: str = "#EDB78C"
    pelo: str = "#5A3A2A"
    peinado: str = "mono"            # mono (recogido) | suelto | corto | coleta
    ropa: str = "#F2EEE6"            # blusa / vestido
    ropa2: str = "#2C3B57"           # saco o detalle
    tipo_ropa: str = "blusa"         # blusa | vestido | saco
    aretes: bool = True
    lentes: bool = False
    edad: int = 35                   # >45: una cana en el pelo

    # ---------------------------------------------------------------- capas (600x600 lógico)
    def _lienzo(self):
        return Image.new("RGBA", (600 * S, 600 * S), (0, 0, 0, 0))

    def _P(self, *xy):
        return [v * S for v in xy]

    @lru_cache(maxsize=None)
    def capa(self, nombre):
        im = self._lienzo()
        d = ImageDraw.Draw(im)
        P = self._P
        piel, piel_d = _hex(self.piel), _osc(_hex(self.piel), 0.88)
        pelo, ropa, ropa2 = _hex(self.pelo), _hex(self.ropa), _hex(self.ropa2)
        if nombre == "cuerpo":
            d.rounded_rectangle(P(274, 372, 326, 446), radius=18 * S, fill=piel_d)                  # cuello
            if self.tipo_ropa == "vestido":
                d.polygon(P(170, 600, 430, 600, 380, 440, 220, 440), fill=ropa)
                d.chord(P(200, 410, 400, 500), 180, 360, fill=ropa)
            else:
                d.chord(P(90, 430, 510, 760), 180, 360, fill=ropa2 if self.tipo_ropa == "saco" else ropa)
                d.rectangle(P(90, 595, 510, 600), fill=ropa)
                if self.tipo_ropa == "saco":
                    d.polygon(P(256, 440, 300, 520, 344, 440), fill=ropa)
                else:                                                                        # cuello de blusa
                    d.polygon(P(262, 436, 300, 476, 276, 486, 246, 448), fill=_osc(ropa, 0.9))
                    d.polygon(P(338, 436, 300, 476, 324, 486, 354, 448), fill=_osc(ropa, 0.9))
                    for y in (500, 540, 580):
                        d.ellipse(P(296, y, 304, y + 8), fill=_osc(ropa, 0.75))
        elif nombre == "pelo_atras":
            if self.peinado == "suelto":
                d.rounded_rectangle(P(196, 230, 404, 470), radius=90 * S, fill=pelo)
            elif self.peinado == "coleta":
                d.ellipse(P(380, 240, 450, 400), fill=pelo)
        elif nombre == "cabeza":
            d.ellipse(P(204, 290, 232, 336), fill=piel_d)                                             # orejas
            d.ellipse(P(368, 290, 396, 336), fill=piel_d)
            if self.peinado == "mono":
                d.ellipse(P(262, 124, 338, 194), fill=pelo)                                           # moño
                d.arc(P(272, 136, 328, 186), 200, 340, fill=_osc(pelo, 1.3), width=4 * S)
            d.ellipse(P(206, 182, 394, 352 if self.peinado != "corto" else 320), fill=pelo)          # pelo (detrás de la cara)
            d.ellipse(P(216, 214, 384, 412), fill=piel)                                               # cara
            mejilla = tuple(int(a * 0.75 + b * 0.25) for a, b in zip(piel, (232, 110, 120)))
            d.ellipse(P(236, 324, 262, 338), fill=mejilla)
            d.ellipse(P(338, 324, 364, 338), fill=mejilla)
            d.arc(P(290, 300, 312, 340), 60, 160, fill=piel_d, width=5 * S)                          # nariz
            if self.peinado != "corto":                                                              # flequillo de lado
                d.pieslice(P(196, 150, 420, 330), 190, 300, fill=pelo)
                d.ellipse(P(216, 214, 384, 412), outline=None)
            if self.edad > 45:
                d.arc(P(232, 196, 330, 280), 200, 260, fill=(200, 196, 192), width=6 * S)
            if self.aretes:
                d.ellipse(P(212, 336, 224, 348), fill=(214, 172, 92))
                d.ellipse(P(376, 336, 388, 348), fill=(214, 172, 92))
            d.ellipse(P(216, 236, 384, 412), fill=piel) if False else None
            d.arc(P(252, 270, 286, 286), 200, 340, fill=_osc(pelo, 0.8), width=6 * S)                # cejas
            d.arc(P(314, 270, 348, 286), 200, 340, fill=_osc(pelo, 0.8), width=6 * S)
        elif nombre == "ojos_abiertos":
            for x in (268, 332):
                d.ellipse(P(x - 7, 293, x + 7, 311), fill=INK)
                d.ellipse(P(x - 1, 296, x + 4, 301), fill=(255, 255, 255))
                d.line(P(x - 9, 292, x - 13, 287), fill=INK, width=3 * S)                            # pestaña
        elif nombre == "ojos_cerrados":
            for x in (268, 332):
                d.arc(P(x - 9, 296, x + 9, 310), 10, 170, fill=INK, width=4 * S)
        elif nombre == "lentes" and self.lentes:
            for x in (268, 332):
                d.ellipse(P(x - 21, 281, x + 21, 323), outline=INK, width=4 * S)
            d.arc(P(290, 294, 310, 306), 200, 340, fill=INK, width=4 * S)
        elif nombre.startswith("boca_"):
            tipo = nombre[5:]
            labio = (176, 70, 86)
            if tipo == "sonrisa":
                d.arc(P(282, 350, 318, 374), 20, 160, fill=labio, width=5 * S)
            elif tipo == "abierta":
                d.chord(P(286, 352, 314, 380), 0, 180, fill=labio)
            else:
                d.line(P(288, 364, 312, 364), fill=labio, width=5 * S)
        elif nombre == "brazo":                                                                     # brazo al frente
            manga = _hex(self.ropa2) if self.tipo_ropa == "saco" else _osc(ropa, 0.93)
            d.line(P(430, 520, 470, 590, 520, 600), fill=manga, width=46 * S, joint="curve")
            d.ellipse(P(500, 572, 548, 600), fill=piel)
        return im.resize((600, 600), Image.Resampling.LANCZOS)

    @lru_cache(maxsize=None)
    def _escalada(self, nombre, tam):
        return self.capa(nombre).resize((tam, tam), Image.Resampling.LANCZOS)

    def parpadea(self, t, semilla=3):
        rng = random.Random(semilla)
        x = rng.uniform(0.8, 2.0)
        while x < t + 1:
            if x <= t < x + 0.13:
                return True
            x += rng.uniform(3.0, 4.0)
        return False

    def pegar(self, lienzo, cx, cy, tam, t, hablando=False, brazo=False, boca="sonrisa"):
        """Personaje (busto) centrado en (cx, cy) con lado tam. Respira y parpadea."""
        tam = int(tam)
        capa = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        resp = 1 + 0.008 * math.sin(t * 2.0)
        for n in ("pelo_atras", "cuerpo"):
            capa.alpha_composite(self._escalada(n, tam))
        cab = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        b = ("abierta" if int(t * 7) % 2 else "neutra") if hablando else boca
        for n in ("cabeza", "ojos_cerrados" if self.parpadea(t) else "ojos_abiertos", "lentes", f"boca_{b}"):
            cab.alpha_composite(self._escalada(n, tam))
        cab = cab.rotate(1.5 * math.sin(t * 1.2), resample=Image.Resampling.BICUBIC, center=(tam / 2, tam * 0.7),
                         translate=(0, -2 * math.sin(t * 2.0) * (resp - 1) * 100))
        capa.alpha_composite(cab)
        if brazo:
            capa.alpha_composite(self._escalada("brazo", tam))
        lienzo.paste(capa, (int(cx - tam / 2), int(cy - tam / 2)), capa)


NATALIA = Personaje(piel="#E8B08A", pelo="#5B3A28", peinado="mono", ropa="#F3EFE7", ropa2="#2C3B57", tipo_ropa="blusa", edad=35)
ESPECTADORA = Personaje(piel="#D9A07A", pelo="#2E2226", peinado="suelto", ropa="#6E1C2E", ropa2="#6E1C2E", tipo_ropa="blusa",
                        aretes=True, edad=42)
