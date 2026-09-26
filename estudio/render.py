"""Motor de render (sección 6): ejecuta edl.json con Pillow + FFmpeg.

La EDL es la única fuente de verdad: aquí no se decide nada, solo se dibuja lo
que dice. El audio se mezcla SIEMPRE completo (voz + efectos) y se normaliza.
"""
from __future__ import annotations

import io
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import leer_json
from .esquemas import EDL
from .estilos import cargar_estilo
from .proyecto import CarpetaProyecto
from .tira import _barrido, _golpe, _zumbido, armar_tira, niebla, pixelar, quitar_fondo_liso

W, H, FPS, SR = 1920, 1080, 30, 48000
FUENTES = ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "DejaVuSans-Bold.ttf"]


def _fuente(tam: int):
    for f in FUENTES:
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _suave(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _sale(x: float) -> float:
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


# ------------------------------------------------------------------ recursos

def papel_arrugado(w: int, h: int, semilla: int = 5) -> Image.Image:
    rng = np.random.default_rng(semilla)
    base = np.array([236, 227, 207], np.float32)
    grano = rng.normal(0, 5, (h, w, 1)).astype(np.float32)
    manchas = np.asarray(Image.fromarray((rng.random((h // 60 + 2, w // 60 + 2)) * 255).astype("uint8"))
                         .resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(30)),
                         np.float32)[:, :, None] / 255 - 0.5
    img = np.clip(base + grano + manchas * 26, 0, 255).astype("uint8")
    papel = Image.fromarray(img, "RGB")
    # pliegues: líneas claras y oscuras muy suaves
    capa = Image.new("L", (w, h), 128)
    d = ImageDraw.Draw(capa)
    r = random.Random(semilla)
    for _ in range(18):
        x0, y0 = r.randint(-200, w), r.randint(-200, h)
        ang = r.uniform(0, math.pi)
        largo = r.randint(400, 1400)
        pts = [(x0, y0)]
        for _ in range(4):
            ang += r.uniform(-0.35, 0.35)
            x0 += int(math.cos(ang) * largo / 4)
            y0 += int(math.sin(ang) * largo / 4)
            pts.append((x0, y0))
        d.line(pts, fill=r.choice([140, 116]), width=r.randint(1, 3))
    capa = capa.filter(ImageFilter.GaussianBlur(2.2))
    luz = np.asarray(capa, np.float32)[:, :, None] / 128
    img = np.clip(np.asarray(papel, np.float32) * luz, 0, 255)
    # viñeta suave
    yy, xx = np.mgrid[0:h, 0:w]
    v = 1 - 0.18 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return Image.fromarray(np.clip(img * v[:, :, None], 0, 255).astype("uint8"), "RGB")


def _sombra(rgba: Image.Image, radio: int = 16, alfa: int = 120, desplaz=(10, 14)) -> tuple[Image.Image, tuple]:
    a = rgba.split()[-1]
    m = 2 * radio
    s = Image.new("RGBA", (rgba.width + 2 * m, rgba.height + 2 * m), (0, 0, 0, 0))
    negro = Image.new("RGBA", rgba.size, (0, 0, 0, alfa))
    s.paste(negro, (m, m), a)
    return s.filter(ImageFilter.GaussianBlur(radio)), (desplaz[0] - m, desplaz[1] - m)


def _pixelar_zonas(img: Image.Image, zonas: list, bloque: int) -> Image.Image:
    img = img.copy()
    for x0, y0, x1, y1 in zonas:
        caja = (int(x0 * img.width), int(y0 * img.height), int(x1 * img.width), int(y1 * img.height))
        img.paste(pixelar(img.crop(caja), bloque), caja[:2])
    return img


class Escenario:
    """Compone el cuadro estático de cada clip (papel + recorte o recuadro)."""

    def __init__(self, raiz: Path, papel: Image.Image, comportamiento: dict[str, str]):
        self.raiz = raiz
        self.papel = papel
        self.comportamiento = comportamiento     # modo del estilo -> recorte | recuadro
        self.cache: dict = {}

    def cuadro(self, clip: dict) -> Image.Image:
        zonas = next((e["zonas"] for e in clip["efectos"] if e["efecto"] == "pixelar"), None)
        clave = (clip["archivo"], clip["modo"], str(zonas), clip["id"])
        if clave in self.cache:
            return self.cache[clave]
        img = Image.open(self.raiz / clip["archivo"]).convert("RGB")
        if zonas:
            img = _pixelar_zonas(img, zonas, next(e.get("bloque", 26) for e in clip["efectos"] if e["efecto"] == "pixelar"))
        lienzo = self.papel.copy().convert("RGBA")
        if self.comportamiento.get(clip["modo"], "recuadro") == "recorte":
            esquina = np.asarray(img.resize((40, 24)), np.float32)
            blanco = np.mean([esquina[0, 0], esquina[0, -1], esquina[-1, 0], esquina[-1, -1]]) > 232
            caja_max = (int(W * 0.84), int(H * 0.72))
            if blanco:
                # dibujo sobre fondo blanco: se «imprime» en el papel (multiplicar)
                d = img.copy()
                d.thumbnail(caja_max, Image.Resampling.LANCZOS)
                x, y = (W - d.width) // 2, int(H * 0.50 - d.height / 2)
                zona = np.asarray(lienzo.crop((x, y, x + d.width, y + d.height)).convert("RGB"), np.float32)
                mult = zona * np.asarray(d, np.float32) / 255
                lienzo.paste(Image.fromarray(mult.astype("uint8")), (x, y))
            else:
                rec = quitar_fondo_liso(img)
                caja = rec.getbbox()
                if caja:
                    rec = rec.crop(caja)
                rec.thumbnail(caja_max, Image.Resampling.LANCZOS)
                x, y = (W - rec.width) // 2, int(H * 0.50 - rec.height / 2)
                s, (dx, dy) = _sombra(rec, 18, 110)
                lienzo.alpha_composite(s, (max(0, x + dx), max(0, y + dy)))
                lienzo.alpha_composite(rec, (x, y))
        else:
            r = random.Random(clip["id"])
            marco = 14
            d = img.resize((int(W * 0.74), int(W * 0.74 * img.height / img.width)), Image.Resampling.LANCZOS)
            conmarco = Image.new("RGBA", (d.width + 2 * marco, d.height + 2 * marco), (250, 248, 242, 255))
            conmarco.paste(d, (marco, marco))
            conmarco = conmarco.rotate(r.uniform(-1.2, 1.2), expand=True, resample=Image.Resampling.BICUBIC)
            x, y = (W - conmarco.width) // 2, int(H * 0.46 - conmarco.height / 2)
            s, (dx, dy) = _sombra(conmarco, 20, 130)
            lienzo.alpha_composite(s, (max(0, x + dx), max(0, y + dy)))
            lienzo.alpha_composite(conmarco, (x, y))
        final = lienzo.convert("RGB")
        self.cache[clave] = final
        if len(self.cache) > 6:
            self.cache.pop(next(iter(self.cache)))
        return final


def _camara(img: Image.Image, s: float, foco: tuple[float, float], dx: float = 0, dy: float = 0) -> Image.Image:
    if s <= 1.0005 and not dx and not dy:
        return img
    s = max(s, 1.0 + (0.012 if (dx or dy) else 0))
    w, h = W / s, H / s
    cx = min(max(foco[0] * W + dx, w / 2), W - w / 2)
    cy = min(max(foco[1] * H + dy, h / 2), H - h / 2)
    return img.resize((W, H), Image.Resampling.BILINEAR, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))


# ------------------------------------------------------------------ textos

def _texto_img(texto: str, tam: int, contorno: int, color=(255, 255, 255)) -> Image.Image:
    f = _fuente(tam)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    caja = d0.textbbox((0, 0), texto, font=f, stroke_width=contorno)
    im = Image.new("RGBA", (caja[2] - caja[0] + 8, caja[3] - caja[1] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - caja[0], 4 - caja[1]), texto, font=f, fill=color, stroke_width=contorno,
                            stroke_fill=(0, 0, 0))
    return im


# ------------------------------------------------------------------ sonido

def _sfx(tipo: str, variante: int) -> np.ndarray:
    rng = np.random.default_rng(100 + variante)
    if tipo == "barrido":
        return _barrido(SR, 0.55 + 0.1 * variante, rng)
    if tipo == "golpe":
        return _golpe(SR, 1.6)
    if tipo == "zumbido":
        return _zumbido(SR, 1.2)
    t = np.arange(int(SR * (0.35 if tipo == "golpe_suave" else 0.12))) / SR
    if tipo == "golpe_suave":
        f = 90 * np.exp(-t * 6) + 45
        return np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 11) * 0.6
    f0 = 660 + 80 * variante
    return np.sin(2 * math.pi * f0 * t * (1 + 1.5 * t)) * np.exp(-t * 40) * 0.5   # pop


def mezclar_audio(raiz: Path, edl: dict) -> np.ndarray:
    total = int(edl["duracion_total"] * SR) + SR
    mezcla = np.zeros(total, np.float32)
    for v in edl["pistas"]["voz"]:
        with wave.open(str(raiz / v["archivo"])) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        i = int(v["inicio"] * SR)
        mezcla[i:i + len(x)] += x[: total - i]
    for s in edl["pistas"]["sfx"]:
        tipo, var = s["variante"].rsplit("_", 1)
        x = _sfx(tipo, int(var)).astype(np.float32)
        tono = s.get("tono", 1.0)
        idx = np.arange(0, len(x) - 1, tono)
        x = np.interp(idx, np.arange(len(x)), x) * s.get("volumen", 0.7) * 0.6
        i = int(s["inicio"] * SR)
        mezcla[i:i + len(x)] += x[: max(0, total - i)]
    return mezcla


# ------------------------------------------------------------------ render

def renderizar(carpeta: CarpetaProyecto, ffmpeg: str, destino: Path | None = None, desde: float = 0.0,
               hasta: float | None = None, avisar=print) -> Path:
    raiz = carpeta.ruta
    edl = leer_json(raiz / "edl.json")
    EDL.model_validate(edl)
    proyecto = carpeta.cargar()
    estilo = cargar_estilo(proyecto.estilo)
    esc = carpeta.cargar_escenas()
    destino = destino or raiz / "render" / "final.mp4"
    destino.parent.mkdir(parents=True, exist_ok=True)
    papel_ruta = raiz / "assets" / "papel_arrugado.png"
    if not papel_ruta.exists():
        papel_ruta.parent.mkdir(parents=True, exist_ok=True)
        papel_arrugado(W, H, proyecto.semilla % 1000).save(papel_ruta)
    papel = Image.open(papel_ruta).convert("RGB").resize((W, H))
    escenario = Escenario(raiz, papel, estilo.comportamiento_montaje)

    # tira (15): bases a 1080 de alto, con niebla a los lados para centrar cualquier nivel
    tira = None
    if esc.niveles:
        armada = armar_tira(esc, estilo, raiz, seed=proyecto.semilla)
        t = armada.t
        esc_f = H / armada.normal.height
        pad = W // 2
        fondo = niebla(int(armada.normal.width * esc_f) + 2 * pad, H, t).convert("RGBA")
        bases = {}
        for nombre, img in (("n", armada.normal), ("p", armada.pixelada)):
            b = fondo.copy()
            b.alpha_composite(img.resize((int(img.width * esc_f), H), Image.Resampling.LANCZOS), (pad, 0))
            bases[nombre] = b.convert("RGB")
        cx = [int(c * esc_f) + pad for c in armada.centros_x]
        vx0, vy0, vx1, vy1 = (int(v * esc_f) for v in armada.caja_villano)
        tira = {"bases": bases, "cx": cx, "caja": (vx0 + pad, vy0, vx1 + pad, vy1),
                "g": int(t.borde_grosor * esc_f), "bloque": int(t.pixel_bloque * esc_f), "color": t.brillo_villano}

    def cuadro_tira(centro: float, pixelado: bool, bloque_revelar: int | None = None) -> Image.Image:
        base = tira["bases"]["p" if pixelado else "n"]
        x0 = int(min(max(centro - W / 2, 0), base.width - W))
        im = base.crop((x0, 0, x0 + W, H))
        if bloque_revelar and bloque_revelar > 1:
            a, b, c, d = tira["caja"]
            g = tira["g"]
            zona = im.crop((a + g - x0, b + g, c - g - x0, d - g))
            im.paste(pixelar(zona, bloque_revelar), (a + g - x0, b + g))
        return im

    subs = edl["pistas"]["subtitulos"]
    textos = edl["pistas"]["textos"]
    cache_txt: dict = {}
    clips = edl["pistas"]["escenas"]
    total = edl["duracion_total"] if hasta is None else min(hasta, edl["duracion_total"])
    n0, n1 = int(desde * FPS), int(total * FPS)

    video_tmp = destino.with_suffix(".video.mp4")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                             "-pix_fmt", "yuv420p", str(video_tmp)], stdin=subprocess.PIPE)
    temblor = random.Random(proyecto.semilla)
    ultimo: Image.Image | None = None
    ci = 0
    for n in range(n0, n1):
        tt = n / FPS
        while ci + 1 < len(clips) and clips[ci + 1]["inicio"] <= tt:
            ci += 1
        c = clips[ci]
        loc = tt - c["inicio"]
        dur = c["fin"] - c["inicio"]
        ef = {e["efecto"]: e for e in c["efectos"]}
        # --- imagen base del clip
        if c["modo"] == "tira" and tira:
            e = ef["tira_deslizar_a_nivel"]
            if e.get("pasar"):
                cen = tira["cx"][0] + (tira["cx"][-1] - tira["cx"][0]) * _suave(loc / max(0.5, dur))
            else:
                d0, d1 = e["desde"] - 1, e["hasta"] - 1
                cen = tira["cx"][d0] + (tira["cx"][d1] - tira["cx"][d0]) * _suave(loc / min(0.8, dur * 0.5))
            img = cuadro_tira(cen, e.get("villano_pixelado", True))
            if e.get("temblor") and loc > 0.8:
                amp = 5 * min(1, (loc - 0.8) / 1.5)
                img = _camara(img, 1.02, (0.5, 0.5), temblor.uniform(-amp, amp), temblor.uniform(-amp, amp))
        elif "revelar_pixelado" in ef and tira and loc < ef["revelar_pixelado"]["duracion"]:
            niv = ef["revelar_pixelado"]["nivel"] - 1
            if loc < 0.55:
                img = cuadro_tira(tira["cx"][niv], True)
            else:
                b = int(round(tira["bloque"] * (1 - _suave((loc - 0.55) / 0.4)))) or 1
                img = cuadro_tira(tira["cx"][niv], False, b if b > 1 else None)
        else:
            base = escenario.cuadro(c)
            off = ef["revelar_pixelado"]["duracion"] if "revelar_pixelado" in ef else 0.0
            p = (loc - off) / max(0.3, dur - off)
            mov = c.get("movimiento")
            s, foco = 1.0, (0.5, 0.5)
            if mov:
                foco = tuple(mov.get("punto_foco") or (0.5, 0.5))
                if mov["tipo"] == "zoom_golpe":
                    golpe = ef.get("zoom_golpe", {}).get("en", c["inicio"] + dur * 0.35) - c["inicio"]
                    s = 1.0 + (mov["a"] - 1.0) * _sale((loc - golpe) / 0.16) if loc >= golpe else 1.0
                else:
                    s = mov["de"] + (mov["a"] - mov["de"]) * _suave(p)
                if mov["tipo"] == "paneo_lento" and "paneo_lento" in ef:
                    h2 = ef["paneo_lento"]["hasta"]
                    foco = (foco[0] + (h2[0] - foco[0]) * _suave(p), foco[1] + (h2[1] - foco[1]) * _suave(p))
            if "reencuadre" in ef and tt >= ef["reencuadre"]["en"]:
                r = ef["reencuadre"]
                s = r["escala"] + 0.015 * _suave((tt - r["en"]) / max(0.5, c["fin"] - r["en"]))
                foco = tuple(r["punto_foco"])
            dx = dy = 0.0
            if "temblor_leve" in ef:
                a = ef["temblor_leve"].get("amplitud", 3)
                dx, dy = temblor.uniform(-a, a), temblor.uniform(-a, a)
            img = _camara(base, s, foco, dx, dy)
        # --- transición y destellos
        if c["transicion_entrada"] == "fundido_corto" and loc < 0.25 and ultimo is not None:
            img = Image.blend(ultimo, img, _suave(loc / 0.25))
        if "destello_rojo" in ef:
            dt = tt - ef["destello_rojo"]["en"]
            if 0 <= dt < 0.6:
                img = Image.blend(img, Image.new("RGB", (W, H), (255, 42, 42)), 0.55 * math.exp(-dt * 6))
        if any(img is v for v in escenario.cache.values()):
            img = img.copy()           # nunca escribir sobre el cuadro guardado en caché
        # --- textos en pantalla
        for t in textos:
            if t["inicio"] <= tt < t["fin"]:
                k = ("T", t["texto"])
                if k not in cache_txt:
                    cache_txt[k] = _texto_img(t["texto"], 80, 9, (255, 236, 90))
                ti = cache_txt[k]
                a = _suave((tt - t["inicio"]) / 0.12)
                if a < 1:
                    ti2 = ti.copy()
                    ti2.putalpha(ti.split()[-1].point(lambda v: int(v * a)))
                else:
                    ti2 = ti
                img.paste(ti2, ((W - ti.width) // 2, 26), ti2)
        # --- subtítulo
        for sb in subs:
            if sb["inicio"] <= tt < sb["fin"]:
                k = ("S", sb["texto"])
                if k not in cache_txt:
                    cache_txt[k] = _texto_img(sb["texto"], 64, 7)
                si = cache_txt[k]
                img.paste(si, ((W - si.width) // 2, H - 150 - si.height // 2), si)
                break
        proc.stdin.write(img.tobytes())
        ultimo = img
        if n % (FPS * 30) == 0:
            avisar(f"  render {tt / 60:.1f} / {total / 60:.1f} min")
    proc.stdin.close()
    proc.wait()

    # --- audio completo, normalizado, y unión
    mezcla = mezclar_audio(raiz, edl)[int(desde * SR):int(total * SR)]
    wav = destino.with_suffix(".mezcla.wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mezcla, -1, 1) * 32767).astype("<i2").tobytes())
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video_tmp), "-i", str(wav),
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "48000", "-shortest", str(destino)], check=True)
    video_tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    # subtítulos también como SRT
    srt = destino.with_suffix(".srt")
    with open(srt, "w", encoding="utf-8") as f:
        for i, sb in enumerate(subs, 1):
            f.write(f"{i}\n{_srt(sb['inicio'])} --> {_srt(sb['fin'])}\n{sb['texto']}\n\n")
    return destino


def _srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
