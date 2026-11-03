"""Shorts verticales (1080x1920) a partir del video largo (reutilizable).
Cada Short = gancho nuevo (voz MiniMax) + 1-2 fragmentos del audio original, recompuesto en vertical: El Profesor
arriba, la escena original al centro (entera, no recortada) y subtítulos grandes en la mitad de abajo. Al final, 2 s de
«Video completo en el canal» con la miniatura del video largo."""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render as R  # noqa: E402  (escenas, cámara y transiciones del video largo)
import escenas as E  # noqa: E402
import profesor_anim as PR  # noqa: E402

AQUI = R.AQUI
FF = R.FF
SR = 44100
VW, VH, FPS = 1080, 1920, 30
TL = R.TL
RHUBARB = None
for p in (AQUI.parent / "rhubarb").rglob("rhubarb"):
    if p.is_file():
        RHUBARB = str(p)
LEYENDA = "Contenido inspirado en las ideas de Brian Tracy. Voz generada con IA. Este canal no está afiliado a Brian Tracy."

SHORTS = [
    {"n": 1, "partes": [(7, "Test rápido", None), (8, "Ahora viene algo", "cruce tu línea.")],
     "titulo": "Mujer, ¿cuántas de estas has hecho por un hombre? 😳",
     "desc": "Responde con sí o no. Si dices sí a dos, estás aceptando menos de lo que mereces."},
    {"n": 2, "partes": [(28, "El día que alguien cruce", "es lo que enseña."), (8, "Puedes decir cien veces", "cuando no lo cumplen.")],
     "titulo": "Las 4 palabras que toda mujer debe decir cuando no la respetan",
     "desc": "Sin explicaciones, sin discutir, sin pedir perdón."},
    {"n": 3, "partes": [(6, "Piensa en dos piedras", "como diamante o como piedra del camino.")],
     "titulo": "¿Eres diamante o piedra del camino? Mujer, escucha esto",
     "desc": "Las dos salieron de la misma tierra. La diferencia es la presión que aguantaste."},
    {"n": 4, "partes": [(18, "Haz esta prueba", "saben querer desde arriba.")],
     "titulo": "La prueba para saber qué amigas te quieren de verdad (mujeres)",
     "desc": "¿Quién se alegró por ti? ¿Quién llegó cuando estuviste mal?"},
]


def leer(ruta):
    r = subprocess.run([FF, "-v", "error", "-i", str(ruta), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


VOZ = leer(AQUI / "audio_final.wav")
_E = np.sqrt(np.convolve(VOZ ** 2, np.ones(441) / 441, mode="same"))[::441]       # energía cada 10 ms


def silencio_cerca(t, ventana=0.8):
    a, b = max(0, int((t - ventana) * 100)), min(len(_E) - 1, int((t + ventana) * 100))
    return (a + int(np.argmin(_E[a:b]))) / 100 if b > a else t


def tiempo(seg_id, texto, final=False):
    s = next(x for x in TL["segmentos"] if x["id"] == seg_id)
    total = " ".join(s["parrafos"])
    if texto is None:
        return s["fin"] if final else s["inicio"]
    k = total.find(texto)
    if k < 0:
        raise SystemExit(f"no encuentro «{texto}» en el segmento {seg_id}")
    if final:
        k += len(texto)
    t = s["inicio"] + (s["fin"] - s["inicio"]) * k / len(total)
    return silencio_cerca(t)


def texto_entre(seg_id, a, b):
    s = next(x for x in TL["segmentos"] if x["id"] == seg_id)
    total = " ".join(s["parrafos"])
    i = total.find(a) if a else 0
    j = total.find(b) + len(b) if b else len(total)
    return total[i:j]


def escribir_wav(ruta, x):
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def bocas_de(wav, texto, nombre):
    out = AQUI / "shorts" / f"{nombre}_bocas.json"
    if not out.exists():
        txt = AQUI / "shorts" / f"{nombre}.txt"
        txt.write_text(texto, encoding="utf-8")
        subprocess.run([RHUBARB, "-q", "-r", "phonetic", "--extendedShapes", "GHX", "--dialogFile", str(txt), "-f", "json",
                        "-o", str(out), str(wav)], check=True)
    return [[c["start"], c["value"]] for c in json.loads(out.read_text())["mouthCues"]]


def armar(sh):
    """Audio del Short + mapa de tiempo (del Short al video largo) + subtítulos + bocas."""
    ganchos = json.loads((AQUI / "shorts" / "ganchos.json").read_text())
    g_txt = ganchos[str(sh["n"])]
    g = leer(AQUI / "shorts" / "audio" / f"gancho_{sh['n']}.mp3")
    trozos, mapa, subs, bocas = [g, np.zeros(int(0.35 * SR), np.float32)], [], [], []
    t = 0.0
    dur_g = len(g) / SR
    subs += [(t + a, t + b, x) for a, b, x in repartir(g_txt, dur_g)]
    gwav = AQUI / "shorts" / f"gancho_{sh['n']}.wav"
    escribir_wav(gwav, g)
    bocas += [[t + a, v] for a, v in bocas_de(gwav, g_txt, f"gancho_{sh['n']}")]
    mapa.append((0.0, dur_g + 0.35, None, g_txt))
    t = dur_g + 0.35
    ts, vs = PR.bocas()
    for seg_id, a, b in sh["partes"]:
        t0, t1 = tiempo(seg_id, a), tiempo(seg_id, b, final=True)
        trozo = VOZ[int(t0 * SR):int(t1 * SR)].copy()
        f = int(0.03 * SR); trozo[:f] *= np.linspace(0, 1, f); trozo[-f:] *= np.linspace(1, 0, f)
        trozos += [trozo, np.zeros(int(0.3 * SR), np.float32)]
        txt = texto_entre(seg_id, a, b)
        subs += [(t + x, t + y, z) for x, y, z in repartir(txt, t1 - t0)]
        bocas += [[t + (tt - t0), v] for tt, v in zip(ts, vs) if t0 <= tt < t1]
        mapa.append((t, t + (t1 - t0) + 0.3, t0, txt))
        t += (t1 - t0) + 0.3
    audio = np.concatenate(trozos + [np.zeros(int(2.2 * SR), np.float32)])           # +2 s de cierre
    return audio, mapa, subs, sorted(bocas), t


def repartir(texto, dur):
    """Subtítulos de 2 a 4 palabras (grandes), repartidos por letras."""
    pal = texto.split()
    grupos, act = [], []
    for p in pal:
        act.append(p)
        if len(act) >= 4 or (len(act) >= 2 and re.search(r"[.,;:?!»\"]$", p)):
            grupos.append(" ".join(act)); act = []
    if act:
        grupos.append(" ".join(act))
    letras = sum(len(x) + 1 for x in grupos)
    out, t = [], 0.0
    for gtxt in grupos:
        d = dur * (len(gtxt) + 1) / letras
        out.append((t, t + d, gtxt)); t += d
    return out


def fondo_vertical():
    return E.vignette_bg((58, 26, 38), E.NIGHT).resize((VW, VH), Image.Resampling.BICUBIC)


FONDO = None
MINI = None


def cuadro(T, mapa, subs, bocas_ts, bocas_vs, fin_habla, titulo_gancho):
    global FONDO, MINI
    if FONDO is None:
        FONDO = fondo_vertical()
        MINI = Image.open(AQUI / "miniatura.png").convert("RGB").resize((900, 506))
    img = FONDO.copy()
    d = ImageDraw.Draw(img, "RGBA")
    E.particulas(d, T, 24, E.GOLD, 0.7)
    if T >= fin_habla:                                            # cierre: «Video completo en el canal»
        q = E.ease((T - fin_habla) / 0.4)
        img.paste(MINI, (90, 640))
        d.rounded_rectangle([90, 640, 990, 1146], 18, outline=E.GOLD, width=6)
        d.text((VW / 2, 470), "VIDEO COMPLETO", font=E.BEBAS(130), fill=E.rgba(E.CREAM, 255 * q), anchor="mm")
        d.text((VW / 2, 1290), "EN EL CANAL", font=E.BEBAS(130), fill=E.rgba(E.GOLD, 255 * q), anchor="mm")
        return img
    # escena del video largo, entera, en el centro
    parte = next((m for m in mapa if m[0] <= T < m[1]), mapa[-1])
    if parte[2] is None:                                          # gancho: tarjeta de texto propia
        f = E.BEBAS(110)
        filas = E.envolver(d, titulo_gancho.upper(), f, 960)
        y = 960 - (len(filas) - 1) * 60
        for k, fila in enumerate(filas):
            p = E.back((T - k * 0.25) / 0.45)
            if p > 0:
                d.text((VW / 2, y), fila, font=E.BEBAS(int(110 * min(1.1, p))), fill=E.rgba(E.GOLD if k % 2 else E.CREAM, 255 * min(1, p)), anchor="mm")
            y += 120
    else:
        Tl = parte[2] + (T - parte[0])
        i = R.escena_en(Tl)
        esc = R.escena_lista(i, Tl - R.ESC[i]["inicio"]).resize((VW, 608), Image.Resampling.BILINEAR)
        sombra = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
        ImageDraw.Draw(sombra).rectangle([0, 676, VW, 1290], fill=(0, 0, 0, 140))
        img = img.convert("RGBA"); img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(20))); img = img.convert("RGB")
        img.paste(esc, (0, 660))
        d = ImageDraw.Draw(img, "RGBA")
        d.line([(0, 660), (VW, 660)], fill=E.GOLD, width=4); d.line([(0, 1268), (VW, 1268)], fill=E.GOLD, width=4)
    # El Profesor arriba (con su boca)
    import bisect
    k = bisect.bisect_right(bocas_ts, T) - 1
    boca = bocas_vs[k] if k >= 0 else "X"
    PR.boca_en = lambda _t, b=boca: b
    gesto = E.ease(T / 0.4) * (1 - E.ease((T - 3.0) / 0.4))
    PR.dibujar(img, VW / 2, 330, 520, T, gesto=gesto)
    # subtítulos grandes en la mitad de abajo
    s = next((x for x in subs if x[0] <= T < x[1]), None)
    if s:
        d = ImageDraw.Draw(img, "RGBA")
        f = E.BEBAS(118)
        filas = E.envolver(d, s[2].upper(), f, 980)
        y = 1480 - (len(filas) - 1) * 60
        for fila in filas:
            d.text((VW / 2, y), fila, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0))
            y += 120
    return img


def hacer(sh):
    out_dir = AQUI / "shorts"
    audio, mapa, subs, bocas, fin_habla = armar(sh)
    wav = out_dir / f"short_{sh['n']}.wav"
    escribir_wav(wav, audio)
    dur = len(audio) / SR
    ts, vs = [b[0] for b in bocas], [b[1] for b in bocas]
    destino = out_dir / f"short_{sh['n']}.mp4"
    ff = subprocess.Popen([FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                           "-i", str(wav), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-af", "loudnorm=I=-14:TP=-1", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(destino)],
                          stdin=subprocess.PIPE)
    ganchos = json.loads((out_dir / "ganchos.json").read_text())
    for f in range(int(dur * FPS)):
        ff.stdin.write(cuadro(f / FPS, mapa, subs, ts, vs, fin_habla, ganchos[str(sh["n"])]).tobytes())
    ff.stdin.close(); ff.wait()
    return destino, dur


if __name__ == "__main__":
    from multiprocessing import Pool
    cuales = [int(x) for x in sys.argv[1:]] or [s["n"] for s in SHORTS]
    with Pool(4) as pool:
        res = pool.map(hacer, [s for s in SHORTS if s["n"] in cuales])
    lineas = []
    for sh, (dest, dur) in zip([s for s in SHORTS if s["n"] in cuales], res):
        print(dest.name, f"{dur:.1f} s")
        lineas.append(f"SHORT {sh['n']} ({dur:.0f} s)\nTítulo: {sh['titulo']}\nDescripción: {sh['desc']} Video completo en el canal.\n"
                      f"#Shorts #amorpropio #mujeres\n{LEYENDA}\n")
    (AQUI / "shorts" / "shorts.txt").write_text("\n".join(lineas), encoding="utf-8")
