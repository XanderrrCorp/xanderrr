"""Capa de audio de Peligro Tropical (solo canal animales-peligrosos; se prende y apaga por canal).

Entra: la voz final + sus frases (con intención) y sus palabras con tiempo (Whisper si está; si no, repartidas por
letras dentro de cada frase). Sale: música ORIGINAL sintetizada que cambia por sección, efectos sintetizados en
palabras clave, la música bajando sola bajo la voz, y master a -14 LUFS integrado con pico ≤ -1 dBTP.

Música por sección:
  hook      → drone grave + pulso
  tranquilo → marimba y guitarra cálidas (Re mayor)
  peligro   → la misma música, que se desafina poco a poco + drone en segunda menor
  mordida   → SILENCIO total de la música (≈1,2 s) en la palabra de la mordedura o picadura
  veneno    → pulso tenso grave (y latidos)
  remate    → una sola nota
Efectos: golpe (mordedura/picadura), destello, pasos en barro, roce de hojas, zumbido, latidos.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

from . import dsp as D
from . import instruments as I
from .dsp import SR, TAU, dbg, integrated, ns, rng, true_peak

OBJETIVO_LUFS = -14.0
TECHO_DBTP = -1.25                     # el limitador apunta un poco más abajo para quedar ≤ -1 dBTP medido
VOZ_LUFS = -18.0                        # la voz se lleva aquí antes de mezclar
MUSICA_BAJO_VOZ = -21.0                 # LU de la música (sin agachar) respecto a la voz (07-11: -15 sonaba muy duro)
AGACHE_DB = -9.0                        # cuánto baja la música mientras se habla
CANAL_PT = "animales-peligrosos"


# ------------------------------------------------------------------ activación por canal
AJUSTE = "audio_animado"
# (07-11) APAGADA otra vez: en el primer video real el dueño dijo «la música es pésima: se escucha muy duro y se repite
# la canción mucho sin nada que la difumine». Vuelve la música de su biblioteca (la de siempre). Se prende por canal con
# Canal.ajustes["audio_animado"] = True solo si él lo pide tras oír la versión arreglada (más baja y con cruces largos).
PRENDIDA_POR_DEFECTO = False


def activa(canal: str | None, ajustes: dict | None = None) -> bool:
    """Solo en Peligro Tropical (el dueño: «solo en Peligro Tropical»); cualquier otro canal: apagada aunque lo pida."""
    if canal != CANAL_PT:
        return False
    if ajustes is not None:
        valor = ajustes.get(AJUSTE)
    else:
        from ...plataforma.consultas import ajuste_canal

        valor = ajuste_canal(canal, AJUSTE)
    return PRENDIDA_POR_DEFECTO if valor is None else bool(valor)


def frases_de_escenas(escenas) -> list[dict]:
    """Las escenas del proyecto (con su tiempo real en la voz) como frases para la capa de audio."""
    out = []
    for e in escenas:
        ini, fin = e.tiempo.real_inicio, e.tiempo.real_fin
        if ini is None or fin is None:
            continue
        out.append({"seccion": e.seccion, "intencion": str(getattr(e.intencion, "value", e.intencion)),
                    "texto": e.narracion, "ini": float(ini), "fin": float(fin)})
    return out


def mezclar_para_render(voz_mono: np.ndarray, sr: int, otros_sfx: np.ndarray, datos: dict) -> np.ndarray:
    """Lo que usa render.mezclar_audio: voz y efectos del video (mono a sr) → mezcla mono a sr con la capa."""
    def a48(x):
        return x if sr == SR else signal.resample_poly(x, SR, sr)
    def de48(x):
        return x if sr == SR else signal.resample_poly(x, sr, SR)
    voz = a48(np.asarray(voz_mono, float))
    otros = a48(np.asarray(otros_sfx, float))
    res = construir(voz, datos["frases"], datos.get("palabras"), otros_sfx=otros, semilla=int(datos.get("semilla", 7)))
    mono = de48(res.mezcla.mean(0))
    n = len(voz_mono)
    return np.pad(mono, (0, max(0, n - len(mono))))[:n].astype(np.float32)


# ------------------------------------------------------------------ palabras y secciones
def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def palabras_estimadas(frases: list[dict]) -> list[dict]:
    """Sin Whisper: reparte el tiempo de cada frase entre sus palabras según las letras."""
    out = []
    for k, f in enumerate(frases):
        pal = f["texto"].split()
        letras = sum(len(p) + 1 for p in pal) or 1
        t = f["ini"]
        dur = f["fin"] - f["ini"]
        for p in pal:
            d = dur * (len(p) + 1) / letras
            out.append({"w": p, "ini": round(t, 3), "fin": round(t + d, 3), "frase": k})
            t += d
    return out


def palabras_whisper(voz_wav: Path, frases: list[dict]) -> list[dict] | None:
    """Tiempos reales por palabra con faster-whisper (en el PC del dueño). None si no está instalado."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    modelo = WhisperModel("small", device="auto", compute_type="int8")
    segs, _ = modelo.transcribe(str(voz_wav), language="es", word_timestamps=True)
    out = []
    for s in segs:
        for w in s.words or []:
            out.append({"w": w.word.strip(), "ini": round(w.start, 3), "fin": round(w.end, 3)})
    for p in out:                                                       # a qué frase pertenece
        p["frase"] = next((k for k, f in enumerate(frases) if f["ini"] - 0.3 <= p["ini"] < f["fin"] + 0.3), len(frases) - 1)
    return out


MORDIDA = r"(muerde|mordi|mordid|mordedura|muerden|pica\b|picad|picó|pico\b|clava|aguij|ataca\b|atacó)"
VENENO = r"(veneno|venen|toxin|neurotox|sangre|coagul|ponzoñ)"
SFX_PALABRAS = [
    ("golpe", MORDIDA, 0.0),
    ("destello", r"(destell|brill|relampag)", 6.0),
    ("pasos", r"(camin|pasos|pisas|pisan|barro|potrero|trocha)", 8.0),
    ("hojas", r"(hojas|pasto|monte\b|selva|arbust|matorral|hierba|maleza)", 8.0),
    ("zumbido", r"(zumb|zancud|mosquit|abeja|avispa|mosca)", 6.0),
    ("latidos", r"(corazon|latid|late\b|acelera|miedo|panico)", 8.0),
]


def secciones(frases: list[dict], palabras: list[dict], dur: float) -> tuple[list[dict], list[float]]:
    """Mapa de música: [{tipo, ini, fin}] y los instantes de mordida (silencio + golpe)."""
    mordidas = [p["ini"] for p in palabras if re.match(MORDIDA, _norm(p["w"]))]
    tipos = []
    tras_mordida = False
    for k, f in enumerate(frases):
        intn, txt = f.get("intencion", ""), _norm(f["texto"])
        if intn == "gancho" or (f.get("seccion") or "").startswith("gancho"):
            t = "hook"
        elif any(f["ini"] - 0.05 <= m <= f["fin"] for m in mordidas):
            t, tras_mordida = "peligro", True
        elif intn in ("cierre", "giro", "llamado_accion") and k >= len(frases) - 3:
            t = "remate"
        elif tras_mordida and (re.search(VENENO, txt) or intn in ("explicacion", "dato_impactante", "comparacion")):
            t = "veneno"
        elif intn in ("amenaza", "tension_creciente", "advertencia", "revelacion"):
            t = "peligro"
        else:
            t, tras_mordida = "tranquilo", False
        tipos.append(t)
    out = []
    for f, t in zip(frases, tipos):
        if out and out[-1]["tipo"] == t:
            out[-1]["fin"] = f["fin"]
        else:
            out.append({"tipo": t, "ini": f["ini"], "fin": f["fin"]})
    for a, b in zip(out, out[1:]):                                         # sin huecos: cada sección hasta la siguiente
        a["fin"] = b["ini"]
    out[0]["ini"], out[-1]["fin"] = 0.0, dur
    return out, mordidas


# ------------------------------------------------------------------ instrumentos propios
def m2f(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def marimba(f, vel, r, dur=1.1):
    """barra de marimba: parciales 1 / 3,93 / 9,2 con caída rápida en los agudos + golpe de mazo blando"""
    t = D.tt(dur)
    y = (np.sin(TAU * f * t) * np.exp(-t / 0.42) + 0.32 * np.sin(TAU * f * 3.93 * t) * np.exp(-t / 0.09)
         + 0.08 * np.sin(TAU * f * 9.2 * t) * np.exp(-t / 0.03))
    y += D.lp(r.standard_normal(len(t)), 1800) * np.exp(-t / 0.004) * 0.15
    return D.fades(y * vel * (1 - np.exp(-t / 0.001)), 0.0005, 0.05)


def guitarra(notas_f, vel, r, dur=1.8, rasgueo=0.018):
    """rasgueo cálido: cuerdas pulsadas (pluck de la skill) una tras otra"""
    n = ns(dur + rasgueo * len(notas_f))
    y = np.zeros(n)
    for k, f in enumerate(notas_f):
        x = I.pluck(f, vel=vel * (0.9 - 0.06 * k), r=r, dur=dur, bright=0.32, pos=0.2)
        i = ns(k * rasgueo)
        y[i:i + len(x)] += x[: n - i]
    return D.lp(y, 3200)


ACORDES = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]     # Re – La – Si menor – Sol
BAJOS = [50, 45, 47, 43]


def _desafino(t_rel, total, r):
    """cents de desafinación que crecen en la sección de peligro (deriva aleatoria hasta ±45)"""
    prog = min(1.0, max(0.0, t_rel / max(total, 1e-3)))
    return r.normal(0, 1) * 45 * prog ** 1.3 + 25 * prog * np.sin(t_rel * 1.7)


def musica_tranquila(ini, fin, r, desafinar=False, tempo=96):
    """marimba (corcheas en arpegio) + guitarra (tiempos 1 y 3), un acorde por compás"""
    n = ns(fin - ini + 2.5)
    out = np.zeros((2, n))
    b = 60 / tempo
    compas, k = 4 * b, 0
    t = 0.0
    while t < fin - ini:
        ac = ACORDES[k % 4]
        for j in range(8):
            tj = t + j * b / 2
            if tj >= fin - ini:
                break
            m = ac[[0, 1, 2, 1, 2, 0, 1, 2][j]] + 12
            c = _desafino(tj, fin - ini, r) if desafinar else 0
            x = marimba(m2f(m) * 2 ** (c / 1200), 0.38 if j % 2 == 0 else 0.26, r)
            D.place(out, D.pan(x, -0.35 + 0.1 * (j % 3)), tj)
        for tb in (0, 2):
            tj = t + tb * b
            if tj >= fin - ini:
                break
            c = _desafino(tj, fin - ini, r) if desafinar else 0
            notas = [m2f(m) * 2 ** ((c + r.normal(0, 6 if desafinar else 1)) / 1200) for m in [BAJOS[k % 4]] + ac]
            D.place(out, D.pan(guitarra(notas, 0.34, r), 0.3), tj)
        t += compas
        k += 1
    if desafinar:                                                           # drone en segunda menor que entra
        d = I.pad([m2f(38), m2f(39)], fin - ini, vel=0.22, r=r, att=(fin - ini) * 0.6, rel=0.8, warm=420, detune=14)
        D.place(out, d, 0.0)
    return out


def musica_hook(ini, fin, r, tempo=96):
    """drone grave (Re + La) + pulso de golpe sordo en cada tiempo que crece, y brillo agudo al final"""
    dur = fin - ini
    out = np.zeros((2, ns(dur + 2.0)))
    D.place(out, I.pad([m2f(38), m2f(45), m2f(50)], dur, vel=0.5, r=r, att=0.8, rel=1.2, warm=520, detune=9), 0.0)
    b = 60 / tempo
    t = 0.0
    while t < dur:
        tt_ = D.tt(0.45)
        f = 52 * (1 + 0.5 * np.exp(-tt_ / 0.03))
        x = np.sin(TAU * np.cumsum(f) / SR) * np.exp(-tt_ / 0.14) * (0.45 + 0.4 * t / max(dur, 1))
        D.place(out, D.st(x), t)
        t += b
    return out


def musica_veneno(ini, fin, r, tempo=112):
    """pulso tenso: corcheas graves con filtro que respira + agudo en semitono, sin melodía"""
    dur = fin - ini
    out = np.zeros((2, ns(dur + 1.5)))
    b = 60 / tempo / 2
    t, k = 0.0, 0
    while t < dur:
        tt_ = D.tt(0.24)
        f = m2f(38 if k % 4 else 37)
        saw = 2 * ((f * tt_) % 1) - 1
        x = D.lp(saw, 260 + 160 * (1 + np.sin(t * 0.9))) * np.exp(-tt_ / 0.09) * 0.42
        D.place(out, D.st(x), t)
        if k % 8 == 4:
            g = I.vibes(m2f(75), vel=0.12, r=r, dur=0.8, trem_depth=0.0)
            D.place(out, D.pan(g, 0.4), t)
        t += b
        k += 1
    D.place(out, I.pad([m2f(50), m2f(51)], dur, vel=0.12, r=r, att=1.5, rel=1.0, warm=700, detune=20), 0.0)
    return out


def musica_remate(ini, fin, r):
    """una sola nota: vibráfono agudo + grave suave, y nada más"""
    out = np.zeros((2, ns(fin - ini + 4.0)))
    D.place(out, D.pan(I.vibes(m2f(74), vel=0.5, r=r, dur=3.2, trem_depth=0.12), 0.1), 0.15)
    D.place(out, D.st(I.pluck(m2f(38), vel=0.4, r=r, dur=3.0, bright=0.2)), 0.15)
    return out


# ------------------------------------------------------------------ efectos sintetizados
def sfx_golpe(r):
    t = D.tt(0.9)
    boom = np.sin(TAU * np.cumsum(70 * np.exp(-t / 0.18) + 38) / SR) * np.exp(-t / 0.28)
    crack = D.hp(r.standard_normal(len(t)), 1800) * np.exp(-t / 0.012) * 0.7
    cuerpo = D.bp(r.standard_normal(len(t)), 120, 900) * np.exp(-t / 0.05) * 0.6
    return D.st(D.fades(boom * 0.9 + crack + cuerpo, 0.0005, 0.1))


def sfx_destello(r):
    t = D.tt(0.7)
    f = 900 + 5200 * (t / 0.7) ** 1.6
    ruido = r.standard_normal(len(t))
    barrido = D.reson(ruido, 3000, 2.0) * 0.0 + D.bp(ruido, 2500, 9000) * (t / 0.7) ** 2
    campana = np.sin(TAU * np.cumsum(f) / SR) * 0.15 * np.exp(-((t - 0.55) / 0.12) ** 2)
    brillo = I.glock(m2f(98), vel=0.35, r=r, dur=0.9)
    y = barrido * 0.5 + campana
    y = np.pad(y, (0, max(0, len(brillo) - len(y))))
    y[ns(0.5):ns(0.5) + len(brillo)] += brillo[: len(y) - ns(0.5)]
    return D.pan(D.fades(y, 0.02, 0.1), 0.0)


def sfx_pasos(r, n=4, intervalo=0.42):
    out = np.zeros((2, ns(n * intervalo + 0.5)))
    for k in range(n):
        t = D.tt(0.32)
        golpe = np.sin(TAU * np.cumsum(r.uniform(70, 95) * (1 + 0.3 * np.exp(-t / 0.02))) / SR) * np.exp(-t / 0.05)
        ruido = r.standard_normal(len(t))
        chapoteo = D.bp(ruido, 300, 1400) * np.exp(-t / 0.09) * (0.6 + 0.4 * np.sin(TAU * r.uniform(30, 55) * t))
        succion = D.bp(ruido, 600, 2200) * np.exp(-((t - 0.16) / 0.05) ** 2) * 0.35
        D.place(out, D.pan(golpe * 0.8 + chapoteo * 0.7 + succion, -0.3 if k % 2 else 0.3), k * intervalo)
    return out


def sfx_hojas(r, dur=1.0):
    t = D.tt(dur)
    ruido = D.bp(r.standard_normal(len(t)), 2200, 7000)
    env = np.clip(np.sin(np.pi * t / dur), 0, 1) ** 0.7 * (0.5 + 0.5 * D.smooth_noise(len(t), r, 9))
    chasquidos = np.zeros(len(t))
    for _ in range(int(dur * 22)):
        i = r.integers(0, len(t) - 200)
        chasquidos[i:i + 120] += D.hp(r.standard_normal(120), 3000) * np.exp(-np.arange(120) / 25) * r.uniform(0.3, 1)
    return D.pan(ruido * env * 0.5 + chasquidos * 0.4, 0.35)


def sfx_zumbido(r, dur=1.5):
    t = D.tt(dur)
    f = 230 + 25 * np.sin(TAU * 1.3 * t) + 40 * (t / dur)
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    am = 0.6 + 0.4 * np.sin(TAU * 31 * t)
    env = np.sin(np.pi * t / dur) ** 0.8
    x = D.bp(saw * am, 300, 3200) * env * 0.5
    pan_t = np.sin(TAU * 0.6 * t)
    return np.vstack([x * (1 - 0.4 * pan_t), x * (1 + 0.4 * pan_t)]) * 0.7


def sfx_latidos(r, n=4, intervalo=0.82):
    out = np.zeros((2, ns(n * intervalo + 0.4)))
    for k in range(n):
        for dt, a in ((0.0, 1.0), (0.17, 0.7)):
            t = D.tt(0.25)
            x = np.sin(TAU * np.cumsum(48 * (1 + 0.6 * np.exp(-t / 0.02))) / SR) * np.exp(-t / 0.07) * a
            D.place(out, D.st(D.lp(x, 180)), k * intervalo + dt)
    return out


SFX = {"golpe": (sfx_golpe, -2.0), "destello": (sfx_destello, -10.0), "pasos": (sfx_pasos, -9.0),
       "hojas": (sfx_hojas, -11.0), "zumbido": (sfx_zumbido, -12.0), "latidos": (sfx_latidos, -5.0)}


def eventos_sfx(palabras: list[dict], destellos: list[float] = (), secs: list[dict] = ()) -> list[dict]:
    """Qué efecto va en qué palabra (con separación mínima por tipo para no saturar)."""
    ev, ultimo = [], {}
    for p in palabras:
        w = _norm(p["w"])
        for tipo, patron, sep in SFX_PALABRAS:
            if re.match(patron, w) and p["ini"] - ultimo.get(tipo, -99) >= sep:
                ev.append({"tipo": tipo, "t": round(max(0.0, p["ini"] - 0.03), 3), "palabra": p["w"]})
                ultimo[tipo] = p["ini"]
    for t in destellos:
        ev.append({"tipo": "destello", "t": round(max(0.0, t - 0.45), 3), "palabra": "(destello visual)"})
    for s in secs:                                                          # el veneno entra con latidos
        if s["tipo"] == "veneno" and s["ini"] - ultimo.get("latidos", -99) >= 4:
            ev.append({"tipo": "latidos", "t": round(s["ini"] + 0.1, 3), "palabra": "(entra el veneno)"})
            ultimo["latidos"] = s["ini"]
    return sorted(ev, key=lambda e: e["t"])


# ------------------------------------------------------------------ mezcla
def _actividad_voz(voz: np.ndarray, umbral_db=-38.0) -> np.ndarray:
    """1 donde hay voz (envolvente RMS 30 ms), a 1000 Hz de control."""
    paso = SR // 1000
    n = len(voz) // paso
    pot = (voz[: n * paso] ** 2).reshape(n, paso).mean(1)
    rms = np.sqrt(np.maximum(ndimage.uniform_filter1d(pot, 30), 0))
    return (20 * np.log10(rms + 1e-9) > umbral_db).astype(float)


def _agache(act: np.ndarray, n_muestras: int, prof=AGACHE_DB, ataque=0.07, suelta=0.45) -> np.ndarray:
    ctrl = 1000
    act = ndimage.maximum_filter1d(act, int(0.2 * ctrl))                   # cubre huecos cortos entre palabras
    ka, kr = 1 - np.exp(-1 / (ataque * ctrl)), 1 - np.exp(-1 / (suelta * ctrl))
    env = np.zeros(len(act))
    e = 0.0
    for i, v in enumerate(act):
        e += (v - e) * (ka if v > e else kr)
        env[i] = e
    return np.interp(np.arange(n_muestras) / SR, np.arange(len(act)) / ctrl, prof * env)


def limitador(x, techo_db=TECHO_DBTP, look=0.003, rel=0.08):
    """limitador con detección 4x sobremuestreada y anticipación (el de la skill, mix.py)"""
    c = dbg(techo_db)
    n = x.shape[1]
    up = np.abs(signal.resample_poly(x, 4, 1, axis=-1)).max(0)
    pk = np.pad(up, (0, max(0, 4 * n - len(up))))[: 4 * n].reshape(n, 4).max(1)
    gr = np.minimum(1.0, c / np.maximum(pk, 1e-12))
    la = max(1, ns(look))
    g1 = ndimage.minimum_filter1d(gr, 2 * la + 1, mode="nearest")
    kr = 1 - np.exp(-1 / (rel * SR))
    g2 = g1.copy()
    idx = np.flatnonzero(g1 < 1.0)
    if len(idx):
        g = 1.0
        ini = idx[0]
        for i in range(ini, min(n, idx[-1] + ns(rel * 8))):
            g = min(g1[i], g + (1 - g) * kr)
            g2[i] = g
    g3 = np.minimum(1.0, ndimage.uniform_filter1d(g2, 2 * la + 1, mode="nearest"))
    return x * g3[None, :]


@dataclass
class Resultado:
    mezcla: np.ndarray
    musica: np.ndarray
    sfx: np.ndarray
    voz: np.ndarray
    secciones: list
    eventos: list
    lufs: float
    pico_dbtp: float


GENERADORES = {"hook": musica_hook, "tranquilo": musica_tranquila, "peligro": lambda a, b, r: musica_tranquila(a, b, r, desafinar=True),
               "veneno": musica_veneno, "remate": musica_remate}


def construir(voz: np.ndarray, frases: list[dict], palabras: list[dict] | None = None, destellos: list[float] = (),
              otros_sfx: np.ndarray | None = None, semilla: int = 7) -> Resultado:
    """voz: mono float a 48 kHz (la voz final ya colocada). otros_sfx: los efectos que ya tenga el video (estéreo)."""
    r = rng(semilla)
    dur = len(voz) / SR
    n = len(voz)
    palabras = palabras or palabras_estimadas(frases)
    secs, mordidas = secciones(frases, palabras, dur)
    # 1) voz a -18 LUFS
    v = D.st(voz)
    lv = integrated(v)
    v = v * dbg(VOZ_LUFS - lv) if np.isfinite(lv) else v
    # 2) música por sección, con cruces cortos
    m = np.zeros((2, n + ns(4)))
    for k, s in enumerate(secs):
        x = GENERADORES[s["tipo"]](s["ini"], s["fin"], r)
        largo = ns(s["fin"] - s["ini"]) + ns(2.5)                     # (07-11) cruce largo: una parte se funde en la otra
        x = x[:, :largo]
        fo = min(x.shape[1], ns(2.5))
        x[:, :min(x.shape[1], ns(2.0))] *= np.linspace(0, 1, min(x.shape[1], ns(2.0)))[None, :] if k else 1.0
        x[:, -fo:] *= np.linspace(1, 0, fo)[None, :]
        D.place(m, x, s["ini"])
    m = m[:, :n]
    lm = integrated(m)
    if np.isfinite(lm):
        m *= dbg(VOZ_LUFS + MUSICA_BAJO_VOZ - lm)
    # 3) se agacha bajo la voz y sube en las pausas; silencio total en cada mordida
    g = _agache(_actividad_voz(voz), n)
    for t0 in mordidas:
        a, b = ns(max(0, t0 - 0.02)), ns(t0 + 1.25)
        g[a:b] = -120.0
        sube = ns(0.6)                                                       # vuelve suave
        g[b:b + sube] = np.minimum(g[b:b + sube], np.linspace(-40, 0, len(g[b:b + sube])))
    m = m * dbg(g)[None, :]
    # 4) efectos
    ev = eventos_sfx(palabras, destellos, secs)
    fx = np.zeros((2, n + ns(5)))
    for e in ev:
        gen, db = SFX[e["tipo"]]
        x = gen(rng(semilla + int(e["t"] * 100)))
        x = x / (np.abs(x).max() + 1e-9) * dbg(db) * dbg(VOZ_LUFS + 12)    # nivel relativo a la voz
        D.place(fx, x, e["t"])
    fx = fx[:, :n]
    if otros_sfx is not None:
        fx += D.st(otros_sfx)[:, :n] * dbg(-3)
    # 5) master a -14 LUFS y pico ≤ -1 dBTP
    mezcla = v + m + fx
    lmx = integrated(mezcla)
    mezcla = mezcla * dbg(OBJETIVO_LUFS - lmx)
    for _ in range(3):
        mezcla = limitador(mezcla)
        l2 = integrated(mezcla)
        if abs(l2 - OBJETIVO_LUFS) < 0.15:
            break
        mezcla = mezcla * dbg(OBJETIVO_LUFS - l2)
    mezcla = limitador(mezcla)
    return Resultado(mezcla, m, fx, v, secs, ev, round(float(integrated(mezcla)), 2), round(float(true_peak(mezcla)), 2))


NOMBRE_SECCION = {"hook": "Hook: drone grave + pulso que crece", "tranquilo": "Capítulo tranquilo: marimba + guitarra cálidas (Re mayor)",
                  "peligro": "Peligro: la misma música se desafina + drone en segunda menor",
                  "veneno": "Veneno: pulso tenso grave + latidos", "remate": "Remate: una sola nota"}


def resumen(res: Resultado) -> str:
    def mmss(t):
        return f"{int(t // 60)}:{t % 60:04.1f}"
    filas = ["| Desde | Hasta | Sección | Música |", "|---|---|---|---|"]
    for s in res.secciones:
        filas.append(f"| {mmss(s['ini'])} | {mmss(s['fin'])} | {s['tipo']} | {NOMBRE_SECCION[s['tipo']]} |")
    filas += ["", "| Momento | Efecto | En la palabra |", "|---|---|---|"]
    for e in res.eventos:
        filas.append(f"| {mmss(e['t'])} | {e['tipo']} | {e['palabra']} |")
    filas += ["", f"Master: {res.lufs} LUFS integrado · pico {res.pico_dbtp} dBTP. Silencio total de la música en cada mordida."]
    return "\n".join(filas)


def guardar(res: Resultado, carpeta: Path) -> dict:
    carpeta.mkdir(parents=True, exist_ok=True)
    D.write_wav(str(carpeta / "mezcla.wav"), res.mezcla)
    D.write_wav(str(carpeta / "pista_musica.wav"), res.musica)
    D.write_wav(str(carpeta / "pista_efectos.wav"), res.sfx)
    (carpeta / "resumen_audio.md").write_text(resumen(res), encoding="utf-8")
    datos = {"secciones": res.secciones, "efectos": res.eventos, "lufs": res.lufs, "pico_dbtp": res.pico_dbtp}
    (carpeta / "audio_animado.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return datos
