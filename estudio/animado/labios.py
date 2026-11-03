"""Rhubarb Lip Sync sobre cada segmento (con su texto como --dialogFile) → bocas/NNN.json y bocas.json (tiempos absolutos)."""
import json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
AQUI = Path(__file__).resolve().parent.parent
import os
import shutil

# Rhubarb Lip Sync (gratis, github.com/DanielSWolf/rhubarb-lip-sync): variable RHUBARB o en el PATH
RHUBARB = os.environ.get("RHUBARB") or shutil.which("rhubarb") or "rhubarb"
TL = json.loads((AQUI / "timeline.json").read_text(encoding="utf-8"))

def uno(s):
    out = AQUI / "bocas" / f"{s['id']:03d}.json"
    if not out.exists():
        txt = AQUI / "bocas" / f"{s['id']:03d}.txt"
        txt.write_text(s["texto"], encoding="utf-8")
        subprocess.run([RHUBARB, "-q", "-r", "phonetic", "--extendedShapes", "GHX", "--dialogFile", str(txt),
                        "-f", "json", "-o", str(out), str(AQUI / "segmentos" / f"{s['id']:03d}.wav")], check=True)
    return s, json.loads(out.read_text())["mouthCues"]

with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(uno, TL["segmentos"]))
todas = []
for s, cues in res:
    todas += [[round(s["inicio"] + c["start"], 3), c["value"]] for c in cues]
todas.sort()
(AQUI / "bocas.json").write_text(json.dumps(todas))
print(len(todas), "cambios de boca")
