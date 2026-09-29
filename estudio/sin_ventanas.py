"""En Windows, que ffmpeg, Claude y los tramos del render no abran ventanas negras.

Xandart corre con pythonw (sin consola), así que cada programa de consola que lanza abre su propia
ventana. Esto hace que, si quien llama no pidió otra cosa, se lancen con CREATE_NO_WINDOW. Cubre
también a las librerías que lanzan ffmpeg por su cuenta. Quien sí quiere una ventana (la de iniciar
sesión en Claude) pasa sus propios creationflags.
"""
from __future__ import annotations

import os
import subprocess

SIN_VENTANA = 0x08000000          # CREATE_NO_WINDOW
_activo = False


def activar() -> None:
    global _activo
    if os.name != "nt" or _activo:
        return
    original = subprocess.Popen.__init__

    def __init__(self, *args, **kwargs):
        if not kwargs.get("creationflags"):
            kwargs["creationflags"] = SIN_VENTANA
        original(self, *args, **kwargs)

    subprocess.Popen.__init__ = __init__
    _activo = True
