"""Voz (sección 5.5 y 14.5) con MiniMax y tiempos REALES por escena.

Se sintetiza por ORACIONES completas (buena entonación) y no por escena. Cuando
una oración abarca varias escenas, el corte entre ellas se busca en el audio:
el punto de menor energía cerca de donde debería caer según los caracteres, que
es la pausa real de la coma. Si MiniMax entrega marcas por palabra se pueden
usar en su lugar; aquí no hacen falta para cortar entre escenas.

Las pausas entre oraciones las pone el código (14.5): más largas al cambiar de
sección y un silencio breve antes de cada revelación.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import ConfigCostos, clave_api, escribir_json, leer_config, leer_json
from .costos import FrenoPresupuesto
from .esquemas import Escena
from .proyecto import CarpetaProyecto

SR = 48000
MODULO = "voz"


class ErrorVoz(Exception):
    pass


@dataclass
class Grupo:
    escenas: list[Escena]

    @property
    def texto(self) -> str:
        return " ".join(e.narracion.strip() for e in self.escenas)


def agrupar(escenas: list[Escena]) -> list[Grupo]:
    grupos, actual = [], []
    for i, e in enumerate(escenas):
        actual.append(e)
        fin_oracion = e.narracion.rstrip().endswith((".", "?", "!", "…", ":"))
        cambia = i + 1 < len(escenas) and escenas[i + 1].seccion != e.seccion
        if fin_oracion or cambia or len(actual) >= 4:
            grupos.append(Grupo(actual))
            actual = []
    if actual:
        grupos.append(Grupo(actual))
    return grupos


def _a_pcm(mp3: bytes, ffmpeg: str) -> np.ndarray:
    r = subprocess.run([ffmpeg, "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", str(SR),
                        "pipe:1"], input=mp3, capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768


def _energia(x: np.ndarray, ventana: int = 480) -> np.ndarray:
    n = len(x) // ventana
    return np.sqrt((x[: n * ventana].reshape(n, ventana) ** 2).mean(axis=1) + 1e-12)


def recortar_silencio(x: np.ndarray, umbral_db: float = -42) -> np.ndarray:
    e = _energia(x)
    if not len(e):
        return x
    ref = e.max()
    activos = np.where(20 * np.log10(e / ref + 1e-12) > umbral_db)[0]
    if not len(activos):
        return x
    ini = max(0, activos[0] * 480 - int(0.02 * SR))
    fin = min(len(x), (activos[-1] + 1) * 480 + int(0.06 * SR))
    return x[ini:fin]


def cortes_por_pausas(x: np.ndarray, pesos: list[int], margen_s: float = 0.6) -> list[int]:
    """Muestras donde cortar entre escenas de una misma oración: la posición
    esperada por caracteres, corregida al punto más silencioso cercano."""
    total = sum(pesos)
    e = _energia(x)
    cortes, acum = [], 0
    for p in pesos[:-1]:
        acum += p
        esperado = int(len(e) * acum / total)
        m = int(margen_s * SR / 480)
        a, b = max(1, esperado - m), min(len(e) - 1, esperado + m)
        if b <= a:
            cortes.append(esperado * 480)
            continue
        # pesa la cercanía a lo esperado para no saltar a otra pausa lejana
        ventana = e[a:b] * (1 + 0.6 * np.abs(np.arange(a, b) - esperado) / max(1, m))
        cortes.append(int((a + int(np.argmin(ventana))) * 480))
    return cortes


class VozMiniMax:
    nombre = "minimax"

    def __init__(self, config: ConfigCostos, ajustes: dict, sesion=None):
        import requests

        self.url = ajustes["url"]
        self.modelo = ajustes["modelo"]
        self.voz_id = ajustes["voz_id"]
        self.idioma = ajustes.get("idioma", "Spanish")
        self.velocidad = float(ajustes.get("velocidad", 1.0))
        self.clave = clave_api(ajustes.get("variable_clave", "MINIMAX_API_KEY"))
        self.tarifa_mil = config.precio("tts_por_1000_caracteres")
        self.sesion = sesion or requests.Session()

    def huella(self, texto: str) -> str:
        return hashlib.sha256(f"{self.modelo}|{self.voz_id}|{self.velocidad}|{texto}".encode()).hexdigest()[:16]

    def estimar_usd(self, texto: str) -> float:
        return len(texto) / 1000 * self.tarifa_mil

    def sintetizar(self, texto: str) -> tuple[bytes, int]:
        cab = {"Content-Type": "application/json"}
        if self.clave:
            cab["Authorization"] = f"Bearer {self.clave}"
        cuerpo = {"model": self.modelo, "text": texto, "stream": False, "language_boost": self.idioma,
                  "voice_setting": {"voice_id": self.voz_id, "speed": self.velocidad, "vol": 1, "pitch": 0},
                  "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1}}
        r = self.sesion.post(self.url, headers=cab, data=json.dumps(cuerpo), timeout=180)
        if r.status_code >= 400:
            raise ErrorVoz(f"HTTP {r.status_code}: {r.text[:300]}")
        d = r.json()
        base = d.get("base_resp") or {}
        if base.get("status_code") not in (0, None):
            raise ErrorVoz(f"MiniMax: {base}")
        audio = (d.get("data") or {}).get("audio")
        if not audio:
            raise ErrorVoz("MiniMax no devolvió audio")
        caracteres = int((d.get("extra_info") or {}).get("usage_characters") or len(texto))
        return bytes.fromhex(audio), caracteres


def pausa_despues(actual: Escena, siguiente: Escena | None) -> float:
    if siguiente is None:
        return 0.8
    p = 0.32
    if siguiente.seccion != actual.seccion:
        p = 0.75
    if siguiente.intencion == "revelacion":
        p = max(p, 0.5)          # silencio breve antes de revelar (14.5)
    if actual.narracion.rstrip().endswith("?"):
        p = max(p, 0.45)
    return p + actual.pausa_despues_seg


def generar_voz(carpeta: CarpetaProyecto, ffmpeg: str, voz=None, config: ConfigCostos | None = None,
                permiso: bool = False, avisar=print) -> dict:
    config = config or ConfigCostos.cargar()
    voz = voz or VozMiniMax(config, leer_config("proveedores.json")["voz"])
    esc = carpeta.cargar_escenas()
    libro = carpeta.libro(config)
    dir_audio = carpeta.ruta / "audio" / "grupos"
    dir_audio.mkdir(parents=True, exist_ok=True)
    ruta_man = carpeta.ruta / "audio" / "voz_manifiesto.json"
    man = leer_json(ruta_man) if ruta_man.exists() else {}
    grupos = agrupar(esc.escenas)
    gastado = 0.0
    piezas: list[tuple[Escena, np.ndarray]] = []
    for gi, g in enumerate(grupos):
        clave = f"g{gi:03d}"
        h = voz.huella(g.texto)
        archivo = dir_audio / f"{clave}.mp3"
        if not (man.get(clave, {}).get("huella") == h and archivo.exists()):
            try:
                libro.autorizar(voz.estimar_usd(g.texto), permiso=permiso)
            except FrenoPresupuesto:
                raise
            mp3, chars = voz.sintetizar(g.texto)
            costo = chars / 1000 * voz.tarifa_mil
            libro.registrar(modulo=MODULO, proveedor=voz.nombre, modelo=voz.modelo,
                            unidades={"caracteres": chars}, costo_usd=costo, detalle=clave)
            gastado += costo
            archivo.write_bytes(mp3)
            man[clave] = {"huella": h, "texto": g.texto, "escenas": [e.id for e in g.escenas], "caracteres": chars}
            escribir_json(ruta_man, man)
            avisar(f"  voz {clave}: {len(g.texto)} caracteres")
        x = recortar_silencio(_a_pcm(archivo.read_bytes(), ffmpeg))
        if len(g.escenas) == 1:
            piezas.append((g.escenas[0], x))
        else:
            cortes = cortes_por_pausas(x, [len(e.narracion) for e in g.escenas])
            limites = [0] + cortes + [len(x)]
            for e, a, b in zip(g.escenas, limites[:-1], limites[1:]):
                piezas.append((e, recortar_silencio(x[a:b], -38)))
    # montaje con pausas controladas y tiempos reales
    pista, tiempos, t = [], {}, 0.0
    for i, (e, x) in enumerate(piezas):
        sig = piezas[i + 1][0] if i + 1 < len(piezas) else None
        pausa = pausa_despues(e, sig) if (sig is None or sig.id not in _mismo_grupo(grupos, e)) else 0.12
        tiempos[e.id] = (round(t, 3), round(t + len(x) / SR, 3))
        pista.append(x)
        pista.append(np.zeros(int(pausa * SR), np.float32))
        t += len(x) / SR + pausa
    audio = np.concatenate(pista)
    audio = audio / max(1e-6, np.abs(audio).max()) * 0.89
    salida = carpeta.ruta / "audio" / "voz.wav"
    with wave.open(str(salida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    for e in esc.escenas:
        if e.id in tiempos:
            e.tiempo.real_inicio, e.tiempo.real_fin = tiempos[e.id]
            e.tiempo.alineacion_confiable = True
    carpeta.guardar_escenas(esc)
    escribir_json(carpeta.ruta / "audio" / "alineacion.json",
                  {"metodo": "oraciones + corte en pausas", "duracion": round(t, 3),
                   "escenas": {str(k): v for k, v in tiempos.items()}})
    return {"duracion": t, "grupos": len(grupos), "costo_usd": gastado, "archivo": str(salida)}


def _mismo_grupo(grupos: list[Grupo], e: Escena) -> set[int]:
    for g in grupos:
        ids = [x.id for x in g.escenas]
        if e.id in ids:
            return set(ids)
    return set()
