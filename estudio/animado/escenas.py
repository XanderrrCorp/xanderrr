"""Escenas de «Estándares altos» (Código del Éxito · mujeres). Todo dibujado con código (Pillow), sin stock.
Base de estilo: el demo del dueño (paleta, fuentes, easing, libreta, puertas, tarjetas de comentarios)."""
import math
import random
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
F = Path(__file__).resolve().parent.parent / "fuentes"

NIGHT = (18, 14, 20); WINE = (110, 28, 46); GOLD = (214, 172, 92)
CREAM = (246, 238, 224); INK = (40, 30, 36); WHITE = (255, 255, 255)
PAPER = (252, 248, 240); GREY = (120, 110, 115)


@lru_cache(maxsize=None)
def _f(nombre, tam):
    return ImageFont.truetype(str(F / nombre), max(8, int(tam)))


def BEBAS(s): return _f("BebasNeue-Regular.ttf", s)
def PLAY(s, w=700): return _f(f"Playfair-{ {400: 400, 500: 400, 600: 600, 700: 700}.get(w, 700) }.woff", s)
def HAND(s, w=600): return _f(f"Caveat-{ {400: 400, 600: 600, 700: 700}.get(w, 600) }.woff", s)


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def ease_io(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def back(t):  # entra con rebote suave
    t = max(0.0, min(1.0, t)); c = 1.7; return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
def lerp(a, b, t): return a + (b - a) * t
def mix(c1, c2, t): return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))
def rgba(c, a): return tuple(c) + (max(0, min(255, int(a))),)


def vignette_bg(c_center, c_edge, cx=0.5, cy=0.5):
    glow = Image.new("RGB", (W, H), c_edge)
    d = ImageDraw.Draw(glow)
    for i in range(14, 0, -1):
        r = i / 14
        d.ellipse([W * cx - 1150 * r, H * cy - 720 * r, W * cx + 1150 * r, H * cy + 720 * r], fill=mix(c_center, c_edge, r))
    return glow.filter(ImageFilter.GaussianBlur(70))


@lru_cache(maxsize=None)
def fondo(nombre):
    if nombre == "noche":
        return vignette_bg((58, 26, 38), NIGHT)
    if nombre == "vino":
        return vignette_bg((128, 34, 54), (34, 10, 18))
    return vignette_bg((252, 246, 236), (226, 212, 190))


def particulas(d, t, n=40, color=GOLD, fuerza=1.0, semilla=0):
    for i in range(n):
        ph = i * 1.7 + semilla
        x = (i * 211 + semilla * 37) % W + 30 * math.sin(t * 0.4 + ph)
        y = H - ((t * 46 + i * 97 + semilla * 53) % (H + 100))
        r = 2 + (i % 3)
        al = (70 + 60 * math.sin(t * 1.6 + ph)) * fuerza
        d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(color, al))


def lienzo(nombre, t=0.0, part=True):
    img = fondo(nombre).copy()
    d = ImageDraw.Draw(img, "RGBA")
    if part and nombre in ("noche", "vino"):
        particulas(d, t, 36 if nombre == "noche" else 28, GOLD, 0.9)
    return img, d


def envolver(d, texto, fuente, ancho):
    filas, linea = [], ""
    for p in texto.split():
        prueba = (linea + " " + p).strip()
        if d.textlength(prueba, font=fuente) > ancho and linea:
            filas.append(linea); linea = p
        else:
            linea = prueba
    if linea:
        filas.append(linea)
    return filas


def centro(d, xy, s, f, fill, anchor="mm"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


# ================================================================== tipografía animada (palabra por palabra)
def anillos(d, t, cx=W / 2, cy=H / 2, a=1.0):
    for k in range(3):
        r = 300 + k * 120 + 20 * math.sin(t * 0.8 + k)
        ini = (t * (18 + k * 9) * (1 if k % 2 else -1)) % 360
        d.arc([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], ini, ini + 200, fill=rgba(GOLD, (70 - k * 14) * a), width=4)


def barrido_luz(img, t, y0=200, y1=900, cada=3.2, desde=2.0):
    """Una franja de luz que cruza la pantalla cada ~3 s (algo siempre se mueve)."""
    if t < desde:
        return
    q = ((t - desde) % cada) / 0.9
    if q > 1:
        return
    d = ImageDraw.Draw(img, "RGBA")
    x = -300 + (W + 600) * E_ease(q)
    d.polygon([(x, y0), (x + 140, y0), (x + 40, y1), (x - 100, y1)], fill=(255, 240, 210, 26))


def E_ease(q):
    return 1 - (1 - max(0.0, min(1.0, q))) ** 3


def tipografia(t, dur, e):
    img, d = lienzo(e.get("fondo", "noche"), t)
    lado = bool(e.get("lado"))
    CX, ANCHO = (1300, 960) if lado else (W / 2, 1640)
    anillos(d, t, cx=CX)
    lineas = e["lineas"]
    n = len(lineas)
    tams = []
    for txt, _ in lineas:
        tam = 250 if n <= 2 else 190
        while d.textlength(txt, font=BEBAS(tam)) > ANCHO and tam > 60:
            tam -= 6
        tams.append(tam)
    alto = sum(tam * 0.92 for tam in tams)
    y = H / 2 - alto / 2 - 30
    k = 0
    for li, ((txt, col), tam) in enumerate(zip(lineas, tams)):
        y += tam * 0.46
        c = GOLD if col == "dorado" else WHITE
        f = BEBAS(tam)
        x = CX - d.textlength(txt, font=f) / 2
        lado = -1 if li % 2 == 0 else 1
        for pal in txt.split():
            st = 0.1 + k * 0.16
            p = back((t - st) / 0.45)
            q = ease((t - st) / 0.35)
            if q > 0:
                flota = 5 * math.sin(t * 2.2 + k)
                ff = BEBAS(int(tam * lerp(1.25, 1.0, min(1, q))))
                d.text((x + lado * (1 - min(1, p)) * 160, y + flota), pal, font=ff, fill=rgba(c, 255 * q), anchor="lm")
            x += d.textlength(pal + " ", font=f)
            k += 1
        y += tam * 0.46
    p = ease((t - (0.3 + k * 0.16)) / 0.8)
    if p > 0:
        x0 = CX - 380
        d.rounded_rectangle([x0, y + 30, x0 + 760 * p, y + 42], 6, fill=rgba(GOLD, 230))
        brillo = (t * 0.6) % 1.5
        if brillo < 1:
            bx = x0 + 760 * brillo
            d.ellipse([bx - 18, y + 22, bx + 18, y + 50], fill=rgba(WHITE, 160 * math.sin(brillo * math.pi)))
    barrido_luz(img, t)
    if e.get("final"):
        a = ease((t - (dur - 1.4)) / 1.4)
        if a > 0:
            img = Image.blend(img, Image.new("RGB", (W, H), NIGHT), a)
    return img


# ================================================================== frase sobre fondo oscuro (palabras que saltan)
def fondo_frase(t, dur, e):
    nombre = e.get("fondo", "noche")
    img, d = lienzo(nombre, t)
    lado = bool(e.get("lado"))
    CX, ANCHO = (1300, 900) if lado else (W / 2, 1500)
    anillos(d, t, cx=CX, a=0.8)
    respira = 0.5 + 0.5 * math.sin(t * 0.9)
    d.ellipse([CX - 560, H / 2 - 320, CX + 560, H / 2 + 320], fill=rgba(GOLD, 6 + 10 * respira))
    f = PLAY(84, 700)
    crudo = e["frase"]
    filas = envolver(d, crudo.replace("*", ""), f, ANCHO)
    marcas, dentro = [], False                      # qué palabras (por posición) van en dorado
    for tok in crudo.split():
        empieza = tok.startswith("*") or tok.startswith("«*")
        if empieza:
            dentro = True
        marcas.append(dentro)
        if tok.rstrip(".,;:!?»\"").endswith("*"):
            dentro = False
    palabras = sum(len(r.split()) for r in filas)
    vel = max(0.12, min(0.32, (min(3.0, dur * 0.45)) / max(1, palabras)))
    y = H / 2 - (len(filas) - 1) * 55 - 20
    k = 0
    for fila in filas:
        x = CX - d.textlength(fila, font=f) / 2
        for pal in fila.split():
            st = 0.25 + k * vel
            a = ease((t - st) / 0.3)
            if a > 0:
                es_clave = marcas[k] if k < len(marcas) else False
                tam = int(84 * lerp(1.5, 1.0, back((t - st) / 0.4))) if a < 1 else 84
                if es_clave:
                    tam = int(tam * (1.0 + 0.04 * math.sin(t * 4)))
                ff = PLAY(tam, 700)
                cx = x + d.textlength(pal, font=f) / 2
                d.text((cx, y + (1 - a) * 22), pal, font=ff, fill=rgba(GOLD if es_clave else CREAM, 255 * a), anchor="mm")
                if es_clave and a >= 1:
                    w_ = d.textlength(pal, font=f)
                    d.line([x, y + 52, x + w_ * ease((t - st - 0.3) / 0.4), y + 52], fill=rgba(GOLD, 230), width=5)
            x += d.textlength(pal + " ", font=f)
            k += 1
        y += 110
    barrido_luz(img, t)
    d = ImageDraw.Draw(img, "RGBA")
    p = ease((t - 0.6) / 1.0)
    d.line([CX - 90 * p, y + 10, CX + 90 * p, y + 10], fill=rgba(GOLD, 220), width=4)
    d.regular_polygon((CX, y + 10, 10 * p + 0.1), 4, rotation=45 + t * 40, fill=rgba(GOLD, 255 * p))
    return img


# ================================================================== libreta (del demo, con texto propio)
def libreta(t, dur, e):
    img = Image.new("RGB", (W, H), (60, 40, 42)); d = ImageDraw.Draw(img, "RGBA")
    for i in range(0, H, 6):
        c = mix((92, 62, 50), (70, 46, 40), (math.sin(i * 0.05) + 1) / 2)
        d.line([0, i, W, i], fill=c, width=6)
    z = lerp(1.04, 1.0, ease(t / 1.5))
    pw, ph = 1180 * z, 860 * z
    px, py = W / 2 - pw / 2, H / 2 - ph / 2
    d.rounded_rectangle([px + 18, py + 22, px + pw + 18, py + ph + 22], 24, fill=(0, 0, 0, 90))
    d.rounded_rectangle([px, py, px + pw, py + ph], 24, fill=CREAM)
    d.rectangle([px, py, px + 70 * z, py + ph], fill=WINE)
    for k in range(9):
        cy = py + 70 + k * (ph - 140) / 8
        d.ellipse([px + 50 * z, cy - 14, px + 90 * z, cy + 14], outline=(160, 160, 165), width=5)
    for k in range(10):
        y = py + 230 * z + k * 62 * z
        d.line([px + 130 * z, y, px + pw - 60 * z, y], fill=(180, 200, 220, 160), width=2)
    d.line([px + 200 * z, py + 40, px + 200 * z, py + ph - 40], fill=(220, 120, 120, 150), width=2)
    pa = ease(t / 0.6)
    d.text((px + 240 * z, py + 120 * z), e["titulo"], font=BEBAS(int(78 * z)), fill=rgba(WINE, 255 * pa), anchor="lm")
    msgs = e["lineas"]
    total = sum(len(m) for m in msgs)
    shown = int(total * ease_io((t - 0.6) / max(1.5, min(3.5, dur * 0.55))))
    y = py + 300 * z
    hf = HAND(int(84 * z))
    for m in msgs:
        n = max(0, min(len(m), shown)); shown -= len(m)
        if n:
            d.text((px + 240 * z, y), m[:n], font=hf, fill=INK, anchor="ls")
        y += 124 * z
    fin_esc = 0.6 + max(1.5, min(3.5, dur * 0.55))
    y = py + 300 * z
    for k, m in enumerate(msgs):                                   # resaltador que pasa línea por línea
        q = ease((t - fin_esc - 0.6 - k * 1.1) / 0.6)
        if q > 0:
            w_ = d.textlength(m, font=hf)
            d.rectangle([px + 236 * z, y - 30 * z, px + 236 * z + w_ * q, y + 6 * z], fill=(214, 172, 92, 70))
        y += 124 * z
    cb = ease((t - (0.6 + min(3.5, dur * 0.55) + 0.3)) / 0.5)
    bx, by = px + pw - 210 * z, py + 80 * z
    d.rounded_rectangle([bx, by, bx + 90 * z, by + 90 * z], 12, outline=WINE, width=6)
    if cb > 0:
        pts = [(bx + 18 * z, by + 48 * z), (bx + 38 * z, by + 70 * z), (bx + 76 * z, by + 18 * z)]
        if cb < 0.5:
            q = cb / 0.5; end = (lerp(pts[0][0], pts[1][0], q), lerp(pts[0][1], pts[1][1], q))
            d.line([pts[0], end], fill=GOLD, width=12)
        else:
            q = (cb - 0.5) / 0.5; end = (lerp(pts[1][0], pts[2][0], q), lerp(pts[1][1], pts[2][1], q))
            d.line([pts[0], pts[1], end], fill=GOLD, width=12, joint="curve")
    return img


# ================================================================== LA TABLA (hilo conductor)
COLS = ["Lo que tolero hoy", "Lo que me cuesta", "Mi nuevo mínimo"]
TX0, TY0, TW, TH = 160, 150, 1600, 750
LBL = 390
ROW_H = (TH - 120) / 5


LAPIZ = []


def _celdas_texto(d, texto, x, y, w, h, frac, fuente):
    filas = envolver(d, texto, fuente, w - 30)
    total = sum(len(r) for r in filas)
    shown = int(total * frac)
    yy = y + h / 2 - (len(filas) - 1) * fuente.size * 0.45
    for fila in filas:
        n = max(0, min(len(fila), shown)); shown -= len(fila)
        if n:
            d.text((x + 18, yy), fila[:n], font=fuente, fill=(32, 40, 92), anchor="lm")
            if 0 < frac < 1 and n < len(fila) or (0 < frac < 1 and shown <= 0 and n == len(fila)):
                LAPIZ.append((x + 18 + d.textlength(fila[:n], font=fuente), yy))
        yy += fuente.size * 0.9


def lapiz(d, x, y, t):
    """Lápiz que se mueve un poquito mientras escribe."""
    x += 6 * math.sin(t * 22); y += 4 * math.cos(t * 17)
    pts = [(x, y), (x + 22, y - 30), (x + 150, y - 150), (x + 128, y - 172), (x + 6, y - 50)]
    d.polygon([(x, y), (x + 10, y - 34), (x + 30, y - 22)], fill=(60, 50, 50))
    d.polygon([(x + 10, y - 34), (x + 138, y - 160), (x + 158, y - 140), (x + 30, y - 22)], fill=GOLD)
    d.polygon([(x + 138, y - 160), (x + 150, y - 172), (x + 170, y - 152), (x + 158, y - 140)], fill=(230, 150, 170))


def dibujar_tabla(t, e, tabla, celdas_progreso=None, activa=None, col_luz=None, dibujar_grid=1.0, cabeceras=1.0,
                  etiquetas=5, escala=1.0, dx=0.0, dy=0.0, fondo_nombre="crema"):
    """Dibuja la hoja de la tabla. celdas_progreso: {(fila, col): fracción escrita} (fila/col desde 1)."""
    img = fondo(fondo_nombre).copy()
    hoja = Image.new("RGBA", (TW + 40, TH + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(hoja, "RGBA")
    ox, oy = 20, 20
    d.rounded_rectangle([ox, oy, ox + TW, oy + TH], 22, fill=PAPER, outline=rgba(GOLD, 160), width=3)
    cw = (TW - LBL) / 3
    # resaltado de la fila activa
    if activa:
        p = ease(t / 0.5)
        y0 = oy + 120 + (activa - 1) * ROW_H
        d.rectangle([ox + 4, y0 + 2, ox + 4 + (TW - 8) * p, y0 + ROW_H - 2], fill=rgba(GOLD, 70))
        d.rectangle([ox + 4, y0 + 2, ox + 14, y0 + ROW_H - 2], fill=rgba(WINE, 255 * p))
    if col_luz:
        x0 = ox + LBL + (col_luz - 1) * cw
        d.rectangle([x0 + 2, oy + 4, x0 + cw - 2, oy + TH - 4], fill=rgba(GOLD, 60))
    # cuadrícula que se dibuja
    g = dibujar_grid
    lin = rgba(INK, 150)
    d.line([ox + 20, oy + 120, ox + 20 + (TW - 40) * ease(g), oy + 120], fill=rgba(WINE, 220), width=4)
    for k in range(1, 5):
        yk = oy + 120 + k * ROW_H
        d.line([ox + 20, yk, ox + 20 + (TW - 40) * ease(g * 1.2 - 0.1 * k), yk], fill=lin, width=2)
    for k in range(3):
        xk = ox + LBL + k * cw
        d.line([xk, oy + 20, xk, oy + 20 + (TH - 40) * ease(g * 1.2 - 0.15 * k)], fill=lin, width=2)
    # cabeceras
    for k, c in enumerate(COLS):
        a = max(0.0, min(1.0, cabeceras * 3 - k))
        if a > 0:
            x = ox + LBL + k * cw + cw / 2
            d.text((x, oy + 62 + (1 - a) * 16), c.upper(), font=BEBAS(60), fill=rgba(WINE, 255 * a), anchor="mm")
    # etiquetas de fila
    for k in range(5):
        a = max(0.0, min(1.0, etiquetas - k))
        if a <= 0:
            continue
        y = oy + 120 + k * ROW_H + ROW_H / 2
        nom = tabla["filas"][k]
        d.text((ox + 40, y), f"{k + 1}.", font=BEBAS(44), fill=rgba(GOLD, 255 * a), anchor="lm")
        d.text((ox + 80, y), nom.upper(), font=BEBAS(50), fill=rgba(INK, 255 * a), anchor="lm")
    # celdas manuscritas
    fu = HAND(52, 600)
    LAPIZ.clear()
    for (fi, co), frac in (celdas_progreso or {}).items():
        if frac <= 0:
            continue
        x = ox + LBL + (co - 1) * cw
        y = oy + 120 + (fi - 1) * ROW_H
        _celdas_texto(d, tabla["celdas"][fi - 1][co - 1], x, y, cw, ROW_H, frac, fu)
    if LAPIZ:
        lapiz(d, *LAPIZ[-1], t)
    # sombra + composición con cámara
    s = escala * lerp(1.0, 1.025, ease_io(t / 12.0))
    hw, hh = int((TW + 40) * s), int((TH + 40) * s)
    hoja_s = hoja.resize((hw, hh), Image.Resampling.BILINEAR)
    cx, cy = W / 2 + dx, (TY0 + TH / 2 + 12) + dy
    pos = (int(cx - hw / 2), int(cy - hh / 2))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([pos[0] + 22, pos[1] + 30, pos[0] + hw - 2, pos[1] + hh + 6], 26,
                                              fill=(60, 40, 30, 70))
    img = img.convert("RGBA")
    img.alpha_composite(sombra)
    img.alpha_composite(hoja_s, pos)
    return img.convert("RGB")


def _llenas(n):
    return {(f, c): 1.0 for f in range(1, n + 1) for c in (1, 2, 3)}


def tabla(t, dur, e, tab):
    modo = e.get("modo", "fila")
    llenas = _llenas(e.get("llenas", 0))
    titulo = None
    kw = {}
    if modo == "presentar":
        kw = dict(dibujar_grid=ease(t / 2.2), cabeceras=0, etiquetas=0, dy=(1 - ease(t / 0.9)) * 300)
        titulo = "TU TABLA DE ESTÁNDARES"
    elif modo == "columnas":
        kw = dict(cabeceras=ease_io(t / max(2.0, dur * 0.8)), etiquetas=0)
    elif modo == "filas":
        kw = dict(etiquetas=5 * ease_io(t / max(2.0, dur * 0.75)))
        if t > dur * 0.78:
            kw["activa"] = 5
    elif modo == "fila":
        fila = e["fila"]
        z = ease_io((t - 0.6) / 1.4)
        rel = (20 + 120 + (fila - 0.5) * ROW_H) - (TH + 40) / 2
        kw = dict(activa=fila, escala=lerp(1.0, 1.05, z), dy=lerp(0, 25, z))
        titulo = f"FILA {e['fila']}"
    elif modo == "escribir":
        fila, cols = e["fila"], e["columnas"]
        frac = ease_io((t - 0.5) / max(2.0, dur * 0.8))
        prog = dict(llenas)
        if cols[0] > 1:                                        # lo de antes de esta fila ya está escrito
            for c in range(1, cols[0]):
                prog[(fila, c)] = 1.0
        for k, c in enumerate(cols):
            prog[(fila, c)] = max(0.0, min(1.0, frac * len(cols) - k))
        z = ease_io(t / 1.2) * (1 - ease_io((t - dur + 1.0) / 1.0))
        rel = (20 + 120 + (fila - 0.5) * ROW_H) - (TH + 40) / 2
        esc = lerp(1.0, 1.14, z)
        dy = lerp(0, 520 - (TY0 + TH / 2 + 12) - rel * 1.14, z)
        dy = max(dy, 20 - (TY0 + TH / 2 + 12) + (TH + 40) * esc / 2)      # que no se corte la fila de títulos
        kw = dict(activa=fila, celdas_progreso=prog, escala=esc, dy=dy)
    elif modo in ("completa", "doblar"):
        kw = dict(celdas_progreso=llenas)
        if modo == "doblar":
            p = ease_io((t - 1.0) / 2.5)
            kw.update(escala=lerp(1.0, 0.42, p), dy=lerp(0, -170, p))
    elif modo == "mapa":
        k = min(3, 1 + int(t / max(1.5, dur / 3)))
        kw = dict(celdas_progreso=llenas, col_luz=k)
        titulo = ["DÓNDE ESTÁS", "CUÁNTO TE CUESTA", "A DÓNDE VAS"][k - 1]
    if "celdas_progreso" not in kw:
        kw["celdas_progreso"] = llenas
    img = dibujar_tabla(t, e, tab, **kw)
    d = ImageDraw.Draw(img, "RGBA")
    if titulo:
        a = ease(t / 0.5)
        d.text((W / 2, 92), titulo, font=BEBAS(78), fill=rgba(WINE, 255 * a), anchor="mm")
    if modo == "completa":
        for f in range(5):                                     # una palomita dorada por fila
            p = ease((t - 0.6 - f * 0.35) / 0.4)
            if p > 0:
                y = TY0 + 30 + 120 + f * ROW_H + ROW_H / 2 + 20
                x = TX0 + TW + 6
                d.ellipse([x - 26 * p, y - 26 * p, x + 26 * p, y + 26 * p], fill=rgba(GOLD, 255))
                d.line([(x - 11, y), (x - 3, y + 9), (x + 12, y - 9)], fill=rgba(WHITE, 255 * p), width=6)
        d.text((W / 2, 92), "CINCO FILAS · QUINCE CASILLAS", font=BEBAS(70), fill=rgba(WINE, 255 * ease(t / 0.5)), anchor="mm")
    if modo == "doblar":
        p = ease((t - 2.8) / 0.8)
        if p > 0:
            d.text((W / 2, 740), "Guárdala donde la veas", font=PLAY(66, 700), fill=rgba(WINE, 255 * p), anchor="mm")
            d.text((W / 2, 820), "y esta semana lee solo la tercera columna", font=PLAY(44, 400), fill=rgba(INK, 230 * p), anchor="mm")
    return img


def temporizador(d, cx, cy, r, frac_restante, numero, a=255):
    d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=rgba(NIGHT, 0.85 * a))
    d.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=rgba(GREY, 0.5 * a), width=18)
    if frac_restante > 0:
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac_restante, fill=rgba(GOLD, a), width=18)
    d.text((cx, cy + 6), numero, font=BEBAS(int(r * 1.1)), fill=rgba(WHITE, a), anchor="mm")


def pausa(t, dur, e, tab):
    fila = e["fila"]
    prog = _llenas(fila)
    img = dibujar_tabla(t, e, tab, celdas_progreso=prog, activa=fila, escala=0.78, dx=-230, dy=10)
    d = ImageDraw.Draw(img, "RGBA")
    t0 = e["temporizador_desde"] - e["inicio"]                  # cuándo empieza el silencio de 3 s
    cx, cy, r = 1640, 520, 150
    a = 255 * ease(t / 0.4)
    if t < t0:
        temporizador(d, cx, cy, r, 1.0, "3", a)
    else:
        q = (t - t0) / 3.0
        temporizador(d, cx, cy, r, max(0.0, 1 - q), str(max(1, 3 - int(q * 3))), a)
    pulso = 0.85 + 0.15 * math.sin(t * 5)
    d.text((cx, cy - r - 70), "PAUSA", font=BEBAS(int(96 * pulso)), fill=rgba(WINE, a), anchor="mm")
    d.text((cx, cy + r + 66), "y escribe", font=HAND(78, 700), fill=rgba(INK, a), anchor="mm")
    d.text((W / 2 - 230, 70), f"FILA {fila} · {tab['filas'][fila - 1].upper()}", font=BEBAS(70), fill=rgba(WINE, a), anchor="mm")
    return img


# ================================================================== test Sí / No
def test(t, dur, e):
    img, d = lienzo("noche", t)
    pr = e["preguntas"]
    paso = max(2.5, (dur - 1.5) / len(pr))
    d.text((W / 2, 110), "TEST RÁPIDO", font=BEBAS(96), fill=rgba(GOLD, 255 * ease(t / 0.5)), anchor="mm")
    d.text((W / 2, 180), "responde en tu mente", font=PLAY(40, 400), fill=rgba(CREAM, 200 * ease(t / 0.8)), anchor="mm")
    for k, q in enumerate(pr):
        st = 0.5 + k * paso
        p = ease((t - st) / 0.6)
        if p <= 0:
            continue
        y = 300 + k * 175
        x = lerp(-200, 170, p)
        d.rounded_rectangle([x, y, x + 1580, y + 140], 24, fill=rgba((40, 26, 34), 240), outline=rgba(GOLD, 90), width=2)
        d.text((x + 50, y + 70), q, font=PLAY(46, 600), fill=rgba(CREAM, 255 * p), anchor="lm")
        for j, et in enumerate(("SÍ", "NO")):
            bx = x + 1250 + j * 160
            d.rounded_rectangle([bx, y + 38, bx + 64, y + 102], 10, outline=rgba(CREAM, 220 * p), width=4)
            d.text((bx + 94, y + 72), et, font=BEBAS(48), fill=rgba(CREAM, 220 * p), anchor="mm")
        c = ease((t - st - 1.1) / 0.4)
        if c > 0:
            bx = x + 1250
            d.line([(bx + 12, y + 70), (bx + 28, y + 88)], fill=rgba(GOLD, 255), width=9)
            if c > 0.4:
                q2 = (c - 0.4) / 0.6
                d.line([(bx + 28, y + 88), (bx + 28 + 30 * q2, y + 88 - 46 * q2)], fill=rgba(GOLD, 255), width=9)
    return img


# ================================================================== preguntas al espejo (una a la vez)
def preguntas(t, dur, e):
    img, d = lienzo("noche", t)
    pr = e["preguntas"]
    paso = dur / len(pr)
    k = min(len(pr) - 1, int(t / paso))
    tl = t - k * paso
    # espejo ovalado
    cx, cy = W / 2, H / 2 - 20
    d.ellipse([cx - 360, cy - 430, cx + 360, cy + 430], outline=rgba(GOLD, 200), width=10)
    d.ellipse([cx - 340, cy - 410, cx + 340, cy + 410], fill=rgba((60, 40, 52), 160))
    brillo = (t * 0.25) % 1.6 - 0.3
    d.polygon([(cx - 300 + 600 * brillo, cy - 380), (cx - 220 + 600 * brillo, cy - 380),
               (cx - 360 + 600 * brillo, cy + 380), (cx - 440 + 600 * brillo, cy + 380)], fill=rgba(WHITE, 14))
    a = ease(tl / 0.5) * (1 - ease((tl - paso + 0.4) / 0.4))
    f = PLAY(62, 700)
    filas = envolver(d, pr[k], f, 600)
    y = cy - (len(filas) - 1) * 40
    for fila in filas:
        d.text((cx, y), fila, font=f, fill=rgba(CREAM, 255 * a), anchor="mm"); y += 80
    for j in range(len(pr)):
        x = W / 2 - (len(pr) - 1) * 22 + j * 44
        d.ellipse([x - 8, 50 - 8, x + 8, 50 + 8], fill=rgba(GOLD if j <= k else GREY, 230))
    return img


# ================================================================== puertas (del demo)
def door(d, cx, base, w, h, color, swing=0.0, lock=None):
    vis = w * (1 - 0.55 * abs(swing))
    x0 = cx - w / 2 if swing >= 0 else cx + w / 2 - vis
    d.rectangle([cx - w / 2 - 26, base - h - 26, cx + w / 2 + 26, base], fill=(60, 40, 34))
    d.rectangle([cx - w / 2, base - h, cx + w / 2, base], fill=(25, 18, 22))
    shade = mix(color, (0, 0, 0), 0.35 * abs(swing))
    d.rectangle([x0, base - h, x0 + vis, base], fill=shade)
    for k in range(2):
        py0 = base - h + 40 + k * (h - 80) / 2
        d.rectangle([x0 + vis * 0.15, py0, x0 + vis * 0.85, py0 + (h - 80) / 2 - 30], outline=mix(shade, (0, 0, 0), 0.3), width=6)
    if lock is not None:
        hx = x0 + vis * 0.82; hy = base - h / 2
        d.ellipse([hx - 18, hy - 18, hx + 18, hy + 18], fill=GOLD)
        bx = lerp(hx - 70, hx + 10, lock)
        d.rounded_rectangle([bx - 40, hy - 70, bx + 40, hy - 50], 8, fill=GOLD)
        d.rectangle([hx - 4, hy - 60, hx + 4, hy - 18], fill=GOLD)


def puertas(t, dur, e):
    img, d = lienzo("noche", t, part=False)
    base = 900
    d.rectangle([0, base, W, H], fill=(30, 22, 26))
    sw = math.sin(t * 5.5) * max(0.15, 1 - t / dur)
    door(d, 560, base, 340, 560, (150, 120, 100), swing=sw)
    lk = ease((t - 2.2) / 0.7)
    door(d, 1360, base, 360, 580, WINE, swing=0, lock=lk)
    for k, fx in enumerate([1120, 1600]):
        d.rounded_rectangle([fx - 50, base - 110, fx + 50, base], 10, fill=(150, 90, 60))
        for j in range(5):
            ang = j * 1.25 + k
            cx, cy = fx + math.cos(ang) * 30, base - 150 + math.sin(ang) * 24
            d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=(230, 150, 170) if j % 2 else GOLD)
    a1 = 255 * ease((t - 0.3) / 0.6); a2 = 255 * ease((t - 1.2) / 0.6)
    centro(d, (560, 170), "LO QUE DICES", BEBAS(86), rgba(WHITE, a1))
    centro(d, (560, 245), "cualquiera la empuja", PLAY(44, 400), (200, 190, 190, int(a1)))
    centro(d, (1360, 170), "LO QUE HACES TÚ", BEBAS(86), rgba(GOLD, a2))
    centro(d, (1360, 245), "si cruzan la línea, se cierra", PLAY(44, 400), (230, 215, 190, int(a2)))
    if lk >= 1:
        p = ease((t - 3.0) / 0.5)
        centro(d, (1680, 560), "¡CLIC!", BEBAS(int(110 * lerp(1.6, 1, p))), rgba(GOLD, 255 * p))
    return img


# ================================================================== comentario que se escribe solo
def icono_comentario(d, cx, cy, s, color):
    d.rounded_rectangle([cx - s, cy - s * 0.75, cx + s, cy + s * 0.55], s * 0.3, fill=color)
    d.polygon([(cx - s * 0.5, cy + s * 0.5), (cx - s * 0.65, cy + s * 1.0), (cx - s * 0.05, cy + s * 0.5)], fill=color)
    for k in (-1, 0, 1):
        d.ellipse([cx + k * s * 0.45 - s * 0.12, cy - s * 0.22, cx + k * s * 0.45 + s * 0.12, cy + 0.02 * s], fill=NIGHT)


def comentario(t, dur, e):
    img, d = lienzo("noche", t)
    p = back(t / 0.7)
    x0, y0, w, h = 300, 330, 1320, 300
    yy = y0 + (1 - p) * 120
    d.rounded_rectangle([x0 + 12, yy + 16, x0 + w + 12, yy + h + 16], 30, fill=(0, 0, 0, 120))
    d.rounded_rectangle([x0, yy, x0 + w, yy + h], 30, fill=WHITE)
    d.ellipse([x0 + 50, yy + 50, x0 + 140, yy + 140], fill=WINE)
    centro(d, (x0 + 95, yy + 97), "TÚ", BEBAS(48), WHITE)
    d.text((x0 + 170, yy + 75), "Tu comentario", font=PLAY(34, 600), fill=GREY, anchor="lm")
    frase = e["frase"]
    n = int(len(frase) * ease_io((t - 0.8) / 1.8))
    d.text((x0 + 170, yy + 170), frase[:n], font=PLAY(78, 700), fill=INK, anchor="lm")
    if n < len(frase) or int(t * 2) % 2:
        cx = x0 + 170 + d.textlength(frase[:n], font=PLAY(78, 700)) + 8
        d.rectangle([cx, yy + 130, cx + 6, yy + 210], fill=WINE)
    q = back((t - 2.9) / 0.5)
    if q > 0:
        icono_comentario(d, W / 2, 740, 70 * q, GOLD)
        d.text((W / 2, 860), "Escríbelo en los comentarios, tal cual", font=PLAY(48, 600), fill=rgba(CREAM, 255 * min(1, q)), anchor="mm")
    d.text((W / 2, 200), e.get("encabezado", "DEBAJO DE TU TABLA, EN LETRAS GRANDES"), font=BEBAS(64), fill=rgba(GOLD, 255 * ease(t / 0.6)), anchor="mm")
    return img


# ================================================================== tarjetas de comentarios (del demo)
COMMENTS = [
    ("M", "No mendigo amor, me lo doy yo primero.", 1840),
    ("R", "Siempre he sido joya, no oferta. Y de donde me voy, no vuelvo.", 1312),
    ("L", "Un tropiezo no es un camino.", 977),
]


def corazon(d, hx, hy, s, color):
    d.ellipse([hx - 2 * s, hy - s, hx, hy + s / 2], fill=color)
    d.ellipse([hx - s * 1.0, hy - s, hx + s, hy + s / 2], fill=color)
    d.polygon([(hx - 2 * s, hy), (hx + s, hy), (hx - s / 2, hy + 1.6 * s)], fill=color)


def comentarios(t, dur, e):
    img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
    ha = ease(t / 0.5)
    centro(d, (W / 2, 130), "LO QUE ESCRIBIERON USTEDES", BEBAS(110), rgba(WINE, 255 * ha))
    d.rounded_rectangle([W / 2 - 200, 195, W / 2 - 200 + 400 * ha, 203], 4, fill=GOLD)
    for i, (ini, txt, likes) in enumerate(COMMENTS):
        st = 0.5 + i * 0.9
        p = ease((t - st) / 0.7)
        if p <= 0:
            continue
        x = lerp(W + 50, 260, p); y = 260 + i * 215
        d.rounded_rectangle([x + 10, y + 14, x + 1410, y + 194], 28, fill=(0, 0, 0, 30))
        d.rounded_rectangle([x, y, x + 1400, y + 180], 28, fill=WHITE)
        d.ellipse([x + 40, y + 45, x + 130, y + 135], fill=[WINE, GOLD, (150, 110, 130)][i])
        centro(d, (x + 85, y + 92), ini, BEBAS(64), WHITE)
        tf = PLAY(46, 600)
        rows = envolver(d, txt, tf, 1050)
        for r_, row in enumerate(rows):
            d.text((x + 170, y + 90 + (r_ - (len(rows) - 1) / 2) * 58), row, font=tf, fill=INK, anchor="lm")
        c = int(likes * ease((t - st - 0.3) / 1.5))
        num = f"{c:,}".replace(",", ".")
        d.text((x + 1340, y + 90), num, font=BEBAS(56), fill=WINE, anchor="rm")
        corazon(d, x + 1340 - d.textlength(num, font=BEBAS(56)) - 30, y + 90, 14, WINE)
    fa = ease((t - 3.6) / 0.6)
    del fa
    return img


# ================================================================== ilustraciones planas (sin caras)
def persona(d, x, base, alto, cuerpo, pelo, a=255, brazo=0.0):
    """Figura plana: cabeza sin rasgos, pelo, vestido. brazo: -1..1 levanta el brazo derecho."""
    r = alto * 0.11
    hy = base - alto + r
    d.polygon([(x - alto * 0.2, base), (x + alto * 0.2, base), (x + alto * 0.1, hy + r * 1.3), (x - alto * 0.1, hy + r * 1.3)], fill=rgba(cuerpo, a))
    d.ellipse([x - r * 1.15, hy - r * 1.1, x + r * 1.15, hy + r * 1.6], fill=rgba(pelo, a))
    d.ellipse([x - r, hy - r, x + r, hy + r], fill=rgba((214, 170, 140), a))
    d.pieslice([x - r * 1.1, hy - r * 1.15, x + r * 1.1, hy + r * 0.9], 180, 360, fill=rgba(pelo, a))
    hx, hy2 = x + alto * 0.1, hy + r * 1.6
    ex, ey = hx + alto * 0.22, hy2 + alto * (0.25 - 0.45 * brazo)
    d.line([(hx, hy2), (ex, ey)], fill=rgba(cuerpo, a), width=int(alto * 0.05))
    d.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], fill=rgba((214, 170, 140), a))
    return ex, ey


def historia(t, dur, e):
    esc = e["escena"]
    if esc == "soltar":
        img, d = lienzo("crema", t, part=False)
        d.rectangle([0, 860, W, H], fill=(226, 210, 186))
        p = ease(t / 0.8)
        ex, ey = persona(d, 760, 860, 560, WINE, (70, 40, 40), 255 * p, brazo=0.55)
        # pesos oscuros atados que se sueltan uno a uno; destellos dorados al soltarse
        for k in range(4):
            suelta = (t - 2.0 - k * 1.6)
            gx = ex + 130 + k * 120
            if suelta < 0:
                gy = ey + 160 + (k % 2) * 40
                d.line([(ex, ey), (gx, gy - 40)], fill=rgba(INK, 180), width=3)
            else:
                gy = ey + 160 + (k % 2) * 40 + 600 * suelta ** 2
                for j in range(6):
                    ang = j * math.pi / 3 + suelta * 3
                    rr = 40 + 160 * ease(suelta / 1.2)
                    sx, sy = ex + math.cos(ang) * rr, ey + math.sin(ang) * rr
                    d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=rgba(GOLD, 255 * (1 - ease(suelta / 1.2))))
            if gy < H + 80:
                d.rounded_rectangle([gx - 42, gy - 40, gx + 42, gy + 40], 12, fill=rgba((70, 60, 66), 255))
        d.text((1240, 330), "UNA ESPECTADORA", font=BEBAS(70), fill=rgba(WINE, 255 * p), anchor="lm")
        q = ease((t - 1.0) / 0.8)
        for k, fila in enumerate(envolver(d, e["texto"], PLAY(56, 700), 560)):
            d.text((1240, 430 + k * 76), fila, font=PLAY(56, 700), fill=rgba(INK, 255 * q), anchor="lm")
        return img
    if esc == "oficina":
        img, d = lienzo("noche", t, part=False)
        # ventana con edificios y luna
        d.rectangle([1100, 120, 1760, 640], fill=(26, 24, 44), outline=(70, 50, 60), width=14)
        d.ellipse([1560, 170, 1660, 270], fill=(240, 226, 196))
        rnd = random.Random(4)
        for k in range(9):
            bx = 1120 + k * 72; bh = rnd.randint(140, 330)
            d.rectangle([bx, 640 - bh, bx + 60, 640], fill=(40, 34, 56))
            for j in range(0, bh - 30, 34):
                if rnd.random() < 0.35:
                    d.rectangle([bx + 14, 640 - bh + 18 + j, bx + 26, 640 - bh + 30 + j], fill=rgba(GOLD, 200))
        d.rectangle([0, 780, W, H], fill=(36, 24, 30))
        d.rectangle([380, 700, 1380, 740], fill=(110, 70, 52))
        d.rectangle([420, 740, 450, 980], fill=(90, 56, 42)); d.rectangle([1310, 740, 1340, 980], fill=(90, 56, 42))
        persona(d, 760, 760, 420, WINE, (60, 36, 36), brazo=0.1)
        # lámpara con luz
        luz = 0.85 + 0.15 * math.sin(t * 3)
        d.polygon([(1080, 520), (1180, 520), (1260, 700), (1000, 700)], fill=rgba(GOLD, 40 * luz))
        d.polygon([(1090, 470), (1170, 470), (1190, 520), (1070, 520)], fill=GOLD)
        d.line([(1130, 520), (1130, 700)], fill=(160, 140, 120), width=6)
        # papeles que se apilan
        n = min(9, int(t * 1.2))
        for k in range(n):
            d.rectangle([880 + (k % 2) * 8, 690 - k * 9, 1020 + (k % 2) * 8, 700 - k * 9], fill=(240, 232, 216), outline=(200, 190, 175))
        # reloj
        cx, cy = 300, 260
        d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=CREAM, outline=GOLD, width=8)
        ang = -math.pi / 2 + t * 0.6
        d.line([(cx, cy), (cx + 60 * math.cos(ang), cy + 60 * math.sin(ang))], fill=INK, width=6)
        d.line([(cx, cy), (cx + 36 * math.cos(math.pi / 3), cy + 36 * math.sin(math.pi / 3))], fill=INK, width=9)
        a = ease(t / 0.6)
        d.text((160, 470), "NATALIA", font=BEBAS(110), fill=rgba(GOLD, 255 * a), anchor="lm")
        q = ease((t - 1.0) / 0.8)
        for k, fila in enumerate(["la que se quedaba hasta tarde,", "la que cubría a todos,", "la que nunca pedía aumento"]):
            r = ease((t - 1.0 - k * 2.2) / 0.6)
            d.text((160, 560 + k * 56), fila, font=PLAY(40, 400), fill=rgba(CREAM, 230 * r), anchor="lm")
        return img
    # celular a las 11 p. m.
    img, d = lienzo("noche", t, part=False)
    vib = math.sin(t * 60) * 6 if 1.5 < t < 2.6 else 0
    cx, cy = W / 2 + 330 + vib, H / 2 + 20
    d.rounded_rectangle([cx - 230, cy - 440, cx + 230, cy + 440], 60, fill=(24, 22, 28), outline=(90, 80, 90), width=10)
    d.rounded_rectangle([cx - 205, cy - 400, cx + 205, cy + 400], 44, fill=(40, 30, 50))
    d.text((cx, cy - 300), "11:00", font=BEBAS(150), fill=CREAM, anchor="mm")
    d.text((cx, cy - 200), "jueves", font=PLAY(36, 400), fill=rgba(CREAM, 200), anchor="mm")
    p = back((t - 1.5) / 0.6)
    if p > 0:
        y = cy - 90 + (1 - min(1, p)) * 60
        d.rounded_rectangle([cx - 185, y, cx + 185, y + 150], 26, fill=rgba(CREAM, 245))
        d.text((cx - 160, y + 42), "ÉL", font=BEBAS(44), fill=WINE, anchor="lm")
        d.text((cx - 160, y + 100), "¿Qué haces? ;)", font=PLAY(36, 600), fill=INK, anchor="lm")
    q = ease((t - 3.5) / 0.6)
    if q > 0:
        y = cy + 90
        d.rounded_rectangle([cx - 185, y, cx + 185, y + 120], 26, fill=rgba(WINE, 240 * q))
        d.text((cx, y + 60), "Tu hermano: ¿me prestas?", font=PLAY(30, 600), fill=rgba(CREAM, 255 * q), anchor="mm")
    a = ease(t / 0.6)
    d.text((220, 400), "EL PROBLEMA", font=BEBAS(96), fill=rgba(WHITE, 255 * a), anchor="lm")
    d.text((220, 500), "LLEGA EL JUEVES", font=BEBAS(110), fill=rgba(GOLD, 255 * a), anchor="lm")
    d.text((220, 600), "y la culpa aparece en un segundo", font=PLAY(42, 400), fill=rgba(CREAM, 220 * ease((t - 1) / 0.6)), anchor="lm")
    return img


# ================================================================== diamante vs piedra
def diamante_dibujo(d, cx, cy, s, t, a=255):
    top = [(cx - s, cy - s * 0.35), (cx - s * 0.55, cy - s * 0.8), (cx + s * 0.55, cy - s * 0.8), (cx + s, cy - s * 0.35)]
    abajo = (cx, cy + s * 1.05)
    caras = [
        ([top[0], top[1], (cx - s * 0.2, cy - s * 0.35)], (250, 236, 200)),
        ([top[1], top[2], (cx + s * 0.2, cy - s * 0.35), (cx - s * 0.2, cy - s * 0.35)], (255, 250, 236)),
        ([top[2], top[3], (cx + s * 0.2, cy - s * 0.35)], (236, 214, 164)),
        ([top[0], (cx - s * 0.2, cy - s * 0.35), abajo], (226, 196, 130)),
        ([(cx - s * 0.2, cy - s * 0.35), (cx + s * 0.2, cy - s * 0.35), abajo], GOLD),
        ([(cx + s * 0.2, cy - s * 0.35), top[3], abajo], (180, 136, 64)),
    ]
    for pts, col in caras:
        d.polygon(pts, fill=rgba(col, a), outline=rgba(WHITE, 0.6 * a))
    for k in range(3):                                          # destellos que giran
        fase = (t * 0.8 + k * 0.33) % 1.0
        br = math.sin(fase * math.pi)
        gx = cx + s * (-0.5 + k * 0.5); gy = cy - s * (0.6 - 0.25 * k)
        L = 20 + 60 * br
        d.line([(gx - L, gy), (gx + L, gy)], fill=rgba(WHITE, 255 * br * a / 255), width=4)
        d.line([(gx, gy - L), (gx, gy + L)], fill=rgba(WHITE, 255 * br * a / 255), width=4)


def diamante(t, dur, e):
    img, d = lienzo("noche", t)
    d.rectangle([0, 820, W, H], fill=(30, 22, 26))
    a1 = ease(t / 0.7)
    rnd = random.Random(7)
    pts = [(560 + 190 * math.cos(k * 0.7) * rnd.uniform(0.8, 1.1), 700 + 130 * math.sin(k * 0.7) * rnd.uniform(0.8, 1.1)) for k in range(9)]
    d.polygon(pts, fill=rgba((96, 90, 94), 255 * a1))
    d.polygon([(p[0] * 0.95 + 20, p[1] * 0.95 + 20) for p in pts[:5]], fill=rgba((120, 114, 118), 255 * a1))
    a2 = ease((t - 1.0) / 0.8)
    halo = 0.6 + 0.4 * math.sin(t * 2)
    d.ellipse([1360 - 300, 600 - 300, 1360 + 300, 600 + 300], fill=rgba(GOLD, 25 * halo * a2))
    diamante_dibujo(d, 1360, 560, 220 * lerp(0.7, 1.0, back((t - 1.0) / 0.8)) if a2 > 0 else 1, t, 255 * a2)
    centro(d, (560, 220), e["texto_izq"], BEBAS(90), rgba(CREAM, 255 * a1))
    centro(d, (1360, 220), e["texto_der"], BEBAS(110), rgba(GOLD, 255 * a2))
    pie = {"costo": "eso es lo que de verdad sale caro",
           "presion": "la misma tierra · el diamante aguantó la presión"}.get(e.get("variante"), "la gente te trata como ve que tú te tratas")
    q = ease((t - 2.2) / 0.7)
    centro(d, (W / 2, 860), pie, PLAY(50, 600), rgba(CREAM, 255 * q))
    return img


# ================================================================== MI VALOR (PDF + sello)
def mivalor(t, dur, e):
    img, d = lienzo("vino", t)
    p = back(t / 0.9)
    cx, cy = 660, 560 + (1 - min(1, p)) * 200
    hoja = Image.new("RGBA", (620, 820), (0, 0, 0, 0))
    h = ImageDraw.Draw(hoja, "RGBA")
    for k in (3, 2, 1):                                          # páginas detrás
        h.rectangle([10 + k * 8, 10 + k * 6, 590 + k * 8, 790 + k * 6], fill=(230, 220, 204))
    h.rectangle([10, 10, 590, 790], fill=CREAM)
    h.rectangle([34, 34, 566, 766], outline=GOLD, width=4)
    diamante_dibujo(h, 300, 250, 90, t)
    h.text((300, 450), "MI VALOR", font=PLAY(84, 700), fill=WINE, anchor="mm")
    h.text((300, 530), "Programa de amor propio", font=PLAY(32, 400), fill=INK, anchor="mm")
    h.rounded_rectangle([200, 600, 400, 670], 35, fill=WINE)
    h.text((300, 636), "21 DÍAS", font=BEBAS(52), fill=CREAM, anchor="mm")
    h.text((300, 730), "PDF", font=BEBAS(36), fill=GREY, anchor="mm")
    hoja = hoja.rotate(-5 + 2 * math.sin(t * 0.6), resample=Image.Resampling.BICUBIC, expand=True)
    sombra = Image.new("RGBA", hoja.size, (0, 0, 0, 0))
    sombra.paste((0, 0, 0, 110), mask=hoja.getchannel("A"))
    img = img.convert("RGBA")
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(12)), (int(cx - hoja.width / 2 + 24), int(cy - hoja.height / 2 + 30)))
    img.alpha_composite(hoja, (int(cx - hoja.width / 2), int(cy - hoja.height / 2)))
    d = ImageDraw.Draw(img, "RGBA")
    items = ["21 días de amor propio", "Un ejercicio corto antes de cada conversación difícil", "Para sostener tu nuevo mínimo sin culpa"]
    for k, it in enumerate(items):
        q = ease((t - 0.8 - k * 0.7) / 0.6)
        if q > 0:
            y = 380 + k * 130
            d.regular_polygon((1110, y, 14), 4, rotation=45, fill=rgba(GOLD, 255 * q))
            for j, fila in enumerate(envolver(d, it, PLAY(44, 600), 640)):
                d.text((1150 + (1 - q) * 30, y + j * 54), fila, font=PLAY(44, 600), fill=rgba(CREAM, 255 * q), anchor="lm")
    q = ease((t - 3.0) / 0.6)
    d.text((1110, 820), "Enlace en la descripción y en el comentario fijado", font=PLAY(34, 400), fill=rgba(CREAM, 210 * q), anchor="lm")
    if e.get("sello"):
        s = ease((t - 1.6) / 0.35)
        if s > 0:
            esc = lerp(1.8, 1.0, s)
            sx, sy, r = 990, 300, 120 * esc
            sello = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            g = ImageDraw.Draw(sello, "RGBA")
            g.ellipse([20, 20, 380, 380], fill=rgba(GOLD, 245), outline=rgba(WHITE, 230), width=6)
            g.ellipse([46, 46, 354, 354], outline=rgba(WINE, 200), width=4)
            g.text((200, 150), "7 DÍAS", font=BEBAS(96), fill=WINE, anchor="mm")
            g.text((200, 240), "DE GARANTÍA", font=BEBAS(60), fill=WINE, anchor="mm")
            sello = sello.rotate(12, resample=Image.Resampling.BICUBIC).resize((int(2 * r), int(2 * r)))
            img.alpha_composite(sello, (int(sx - r), int(sy - r)))
    return img.convert("RGB")


# ================================================================== membresía
def membresia(t, dur, e):
    img, d = lienzo("noche", t)
    a = ease(t / 0.6)
    centro(d, (W / 2, 210), "EL CÍRCULO", BEBAS(120), rgba(GOLD, 255 * a))
    centro(d, (W / 2, 300), "para sostener tu tabla semana tras semana", PLAY(44, 400), rgba(CREAM, 220 * a))
    # botón «Unirme» con cursor que llega y hace clic
    clic = 2.4
    presion = 1 - 0.08 * math.sin(min(1, max(0, (t - clic) / 0.25)) * math.pi)
    pulso = 1 + 0.03 * math.sin(t * 4) if t > clic + 0.3 else 1
    s = back((t - 0.5) / 0.6) * presion * pulso
    bw, bh = 420 * s, 130 * s
    cx, cy = W / 2, 500
    if s > 0:
        d.rounded_rectangle([cx - bw / 2 + 8, cy - bh / 2 + 10, cx + bw / 2 + 8, cy + bh / 2 + 10], 65 * s, fill=(0, 0, 0, 120))
        d.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], 65 * s, fill=GOLD)
        centro(d, (cx, cy + 4), "UNIRME", BEBAS(int(78 * s)), NIGHT)
    k = ease_io((t - 1.0) / 1.3)
    mx, my = lerp(1500, cx + 60, k), lerp(900, cy + 20, k)
    d.polygon([(mx, my), (mx, my + 60), (mx + 16, my + 46), (mx + 28, my + 72), (mx + 38, my + 66), (mx + 26, my + 42), (mx + 46, my + 42)],
              fill=WHITE, outline=NIGHT)
    if t > clic:
        o = ease((t - clic) / 0.6)
        d.ellipse([cx - 260 * o, cy - 100 * o, cx + 260 * o, cy + 100 * o], outline=rgba(GOLD, 200 * (1 - o)), width=6)
    chips = ["Audio semanal", "Reto de límites", "Lección de dinero"]
    for j, c in enumerate(chips):
        q = back((t - clic - 0.4 - j * 0.5) / 0.5)
        if q > 0:
            x = W / 2 + (j - 1) * 520
            d.rounded_rectangle([x - 230 * q, 720 - 50 * q, x + 230 * q, 720 + 50 * q], 50, fill=rgba(WINE, 255), outline=rgba(GOLD, 200), width=3)
            centro(d, (x, 722), c, PLAY(int(40 * min(1, q)), 600), CREAM)
    q = ease((t - clic - 2.2) / 0.6)
    centro(d, (W / 2, 880), "Te sales cuando quieras", PLAY(42, 400), rgba(CREAM, 200 * q))
    return img


# ================================================================== prueba de amistades: dos columnas
def dos_columnas(t, dur, e):
    img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
    a = ease(t / 0.5)
    centro(d, (W / 2, 110), "LA PRUEBA", BEBAS(100), rgba(WINE, 255 * a))
    for k, (tit, items, x) in enumerate(((e["izq"], e["items_izq"], 520), (e["der"], e["items_der"], 1400))):
        p = ease((t - 0.3 - k * 0.4) / 0.6)
        d.rounded_rectangle([x - 380, 200 + (1 - p) * 60, x + 380, 840 + (1 - p) * 60], 30, fill=rgba(PAPER, 255 * p),
                            outline=rgba(GOLD if k == 0 else WINE, 200 * p), width=4)
        for j, fila in enumerate(envolver(d, tit.upper(), BEBAS(60), 680)):
            centro(d, (x, 290 + j * 60), fila, BEBAS(60), rgba(GOLD if k == 0 else WINE, 255 * p))
        # la columna izquierda se llena primero; la derecha cuando la voz pregunta «¿Quiénes llegaron?»
        base = 1.2 if k == 0 else dur * 0.45
        for j, it in enumerate(items):
            q = (t - base - j * 1.1) / 0.8
            if q > 0:
                n = int(len(it) * min(1, q))
                d.text((x - 300, 440 + j * 110), "•  " + it[:n], font=HAND(74, 700), fill=(32, 40, 92), anchor="lm")
    q = ease((t - dur * 0.8) / 0.8)
    if q > 0:
        centro(d, (W / 2, 885), "¿Quién aparece en las dos?", PLAY(46, 700), rgba(WINE, 255 * q))
    return img


# ================================================================== cita (idea de décadas)
def cita(t, dur, e):
    img, d = lienzo("vino", t)
    anillos(d, t)
    q = back(t / 0.6)
    d.text((300, 300 + (1 - min(1, q)) * 40), "“", font=PLAY(int(320 * max(0.1, q)), 700), fill=rgba(GOLD, 230), anchor="mm")
    f = PLAY(78, 700)
    filas = envolver(d, e["frase"], f, 1300)
    total = sum(len(r) for r in filas)
    shown = int(total * ease_io((t - 0.5) / max(1.5, min(3.0, dur * 0.4))))
    y = H / 2 - (len(filas) - 1) * 52 - 30
    for fila in filas:
        n = max(0, min(len(fila), shown)); shown -= len(fila)
        if n:
            d.text((W / 2, y), fila[:n], font=f, fill=CREAM, anchor="mm")
        y += 104
    a = ease((t - 3.2) / 0.7)
    d.text((W / 2, y + 40), e.get("autor", ""), font=PLAY(40, 400), fill=rgba(GOLD, 230 * a), anchor="mm")
    return img


# ================================================================== las cuatro palabras (misterio → revelación)
def cuatro_palabras(t, dur, e):
    revelar = e.get("revelar", False)
    img, d = lienzo("noche", t)
    anillos(d, t)
    palabras = ["YA", "NO", "LO", "ACEPTO"]
    ancho = [220, 220, 220, 420]
    x = W / 2 - (sum(ancho) + 3 * 40) / 2
    centro(d, (W / 2, 220), "LAS 4 PALABRAS" if not revelar else "DILO CON CALMA", BEBAS(96), rgba(GOLD, 255 * ease(t / 0.5)))
    for k, (pal, w_) in enumerate(zip(palabras, ancho)):
        st = 0.4 + k * 0.35
        p = back((t - st) / 0.5)
        if p <= 0:
            x += w_ + 40; continue
        cy = 540 + 8 * math.sin(t * 3 + k)
        flip = ease((t - 1.6 - k * 0.45) / 0.35) if revelar else 0.0
        alto = 220 * abs(1 - 2 * flip) if revelar else 220 * min(1, p)
        cara = flip >= 0.5
        sacude = 0 if revelar else 6 * math.sin(t * 18 + k) * (1 if int(t * 1.5 + k) % 3 == 0 else 0)
        d.rounded_rectangle([x + sacude, cy - alto / 2, x + w_ + sacude, cy + alto / 2], 26,
                            fill=rgba(GOLD if cara else (60, 40, 52), 255), outline=rgba(GOLD, 220), width=4)
        if alto > 60:
            if cara:
                d.text((x + w_ / 2, cy + 6), pal, font=BEBAS(150), fill=NIGHT, anchor="mm")
            else:
                d.text((x + w_ / 2 + sacude, cy + 6), "?", font=BEBAS(150), fill=rgba(GOLD, 255), anchor="mm")
        x += w_ + 40
    a = ease((t - 2.0) / 0.6)
    pie = "al final del video" if not revelar else "y después, haz lo que escribiste en tu tercera columna"
    centro(d, (W / 2, 820), pie, PLAY(50, 600), rgba(CREAM, 230 * a))
    return img


# ================================================================== las dos trampas
def trampas(t, dur, e):
    img, d = lienzo("noche", t)
    centro(d, (W / 2, 120), "DOS MENSAJES · DOS TRAMPAS", BEBAS(90), rgba(GOLD, 255 * ease(t / 0.5)))
    lados = [("TRAMPA 1", ["«No seas tan exigente»", "«Nadie es perfecto»", "«Te vas a quedar sola»", "«Agradece lo que tienes»"], 520, 0.4),
             ("TRAMPA 2", ["La cartera más cara", "Las uñas perfectas", "Las mejores fotos"], 1400, dur * 0.42)]
    for k, (tit, items, cx, st) in enumerate(lados):
        p = ease((t - st) / 0.5)
        if p <= 0:
            continue
        d.rounded_rectangle([cx - 400, 220 + (1 - p) * 50, cx + 400, 830 + (1 - p) * 50], 30, fill=rgba((44, 28, 38), 240),
                            outline=rgba(GOLD, 120), width=3)
        centro(d, (cx, 290), tit, BEBAS(70), rgba(GOLD, 255 * p))
        centro(d, (cx, 345), "conformarte con migajas" if k == 0 else "confundir valor con apariencia", PLAY(34, 400), rgba(CREAM, 200 * p))
        for j, it in enumerate(items):
            q = back((t - st - 0.5 - j * 0.6) / 0.45)
            if q > 0:
                y = 430 + j * 95
                d.rounded_rectangle([cx - 330, y - 36, cx + 330, y + 36], 36, fill=rgba(WINE if k == 0 else (90, 70, 84), 250))
                centro(d, (cx, y), it, PLAY(int(38 * min(1, q)), 600), CREAM)
    x = ease((t - dur * 0.82) / 0.4)                                # las dos tachadas con una X roja
    if x > 0:
        for cx in (520, 1400):
            d.line([(cx - 330 * x, 380 - 50 * x * 0), (cx - 330 + 660 * x, 380 + 420 * x)], fill=rgba((214, 60, 70), 230), width=16)
            d.line([(cx + 330, 380), (cx + 330 - 660 * x, 380 + 420 * x)], fill=rgba((214, 60, 70), 230), width=16)
    return img


# ================================================================== encuesta en los comentarios
def encuesta(t, dur, e):
    img, d = lienzo("vino", t)
    anillos(d, t, a=0.7)
    ops = e["opciones"]
    centro(d, (W / 2, 170), e["pregunta"], PLAY(60, 700), rgba(CREAM, 255 * ease(t / 0.5)))
    icono_comentario(d, W / 2, 300, 46 * back((t - 0.3) / 0.5) + 0.1, GOLD)
    n = len(ops)
    anchos = 1500 / n
    for k, op in enumerate(ops):
        p = back((t - 0.6 - k * 0.25) / 0.45)
        if p <= 0:
            continue
        cx = W / 2 - 750 + anchos * (k + 0.5)
        r = min(150, anchos * 0.42) * min(1.08, p)
        pulso = 1 + 0.05 * math.sin(t * 4 + k * 1.3)
        d.ellipse([cx - r * pulso, 560 - r * pulso, cx + r * pulso, 560 + r * pulso], fill=rgba(GOLD, 240), outline=rgba(WHITE, 200), width=4)
        centro(d, (cx, 568), op["n"], BEBAS(int(r * 1.1)), NIGHT)
        centro(d, (cx, 560 + r + 50), op["t"], PLAY(36, 600), rgba(CREAM, 230 * min(1, p)))
    a = ease((t - 1.8) / 0.6)
    centro(d, (W / 2, 860), e.get("pie", "Escribe tu número en los comentarios"), BEBAS(64), rgba(GOLD, 255 * a))
    return img


# ================================================================== el diamante en su estuche
def estuche(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = W / 2, 640
    abre = ease_io((t - 0.6) / 1.4)
    d.rounded_rectangle([cx - 380, cy - 40, cx + 380, cy + 200], 30, fill=(90, 20, 36))
    d.rounded_rectangle([cx - 340, cy - 20, cx + 340, cy + 60], 20, fill=(140, 40, 60))
    tapa_h = 260 * (1 - abre) + 60
    d.rounded_rectangle([cx - 380, cy - 40 - tapa_h, cx + 380, cy - 40 + 20], 30, fill=(110, 26, 44), outline=GOLD, width=4)
    if abre > 0.3:
        s_ = 130 * ease((abre - 0.3) / 0.7)
        d.ellipse([cx - 280, cy - 300, cx + 280, cy + 40], fill=rgba(GOLD, 30 * abre))
        diamante_dibujo(d, cx, cy - 130 - 10 * math.sin(t * 2), s_ + 1, t)
    centro(d, (W / 2, 140), "NADIE LE DICE AL DIAMANTE", BEBAS(84), rgba(CREAM, 255 * ease(t / 0.5)))
    centro(d, (W / 2, 230), "QUE ES EXIGENTE POR QUERER UN ESTUCHE", BEBAS(84), rgba(GOLD, 255 * ease((t - 0.5) / 0.5)))
    return img


ESCENAS = {"tipografia": tipografia, "fondo_frase": fondo_frase, "libreta": libreta, "test": test, "preguntas": preguntas,
           "puertas": puertas, "comentario": comentario, "comentarios": comentarios, "historia": historia, "diamante": diamante,
           "mivalor": mivalor, "membresia": membresia, "dos_columnas": dos_columnas, "cita": cita,
           "cuatro_palabras": cuatro_palabras, "trampas": trampas, "encuesta": encuesta, "estuche": estuche}


def dibujar(e, t, tab):
    if e["tipo"] == "tabla":
        return tabla(t, e["duracion"], e, tab)
    if e["tipo"] == "pausa":
        return pausa(t, e["duracion"], e, tab)
    return ESCENAS[e["tipo"]](t, e["duracion"], e)


def textos_en_pantalla(e, tab):
    """Lo que la escena ya muestra en grande (para esconder el subtítulo que dice lo mismo)."""
    partes = []
    if e["tipo"] == "cuatro_palabras" and e.get("revelar"):
        partes.append("ya no lo acepto")
    if e["tipo"] == "trampas":
        partes.append("no seas tan exigente nadie es perfecto te vas a quedar sola agradece lo que tienes")
    for k in ("frase", "texto", "titulo", "texto_izq", "texto_der", "pregunta"):
        if isinstance(e.get(k), str):
            partes.append(e[k].replace("*", ""))
    for ln in e.get("lineas", []) or []:
        partes.append(ln[0] if isinstance(ln, list) else ln)
    partes += e.get("preguntas", []) or []
    if e["tipo"] == "comentarios":
        partes += [c[1] for c in COMMENTS]
    return " ".join(partes)


# ================================================================== historias con personajes (estilo de El Profesor)
def _texto_lado(d, x, y, titulo, cuerpo, t, color_t, color_c, ancho=640):
    a = ease(t / 0.6)
    d.text((x, y), titulo, font=BEBAS(96), fill=rgba(color_t, 255 * a), anchor="lm")
    for k, fila in enumerate(envolver(d, cuerpo, PLAY(50, 700), ancho)):
        q = ease((t - 0.8 - k * 0.5) / 0.6)
        d.text((x + (1 - q) * 30, y + 100 + k * 68), fila, font=PLAY(50, 700), fill=rgba(color_c, 255 * q), anchor="lm")


def historia_personajes(t, dur, e):
    import personajes as Q
    esc = e["escena"]
    z = 1 + 0.04 * ease_io(t / max(1, dur))                          # zoom lento de cámara (3-5 %)
    if esc == "oficina":                                             # Natalia en la oficina, tarde
        img = Image.new("RGB", (W, H), (46, 36, 52)); d = ImageDraw.Draw(img, "RGBA")
        d.rectangle([0, 0, W, 700], fill=(58, 46, 64))
        d.rectangle([1180, 120, 1760, 560], fill=(30, 26, 48), outline=(90, 70, 84), width=12)       # ventana de noche
        d.ellipse([1600, 160, 1680, 240], fill=(240, 226, 196))
        rnd = random.Random(4)
        for k in range(8):
            bx = 1196 + k * 70; bh = rnd.randint(120, 300)
            d.rectangle([bx, 560 - bh, bx + 56, 560], fill=(44, 38, 62))
            for j in range(0, bh - 30, 34):
                if rnd.random() < 0.35:
                    d.rectangle([bx + 14, 560 - bh + 18 + j, bx + 26, 560 - bh + 30 + j], fill=rgba(GOLD, 200))
        cx, cy = 300, 230                                                                              # reloj: tarde
        d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=CREAM, outline=GOLD, width=8)
        for k in range(12):
            a_ = k * math.pi / 6
            d.line([(cx + 70 * math.cos(a_), cy + 70 * math.sin(a_)), (cx + 80 * math.cos(a_), cy + 80 * math.sin(a_))], fill=INK, width=4)
        ang = -math.pi / 2 + t * 0.8
        d.line([(cx, cy), (cx + 62 * math.cos(ang), cy + 62 * math.sin(ang))], fill=INK, width=5)
        d.line([(cx, cy), (cx + 40 * math.cos(math.pi * 0.42), cy + 40 * math.sin(math.pi * 0.42))], fill=INK, width=9)
        Q.NATALIA.pegar(img, 760, 520, 620, t, brazo=False, boca="neutra")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle([380, 700, 1500, 760], fill=(120, 80, 60)); d.rectangle([380, 760, 1500, 1080], fill=(96, 62, 46))
        d.rounded_rectangle([900, 470, 1140, 680], 12, fill=(30, 30, 40))                               # computador
        brillo = 0.75 + 0.25 * math.sin(t * 2)
        d.rounded_rectangle([914, 484, 1126, 650], 8, fill=rgba((120, 170, 220), 200 * brillo))
        for k in range(4):
            d.rectangle([934, 504 + k * 34, 934 + 140 - (k % 2) * 50, 516 + k * 34], fill=(240, 240, 250, 180))
        d.rectangle([1000, 680, 1040, 704], fill=(30, 30, 40))
        n = min(8, int(t * 1.2))
        for k in range(n):                                                                              # papeles que se apilan
            d.rectangle([520 + (k % 2) * 8, 690 - k * 9, 680 + (k % 2) * 8, 700 - k * 9], fill=(240, 232, 216), outline=(200, 190, 175))
        _texto_lado(d, 1200, 660, "NATALIA", "", t, GOLD, CREAM)
        for k, fila in enumerate(["se quedaba hasta tarde", "cubría a todos", "nunca pedía aumento"]):
            q = ease((t - 1.0 - k * 1.8) / 0.5)
            if q > 0:
                d.regular_polygon((1215, 760 + k * 62, 9), 4, rotation=45, fill=rgba(GOLD, 255 * q))
                d.text((1240, 760 + k * 62), fila, font=PLAY(44, 600), fill=rgba(CREAM, 255 * q), anchor="lm")
    elif esc == "natalia_escribe":                                   # Natalia escribiendo su tabla
        img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
        Q.NATALIA.pegar(img, 520, 470, 640, t, brazo=True, boca="neutra")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle([0, 760, W, H], fill=(214, 196, 170))
        d.polygon([(330, 790), (900, 770), (930, 1000), (300, 1030)], fill=PAPER, outline=(200, 186, 160))
        mx = 560 + 120 * math.sin(t * 2.4); my = 860 + 30 * math.sin(t * 5)
        lapiz(d, mx, my, t)
        frase = e.get("frase", "")
        f = HAND(84, 700)
        filas = envolver(d, frase, f, 760)
        total = sum(len(r) for r in filas)
        shown = int(total * ease_io((t - 0.5) / max(2.0, dur * 0.6)))
        y = 330
        d.text((1020, 220), "LO QUE ESCRIBIÓ NATALIA", font=BEBAS(70), fill=WINE, anchor="lm")
        for fila in filas:
            k = max(0, min(len(fila), shown)); shown -= len(fila)
            if k:
                d.text((1020, y), fila[:k], font=f, fill=(32, 40, 92), anchor="lm")
            y += 104
    elif esc == "soltar":                                             # la espectadora suelta lo que pesa
        img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
        d.rectangle([0, 900, W, H], fill=(226, 210, 186))
        Q.ESPECTADORA.pegar(img, 560, 560, 680, t, boca="sonrisa" if t > 6 else "neutra")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle([380, 900, 740, 1080], fill=(110, 28, 46))                                          # falda/cuerpo bajo el busto
        ex, ey = 840, 640
        for k in range(4):
            suelta = (t - 1.8 - k * 1.5)
            gx = ex + 40 + k * 110
            if suelta < 0:
                gy = ey + 160 + (k % 2) * 40
                d.line([(ex - 40, ey), (gx, gy - 40)], fill=rgba(INK, 180), width=3)
            else:
                gy = ey + 160 + (k % 2) * 40 + 600 * suelta ** 2
                for j in range(6):
                    ang = j * math.pi / 3 + suelta * 3
                    rr = 40 + 160 * ease(suelta / 1.2)
                    sx, sy = gx + math.cos(ang) * rr * 0.5, ey + 120 + math.sin(ang) * rr * 0.5
                    d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=rgba(GOLD, 255 * (1 - ease(suelta / 1.2))))
            if gy < H + 80:
                d.rounded_rectangle([gx - 40, gy - 38, gx + 40, gy + 38], 12, fill=(70, 60, 66))
        _texto_lado(d, 1260, 360, "UNA ESPECTADORA", e.get("texto", ""), t, WINE, INK, 560)
    else:
        return historia(t, dur, e)
    if z > 1.001:
        w, h = W / z, H / z
        img = img.resize((W, H), Image.Resampling.BILINEAR, box=((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2))
    return img


ESCENAS["historia"] = historia_personajes


# ================================================================== pantalla final (últimos 20 s)
FINAL_VIDEO = (1010, 140, 1770, 568)            # hueco del elemento «video» (16:9)
FINAL_SUSCRIBIR = (1180, 760, 110)              # círculo de «suscribirse» (centro x, centro y, radio)
FINAL_BOTON = (1560, 760)


def _punteado(d, caja, color, paso=22, largo=12, ancho=4):
    x0, y0, x1, y1 = caja
    for x in range(int(x0), int(x1), paso):
        d.line([(x, y0), (min(x + largo, x1), y0)], fill=color, width=ancho)
        d.line([(x, y1), (min(x + largo, x1), y1)], fill=color, width=ancho)
    for y in range(int(y0), int(y1), paso):
        d.line([(x0, y), (x0, min(y + largo, y1))], fill=color, width=ancho)
        d.line([(x1, y), (x1, min(y + largo, y1))], fill=color, width=ancho)


def pantalla_final(t, dur, e):
    img = vignette_bg((110, 28, 46), NIGHT, cx=0.3, cy=0.5) if False else fondo("noche").copy()
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([-300, 0, 1100, 1080], fill=rgba(WINE, 50))
    particulas(d, t, 26, GOLD, 0.7)
    a = ease(t / 0.8)
    _punteado(d, FINAL_VIDEO, rgba(CREAM, 90 * a))
    cx, cy, r = FINAL_SUSCRIBIR
    for k in range(0, 360, 14):
        d.arc([cx - r, cy - r, cx + r, cy + r], k, k + 7, fill=rgba(CREAM, 90 * a), width=4)
    bx, by = FINAL_BOTON
    p = back((t - 1.0) / 0.6)
    if p > 0:
        pulso = 1 + 0.035 * math.sin(t * 4)
        w_, h_ = 520 * min(1.05, p) * pulso, 110 * min(1.05, p) * pulso
        d.rounded_rectangle([bx - w_ / 2 + 6, by - h_ / 2 + 8, bx + w_ / 2 + 6, by + h_ / 2 + 8], h_ / 2, fill=(0, 0, 0, 120))
        d.rounded_rectangle([bx - w_ / 2, by - h_ / 2, bx + w_ / 2, by + h_ / 2], h_ / 2, fill=GOLD)
        d.text((bx, by - 12), "UNIRME", font=BEBAS(int(60 * min(1, p))), fill=NIGHT, anchor="mm")
        d.text((bx, by + 30), "El círculo de las dueñas", font=PLAY(int(26 * min(1, p)), 600), fill=NIGHT, anchor="mm")
    if e.get("frase") and t > e.get("frase_desde", dur - 6):        # la frase final, mientras El Profesor la dice
        q = ease((t - e.get("frase_desde", dur - 6)) / 0.6)
        filas = envolver(d, e["frase"].upper(), BEBAS(72), 1800)
        for k, fila in enumerate(filas):
            d.text((W / 2, 56 + k * 70), fila, font=BEBAS(72), fill=rgba(GOLD, 255 * q), anchor="mm")
    return img


ESCENAS["pantalla_final"] = pantalla_final
