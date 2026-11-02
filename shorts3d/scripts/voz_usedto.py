"""Voz de «Used To» (inglés): graba cada FRASE del guion con MiniMax, la deja al nivel de la mezcla y mide
los tiempos de cada palabra -> src/usedto/vo.json (de ahí salen los cortes y los subtítulos).

COBRA (unos pocos pesos por Short), así que no graba nada sin --pagar:
    python scripts/voz_terror.py            # dice qué grabaría y cuántos caracteres son
    python scripts/voz_terror.py --pagar    # graba lo que falte y mide todo
    python scripts/voz_terror.py --medir    # solo vuelve a medir los .wav que ya hay (gratis)
La voz y la velocidad se cambian en src/usedto/guion.json («voz»). Las líneas ya grabadas no se vuelven a pagar;
para regrabar una, borra su .mp3 en public/usedto/vo/.
"""
import json, os, re, subprocess, sys, urllib.request, wave, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent
G = json.loads((P / "src/usedto/guion.json").read_text(encoding="utf-8"))
VO = P / "public/usedto/vo"; VO.mkdir(parents=True, exist_ok=True)
OUT = P / "src/usedto/vo.json"
lineas = {f"f{i + 1}": f["texto"] for i, f in enumerate(G["frases"])}
pagar, solo_medir = "--pagar" in sys.argv, "--medir" in sys.argv
faltan = [k for k in lineas if not (VO / f"{k}.mp3").exists()]
if not pagar and not solo_medir:
    print(f"voz {G['voz']['voice_id']} a {G['voz']['speed']}x · faltan {len(faltan)} de {len(lineas)} líneas · "
          f"{sum(len(lineas[k]) for k in faltan)} caracteres. Para grabarlas: --pagar")
    sys.exit(0)
cobrados = 0
for k in (faltan if pagar else []):
    body = {"model": "speech-2.6-hd", "text": lineas[k], "stream": False, "language_boost": "English",
            "voice_setting": {"voice_id": G["voz"]["voice_id"], "speed": G["voz"]["speed"], "vol": 1, "pitch": 0},
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1}}
    req = urllib.request.Request("https://api.minimax.io/v1/t2a_v2", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("MINIMAX_API_KEY", "x")})
    d = json.load(urllib.request.urlopen(req, timeout=180))
    if (d.get("base_resp") or {}).get("status_code") not in (0, None):
        sys.exit(f"MiniMax: {d.get('base_resp')}")
    (VO / f"{k}.mp3").write_bytes(bytes.fromhex(d["data"]["audio"]))
    cobrados += int((d.get("extra_info") or {}).get("usage_characters") or len(lineas[k]))
    print("grabada", k)
# a 48 kHz y al MISMO nivel RMS que la música (-20 dBFS): así los dB de spec.ts son reales
for k in lineas:
    if (VO / f"{k}.mp3").exists():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(VO / f"{k}.mp3"), "-ar", "48000", "-ac", "1",
                        "-af", "loudnorm=I=-20:TP=-2:LRA=11", str(VO / f"{k}.wav")], check=True)

def medir(k, txt):
    w = wave.open(str(VO / f"{k}.wav")); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = int(sr * 0.01); n = len(x) // hop
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) for i in range(n)])
    voiced = e > max(0.012, e.max() * 0.06)
    idx = np.where(voiced)[0]; a, b = idx[0], idx[-1] + 1
    segs, s0, sil = [], a, 0
    for i in range(a, b):
        if voiced[i]:
            if sil >= 14: segs.append((s0, i - sil)); s0 = i
            sil = 0
        else: sil += 1
    segs.append((s0, b))
    palabras = [p for p in txt.replace("…", "… ").split() if p.strip()]
    grupos, g = [], []
    for p in palabras:
        g.append(p)
        if re.search(r"[.,…?!:»]$", p): grupos.append(g); g = []
    if g: grupos.append(g)
    peso = lambda p: len(re.sub(r"\W", "", p)) + 1.5
    if len(segs) == len(grupos): tramos = list(zip(grupos, segs))
    else:
        tot = sum(peso(p) for p in palabras); t0 = a; tramos = []
        for gg in grupos:
            d = (b - a) * sum(peso(p) for p in gg) / tot; tramos.append((gg, (t0, t0 + d))); t0 += d
    out = []
    for gg, (u, v) in tramos:
        tot = sum(peso(p) for p in gg); t0 = u
        for p in gg:
            d = (v - u) * peso(p) / tot
            out.append({"text": p, "start": round(t0 / 100, 3), "end": round((t0 + d) / 100, 3)}); t0 += d
    return {"text": txt, "seconds": round(len(x) / sr, 3), "voiceStart": round(a / 100, 3), "voiceEnd": round(b / 100, 3), "words": out}

res = {k: medir(k, t) for k, t in lineas.items() if (VO / f"{k}.wav").exists()}
OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
pal = sum(len(r["words"]) for r in res.values()); hab = sum(r["voiceEnd"] - r["voiceStart"] for r in res.values())
print(f"medidas {len(res)}/{len(lineas)} líneas · {pal / max(hab, 1e-6) * 60:.0f} palabras/min al hablar (la ficha pide 155–165 en el video; el revisor da la cifra final)")
if cobrados: print("caracteres cobrados:", cobrados)
