"""Voz del modo Tracy: el guion completo en bloques de ≤2500 caracteres con MiniMax.

Reutiliza `VozMiniMax` (misma llamada, misma huella para no volver a pagar, mismo libro de
costos y freno). Cada bloque termina en una oración completa. Los bloques se unen en
`audio/voz.wav` con una pausa corta entre ellos y queda anotado dónde empieza cada uno
(`audio/bloques.json`) para que Whisper los alinee por separado.
"""
from __future__ import annotations

import re
import subprocess
import wave
from pathlib import Path

import numpy as np

from ..config import ConfigCostos, escribir_json, leer_json
from ..proyecto import CarpetaProyecto
from ..voz import SR, _a_pcm, recortar_silencio

MODULO = "voz_tracy"
PAUSA_ENTRE_BLOQUES_S = 0.35

_FIN_ORACION = re.compile(r"(?<=[.!?…])[\"»”')\]]*\s+")


def oraciones(texto: str) -> list[str]:
    """Oraciones del guion. Un salto de párrafo también cierra oración."""
    salida = []
    for parrafo in re.split(r"\n\s*\n|\r?\n", texto):
        parrafo = " ".join(parrafo.split())
        if not parrafo:
            continue
        salida += [o.strip() for o in _FIN_ORACION.split(parrafo) if o.strip()]
    return salida


def _partir_larga(oracion: str, maximo: int) -> list[str]:
    """Una oración de más de `maximo` caracteres (rarísimo) se corta en comas o, si no hay, en espacios."""
    piezas, actual = [], ""
    for trozo in re.split(r"(?<=[,;:])\s+", oracion):
        if len(trozo) > maximo:
            palabras, trozo_actual = trozo.split(), ""
            for p in palabras:
                if trozo_actual and len(trozo_actual) + 1 + len(p) > maximo:
                    piezas.append(trozo_actual)
                    trozo_actual = p
                else:
                    trozo_actual = f"{trozo_actual} {p}".strip()
            trozo = trozo_actual
        if actual and len(actual) + 1 + len(trozo) > maximo:
            piezas.append(actual)
            actual = trozo
        else:
            actual = f"{actual} {trozo}".strip()
    if actual:
        piezas.append(actual)
    return piezas


def bloques(texto: str, maximo: int = 2500) -> list[str]:
    """Bloques de ≤ `maximo` caracteres que terminan siempre en una oración completa."""
    salida, actual = [], ""
    for o in oraciones(texto):
        for pieza in ([o] if len(o) <= maximo else _partir_larga(o, maximo)):
            if actual and len(actual) + 1 + len(pieza) > maximo:
                salida.append(actual)
                actual = pieza
            else:
                actual = f"{actual} {pieza}".strip()
    if actual:
        salida.append(actual)
    return salida


class VozSimulada:
    """Ensayo sin gastar: un pulso de tono por palabra (≈3,8 palabras por segundo, como la
    voz real a 1,3) con silencios entre palabras y pausas más largas al final de cada oración.
    El alineador simulado lee esos pulsos del audio real, así el ensayo recorre todo el camino."""
    nombre = "simulado"
    modelo = "simulado"
    tarifa_mil = 0.0

    def huella(self, texto: str) -> str:
        import hashlib

        return "sim-" + hashlib.sha256(texto.encode()).hexdigest()[:12]

    def estimar_usd(self, texto: str) -> float:
        return 0.0

    def sintetizar(self, texto: str) -> tuple[bytes, int]:
        sr = 32000
        partes = [np.zeros(int(0.05 * sr), np.float32)]
        for i, palabra in enumerate(texto.split()):
            dur = 0.10 + 0.028 * len(palabra)
            t = np.arange(int(dur * sr)) / sr
            env = np.minimum(1, np.minimum(t, dur - t) / 0.015)
            partes.append((0.5 * np.sin(2 * np.pi * (180 + 7 * (i % 13)) * t) * env).astype(np.float32))
            pausa = 0.42 if palabra.endswith((".", "?", "!", "…")) else (0.2 if palabra.endswith((",", ";", ":")) else 0.07)
            partes.append(np.zeros(int(pausa * sr), np.float32))
        pcm = (np.concatenate(partes) * 32767).astype("<i2").tobytes()
        from ..pipeline import ffmpeg

        r = subprocess.run([ffmpeg(), "-loglevel", "error", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
                            "-f", "mp3", "-b:a", "96k", "pipe:1"], input=pcm, capture_output=True, check=True)
        return r.stdout, len(texto)


def voz_para(proveedor: str | None, preset: dict, config: ConfigCostos):
    if proveedor == "simulado":
        return VozSimulada()
    from ..voz import VozMiniMax
    from .preset import ajustes_voz

    return VozMiniMax(config, ajustes_voz(preset))


def generar_audio(carpeta: CarpetaProyecto, texto_tts: str, ffmpeg: str, voz, preset: dict,
                  config: ConfigCostos | None = None, permiso: bool = False, avisar=print) -> dict:
    """Sintetiza el guion por bloques (reanudable: lo ya pagado no se vuelve a pedir) y arma voz.wav."""
    config = config or ConfigCostos.cargar()
    libro = carpeta.libro(config)
    dir_bloques = carpeta.ruta / "audio" / "bloques"
    dir_bloques.mkdir(parents=True, exist_ok=True)
    ruta_man = carpeta.ruta / "audio" / "bloques.json"
    man = leer_json(ruta_man) if ruta_man.exists() else {}
    textos = bloques(texto_tts, preset["bloque_tts_max"])
    gastado, pista, info, t = 0.0, [], [], 0.0
    for i, txt in enumerate(textos):
        clave = f"b{i:03d}"
        h = voz.huella(txt)
        archivo = dir_bloques / f"{clave}.mp3"
        if not (man.get(clave, {}).get("huella") == h and archivo.exists()):
            libro.autorizar(voz.estimar_usd(txt), permiso=permiso)
            mp3, chars = voz.sintetizar(txt)
            costo = chars / 1000 * voz.tarifa_mil
            if costo or voz.nombre != "simulado":
                libro.registrar(modulo=MODULO, proveedor=voz.nombre, modelo=voz.modelo,
                                unidades={"caracteres": chars}, costo_usd=costo, detalle=clave)
            gastado += costo
            archivo.write_bytes(mp3)
            man[clave] = {"huella": h, "caracteres": chars}
            escribir_json(ruta_man, man)
            avisar(f"  voz {clave}: {len(txt)} caracteres ({i + 1}/{len(textos)})")
        x = recortar_silencio(_a_pcm(archivo.read_bytes(), ffmpeg))
        info.append({"clave": clave, "texto": txt, "inicio": round(t, 3), "fin": round(t + len(x) / SR, 3)})
        pista += [x, np.zeros(int(PAUSA_ENTRE_BLOQUES_S * SR), np.float32)]
        t += len(x) / SR + PAUSA_ENTRE_BLOQUES_S
    audio = np.concatenate(pista) if pista else np.zeros(1, np.float32)
    audio = audio / max(1e-6, float(np.abs(audio).max())) * 0.89
    salida = carpeta.ruta / "audio" / "voz.wav"
    escribir_wav(salida, audio)
    escribir_json(carpeta.ruta / "audio" / "bloques_tiempos.json", {"duracion": round(t, 3), "bloques": info})
    return {"duracion": t, "bloques": info, "costo_usd": gastado, "archivo": str(salida)}


def escribir_wav(ruta: Path, audio: np.ndarray, sr: int = SR) -> None:
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def leer_wav(ruta: Path) -> np.ndarray:
    with wave.open(str(ruta), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
