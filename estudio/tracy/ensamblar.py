"""Ensamblaje del modo Tracy con FFmpeg.

Por cada segmento se codifica un tramo de video:
- el clip (stock o seminario) escalado y recortado a 1920x1080, a 30 cuadros;
- recortado a la duración exacta del segmento (en cuadros, contados sobre el tiempo acumulado
  para que la suma no se corra de la voz);
- sin su audio; el seminario se mantiene en blanco y negro;
- con los subtítulos encima: PNG hechos con Pillow en Bebas Neue, centrados en la mitad de la
  pantalla (no depende de que el FFmpeg instalado traiga libass).

Luego los tramos se pegan con corte directo (sin transición). El audio es la narración, un swoosh en
cada cambio de escena y, si el canal tiene una, la música de fondo bajita en todo el video (el audio de
los clips nunca suena). Queda `render/final.mp4` + `.srt`, y una copia en la carpeta de Videos.
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


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def png_subtitulo(texto: str, destino: Path, color: str = "#FFE21F") -> Path:
    """Texto (amarillo por defecto) con borde negro en Bebas Neue, recortado a su tamaño (se centra al montar)."""
    fuente = ImageFont.truetype(str(FUENTE), TAM_SUB)
    borde = 7
    caja = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), texto, font=fuente, stroke_width=borde)
    ancho, alto = caja[2] - caja[0] + 2 * borde, caja[3] - caja[1] + 2 * borde
    im = Image.new("RGBA", (min(ancho, W - 40), alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # sombra suave debajo y luego el texto con borde
    d.text((borde - caja[0] + 4, borde - caja[1] + 5), texto, font=fuente, fill=(0, 0, 0, 150),
           stroke_width=borde, stroke_fill=(0, 0, 0, 150))
    d.text((borde - caja[0], borde - caja[1]), texto, font=fuente, fill=(*_rgb(color), 255),
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


def _codec(ffmpeg: str) -> list[str]:
    """La tarjeta NVIDIA si hay (mismo criterio que el render de siempre); si no, x264."""
    from ..render import _argumentos_codificador

    return _argumentos_codificador(ffmpeg, "veryfast", "20", None)


FUNDIDO_S = 0.4      # transición suave entre escenas (cross-fade)


def comando_tramo(ffmpeg: str, clip: dict, subs: list[tuple[Path, float, float]], salida: Path,
                  final: dict | None = None, barras: int = 0, previo: dict | None = None) -> list[str]:
    """`previo`: el clip de antes (stock o seminario). El tramo empieza fundiéndose desde la continuación
    de ese clip durante FUNDIDO_S: transición suave sin correr ningún tiempo (cada tramo dura lo mismo)."""
    """`final` (solo en la escena final): {"particulas", "voz", "presentador"?, "suscribete"?: (carpeta, en_s)}."""
    n = _cuadros(clip["fin"]) - _cuadros(clip["inicio"])
    dur = n / FPS
    cmd = [ffmpeg, "-y", "-loglevel", "error"]
    if clip["tipo"] in ("stock", "final"):
        cmd += ["-stream_loop", "-1"]           # por si el clip se queda corto (el fondo final va en bucle)
    cmd += ["-ss", f"{clip['desde']:.3f}", "-t", f"{dur + 1:.3f}", "-i", str(clip["archivo"])]
    if clip["tipo"] == "final" and final:
        k = 1
        from .escena_final import BUCLE_PARTICULAS_S

        cmd += ["-stream_loop", "-1", "-ss", f"{clip['inicio'] % BUCLE_PARTICULAS_S:.3f}", "-t", f"{dur + 1:.3f}",
                "-i", str(final["particulas"])]
        cmd += ["-ss", f"{_cuadros(clip['inicio']) / FPS:.3f}", "-t", f"{dur + 0.5:.3f}", "-i", str(final["voz"])]
        # setpts renumera los cuadros tras la vuelta del bucle; apad alarga la voz con silencio: si las
        # ondas se acababan un cuadro antes que el tramo, FFmpeg se quedaba guardando cuadros hasta
        # llenar la memoria
        filtro = (f"[0:v]{ESCALA},setpts=N/({FPS}*TB),hue=s=0,eq=brightness=-0.05:contrast=1.08,format=gbrp[b];"
                  f"[1:v]scale={W}:{H},fps={FPS},setpts=N/({FPS}*TB),format=gbrp[p];"
                  f"[b][p]blend=all_mode=screen,format=yuv420p[f0];"
                  f"[2:a]asetpts=PTS-STARTPTS,apad,showfreqs=s=520x140:mode=bar:ascale=sqrt:fscale=log:win_size=2048:colors=white,"
                  f"fps={FPS},format=rgba,colorkey=black:0.3:0.1[ondas];"
                  f"[f0][ondas]overlay=x=W-w-70:y=H-h-{40 + barras}:eof_action=pass[f1]")
        actual, k = "f1", 3
        if final.get("presentador"):
            cmd += ["-i", str(final["presentador"])]
            filtro += f";[{actual}][{k}:v]overlay=x=20:y=H-h[f2]"
            actual, k = "f2", k + 1
        if final.get("suscribete"):
            carpeta, en = final["suscribete"]
            cmd += ["-framerate", str(FPS), "-i", str(Path(carpeta) / "s_%03d.png")]
            filtro += (f";[{k}:v]setpts=PTS-STARTPTS+{en:.3f}/TB[sus];"
                       f"[{actual}][sus]overlay=x=W-w-10:y={10 + barras}:eof_action=pass:"
                       f"enable='between(t,{en:.3f},{en + 3.5:.3f})'[f3]")
            actual, k = "f3", k + 1
        filtro += f";[{actual}]null[v0]"
        primero = k
    else:
        filtro = f"[0:v]{ESCALA}" + (",hue=s=0" if clip["tipo"] == "seminario" else "") + "[v0]"
        primero = 1
    if previo and previo["tipo"] in ("stock", "seminario") and dur > FUNDIDO_S + 0.3:
        sigue = previo["desde"] + (_cuadros(previo["fin"]) - _cuadros(previo["inicio"])) / FPS
        if previo["tipo"] == "stock":
            cmd += ["-stream_loop", "-1"]
        cmd += ["-ss", f"{sigue:.3f}", "-t", f"{FUNDIDO_S + 0.5:.3f}", "-i", str(previo["archivo"])]
        filtro = filtro.replace("[v0]", "[base0]", 1)
        filtro += (f";[{primero}:v]{ESCALA}" + (",hue=s=0" if previo["tipo"] == "seminario" else "")
                   + f",format=yuv420p,setpts=PTS-STARTPTS,settb=AVTB,fps={FPS},trim=duration={FUNDIDO_S + 0.1:.3f}[ant];"
                   f"[base0]format=yuv420p,setpts=PTS-STARTPTS,settb=AVTB,fps={FPS}[act];"
                   f"[ant][act]xfade=transition=fade:duration={FUNDIDO_S}:offset=0[v0]")
        primero += 1
    for png, _, _ in subs:
        cmd += ["-i", str(png)]
    for j, (_, a, b) in enumerate(subs):
        filtro += (f";[v{j}][{primero + j}:v]overlay=x=(W-w)/2:y=(H-h)/2:"
                   f"enable='between(t,{a:.3f},{b:.3f})'[v{j + 1}]")
    salida_v = f"v{len(subs)}"
    if barras:
        # franjas negras de cine arriba y abajo (encima de todo, menos los subtítulos que van al centro)
        filtro += (f";[{salida_v}]drawbox=x=0:y=0:w=iw:h={barras}:color=black:t=fill,"
                   f"drawbox=x=0:y=ih-{barras}:w=iw:h={barras}:color=black:t=fill[cine]")
        salida_v = "cine"
    cmd += ["-filter_complex", filtro, "-map", f"[{salida_v}]", "-frames:v", str(n), "-an",
            *_codec(ffmpeg), "-pix_fmt", "yuv420p", "-r", str(FPS), str(salida)]
    return cmd


def _subs_del_tramo(clip: dict, trozos: list[dict], carpeta: Path, color: str = "#FFE21F"
                    ) -> list[tuple[Path, float, float]]:
    a0, b0 = _cuadros(clip["inicio"]) / FPS, _cuadros(clip["fin"]) / FPS
    salida = []
    for k, t in enumerate(trozos):
        a, b = max(t["inicio"], a0), min(t["fin"], b0)
        if b - a < 1 / FPS:
            continue
        png = carpeta / f"sub_{k:04d}.png"
        if not png.exists():
            png_subtitulo(_limpiar_texto(t["texto"]), png, color)
        salida.append((png, a - a0, b - a0))
    return salida


def cortes_de_escena(clips: list[dict]) -> list[float]:
    """Dónde cambia lo que se ve: cada corte entre clips, menos dentro de la escena final (ahí el fondo
    sigue igual y no hay cambio de escena)."""
    return [round(_cuadros(c["inicio"]) / FPS, 3) for prev, c in zip(clips, clips[1:])
            if not (prev["tipo"] == "final" and c["tipo"] == "final")]


def pista_swoosh(cortes: list[float], duracion: float, ffmpeg: str, destino: Path) -> Path | None:
    """Un «swoosh» en cada cambio de escena (su punto más fuerte cae justo en el corte). Usa los de la
    biblioteca con licencia (tipo «barrido») o el sintético de Xandart."""
    import wave

    import numpy as np

    from ..render import SR, _igualar, _sonido

    if not cortes:
        return None
    pista = np.zeros(int((duracion + 1) * SR), np.float32)
    for k, t in enumerate(cortes):
        x, _ = _sonido("barrido", k % 3 + 1, ffmpeg)
        x = _igualar(np.asarray(x, np.float32), 0.2) * 0.5
        pico = int(np.argmax(np.abs(x))) if len(x) else 0
        i = int(t * SR) - min(pico, int(0.25 * SR))
        if i < 0:
            x, i = x[-i:], 0
        pista[i:i + len(x)] += x[: max(0, len(pista) - i)]
    pista = np.clip(pista, -1, 1)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((pista * 32767).astype("<i2").tobytes())
    return destino


def _procesos() -> int:
    from ..render import _procesos as procesos

    return procesos(None)


def ensamblar(carpeta: CarpetaProyecto, ffmpeg: str, avisar=print, progreso=None, musica: str | None = None,
              volumen_musica_db: float = -24.0, preset: dict | None = None) -> Path:
    preset = preset or {}
    clips = leer_json(carpeta.ruta / "clips.json")["clips"]
    ors = leer_json(carpeta.ruta / "audio" / "oraciones.json")
    duracion = float(ors["duracion"])
    trozos = trozos_subtitulo(ors["oraciones"], duracion)
    dir_r = carpeta.ruta / "render"
    dir_t = dir_r / "tracy"
    color = preset.get("color_subtitulos") or "#FFE21F"
    dir_s = dir_t / f"subs_{color.lstrip('#').lower()}"
    dir_t.mkdir(parents=True, exist_ok=True)
    dir_s.mkdir(parents=True, exist_ok=True)
    hechos = [0]
    posicion = {c["id"]: k for k, c in enumerate(clips)}
    extra: dict = {}
    finales = [c for c in clips if c["tipo"] == "final"]
    if finales:
        from .escena_final import cuadros_suscribete, momentos_suscribete, particulas, preparar_presentador

        avisar("Preparando la escena final (partículas, presentador, botón)…")
        extra = {"particulas": particulas(ffmpeg), "voz": carpeta.ruta / "audio" / "voz.wav",
                 "presentador": preparar_presentador(preset.get("presentador"), dir_t / "presentador.png"),
                 "carpeta_sus": cuadros_suscribete(),
                 "momentos": momentos_suscribete(finales, float(preset.get("suscribete_cada_s", 60)))}
        if not extra["presentador"]:
            avisar(f"  no encontré la imagen del presentador en «{preset.get('presentador')}»: la escena final va sin él")

    def hacer(clip: dict) -> Path:
        salida = dir_t / f"tramo_{clip['id']:04d}.mp4"
        subs = _subs_del_tramo(clip, trozos, dir_s, color)
        final = None
        if clip["tipo"] == "final":
            en = extra["momentos"].get(clip["id"])
            final = {"particulas": extra["particulas"], "voz": extra["voz"], "presentador": extra["presentador"],
                     "suscribete": (extra["carpeta_sus"], en) if en is not None else None}
        barras = int(preset.get("alto_barras", 130)) if preset.get("barras_cine", True) else 0
        k = posicion[clip["id"]]
        previo = clips[k - 1] if k > 0 and not (clip["tipo"] == "final" and clips[k - 1]["tipo"] == "final") else None
        r = subprocess.run(comando_tramo(ffmpeg, clip, subs, salida, final, barras, previo), capture_output=True, text=True,
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
    # único efecto de sonido: un swoosh en cada cambio de escena
    swoosh = pista_swoosh(cortes_de_escena(clips), duracion, ffmpeg, dir_t / "swoosh.wav")
    musica = Path(musica) if musica else None
    entradas = ["-i", str(mudo), "-i", str(voz)]
    filtro = "[1:a]aresample=48000[v1]"
    if swoosh:
        entradas += ["-i", str(swoosh)]
        filtro += f";[v1][2:a]amix=inputs=2:duration=first:normalize=0[vz]"
    else:
        filtro += ";[v1]anull[vz]"
    if musica and musica.exists():
        # música de fondo suave durante TODO el video: bajita, sin agudos chillones, en bucle, con
        # entrada y salida suaves, y se agacha sola mientras hay voz. La voz siempre manda.
        avisar(f"Poniendo la narración, los swoosh y la música de fondo ({musica.name})…")
        k = len(entradas) // 2
        entradas += ["-stream_loop", "-1", "-i", str(musica)]
        sale = max(0.0, duracion - 3)
        filtro += (f";[1:a]aresample=48000[guia];"
                   f"[{k}:a]aresample=48000,lowpass=f=7500,volume={volumen_musica_db}dB,"
                   f"afade=t=in:d=3,afade=t=out:st={sale:.3f}:d=3,atrim=0:{duracion:.3f}[m];"
                   f"[m][guia]sidechaincompress=threshold=0.04:ratio=2.5:attack=40:release=700[mb];"
                   f"[vz][mb]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        if musica:
            avisar(f"  no encontré la música de fondo en «{musica}»: el video sale solo con la voz")
        avisar("Poniendo la narración y los swoosh…")
        filtro += ";[vz]anull[a]"
    cmd = [ffmpeg, "-y", "-loglevel", "error", *entradas, "-filter_complex", filtro, "-map", "0:v", "-map", "[a]"]
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
