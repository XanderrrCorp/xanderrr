"""Audio final: voz + música suave por debajo (se agacha cuando habla y sube en las pausas) + master -14 LUFS / ≤-1 dBTP.

Música: la de la carpeta del canal si existe (datos/codigo_exito/musica, pistas con licencia del dueño); si no, una
cama tranquila hecha por código (acordes de pad cálido + guitarra suave, Re mayor, 70 bpm). Mismo motor de la Fase 1 de
Peligro Tropical (dsp/instruments de la skill, MIT).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from ..pt_animado.audio import capa
from ..pt_animado.audio import dsp as D
from ..pt_animado.audio.dsp import SR, TAU, dbg, integrated, ns, rng

PROGRESION = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61]]   # Re – Si m – Sol – La
VOZ_LUFS, MUSICA_BAJO_VOZ, OBJETIVO = -18.0, -17.0, -14.0


def cama_por_codigo(dur: float, semilla: int = 3) -> np.ndarray:
    r = rng(semilla)
    n = ns(dur + 4)
    m = np.zeros((2, n))
    compas = 60 / 70 * 4
    t0, k = 0.0, 0
    while t0 < dur + 2:
        notas = PROGRESION[k % len(PROGRESION)]
        largo = compas + 1.5
        t = D.tt(largo)
        env = np.minimum(1, t / 1.2) * np.minimum(1, (largo - t) / 1.5)
        pad = sum(np.sin(TAU * capa.m2f(nn) * t) * (0.5 if i == 0 else 0.22) + 0.06 * np.sin(TAU * capa.m2f(nn) * 2.003 * t)
                  for i, nn in enumerate(notas))
        pad = D.lp(pad * env, 1400)
        D.place(m, D.st(pad) * 0.35, t0)
        g = capa.guitarra([capa.m2f(nn + 12) for nn in notas[1:]], 0.18, r, dur=2.4, rasgueo=0.05)
        D.place(m, D.st(g) * 0.5, t0 + 0.05)
        t0 += compas
        k += 1
    return m[:, :ns(dur)]


def cama_de_archivo(carpeta: Path, dur: float, ffmpeg: str) -> np.ndarray | None:
    pistas = sorted([p for p in carpeta.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")]) if carpeta.exists() else []
    if not pistas:
        return None
    trozos, total = [], 0.0
    k = 0
    while total < dur and k < 200:
        r = subprocess.run([ffmpeg, "-v", "error", "-i", str(pistas[k % len(pistas)]), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                           capture_output=True, check=True)
        x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).T.astype(np.float64)
        trozos.append(x); total += x.shape[1] / SR; k += 1
    m = np.concatenate(trozos, axis=1)[:, :ns(dur)]
    return m


NIVEL_SFX = {"whoosh": -21.0, "pop": -24.0, "clic": -24.0, "lapiz": -22.0, "tick": -26.0, "tono": -24.0}


def carpeta_sfx() -> Path:
    import os

    if os.environ.get("CODIGO_EXITO_SFX"):
        return Path(os.environ["CODIGO_EXITO_SFX"])
    from ..plataforma.db import carpeta_datos

    return carpeta_datos() / "codigo_exito" / "sfx"


def pista_efectos(efectos, n: int, ffmpeg: str) -> np.ndarray:
    """los efectos del dueño (whoosh, pop, clic, lápiz…) en cada corte; sin su carpeta, ninguno"""
    fx = np.zeros((2, n))
    sonidos: dict = {}
    for e in efectos:
        if e["tipo"] not in sonidos:
            ruta = carpeta_sfx() / f"{e['tipo']}.wav"
            if not ruta.exists():
                sonidos[e["tipo"]] = None
                continue
            r = subprocess.run([ffmpeg, "-v", "error", "-i", str(ruta), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True)
            x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).T.astype(np.float64)
            sonidos[e["tipo"]] = x / (np.abs(x).max() + 1e-9) * dbg(NIVEL_SFX.get(e["tipo"], -24.0) + 6)
        x = sonidos[e["tipo"]]
        if x is not None:
            D.place(fx, x, max(0.0, e["t"] - (0.12 if e["tipo"] == "whoosh" else 0.0)))
    return fx


def mezclar(voz: np.ndarray, ffmpeg: str, carpeta_musica: Path | None = None, efectos: list[dict] = ()) -> tuple[np.ndarray, dict]:
    """voz mono float a 48 kHz → mezcla estéreo float32 lista para el video"""
    n = len(voz)
    dur = n / SR
    m = (cama_de_archivo(carpeta_musica, dur, ffmpeg) if carpeta_musica else None)
    origen = "biblioteca del canal" if m is not None else "por código"
    if m is None:
        m = cama_por_codigo(dur)
    m = np.pad(m, ((0, 0), (0, max(0, n - m.shape[1]))))[:, :n]
    v = D.st(voz)
    lv = integrated(v)
    v = v * dbg(VOZ_LUFS - lv) if np.isfinite(lv) else v
    lm = integrated(m)
    if np.isfinite(lm):
        m = m * dbg(VOZ_LUFS + MUSICA_BAJO_VOZ - lm)
    m = m * dbg(capa._agache(capa._actividad_voz(voz), n, prof=-8.0))[None, :]
    fo = ns(3.0)
    m[:, -fo:] *= np.linspace(1, 0, fo)[None, :]
    mezcla = v + m + pista_efectos(efectos, n, ffmpeg)
    mezcla = mezcla * dbg(OBJETIVO - integrated(mezcla))
    for _ in range(3):
        mezcla = capa.limitador(mezcla)
        l2 = integrated(mezcla)
        if abs(l2 - OBJETIVO) < 0.15:
            break
        mezcla = mezcla * dbg(OBJETIVO - l2)
    mezcla = capa.limitador(mezcla)
    return mezcla.astype(np.float32), {"musica": origen, "lufs": round(float(integrated(mezcla)), 2),
                                       "pico_dbtp": round(float(D.true_peak(mezcla)), 2)}
