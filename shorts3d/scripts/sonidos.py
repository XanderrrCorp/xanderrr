"""Efectos y música de suspenso sintetizados por código (sin derechos de terceros)."""
import wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent / "public/audio"
SR = 48000
rng = np.random.default_rng(7)

def save(name, x, stereo=False):
    x = np.asarray(x, dtype=np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    d = (x * 32767).astype(np.int16)
    with wave.open(str(P / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())

def t(sec): return np.arange(int(sec * SR)) / SR
def env(n, a, r):
    e = np.ones(n); A = int(a * SR); R = int(r * SR)
    if A: e[:A] = np.linspace(0, 1, A)
    if R: e[-R:] *= np.linspace(1, 0, R)
    return e
def lp(x, k):  # pasa bajos simple de un polo
    y = np.zeros_like(x); a = k; acc = 0.0
    for i in range(len(x)): acc += a * (x[i] - acc); y[i] = acc
    return y
def lpv(x, ks):  # pasa bajos variable
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc += ks[i] * (x[i] - acc); y[i] = acc
    return y

# whoosh: ruido con barrido de filtro
n = t(0.7); x = rng.standard_normal(len(n))
ks = 0.02 + 0.25 * np.sin(np.pi * n / 0.7) ** 2
save("sfx/whoosh.wav", lpv(x, ks) * np.sin(np.pi * n / 0.7) ** 1.5)
# zumbido grave del avispón (diente de sierra con aleteo)
n = t(3.2); f0 = 118 + 6 * np.sin(2 * np.pi * 0.7 * n)
ph = 2 * np.pi * np.cumsum(f0) / SR
saw = sum(np.sin(k * ph) / k for k in range(1, 14))
save("sfx/zumbido.wav", lp(saw * (0.75 + 0.25 * np.sin(2 * np.pi * 31 * n)), 0.12) * env(len(n), 0.3, 0.9))
# golpecito metálico (picadura que rebota)
n = t(0.25); x = sum(np.sin(2 * np.pi * fr * n) * np.exp(-n * d) for fr, d in [(3150, 30), (4720, 38), (6110, 45), (2380, 26)])
save("sfx/tic_metal.wav", x + 0.3 * rng.standard_normal(len(n)) * np.exp(-n * 120))
# pop de insignia
n = t(0.18); fr = 900 * np.exp(-n * 14) + 300
save("sfx/badge.wav", np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-n * 22))
n = t(0.25); fr = 600 * np.exp(-n * 10) + 140
save("sfx/pop.wav", np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-n * 14))
# madera (la puerta del tronco se abre)
n = t(0.9); x = lp(rng.standard_normal(len(n)), 0.05) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * n)) * env(len(n), 0.05, 0.4)
save("sfx/madera.wav", x + 0.6 * np.sin(2 * np.pi * 95 * n) * np.exp(-n * 6))
# alarma: dos pulsos graves
n = t(1.4); x = np.zeros(len(n))
for st in (0.0, 0.55):
    m = (n >= st); u = n[m] - st
    x[m] += np.sin(2 * np.pi * 70 * u) * np.exp(-u * 7) + 0.4 * np.sin(2 * np.pi * 140 * u) * np.exp(-u * 9)
save("sfx/alarma.wav", x)
# enjambre: muchas abejas desafinadas que crecen
n = t(4.0); x = np.zeros(len(n))
for k in range(26):
    f0 = 210 + rng.uniform(-35, 60) + 8 * np.sin(2 * np.pi * rng.uniform(3, 8) * n + k)
    x += np.sign(np.sin(2 * np.pi * np.cumsum(f0) / SR)) * rng.uniform(0.3, 1)
save("sfx/enjambre.wav", lp(x, 0.08) * np.linspace(0.15, 1, len(n)) * env(len(n), 0.2, 0.8))
# vibración: zumbido grave con trémolo
n = t(4.5); x = sum(np.sin(2 * np.pi * fr * n) * a for fr, a in [(150, 1), (300, 0.4), (450, 0.2)])
save("sfx/vibracion.wav", x * (0.6 + 0.4 * np.sin(2 * np.pi * 22 * n)) * env(len(n), 0.25, 1.0))
# subida de calor: tono que sube + siseo
n = t(4.0); fr = 180 + 260 * (n / 4) ** 1.5
x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * 0.6 + lp(rng.standard_normal(len(n)), 0.3) * 0.25 * (n / 4)
save("sfx/subida.wav", x * env(len(n), 0.4, 0.6))
# golpe suave final
n = t(1.2); fr = 90 * np.exp(-n * 3) + 38
save("sfx/golpe.wav", np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-n * 3.5) + lp(rng.standard_normal(len(n)), 0.1) * np.exp(-n * 18) * 0.5)

# música de suspenso (45 s): pedal grave, acordes menores lentos, pulso tipo latido y tensión que sube
D = 46; n = t(D); x = np.zeros(len(n))
x += 0.55 * np.sin(2 * np.pi * 55 * n) + 0.25 * np.sin(2 * np.pi * 82.4 * n)
chords = [[220, 261.6, 329.6], [196, 246.9, 311.1], [174.6, 220, 261.6], [207.7, 246.9, 329.6]]
for i, ch in enumerate(chords * 3):
    st = i * 4.0
    m = (n >= st) & (n < st + 4.6); u = n[m] - st
    e = np.sin(np.pi * np.clip(u / 4.6, 0, 1)) ** 1.3
    for fr in ch:
        x[m] += 0.12 * e * (np.sin(2 * np.pi * fr * u) + 0.4 * np.sin(2 * np.pi * fr * 1.003 * u))
beat = 0.82
for k in range(int(D / beat)):
    st = k * beat
    for off, amp in ((0, 1), (0.2, 0.6)):
        m = (n >= st + off) & (n < st + off + 0.35); u = n[m] - st - off
        x[m] += amp * 0.7 * np.sin(2 * np.pi * (60 * np.exp(-u * 8) + 40) * u) * np.exp(-u * 12)
ten = np.clip((n - 25) / 10, 0, 1) * np.clip((36 - n) / 2 + 1, 0, 1)
x += ten * 0.18 * np.sin(2 * np.pi * (880 + 40 * np.sin(2 * np.pi * 5 * n)) * n)
save("musica.wav", lp(x, 0.2) * env(len(n), 1.0, 3.0))
print("listo")
