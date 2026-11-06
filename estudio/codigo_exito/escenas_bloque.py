"""Bloques [PROFESOR] con las ESCENAS de los primeros videos de Código del Éxito (estudio/animado: tipografía, frase
sobre fondo, libreta, número de la regla, dos columnas, preguntas, comentario, camino, tabla…) y El Profesor entrando
de lado o en la esquina. Ninguna escena pasa de ~9 s, la cámara siempre se mueve (acercamiento + golpe de zoom cada
3,5 s) y entre escenas va un corte con movimiento. SIN subtítulos (los pone Remotion) y sin viñeta ni grano (Remotion
los pone encima de todo).

Plan de un bloque (lo arma Claude o, en la prueba, a mano): [{"tipo", "inicio" (s dentro del bloque), "profesor":
"lado"|"esquina"|None, ...campos de la escena}], el fin de cada escena es el inicio de la siguiente.
"""
from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

from PIL import Image

from .profesor import bocas_rhubarb, carpeta_capas

W, H, FPS = 1920, 1080, 30
XF = 0.4                                       # corte con movimiento entre escenas
TRANS = ["empuje", "zoom", "fundido", "barrido"]


def carpeta_fuentes() -> Path:
    if os.environ.get("CODIGO_EXITO_FUENTES"):
        return Path(os.environ["CODIGO_EXITO_FUENTES"])
    from ..plataforma.db import carpeta_datos

    propia = carpeta_datos() / "codigo_exito" / "fuentes"
    return propia if (propia / "BebasNeue-Regular.ttf").exists() else Path(__file__).resolve().parent / "fuentes"  # las del repo (OFL)


def _motor():
    """el motor viejo se importa como lo usan sus archivos («import escenas as E»): con su carpeta en la ruta"""
    import importlib
    import sys

    carpeta = str(Path(__file__).resolve().parent.parent / "animado")
    if carpeta not in sys.path:
        sys.path.insert(0, carpeta)
    E = importlib.import_module("escenas")
    importlib.import_module("escenas_extra")              # registran sus escenas en E.ESCENAS
    importlib.import_module("escenas_perseguir")
    P = importlib.import_module("profesor_anim")

    E.F = carpeta_fuentes()
    P.CAPAS = carpeta_capas()
    return E, P


def camara(E, img, n, dur, t):
    """acercamiento/alejamiento del 10 %, paneo de lado y golpe suave de zoom cada 3,5 s (de los primeros videos)"""
    prog = E.ease_io(t / max(1.0, dur))
    z = 1.0 + 0.10 * (prog if n % 2 == 0 else 1 - prog)
    fase = (t % 3.5) / 3.5
    if t > 1.0:
        z += 0.03 * math.exp(-fase * 6) * (1 - math.exp(-fase * 40))
    px = (1 if n % 3 == 0 else -1 if n % 3 == 1 else 0.5) * 70 * (prog - 0.5)
    py = 18 * math.sin(t * 0.7 + n)
    w, h = W / z, H / z
    x0 = min(max(0.0, (W - w) / 2 + px * (z - 1) * 6), W - w)
    y0 = min(max(0.0, (H - h) / 2 + py * (z - 1) * 6), H - h)
    return img.resize((W, H), Image.Resampling.BILINEAR, box=(x0, y0, x0 + w, y0 + h))


def transicion(E, a, b, q, tipo):
    from PIL import ImageDraw

    q = E.ease_io(q)
    if tipo == "empuje":
        out = Image.new("RGB", (W, H)); dx = int(W * q)
        out.paste(a, (-dx, 0)); out.paste(b, (W - dx, 0))
        return out
    if tipo == "zoom":
        z = 1 + 0.25 * q
        w, h = W / z, H / z
        return Image.blend(a.resize((W, H), Image.Resampling.BILINEAR, box=((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2)), b, q)
    if tipo == "barrido":
        out = a.copy(); x = int(W * q)
        out.paste(b.crop((0, 0, x, H)), (0, 0))
        ImageDraw.Draw(out).rectangle([x - 14, 0, x + 14, H], fill=E.GOLD)
        return out
    return Image.blend(a, b, q)


def completar(plan: list[dict], dur: float) -> list[dict]:
    out = []
    for k, e in enumerate(plan):
        fin = plan[k + 1]["inicio"] if k + 1 < len(plan) else dur
        out.append({**e, "n": k + 1, "fin": fin, "duracion": round(fin - e["inicio"], 3)})
    return out


def pantalla(plan: list[dict]) -> list[tuple[float, float, set[str]]]:
    """palabras que cada escena muestra en grande (para no repetirlas en el subtítulo)"""
    import re
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", s.lower())
        return set(re.findall(r"\w+", "".join(c for c in s if not unicodedata.combining(c))))
    out = []
    for e in plan:
        textos = [x[0] if isinstance(x, list) else x for x in e.get("lineas", [])] + [e.get("frase", ""), e.get("titulo", "") if isinstance(e.get("titulo"), str) else " ".join(e.get("titulo") or [])]
        out.append((e["inicio"], e["fin"], norm(" ".join(textos).replace("*", ""))))
    return out


def renderizar(plan: list[dict], wav: Path | None, texto: str, dur: float, destino: Path, ffmpeg: str,
               gestos: list[tuple[float, float]] = ()) -> Path:
    if destino.exists():
        return destino
    E, P = _motor()
    if not (P.CAPAS / "cabeza_base.png").exists():
        raise FileNotFoundError(f"faltan las capas del Profesor en {P.CAPAS}")
    P._capa.cache_clear()
    cues = bocas_rhubarb(wav, texto, destino.with_suffix(".bocas.json")) if wav else []
    P._BOCAS = ([c[0] for c in cues] or [0.0], [c[1] for c in cues] or ["X"])
    esc = completar(plan, dur)

    def gesto(T):
        g = 0.0
        for a, b in gestos:
            if a - 0.35 <= T <= b + 0.35:
                g = max(g, min(E.ease((T - a + 0.35) / 0.35), E.ease((b + 0.35 - T) / 0.35)))
        return g

    def escena(i, t):
        e = esc[i]
        return camara(E, E.dibujar(e, t, e.get("tabla")), e["n"], e["duracion"], t)

    def profe(img, i, T):
        e = esc[i]
        modo = e.get("profesor")
        if not modo:
            return
        t = T - e["inicio"]
        previo = esc[i - 1].get("profesor") if i > 0 else None
        entrada = 1.0 if previo == modo else E.back(t / 0.5)
        if modo == "lado":
            P.dibujar(img, 390, 540, 640, T, gesto=gesto(T), entrada=entrada)
        else:
            P.dibujar(img, 1765, 205, 250, T, gesto=gesto(T), entrada=entrada)   # arriba a la derecha: abajo van los subtítulos

    tmp = destino.with_suffix(".part.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", str(tmp)],
                            stdin=subprocess.PIPE)
    for f in range(int(round(dur * FPS))):
        T = f / FPS
        i = max(k for k, e in enumerate(esc) if e["inicio"] <= T + 1e-6)
        img = escena(i, T - esc[i]["inicio"])
        tl = esc[i]["fin"] - T
        if tl < XF and i + 1 < len(esc):
            img = transicion(E, img, escena(i + 1, 0.05), 1 - tl / XF, TRANS[i % len(TRANS)])
        profe(img, i, T)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg falló al hacer las escenas del Profesor")
    tmp.replace(destino)
    return destino
