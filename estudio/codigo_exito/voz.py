"""Voz MiniMax por bloque (voz del canal, velocidad 1,15) con su duración real y tiempos por frase.

Tiempos: los subtítulos por frase que devuelve MiniMax (subtitle_enable); si no llegan, Whisper local (faster-whisper);
si tampoco, repartidos por letras dentro del bloque. Después se parten en trozos cortos (1-4 palabras) para la
pantalla. Lo ya pagado no se repite: voz/NNN.mp3 + voz/info.json (si el texto del bloque no cambió).
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np

URL = "https://api.minimax.io/v1/t2a_v2"
MODELO = "speech-2.6-hd"
VOICE_ID = "moss_audio_5f02d02b-2e0e-11f1-803b-3af0d76118b0"   # voz del canal Tracy / Código del Éxito (no es secreta)
VELOCIDAD = 1.15                                               # el dueño: «habla muy lento» a 0,95
SR = 48000
PAUSA_BLOQUES = 0.6


def _sintetizar(texto: str, sesion) -> tuple[bytes, list | None, int]:
    from ..config import clave_api

    cab = {"Content-Type": "application/json"}
    clave = clave_api("MINIMAX_API_KEY")
    if clave:
        cab["Authorization"] = f"Bearer {clave}"
    cuerpo = {"model": MODELO, "text": texto, "stream": False, "language_boost": "Spanish",
              "voice_setting": {"voice_id": VOICE_ID, "speed": VELOCIDAD, "vol": 1, "pitch": 0},
              "audio_setting": {"sample_rate": 44100, "bitrate": 128000, "format": "mp3", "channel": 1},
              "subtitle_enable": True}
    ultimo = ""
    for intento in range(4):
        r = sesion.post(URL, headers=cab, data=json.dumps(cuerpo), timeout=300)
        if r.status_code == 200:
            d = r.json()
            if (d.get("base_resp") or {}).get("status_code") in (0, None) and (d.get("data") or {}).get("audio"):
                sub = None
                url_sub = (d.get("data") or {}).get("subtitle_file")
                if url_sub:
                    try:
                        sub = sesion.get(url_sub, timeout=60).json()
                    except Exception:  # noqa: BLE001 — sin subtítulos se reparten por letras
                        sub = None
                car = int((d.get("extra_info") or {}).get("usage_characters") or len(texto))
                return bytes.fromhex(d["data"]["audio"]), sub, car
            ultimo = str(d.get("base_resp"))
        else:
            ultimo = f"HTTP {r.status_code}"
        time.sleep(5 * (intento + 1))
    raise RuntimeError(f"MiniMax no devolvió audio ({ultimo})")


def leer_pcm(ruta: Path, ffmpeg: str) -> np.ndarray:
    r = subprocess.run([ffmpeg, "-v", "error", "-i", str(ruta), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768
    a = np.abs(x) > 0.01
    if not a.any():
        return x, 0.0
    i, j = int(np.argmax(a)), len(x) - int(np.argmax(a[::-1]))
    i0 = max(0, i - 480)
    return x[i0: j + 480], i0 / SR                                  # sin silencios en los bordes (y cuánto se quitó)


def frases_minimax(sub, recorte: float) -> list[dict]:
    """subtítulos de MiniMax ([{text, time_begin, time_end}] en ms) → frases en segundos dentro del bloque"""
    out = []
    for s in sub or []:
        t = (s.get("text") or "").strip()
        if t and s.get("time_end") is not None:
            out.append({"texto": t, "ini": max(0.0, s["time_begin"] / 1000 - recorte), "fin": max(0.0, s["time_end"] / 1000 - recorte)})
    return out


def frases_por_pausas(texto: str, x: np.ndarray) -> list[dict]:
    """Sin tiempos de MiniMax: cada oración se reparte por letras y el corte se corre a la pausa más cercana del audio."""
    from ..voz import SR as SR_VOZ, cortes_por_pausas

    partes = [p.strip() for p in re.split(r"(?<=[.!?:;])\s+", texto) if p.strip()]
    dur = len(x) / SR
    if len(partes) < 2:
        return [{"texto": texto, "ini": 0.0, "fin": round(dur, 3)}]
    cortes = [c / SR_VOZ * (SR_VOZ / SR) for c in cortes_por_pausas(x, [len(p) for p in partes])] if SR_VOZ == SR else None
    if cortes is None:
        cortes = [dur * sum(len(q) for q in partes[:k + 1]) / sum(len(q) for q in partes) for k in range(len(partes) - 1)]
    bordes = [0.0] + [round(c, 3) for c in cortes] + [round(dur, 3)]
    return [{"texto": p, "ini": bordes[k], "fin": bordes[k + 1]} for k, p in enumerate(partes)]


def trozos(frases: list[dict], maximo: int = 4) -> list[dict]:
    """frases → trozos cortos de 1-4 palabras (corta en comas), con su tiempo repartido por letras"""
    out = []
    for f in frases:
        palabras = f["texto"].split()
        grupos, g = [], []
        for w in palabras:
            g.append(w)
            if len(g) >= maximo or re.search(r"[,.;:!?]$", w):
                grupos.append(g); g = []
        if g:
            grupos.append(g)
        total = sum(len(" ".join(x)) for x in grupos) or 1
        t = f["ini"]
        for x in grupos:
            d = (f["fin"] - f["ini"]) * len(" ".join(x)) / total
            out.append({"texto": " ".join(x), "ini": round(t, 3), "fin": round(t + d, 3)})
            t += d
    return out


def generar(trabajo: Path, bloques: list[dict], ffmpeg: str, permiso: bool, avisar=print, sesion=None) -> dict:
    """voz/NNN.mp3 por bloque → voz/voz.wav (todo seguido) + timeline.json (inicio/fin de cada bloque y sus trozos)"""
    import requests

    sesion = sesion or requests
    d = trabajo / "voz"
    d.mkdir(parents=True, exist_ok=True)
    info_ruta = d / "info.json"
    info = json.loads(info_ruta.read_text("utf-8")) if info_ruta.exists() else {}
    faltan = [b for b in bloques if info.get(str(b["id"]), {}).get("texto") != b["texto"] or not (d / f"{b['id']:03d}.mp3").exists()]
    if faltan and not permiso:
        letras = sum(len(b["texto"]) for b in faltan)
        raise PermissionError(f"Faltan {len(faltan)} bloques de voz ({letras} letras). Se necesita permiso para gastar.")
    for b in faltan:
        avisar(f"  voz del bloque {b['id']} de {len(bloques)}…")
        mp3, sub, car = _sintetizar(b["texto"], sesion)
        (d / f"{b['id']:03d}.mp3").write_bytes(mp3)
        info[str(b["id"])] = {"texto": b["texto"], "caracteres": car, "subtitulos": sub}
        info_ruta.write_text(json.dumps(info, ensure_ascii=False, indent=1), "utf-8")
    pista, t, salida = [], 0.0, []
    for k, b in enumerate(bloques):
        x, recorte = leer_pcm(d / f"{b['id']:03d}.mp3", ffmpeg)
        dur = len(x) / SR
        frases = frases_minimax(info[str(b["id"])].get("subtitulos"), recorte) or frases_por_pausas(b["texto"], x)
        salida.append({**b, "inicio": round(t, 3), "fin": round(t + dur, 3),
                       "trozos": [{**z, "ini": round(z["ini"] + t, 3), "fin": round(min(z["fin"], dur) + t, 3)} for z in trozos(frases)]})
        pausa = PAUSA_BLOQUES if k + 1 < len(bloques) else 1.5
        pista += [x, np.zeros(int(pausa * SR), np.float32)]
        t += dur + pausa
    voz = np.concatenate(pista)
    import wave

    with wave.open(str(d / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(voz, -1, 1) * 32767).astype("<i2").tobytes())
    tl = {"duracion": round(len(voz) / SR, 3), "bloques": salida,
          "caracteres": sum(v.get("caracteres", 0) for v in info.values())}
    (trabajo / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), "utf-8")
    return tl
