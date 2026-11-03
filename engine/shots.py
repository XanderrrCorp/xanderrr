"""Plantillas de escena para La Libreta de Inés.

Cada plantilla: fn(img, pen, t, dur, p) -> lista de tiempos de impacto (segundos)
p = diccionario de parámetros de la escena (ver references/plan.md).
Los impactos disparan sacudida de cámara + sonido "pop".
"""
import math
from PIL import Image, ImageDraw, ImageFont
import ink
from ink import (W, H, SS, Pen, ines, htext, pop_htext, bg_white, bg_sala, bg_cocina, gloria,
                 back, ease, clamp, INK, PLUM, WHITE, RED, GREEN, PURPLE, SKIN, HF)

TERRA = (204, 98, 58); SAGE = (118, 170, 140); MUST = (240, 190, 70); CREAM = (252, 246, 232)
GREY = (140, 140, 140)
COLORS = {"rojo": RED, "verde": GREEN, "morado": PURPLE, "terra": TERRA, "negro": INK, "gris": GREY}
def col(name, default=INK):
    if isinstance(name, str): return COLORS.get(name, default)
    return tuple(name) if name else default

def LG(size): return ImageFont.truetype(ink.os.path.join(ink.HERE, "fonts", "LuckiestGuy-Regular.ttf"), int(size * SS))

def wrap(text, size, maxw, font=HF):
    f = font(size); words = text.split(); lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.getlength(test) / SS <= maxw or not cur: cur = test
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def block(d, x, y, text, size, fill=INK, maxw=700, font=HF, lh=1.15, anchor="mm"):
    lines = wrap(text, size, maxw, font)
    y0 = y - (len(lines) - 1) * size * lh / 2
    for i, l in enumerate(lines):
        d.text((x * SS, (y0 + i * size * lh) * SS), l, font=font(size), fill=fill, anchor=anchor)
    return len(lines)

def pop_lucky(img, xy, s, size, fill, k, rot=0, outline=True, maxw=None):
    if k <= 0.02: return
    if maxw:
        wl = LG(size).getlength(s) / SS
        if wl > maxw: size = size * maxw / wl
    f = LG(size * k); tw = int(f.getlength(s)) + 120
    tmp = Image.new("RGBA", (tw, int(size * k * 2.0 * SS)), (0, 0, 0, 0))
    dd = ImageDraw.Draw(tmp)
    if outline: dd.text((tw // 2, tmp.height // 2), s, font=f, fill=WHITE, anchor="mm", stroke_width=int(10 * SS * k), stroke_fill=WHITE)
    dd.text((tw // 2, tmp.height // 2), s, font=f, fill=fill, anchor="mm")
    if rot: tmp = tmp.rotate(rot, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tmp, (int(xy[0] * SS) - tmp.width // 2, int(xy[1] * SS) - tmp.height // 2))

def background(pen, name):
    {"sala": bg_sala, "cocina": bg_cocina}.get(name, bg_white)(pen)

def card(pen, x0, y0, x1, y1, fill=CREAM, k=1.0):
    if k <= 0.02: return
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = 0.6 + 0.4 * k
    pen.rect(cx - (cx - x0) * s, cy - (cy - y0) * s, cx + (x1 - cx) * s, cy + (y1 - cy) * s, fill, 5, r=28)

def red_x(pen, x, y, r, k):
    if k <= 0: return
    a = clamp(k * 2); b = clamp(k * 2 - 1)
    pen.line([(x - r, y - r), (x - r + 2 * r * a, y - r + 2 * r * a)], 12, RED)
    if b > 0: pen.line([(x + r, y - r), (x + r - 2 * r * b, y - r + 2 * r * b)], 12, RED)

def inez(pen, t, p, x=None, default_pose="down", default_expr="meh", sc=0.95):
    pose = p.get("pose", default_pose); expr = p.get("cara", default_expr)
    side = p.get("ines", "izq")
    if x is None: x = {"izq": 520, "centro": 960, "der": 1400}.get(side, 520)
    ines(pen, x, 285, sc, t, pose, expr, talk=p.get("habla", True))

# ---------------- plantillas ----------------
def t_habla(img, pen, t, dur, p):
    """Inés hablando. Opcional: 'palabra' que aparece grande al lado."""
    background(pen, p.get("fondo", "blanco"))
    side = p.get("ines", "centro" if not p.get("palabra") else "izq")
    p = dict(p, ines=side); inez(pen, t, p)
    hits = []
    if p.get("palabra"):
        at = p.get("en", 0.25) * dur
        x = 1350 if side == "izq" else 570
        pop_lucky(img, (x, 430), p["palabra"], p.get("tam", 120), col(p.get("color"), INK), back((t - at) / 0.3), rot=p.get("giro", -3), maxw=780)
        hits.append(at)
        if p.get("sub"):
            at2 = at + 0.5
            if t > at2: block(pen.d, x, 600, p["sub"], 52, INK, 760)
    return hits

def t_numero(img, pen, t, dur, p):
    """Entrada de un punto de la lista: número gigante + título."""
    bg_white(pen)
    ines(pen, 1450, 285, 0.95, t, p.get("pose", "hip"), p.get("cara", "meh"), talk=True)
    k = back((t - 0.15) / 0.3)
    if k > 0.05: pen.ell(560, 400, 230 * k, 230 * k, MUST, 6)
    pop_lucky(img, (560, 410), str(p.get("n", 1)), 300, TERRA, k, outline=False)
    if t > 0.6:
        kk = ease((t - 0.6) / 0.3)
        block(pen.d, 560, 760 + 20 * (1 - kk), p.get("titulo", ""), 66, INK, 820)
    return [0.15]

def t_dinero(img, pen, t, dur, p):
    """Cifra grande (con conteo opcional) y etiqueta. Inés reacciona."""
    bg_white(pen)
    ines(pen, 430, 470, 2.0, t, p.get("pose", "down"), p.get("cara", "wide"), talk=True)
    at = p.get("en", 0.2) * dur
    c = col(p.get("color", "rojo"), RED)
    txt = p.get("cifra", "730")
    if p.get("desde") is not None and t >= at:
        a, b = float(p["desde"]), float(p["hasta"]); kk = ease((t - at) / max(0.6, dur * 0.35))
        v = a + (b - a) * kk
        txt = (p.get("pre", "") + f"{v:,.0f}".replace(",", ".") + p.get("post", ""))
    pop_lucky(img, (1300, 400), txt, p.get("tam", 170), c, back((t - at) / 0.3), rot=-2, maxw=900)
    if p.get("etiqueta") and t > at + 0.5:
        block(pen.d, 1300, 590, p["etiqueta"], 64, INK, 880)
    if p.get("nota"): htext(pen.d, (1880, 1040), p["nota"], 28, GREY, "rs")
    return [at]

def t_tachar(img, pen, t, dur, p):
    """Lista de cosas que aparecen y se tachan con X roja, una por una."""
    bg_white(pen)
    items = p.get("items", [])[:4]
    ines(pen, 1500, 285, 0.95, t, p.get("pose", "point"), p.get("cara", "meh"), talk=True)
    if p.get("titulo"): pop_lucky(img, (620, 110), p["titulo"], 80, INK, back((t - 0.05) / 0.3))
    n = max(1, len(items)); hits = []
    slot = (dur - 0.4) / n
    for i, it in enumerate(items):
        ta = 0.3 + i * slot; y = 250 + i * 190
        if t > ta:
            kk = back((t - ta) / 0.3)
            card(pen, 140, y - 70, 1100, y + 70, CREAM, kk)
            if kk > 0.6: block(pen.d, 620, y, it, 56, INK, 880)
            tx = ta + slot * 0.55
            if p.get("tachar", True) and t > tx:
                red_x(pen, 620, y, 75, (t - tx) / 0.25); hits.append(tx)
    return hits

def t_telefono(img, pen, t, dur, p):
    """Celular con una app y cobros que van apareciendo. 'marca' = índice a resaltar."""
    d = pen.d
    d.rectangle([0, 0, W * SS, H * SS], fill=SAGE)
    ines(pen, 1500, 285, 0.95, t, "phone", p.get("cara", "meh"), talk=True)
    pen.rect(330, 40, 930, 1040, (40, 40, 46), r=60)
    pen.rect(355, 70, 905, 1015, (250, 250, 250), 3, r=40)
    pen.rect(355, 70, 905, 190, (110, 70, 200), 0, r=40); d.rectangle([355 * SS, 150 * SS, 905 * SS, 190 * SS], fill=(110, 70, 200))
    htext(d, (400, 130), p.get("app", "Mi Banco"), 50, WHITE, "lm")
    rows = p.get("cobros", [])[:6]; hits = []
    slot = (dur - 0.5) / max(1, len(rows))
    for i, (name, amt) in enumerate(rows):
        ta = 0.3 + i * slot; y = 260 + i * 120
        if t > ta:
            kk = ease((t - ta) / 0.25)
            yy = y + 20 * (1 - kk)
            hl = p.get("marca") == i
            if hl and t > ta + 0.3:
                pen.rect(375, yy - 50, 885, yy + 50, (255, 225, 225), 4, r=18); hits.append(ta + 0.3)
            htext(d, (400, yy), name, 38, INK, "lm")
            htext(d, (860, yy), amt, 40, RED if hl else INK, "rm")
            pen.line([(390, yy + 55), (870, yy + 55)], 2, (220, 220, 220))
    if p.get("total") and t > dur * 0.75:
        pop_lucky(img, (630, 960), p["total"], 70, RED, back((t - dur * 0.75) / 0.3), outline=False)
        hits.append(dur * 0.75)
    return hits

def t_comparar(img, pen, t, dur, p):
    """Dos tarjetas lado a lado: izquierda (mal) vs derecha (bien)."""
    bg_white(pen)
    L, R = p.get("izq", ["", ""]), p.get("der", ["", ""])
    k1 = back((t - 0.2) / 0.3); k2 = back((t - dur * 0.45) / 0.3)
    card(pen, 120, 170, 900, 820, (255, 232, 228), k1)
    if k1 > 0.6:
        pop_lucky(img, (510, 280), L[0], 64, RED, 1, outline=False, maxw=680); block(pen.d, 510, 560, L[1], 60, INK, 680)
    card(pen, 1020, 170, 1800, 820, (226, 240, 228), k2)
    if k2 > 0.6:
        pop_lucky(img, (1410, 280), R[0], 64, GREEN, 1, outline=False, maxw=680); block(pen.d, 1410, 560, R[1], 60, INK, 680)
    pop_lucky(img, (960, 500), "VS", 64, INK, back((t - dur * 0.4) / 0.25))
    return [0.2, dur * 0.45]

def t_cuenta(img, pen, t, dur, p):
    """Operación que se arma por partes: ['2', '× 365', '= 730']."""
    bg_white(pen)
    parts = p.get("partes", ["2", "× 365", "= 730"]); hits = []
    f = LG(130); widths = [f.getlength(s) / SS + 60 for s in parts]
    x = 960 - sum(widths) / 2
    slot = (dur * 0.7) / len(parts)
    for i, s in enumerate(parts):
        ta = 0.2 + i * slot
        c = col(p.get("color", "rojo"), RED) if i == len(parts) - 1 else INK
        pop_lucky(img, (x + widths[i] / 2, 440), s, 130, c, back((t - ta) / 0.3), outline=False)
        if t >= ta: hits.append(ta)
        x += widths[i]
    if p.get("etiqueta") and t > dur * 0.75: block(pen.d, 960, 680, p["etiqueta"], 62, INK, 1300)
    if p.get("nota"): htext(pen.d, (1880, 1040), p["nota"], 28, GREY, "rs")
    return hits

def t_libreta(img, pen, t, dur, p):
    """Mención del producto: Inés presenta la libreta."""
    bg_white(pen)
    ines(pen, 560, 285, 0.95, t, "present", "happy" if t > dur * 0.6 else "meh", talk=True)
    k = back((t - 0.25) / 0.35)
    if k > 0.02:
        s = 0.5 + 0.5 * k; cx, cy = 1350, 500
        pen.rect(cx - 300 * s, cy - 380 * s, cx + 300 * s, cy + 380 * s, (112, 140, 80), 6, r=24)
        pen.rect(cx - 265 * s, cy - 345 * s, cx + 265 * s, cy + 345 * s, CREAM, 4, r=16)
        if k > 0.7:
            pop_lucky(img, (cx, cy - 190), "LA LIBRETA", 64, TERRA, 1, outline=False)
            pop_lucky(img, (cx, cy - 110), "DE INÉS", 64, TERRA, 1, outline=False)
            block(pen.d, cx, cy + 60, p.get("frase", "Plan de 30 días para tapar las fugas de tu dinero"), 46, INK, 460)
    if p.get("donde") and t > dur * 0.5:
        pop_lucky(img, (1350, 1000), p["donde"], 46, INK, back((t - dur * 0.5) / 0.3))
    return [0.25]

def t_suscribete(img, pen, t, dur, p):
    """Llamado a suscribirse con remate (sarcástico o de identidad)."""
    bg_white(pen)
    ines(pen, 560, 285, 0.95, t, "point", p.get("cara", "meh"), talk=True)
    k = back((t - 0.2) / 0.3); hits = [0.2]
    if k > 0.02:
        pen.rect(1000, 360 - 30 * k, 1800, 520 + 30 * k, RED, 5, r=80)
        if k > 0.6: htext(pen.d, (1400, 440), "Suscríbete", 110 * min(1, k), WHITE)
    clicked = t > dur * 0.55
    if clicked:
        pen.rect(1000, 360, 1800, 550, (120, 120, 120), 5, r=80); htext(pen.d, (1400, 455), "Suscrita", 110, WHITE)
        hits.append(dur * 0.55)
    if p.get("remate") and t > dur * 0.35:
        block(pen.d, 1400, 720, p["remate"], 56, INK, 900)
    return hits

def t_pregunta(img, pen, t, dur, p):
    """Llamado a comentar: burbuja con la frase o pregunta que deben escribir."""
    bg_white(pen)
    ines(pen, 1460, 285, 0.95, t, p.get("pose", "present"), p.get("cara", "happy"), talk=True)
    k = back((t - 0.2) / 0.35)
    if k > 0.02:
        s = 0.6 + 0.4 * k
        pen.rect(960 - 760 * s, 520 - 300 * s, 960 + 200 * s, 520 + 300 * s, WHITE, 6, r=40)
        pen.poly([(1110, 650), (1240, 700), (1110, 760)], WHITE, 6)
        if k > 0.7:
            htext(pen.d, (580, 300), "Escríbelo en los comentarios:", 46, GREY)
            block(pen.d, 580, 540, p.get("frase", ""), 74, INK, 700, font=HF)
    return [0.2]

def t_titulo(img, pen, t, dur, p):
    """Cartel grande a pantalla (gancho, bloque o remate)."""
    background(pen, p.get("fondo", "blanco"))
    lines = p.get("lineas", ["TÍTULO"]); hits = []
    for i, l in enumerate(lines):
        ta = 0.1 + i * 0.35
        c = col(p.get("colores", [])[i] if i < len(p.get("colores", [])) else "negro", INK)
        pop_lucky(img, (960, 540 + (i - (len(lines) - 1) / 2) * 170), l, p.get("tam", 150), c, back((t - ta) / 0.3), rot=(-3 if i % 2 else 2), maxw=1700)
        if t >= ta: hits.append(ta)
    return hits

def t_gloria(img, pen, t, dur, p):
    """Escena de cocina con Gloria (la nevera vieja) — momento de humor."""
    bg_cocina(pen)
    ines(pen, 560, 285, 0.95, t, p.get("pose", "hip"), p.get("cara", "meh"), talk=True)
    sh = 1.0 if p.get("tiembla", True) and 0.4 < t < dur * 0.6 else 0
    gloria(pen, 1380, 560, sh, t)
    if p.get("cartel"):
        pop_lucky(img, (1380, 100), p["cartel"], 90, col(p.get("color", "rojo"), RED), back((t - 0.4) / 0.25), rot=math.sin(t * 40) * 3 * sh, maxw=900)
    return [0.4]

TEMPLATES = {"habla": t_habla, "numero": t_numero, "dinero": t_dinero, "tachar": t_tachar, "telefono": t_telefono,
             "comparar": t_comparar, "cuenta": t_cuenta, "libreta": t_libreta, "suscribete": t_suscribete,
             "pregunta": t_pregunta, "titulo": t_titulo, "gloria": t_gloria}
