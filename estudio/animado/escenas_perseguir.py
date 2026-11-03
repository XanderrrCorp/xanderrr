"""Escenas para videos tipo «camino por días» (reutilizables): el mapa de paradas, dos mujeres en la cama a las 11 p. m.,
el celular que se voltea, las notificaciones, el hueco que se llena y los mensajes de él. Todas con movimiento continuo."""
import math

from PIL import Image, ImageDraw

import escenas as E
from escenas import (BEBAS, CREAM, GOLD, GREY, HAND, INK, NIGHT, PAPER, PLAY, W, WHITE, WINE, H, anillos, back, centro,
                     ease, ease_io, envolver, fondo, lerp, lienzo, rgba)
import escenas_extra as X
import personajes as Q

ELLA = Q.Personaje(piel="#DDA27C", pelo="#3A2A26", peinado="suelto", ropa="#6E1C2E", ropa2="#6E1C2E", edad=34)
ELLA2 = Q.Personaje(piel="#DDA27C", pelo="#3A2A26", peinado="mono", ropa="#D6AC5C", ropa2="#D6AC5C", edad=34)


# ------------------------------------------------------------------ el camino de paradas
def camino(t, dur, e):
    """Un sendero con las paradas (Día 1, 3, 7, 21, 90 y la sexta sin fecha). Un punto dorado camina hasta la parada
    actual; las anteriores quedan doradas."""
    img, d = lienzo("noche", t)
    paradas = e.get("paradas", ["DÍA 1", "DÍA 3", "DÍA 7", "DÍA 21", "DÍA 90", "?"])
    actual = e.get("actual", 0)                # 0 = mostrar el camino entero
    pts = []
    for k in range(len(paradas)):
        x = 180 + k * (W - 360) / (len(paradas) - 1)
        y = 620 + 120 * math.sin(k * 1.3)
        pts.append((x, y))
    trazo = ease_io(t / 1.6)
    for k in range(len(pts) - 1):                                  # sendero que se dibuja
        q = max(0.0, min(1.0, trazo * (len(pts) - 1) - k))
        if q <= 0:
            continue
        (x0, y0), (x1, y1) = pts[k], pts[k + 1]
        for j in range(0, 20):
            if j / 20 > q:
                break
            xa, ya = lerp(x0, x1, j / 20), lerp(y0, y1, j / 20)
            d.ellipse([xa - 5, ya - 5, xa + 5, ya + 5], fill=rgba(GOLD if actual and k < actual - 1 else CREAM, 150))
    for k, ((x, y), et) in enumerate(zip(pts, paradas)):
        q = back((t - 0.3 - k * 0.2) / 0.4)
        if q <= 0:
            continue
        hecho = actual and k < actual - 1
        es = actual and k == actual - 1
        r = (62 if es else 46) * min(1.1, q) * (1 + (0.06 * math.sin(t * 4) if es else 0))
        d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(GOLD if (hecho or es) else (60, 44, 56), 255), outline=rgba(CREAM, 200), width=4)
        centro(d, (x, y + 4), str(k + 1), BEBAS(int(r * 1.1)), NIGHT if (hecho or es) else CREAM)
        centro(d, (x, y + r + 44), et, BEBAS(48), rgba(GOLD if es else CREAM, 255 * min(1, q)))
    if actual:                                                     # el punto que camina hasta la parada actual
        k0 = max(0, actual - 2)
        q = ease_io((t - 0.8) / 1.4)
        (x0, y0), (x1, y1) = pts[k0], pts[actual - 1]
        xm, ym = lerp(x0, x1, q), lerp(y0, y1, q) - 60 * math.sin(q * math.pi)
        d.ellipse([xm - 18, ym - 18, xm + 18, ym + 18], fill=WHITE, outline=GOLD, width=5)
    tit = e.get("titulo", "")
    if tit:
        a = ease((t - 0.2) / 0.5)
        centro(d, (W / 2, 160), tit, BEBAS(110), rgba(GOLD, 255 * a))
    sub = e.get("subtitulo", "")
    if sub:
        centro(d, (W / 2, 260), sub, PLAY(52, 700), rgba(CREAM, 255 * ease((t - 0.6) / 0.5)))
    return img


# ------------------------------------------------------------------ dos mujeres a las 11 de la noche
def _cama(d, cx, base, ancho, color):
    d.rounded_rectangle([cx - ancho / 2, base - 40, cx + ancho / 2, base + 160], 30, fill=color)
    d.rounded_rectangle([cx - ancho / 2 + 20, base - 90, cx - ancho / 2 + 220, base - 10], 30, fill=(240, 232, 222))


def dos_camas(t, dur, e):
    img = Image.new("RGB", (W, H), (34, 30, 48)); d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([W / 2 - 3, 0, W / 2 + 3, H], fill=(20, 16, 28))
    fase = e.get("fase", "ambas")
    # izquierda: el celular a 5 cm de la cara, la luz azul le pega
    ELLA.pegar(img, 480, 560, 620, t, boca="neutra")
    d = ImageDraw.Draw(img, "RGBA")
    brillo = 0.7 + 0.3 * math.sin(t * 9) * (1 if int(t * 2) % 3 else 0)
    d.ellipse([300, 360, 660, 720], fill=rgba((90, 150, 230), 34 * brillo))
    _cama(d, 480, 820, 760, (80, 60, 90))
    px, py = 560 + 6 * math.sin(t * 13), 590
    d.rounded_rectangle([px - 50, py - 90, px + 50, py + 90], 14, fill=(20, 20, 26), outline=(90, 90, 100), width=4)
    d.rounded_rectangle([px - 40, py - 78, px + 40, py + 78], 8, fill=rgba((120, 170, 230), 230 * brillo))
    escrito = "Hola, ¿cómo" if int(t * 1.3) % 3 == 0 else ("Hola" if int(t * 1.3) % 3 == 1 else "")
    d.text((px - 34, py + 50), escrito, font=PLAY(18, 600), fill=INK, anchor="lm")
    centro(d, (480, 120), "23:00 · EN LÍNEA", BEBAS(64), rgba((150, 190, 240), 255 * ease(t / 0.5)))
    if fase == "ambas":
        a = ease((t - 0.3) / 0.6)
        if a > 0:
            ELLA2.pegar(img, 1440, 560, 620, t, boca="sonrisa")
            d = ImageDraw.Draw(img, "RGBA")
            d.ellipse([1250, 380, 1640, 740], fill=rgba(GOLD, 26 * a))
            _cama(d, 1440, 820, 760, (110, 40, 60))
            # taza de té con vapor y libro
            d.rounded_rectangle([1300, 640, 1380, 720], 16, fill=CREAM)
            for k in range(3):
                yv = 630 - ((t * 40 + k * 25) % 70)
                d.ellipse([1320 + k * 16, yv, 1334 + k * 16, yv + 14], fill=rgba(WHITE, 90))
            d.polygon([(1430, 700), (1590, 680), (1600, 760), (1440, 780)], fill=(230, 220, 200), outline=GOLD)
            # celular boca abajo en la mesa
            d.rectangle([1700, 760, 1880, 800], fill=(90, 60, 50))
            d.rounded_rectangle([1730, 742, 1850, 762], 6, fill=(30, 30, 36))
            centro(d, (1440, 120), "23:00 · SU NOCHE ES SUYA", BEBAS(64), rgba(GOLD, 255 * a))
    else:
        centro(d, (1440, 540), "?", BEBAS(int(260 + 20 * math.sin(t * 3))), rgba(CREAM, 60))
    return img


# ------------------------------------------------------------------ el celular que se voltea boca abajo
def celular_voltear(t, dur, e):
    img, d = lienzo("vino", t)
    d.rectangle([0, 760, W, H], fill=(70, 46, 40))
    gira = ease_io((t - e.get("voltear_en", dur * 0.5)) / 0.8)
    cx, cy = W / 2, 560 + 200 * gira
    alto = 640 * (1 - 2 * gira) + 30 if gira < 0.5 else 30 + 60 * (gira - 0.5) * 2      # boca abajo: queda acostado
    ancho = 320
    cara = gira < 0.5
    d.rounded_rectangle([cx - ancho / 2, cy - alto / 2, cx + ancho / 2, cy + alto / 2], 40,
                        fill=(24, 22, 28) if cara else (40, 36, 44), outline=GOLD if not cara else (90, 90, 100), width=6)
    if cara and alto > 200:
        d.rounded_rectangle([cx - ancho / 2 + 18, cy - alto / 2 + 22, cx + ancho / 2 - 18, cy + alto / 2 - 22], 26,
                            fill=(60, 110, 170))
        n = int(t * 1.5) % 4
        for k in range(n):
            d.rounded_rectangle([cx - 120, cy - alto / 2 + 60 + k * 70, cx + 120, cy - alto / 2 + 115 + k * 70], 14, fill=(240, 240, 248, 220))
    if not cara:
        ondas = (t * 1.2) % 1
        d.ellipse([cx - 200 - 120 * ondas, cy - 40 - 30 * ondas, cx + 200 + 120 * ondas, cy + 40 + 30 * ondas], outline=rgba(GOLD, 160 * (1 - ondas)), width=4)
    centro(d, (W / 2, 140), e.get("titulo", "PONLO BOCA ABAJO"), BEBAS(110), rgba(GOLD, 255 * ease(t / 0.5)))
    if not cara:
        centro(d, (W / 2, 280), e.get("despues", "tu noche te pertenece"), PLAY(56, 700), rgba(CREAM, 255 * ease((t - e.get("voltear_en", dur * 0.5) - 0.6) / 0.5)))
    return img


# ------------------------------------------------------------------ el celular que vibra con notificaciones
def notificaciones(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = 1320 + (8 * math.sin(t * 60) if (t % 2.5) < 0.4 else 0), 560
    d.rounded_rectangle([cx - 250, cy - 460, cx + 250, cy + 460], 60, fill=(24, 22, 28), outline=(90, 80, 90), width=10)
    d.rounded_rectangle([cx - 226, cy - 430, cx + 226, cy + 430], 44, fill=(36, 30, 46))
    d.text((cx, cy - 330), "11:47", font=BEBAS(140), fill=CREAM, anchor="mm")
    notis = e.get("notis", [("Familia", "Tía: ¿vienen el domingo?"), ("Tienda", "¡2x1 solo hoy!"), ("Banco", "Tu saldo es…"), ("Grupo trabajo", "Mañana reunión 8 am")])
    for k, (de, txt) in enumerate(notis):
        st = 0.8 + k * max(1.2, (dur - 2) / len(notis))
        q = back((t - st) / 0.4)
        if q <= 0:
            continue
        y = cy - 200 + k * 140
        d.rounded_rectangle([cx - 210, y, cx + 210, y + 120], 24, fill=rgba(CREAM, 240 * min(1, q)))
        d.text((cx - 190, y + 36), de, font=BEBAS(36), fill=WINE, anchor="lm")
        d.text((cx - 190, y + 84), txt[:26], font=PLAY(28, 600), fill=INK, anchor="lm")
        d.text((cx + 190, y + 36), "NO ES ÉL", font=BEBAS(28), fill=rgba(GREY, 255 * min(1, q)), anchor="rm")
    a = ease(t / 0.6)
    d.text((200, 360), e.get("titulo", "DÍA 1"), font=BEBAS(150), fill=rgba(GOLD, 255 * a), anchor="lm")
    d.text((200, 500), e.get("subtitulo", "LA ANSIEDAD"), font=BEBAS(110), fill=rgba(CREAM, 255 * a), anchor="lm")
    latido = 1 + 0.12 * max(0.0, math.sin(t * 7.5)) ** 8
    X_ = 330
    d.ellipse([X_ - 50 * latido, 700 - 45 * latido, X_ + 50 * latido, 700 + 45 * latido], fill=rgba((214, 60, 70), 230))
    d.text((440, 700), f"{int(98 + 20 * abs(math.sin(t * 2)))} lpm", font=BEBAS(70), fill=CREAM, anchor="lm")
    return img


# ------------------------------------------------------------------ el vacío: un hueco que se llena con lo tuyo
def vacio(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = W / 2 + 280, 560
    r = 260 + 10 * math.sin(t * 1.6)
    llenar = ease_io((t - e.get("llenar_en", dur * 0.45)) / 2.0)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=rgba(CREAM, 160), width=6)
    for k in range(18):                                           # borde punteado que gira: el hueco
        ang = k * math.pi / 9 + t * 0.3
        d.ellipse([cx + (r + 30) * math.cos(ang) - 5, cy + (r + 30) * math.sin(ang) - 5,
                   cx + (r + 30) * math.cos(ang) + 5, cy + (r + 30) * math.sin(ang) + 5], fill=rgba(GOLD, 120))
    cosas = e.get("cosas", ["un curso", "tus amigas", "tu fe", "tu cuerpo", "tu proyecto", "tu descanso"])
    for k, c in enumerate(cosas):
        q = ease((llenar * len(cosas)) - k)
        if q <= 0:
            continue
        ang = k * 2 * math.pi / len(cosas) + t * 0.15
        rr = lerp(r + 300, r * 0.55, q)
        x, y = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        d.rounded_rectangle([x - 110, y - 36, x + 110, y + 36], 36, fill=rgba(GOLD, 240))
        centro(d, (x, y), c, PLAY(30, 700), NIGHT)
    a = ease(t / 0.6)
    d.text((140, 380), e.get("titulo", "DÍA 3"), font=BEBAS(150), fill=rgba(GOLD, 255 * a), anchor="lm")
    d.text((140, 520), e.get("subtitulo", "EL VACÍO"), font=BEBAS(110), fill=rgba(CREAM, 255 * a), anchor="lm")
    q = ease((t - e.get("llenar_en", dur * 0.45)) / 0.6)
    d.text((140, 680), "no es un error:", font=PLAY(48, 600), fill=rgba(CREAM, 230 * q), anchor="lm")
    d.text((140, 750), "es espacio que ahora es tuyo", font=PLAY(48, 700), fill=rgba(GOLD, 255 * q), anchor="lm")
    return img


# ------------------------------------------------------------------ día 7: llegan los mensajes de él
def mensaje_el(t, dur, e):
    img, d = lienzo("noche", t)
    cx, cy = 1320, 560
    vibra = 8 * math.sin(t * 60) if 0.6 < t < 1.2 else 0
    d.rounded_rectangle([cx - 250 + vibra, cy - 460, cx + 250 + vibra, cy + 460], 60, fill=(24, 22, 28), outline=GOLD, width=8)
    d.rounded_rectangle([cx - 226 + vibra, cy - 430, cx + 226 + vibra, cy + 430], 44, fill=(40, 34, 50))
    d.text((cx, cy - 360), "ÉL", font=BEBAS(64), fill=CREAM, anchor="mm")
    msgs = e.get("mensajes", ["Hola, ¿cómo estás? Te extraño.", "Vi esta canción y me acordé de ti.", "¿Todo bien?"])
    for k, m in enumerate(msgs):
        q = back((t - 0.8 - k * 1.6) / 0.4)
        if q <= 0:
            continue
        filas = envolver(d, m, PLAY(32, 600), 360)
        y = cy - 260 + k * 190
        d.rounded_rectangle([cx - 210, y, cx + 200, y + 40 + 44 * len(filas)], 26, fill=rgba(CREAM, 245 * min(1, q)))
        for j, f in enumerate(filas):
            d.text((cx - 190, y + 42 + j * 44), f, font=PLAY(32, 600), fill=INK, anchor="lm")
    a = ease(t / 0.6)
    d.text((160, 330), "DÍA 7", font=BEBAS(150), fill=rgba(GOLD, 255 * a), anchor="lm")
    d.text((160, 470), "LA PRUEBA", font=BEBAS(110), fill=rgba(CREAM, 255 * a), anchor="lm")
    q = back((t - e.get("pregunta_en", dur * 0.6)) / 0.5)
    if q > 0:
        s = 1 + 0.04 * math.sin(t * 4)
        d.rounded_rectangle([140, 600, 800, 760], 30, fill=rgba(GOLD, 245 * min(1, q)))
        d.text((470, 680), "¿QUÉ CAMBIÓ?", font=BEBAS(int(110 * min(1, q) * s) + 1), fill=NIGHT, anchor="mm")
        d.text((470, 820), "en hechos, no en palabras", font=PLAY(44, 600), fill=rgba(CREAM, 230 * min(1, q)), anchor="mm")
    return img


E.ESCENAS.update({"camino": camino, "dos_camas": dos_camas, "celular_voltear": celular_voltear, "notificaciones": notificaciones,
                  "vacio": vacio, "mensaje_el": mensaje_el})
