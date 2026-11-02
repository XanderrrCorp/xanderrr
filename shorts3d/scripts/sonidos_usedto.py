"""Música provisional y efectos de «Used To», hechos por código (gratis).

LA MÚSICA DE VERDAD va de la Biblioteca de audio de YouTube (Jazz & Blues o Acústica, ánimo Happy/Bright) o de
Pixabay: se descarga en el PC del dueño y se guarda como public/usedto/musica.wav (la misma en todos los videos,
para que el sonido sea la marca). Esta es solo una cama de jazz acústico a 110 BPM para ensayar la mezcla.
La música y la voz quedan al mismo RMS (-20 dBFS) y la composición pone la música 15–18 dB por debajo.
"""
import wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent / "public/usedto"
P.mkdir(parents=True, exist_ok=True)
SR = 48000
rng = np.random.default_rng(7)
def t(s): return np.arange(int(s * SR)) / SR
def save(name, x, rms=None):
    x = np.asarray(x, float)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * rms if rms else x / (np.max(np.abs(x)) + 1e-9) * 0.89
    with wave.open(str(P / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -0.99, 0.99) * 32767).astype(np.int16).tobytes())
def lp(x, k):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
nota = lambda m: 440 * 2 ** ((m - 69) / 12)
def pulsada(f, dur, brillo=0.5):
    """cuerda pulsada (Karplus-Strong vectorizado por periodos)"""
    n = int(dur * SR); L = max(2, int(SR / f)); buf = rng.uniform(-1, 1, L); out = np.empty(n)
    for i in range(0, n, L):
        k = min(L, n - i); out[i:i + k] = buf[:k]
        buf = brillo * buf + (1 - brillo) * np.roll(buf, 1); buf *= 0.996
    return out * np.exp(-np.arange(n) / SR * 2.2)

# ---- música: guitarra jazz (acordes ii-V-I con swing) + contrabajo caminando + escobillas, 110 BPM ----
bpm = 110; beat = 60 / bpm; dur = 84.0; mus = np.zeros(int(dur * SR) + SR * 3)
prog = [[50, 53, 57, 60], [43, 47, 50, 53], [48, 52, 55, 59], [45, 49, 52, 55]]  # Dm7 G7 Cmaj7 A7
bajo = [[38, 41, 45, 43], [31, 35, 38, 40], [36, 40, 43, 45], [33, 37, 40, 41]]
for b in range(int(dur / beat)):
    c = (b // 4) % 4; st = b * beat; i0 = int(st * SR)
    x = pulsada(nota(bajo[c][b % 4]), beat * 1.1, 0.35) * 1.3; mus[i0:i0 + len(x)] += x
    if b % 4 in (1, 3):  # guitarra en los tiempos débiles, con swing
        for k, m in enumerate(prog[c]):
            j = i0 + int((0.02 * k + (0.08 if b % 2 else 0)) * SR); x = pulsada(nota(m + 12), 0.6, 0.55) * 0.5; mus[j:j + len(x)] += x
    for sw in (0, 0.66):  # escobilla
        j = i0 + int(sw * beat * SR); n = t(0.12); x = rng.standard_normal(len(n)) * np.exp(-n * 30) * (0.25 if sw else 0.4); mus[j:j + len(x)] += x
mus = mus[: int(dur * SR)] * np.minimum(1, t(dur) / 0.5)
save("musica.wav", mus, rms=10 ** (-20 / 20))

# ---- efectos: uno por acción visible ----
n = t(0.5); save("crujido.wav", lp((np.sin(2 * np.pi * np.cumsum(90 + 40 * n) / SR) > 0.93).astype(float) + 0.05 * rng.standard_normal(len(n)), 0.25) * np.sin(np.pi * n / 0.5))
n = t(0.45); save("chasquido.wav", rng.standard_normal(len(n)) * np.exp(-n * 45) + np.sin(2 * np.pi * 420 * n) * np.exp(-n * 25) * 0.6)
n = t(0.9); save("golpe.wav", np.sin(2 * np.pi * 70 * n * (1 - 0.25 * n)) * np.exp(-n * 7) + lp(rng.standard_normal(len(n)), 0.15) * np.exp(-n * 12) * 0.9 + sum(np.sin(2 * np.pi * f * n) * np.exp(-n * d) * 0.2 for f, d in [(1180, 18), (1730, 22)]))
n = t(0.18); save("clic.wav", np.sin(2 * np.pi * 2600 * n) * np.exp(-n * 90) + rng.standard_normal(len(n)) * np.exp(-n * 200) * 0.5)
n = t(1.4); save("ding.wav", sum(np.sin(2 * np.pi * f * n) * np.exp(-n * d) * a for f, d, a in [(1760, 2.2, 1), (3520, 3.5, 0.35), (5280, 5, 0.15)]))
n = t(0.7); x = np.zeros(len(n))
for k in range(9): s0 = int(k * 0.07 * SR); m = n[: len(n) - s0]; x[s0:] += (np.sin(2 * np.pi * 3100 * m) * np.exp(-m * 120) + rng.standard_normal(len(m)) * np.exp(-m * 300) * 0.4)
save("trinquete.wav", x)
n = t(0.6); f0 = 300 + 900 * np.exp(-n * 9); save("resorte.wav", np.sin(2 * np.pi * np.cumsum(f0) / SR) * np.exp(-n * 5) * (1 + 0.5 * np.sin(2 * np.pi * 38 * n)))
n = t(1.0); save("clank.wav", sum(np.sin(2 * np.pi * f * n) * np.exp(-n * d) for f, d in [(410, 6), (987, 9), (1530, 12), (2650, 16)]) + rng.standard_normal(len(n)) * np.exp(-n * 80))
n = t(0.5); save("hacha.wav", lp(rng.standard_normal(len(n)), np.linspace(0.05, 0.5, len(n))[0]) * np.sin(np.pi * n / 0.5) ** 2 * 0.6 + np.concatenate([np.zeros(int(0.32 * SR)), rng.standard_normal(len(n) - int(0.32 * SR)) * np.exp(-t(0.5 - 0.32) * 50)]))
n = t(2.0); save("zumbido.wav", (np.sin(2 * np.pi * np.cumsum(60 + 140 * n) / SR) + 0.4 * np.sign(np.sin(2 * np.pi * np.cumsum(120 + 280 * n) / SR))) * np.minimum(1, n / 0.2) * np.exp(-np.maximum(0, n - 1.5) * 6))
n = t(1.5); save("giro.wav", np.sin(2 * np.pi * np.cumsum(140 + 60 * n) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * (4 + 6 * n) * n)) * np.minimum(1, n / 0.3) * np.exp(-np.maximum(0, n - 1.1) * 5))
n = t(0.6); x = rng.standard_normal(len(n)); save("barrido.wav", lp(x, 0.08) * np.sin(np.pi * n / 0.6) ** 2)
print("sonidos de Used To listos en", P)
