"""Mide cada frase: inicio/fin de la voz y tiempo estimado de cada palabra (por energía y pausas)."""
import json, re, wave, pathlib, sys
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P / "scripts"))
import os
from voz_minimax import FRASES, FRASES_PANTERA  # noqa (no cobra: solo lee los textos)
PROD = os.environ.get("PROD", "avispon")
if PROD == "pantera": FRASES = FRASES_PANTERA
VOD = "public/pantera/vo" if PROD == "pantera" else "public/audio/vo"
OUT = "src/pantera/vo.json" if PROD == "pantera" else "src/data/vo.json"
res = {}
for k, texto in FRASES.items():
    w = wave.open(str(P / f"{VOD}/{k}.wav")); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = int(sr * 0.01); n = len(x) // hop
    e = np.array([np.sqrt(np.mean(x[i*hop:(i+1)*hop] ** 2)) for i in range(n)])
    thr = max(0.012, e.max() * 0.06)
    voiced = e > thr
    idx = np.where(voiced)[0]; a, b = idx[0], idx[-1] + 1
    # segmentos con voz separados por silencios >= 0,14 s
    segs, s0, sil = [], a, 0
    for i in range(a, b):
        if voiced[i]:
            if sil >= 14: segs.append((s0, i - sil)); s0 = i
            sil = 0
        else: sil += 1
    segs.append((s0, b))
    palabras = texto.replace("…", "… ").split()
    palabras = [p for p in palabras if p.strip()]
    # grupos por puntuación
    grupos, g = [], []
    for p in palabras:
        g.append(p)
        if re.search(r"[.,…?!:]$", p): grupos.append(g); g = []
    if g: grupos.append(g)
    peso = lambda p: len(re.sub(r"\W", "", p)) + 1.5
    if len(segs) == len(grupos):
        tramos = list(zip(grupos, segs))
    else:  # reparto proporcional de todo el tramo con voz
        tot = sum(peso(p) for p in palabras); t = a; tramos = []
        for gg in grupos:
            d = (b - a) * sum(peso(p) for p in gg) / tot; tramos.append((gg, (t, t + d))); t += d
    out = []
    for gg, (u, v) in tramos:
        tot = sum(peso(p) for p in gg); t = u
        for p in gg:
            d = (v - u) * peso(p) / tot
            out.append({"text": p, "start": round(t / 100, 3), "end": round((t + d) / 100, 3)}); t += d
    res[k] = {"text": texto, "seconds": round(len(x) / sr, 3), "voiceStart": round(a / 100, 3), "voiceEnd": round(b / 100, 3),
              "segments": len(segs), "groups": len(grupos), "words": out}
    print(k, res[k]["seconds"], "voz", res[k]["voiceStart"], "-", res[k]["voiceEnd"], "segs", len(segs), "grupos", len(grupos))
(P / OUT).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
