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


def _frases(texto: str, fin: str = r"[.:;?!…]$") -> list[list[str]]:
    salida, actual = [], []
    for p in texto.split():
        actual.append(p)
        if re.search(fin, p):
            salida.append(actual)
            actual = []
    if actual:
        salida.append(actual)
    return salida


def _repartir(grupos_de_palabras: list[list[str]], tramos: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Asigna a cada grupo de palabras un trozo seguido de los tramos de voz. Elige los cortes (siempre en
    silencios) que mejor cumplen dos cosas a la vez: que cada grupo dure lo que le toca según su largo, y que
    los cortes caigan en los silencios más largos (programación dinámica)."""
    n, m = len(grupos_de_palabras), len(tramos)
    if not tramos:
        return []
    if m < n:                                       # menos tramos que grupos: se reparte por largo de texto
        a, b = tramos[0][0], tramos[-1][1]
        pesos = [sum(_peso(p) for p in g) for g in grupos_de_palabras]
        total, acum, salida = sum(pesos), 0.0, []
        for w in pesos:
            salida.append((a + (b - a) * acum / total, a + (b - a) * (acum + w) / total))
            acum += w
        return salida
    pesos = [sum(_peso(p) for p in g) for g in grupos_de_palabras]
    total_voz = tramos[-1][1] - tramos[0][0]
    esperado = [total_voz * w / sum(pesos) for w in pesos]
    huecos = [tramos[i + 1][0] - tramos[i][1] for i in range(m - 1)]
    medio = (sum(huecos) / len(huecos)) if huecos else 1.0
    INF = float("inf")
    # costo[k][j]: el grupo k termina en el tramo j
    costo = [[INF] * m for _ in range(n)]
    atras = [[-1] * m for _ in range(n)]
    for j in range(m):
        d = tramos[j][1] - tramos[0][0]
        costo[0][j] = ((d - esperado[0]) / esperado[0]) ** 2
    for k in range(1, n):
        for j in range(k, m):
            mejor, de = INF, -1
            for i in range(k - 1, j):               # el grupo k-1 termina en i; el k va de i+1 a j
                if costo[k - 1][i] == INF:
                    continue
                d = tramos[j][1] - tramos[i + 1][0]
                c = costo[k - 1][i] + ((d - esperado[k]) / esperado[k]) ** 2 - 0.6 * min(3.0, huecos[i] / medio)
                if c < mejor:
                    mejor, de = c, i
            costo[k][j], atras[k][j] = mejor, de
    fin = m - 1
    cortes = []
    for k in range(n - 1, 0, -1):
        i = atras[k][fin]
        cortes.append(i)
        fin = i
    cortes.reverse()
    salida, ini = [], 0
    for c in cortes:
        salida.append((tramos[ini][0], tramos[c][1]))
        ini = c + 1
    salida.append((tramos[ini][0], tramos[-1][1]))
    return salida


def _peso(palabra: str) -> float:
    letras = len(re.sub(r"[^\wáéíóúñü]", "", palabra.lower()))
    return 0.6 + letras


class TranscriptorPausas:
    nombre = "pausas"

    def transcribir(self, audio16k: np.ndarray, texto_esperado: str = "") -> list[dict]:
        oraciones = _frases(texto_esperado)
        tramos = _tramos_de_voz(audio16k)
        if not oraciones or not tramos:
            return []
        salida = []
        # 1) cada oración (punto, dos puntos, ?, !) a su trozo de voz; 2) dentro, cada parte entre comas
        for palabras_or, (a, b) in zip(oraciones, _repartir(oraciones, tramos)):
            internos = [(max(a, x), min(b, y)) for x, y in tramos if y > a and x < b] or [(a, b)]
            partes = _frases(" ".join(palabras_or), r"[,;]$")
            for palabras, (pa, pb) in zip(partes, _repartir(partes, internos)):
                pesos = [_peso(p) for p in palabras]
                total, acum = sum(pesos), 0.0
                for p, w in zip(palabras, pesos):
                    ini_p = pa + (pb - pa) * acum / total
                    acum += w
                    salida.append({"palabra": p, "inicio": round(ini_p, 3), "fin": round(pa + (pb - pa) * acum / total, 3)})
        return salida
