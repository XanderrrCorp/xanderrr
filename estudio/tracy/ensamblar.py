"""Ensamblaje del modo Tracy con FFmpeg.

Por cada segmento se codifica un tramo de video:
- el clip (stock o seminario) escalado y recortado a 1920x1080, a 30 cuadros;
- recortado a la duración exacta del segmento (en cuadros, contados sobre el tiempo acumulado
  para que la suma no se corra de la voz);
- sin su audio; el seminario se mantiene en blanco y negro;
- con los subtítulos encima: PNG hechos con Pillow en Bebas Neue, centrados en la mitad de la
  pantalla (no depende de que el FFmpeg instalado traiga libass).

Luego los tramos se pegan con corte directo (sin transición). El audio es la narración y, si el
canal tiene una, la música de fondo bajita (el audio de los clips nunca suena). Queda `render/final.mp4` + `.srt`, y una copia en la carpeta de Videos.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import leer_json
from ..proyecto import CarpetaProyecto

W, H, FPS = 1920, 1080, 30
FUENTE = Path(__file__).resolve().parent.parent / "fuentes" / "BebasNeue-Regular.ttf"
TAM_SUB = 118
MAX_PALABRAS, MAX_CARACTERES = 4, 24
ESCALA = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"


# ------------------------------------------------------------------ subtítulos

def trozos_subtitulo(oraciones: list[dict], duracion: float) -> list[dict]:
    """Frases cortas (hasta 4 palabras / 24 letras) con su tiempo real, cortadas en la puntuación."""
    trozos: list[dict] = []
    for o in oraciones:
        actual: list[dict] = []
        pal = o.get("palabras") or []
        for k, w in enumerate(pal):
            actual.append(w)
            texto = " ".join(x["p"] for x in actual)
            ultimo = k == len(pal) - 1
            corte = w["p"].endswith((",", ";", ":", ".", "?", "!", "…", "—"))
            siguiente = pal[k + 1]["p"] if not ultimo else ""
            if ultimo or corte or len(actual) >= MAX_PALABRAS or len(texto) + 1 + len(siguiente) > MAX_CARACTERES:
                trozos.append({"texto": texto, "inicio": actual[0]["inicio"], "fin": actual[-1]["fin"]})
                actual = []
    # cada trozo se queda hasta que empieza el siguiente (sin parpadeos), como mucho 0,6 s de más
    for k, t in enumerate(trozos):
        sig = trozos[k + 1]["inicio"] if k + 1 < len(trozos) else duracion
        t["fin"] = round(min(max(t["fin"], t["inicio"] + 0.25) + 0.6, sig), 3)
    return [t for t in trozos if t["fin"] > t["inicio"]]


def _limpiar_texto(texto: str) -> str:
    return texto.strip().rstrip(".,;:").strip().upper()     # «¿…?» y «¡…!» se quedan


def png_subtitulo(texto: str, destino: Path) -> Path:
    """Texto blanco con borde negro en Bebas Neue, recortado a su tamaño (se centra al montar)."""
    fuente = ImageFont.truetype(str(FUENTE), TAM_SUB)
    borde = 7
    caja = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto, font=fuente, stroke_width=borde)
    ancho, alto = caja[2] - caja[0] + 2 * borde, caja[3] - caja[1] + 2 * borde
    im = Image.new("RGBA", (min(ancho, W - 40), alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # sombra suave debajo y luego el texto con borde
    d.text((borde - caja[0] + 4, borde - caja[1] + 5), texto, font=fuente, fill=(0, 0, 0, 150),
           stroke_width=borde, stroke_fill=(0, 0, 0, 150))
    d.text((borde - caja[0], borde - caja[1]), texto, font=fuente, fill=(255, 255, 255, 255),
           stroke_width=borde, stroke_fill=(0, 0, 0, 255))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    return destino


def srt(trozos: list[dict], destino: Path) -> Path:
    def reloj(t: float) -> str:
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    lineas = []
    for k, t in enumerate(trozos, 1):
        lineas += [str(k), f"{reloj(t['inicio'])} --> {reloj(t['fin'])}", t["texto"], ""]
    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino


# ------------------------------------------------------------------ tramos

def _cuadros(t: float) -> int:
    return int(round(t * FPS))


def comando_tramo(ffmpeg: str, clip: dict, subs: list[tuple[Path, float, float]], salida: Path) -> list[str]:
    n = _cuadros(clip["fin"]) - _cuadros(clip["inicio"])
    dur = n / FPS
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    if clip["tipo"] == "stock":
        cmd += ["-stream_loop", "-1"]           # por si el clip se queda corto por décimas
    cmd += ["-ss", f"{clip['desde']:.3f}", "-t", f"{dur + 1:.3f}", "-i", str(clip["archivo"])]
    for png, _, _ in subs:
        cmd += ["-i", str(png)]
    filtro = f"[0:v]{ESCALA}" + (",hue=s=0" if clip["tipo"] == "seminario" else "") + "[v0]"
    for k, (_, a, b) in enumerate(subs, 1):
        filtro += (f";[v{k - 1}][{k}:v]overlay=x=(W-w)/2:y=(H-h)/2:"
                   f"enable='between(t,{a:.3f},{b:.3f})'[v{k}]")
    cmd += ["-filter_complex", filtro, "-map", f"[v{len(subs)}]", "-frames:v", str(n), "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            str(salida)]
    return cmd


def _subs_del_tramo(clip: dict, trozos: list[dict], carpeta: Path) -> list[tuple[Path, float, float]]:
    a0, b0 = _cuadros(clip["inicio"]) / FPS, _cuadros(clip["fin"]) / FPS
    salida = []
    for k, t in enumerate(trozos):
        a, b = max(t["inicio"], a0), min(t["fin"], b0)
        if b - a < 1 / FPS:
            continue
        png = carpeta / f"sub_{k:04d}.png"
        if not png.exists():
            png_subtitulo(_limpiar_texto(t["texto"]), png)
        salida.append((png, a - a0, b - a0))
    return salida


def _procesos() -> int:
    from ..render import _procesos as procesos

    return procesos(None)


def ensamblar(carpeta: CarpetaProyecto, ffmpeg: str, avisar=print, progreso=None, musica: str | None = None,
              volumen_musica_db: float = -24.0) -> Path:
    clips = leer_json(carpeta.ruta / "clips.json")["clips"]
    ors = leer_json(carpeta.ruta / "audio" / "oraciones.json")
    duracion = float(ors["duracion"])
    trozos = trozos_subtitulo(ors["oraciones"], duracion)
    dir_r = carpeta.ruta / "render"
    dir_t = dir_r / "tracy"
    dir_s = dir_t / "subs"
    dir_t.mkdir(parents=True, exist_ok=True)
    dir_s.mkdir(parents=True, exist_ok=True)
    hechos = [0]

    def hacer(clip: dict) -> Path:
        salida = dir_t / f"tramo_{clip['id']:04d}.mp4"
        subs = _subs_del_tramo(clip, trozos, dir_s)
        r = subprocess.run(comando_tramo(ffmpeg, clip, subs, salida), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0 or not salida.exists():
            raise RuntimeError(f"FFmpeg falló en el segmento {clip['id']}: {(r.stderr or '')[-400:]}")
        hechos[0] += 1
        if progreso:
            progreso(hechos[0] / len(clips))
        return salida

    avisar(f"Armando {len(clips)} segmentos a 1920x1080…")
    with ThreadPoolExecutor(max_workers=max(1, _procesos())) as grupo:
        tramos = list(grupo.map(hacer, clips))
    lista = dir_t / "lista.txt"
    lista.write_text("".join(f"file '{t.as_posix()}'\n" for t in tramos), encoding="utf-8")
    mudo = dir_t / "video_mudo.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c", "copy", str(mudo)], check=True, capture_output=True)
    final = dir_r / "final.mp4"
    tmp = dir_r / "final.tmp.mp4"
    voz = carpeta.ruta / "audio" / "voz.wav"
    musica = Path(musica) if musica else None
    if musica and musica.exists():
        # música de fondo suave: bajita, sin agudos chillones, en bucle con entrada y salida suaves,
        # y se agacha sola mientras hay voz (sube apenas en las pausas). La voz siempre manda.
        avisar(f"Poniendo la narración y la música de fondo ({musica.name})…")
        sale = max(0.0, duracion - 3)
        filtro = (f"[1:a]asplit=2[voz][guia];"
                  f"[2:a]aresample=48000,lowpass=f=5500,volume={volumen_musica_db}dB,"
                  f"afade=t=in:d=3,afade=t=out:st={sale:.3f}:d=3,atrim=0:{duracion:.3f}[m];"
                  f"[m][guia]sidechaincompress=threshold=0.02:ratio=4:attack=30:release=600[mb];"
                  f"[voz][mb]amix=inputs=2:duration=first:normalize=0[a]")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(mudo), "-i", str(voz),
               "-stream_loop", "-1", "-i", str(musica), "-filter_complex", filtro,
               "-map", "0:v", "-map", "[a]"]
    else:
        if musica:
            avisar(f"  no encontré la música de fondo en «{musica}»: el video sale solo con la voz")
        avisar("Poniendo la narración…")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(mudo), "-i", str(voz), "-map", "0:v", "-map", "1:a"]
    subprocess.run(cmd + ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)],
                   check=True, capture_output=True)
    os.replace(tmp, final)
    srt(trozos, final.with_suffix(".srt"))
    return final


def entregar(carpeta: CarpetaProyecto, final: Path) -> Path:
    """Copia el video (y su .srt) a la carpeta de Videos, como los demás videos de Xandart."""
    from ..pipeline import carpeta_videos
    from ..proyecto import slugificar

    destino = carpeta_videos() / f"{slugificar(carpeta.cargar().titulo)[:60]}.mp4"
    shutil.copy(final, destino)
    shutil.copy(final.with_suffix(".srt"), destino.with_suffix(".srt"))
    return destino
