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


# ------------------------------------------------------------------ fase 2: visuales y ensamblaje

def paso_visual(c: CarpetaProyecto, avisar=print, ejecutar=None, sesion=None, progreso=None) -> dict:
    """Plan visual (Claude) → clips (Pexels + seminario, sin repetir) → video con subtítulos."""
    import requests

    from ..pipeline import ffmpeg
    from .clips import elegir_clips
    from .ensamblar import ensamblar
    from .planificador import planificar

    from .preset import EXT_AUDIO, EXT_IMAGEN, EXT_VIDEO, encontrar

    p = c.cargar()
    preset = cargar_preset(p.canal)
    preset["clip_base"] = encontrar(preset["clip_base"], EXT_VIDEO) or preset["clip_base"]
    preset["musica"] = encontrar(preset.get("musica"), EXT_AUDIO) or preset.get("musica")
    config = ConfigCostos.cargar()
    plan = planificar(c, preset, ejecutar=ejecutar, avisar=avisar, config=config)
    from ..config import leer_json
    from .planificador import marcar_final

    duracion = float(leer_json(c.ruta / "segmentos.json")["duracion"])
    plan = marcar_final(plan, duracion, preset["escena_final_desde"], preset["proporcion_seminario"])
    avisar("Buscando los clips (Pexels y seminario)…")
    r = elegir_clips(c, plan, preset, ffmpeg(), avisar=avisar, sesion=sesion or requests)
    preset["presentador"] = encontrar(preset.get("presentador"), EXT_IMAGEN) or preset.get("presentador")
    final = ensamblar(c, ffmpeg(), avisar=avisar, progreso=progreso, musica=preset.get("musica"),
                      volumen_musica_db=preset.get("volumen_musica_db", -24.0), preset=preset)
    return {"final": final, "stock": r["stock"], "seminario": r["seminario"], "escena_final": r.get("final", 0),
            "segmentos": len(plan)}


def producir(c: CarpetaProyecto, t, proveedor: str | None = None, permiso: bool = False, ejecutar=None,
             sesion=None, voz=None, transcriptor=None) -> Path:
    """Todo el video Tracy de una vez (lo que corre el botón de la página). Reanudable: la voz,
    Whisper, el plan y las descargas ya hechas no se repiten."""
    from ..plataforma import cobro
    from .ensamblar import entregar

    config = ConfigCostos.cargar()
    try:
        apartado = cobro.abrir_video(c.ruta, c.cargar().duracion_objetivo_seg / 60)
        if apartado and apartado.get("creditos"):
            t.avisar(f"Créditos apartados para el video: {apartado['creditos']}")
    except Exception as ex:  # noqa: BLE001 — sin saldo se avisa y no se gasta nada
        raise RuntimeError(str(ex)) from ex
    t.paso, t.progreso = "voz", 0.02
    a = paso_audio(c, proveedor=proveedor, permiso=permiso, avisar=t.avisar, voz=voz, transcriptor=transcriptor)
    t.avisar(f"Voz lista: {a['duracion'] / 60:.1f} min, {len(a['segmentos'])} segmentos, coincidencia con el "
             f"guion {a['confianza']:.0%}")
    t.paso, t.progreso = "visual", 0.35

    def avance(x: float) -> None:
        t.progreso = 0.5 + 0.45 * x

    r = paso_visual(c, avisar=t.avisar, ejecutar=ejecutar, sesion=sesion, progreso=avance)
    t.paso, t.progreso = "entrega", 0.97
    destino = entregar(c, r["final"])
    c.marcar("export_final", "completo", [str(destino)])
    try:
        cobrado = cobro.cerrar_video(c.ruta, a["duracion"] / 60)
        if cobrado:
            t.avisar(f"Créditos cobrados: {cobrado['cobrado']}")
    except Exception:  # noqa: BLE001
        pass
    from ..config import formato_cop

    t.avisar(f"Costo del video: {formato_cop(c.libro(config).total_cop())} · {r['stock']} clips de stock y "
             f"{r['seminario']} de seminario")
    t.avisar(f"Video listo: {destino}")
    return destino
