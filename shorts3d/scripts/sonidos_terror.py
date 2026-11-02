"""Música y efectos del Short de terror, hechos por código (no se paga nada).

LA MEZCLA SE DECIDE AQUÍ Y EN src/terror/spec.ts: la música sale normalizada al MISMO nivel RMS que la voz
(-20 dBFS, ver voz_terror.py), y la composición la pone 15 dB por debajo en los huecos y 18 dB por debajo
mientras habla. Así «15–18 dB bajo la voz» es una cuenta, no una impresión.
"""
import wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent / "public/terror"
(P).mkdir(parents=True, exist_ok=True)
SR = 48000
RMS_OBJETIVO = 10 ** (-20 / 20)
rng = np.random.default_rng(13)
def t(s): return np.arange(int(s * SR)) / SR
def lp(x, k):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
def lp_rapido(x, k):  # filtro de un polo vectorizado por bloques (para la música larga)
    from scipy.signal import lfilter
    return lfilter([k], [1, k - 1], x)
def save(name, x, rms=None):
    x = np.asarray(x, float)
    if rms: x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * rms
    else: x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    x = np.clip(x, -0.99, 0.99)
    with wave.open(str(P / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())

# ---- música: piano grave en menor (arpegio lento) + cuerdas suaves, 80 s, 70 BPM ----
try:
    import scipy  # noqa
    filt = lp_rapido
except ImportError:
    filt = lp
dur = 80.0; n = t(dur); mus = np.zeros(len(n))
nota = lambda m: 440 * 2 ** ((m - 69) / 12)
acordes = [[45, 52, 57, 60], [41, 48, 53, 57], [43, 50, 55, 58], [40, 47, 52, 56]]  # Am, F, Gm, E (tensión)
beat = 60 / 70
for k in range(int(dur / beat)):
    ac = acordes[(k // 8) % 4]; m = ac[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]] + 12
    st = k * beat; i0 = int(st * SR); seg = n[i0:i0 + int(2.5 * SR)] - st
    f = nota(m)
    tono = (np.sin(2 * np.pi * f * seg) + 0.4 * np.sin(4 * np.pi * f * seg) + 0.15 * np.sin(6 * np.pi * f * seg)) * np.exp(-seg * 2.2)
    mus[i0:i0 + len(seg)] += tono * (0.9 if k % 8 == 0 else 0.55)
for c in range(int(dur / (8 * beat)) + 1):
    ac = acordes[c % 4]; st = c * 8 * beat; i0 = int(st * SR); L = int(8 * beat * SR); seg = n[i0:i0 + L] - st
    env = np.minimum(1, seg / 1.5) * np.minimum(1, (8 * beat - seg) / 1.5)
    pad = sum(np.sin(2 * np.pi * nota(m) * seg + 0.3 * np.sin(2 * np.pi * 5 * seg)) for m in ac[:3])
    mus[i0:i0 + len(seg)] += pad * env * 0.18
mus = filt(mus, 0.25)
mus *= np.minimum(1, n / 1.0)
save("musica.wav", mus, rms=RMS_OBJETIVO)

# ---- stinger: golpe orquestal (acorde grave de metales + timbal + platillo) ----
n = t(3.0); x = np.zeros(len(n))
for m in [33, 40, 45, 48, 52]:
    f = nota(m); ph = 2 * np.pi * f * n
    x += sum(np.sin(k * ph) / k for k in range(1, 9)) * np.exp(-n * 1.3)
x += np.sin(2 * np.pi * 55 * n * (1 - 0.15 * n)) * np.exp(-n * 3) * 2.5
x += lp(rng.standard_normal(len(n)), 0.5) * np.exp(-n * 2.5) * 0.6
save("stinger.wav", x * np.minimum(1, n / 0.004))
# ---- golpe en la ventana: nudillo seco sobre madera y vidrio ----
n = t(0.35)
x = np.sin(2 * np.pi * 180 * n) * np.exp(-n * 40) + 0.6 * np.sin(2 * np.pi * 1900 * n) * np.exp(-n * 70) + 0.4 * rng.standard_normal(len(n)) * np.exp(-n * 160)
save("golpe.wav", x)
# ---- paso pesado ----
n = t(0.6)
save("paso.wav", np.sin(2 * np.pi * 48 * n * (1 - 0.3 * n)) * np.exp(-n * 9) + lp(rng.standard_normal(len(n)), 0.08) * np.exp(-n * 14) * 0.8)
# ---- trueno: chasquido + retumbo largo ----
n = t(3.2); x = lp(rng.standard_normal(len(n)), 0.02) * np.exp(-n * 1.1) * 3
x += rng.standard_normal(len(n)) * np.exp(-n * 25)
save("trueno.wav", x * np.minimum(1, n / 0.01))
# ---- grito agudo de la cosa: chirrido con vibrato y aspereza ----
n = t(1.3); f0 = 900 + 500 * np.minimum(1, n / 0.25) + 60 * np.sin(2 * np.pi * 9 * n)
ph = 2 * np.pi * np.cumsum(f0) / SR
x = (np.sin(ph) + 0.5 * np.sin(2.01 * ph) + 0.3 * np.sign(np.sin(3 * ph))) * (0.6 + 0.4 * rng.standard_normal(len(n)) * 0.3)
save("grito.wav", lp(x, 0.35) * np.minimum(1, n / 0.05) * np.exp(-n * 1.6))
# ---- puerta / ventana que cruje ----
n = t(1.4); f0 = 220 + 90 * np.sin(2 * np.pi * 0.7 * n)
pulsos = (np.sin(2 * np.pi * np.cumsum(f0) / SR) > 0.97).astype(float)
save("puerta.wav", lp(pulsos + 0.1 * rng.standard_normal(len(n)), 0.3) * np.sin(np.pi * n / 1.4))
save("crujido.wav", lp((np.sin(2 * np.pi * np.cumsum(140 + 60 * n) / SR) > 0.95).astype(float), 0.3)[: int(0.6 * SR)] * np.sin(np.pi * t(0.6) / 0.6))
# ---- latido ----
n = t(0.7); lat = lambda s: np.sin(2 * np.pi * 52 * (n - s)) * np.exp(-np.maximum(0, n - s) * 18) * (n >= s)
save("latido.wav", lat(0) + 0.7 * lat(0.22))
# ---- whoosh de transición ----
n = t(0.45); x = rng.standard_normal(len(n)); k = np.linspace(0.02, 0.4, len(n))
y = np.empty_like(x); acc = 0.0
for i in range(len(x)): acc += k[i] * (x[i] - acc); y[i] = acc
save("whoosh.wav", y * np.sin(np.pi * n / 0.45) ** 2)
print("sonidos de terror listos en", P)
