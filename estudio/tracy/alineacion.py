"""Tiempos reales por oración: Whisper local (faster-whisper) + emparejado con el guion.

Whisper da marcas por palabra de lo que OYE; el texto que manda es el del guion. Las
palabras transcritas se emparejan con las del guion (difflib). Las que Whisper oyó distinto
toman el tramo de lo que oyó en su lugar, y las que no oyó se interpolan entre sus vecinas.
Así cada oración del guion recibe su inicio y fin reales en `audio/voz.wav`.

Se transcribe bloque por bloque (los mismos del TTS) para que un error no se arrastre, y
cada transcripción queda guardada: volver a segmentar no vuelve a correr Whisper.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from pathlib import Path

import numpy as np

from ..config import escribir_json, leer_config, leer_json
from ..proyecto import CarpetaProyecto
from ..voz import SR
from .audio import leer_wav, oraciones
from .numeros import numeros_a_palabras

SR_WHISPER = 16000


def normalizar(palabra: str) -> str:
    t = unicodedata.normalize("NFKD", palabra.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", t)


# ------------------------------------------------------------------ transcriptores

def cuda_completo() -> bool:
    """¿Están las librerías que Whisper necesita para usar la tarjeta NVIDIA? (CUDA 12: cublas64_12.dll y
    cuDNN 9: cudnn*64_9.dll). Se buscan en el PATH y en las carpetas de instalación de NVIDIA. Si falta
    alguna, Whisper usa el procesador: con CUDA a medias se quedaba pegado sin avisar."""
    import glob
    import os

    if os.name != "nt":
        return False
    carpetas = [c for c in os.environ.get("PATH", "").split(os.pathsep) if c]
    for var in ("CUDA_PATH", "CUDNN_PATH"):
        if os.environ.get(var):
            carpetas += [os.path.join(os.environ[var], "bin")]
    carpetas += glob.glob(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12*\bin")
    carpetas += glob.glob(r"C:\Program Files\NVIDIA\CUDNN\v9*\bin\12*")
    carpetas += glob.glob(r"C:\Program Files\NVIDIA\CUDNN\v9*\bin")

    def hay(patron: str) -> bool:
        return any(glob.glob(os.path.join(c, patron)) for c in carpetas)

    return hay("cublas64_12.dll") and hay("cudnn*64_9.dll")


def _carpetas_cuda_al_path() -> None:
    """Las carpetas de cuDNN no siempre quedan en el PATH al instalarlo: se agregan para este proceso."""
    import glob
    import os

    extra = glob.glob(r"C:\Program Files\NVIDIA\CUDNN\v9*\bin\12*") + \
        glob.glob(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12*\bin")
    for c in extra:
        if c not in os.environ.get("PATH", ""):
            os.environ["PATH"] = c + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                try:
                    os.add_dll_directory(c)
                except OSError:
                    pass


class TranscriptorWhisper:
    """faster-whisper local. La primera vez baja el modelo (small ≈ 480 MB) y queda guardado."""

    def __init__(self, modelo: str | None = None, dispositivo: str | None = None):
        ajustes = leer_config("proveedores.json").get("whisper", {})
        self.modelo = modelo or ajustes.get("modelo", "small")
        self.dispositivo = dispositivo or ajustes.get("dispositivo", "auto")
        if self.dispositivo == "auto":
            # la tarjeta solo si CUDA 12 y cuDNN 9 están completos; si no, el procesador (nunca se traba)
            if cuda_completo():
                _carpetas_cuda_al_path()
                self.dispositivo = "cuda"
            else:
                self.dispositivo = "cpu"
        self.idioma = ajustes.get("idioma", "es")
        self._m = None
        self.nombre = f"whisper-{self.modelo}"

    def _cargar(self):
        if self._m is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as ex:   # pragma: no cover — depende de la instalación
                raise RuntimeError("Falta Whisper local: instala con  pip install -e \".[tracy]\"") from ex
            tipo = "int8" if self.dispositivo in ("cpu", "auto") else "int8_float16"
            try:
                self._m = WhisperModel(self.modelo, device=self.dispositivo, compute_type=tipo)
            except (RuntimeError, OSError, ValueError):
                if self.dispositivo == "cpu":
                    raise
                self.dispositivo = "cpu"                 # sin CUDA usable: el procesador
                self._m = WhisperModel(self.modelo, device="cpu", compute_type="int8")
        return self._m

    def transcribir(self, audio16k: np.ndarray, texto_esperado: str = "") -> list[dict]:
        try:
            return self._transcribir(audio16k)
        except (RuntimeError, OSError) as ex:
            # con una tarjeta NVIDIA sin las librerías de CUDA (cublas, cudnn) Whisper falla al empezar:
            # se sigue con el procesador, que siempre funciona (más lento, mismo resultado)
            if self.dispositivo == "cpu" or not any(p in str(ex).lower() for p in ("cublas", "cudnn", "cuda", ".dll")):
                raise
            self.dispositivo, self._m = "cpu", None
            return self._transcribir(audio16k)

    def _transcribir(self, audio16k: np.ndarray) -> list[dict]:
        # beam_size=1: 2-3 veces más rápido en el procesador; el texto que manda es el del guion, Whisper
        # solo aporta los tiempos, así que buscar la mejor frase entre 5 no mejora nada
        segs, _ = self._cargar().transcribe(audio16k.astype(np.float32), language=self.idioma, word_timestamps=True,
                                            beam_size=1, condition_on_previous_text=False)
        # la lista se arma aquí adentro: faster-whisper trabaja al recorrer los segmentos (ahí falla CUDA)
        return [{"palabra": w.word.strip(), "inicio": float(w.start), "fin": float(w.end)}
                for s in segs for w in (s.words or []) if w.word.strip()]


class TranscriptorSimulado:
    """Para el ensayo con la voz simulada: lee del audio los pulsos (uno por palabra) y les pone
    las palabras esperadas. Recorre el mismo camino que Whisper sin bajar ningún modelo."""
    nombre = "simulado"

    def transcribir(self, audio16k: np.ndarray, texto_esperado: str = "") -> list[dict]:
        ventana = SR_WHISPER // 100                     # 10 ms
        n = len(audio16k) // ventana
        if n == 0:
            return []
        e = np.sqrt((audio16k[: n * ventana].reshape(n, ventana) ** 2).mean(axis=1) + 1e-12)
        activo = e > e.max() * 0.08
        tramos, ini = [], None
        for i, a in enumerate(np.append(activo, False)):
            if a and ini is None:
                ini = i
            elif not a and ini is not None:
                tramos.append((ini, i))
                ini = None
        # une huecos de menos de 40 ms (no son pausas entre palabras)
        unidos: list[list[int]] = []
        for a, b in tramos:
            if unidos and a - unidos[-1][1] < 4:
                unidos[-1][1] = b
            else:
                unidos.append([a, b])
        palabras = texto_esperado.split()
        return [{"palabra": p, "inicio": a / 100, "fin": b / 100} for p, (a, b) in zip(palabras, unidos)]


def transcriptor_para(proveedor: str | None):
    return TranscriptorSimulado() if proveedor == "simulado" else TranscriptorWhisper()


# ------------------------------------------------------------------ emparejado

def _tokens_oido(palabras: list[dict]) -> list[tuple[str, float, float]]:
    """Palabras de Whisper normalizadas; «1990» se pasa a palabras y reparte su tramo."""
    salida = []
    for w in palabras:
        partes = [normalizar(x) for x in numeros_a_palabras(w["palabra"]).split()]
        partes = [p for p in partes if p]
        if not partes:
            continue
        paso = (w["fin"] - w["inicio"]) / len(partes)
        for k, p in enumerate(partes):
            salida.append((p, w["inicio"] + k * paso, w["inicio"] + (k + 1) * paso))
    return salida


def emparejar(guion: list[str], oido: list[dict], duracion: float) -> tuple[list[tuple[float, float]], float]:
    """Tiempos (inicio, fin) para cada palabra del guion y la fracción que coincidió exacta."""
    g = [normalizar(p) for p in guion]
    w = _tokens_oido(oido)
    tiempos: list[tuple[float, float] | None] = [None] * len(guion)
    iguales = 0
    idx_g = [i for i, x in enumerate(g) if x]           # palabras con letras (se ignoran «—», «…»)
    sm = difflib.SequenceMatcher(None, [g[i] for i in idx_g], [x[0] for x in w], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                tiempos[idx_g[i1 + k]] = (w[j1 + k][1], w[j1 + k][2])
            iguales += i2 - i1
        elif op == "replace":
            # lo que Whisper oyó distinto ocupa el mismo tramo: se reparte por largo de palabra
            ini, fin = w[j1][1], w[j2 - 1][2]
            pesos = [max(1, len(g[idx_g[i]])) for i in range(i1, i2)]
            acum, total = 0, sum(pesos)
            for k, i in enumerate(range(i1, i2)):
                a = ini + (fin - ini) * acum / total
                acum += pesos[k]
                tiempos[idx_g[i]] = (a, ini + (fin - ini) * acum / total)
    _interpolar(guion, tiempos, duracion)
    return [t for t in tiempos], (iguales / len(idx_g) if idx_g else 1.0)   # type: ignore[misc]


def _interpolar(guion: list[str], tiempos: list, duracion: float) -> None:
    """Las palabras sin tiempo se reparten entre la vecina anterior y la siguiente con tiempo."""
    i = 0
    while i < len(tiempos):
        if tiempos[i] is not None:
            i += 1
            continue
        j = i
        while j < len(tiempos) and tiempos[j] is None:
            j += 1
        desde = tiempos[i - 1][1] if i > 0 else 0.0
        hasta = tiempos[j][0] if j < len(tiempos) else duracion
        hasta = max(hasta, desde)
        pesos = [max(1, len(guion[k])) for k in range(i, j)]
        acum, total = 0, sum(pesos)
        for k in range(i, j):
            a = desde + (hasta - desde) * acum / total
            acum += pesos[k - i]
            tiempos[k] = (a, desde + (hasta - desde) * acum / total)
        i = j


# ------------------------------------------------------------------ por proyecto

def _a_16k(x: np.ndarray) -> np.ndarray:
    paso = SR // SR_WHISPER                                  # 48000 → 16000
    n = len(x) // paso
    return x[: n * paso].reshape(n, paso).mean(axis=1)


def alinear(carpeta: CarpetaProyecto, transcriptor, avisar=print) -> dict:
    """Escribe `audio/oraciones.json`: por oración su texto, inicio, fin y palabras con tiempo."""
    info = leer_json(carpeta.ruta / "audio" / "bloques_tiempos.json")
    audio = leer_wav(carpeta.ruta / "audio" / "voz.wav")
    man = leer_json(carpeta.ruta / "audio" / "bloques.json")
    dir_w = carpeta.ruta / "audio" / "whisper"
    dir_w.mkdir(parents=True, exist_ok=True)
    salida, coincidencias = [], []
    pendientes = [b for b in info["bloques"]
                  if (leer_json(dir_w / f"{b['clave']}.json") if (dir_w / f"{b['clave']}.json").exists() else {})
                  .get("huella") != f"{transcriptor.nombre}|{man[b['clave']]['huella']}"]
    if pendientes and hasattr(transcriptor, "_cargar"):
        avisar("Preparando Whisper (la primera vez baja su modelo de unos 480 MB; puede tardar según tu internet)…")
        transcriptor._cargar()
        avisar(f"Whisper listo ({getattr(transcriptor, 'dispositivo', '')}): {len(pendientes)} bloque(s) por transcribir")
    hechos = 0
    for b in info["bloques"]:
        x = audio[int(b["inicio"] * SR): int(b["fin"] * SR)]
        dur = len(x) / SR
        cache = dir_w / f"{b['clave']}.json"
        huella = f"{transcriptor.nombre}|{man[b['clave']]['huella']}"
        guardado = leer_json(cache) if cache.exists() else {}
        if guardado.get("huella") == huella:
            oido = guardado["palabras"]
        else:
            hechos += 1
            avisar(f"  transcribiendo bloque {hechos} de {len(pendientes)} ({dur:.0f} s de voz)…")
            oido = transcriptor.transcribir(_a_16k(x), b["texto"])
            escribir_json(cache, {"huella": huella, "palabras": oido})
        ors = oraciones(b["texto"])
        palabras = [(k, p) for k, o in enumerate(ors) for p in o.split()]
        tiempos, fraccion = emparejar([p for _, p in palabras], oido, dur)
        coincidencias.append(fraccion)
        for k, o in enumerate(ors):
            pts = [(p, t) for (kk, p), t in zip(palabras, tiempos) if kk == k]
            salida.append({"texto": o,
                           "inicio": round(b["inicio"] + pts[0][1][0], 3),
                           "fin": round(b["inicio"] + pts[-1][1][1], 3),
                           "palabras": [{"p": p, "inicio": round(b["inicio"] + t[0], 3),
                                         "fin": round(b["inicio"] + t[1], 3)} for p, t in pts]})
    confianza = float(np.mean(coincidencias)) if coincidencias else 0.0
    datos = {"metodo": transcriptor.nombre, "duracion": info["duracion"], "confianza": round(confianza, 3),
             "oraciones": [{"id": i, **o} for i, o in enumerate(salida)]}
    escribir_json(carpeta.ruta / "audio" / "oraciones.json", datos)
    if confianza < 0.6:
        avisar(f"  ¡ojo! Whisper coincidió solo en el {confianza:.0%} de las palabras: revisa el audio")
    return datos
