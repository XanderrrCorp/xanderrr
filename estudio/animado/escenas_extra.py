"""Escenas nuevas (reutilizables) para listas tipo «N cosas que…»: número de cada punto, burbujas de frases, edades,
dos mujeres frente al espejo, la mesa familiar, el sobre del dinero, el orden de pago, el planner MI CÓDIGO, un dato que
cuenta, tres ventajas, la medalla del cansancio, la mochila de piedras y el resumen final. Se registran en escenas.ESCENAS."""
import math

from PIL import Image, ImageDraw

import escenas as E
from escenas import (BEBAS, CREAM, GOLD, GREY, HAND, INK, NIGHT, PAPER, PLAY, W, WHITE, WINE, H, anillos, back, centro,
                     ease, ease_io, envolver, fondo, lerp, lienzo, rgba)
import personajes as Q

ROJO = (214, 60, 70)
MUJER52 = Q.Personaje(piel="#E2A982", pelo="#8A7F7A", peinado="corto", ropa="#6E1C2E", ropa2="#6E1C2E", edad=52)
MUJER52B = Q.Personaje(piel="#E2A982", pelo="#8A7F7A", peinado="corto", ropa="#9A9096", ropa2="#9A9096", aretes=False, edad=52)
ROSA = Q.Personaje(piel="#D99C76", pelo="#3B2A24", peinado="mono", ropa="#D6AC5C", ropa2="#D6AC5C", edad=47)
HERMANA = Q.Personaje(piel="#D99C76", pelo="#2A2024", peinado="suelto", ropa="#2C3B57", ropa2="#2C3B57", edad=44)
MAMA = Q.Personaje(piel="#E2A982", pelo="#C9C4C0", peinado="mono", ropa="#7A5A6A", ropa2="#7A5A6A", edad=70)
ESPOSO = Q.Personaje(piel="#C98E6A", pelo="#3A3030", peinado="corto", ropa="#3E5A4A", ropa2="#3E5A4A", aretes=False, edad=50)


# ------------------------------------------------------------------ número de cada punto («LA PRIMERA COSA»)
ORDINAL = {1: "PRIMERA", 2: "SEGUNDA", 3: "TERCERA", 4: "CUARTA", 5: "QUINTA", 6: "SEXTA", 7: "SÉPTIMA", 8: "OCTAVA"}


def numero(t, dur, e):
    img, d = lienzo(e.get("fondo", "vino"), t)
    lado = bool(e.get("lado"))
    CX = 1300 if lado else W / 2
    anillos(d, t, cx=CX)
    n = e["n_punto"]
    p = back(t / 0.5)
    r = 120 * min(1.1, p)
    cy = 290
    d.ellipse([CX - r, cy - r, CX + r, cy + r], fill=rgba(GOLD, 255), outline=rgba(WHITE, 200), width=5)
    centro(d, (CX, cy + 10), str(n), BEBAS(int(190 * min(1, p))), NIGHT)
    a = ease((t - 0.4) / 0.4)
    centro(d, (CX, 470), f"LA {ORDINAL.get(n, str(n))} {e.get('etiqueta', 'COSA')}", BEBAS(56), rgba(GOLD, 255 * a))
    y = 590
    for k, linea in enumerate(e["titulo"]):
        q = back((t - 0.7 - k * 0.3) / 0.5)
        if q > 0:
            tam = 120
            while d.textlength(linea, font=BEBAS(tam)) > (900 if lado else 1500):
                tam -= 6
            centro(d, (CX + (1 - min(1, q)) * 80, y), linea, BEBAS(int(tam * lerp(1.2, 1, min(1, q)))), rgba(CREAM if k == 0 else GOLD, 255 * min(1, q)))
        y += 120
    return img


# ------------------------------------------------------------------ burbujas de frases (con «tachar» opcional)
def burbujas(t, dur, e):
    img, d = lienzo(e.get("fondo", "noche"), t)
    centro(d, (W / 2 - 150, 160), e.get("titulo", ""), BEBAS(90), rgba(GOLD, 255 * ease(t / 0.5)))
    frases = e["frases"]
    paso = max(1.0, min(2.2, (dur * 0.7) / len(frases)))
    pos = [(560, 330), (1360, 430), (560, 560), (1360, 690), (560, 820)]
    for k, fr in enumerate(frases):
        st = 0.5 + k * paso
        q = back((t - st) / 0.45)
        if q <= 0:
            continue
        x, y = pos[k % len(pos)]
        f = PLAY(int(44 * min(1, q)) + 1, 600)
        w = d.textlength(fr, font=PLAY(44, 600)) + 80
        izq = k % 2 == 0
        d.rounded_rectangle([x - w / 2, y - 50, x + w / 2, y + 50], 46, fill=rgba(CREAM, 245))
        cola = [(x - w / 2 + 60, y + 40), (x - w / 2 + 30, y + 80), (x - w / 2 + 100, y + 44)] if izq else \
               [(x + w / 2 - 60, y + 40), (x + w / 2 - 30, y + 80), (x + w / 2 - 100, y + 44)]
        d.polygon(cola, fill=rgba(CREAM, 245))
        d.text((x, y + 2), fr, font=f, fill=INK, anchor="mm")
        if e.get("tachar") is not None and t > e["tachar"] * dur:
            z = ease((t - e["tachar"] * dur - k * 0.15) / 0.3)
            if z > 0:
                d.line([(x - w / 2 + 20, y), (x - w / 2 + 20 + (w - 40) * z, y)], fill=rgba(ROJO, 240), width=10)
    return img


# ------------------------------------------------------------------ edades: 25, 30, 40+
def edades(t, dur, e):
    img, d = lienzo("noche", t)
    y = 560
    d.line([(200, y), (200 + 1520 * ease(t / 1.2), y)], fill=rgba(CREAM, 160), width=6)
    marcas = [(25, "un año esperando que alguien cambie"), (30, "otro año esperando el momento perfecto"), (40, "cada año esperando cuesta el doble")]
    for k, (edad, txt) in enumerate(marcas):
        st = 0.6 + k * dur * 0.28
        q = back((t - st) / 0.5)
        if q <= 0:
            continue
        x = 380 + k * 580
        r = 90 * min(1.1, q) * (1.25 if k == 2 else 1)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(GOLD if k == 2 else WINE, 255), outline=rgba(WHITE, 160), width=4)
        centro(d, (x, y + 6), f"{edad}{'+' if k == 2 else ''}", BEBAS(int(110 * min(1, q))), NIGHT if k == 2 else CREAM)
        for j, fila in enumerate(envolver(d, txt, PLAY(38, 600), 460)):
            centro(d, (x, y + 150 + j * 48), fila, PLAY(38, 600), rgba(CREAM, 230 * min(1, q)))
    # reloj de arena que gira
    cx, cy = W / 2, 230
    ang = (t * 40) % 360
    arena = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    g = ImageDraw.Draw(arena)
    g.polygon([(40, 20), (180, 20), (110, 110), (180, 200), (40, 200), (110, 110)], outline=GOLD, width=6)
    nivel = (t / max(1, dur))
    g.polygon([(70 + 40 * nivel, 40 + 70 * nivel), (150 - 40 * nivel, 40 + 70 * nivel), (110, 108)], fill=GOLD)
    g.polygon([(110, 112), (60, 190), (160, 190)], fill=rgba(GOLD, 120 + 135 * nivel))
    arena = arena.rotate(10 * math.sin(t * 2) if int(t) % 6 else ang, resample=Image.Resampling.BICUBIC)
    img.paste(arena, (int(cx - 110), int(cy - 110)), arena)
    return img


# ------------------------------------------------------------------ dos mujeres frente al espejo
def espejo(d, x, y, w, h):
    d.rounded_rectangle([x - w / 2 - 14, y - h / 2 - 14, x + w / 2 + 14, y + h / 2 + 14], 160, fill=rgba(GOLD, 255))
    d.rounded_rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], 150, fill=rgba((200, 210, 220), 255))


def dos_mujeres(t, dur, e):
    img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 900, W, H], fill=(226, 210, 186))
    fase = e.get("fase", "ambas")
    espejo(d, 540, 520, 560, 700); espejo(d, 1380, 520, 560, 700)
    # izquierda: encogida, mira de lado; derecha: derecha, de frente
    enc = ease_io(t / 2.0)
    MUJER52B.pegar(img, 560, 640 + 30 * enc, int(900 - 80 * enc), t, boca="neutra")
    if fase in ("ambas", "segunda"):
        a = ease((t - 0.3) / 0.6)
        if a > 0:
            brillo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(brillo).ellipse([1130, 220, 1630, 820], fill=rgba(GOLD, 70 * a))
            img = img.convert("RGBA"); img.alpha_composite(brillo); img = img.convert("RGB")
            MUJER52.pegar(img, 1380, 600, 920, t, boca="sonrisa")
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([380, 200, 700, 270], 35, fill=rgba(GREY, 230 * ease(t / 0.6)))
    centro(d, (540, 236), "ESPERA PERMISO", BEBAS(52), rgba(WHITE, 255 * ease(t / 0.6)))
    if fase in ("ambas", "segunda"):
        a = ease((t - 0.3) / 0.6)
        d.rounded_rectangle([1220, 200, 1540, 270], 35, fill=rgba(WINE, 240 * a))
        centro(d, (1380, 236), "YA SE LO DIO", BEBAS(52), rgba(WHITE, 255 * a))
    centro(d, (W / 2, 70), "52 AÑOS · EL MISMO ESPEJO", BEBAS(64), rgba(INK, 255 * ease(t / 0.6)))
    return img


# ------------------------------------------------------------------ la mesa del domingo (Rosa)
def mesa_familia(t, dur, e):
    img = Image.new("RGB", (W, H), (234, 220, 198)); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 300], fill=(222, 204, 178))
    gente = [(HERMANA, 380, "¿A tu edad?"), (MAMA, 1540, "¿Y quién va a cuidar a los nietos?"), (ESPOSO, 1180, "Si a ti nunca te gustaron los números.")]
    for p, x, _ in gente:
        p.pegar(img, x, 640, 640, t + x, boca="neutra")
    ROSA.pegar(img, 780, 610, 720, t, hablando=t < 3.0, boca="sonrisa" if t > dur * 0.85 else "neutra")
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 760, W, 820], fill=(150, 96, 70)); d.rectangle([0, 820, W, H], fill=(120, 76, 56))
    for x in (380, 780, 1180, 1540):
        d.ellipse([x - 90, 740, x + 90, 790], fill=(250, 248, 244), outline=(200, 190, 180), width=3)
    q = ease((t - 0.4) / 0.5)
    if q > 0 and t < 3.4:
        d.rounded_rectangle([420, 130, 1240, 250], 46, fill=rgba(GOLD, 240 * q))
        centro(d, (830, 190), "«Me voy a inscribir en un curso»", PLAY(48, 700), rgba(NIGHT, 255 * q))
    for k, (p, x, frase) in enumerate(gente):
        st = 3.4 + k * 1.8
        q = back((t - st) / 0.4)
        if q > 0:
            f = PLAY(44, 700)
            w = d.textlength(frase, font=f) + 70
            bx = min(max(x, w / 2 + 20), W - w / 2 - 20)
            by = 130 + k * 115
            d.rounded_rectangle([bx - w / 2, by, bx + w / 2, by + 100], 46, fill=rgba(WHITE, 250 * min(1, q)), outline=rgba(WINE, 200), width=4)
            d.text((bx, by + 50), frase, font=f, fill=INK, anchor="mm")
    centro(d, (W / 2, 60), "DOMINGO · ALMUERZO FAMILIAR", BEBAS(56), rgba(WINE, 255 * ease(t / 0.6)))
    return img


# ------------------------------------------------------------------ el sobre con tu nombre
def sobre(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = W / 2 + 250, 600
    p = back(t / 0.6)
    w, h = 620 * min(1, p), 380 * min(1, p)
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=(236, 222, 196))
    d.polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx, cy + 20)], fill=(222, 204, 172))
    nombre = e.get("nombre", "MI NOMBRE")
    n = int(len(nombre) * ease_io((t - 0.8) / 1.2))
    d.text((cx, cy + 110), nombre[:n], font=HAND(80, 700), fill=(32, 40, 92), anchor="mm")
    for k in range(6):                                                      # monedas que caen al sobre
        st = 1.8 + k * 0.7
        q = (t - st) / 0.8
        if 0 < q < 1:
            y = lerp(-80, cy - 40, ease_io(q))
            x = cx + (k % 3 - 1) * 90
            d.ellipse([x - 40, y - 40, x + 40, y + 40], fill=GOLD, outline=(160, 120, 50), width=5)
            centro(d, (x, y + 4), "$", BEBAS(56), (120, 86, 30))
    a = ease((t - 0.4) / 0.6)
    d.text((240, 420), "PÁGATE", font=BEBAS(150), fill=rgba(CREAM, 255 * a), anchor="lm")
    d.text((240, 560), "A TI PRIMERO", font=BEBAS(150), fill=rgba(GOLD, 255 * a), anchor="lm")
    d.text((240, 680), "aunque sea el 5 %", font=PLAY(46, 600), fill=rgba(CREAM, 220 * ease((t - 1.2) / 0.6)), anchor="lm")
    return img


# ------------------------------------------------------------------ el orden de pago (TÚ pasa al primer lugar)
def orden_pago(t, dur, e):
    img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
    centro(d, (W / 2, 120), "CUANDO TE ENTRA EL DINERO", BEBAS(90), rgba(WINE, 255 * ease(t / 0.5)))
    items = ["Mercado", "Servicios", "Préstamos", "Los demás", "TÚ"]
    mover = ease_io((t - dur * 0.45) / 1.2)
    orden_final = ["TÚ", "Mercado", "Servicios", "Préstamos", "Los demás"]
    for k, it in enumerate(items):
        st = 0.4 + k * 0.35
        q = back((t - st) / 0.4)
        if q <= 0:
            continue
        y0 = 260 + k * 140
        y1 = 260 + orden_final.index(it) * 140
        y = lerp(y0, y1, mover)
        es_tu = it == "TÚ"
        x = W / 2 + (60 * math.sin(mover * math.pi) if es_tu else 0)
        d.rounded_rectangle([x - 420, y - 52, x + 420, y + 52], 26, fill=rgba(GOLD if es_tu else PAPER, 255), outline=rgba(WINE if es_tu else GREY, 200), width=3)
        centro(d, (x - 330, y + 2), f"{orden_final.index(it) + 1 if mover > 0.5 else k + 1}.", BEBAS(56), WINE)
        centro(d, (x, y + 2), it, BEBAS(64) if es_tu else PLAY(46, 600), NIGHT if es_tu else INK)
    return img


# ------------------------------------------------------------------ MI CÓDIGO (planner de 7 días en el celular)
def micodigo(t, dur, e):
    img, d = lienzo("vino", t)
    cx, cy = 620, 560 + (1 - min(1, back(t / 0.7))) * 200
    d.rounded_rectangle([cx - 250 + 14, cy - 460 + 18, cx + 250 + 14, cy + 460 + 18], 60, fill=(0, 0, 0, 110))
    d.rounded_rectangle([cx - 250, cy - 460, cx + 250, cy + 460], 60, fill=(24, 22, 28), outline=GOLD, width=6)
    d.rounded_rectangle([cx - 226, cy - 430, cx + 226, cy + 430], 44, fill=CREAM)
    d.text((cx, cy - 360), "MI CÓDIGO", font=PLAY(64, 700), fill=WINE, anchor="mm")
    dia = 1 + int(t / 2.2) % 7
    d.text((cx, cy - 290), f"DÍA {dia} DE 7", font=BEBAS(44), fill=GOLD, anchor="mm")
    areas = ["Mentalidad", "Dinero", "Disciplina", "Presencia"]
    for k, a_ in enumerate(areas):
        y = cy - 190 + k * 140
        d.rounded_rectangle([cx - 200, y - 50, cx + 200, y + 50], 20, fill=PAPER, outline=rgba(GOLD, 160), width=2)
        d.text((cx - 170, y), a_, font=BEBAS(48), fill=INK, anchor="lm")
        c = ease((t - 1.0 - k * 0.6) / 0.4)
        bx = cx + 130
        d.rounded_rectangle([bx, y - 24, bx + 48, y + 24], 8, outline=WINE, width=4)
        if c > 0:
            d.line([(bx + 8, y), (bx + 20, y + 14)], fill=GOLD, width=8)
            if c > 0.4:
                q = (c - 0.4) / 0.6
                d.line([(bx + 20, y + 14), (bx + 20 + 22 * q, y + 14 - 34 * q)], fill=GOLD, width=8)
    items = e.get("items", ["Planner de 7 días", "Lo llenas desde tu celular", "Un paso pequeño por área, cada día"])
    for k, it in enumerate(items):
        q = ease((t - 0.8 - k * 0.6) / 0.5)
        if q > 0:
            y = 380 + k * 120
            d.regular_polygon((1050, y, 14), 4, rotation=45, fill=rgba(GOLD, 255 * q))
            for j, fila in enumerate(envolver(d, it, PLAY(48, 600), 700)):
                d.text((1090 + (1 - q) * 30, y + j * 56), fila, font=PLAY(48, 600), fill=rgba(CREAM, 255 * q), anchor="lm")
    q = ease((t - 2.6) / 0.6)
    d.text((1050, 800), "Enlace en la descripción y en el comentario fijado", font=PLAY(34, 400), fill=rgba(CREAM, 210 * q), anchor="lm")
    if e.get("sello"):
        s = ease((t - 1.6) / 0.35)
        if s > 0:
            r = 120 * lerp(1.8, 1.0, s)
            sello = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            g = ImageDraw.Draw(sello, "RGBA")
            g.ellipse([20, 20, 380, 380], fill=rgba(GOLD, 245), outline=rgba(WHITE, 230), width=6)
            g.text((200, 150), "7 DÍAS", font=BEBAS(96), fill=WINE, anchor="mm")
            g.text((200, 240), "DE GARANTÍA", font=BEBAS(60), fill=WINE, anchor="mm")
            sello = sello.rotate(12, resample=Image.Resampling.BICUBIC).resize((int(2 * r), int(2 * r)))
            img.paste(sello, (int(900 - r), int(220 - r)), sello)
    return img


# ------------------------------------------------------------------ un dato que cuenta (45)
def dato(t, dur, e):
    img, d = lienzo("noche", t)
    anillos(d, t)
    v = int(e["valor"] * ease_io((t - 0.4) / 2.0))
    centro(d, (W / 2, 470), str(v), BEBAS(int(380 * (1 + 0.03 * math.sin(t * 3)))), rgba(GOLD, 255))
    centro(d, (W / 2, 690), e.get("unidad", ""), BEBAS(80), rgba(CREAM, 255 * ease((t - 1.2) / 0.5)))
    for k, fila in enumerate(envolver(d, e["texto"], PLAY(44, 600), 1300)):
        centro(d, (W / 2, 790 + k * 56), fila, PLAY(44, 600), rgba(CREAM, 220 * ease((t - 2.0) / 0.6)))
    return img


# ------------------------------------------------------------------ tres ventajas / lista de tarjetas
def lista3(t, dur, e):
    img, d = lienzo("vino", t)
    centro(d, (W / 2, 140), e.get("titulo", ""), BEBAS(90), rgba(GOLD, 255 * ease(t / 0.5)))
    items = e["items"]
    paso = max(1.2, (dur * 0.75) / len(items))
    for k, (tit, sub) in enumerate(items):
        q = back((t - 0.5 - k * paso) / 0.5)
        if q <= 0:
            continue
        x = W / 2 + (k - (len(items) - 1) / 2) * 560
        y = 560 + (1 - min(1, q)) * 80
        d.rounded_rectangle([x - 240, y - 230, x + 240, y + 230], 34, fill=rgba(PAPER, 250), outline=rgba(GOLD, 220), width=4)
        d.ellipse([x - 50, y - 190, x + 50, y - 90], fill=GOLD)
        centro(d, (x, y - 136), str(k + 1), BEBAS(80), NIGHT)
        centro(d, (x, y - 10), tit, BEBAS(70), WINE)
        for j, fila in enumerate(envolver(d, sub, PLAY(34, 600), 400)):
            centro(d, (x, y + 70 + j * 44), fila, PLAY(34, 600), INK)
    return img


# ------------------------------------------------------------------ 12:30 de la noche (la mujer que no para)
def noche_plancha(t, dur, e):
    img = Image.new("RGB", (W, H), (40, 34, 52)); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, W, 760], fill=(52, 44, 64))
    d.rectangle([1260, 130, 1760, 520], fill=(26, 24, 46), outline=(90, 70, 84), width=12)
    d.ellipse([1580, 170, 1660, 250], fill=(240, 226, 196))
    MUJER52.pegar(img, 760, 560, 900, t, boca="neutra")
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(380, 760), (1180, 760), (1120, 800), (440, 800)], fill=(170, 160, 168))         # tabla de planchar
    d.line([(560, 800), (520, 1000)], fill=(120, 110, 118), width=10); d.line([(1000, 800), (1040, 1000)], fill=(120, 110, 118), width=10)
    px = 820 + 160 * math.sin(t * 2.2)
    d.polygon([(px - 90, 752), (px + 70, 752), (px + 110, 712), (px - 60, 712)], fill=(200, 200, 210))
    d.rounded_rectangle([px - 40, 680, px + 40, 712], 12, fill=WINE)
    for k in range(3):                                                    # vapor
        y = 690 - ((t * 60 + k * 30) % 90)
        d.ellipse([px + 60 + k * 14, y, px + 80 + k * 14, y + 20], fill=rgba(WHITE, 80))
    a = ease(t / 0.6)
    d.text((160, 170), "12:30 A.M.", font=BEBAS(130), fill=rgba(GOLD, 255 * a), anchor="lm")
    for k, fila in enumerate(["planchar", "dejar lista la comida", "contestar a la hija", "a la cama a la 1, de pie a las 5"]):
        q = ease((t - 1.0 - k * 1.2) / 0.5)
        if q > 0:
            d.regular_polygon((175, 290 + k * 62, 10), 4, rotation=45, fill=rgba(GOLD, 255 * q))
            d.text((200, 290 + k * 62), fila, font=PLAY(44, 600), fill=rgba(CREAM, 255 * q), anchor="lm")
    return img


# ------------------------------------------------------------------ la medalla del cansancio
def medalla(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = W / 2, 470
    sw = 8 * math.sin(t * 2)
    d.polygon([(cx - 120 + sw, 120), (cx - 20 + sw, 120), (cx + 40, cy - 120), (cx - 60, cy - 120)], fill=WINE)
    d.polygon([(cx + 20 + sw, 120), (cx + 120 + sw, 120), (cx + 60, cy - 120), (cx - 40, cy - 120)], fill=(150, 34, 60))
    p = back(t / 0.6)
    r = 170 * min(1.05, p)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD, outline=(160, 120, 50), width=10)
    centro(d, (cx, cy + 6), "CANSADA", BEBAS(int(92 * min(1, p)) + 1), (110, 80, 30))
    x = ease((t - dur * 0.45) / 0.4)
    if x > 0:
        d.line([(cx - 220, cy - 220), (cx - 220 + 440 * x, cy - 220 + 440 * x)], fill=rgba(ROJO, 240), width=22)
    q = ease((t - dur * 0.55) / 0.6)
    centro(d, (W / 2, 770), "DESCANSAR NO ES FLOJERA.", BEBAS(96), rgba(CREAM, 255 * q))
    centro(d, (W / 2, 870), "ES ESTRATEGIA.", BEBAS(110), rgba(GOLD, 255 * ease((t - dur * 0.6) / 0.6)))
    return img


# ------------------------------------------------------------------ la mochila de piedras → cimiento
def mochila(t, dur, e):
    img, d = lienzo("noche", t, part=False)
    d.rectangle([0, 900, W, H], fill=(30, 22, 26))
    fase = e.get("fase")
    trans = 0.0 if fase == "carga" else ease_io((t - 0.4) / 2.0) if fase == "cimiento" else ease_io((t - dur * 0.45) / 2.0)
    bx, by = 520, 560
    d.rounded_rectangle([bx - 220, by - 260, bx + 220, by + 300], 90, fill=rgba((92, 70, 60), 255 * (1 - trans * 0.7)))
    d.rounded_rectangle([bx - 160, by - 330, bx + 160, by - 220], 50, outline=rgba((92, 70, 60), 255 * (1 - trans)), width=26)
    etiquetas = ["un error", "una culpa", "lo que te dijeron", "esa relación", "esa decisión", "lo que te recuerdan"]
    for k, et in enumerate(etiquetas):
        sx, sy = bx - 120 + (k % 3) * 120, by - 120 + (k // 3) * 170
        tx, ty = 1060 + k * 115, 860
        x, y = lerp(sx, tx, trans), lerp(sy, ty, trans) - math.sin(trans * math.pi) * 200
        d.ellipse([x - 62, y - 48, x + 62, y + 48], fill=(110, 104, 108), outline=(80, 74, 78), width=4)
        if trans < 0.2:
            centro(d, (x, y), et.split()[-1].upper()[:9], BEBAS(28), rgba(CREAM, 220))
    if trans > 0.7:                                                        # la casa sobre el cimiento
        a = ease((trans - 0.7) / 0.3)
        d.rectangle([1080, 560, 1720, 810], outline=rgba(GOLD, 255 * a), width=10)
        d.polygon([(1040, 570), (1400, 330), (1760, 570)], outline=rgba(GOLD, 255 * a), width=10)
        d.rectangle([1350, 680, 1450, 810], outline=rgba(GOLD, 255 * a), width=8)
    a = ease(t / 0.6)
    titulo = "UNA MOCHILA LLENA DE PIEDRAS" if trans < 0.5 else "EL CIMIENTO DE UNA CASA FIRME"
    centro(d, (W / 2, 110), titulo, BEBAS(84), rgba(GOLD if trans >= 0.5 else CREAM, 255 * a))
    return img


# ------------------------------------------------------------------ el resumen (lista con palomitas)
def resumen(t, dur, e):
    img = fondo("crema").copy(); d = ImageDraw.Draw(img, "RGBA")
    centro(d, (W / 2, 90), e.get("titulo", "LAS 8, EN UNA SOLA MIRADA"), BEBAS(84), rgba(WINE, 255 * ease(t / 0.5)))
    items = e["items"]
    paso = max(0.8, (dur * 0.85) / len(items))
    for k, it in enumerate(items):
        q = ease((t - 0.4 - k * paso) / 0.4)
        if q <= 0:
            continue
        col, fila = k % 2, k // 2
        x = 200 + col * 820
        y = 220 + fila * 180
        d.rounded_rectangle([x, y, x + 760, y + 140], 24, fill=rgba(PAPER, 255 * q), outline=rgba(GOLD, 180 * q), width=3)
        d.ellipse([x + 26, y + 36, x + 94, y + 104], fill=rgba(GOLD, 255 * q))
        d.line([(x + 44, y + 70), (x + 58, y + 86), (x + 80, y + 54)], fill=rgba(WHITE, 255 * q), width=8)
        for j, ln in enumerate(envolver(d, it, PLAY(38, 600), 600)):
            d.text((x + 120 + (1 - q) * 20, y + 70 + (j - (len(envolver(d, it, PLAY(38, 600), 600)) - 1) / 2) * 46), ln,
                   font=PLAY(38, 600), fill=rgba(INK, 255 * q), anchor="lm")
    return img


# ------------------------------------------------------------------ capítulo 5 contra capítulo 20
def capitulos_libro(t, dur, e):
    img, d = lienzo("vino", t)
    for k, (x, txt, sub, col) in enumerate(((620, "CAPÍTULO 5", "tu historia", CREAM), (1300, "CAPÍTULO 20", "la de otra persona", GOLD))):
        q = back((t - 0.3 - k * 0.6) / 0.5)
        if q <= 0:
            continue
        y = 520 + (1 - min(1, q)) * 120
        d.rounded_rectangle([x - 230, y - 300, x + 230, y + 300], 18, fill=rgba(PAPER, 255), outline=rgba(col, 255), width=6)
        d.rectangle([x - 230, y - 300, x - 196, y + 300], fill=rgba(WINE if k == 0 else GOLD, 255))
        centro(d, (x + 16, y - 40), txt, BEBAS(80), WINE)
        centro(d, (x + 16, y + 50), sub, PLAY(36, 400), INK)
    q = ease((t - 2.0) / 0.5)
    centro(d, (W / 2, 120), "NO SE COMPARAN", BEBAS(100), rgba(CREAM, 255 * q))
    centro(d, (W / 2, 960), "la única comparación: ¿eres mejor que la de ayer?", PLAY(44, 600), rgba(GOLD, 255 * ease((t - dur * 0.6) / 0.6)))
    return img


E.ESCENAS.update({"numero": numero, "burbujas": burbujas, "edades": edades, "dos_mujeres": dos_mujeres, "mesa_familia": mesa_familia,
                  "sobre": sobre, "orden_pago": orden_pago, "micodigo": micodigo, "dato": dato, "lista3": lista3,
                  "noche_plancha": noche_plancha, "medalla": medalla, "mochila": mochila, "resumen": resumen,
                  "capitulos_libro": capitulos_libro})


_viejo = E.textos_en_pantalla


def textos_en_pantalla(e, tab):
    extra = []
    if e["tipo"] == "numero":
        extra += e["titulo"] + [f"la {ORDINAL.get(e['n_punto'], '')} cosa"]
    if e["tipo"] in ("burbujas",):
        extra += e["frases"]
    if e["tipo"] in ("resumen", "lista3"):
        extra += [x if isinstance(x, str) else " ".join(x) for x in e["items"]]
    return _viejo(e, tab) + " " + " ".join(extra)


E.textos_en_pantalla = textos_en_pantalla
