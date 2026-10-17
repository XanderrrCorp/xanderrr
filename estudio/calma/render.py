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
from .trazo import BLANCO, GRIS, NEGRO, VERDE, camino, factor_temblor, figura, fijar_estilo, raya

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


LAVADO = 0.72          # «lavado:»: cuánto se acerca al blanco (los diagramas encima se leen bien)


def fondo(tipo: str) -> np.ndarray:
    clave = f"{tipo}|{factor_temblor():.2f}"
    if clave in _FONDOS:
        return _FONDOS[clave]
    if tipo.startswith("lavado:"):
        base = fondo(tipo[len("lavado:"):]).astype(np.float32)
        img = (base * (1 - LAVADO) + 255 * LAVADO).astype(np.uint8)
    elif tipo.startswith("archivo:"):                               # el papel de otro canal o un fondo pintado
        img = cv2.imread(tipo[len("archivo:"):], cv2.IMREAD_COLOR)
        if img is None:
            return fondo("blanco")
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    elif tipo.startswith("color:"):
        hx = tipo[len("color:"):].lstrip("#")
        try:
            r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return fondo("blanco")
        img = np.empty((H, W, 3), np.uint8)
        img[:] = (b, g, r)
    else:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{_fondo_svg(tipo)}</svg>'
        img = svg_a_rgba(svg, W, H)[:, :, :3]
    _FONDOS[clave] = np.ascontiguousarray(img)
    return _FONDOS[clave]


# ------------------------------------------------------------------ ambiente (17-10): partículas y luz

PARTICULAS = ("lluvia", "nieve", "ceniza", "polvo", "hojas", "chispas", "burbujas")
LUCES = ("dia", "noche", "atardecer", "tormenta")


def _azar(n: int, semilla: int) -> np.ndarray:
    return np.random.default_rng(semilla).random((n, 4))


def particulas(cuadro: np.ndarray, tipo: str, t: float, semilla: int = 0) -> None:
    """Lluvia, nieve, ceniza… dibujadas en el cuadro según el tiempo (sin estado: el mismo t da el mismo cuadro)."""
    if tipo not in PARTICULAS:
        return
    aa = cv2.LINE_AA
    if tipo == "lluvia":
        r = _azar(110, semilla)
        for x0, y0, v, k in r:
            y = (y0 * (H + 200) + t * (1500 + 500 * v)) % (H + 200) - 100
            x = (x0 * (W + 300) - (y + 100) * 0.25) % (W + 300) - 150
            largo = 30 + 26 * k
            cv2.line(cuadro, (int(x), int(y)), (int(x - largo * 0.25), int(y - largo)), (175, 150, 125), 3, aa)
        return
    if tipo in ("nieve", "ceniza", "polvo"):
        n, vel, color, radio = {"nieve": (80, 90, (255, 255, 255), 7), "ceniza": (70, 60, (130, 130, 135), 5),
                                "polvo": (60, 40, (150, 190, 215), 4)}[tipo]
        r = _azar(n, semilla)
        for x0, y0, v, k in r:
            y = (y0 * (H + 40) + t * vel * (0.6 + v)) % (H + 40) - 20
            x = (x0 * W + 40 * math.sin(t * (0.5 + v) + k * 6.28) + (t * 25 if tipo == "polvo" else 0)) % W
            rr = int(radio * (0.6 + k))
            cv2.circle(cuadro, (int(x), int(y)), rr, color, -1, aa)
            if tipo == "nieve":
                cv2.circle(cuadro, (int(x), int(y)), rr, (215, 210, 205), 1, aa)
        return
    if tipo == "hojas":
        r = _azar(16, semilla)
        for x0, y0, v, k in r:
            y = (y0 * (H + 80) + t * (70 + 50 * v)) % (H + 80) - 40
            x = (x0 * W + 90 * math.sin(t * (0.7 + v) + k * 6.28)) % W
            color = ((110, 175, 120), (90, 160, 230), (80, 130, 200))[int(k * 3) % 3]
            cv2.ellipse(cuadro, (int(x), int(y)), (16, 8), (t * 90 * (v - 0.5) + k * 360) % 360, 0, 360, color, -1, aa)
        return
    if tipo == "chispas":
        r = _azar(40, semilla)
        for x0, y0, v, k in r:
            y = H - ((y0 * (H + 40) + t * (120 + 120 * v)) % (H + 40))
            x = (x0 * W + 30 * math.sin(t * 2 + k * 6.28)) % W
            cv2.circle(cuadro, (int(x), int(y)), int(3 + 4 * k), (70, 150, 250), -1, aa)
        return
    r = _azar(26, semilla)                               # burbujas
    for x0, y0, v, k in r:
        y = H - ((y0 * (H + 60) + t * (90 + 80 * v)) % (H + 60)) + 30
        x = (x0 * W + 25 * math.sin(t * 1.5 + k * 6.28)) % W
        cv2.circle(cuadro, (int(x), int(y)), int(8 + 14 * k), (225, 200, 170), 3, aa)


def luz(cuadro: np.ndarray, tipo: str, t: float) -> np.ndarray:
    """Tinte del fondo: noche azulada, atardecer cálido, tormenta gris con algún relámpago."""
    if tipo == "noche":
        return (cuadro.astype(np.float32) * (0.82, 0.72, 0.66)).astype(np.uint8)
    if tipo == "atardecer":
        return (cuadro.astype(np.float32) * (0.86, 0.93, 1.0) + (0, 6, 18)).clip(0, 255).astype(np.uint8)
    if tipo == "tormenta":
        f = (cuadro.astype(np.float32) * 0.8).astype(np.uint8)
        fase = t % 5.3
        if fase < 0.08 or 0.16 < fase < 0.22:            # relámpago: dos destellos cortos cada ~5 s
            return cv2.addWeighted(f, 0.4, np.full_like(f, 255), 0.6, 0)
        return f
    return cuadro


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


SIN_SOMBRA = ("imagen", "texto", "titulo_tema", "flecha", "corchete", "circulo_rojo", "x_roja", "chulo",
              "lineas_movimiento", "ondas", "lluvia", "nieve", "viento", "vapor", "zzz", "rayo", "estrellas")
PARALLAX_FONDO = 0.4      # el fondo sigue el 40 % del zoom de cámara: se siente la profundidad
PANEO = 22                # px que el fondo se desliza de lado durante una escena (el personaje no)


def _camara(datos: dict, esc: dict, t: float) -> tuple[float, float, float, float, float]:
    dx, dy = temblor_pantalla(esc.get("temblor", []), t)
    z, fx, fy = empujon_camara(esc.get("empujon", []), t)
    zd = _deriva(datos, esc, t)
    if zd > 1.0005:                                    # la deriva se centra en la mitad de la pantalla
        fx, fy = (fx * (z - 1) + 960 * (zd - 1)) / max(1e-6, (z - 1) + (zd - 1)), \
                 (fy * (z - 1) + 540 * (zd - 1)) / max(1e-6, (z - 1) + (zd - 1))
        z = z * zd
    return z, fx, fy, dx, dy


def _fondo_con_ambiente(datos: dict, esc: dict, t: float, camara=None) -> np.ndarray:
    """El fondo de la escena; con profundidad, se mueve menos que lo de adelante y se desliza de lado."""
    base = fondo(esc.get("fondo", "blanco"))
    amb = esc.get("ambiente") or {}
    if camara is not None:
        z, fx, fy, dx, dy = camara
        p = (t - esc["inicio"]) / max(0.1, esc["fin"] - esc["inicio"])
        lado = (1 if int(esc.get("id", 0)) % 2 else -1) * PANEO * (min(1.0, max(0.0, p)) - 0.5) * 2
        zb = max(1 + (z - 1) * PARALLAX_FONDO, 1 + (PANEO + 8) * 2 / W)
        m = np.array([[zb, 0, fx - zb * fx + dx * 0.5 + lado], [0, zb, fy - zb * fy + dy * 0.5]], np.float32)
        cuadro = cv2.warpAffine(base, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    else:
        cuadro = base.copy()
    if amb.get("luz") in LUCES:
        cuadro = luz(cuadro, amb["luz"], t)
    if amb.get("particulas"):
        particulas(cuadro, amb["particulas"], t, int(esc.get("id", 0)))
    return cuadro


def cuadro_en(datos: dict, t: float) -> np.ndarray:
    video = datos.get("video", {})
    fijar_estilo(bool(video.get("trazo_limpio")))
    sombras = bool(video.get("sombras"))
    esc = next((e for e in datos["escenas"] if e["inicio"] <= t < e["fin"]), datos["escenas"][-1])
    z, fx, fy, dx, dy = _camara(datos, esc, t)
    profundidad = bool(video.get("parallax")) and esc.get("tipo") != "cuadricula"
    cuadro = _fondo_con_ambiente(datos, esc, t, (z, fx, fy, dx, dy) if profundidad else None)
    for el in esc["elementos"]:                       # en el orden del JSON: el último queda encima
        a = estado_en(el, t, esc["fin"])
        if not a.visible or a.escala <= 0.01:
            continue
        base = escala_maxima(el)
        img, ancla = sprite(el["pieza"], a.estado, base, sombra=sombras and el["pieza"] not in SIN_SOMBRA)
        if profundidad:                                # la cámara se aplica a cada pieza (el fondo ya va aparte)
            _pegar(cuadro, img, ancla, fx + z * (a.x - fx) + dx, fy + z * (a.y - fy) + dy, a.escala / base * z, a.giro)
        else:
            _pegar(cuadro, img, ancla, a.x, a.y, a.escala / base, a.giro)
    if not profundidad and (abs(dx) > 0.3 or abs(dy) > 0.3 or z > 1.0005):
        m = np.array([[z, 0, fx - z * fx + dx], [0, z, fy - z * fy + dy]], np.float32)
        cuadro = cv2.warpAffine(cuadro, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if esc.get("comentario"):
        cuadro = _comentario(cuadro, esc, t)
    return cuadro


def _comentario(cuadro: np.ndarray, esc: dict, t: float) -> np.ndarray:
    """(17-10) El cuadro de comentario que se escribe solo (el mismo de Peligro Tropical), encima de todo."""
    from PIL import Image

    from ..render_receta import comentario

    ef = {**esc["comentario"], "dur": max(0.5, esc["fin"] - esc["inicio"])}
    img = comentario(Image.fromarray(cuadro[:, :, ::-1]), ef, t - esc["inicio"])
    return np.ascontiguousarray(np.asarray(img)[:, :, ::-1])


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
