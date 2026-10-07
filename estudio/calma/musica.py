"""Elegir la música de fondo de la biblioteca (solo pistas con licencia registrada).

Pedido del dueño para Hazlo con Calma: electrónica, tensa, de ritmo bajo y sin melodía que
mande. Entre las pistas de ánimo «tension» (si no hay, «misterio») se mide cada una y gana la
de menos golpes por segundo y menos melodía marcada. El nombre elegido queda en el informe y
se puede cambiar a mano en la página.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

ANIMOS = ("tension", "misterio")
SR = 22050


def medir(audio: np.ndarray, sr: int = SR, segundos: float = 60.0) -> dict:
    """golpes_s: arranques de sonido por segundo (ritmo); melodia: qué tan sobresalen las notas
    entre 300 y 3000 Hz (0 = colchón parejo, 1 = una melodía que manda)."""
    x = audio[: int(segundos * sr)]
    if len(x) < sr:
        return {"golpes_s": 99.0, "melodia": 1.0}
    n, hop = 2048, 512
    cuadros = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    esp = np.abs(np.fft.rfft(cuadros, axis=1))
    flujo = np.maximum(0, np.diff(np.log1p(esp), axis=0)).sum(axis=1)
    umbral = flujo.mean() + 1.5 * flujo.std()
    picos = (flujo[1:-1] > umbral) & (flujo[1:-1] >= flujo[:-2]) & (flujo[1:-1] >= flujo[2:])
    golpes = float(picos.sum()) / (len(x) / sr)
    f = np.fft.rfftfreq(n, 1 / sr)
    banda = esp[:, (f >= 300) & (f <= 3000)]
    tope = np.sort(banda, axis=1)[:, -5:].sum(axis=1)
    melodia = float(np.median(tope / (banda.sum(axis=1) + 1e-9)))
    return {"golpes_s": round(golpes, 2), "melodia": round(melodia, 3)}


def elegir(ffmpeg: str, avisar=print, animos: tuple[str, ...] = ANIMOS) -> dict | None:
    """La pista más adecuada de la biblioteca, o None si no hay música con licencia."""
    from .. import biblioteca

    candidatas: list[Path] = []
    animo = None
    for a in animos:
        candidatas = biblioteca.utilizables("musica", a)
        if candidatas:
            animo = a
            break
    if not candidatas:
        avisar(f"No hay música de ánimo {' ni '.join(animos)} en la biblioteca: el video va solo con la voz")
        return None
    medidas = []
    for ruta in candidatas:
        try:
            m = medir(biblioteca.leer_audio(ruta, ffmpeg, SR))
        except Exception as ex:  # noqa: BLE001 — una pista dañada no frena el video
            avisar(f"  no pude leer {ruta.name}: {ex}")
            continue
        medidas.append({"ruta": str(ruta), "nombre": ruta.name, "animo": animo, **m})
    if not medidas:
        return None
    g = np.array([m["golpes_s"] for m in medidas])
    mel = np.array([m["melodia"] for m in medidas])

    def z(v):
        return (v - v.mean()) / (v.std() + 1e-9)

    puntaje = z(g) + z(mel)
    mejor = medidas[int(np.argmin(puntaje))]
    por_archivo = {Path(a["archivo"]).name: a for a in biblioteca.indice()}
    reg = por_archivo.get(mejor["nombre"], {})
    mejor["nombre_original"] = reg.get("nombre_original", mejor["nombre"])
    mejor["licencia"] = reg.get("licencia")
    mejor["atribucion"] = reg.get("atribucion", "")
    mejor["de"] = len(medidas)
    return mejor
