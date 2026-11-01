"""Sonidos del Short de la pantera, hechos por código."""
import wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent / "public/pantera"
SR = 48000
rng = np.random.default_rng(11)
def save(name, x):
    x = np.asarray(x, float); x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    with wave.open(str(P / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
def t(s): return np.arange(int(s * SR)) / SR
def lp(x, k):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
# gruñido grave: tono bajo con aspereza y ruido filtrado
n = t(1.6); f0 = 62 + 10 * np.sin(2 * np.pi * 0.8 * n)
ph = 2 * np.pi * np.cumsum(f0) / SR
x = sum(np.sin(k * ph) / k ** 0.8 for k in range(1, 18)) * (0.7 + 0.3 * np.sin(2 * np.pi * 23 * n))
x = lp(x + 0.6 * rng.standard_normal(len(n)) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * n)), 0.06)
save("sfx/gruñido.wav", x * np.sin(np.pi * n / 1.6) ** 0.7)
# corte: whoosh corto y suave
n = t(0.32); x = rng.standard_normal(len(n))
save("sfx/corte.wav", lp(x, 0.12) * np.sin(np.pi * n / 0.32) ** 2)
# brillo: barrido de luz (campanitas que suben)
n = t(1.4); x = np.zeros(len(n))
for k, fr in enumerate([1320, 1760, 2093, 2637, 3136]):
    st = k * 0.12; m = n >= st; u = n[m] - st
    x[m] += np.sin(2 * np.pi * fr * u) * np.exp(-u * 4)
save("sfx/brillo.wav", x)
# crujido del caparazón: chasquidos secos y graves
n = t(0.7); x = np.zeros(len(n))
for k in range(9):
    st = 0.015 * k + rng.uniform(0, 0.02); m = n >= st; u = n[m] - st
    x[m] += rng.standard_normal(m.sum()) * np.exp(-u * rng.uniform(60, 120)) * rng.uniform(0.4, 1)
x += np.sin(2 * np.pi * 85 * n) * np.exp(-n * 14) * 0.8
save("sfx/crujido.wav", x)
# (sin ambiente de selva: el grillo sintético sonaba como un zumbido durante todo el video)
print("listo")

# --- Short de los departamentos: campanita y tecleo ---
C = pathlib.Path(__file__).resolve().parent.parent / "public/colombia/sfx"
C.mkdir(parents=True, exist_ok=True)
def save_c(name, x):
    x = np.asarray(x, float); x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    with wave.open(str(C / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
n = t(1.2)
save_c("campanita.wav", sum(np.sin(2 * np.pi * fr * n) * np.exp(-n * d) for fr, d in [(1568, 3), (2349, 4), (3136, 5)]) * (1 + 0.3 * np.sin(2 * np.pi * 9 * n)))
n = t(1.2); x = np.zeros(len(n))
for k in range(14):
    st = k * 0.08 + rng.uniform(0, 0.02); m = (n >= st) & (n < st + 0.03); u = n[m] - st
    x[m] += rng.standard_normal(m.sum()) * np.exp(-u * 300)
save_c("tecleo.wav", x)
print("colombia listo")
