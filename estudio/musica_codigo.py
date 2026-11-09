"""Música hecha por código para Peligro Tropical v4 (07/09-11, pedido del dueño: «haz las canciones con código y que no
duren todo el video, solo en tramos específicos»). Sin licencias: todo se sintetiza aquí.

Lección del 07-11 (la capa animada le sonó «pésima, muy dura y se repite»): aquí todo es SUAVE y nada se repite en
bucle: pad cálido con filtro bajo, notas que se eligen compás por compás (otra semilla, otra melodía), sin batería dura,
entrada y salida de 2 s. Tres ánimos:
- «calma»: acordes mayores lentos y un arpegio punteado que salta notas;
- «tension»: acordes menores y un pulso grave suave;
- «oscura»: zumbido grave (raíz + quinta), choques de medio tono y un timbal lejano de vez en cuando.
"""
from __future__ import annotations

import numpy as np

SR = 48000
_ESCALAS = {
    "calma": [(0, 4, 7), (9, 12, 16), (5, 9, 12), (7, 11, 14), (2, 5, 9)],       # I vi IV V ii (en semitonos)
    "tension": [(0, 3, 7), (8, 12, 15), (10, 14, 17), (5, 8, 12), (7, 10, 14)],  # i VI VII iv v
    "oscura": [(0, 7, 12), (1, 8, 13), (0, 7, 12), (-1, 6, 11)],                  # raíz+quinta con choques
}
_TEMPO = {"calma": 78, "tension": 96, "oscura": 62}
_RAIZ = {"calma": 57, "tension": 52, "oscura": 40}            # MIDI: La3, Mi3, Mi2


def _f(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _suavizar(x: np.ndarray, corte: float) -> np.ndarray:
    from .pt_animado.audio import dsp

    return dsp.lp(x, corte, 2)


def generar(animo: str, dur: float, semilla: int = 0) -> np.ndarray:
    """`dur` segundos de música mono (float32, 48 kHz) con entrada y salida suaves"""
    from .pt_animado.audio import instruments as I

    animo = animo if animo in _ESCALAS else "calma"
    r = np.random.default_rng(semilla)
    n = int(dur * SR)
    out = np.zeros(n + SR * 4, np.float64)
    compas = 4 * 60.0 / _TEMPO[animo]
    raiz = _RAIZ[animo] + int(r.integers(-2, 3))                # cada tramo en otro tono
    acordes = _ESCALAS[animo]
    t = 0.0
    previo = -1
    notas: dict = {}

    def punteo(m: int, dur_n: float, brillo: float) -> np.ndarray:
        """cada nota se sintetiza una vez por tramo y se reusa (con otro volumen)"""
        clave = (m, dur_n, brillo)
        if clave not in notas:
            notas[clave] = I.pluck(_f(m), vel=1.0, r=r, dur=dur_n, bright=brillo)
        return notas[clave]
    while t < dur:
        k = int(r.integers(0, len(acordes)))
        if k == previo:
            k = (k + 1) % len(acordes)
        previo = k
        acorde = [raiz + s for s in acordes[k]]
        i0 = int(t * SR)
        # pad cálido (filtro bajo: nada chillón)
        p = I.pad([_f(m - 12) for m in acorde], compas, vel=0.55, r=r, att=compas * 0.35, rel=compas * 0.5,
                  warm=650.0 if animo != "oscura" else 380.0, detune=5.0).sum(axis=0)
        out[i0:i0 + len(p)] += p[:len(out) - i0]
        if animo == "calma":                                     # arpegio que salta notas al azar
            paso = compas / 8
            for j in range(8):
                if r.random() < 0.38:
                    continue
                m = acorde[int(r.integers(0, 3))] + 12 * int(r.integers(0, 2))
                s = punteo(m, 1.2, 0.25) * (0.22 + 0.1 * r.random())
                a = i0 + int(j * paso * SR)
                out[a:a + len(s)] += s[:max(0, len(out) - a)]
        elif animo == "tension":                                 # pulso grave suave en corcheas
            paso = compas / 8
            for j in range(8):
                if j % 2 and r.random() < 0.5:
                    continue
                s = punteo(acorde[0] - 12, 0.5, 0.1) * (0.32 if j % 4 == 0 else 0.18)
                a = i0 + int(j * paso * SR)
                out[a:a + len(s)] += s[:max(0, len(out) - a)]
        else:                                                    # oscura: timbal lejano cada tanto
            if r.random() < 0.45:
                s = I.timpani(_f(acorde[0] - 12), vel=0.35, r=r, dur=2.6) * 0.5
                a = i0 + int(r.uniform(0, 0.5) * compas * SR)
                out[a:a + len(s)] += s[:max(0, len(out) - a)]
        t += compas
    y = _suavizar(out[:n], 3800.0 if animo == "calma" else 2600.0)
    pico = float(np.max(np.abs(y))) or 1.0
    y = y / pico * 0.6
    f = min(int(SR * 2.0), n // 3)                               # entra y sale despacio (2 s)
    if f:
        y[:f] *= np.linspace(0, 1, f) ** 2
        y[-f:] *= np.linspace(1, 0, f) ** 2
    return y.astype(np.float32)
