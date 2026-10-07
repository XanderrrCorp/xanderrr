"""Efectos de sonido generados por código (100 % propios: sin licencias) y sincronizados con lo que pasa en
pantalla. Van bajitos y con freno: no suena todo, solo lo que importa, y nunca dos «pop» seguidos.

- pop: algo aparece           - swoosh: algo entra deslizando, corte a la cuadrícula, empujón de cámara
- rayon: un trazo se dibuja   - golpe: temblor              - error: la X roja      - ding: el chulo verde
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

SR = 48000
_rng = np.random.default_rng(7)


def _env(n, ataque=0.005, caida=0.08):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / max(ataque, 1e-4)) * np.exp(-t / caida)


def pop(intensidad=1.0):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 520 * np.exp(-t * 18) + 240
    return 0.55 * intensidad * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.035)


def swoosh(dur=0.32, intensidad=1.0):
    return intensidad * _swoosh_base(round(dur, 2))


@lru_cache(maxsize=32)
def _swoosh_base(dur: float) -> np.ndarray:
    n = int(dur * SR)
    ruido = _rng.standard_normal(n)
    t = np.arange(n) / n
    # paso bajo que se abre y se cierra (filtro de un polo con coeficiente que cambia)
    salida, y = np.empty(n), 0.0
    for i in range(n):
        a = 0.05 + 0.35 * np.sin(np.pi * t[i])
        y += a * (ruido[i] - y)
        salida[i] = y
    return 0.9 * salida * np.sin(np.pi * t) ** 1.5


def rayon(dur=0.5):
    n = int(max(0.12, dur) * SR)
    t = np.arange(n) / SR
    ruido = _rng.standard_normal(n)
    ruido = np.diff(np.concatenate([[0.0], ruido]))                     # agudo: roce de marcador
    trazos = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 9 * t + _rng.uniform(0, 6)))
    caida = np.minimum(1.0, (n - np.arange(n)) / (0.04 * SR))
    return 0.12 * ruido * trazos * caida * np.minimum(1.0, t / 0.01)


def golpe(intensidad=1.0):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    f = 95 * np.exp(-t * 6) + 45
    cuerpo = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.12)
    click = _rng.standard_normal(n) * _env(n, 0.0005, 0.006) * 0.4
    return 0.9 * intensidad * (cuerpo + click)


def error():
    partes = []
    for f in (330, 247):
        n = int(0.13 * SR)
        t = np.arange(n) / SR
        onda = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * t) * 0.5
        partes.append(0.28 * onda * _env(n, 0.004, 0.09))
    return np.concatenate(partes)


def ding():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    return 0.35 * (np.sin(2 * np.pi * 1320 * t) + 0.4 * np.sin(2 * np.pi * 2640 * t)) * _env(n, 0.002, 0.18)


def eventos(datos: dict) -> list[tuple[float, str, float]]:
    """(segundo, sonido, duración) de cada cosa que suena, con freno para que no suene todo."""
    ev: list[tuple[float, str, float]] = []
    for esc in datos["escenas"]:
        if esc.get("tipo") == "cuadricula":
            ev.append((esc["inicio"], "swoosh", 0.35))
        for m in esc.get("temblor", []):
            ev.append((float(m.get("t", esc["inicio"])), "golpe", 0))
        for m in esc.get("empujon", []):
            ev.append((float(m.get("t", esc["inicio"])), "swoosh_suave", 0.4))
        for el in esc["elementos"]:
            if esc.get("tipo") == "cuadricula" and el.get("pieza") == "circulo_tema":
                continue
            entra = float(el.get("entra", esc["inicio"]))
            movs = el.get("movimiento") or []
            movs = [movs] if isinstance(movs, (str, dict)) else movs
            tipos = {(m if isinstance(m, str) else m.get("tipo")) for m in movs}
            if el.get("pieza") == "x_roja" and not el.get("ya_estaba"):
                ev.append((entra, "error", 0))
            elif el.get("pieza") == "chulo" and not el.get("ya_estaba"):
                ev.append((entra, "ding", 0))
            elif "dibujar" in tipos:
                d = next((float(m.get("duracion", 0.5)) for m in movs if isinstance(m, dict) and m.get("tipo") == "dibujar"), 0.5)
                ev.append((entra, "rayon", d))
            elif "aparecer" in tipos and not el.get("ya_estaba"):
                ev.append((entra, "pop", 0))
            for m in movs:
                if isinstance(m, dict) and m.get("tipo") == "deslizar" and "desde" in m:
                    ev.append((float(m.get("t", entra)), "swoosh", float(m.get("duracion", 0.5))))
                elif isinstance(m, dict) and m.get("tipo") == "temblor" and m.get("t") is not None:
                    ev.append((float(m["t"]), "golpe_suave", 0))
    ev.sort()
    salida, ultimo = [], {}
    for t, nombre, d in ev:
        espera = {"pop": 0.9, "swoosh": 0.5, "swoosh_suave": 0.8, "rayon": 0.4, "golpe": 0.6, "golpe_suave": 0.8,
                  "error": 0.5, "ding": 0.5}[nombre]
        if t - ultimo.get(nombre, -9) < espera:
            continue
        if salida and nombre == "pop" and t - salida[-1][0] < 0.18:      # algo más ya sonó en ese instante
            continue
        ultimo[nombre] = t
        salida.append((t, nombre, d))
    return salida


def pista(datos: dict, duracion: float, volumen: float = 0.55) -> np.ndarray:
    n = int(duracion * SR) + SR
    pista_ = np.zeros(n, np.float32)
    for t, nombre, d in eventos(datos):
        s = {"pop": lambda: pop(), "swoosh": lambda: swoosh(max(0.25, min(0.5, d or 0.35))),
             "swoosh_suave": lambda: swoosh(0.45, 0.45), "rayon": lambda: rayon(d), "golpe": lambda: golpe(),
             "golpe_suave": lambda: golpe(0.45), "error": error, "ding": ding}[nombre]()
        i = int(t * SR)
        if i >= n:
            continue
        fin = min(n, i + len(s))
        pista_[i:fin] += s[:fin - i].astype(np.float32)
    pico = float(np.abs(pista_).max()) or 1.0
    return (pista_ / max(1.0, pico) * volumen)[: int(duracion * SR)]


def escribir(datos: dict, duracion: float, destino) -> None:
    import wave

    x = pista(datos, duracion)
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
