"""Recortar los silencios largos de la voz (como un editor que corta los respiros).

Se corre DESPUÉS de sacar los tiempos de cada palabra (Whisper trabaja mejor con las pausas naturales) y con
el mismo mapa se corrigen `bloques_tiempos.json` y `oraciones.json`. Algunas pausas se conservan más largas
(por ejemplo, tras el nombre de cada tema, para que se vea la cuadrícula).
"""
from __future__ import annotations

import numpy as np

from ..config import escribir_json, leer_json
from ..tracy.audio import escribir_wav, leer_wav
from ..voz import SR

VENTANA = 480            # 10 ms a 48 kHz
UMBRAL_DB = -40.0


def silencios(x: np.ndarray, minimo_s: float) -> list[tuple[int, int]]:
    n = len(x) // VENTANA
    e = np.sqrt((x[: n * VENTANA].reshape(n, VENTANA) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(e / (e.max() + 1e-12))
    quieto = db < UMBRAL_DB
    salida, ini = [], None
    for i, q in enumerate(quieto):
        if q and ini is None:
            ini = i
        elif not q and ini is not None:
            if (i - ini) * VENTANA / SR >= minimo_s:
                salida.append((ini * VENTANA, i * VENTANA))
            ini = None
    return salida


def recortar_pausas(carpeta, maximo_s: float = 0.22, largas: list[float] | None = None,
                    larga_s: float = 0.6) -> float:
    """Deja cada silencio en `maximo_s` como mucho (los que empiezan junto a un momento de `largas`, en
    `larga_s`). Corrige los tiempos guardados. Devuelve cuántos segundos se quitaron."""
    ruta = carpeta.ruta / "audio" / "voz.wav"
    x = leer_wav(ruta)
    largas = largas or []
    cortes = []
    for a, b in silencios(x, maximo_s + 0.03):
        tope = larga_s if any(abs(a / SR - t) < 0.35 for t in largas) else maximo_s
        sobra = (b - a) - int(tope * SR)
        if sobra > 0:
            centro = (a + b) // 2
            cortes.append((centro - sobra // 2, centro - sobra // 2 + sobra))
    if not cortes:
        return 0.0
    partes, prev = [], 0
    for a, b in cortes:
        partes.append(x[prev:a])
        prev = b
    partes.append(x[prev:])
    escribir_wav(ruta, np.concatenate(partes))

    def mapa(t: float) -> float:
        s = int(t * SR)
        quitado = sum(min(b, s) - a for a, b in cortes if a < s)
        return round((s - quitado) / SR, 3)

    info_ruta = carpeta.ruta / "audio" / "bloques_tiempos.json"
    info = leer_json(info_ruta)
    for b in info["bloques"]:
        b["inicio"], b["fin"] = mapa(b["inicio"]), mapa(b["fin"])
    info["duracion"] = mapa(info["duracion"])
    escribir_json(info_ruta, info)
    ors_ruta = carpeta.ruta / "audio" / "oraciones.json"
    if ors_ruta.exists():
        ors = leer_json(ors_ruta)
        for o in ors["oraciones"]:
            o["inicio"], o["fin"] = mapa(o["inicio"]), mapa(o["fin"])
            for w in o["palabras"]:
                w["inicio"], w["fin"] = mapa(w["inicio"]), mapa(w["fin"])
        ors["duracion"] = info["duracion"]
        escribir_json(ors_ruta, ors)
    return round(sum(b - a for a, b in cortes) / SR, 2)
