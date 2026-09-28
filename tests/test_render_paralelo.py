"""Render en paralelo: mismo video que en un solo proceso (corre también en la prueba de Windows)."""
import subprocess
import wave

import numpy as np
from PIL import Image


def _proyecto(estilo, segundos=54, por_escena=6.0):
    from estudio.edicion import construir_edl
    from estudio.esquemas import EscenasV2
    from estudio.proyecto import CarpetaProyecto

    c = CarpetaProyecto.crear("Paralelo", "animales-peligrosos", estilo.id, segundos, slug="paralelo")
    (c.ruta / "imagenes").mkdir(exist_ok=True)
    escenas, n = [], int(segundos / por_escena)
    for i in range(1, n + 1):
        Image.new("RGB", (640, 360), (30 * i % 255, 90, 160)).save(c.ruta / "imagenes" / f"escena_{i:03d}.png")
        t = (i - 1) * por_escena
        escenas.append({"id": i, "seccion": "Uno", "narracion": f"Frase número {i}.", "intencion": "explicacion",
                        "intensidad": 2, "visual": {"accion": "generar", "tipo": "animal_fondo_gris", "prompt": "x",
                                                    "archivo": f"imagenes/escena_{i:03d}.png"},
                        "tiempo": {"real_inicio": t, "real_fin": t + por_escena - 0.5}})
    c.guardar_escenas(EscenasV2.model_validate({"video": "Paralelo", "canal": "animales-peligrosos",
                                                "estilo": estilo.id, "escenas": escenas}))
    (c.ruta / "audio").mkdir(exist_ok=True)
    with wave.open(str(c.ruta / "audio" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes((np.sin(np.arange(48000 * (segundos + 2)) / 20) * 3000).astype("<i2").tobytes())
    construir_edl(c)
    return c


def _duracion(ffmpeg, f):
    salida = subprocess.run([ffmpeg, "-i", str(f)], capture_output=True, text=True).stderr
    linea = next(x for x in salida.splitlines() if "Duration" in x)
    h, m, s = linea.split("Duration:")[1].split(",")[0].strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def test_render_en_paralelo_da_el_mismo_video(estilo):
    from estudio.pipeline import ffmpeg
    from estudio.render import renderizar

    c = _proyecto(estilo)
    uno = renderizar(c, ffmpeg(), c.ruta / "render" / "uno.mp4", avisar=lambda _: None,
                     salida=(320, 180, 3), procesos=1)
    par = renderizar(c, ffmpeg(), c.ruta / "render" / "par.mp4", avisar=lambda _: None,
                     salida=(320, 180, 3), procesos=2)
    assert abs(_duracion(ffmpeg(), uno) - _duracion(ffmpeg(), par)) < 0.25
    assert not (c.ruta / "render" / "tramos").exists()                  # los tramos se limpian
    assert par.with_suffix(".srt").exists()
