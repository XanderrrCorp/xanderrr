"""Un tramo del render en paralelo (lo lanza render._renderizar_paralelo en otro proceso).

python -m estudio.render_tramo <carpeta> <salida.mp4> <desde> <hasta> <calidad> <ancho> <alto> <fps> <vertical> <hilos>
Dibuja solo el video de ese tramo, sin audio; quien une los tramos pone el audio completo.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    carpeta, salida, desde, hasta, calidad, ancho, alto, fps, vertical, hilos = argv
    os.environ["XANDART_HILOS_X264"] = hilos          # cada tramo usa su parte de los núcleos
    from .plataforma import contexto

    contexto.fijar_espacio(os.environ.get("XANDART_ESPACIO") or None)   # el estilo del espacio, no el del catálogo
    from .pipeline import ffmpeg
    from .proyecto import CarpetaProyecto
    from .render import renderizar

    renderizar(CarpetaProyecto(Path(carpeta)), ffmpeg(), Path(salida), desde=float(desde), hasta=float(hasta),
               avisar=lambda _: None, calidad=calidad, salida=(int(ancho), int(alto), int(fps)),
               vertical=vertical == "1", solo_video=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
