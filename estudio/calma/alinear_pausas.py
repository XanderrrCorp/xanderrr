"""Tiempos por palabra SIN Whisper, a partir de las pausas reales de la voz (respaldo para cuando no se puede
bajar el modelo de Whisper). Menos exacto que Whisper, pero sigue a la voz de verdad:

1. se buscan los tramos de voz y los silencios del audio (energía en ventanas de 20 ms);
2. el texto se parte en frases por la puntuación (. , : ; ? !) y los silencios más largos se toman como
   los cortes entre frases;
3. dentro de cada frase, las palabras se reparten según su largo.

Mismo formato de salida que `TranscriptorWhisper.transcribir` (lista de {palabra, inicio, fin}).
"""
from __future__ import annotations

import re

import numpy as np

SR = 16000
VENTANA = 320            # 20 ms
UMBRAL_DB = -38.0
SILENCIO_MIN = 0.09      # segundos de silencio para contar como pausa


def _tramos_de_voz(x: np.ndarray) -> list[tuple[float, float]]:
    n = len(x) // VENTANA
    if n == 0:
        return []
    e = np.sqrt((x[: n * VENTANA].reshape(n, VENTANA) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(e / (e.max() + 1e-12))
    voz = db > UMBRAL_DB
    tramos, ini = [], None
    for i, v in enumerate(voz):
        if v and ini is None:
            ini = i
        elif not v and ini is not None:
            tramos.append([ini, i])
            ini = None
    if ini is not None:
        tramos.append([ini, n])
    # se unen los tramos separados por silencios muy cortos (dentro de una palabra)
    unidos: list[list[int]] = []
    for a, b in tramos:
        if unidos and (a - unidos[-1][1]) * VENTANA / SR < SILENCIO_MIN:
            unidos[-1][1] = b
        else:
            unidos.append([a, b])
    return [(a * VENTANA / SR, b * VENTANA / SR) for a, b in unidos]


def _frases(texto: str) -> list[list[str]]:
    salida, actual = [], []
    for p in texto.split():
        actual.append(p)
        if re.search(r"[.,:;?!…]$", p):
            salida.append(actual)
            actual = []
    if actual:
        salida.append(actual)
    return salida


def _peso(palabra: str) -> float:
    letras = len(re.sub(r"[^\wáéíóúñü]", "", palabra.lower()))
    return 0.6 + letras


class TranscriptorPausas:
    nombre = "pausas"

    def transcribir(self, audio16k: np.ndarray, texto_esperado: str = "") -> list[dict]:
        frases = _frases(texto_esperado)
        tramos = _tramos_de_voz(audio16k)
        if not frases or not tramos:
            return []
        # cortes entre frases = los silencios más largos (tantos como frases - 1)
        huecos = sorted(range(len(tramos) - 1), key=lambda i: tramos[i + 1][0] - tramos[i][1], reverse=True)
        cortes = sorted(huecos[: len(frases) - 1])
        grupos, ini = [], 0
        for c in cortes:
            grupos.append((tramos[ini][0], tramos[c][1]))
            ini = c + 1
        grupos.append((tramos[ini][0], tramos[-1][1]))
        while len(grupos) < len(frases):              # menos pausas que frases: se parte el tramo más largo
            k = max(range(len(grupos)), key=lambda i: grupos[i][1] - grupos[i][0])
            a, b = grupos[k]
            grupos[k:k + 1] = [(a, (a + b) / 2), ((a + b) / 2, b)]
        salida = []
        for palabras, (a, b) in zip(frases, grupos):
            pesos = [_peso(p) for p in palabras]
            total, acum = sum(pesos), 0.0
            for p, w in zip(palabras, pesos):
                ini_p = a + (b - a) * acum / total
                acum += w
                salida.append({"palabra": p, "inicio": round(ini_p, 3), "fin": round(a + (b - a) * acum / total, 3)})
        return salida
