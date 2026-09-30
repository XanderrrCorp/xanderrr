"""Fase 1 del modo Tracy: guion pegado → números en palabras → voz → Whisper → segmentos.

Crea un proyecto normal (aparece en Mis videos) marcado con visual_mode «stock». No usa
escenas.json ni ningún paso del pipeline de imágenes generadas.
"""
from __future__ import annotations

from ..config import ConfigCostos, escribir_json
from ..proyecto import CarpetaProyecto, slugificar
from .alineacion import alinear, transcriptor_para
from .audio import generar_audio, oraciones, voz_para
from .numeros import numeros_a_palabras
from .preset import CLAVE_CANAL, cargar_preset
from .segmentos import segmentar_proyecto


def crear_proyecto(guion: str, canal: str = CLAVE_CANAL, titulo: str | None = None) -> CarpetaProyecto:
    from ..config import ruta_proyectos
    from ..pipeline import ESTILO_POR_DEFECTO
    from ..plataforma.consultas import registrar_video

    titulo = titulo or (oraciones(guion) or ["Video Tracy"])[0][:80]
    base = slugificar(titulo)[:40] or "tracy"
    slug, n = base, 2
    while (ruta_proyectos() / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    cps = ConfigCostos.cargar().consumo["caracteres_por_segundo_narracion"]
    # el estilo no se usa en modo stock; se deja el de siempre para que el proyecto sea válido
    c = CarpetaProyecto.crear(titulo, canal, ESTILO_POR_DEFECTO, max(1.0, len(guion) / cps), slug=slug)
    p = c.cargar()
    p.visual_mode = "stock"
    c.guardar(p)
    (c.ruta / "guion.txt").write_text(guion, encoding="utf-8")
    registrar_video(slug, titulo, str(c.ruta), canal, round(len(guion) / cps / 60, 1), estado="en_proceso")
    return c


def paso_audio(c: CarpetaProyecto, proveedor: str | None = None, permiso: bool = False, avisar=print,
               voz=None, transcriptor=None) -> dict:
    """Voz, alineación y segmentos de un proyecto Tracy. Reanudable: lo pagado no se repite."""
    from ..pipeline import ffmpeg

    p = c.cargar()
    preset = cargar_preset(p.canal)
    escribir_json(c.ruta / "preset_tracy.json", preset)          # lo que se usó en este video
    guion = (c.ruta / "guion.txt").read_text(encoding="utf-8")
    texto_tts = numeros_a_palabras(guion)
    (c.ruta / "guion_tts.txt").write_text(texto_tts, encoding="utf-8")
    config = ConfigCostos.cargar()
    avisar("Voz…")
    r = generar_audio(c, texto_tts, ffmpeg(), voz or voz_para(proveedor, preset, config), preset,
                      config=config, permiso=permiso, avisar=avisar)
    avisar(f"Alineando con {'Whisper' if proveedor != 'simulado' else 'el alineador simulado'}…")
    al = alinear(c, transcriptor or transcriptor_para(proveedor), avisar=avisar)
    segs = segmentar_proyecto(c, preset)
    return {"duracion": r["duracion"], "bloques": len(r["bloques"]), "costo_usd": r["costo_usd"],
            "oraciones": len(al["oraciones"]), "confianza": al["confianza"], "segmentos": segs}


def rehacer_segmentos(c: CarpetaProyecto) -> list[dict]:
    return segmentar_proyecto(c, cargar_preset(c.cargar().canal))
