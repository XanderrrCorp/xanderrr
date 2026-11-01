"""(01-11) Montaje de la «Edición humana» del modo Tracy: lo que ensamblar.py le agrega a cada toma cuando el plan
viene de tracy/humano.py. Con la edición humana apagada nada de esto se usa.

- Movimiento lento y sutil (acercar, alejar, paneo a un lado o plano fijo), con un poco más de acercamiento en las
  frases de énfasis. Se hace con zoompan sobre la imagen agrandada un 20 % (así no tiembla).
- El mismo tono cálido en todo el stock (el seminario sigue en blanco y negro).
- Destello suave a la entrada (el fundido usa el que ya tenía ensamblar).
- Subtítulo blanco en Bebas Neue con la palabra clave en amarillo.
- Texto grande animado en los momentos clave, con 4 estilos que rotan entre videos (la huella del video).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
FUENTE = Path(__file__).resolve().parent.parent / "fuentes" / "BebasNeue-Regular.ttf"
AMARILLO, BLANCO, NEGRO, ROJO = (255, 226, 31), (255, 255, 255), (0, 0, 0), (214, 40, 40)
PREESCALA = 1.2                       # la imagen se agranda antes de moverla (movimiento suave, sin saltos)
COLOR_CALIDO = "colorbalance=rs=0.05:gs=0.015:bs=-0.05:rm=0.04:gm=0.01:bm=-0.04,eq=saturation=0.93:contrast=1.03"
DESTELLO_S = 0.3
GRANDE_EN_S, GRANDE_DUR_S = 0.15, 2.6


def filtro_movimiento(clip: dict, cuadros: int) -> str:
    """Filtro de FFmpeg (después de escalar a 1920x1080) con el movimiento de la toma; '' si va fija."""
    m = clip.get("movimiento") or "fijo"
    if m == "fijo" or cuadros < 2:
        return ""
    z = max(1.01, min(1.15, float(clip.get("zoom") or 1.05)))
    n = cuadros - 1
    a = f"(on/{n})"                                      # avance de 0 a 1 en la toma
    # suave al empezar y al terminar (como un operador de cámara): 0.5-0.5*cos(pi*a)
    s = f"(0.5-0.5*cos(PI*{a}))"
    centro_x, centro_y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if m == "acercar":
        zoom, x, y = f"1+({z - 1:.4f})*{s}", centro_x, centro_y
    elif m == "alejar":
        zoom, x, y = f"{z:.4f}-({z - 1:.4f})*{s}", centro_x, centro_y
    else:                                              # paneo: un poco de zoom fijo y se desliza de lado
        zp = max(z, 1.06)
        ida = s if m == "paneo_der" else f"(1-{s})"
        zoom, x, y = f"{zp:.4f}", f"(iw-iw/zoom)*{ida}", centro_y
    gw, gh = int(W * PREESCALA) // 2 * 2, int(H * PREESCALA) // 2 * 2
    return (f",scale={gw}:{gh}:flags=bicubic,zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={W}x{H}:fps={FPS},"
            f"setsar=1")


def filtro_toma(clip: dict, cuadros: int, color_calido: bool = True) -> str:
    """Lo que va después de ESCALA en la toma (sin el blanco y negro del seminario, que ya pone ensamblar)."""
    f = ""
    if clip["tipo"] == "stock" and color_calido:
        f += "," + COLOR_CALIDO
    f += filtro_movimiento(clip, cuadros)
    if clip.get("transicion") == "destello":
        f += f",fade=t=in:st=0:d={DESTELLO_S}:color=white"
    return f


# ------------------------------------------------------------------ subtítulo con la palabra en amarillo

def png_resaltado(texto: str, palabra: str | None, destino: Path, tam: int = 118) -> Path:
    """Como el subtítulo de siempre (Bebas Neue, borde negro, sombra), pero blanco con `palabra` en amarillo."""
    fuente = ImageFont.truetype(str(FUENTE), tam)
    borde = 7
    medir = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = medir.textbbox((0, 0), texto, font=fuente, stroke_width=borde)
    ancho, alto = caja[2] - caja[0] + 2 * borde, caja[3] - caja[1] + 2 * borde
    im = Image.new("RGBA", (min(ancho, W - 40), alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    objetivo = _norm(palabra) if palabra else None
    x = borde - caja[0]
    y = borde - caja[1]
    espacio = medir.textlength(" ", font=fuente)
    for k, w in enumerate(texto.split(" ")):
        color = AMARILLO if objetivo and _norm(w).strip("¿?¡!.,;:«»\"'") == objetivo else BLANCO
        d.text((x + 4, y + 5), w, font=fuente, fill=(0, 0, 0, 150), stroke_width=borde, stroke_fill=(0, 0, 0, 150))
        d.text((x, y), w, font=fuente, fill=(*color, 255), stroke_width=borde, stroke_fill=(0, 0, 0, 255))
        x += medir.textlength(w, font=fuente) + espacio
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    return destino


def _norm(t: str | None) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ texto grande animado (4 estilos)

def png_grande(texto: str, estilo: int, destino: Path) -> Path:
    """1 bloque amarillo · 2 blanco con subrayado rojo · 3 etiqueta roja · 4 letras separadas de cine."""
    texto = texto.upper().strip()
    tam = 150 if len(texto) <= 18 else 112
    fuente = ImageFont.truetype(str(FUENTE), tam)
    medir = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    if estilo == 4:
        texto = " ".join(texto)                       # letras separadas
    caja = medir.textbbox((0, 0), texto, font=fuente, stroke_width=6)
    tw, th = caja[2] - caja[0], caja[3] - caja[1]
    tw = min(tw, W - 160)
    pad = 34
    im = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad + 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = pad - caja[0], pad - caja[1]
    if estilo == 1:
        d.rectangle([0, 0, im.width, th + 2 * pad], fill=(*AMARILLO, 245))
        d.text((ox, oy), texto, font=fuente, fill=(*NEGRO, 255))
    elif estilo == 2:
        d.text((ox + 5, oy + 6), texto, font=fuente, fill=(0, 0, 0, 140), stroke_width=6, stroke_fill=(0, 0, 0, 140))
        d.text((ox, oy), texto, font=fuente, fill=(*BLANCO, 255), stroke_width=6, stroke_fill=(*NEGRO, 255))
        d.rectangle([pad, th + 2 * pad, pad + tw, th + 2 * pad + 14], fill=(*ROJO, 255))
    elif estilo == 3:
        d.rounded_rectangle([0, 0, im.width, th + 2 * pad], radius=18, fill=(*ROJO, 240))
        d.text((ox, oy), texto, font=fuente, fill=(*BLANCO, 255))
    else:
        d.text((ox, oy), texto, font=fuente, fill=(*BLANCO, 255), stroke_width=3, stroke_fill=(*NEGRO, 200))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)
    return destino


def overlay_grande(entrada: str, base: str, salida: str, estilo: int, dur: float, barras: int) -> str:
    """Filtro que pone el PNG grande (entrada [k:v]) sobre `base`, con su animación, en el tercio de arriba."""
    a, b = GRANDE_EN_S, min(dur - 0.1, GRANDE_EN_S + GRANDE_DUR_S)
    y0 = barras + 70
    fade = (f"[{entrada}]format=rgba,fade=t=in:st={a:.2f}:d=0.3:alpha=1,"
            f"fade=t=out:st={max(a, b - 0.35):.2f}:d=0.35:alpha=1[gr];")
    if estilo == 1:      # entra desde la izquierda y frena
        x = f"(W-w)/2-(W*0.6)*max(0,1-(t-{a:.2f})/0.35)"
        y = f"{y0}"
    elif estilo == 2:    # sube un poco mientras aparece
        x = "(W-w)/2"
        y = f"{y0}+40*max(0,1-(t-{a:.2f})/0.4)"
    elif estilo == 3:    # entra desde la derecha
        x = f"(W-w)/2+(W*0.6)*max(0,1-(t-{a:.2f})/0.35)"
        y = f"{y0}"
    else:                # aparece quieto (de cine)
        x, y = "(W-w)/2", f"{y0}"
    return (fade + f"[{base}][gr]overlay=x='{x}':y='{y}':enable='between(t,{a:.2f},{b:.2f})'[{salida}]")


# ------------------------------------------------------------------ sonidos escasos y música por sección

def _riser(sr: int, dur: float = 1.6):
    """Sonido que sube (ruido filtrado que se abre + un tono que sube), hecho aquí: sin licencias."""
    import numpy as np

    n = int(dur * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(11)
    ruido = rng.standard_normal(n).astype(np.float32)
    # filtro pasabajos que se abre: media móvil cada vez más corta
    salida = np.zeros(n, np.float32)
    acum = 0.0
    for i in range(n):
        alfa = 0.02 + 0.5 * (i / n) ** 2
        acum += alfa * (ruido[i] - acum)
        salida[i] = acum
    f = 180 + 900 * (t / dur) ** 2
    tono = np.sin(2 * np.pi * np.cumsum(f) / sr).astype(np.float32) * 0.25
    env = ((t / dur) ** 2.2).astype(np.float32)
    x = (salida * 1.6 + tono) * env
    x[-int(0.04 * sr):] *= np.linspace(1, 0, int(0.04 * sr), dtype=np.float32)
    return x / max(1e-6, float(np.abs(x).max()))


def pista_sfx(clips: list[dict], duracion: float, ffmpeg: str, destino: Path) -> Path | None:
    """Whoosh solo en las tomas que el plan marcó (las transiciones suaves y unas pocas más) y un riser que termina
    justo donde entra cada revelación. Nunca en cada corte."""
    import wave

    import numpy as np

    from ..render import SR, _igualar, _sonido

    pista = np.zeros(int((duracion + 1) * SR), np.float32)
    hubo = False
    riser = None
    for k, c in enumerate(clips):
        t = round(int(round(c["inicio"] * FPS)) / FPS, 3)
        if c.get("whoosh") and k > 0:
            x, _ = _sonido("barrido", k % 3 + 1, ffmpeg)
            x = _igualar(np.asarray(x, np.float32), 0.16) * 0.45
            pico = int(np.argmax(np.abs(x))) if len(x) else 0
            i = int(t * SR) - min(pico, int(0.25 * SR))
            if i < 0:
                x, i = x[-i:], 0
            pista[i:i + len(x)] += x[: max(0, len(pista) - i)]
            hubo = True
        if c.get("riser") and k > 0:
            riser = riser if riser is not None else _riser(SR)
            x = riser * 0.22
            i = max(0, int(t * SR) - len(x))
            x = x[-(int(t * SR) - i):] if int(t * SR) - i < len(x) else x
            pista[i:i + len(x)] += x[: max(0, len(pista) - i)]
            hubo = True
    if not hubo:
        return None
    destino.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(pista, -1, 1) * 32767).astype("<i2").tobytes())
    return destino


MIN_TRAMO_MUSICA_S = 20.0
CRUCE_S = 1.5


def tramos_musica(clips: list[dict], pistas: dict, por_defecto: str | None, duracion: float) -> list[dict]:
    """[{inicio, fin, archivo, seccion}]: una pista por sección (gancho, cuerpo, venta, cierre). Los tramos muy
    cortos se unen con el anterior (la música no salta cada rato). Sin pista para una sección, la de siempre."""
    tramos: list[dict] = []
    for c in clips:
        s = c.get("seccion") or "cuerpo"
        if tramos and tramos[-1]["seccion"] == s:
            tramos[-1]["fin"] = c["fin"]
        else:
            tramos.append({"seccion": s, "inicio": c["inicio"], "fin": c["fin"]})
    unidos: list[dict] = []
    for t in tramos:
        if unidos and (t["fin"] - t["inicio"] < MIN_TRAMO_MUSICA_S or unidos[-1]["seccion"] == t["seccion"]) \
                and t["seccion"] != "cierre":
            unidos[-1]["fin"] = t["fin"]
        else:
            unidos.append(dict(t))
    salida = []
    for t in unidos:
        archivo = (pistas or {}).get(t["seccion"]) or por_defecto
        if archivo and Path(archivo).exists():
            salida.append({**t, "archivo": str(archivo)})
    if salida:
        salida[-1]["fin"] = duracion
    return salida


def mezclar(ffmpeg: str, mudo: Path, voz: Path, sfx: Path | None, tramos: list[dict], volumen_db: float,
            duracion: float, salida: Path) -> None:
    """Voz + sonidos + música por sección (cada pista entra y sale con un cruce suave y se agacha sola bajo la
    voz). El video va copiado tal cual."""
    import subprocess

    entradas = ["-i", str(mudo), "-i", str(voz)]
    filtro = "[1:a]aresample=48000,asplit=2[v1][guia]"
    k = 2
    if sfx:
        entradas += ["-i", str(sfx)]
        filtro += f";[v1][{k}:a]amix=inputs=2:duration=first:normalize=0[vz]"
        k += 1
    else:
        filtro += ";[v1]anull[vz]"
    if tramos:
        partes = []
        for j, t in enumerate(tramos):
            a = max(0.0, t["inicio"] - (CRUCE_S if j else 0))
            largo = max(0.5, min(duracion, t["fin"] + (CRUCE_S if j + 1 < len(tramos) else 0)) - a)
            entradas += ["-stream_loop", "-1", "-i", t["archivo"]]
            ms = int(a * 1000)
            filtro += (f";[{k}:a]aresample=48000,atrim=0:{largo:.3f},asetpts=PTS-STARTPTS,"
                       f"afade=t=in:d={CRUCE_S if j else 3}:curve=tri,"
                       f"afade=t=out:st={max(0.0, largo - (CRUCE_S if j + 1 < len(tramos) else 3)):.3f}:"
                       f"d={CRUCE_S if j + 1 < len(tramos) else 3}:curve=tri,adelay={ms}|{ms},apad[m{j}]")
            partes.append(f"[m{j}]")
            k += 1
        filtro += (f";{''.join(partes)}amix=inputs={len(partes)}:normalize=0,atrim=0:{duracion:.3f},"
                   f"lowpass=f=7500,volume={volumen_db}dB[m];"
                   f"[m][guia]sidechaincompress=threshold=0.04:ratio=2.5:attack=40:release=700[mb];"
                   f"[vz][mb]amix=inputs=2:duration=first:normalize=0[a]")
    else:
        filtro += ";[vz]anull[a]"
    cmd = [ffmpeg, "-y", "-loglevel", "error", *entradas, "-filter_complex", filtro, "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(salida)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg falló al mezclar el audio: {(r.stderr or '')[-400:]}")
