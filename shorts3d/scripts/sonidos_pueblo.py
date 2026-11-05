"""Música y efectos de «En este pueblo…», hechos por código (gratis y sin licencias de por medio).

- musica_calida.wav: ukulele + pizzicato caprichoso en mayor (la marca del canal: la misma en los 6).
- musica_tensa.wav: pizzicato grave en menor con pulso lento, para la noche y el clímax.
  La composición funde una con otra según la línea («tensa» en guion.json) y las deja 14–18 dB bajo la voz.
- sfx/*.wav: efectos caricaturescos (pop, boing, plop, pasos, campanas del reloj…).
Si el dueño prefiere música de la Biblioteca de audio de YouTube, basta con reemplazar los dos .wav.
"""
import wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent / "public/pueblo"
(P / "sfx").mkdir(parents=True, exist_ok=True)
SR = 48000
rng = np.random.default_rng(5)
def t(s): return np.arange(int(s * SR)) / SR
def save(name, x, rms=None):
    x = np.asarray(x, float)
    x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * rms if rms else x / (np.max(np.abs(x)) + 1e-9) * 0.89
    with wave.open(str(P / name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(x, -0.99, 0.99) * 32767).astype(np.int16).tobytes())
nota = lambda m: 440 * 2 ** ((m - 69) / 12)
def pluck(f, dur, brillo=0.5, decay=3.0):
    n = int(dur * SR); L = max(2, int(SR / f)); buf = rng.uniform(-1, 1, L); out = np.empty(n)
    for i in range(0, n, L):
        k = min(L, n - i); out[i:i + k] = buf[:k]; buf = brillo * buf + (1 - brillo) * np.roll(buf, 1)
    return out * np.exp(-np.arange(n) / SR * decay)
def pizz(f, dur=0.35):
    n = t(dur); return (np.sin(2 * np.pi * f * n) + 0.3 * np.sin(4 * np.pi * f * n)) * np.exp(-n * 11) * np.minimum(1, n / 0.003)
def pista(dur, bpm, prog, mel, f_acorde, f_mel, f_bajo):
    beat = 60 / bpm; out = np.zeros(int((dur + 3) * SR))
    for b in range(int(dur / beat)):
        c = prog[(b // 4) % len(prog)]; i0 = int(b * beat * SR)
        x = f_bajo(nota(c[0] - 12)) if b % 2 == 0 else None
        if x is not None: out[i0:i0 + len(x)] += x * 0.9
        for half in (0, 0.5):
            j = i0 + int(half * beat * SR)
            for k, m in enumerate(c[1:]):
                y = f_acorde(nota(m)); jj = j + int(k * 0.012 * SR); out[jj:jj + len(y)] += y * 0.35
        m = mel[b % len(mel)]
        if m: y = f_mel(nota(m)); out[i0:i0 + len(y)] += y * 0.55
    return out[: int(dur * SR)]
# cálida: 118 BPM, C–Am–F–G con ukulele y una melodía pizzicato que salta
cal = pista(64.0, 118, [[48, 60, 64, 67], [45, 57, 60, 64], [41, 57, 60, 65], [43, 59, 62, 67]],
            [72, 0, 76, 74, 72, 0, 79, 0, 77, 76, 74, 0, 72, 74, 76, 0],
            lambda f: pluck(f, 0.5, 0.6, 4), lambda f: pizz(f, 0.3), lambda f: pizz(f, 0.5) * 1.2)
save("musica_calida.wav", cal * np.minimum(1, t(64.0) / 0.3), rms=10 ** (-20 / 20))
# tensa: 84 BPM, Am–E con pizzicato grave y una nota repetida inquietante
ten = pista(48.0, 84, [[45, 57, 60, 64], [40, 56, 59, 64], [41, 57, 60, 65], [40, 56, 59, 62]],
            [81, 0, 80, 0, 81, 0, 0, 0], lambda f: pizz(f, 0.25) * 0.8, lambda f: pizz(f, 0.2) * 0.6, lambda f: pizz(f, 0.7) * 1.4)
save("musica_tensa.wav", ten * np.minimum(1, t(48.0) / 0.3), rms=10 ** (-20 / 20))
S = lambda n, x: save(f"sfx/{n}.wav", x)
n = t(0.25); S("pop", np.sin(2 * np.pi * np.cumsum(500 + 1400 * n / 0.25) / SR) * np.exp(-n * 22))
n = t(0.6); S("boing", np.sin(2 * np.pi * np.cumsum(180 + 120 * np.sin(2 * np.pi * 11 * n) * np.exp(-n * 4)) / SR) * np.exp(-n * 5))
n = t(0.3); S("plop", np.sin(2 * np.pi * np.cumsum(900 * np.exp(-n * 14) + 120) / SR) * np.exp(-n * 16))
def paso(d=0.09): n = t(d); return (rng.standard_normal(len(n)) * 0.5 + np.sin(2 * np.pi * 90 * n)) * np.exp(-n * 60)
def serie(fn, k, sep):
    out = np.zeros(int((k * sep + 0.3) * SR))
    for i in range(k): x = fn(); j = int(i * sep * SR); out[j:j + len(x)] += x
    return out
S("pasos", serie(lambda: paso(0.12), 4, 0.28)); S("pasitos", serie(lambda: paso(0.05) * 0.6, 8, 0.11))
n = t(0.8); S("cinta", np.concatenate([rng.standard_normal(int(0.5 * SR)) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t(0.5))) * np.exp(-t(0.5) * 2), rng.standard_normal(int(0.3 * SR)) * np.exp(-t(0.3) * 30)]))
n = t(1.0); S("sollozo", sum(np.sin(2 * np.pi * np.cumsum(420 + 60 * np.sin(2 * np.pi * 6 * n) - 120 * ((n - s0) > 0)) / SR) * np.exp(-np.abs(n - s0 - 0.12) * 14) for s0 in (0.0, 0.35, 0.6)))
n = t(0.7); S("bocina", (np.sign(np.sin(2 * np.pi * 330 * n)) * 0.5 + np.sign(np.sin(2 * np.pi * 415 * n)) * 0.5) * np.minimum(1, n / 0.02) * np.exp(-np.maximum(0, n - 0.5) * 20))
n = t(0.7); S("crujido", ((np.sin(2 * np.pi * np.cumsum(70 + 50 * n) / SR) > 0.94).astype(float) + 0.05 * rng.standard_normal(len(n))) * np.sin(np.pi * n / 0.7))
n = t(0.5); S("costura", serie(lambda: rng.standard_normal(int(0.05 * SR)) * np.exp(-t(0.05) * 60) * 0.7, 5, 0.09))
n = t(2.2); S("campana", sum(np.sin(2 * np.pi * f * n) * np.exp(-n * d) * a for f, d, a in [(523, 1.2, 1), (1046, 1.8, 0.5), (1569, 2.5, 0.25), (659, 1.5, 0.3)]))
out = np.zeros(int(3.2 * SR))
for i, f0 in enumerate([659, 523, 587, 392]):
    n = t(1.6); x = sum(np.sin(2 * np.pi * f * n) * np.exp(-n * d) * a for f, d, a in [(f0, 1.6, 1), (f0 * 2, 2.2, 0.4), (f0 * 3, 3, 0.2)]); j = int(i * 0.5 * SR); out[j:j + len(x)] += x
S("campanas", out)
S("cuerda", serie(lambda: np.sin(2 * np.pi * 2200 * t(0.03)) * np.exp(-t(0.03) * 120), 10, 0.06))
n = t(1.2); S("rascar", serie(lambda: rng.standard_normal(int(0.18 * SR)) * np.sin(np.pi * t(0.18) / 0.18) * 0.6, 4, 0.28))
print("sonidos del pueblo listos en", P)
