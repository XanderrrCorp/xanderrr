#!/bin/bash
# Previa rápida de un episodio de «En este pueblo…» (540x960, lienzo 3D a la mitad) + volumen de YouTube.
# Uso: scripts/previa_pueblo.sh PuebloEp5Juguetes ep5    (en el PC con NVIDIA, para el final: sin --props, con --gl=angle)
cd "$(dirname "$0")/.." || exit 1
COMP=$1; NOM=$2
CHROME=/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
./node_modules/.bin/remotion render src/index.ts "$COMP" "out/${NOM}_crudo.mp4" --scale=0.5 --props='{"dpr":0.5}' --gl=swangle \
  --concurrency=4 --timeout=300000 --crf=20 --log=error --browser-executable=$CHROME 2>&1 | grep -v "^\s*at " | tail -3
ffmpeg -loglevel error -y -i "out/${NOM}_crudo.mp4" -c:v copy -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k "out/${NOM}_previa.mp4" && ls -la "out/${NOM}_previa.mp4"
