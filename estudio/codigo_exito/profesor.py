"""Escenas [PROFESOR] con el motor que ya existe (estudio/animado/profesor_anim.py: capas del dueño, boca de Rhubarb,
parpadeo, balanceo, brazo a la sien). SIN subtítulos (los pone solo Remotion, pedido del dueño) y sin viñeta ni grano
(Remotion los pone encima de TODO, así el Profesor y el stock se ven del mismo mundo).

Capas: carpeta «profesor» (PNG 1200x1200 del dueño: fondo, cuerpo, cabeza_base, ojos_*, rasgos, boca_A..H/X, bigote,
brazo_sien). Se busca en datos/codigo_exito/profesor o en la variable CODIGO_EXITO_PROFESOR. No va al repo.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from ..render import _argumentos_codificador as _cod

W, H, FPS = 1920, 1080, 30
VINO, VINO_OSC, DORADO, CREMA = (92, 22, 38), (34, 8, 16), (214, 172, 92), (244, 232, 210)


def carpeta_capas() -> Path:
    if os.environ.get("CODIGO_EXITO_PROFESOR"):
        return Path(os.environ["CODIGO_EXITO_PROFESOR"])
    from ..plataforma.db import carpeta_datos

    return carpeta_datos() / "codigo_exito" / "profesor"


def fondo() -> Image.Image:
    """terciopelo vino con luz dorada suave al centro (misma paleta del aura y del color del stock)"""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W * 0.5) / (W * 0.62)) ** 2 + ((y - H * 0.46) / (H * 0.75)) ** 2)
    k = np.clip(r, 0, 1)[..., None] ** 1.4
    centro = np.array(VINO, np.float32) * 1.25 + np.array(DORADO, np.float32) * 0.12
    borde = np.array(VINO_OSC, np.float32)
    img = centro * (1 - k) + borde * k
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def bocas_rhubarb(wav: Path, texto: str, destino: Path) -> list[tuple[float, str]]:
    """Rhubarb Lip Sync (gratis; variable RHUBARB o en el PATH). Sin Rhubarb: boca por volumen del audio."""
    if destino.exists():
        return [tuple(x) for x in json.loads(destino.read_text())]
    rh = os.environ.get("RHUBARB") or shutil.which("rhubarb")
    cues: list[tuple[float, str]] = []
    if rh:
        txt = destino.with_suffix(".txt")
        txt.write_text(texto, encoding="utf-8")
        out = destino.with_suffix(".rh.json")
        subprocess.run([rh, "-q", "-r", "phonetic", "--extendedShapes", "GHX", "--dialogFile", str(txt), "-f", "json",
                        "-o", str(out), str(wav)], check=True)
        cues = [(round(c["start"], 3), c["value"]) for c in json.loads(out.read_text())["mouthCues"]]
    else:
        import wave

        with wave.open(str(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        paso = sr // 12
        for i in range(0, len(x), paso):
            e = float(np.sqrt((x[i:i + paso] ** 2).mean() + 1e-12))
            cues.append((round(i / sr, 3), "X" if e < 0.01 else "B" if e < 0.04 else "C" if e < 0.08 else "D"))
    destino.write_text(json.dumps(cues))
    return cues


def renderizar(wav: Path, texto: str, dur: float, destino: Path, ffmpeg: str, gestos: list[tuple[float, float]] = ()) -> Path:
    """Un video mudo de `dur` s: el Profesor a la izquierda (el centro es de los subtítulos), cámara que se acerca despacio, boca con la voz."""
    from ..animado import profesor_anim as P

    if destino.exists():
        return destino
    P.CAPAS = carpeta_capas()
    if not (P.CAPAS / "cabeza_base.png").exists():
        raise FileNotFoundError(f"faltan las capas del Profesor en {P.CAPAS}")
    P._capa.cache_clear()
    cues = bocas_rhubarb(wav, texto, destino.with_suffix(".bocas.json")) if wav else []
    P._BOCAS = ([c[0] for c in cues] or [0.0], [c[1] for c in cues] or ["X"])
    base = fondo()
    tmp = destino.with_suffix(".part.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                             "-i", "-", *_cod(ffmpeg, "veryfast", "17", None), "-pix_fmt", "yuv420p", str(tmp)],
                            stdin=subprocess.PIPE)
    n = int(round(dur * FPS))
    tam = 640                                                     # a la izquierda: el centro queda para los subtítulos
    for f in range(n):
        T = f / FPS
        lienzo = base.copy()
        g = max((math.sin(math.pi * min(1, max(0, (T - a) / max(0.01, b - a)))) for a, b in gestos), default=0.0)
        entrada = min(1.0, T / 0.45)
        P.dibujar(lienzo, W * 0.2, H * 0.52, tam, T, gesto=g, entrada=1 - (1 - entrada) ** 3)
        z = 1.0 + 0.045 * T / max(1.0, dur)                       # acercamiento lento (ningún plano quieto)
        if z > 1.001:
            cw, ch = int(W / z), int(H / z)
            lienzo = lienzo.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.Resampling.BILINEAR)
        proc.stdin.write(lienzo.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg falló al hacer la escena del Profesor")
    tmp.replace(destino)
    return destino
