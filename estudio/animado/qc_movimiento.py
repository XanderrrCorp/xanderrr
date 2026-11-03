"""Mide si el video se queda quieto: compara cuadros cada 0,5 s (sin la franja de subtítulos ni la barra de arriba)
y reporta los tramos sin movimiento. Uso: python qc_movimiento.py video.mp4"""
import subprocess
import sys

import numpy as np

FF = "/usr/bin/ffmpeg"
w, h, fps = 192, 108, 2
r = subprocess.run([FF, "-v", "error", "-i", sys.argv[1], "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                   capture_output=True, check=True)
fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w).astype(np.float32)[:, int(h * 0.1):int(h * 0.84), :]
dif = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
quieto = dif < float(sys.argv[2]) if len(sys.argv) > 2 else dif < 0.35
tramos, ini = [], None
for k, q in enumerate(quieto):
    if q and ini is None:
        ini = k
    if not q and ini is not None:
        tramos.append((ini / fps, (k - ini) / fps)); ini = None
if ini is not None:
    tramos.append((ini / fps, (len(quieto) - ini) / fps))
largos = sorted([t for t in tramos if t[1] >= 3.0], key=lambda x: -x[1])
print(f"cuadros comparados: {len(dif)} · movimiento medio {dif.mean():.2f} · tramos quietos ≥3 s: {len(largos)}")
print("el más largo:", f"{largos[0][1]:.1f} s en {int(largos[0][0] // 60)}:{largos[0][0] % 60:04.1f}" if largos else "ninguno")
for t0, d in largos[:10]:
    print(f"  {int(t0 // 60)}:{t0 % 60:04.1f}  quieto {d:.1f} s")
