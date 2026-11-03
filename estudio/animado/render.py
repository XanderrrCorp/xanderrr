"""Paso 3 y 4: subtítulos + render por tramos en paralelo + unión con el audio.
Uso: python render.py [segundos_max] [salida.mp4]      (sin segundos: todo el video)
     python render.py --hoja t1,t2,...                  (hoja de cuadros para revisar)"""
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import escenas as E  # noqa: E402
import escenas_extra  # noqa: E402,F401
import escenas_perseguir  # noqa: E402,F401
import profesor_anim as PR  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
FF = "/usr/bin/ffmpeg"
W, H, FPS = E.W, E.H, E.FPS
XF = 0.45                                     # fundido entre escenas
PLAN = json.loads((AQUI / "escenas.json").read_text(encoding="utf-8"))
TL = json.loads((AQUI / "timeline.json").read_text(encoding="utf-8"))
TAB = PLAN["tabla"]
ESC = PLAN["escenas"]


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-zñ0-9]+", s)


# ------------------------------------------------------------------ subtítulos (3 a 6 palabras por línea)
def trozos(texto):
    palabras = texto.split()
    salida, actual = [], []
    for p in palabras:
        actual.append(p)
        corta = re.search(r"[.,;:?!»\"]$", p)
        if len(actual) >= 6 or (len(actual) >= 3 and corta):
            salida.append(actual); actual = []
    if actual:
        if len(actual) < 3 and salida and len(salida[-1]) + len(actual) <= 7:
            salida[-1] += actual
        else:
            salida.append(actual)
    return [" ".join(x) for x in salida]


def subtitulos():
    """Reparte el tiempo de cada segmento por letras (cada segmento ya tiene su duración exacta); cuenta la pausa
    de 0,6 s entre párrafos."""
    subs = []
    for s in TL["segmentos"]:
        dur = s["fin"] - s["inicio"]
        pausas = 0.45 * (len(s["parrafos"]) - 1)
        habla = max(0.5, dur - pausas)
        grupos = [trozos(par) for par in s["parrafos"]]
        letras = sum(len(tr) + 1 for g in grupos for tr in g)
        t = s["inicio"]
        for k, g in enumerate(grupos):
            for tr in g:
                d = habla * (len(tr) + 1) / letras
                subs.append({"ini": t, "fin": t + d, "texto": tr})
                t += d
            t += 0.45 if k < len(grupos) - 1 else 0
    return subs


SUBS = subtitulos()
for e in ESC:
    e["_pantalla"] = set(_norm(E.textos_en_pantalla(e, TAB)))


def escena_en(T):
    for i, e in enumerate(ESC):
        if e["inicio"] <= T < e["fin"]:
            return i
    return len(ESC) - 1


def sub_en(T):
    for s in SUBS:
        if s["ini"] <= T < s["fin"]:
            return s
    return None


def dibujar_sub(img, texto):
    d = ImageDraw.Draw(img, "RGBA")
    f = E.BEBAS(78)
    x, y = W / 2, 975
    w = d.textlength(texto, font=f)
    d.rounded_rectangle([x - w / 2 - 34, y - 52, x + w / 2 + 34, y + 50], 18, fill=(0, 0, 0, 120))
    d.text((x, y), texto, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))


def camara(img, e, t):
    """Movimiento de cámara en TODAS las escenas (02-11, el dueño: «hay escenas que se quedan más de 10 s estáticas»):
    acercamiento/alejamiento del 10 %, paneo de lado y un «golpe» suave de zoom cada ~3,5 s, así siempre hay algo
    moviéndose aunque el texto ya esté quieto."""
    k = e["n"]
    dur = max(1.0, e["duracion"])
    prog = E.ease_io(t / dur)
    suave = e["tipo"] in ("tabla", "pausa")
    amp = 0.04 if suave else 0.10
    z = 1.0 + amp * (prog if k % 2 == 0 else 1 - prog)
    kick_cada = 3.5
    fase = (t % kick_cada) / kick_cada
    if t > 1.0:
        z += (0.012 if suave else 0.028) * math.exp(-fase * 6) * (1 - math.exp(-fase * 40))
    px = (1 if k % 3 == 0 else -1 if k % 3 == 1 else 0.5) * 70 * (prog - 0.5)
    py = 18 * math.sin(t * 0.7 + k)
    w, h = W / z, H / z
    x0 = min(max(0.0, (W - w) / 2 + px * (z - 1) * 6), W - w)
    y0 = min(max(0.0, (H - h) / 2 + py * (z - 1) * 6), H - h)
    return img.resize((W, H), Image.Resampling.BILINEAR, box=(x0, y0, x0 + w, y0 + h))


def escena_lista(i, t):
    e = ESC[i]
    return camara(E.dibujar(e, t, TAB), e, t)


def transicion(a, b, q, tipo):
    """q: 0 → solo a, 1 → solo b."""
    q = E.ease_io(q)
    if tipo == "empuje":
        dx = int(W * q)
        out = Image.new("RGB", (W, H))
        out.paste(a, (-dx, 0)); out.paste(b, (W - dx, 0))
        return out
    if tipo == "zoom":
        z = 1 + 0.25 * q
        w, h = W / z, H / z
        a2 = a.resize((W, H), Image.Resampling.BILINEAR, box=((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2))
        return Image.blend(a2, b, q)
    if tipo == "barrido":
        out = a.copy()
        x = int(W * q)
        out.paste(b.crop((0, 0, x, H)), (0, 0))
        dd = ImageDraw.Draw(out)
        dd.rectangle([x - 14, 0, x + 14, H], fill=E.GOLD)
        return out
    return Image.blend(a, b, q)


TIPOS_TRANS = ["empuje", "fundido", "zoom", "barrido", "fundido"]


def chip_tabla(img, T):
    """Indicador fijo «TU TABLA 2/5» (cuántas filas van) en las escenas que no son la tabla."""
    llenas = 0
    for e in ESC:
        if e["tipo"] == "pausa" and e["temporizador_desde"] <= T:
            llenas = max(llenas, e["fila"])
    if llenas == 0:
        return
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([40, 36, 330, 96], 30, fill=(18, 14, 20, 170), outline=E.GOLD + (200,), width=2)
    d.text((70, 66), "TU TABLA", font=E.BEBAS(36), fill=E.CREAM, anchor="lm")
    for k in range(5):
        x = 200 + k * 24
        d.rounded_rectangle([x, 54, x + 16, 78], 4, fill=E.GOLD if k < llenas else (90, 80, 90))


# ------------------------------------------------------------------ El Profesor
POS_ESQUINA = {"mivalor": (1740, 190, 270), "micodigo": (1770, 190, 250), "membresia": (250, 250, 300), "encuesta": (230, 240, 280),
               "comentario": (1700, 860, 300), "cuatro_palabras": (230, 220, 270), "comentarios": (1790, 960, 210),
               "fondo_frase": (240, 830, 320)}
GESTOS = PLAN.get("gestos", [])


def gesto_en(T):
    g = 0.0
    for a, b in GESTOS:
        if a - 0.35 <= T <= b + 0.35:
            g = max(g, min(E.ease((T - a + 0.35) / 0.35), E.ease((b + 0.35 - T) / 0.35)))
    return g


def poner_profesor(img, i, T):
    e = ESC[i]
    modo = e.get("profesor")
    if not modo:
        return
    t = T - e["inicio"]
    previo = ESC[i - 1].get("profesor") if i > 0 else None
    entrada = 1.0 if previo == modo else E.back(t / 0.5)
    if modo == "lado":
        PR.dibujar(img, 390, 560, 640, T, gesto=gesto_en(T), entrada=entrada)
    elif modo == "final":
        PR.dibujar(img, 470, 560, 760, T, apuntar=True, entrada=entrada)
    elif modo == "tabla":
        PR.dibujar(img, 1795, 945, 210, T, gesto=gesto_en(T), entrada=entrada)
    else:
        x, y, tam = POS_ESQUINA.get(e["tipo"], (1700, 830, 300))
        PR.dibujar(img, x, y, tam, T, gesto=gesto_en(T), entrada=entrada)


# ------------------------------------------------------------------ barra de progreso («FILA 3 DE 5»)
PROG = PLAN.get("progreso")


def barra_progreso(img, T):
    if not PROG or not PROG["secciones"]:
        return
    secs = PROG["secciones"]
    if T < secs[0]["inicio"] or T > secs[-1].get("completa", 1e9) + 1.5:
        return
    if any(a <= T < b for a, b in PROG["ocultar"]):
        return
    actual = max(sc["n"] for sc in secs if sc["inicio"] <= T)
    d = ImageDraw.Draw(img, "RGBA")
    total = PROG["total"]
    ancho = 360                                          # cabe con 5 u 8 secciones (antes se salía con 8)
    g = 10 if total <= 6 else 7
    w = (ancho - g * (total - 1)) / total
    x0, y0, h = 1890 - ancho - 14, 52, 16
    d.rounded_rectangle([x0 - 230, 26, x0 + ancho + 14, 92], 30, fill=(18, 14, 20, 150))
    d.text((x0 - 14, y0 + 8), f"{PROG['etiqueta']} {actual} DE {total}", font=E.BEBAS(40), fill=E.CREAM, anchor="rm")
    for sc in secs:
        k = sc["n"] - 1
        x = x0 + k * (w + g)
        comp = sc.get("completa", 1e9)
        pop = 0.0
        if comp <= T < comp + 0.4:
            pop = math.sin((T - comp) / 0.4 * math.pi)
        hh = h * (1 + 0.8 * pop)
        caja = [x, y0 + h / 2 - hh / 2, x + w, y0 + h / 2 + hh / 2]
        if T >= comp:
            d.rounded_rectangle(caja, 5, fill=E.GOLD + (255,))
        else:
            d.rounded_rectangle(caja, 5, fill=(255, 255, 255, 64))
            if sc["n"] == actual:
                frac = max(0.0, min(1.0, (T - sc["inicio"]) / max(1.0, comp - sc["inicio"])))
                d.rounded_rectangle([x, caja[1], x + max(8, w * frac), caja[3]], 5, fill=E.GOLD + (255,))


def cuadro(T):
    i = escena_en(T)
    e = ESC[i]
    img = escena_lista(i, T - e["inicio"])
    tl = e["fin"] - T
    if tl < XF and i + 1 < len(ESC):
        img = transicion(img, escena_lista(i + 1, 0.05), 1 - tl / XF, TIPOS_TRANS[i % len(TIPOS_TRANS)])
    poner_profesor(img, i, T)
    barra_progreso(img, T)
    s = sub_en(T)
    if s:
        pal = set(_norm(s["texto"]))
        if not (pal and pal <= e["_pantalla"]):            # la escena ya lo muestra en grande: sin subtítulo
            dibujar_sub(img, s["texto"])
    return img


def tramo(args):
    k, a, b, destino = args
    ff = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-threads", "1", str(destino)], stdin=subprocess.PIPE)
    for f in range(a, b):
        ff.stdin.write(cuadro(f / FPS).tobytes())
        if (f - a) % 300 == 0:
            print(f"  tramo {k}: {f - a}/{b - a}", flush=True)
    ff.stdin.close(); ff.wait()
    return destino


def render(hasta, salida):
    total = int(min(hasta, TL["duracion"]) * FPS)
    n = max(1, os.cpu_count() or 4)
    partes = max(n, total // (FPS * 20))                    # tramos de ~20 s repartidos entre los núcleos
    tam = -(-total // partes)
    tmp = AQUI / "tramos"
    tmp.mkdir(exist_ok=True)
    trabajos = [(k, a, min(total, a + tam), tmp / f"t{k:04d}.mp4") for k, a in enumerate(range(0, total, tam))]
    with Pool(n) as pool:
        hechos = pool.map(tramo, trabajos, chunksize=1)
    (tmp / "lista.txt").write_text("\n".join(f"file '{h}'" for h in hechos))
    mudo = tmp / "mudo.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"), "-c", "copy", str(mudo)], check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mudo), "-i", str(AQUI / "audio_final.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total / FPS:.3f}", "-movflags", "+faststart", str(salida)], check=True)
    for h in hechos:
        h.unlink()
    print("listo", salida, f"{total / FPS:.1f} s")


def hoja(tiempos, salida):
    fotos = [cuadro(t).resize((640, 360)) for t in tiempos]
    cols = 4
    filas = -(-len(fotos) // cols)
    h = Image.new("RGB", (cols * 640, filas * 390), (0, 0, 0))
    d = ImageDraw.Draw(h)
    for k, (t, f) in enumerate(zip(tiempos, fotos)):
        x, y = (k % cols) * 640, (k // cols) * 390
        h.paste(f, (x, y))
        d.text((x + 8, y + 362), f"{int(t // 60)}:{t % 60:04.1f}  #{ESC[escena_en(t)]['n']} {ESC[escena_en(t)]['tipo']}", fill=(255, 255, 255), font=E.BEBAS(26))
    h.save(salida, quality=85)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--hoja":
        hoja([float(x) for x in sys.argv[2].split(",")], AQUI / (sys.argv[3] if len(sys.argv) > 3 else "hoja.jpg"))
    else:
        render(float(sys.argv[1]) if len(sys.argv) > 1 else 1e9, AQUI / (sys.argv[2] if len(sys.argv) > 2 else "estandares_altos_final.mp4"))
