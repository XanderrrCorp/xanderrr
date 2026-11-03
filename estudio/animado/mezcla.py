"""Sonido (reutilizable): efectos de sfx/ por eventos de escenas.json + música de musica/ con ducking + master a -14 LUFS
(pico ≤ -1 dBTP). Uso: python mezcla.py [video_sin_mezcla.mp4] [salida.mp4]   (sin video: solo audio_mezcla.wav)"""
import json
import math
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent.parent
FF = "/usr/bin/ffmpeg"
SR = 44100
PLAN = json.loads((AQUI / "escenas.json").read_text(encoding="utf-8"))
TL = json.loads((AQUI / "timeline.json").read_text(encoding="utf-8"))
VOL = {"lapiz": -20, "clic": -12, "tick": -18, "tono": -18, "whoosh": -22, "pop": -20}     # dB respecto a la voz


def leer(ruta):
    r = subprocess.run([FF, "-v", "error", "-i", str(ruta), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def eventos():
    """[(t, nombre, duración o None)]"""
    ev = []
    for e in PLAN["escenas"]:
        a, d = e["inicio"], e["duracion"]
        tipo = e["tipo"]
        if tipo == "tabla" and e.get("modo") == "escribir":
            ev.append((a + 0.5, "lapiz", max(2.0, d * 0.8)))
        elif tipo == "libreta":
            ev.append((a + 0.6, "lapiz", max(1.5, min(3.5, d * 0.55))))
        elif tipo == "historia" and e.get("escena") == "natalia_escribe":
            ev.append((a + 0.5, "lapiz", max(2.0, d * 0.6)))
        elif tipo == "comentario":
            ev.append((a + 0.8, "lapiz", 1.8)); ev.append((a + 2.9, "pop", None))
        elif tipo == "puertas":
            ev.append((a + 2.9, "clic", None))
        elif tipo == "pausa":
            t0 = e["temporizador_desde"]
            ev += [(t0, "tono", None), (t0 + 3.0, "tono", None)] + [(t0 + k, "tick", None) for k in (0.5, 1.5, 2.5)]
        elif tipo == "comentarios":
            ev += [(a + 0.5 + i * 0.9, "pop", None) for i in range(3)]
        elif tipo == "test":
            n = len(e["preguntas"]); paso = max(2.5, (d - 1.5) / n)
            ev += [(a + 0.5 + k * paso + 1.1, "pop", None) for k in range(n)]
        elif tipo == "encuesta":
            ev += [(a + 0.6 + k * 0.25, "pop", None) for k in range(len(e["opciones"]))]
        elif tipo == "cuatro_palabras":
            base = 1.6 if e.get("revelar") else 0.4
            paso = 0.45 if e.get("revelar") else 0.35
            ev += [(a + base + k * paso, "pop", None) for k in range(4)]
        elif tipo == "membresia":
            ev += [(a + 2.4, "clic", None)] + [(a + 2.8 + j * 0.5, "pop", None) for j in range(3)]
        elif tipo == "trampas":
            ev.append((a + d * 0.82, "whoosh", None))
        # transiciones grandes: inicio de cada fila, de los CTA de venta/membresía y de la pantalla final
        if (tipo == "tabla" and e.get("modo") == "fila") or tipo in ("mivalor", "membresia", "pantalla_final", "cuatro_palabras"):
            ev.append((max(0.0, a - 0.25), "whoosh", None))
    for sc in (PLAN.get("progreso") or {}).get("secciones", []):
        if "completa" in sc:
            ev.append((sc["completa"], "pop", None))
    return sorted(ev)


def pista_sfx(total):
    sonidos = {n: leer(AQUI / "sfx" / f"{n}.wav") for n in VOL}
    pista = np.zeros(int(total * SR) + SR, np.float32)
    for t, n, dur in eventos():
        s = sonidos[n] * (10 ** (VOL[n] / 20))
        if dur:                                            # el lápiz: en bucle o recortado, con fundidos cortos
            k = int(dur * SR)
            s = np.tile(s, k // len(s) + 1)[:k].copy()
            f = min(len(s) // 4, int(0.08 * SR))
            s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)
        i = int(t * SR)
        j = min(len(pista), i + len(s))
        pista[i:j] += s[:j - i]
    ruta = AQUI / "sfx_pista.wav"
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(pista, -1, 1) * 32767).astype(np.int16).tobytes())
    return ruta


def pistas_musica():
    carpeta = AQUI / "musica"
    return sorted(p for p in carpeta.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".flac")) if carpeta.exists() else []


def mezclar(salida_wav):
    total = TL["duracion"]
    sfx = pista_sfx(total)
    voz = AQUI / "audio_final.wav"
    musica = pistas_musica()
    entradas = ["-i", str(voz), "-i", str(sfx)]
    filtro = "[0:a]aresample=44100,asplit=2[voz][lado];[1:a]aresample=44100[sfx];"
    if musica:
        for m in musica:
            entradas += ["-i", str(m)]
        cadena = "[2:a]aresample=44100,aformat=channel_layouts=mono[m0];"
        prev = "m0"
        for k in range(1, len(musica)):                     # encadenadas con cruce de 3 s
            cadena += f"[{k + 2}:a]aresample=44100,aformat=channel_layouts=mono[n{k}];[{prev}][n{k}]acrossfade=d=3[m{k}];"
            prev = f"m{k}"
        filtro += cadena + (f"[{prev}]aloop=loop=-1:size=2e9,atrim=0:{total:.2f},volume=-26dB[mus];"
                            # ducking: baja ~6 dB más cuando hay voz y sube suave en las pausas
                            "[mus][lado]sidechaincompress=threshold=0.02:ratio=4:attack=80:release=900:makeup=1[musd];"
                            "[voz][sfx][musd]amix=inputs=3:normalize=0:duration=first[mix]")
    else:
        filtro += "[voz][sfx]amix=inputs=2:normalize=0:duration=first[mix]"
        filtro = filtro.replace("asplit=2[voz][lado]", "anull[voz]")
    crudo = AQUI / "mezcla_cruda.wav"
    subprocess.run([FF, "-y", "-v", "error"] + entradas + ["-filter_complex", filtro, "-map", "[mix]", "-ac", "2", str(crudo)], check=True)
    # master a -14 LUFS, pico -1 dBTP (dos pasadas)
    r = subprocess.run([FF, "-hide_banner", "-i", str(crudo), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr).group(0))
    af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    subprocess.run([FF, "-y", "-v", "error", "-i", str(crudo), "-af", af, str(salida_wav)], check=True)
    v = subprocess.run([FF, "-hide_banner", "-i", str(salida_wav), "-af", "loudnorm=I=-14:TP=-1:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    f = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", v.stderr).group(0))
    print(f"master: {f['input_i']} LUFS · pico {f['input_tp']} dBTP · música: {[p.name for p in musica] or 'ninguna (carpeta musica/ vacía)'}")
    return salida_wav


if __name__ == "__main__":
    wav = mezclar(AQUI / "audio_mezcla.wav")
    if len(sys.argv) > 2:
        subprocess.run([FF, "-y", "-v", "error", "-i", sys.argv[1], "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", sys.argv[2]], check=True)
        print("listo", sys.argv[2])
