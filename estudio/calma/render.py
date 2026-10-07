"""Del escenas.json al MP4: cada cuadro se arma pegando las piezas ya dibujadas (caché) con OpenCV,
y ffmpeg lo codifica (la tarjeta NVIDIA si hay). Solo cortes secos entre escenas.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

from .movimientos import empujon_camara, escala_maxima, estado_en, temblor_pantalla
from .raster import sprite, svg_a_rgba
from .trazo import BLANCO, GRIS, NEGRO, VERDE, camino, figura, raya

W, H = 1920, 1080


# ------------------------------------------------------------------ fondos

def _fondo_svg(tipo: str) -> str:
    from .escenarios import ESCENARIOS

    if tipo in ESCENARIOS:
        return ESCENARIOS[tipo]()
    if tipo == "blanco" or tipo not in ("calle", "campo"):
        return f'<rect width="{W}" height="{H}" fill="{BLANCO}"/>'
    partes = [f'<rect width="{W}" height="{H}" fill="#EEF5FA"/>']
    for i, (cx, cy, k) in enumerate(((330, 190, 1.0), (1500, 140, 0.8), (1020, 250, 0.6))):
        nube = []
        for j, (dx, dy, r) in enumerate(((-70, 10, 50), (-10, -20, 66), (60, 0, 54), (110, 18, 38))):
            from .trazo import elipse

            nube.append(figura(elipse(cx + dx * k, cy + dy * k, r * k, r * k * 0.86, n=26), f"nube{i}{j}", BLANCO))
        partes += nube
    if tipo == "calle":
        partes += [f'<rect y="760" width="{W}" height="{H - 760}" fill="#B9B9B9"/>',
                   raya([(-10, 760), (W + 10, 760)], "acera"),
                   f'<rect y="700" width="{W}" height="60" fill="#DADADA"/>',
                   raya([(-10, 700), (W + 10, 700)], "acera2")]
        for i in range(6):
            x = 60 + i * 340
            partes.append(f'<path d="{camino([(x, 920), (x + 180, 920)], f"linea{i}")}" stroke="{BLANCO}" '
                          f'stroke-width="18" stroke-linecap="round" fill="none"/>')
    else:  # campo
        partes += [f'<rect y="760" width="{W}" height="{H - 760}" fill="#CFE3BF"/>', raya([(-10, 760), (W + 10, 760)], "suelo")]
        for i in range(9):
            x = 90 + i * 215 + (i % 2) * 40
            y = 830 + (i % 3) * 70
            partes.append(raya([(x - 18, y), (x - 8, y - 26), (x, y), (x + 10, y - 30), (x + 18, y)], f"pasto{i}",
                               "#4F8A3A", 6, 0.6))
    return "".join(partes)


_FONDOS: dict[str, np.ndarray] = {}


def fondo(tipo: str) -> np.ndarray:
    if tipo not in _FONDOS:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{_fondo_svg(tipo)}</svg>'
        _FONDOS[tipo] = np.ascontiguousarray(svg_a_rgba(svg, W, H)[:, :, :3])
    return _FONDOS[tipo]


# ------------------------------------------------------------------ pegar una pieza

def _pegar(cuadro: np.ndarray, img: np.ndarray, ancla: tuple[float, float], x: float, y: float,
           k: float, giro: float) -> None:
    """Pega `img` (BGRA, dibujada a la escala máxima) con su ancla en (x, y), escalada por k y girada."""
    if k <= 0.01:
        return
    h, w = img.shape[:2]
    ax, ay = ancla
    if abs(k - 1) < 1e-3 and abs(giro) < 0.05 and abs(x - round(x)) < 1e-3 and abs(y - round(y)) < 1e-3:
        x0, y0 = int(round(x - ax)), int(round(y - ay))
        parche, ox, oy = img, x0, y0
    else:
        # caja de destino que contiene la pieza transformada
        c, s = math.cos(math.radians(giro)) * k, math.sin(math.radians(giro)) * k
        esquinas = [(-ax, -ay), (w - ax, -ay), (w - ax, h - ay), (-ax, h - ay)]
        xs = [x + c * px - s * py for px, py in esquinas]
        ys = [y + s * px + c * py for px, py in esquinas]
        ox, oy = int(math.floor(min(xs))) - 1, int(math.floor(min(ys))) - 1
        bw, bh = int(math.ceil(max(xs))) - ox + 2, int(math.ceil(max(ys))) - oy + 2
        m = np.array([[c, -s, x - ox - c * ax + s * ay], [s, c, y - oy - s * ax - c * ay]], np.float32)
        parche = cv2.warpAffine(img, m, (bw, bh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                borderValue=(0, 0, 0, 0))
    ph, pw = parche.shape[:2]
    x1, y1 = max(0, ox), max(0, oy)
    x2, y2 = min(W, ox + pw), min(H, oy + ph)
    if x1 >= x2 or y1 >= y2:
        return
    p = parche[y1 - oy:y2 - oy, x1 - ox:x2 - ox]
    a = p[:, :, 3:4].astype(np.uint16)
    dst = cuadro[y1:y2, x1:x2]
    dst[:] = ((p[:, :, :3].astype(np.uint16) * a + dst.astype(np.uint16) * (255 - a) + 127) // 255).astype(np.uint8)


# ------------------------------------------------------------------ cuadro y video

def _deriva(datos: dict, esc: dict, t: float) -> float:
    """Zoom lento de cámara durante toda la escena; una escena se acerca y la siguiente se aleja."""
    d = float(datos.get("video", {}).get("deriva", 0))
    if not d or esc.get("tipo") == "cuadricula":
        return 1.0
    p = (t - esc["inicio"]) / max(0.1, esc["fin"] - esc["inicio"])
    p = min(1.0, max(0.0, p))
    k = int(esc.get("id", 0))
    return 1 + d * (p if k % 2 else 1 - p)


def cuadro_en(datos: dict, t: float) -> np.ndarray:
    esc = next((e for e in datos["escenas"] if e["inicio"] <= t < e["fin"]), datos["escenas"][-1])
    cuadro = fondo(esc.get("fondo", "blanco")).copy()
    for el in esc["elementos"]:                       # en el orden del JSON: el último queda encima
        a = estado_en(el, t, esc["fin"])
        if not a.visible or a.escala <= 0.01:
            continue
        base = escala_maxima(el)
        img, ancla = sprite(el["pieza"], a.estado, base)
        _pegar(cuadro, img, ancla, a.x, a.y, a.escala / base, a.giro)
    dx, dy = temblor_pantalla(esc.get("temblor", []), t)
    z, fx, fy = empujon_camara(esc.get("empujon", []), t)
    zd = _deriva(datos, esc, t)
    if zd > 1.0005:                                    # la deriva se centra en la mitad de la pantalla
        fx, fy = (fx * (z - 1) + 960 * (zd - 1)) / max(1e-6, (z - 1) + (zd - 1)), \
                 (fy * (z - 1) + 540 * (zd - 1)) / max(1e-6, (z - 1) + (zd - 1))
        z = z * zd
    if abs(dx) > 0.3 or abs(dy) > 0.3 or z > 1.0005:
        m = np.array([[z, 0, fx - z * fx + dx], [0, z, fy - z * fy + dy]], np.float32)
        cuadro = cv2.warpAffine(cuadro, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cuadro


def codificar_args(ffmpeg: str) -> list[str]:
    from ..render import _argumentos_codificador

    return _argumentos_codificador(ffmpeg, "veryfast", "20", None)


def _tramo(datos: dict, desde: int, hasta: int, ruta: str, ffmpeg: str) -> int:
    """Escribe los cuadros [desde, hasta) en un MP4 (corre en otro proceso)."""
    fps = int(datos.get("video", {}).get("fps", 30))
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "pipe:0", *codificar_args(ffmpeg), "-pix_fmt", "yuv420p", "-r", str(fps), ruta]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(desde, hasta):
            proc.stdin.write(cuadro_en(datos, i / fps).tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg falló: {err[-400:]}")
    return hasta - desde


def procesos() -> int:
    """Cuántos pedazos a la vez: los mismos que el render de siempre (núcleos y memoria libre)."""
    from ..render import _procesos

    return _procesos(None)


def render(datos: dict, salida: Path, ffmpeg: str, voz: Path | None = None, musica: Path | None = None,
           volumen_musica_db: float = -26.0, avisar=print, progreso=None, en_paralelo: int | None = None,
           efectos: bool = False) -> dict:
    """Escribe el MP4 armando varios pedazos a la vez (uno por proceso) y uniéndolos sin recodificar.
    Devuelve cuánto tardó (segundos) y cuántos cuadros."""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    fps = int(datos.get("video", {}).get("fps", 30))
    dur = float(datos["video"]["duracion"])
    n = int(round(dur * fps))
    inicio = time.time()
    salida.parent.mkdir(parents=True, exist_ok=True)
    mudo = salida.with_name(salida.stem + "_mudo.mp4")
    k = max(1, min(en_paralelo or procesos(), max(1, n // (fps * 4))))      # pedazos de 4 s como mínimo
    cortes = [round(n * i / k) for i in range(k + 1)]
    carpeta = salida.with_name(salida.stem + "_pedazos")
    carpeta.mkdir(exist_ok=True)
    rutas = [carpeta / f"p{i:02d}.mp4" for i in range(k)]
    if k == 1:
        _tramo(datos, 0, n, str(rutas[0]), ffmpeg)
    else:
        hechos = 0
        with ProcessPoolExecutor(max_workers=k) as grupo:
            tareas = [grupo.submit(_tramo, datos, cortes[i], cortes[i + 1], str(rutas[i]), ffmpeg) for i in range(k)]
            for f in as_completed(tareas):
                hechos += f.result()
                if progreso:
                    progreso(hechos / n)
    lista = carpeta / "lista.txt"
    lista.write_text("".join(f"file '{r.as_posix()}'\n" for r in rutas), encoding="utf-8")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(mudo)], check=True, capture_output=True)
    shutil.rmtree(carpeta, ignore_errors=True)
    t_cuadros = time.time() - inicio
    sfx = None
    if efectos:
        from . import sonidos

        sfx = salida.with_name(salida.stem + "_efectos.wav")
        sonidos.escribir(datos, dur, sfx)
    _mezclar(mudo, salida, ffmpeg, dur, voz, musica, volumen_musica_db, sfx)
    mudo.unlink(missing_ok=True)
    if sfx:
        sfx.unlink(missing_ok=True)
    total = time.time() - inicio
    avisar(f"Render: {n} cuadros en {t_cuadros:.0f} s ({k} a la vez); con el audio, {total:.0f} s en total")
    return {"cuadros": n, "segundos_cuadros": round(t_cuadros, 1), "segundos_total": round(total, 1), "procesos": k}


def _mezclar(mudo: Path, salida: Path, ffmpeg: str, dur: float, voz: Path | None, musica: Path | None,
             volumen_db: float, efectos: Path | None = None) -> None:
    """Voz al frente; la música de fondo bajita, en bucle, se agacha sola cuando habla la voz; los efectos de
    sonido (si hay) se suman al final, por debajo de la voz."""
    if not voz and not musica and not efectos:
        mudo.replace(salida)
        return
    entradas, filtro, mezcla = ["-i", str(mudo)], [], []
    if voz:
        entradas += ["-i", str(voz)]
        filtro.append(f"[1:a]aresample=48000,apad,atrim=0:{dur:.3f}[vz]")
    if musica:
        k = 2 if voz else 1
        entradas += ["-stream_loop", "-1", "-i", str(musica)]
        sale = max(0.0, dur - 2.5)
        filtro.append(f"[{k}:a]aresample=48000,lowpass=f=7000,volume={volumen_db}dB,afade=t=in:d=1.5,"
                      f"afade=t=out:st={sale:.3f}:d=2.5,atrim=0:{dur:.3f}[m]")
        if voz:
            filtro.append("[vz]asplit=2[vz1][guia];[m][guia]sidechaincompress=threshold=0.04:ratio=3:attack=30:"
                          "release=600[mb]")
            mezcla += ["[vz1]", "[mb]"]
        else:
            mezcla.append("[m]")
    elif voz:
        mezcla.append("[vz]")
    if efectos:
        k = len([e for e in entradas if e == "-i"])
        entradas += ["-i", str(efectos)]
        filtro.append(f"[{k}:a]aresample=48000,apad,atrim=0:{dur:.3f}[fx]")
        mezcla.append("[fx]")
    if len(mezcla) == 1:
        filtro.append(f"{mezcla[0]}anull[a]")
    else:
        filtro.append(f"{''.join(mezcla)}amix=inputs={len(mezcla)}:duration=first:normalize=0[a]")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", *entradas, "-filter_complex", ";".join(filtro),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{dur:.3f}", "-movflags", "+faststart", str(salida)], check=True, capture_output=True)
