#!/bin/bash
# hoja de cuadros: une los PNG de out/<carpeta> en una tira reducida -> out/<carpeta>.png
cd "$(dirname "$0")/../out/$1" && ffmpeg -loglevel error -y -pattern_type glob -i 'c*.png' -vf "scale=360:640,tile=${2:-6}x1:padding=6:color=black" -frames:v 1 "../$1.png"
