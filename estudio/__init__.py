"""Estudio de producción de video dentro de Buscanichos."""
from .sin_ventanas import activar as _sin_ventanas

_sin_ventanas()      # en Windows, ffmpeg y compañía trabajan sin abrir ventanas negras
