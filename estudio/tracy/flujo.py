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


def crear_proyecto(guion: str, canal: str = CLAVE_CANAL, titulo: str | None = None,
                   prueba_s: float | None = None) -> CarpetaProyecto:
    from ..config import ruta_proyectos
    from ..pipeline import ESTILO_POR_DEFECTO
    from ..plataforma.consultas import registrar_video

    titulo = titulo or (oraciones(guion) or ["Video Tracy"])[0][:80]
    cps = ConfigCostos.cargar().consumo["caracteres_por_segundo_narracion"]
    if prueba_s:
        # (01-11) «Probar 3 minutos»: solo las primeras oraciones del guion
        from .humano import recortar_guion

        guion = recortar_guion(guion, prueba_s, cps)
        titulo = f"Prueba · {titulo}"[:80]
    base = slugificar(titulo)[:40] or "tracy"
    slug, n = base, 2
    while (ruta_proyectos() / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    # el estilo no se usa en modo stock; se deja el de siempre para que el proyecto sea válido
    c = CarpetaProyecto.crear(titulo, canal, ESTILO_POR_DEFECTO, max(1.0, len(guion) / cps), slug=slug)
    p = c.cargar()
    p.visual_mode = "stock"
    c.guardar(p)
    (c.ruta / "guion.txt").write_text(guion, encoding="utf-8")
    registrar_video(slug, titulo, str(c.ruta), canal, round(len(guion) / cps / 60, 1), estado="en_proceso")
    return c


def paso_audio(c: CarpetaProyecto, proveedor: str | None = None, permiso: bool = False, avisar=print,
               voz=None, transcriptor=None, ejecutar_claude=None) -> dict:
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
    from . import humano

    if humano.activo(preset):
        segs = segmentar_humano(c, preset, avisar=avisar, ejecutar=ejecutar_claude, retocar=True)
    else:
        segs = segmentar_proyecto(c, preset)
    return {"duracion": r["duracion"], "bloques": len(r["bloques"]), "costo_usd": r["costo_usd"],
            "oraciones": len(al["oraciones"]), "confianza": al["confianza"], "segmentos": segs}


def rehacer_segmentos(c: CarpetaProyecto) -> list[dict]:
    from . import humano

    preset = cargar_preset(c.cargar().canal)
    if humano.activo(preset):
        return segmentar_humano(c, preset, retocar=False)
    return segmentar_proyecto(c, preset)


def segmentar_humano(c: CarpetaProyecto, preset: dict, avisar=print, ejecutar=None, retocar: bool = True) -> list[dict]:
    """(01-11) Edición humana: Claude marca las oraciones, la voz lleva pausas naturales y un cierre más lento, y
    los cortes salen de duración variable según lo que se dice."""
    from ..config import leer_json
    from ..pipeline import ffmpeg
    from . import humano

    h = humano.ajustes(preset)
    datos = leer_json(c.ruta / "audio" / "oraciones.json")
    marcas = humano.marcar(c, datos["oraciones"], h, ejecutar=ejecutar, avisar=avisar)
    if retocar:
        humano.retocar_audio(c, marcas, h, ffmpeg(), avisar=avisar)
        datos = leer_json(c.ruta / "audio" / "oraciones.json")
    segs = humano.segmentar(datos["oraciones"], datos["duracion"], marcas, h, c.ruta.name)
    escribir_json(c.ruta / "segmentos.json", {"duracion": datos["duracion"], "humano": True,
                                              "objetivo_s": [h["clip_min_s"], h["clip_max_s"]],
                                              "maximo_s": h["clip_max_s"], "segmentos": segs})
    avisar(f"  {len(segs)} clips de {min(s['duracion'] for s in segs):.0f} a {max(s['duracion'] for s in segs):.0f} s"
           if segs else "  sin clips")
    return segs


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
    from ..config import leer_json
    from . import humano

    duracion = float(leer_json(c.ruta / "segmentos.json")["duracion"])
    if humano.activo(preset) and leer_json(c.ruta / "segmentos.json").get("humano"):
        r = preparar_humano(c, preset, duracion, avisar=avisar, sesion=sesion or requests)
        if humano.ajustes(preset)["revisar_antes"] and not (c.ruta / "revision_aprobada.json").exists():
            avisar("Listo para revisar: mira el gancho, la venta y el cierre, y luego dale «Exportar».")
            return {"final": None, "revision": True, **r}
        return {**exportar(c, preset, avisar=avisar, progreso=progreso), **r}
    plan = planificar(c, preset, ejecutar=ejecutar, avisar=avisar, config=config)
    from .planificador import marcar_final

    plan = marcar_final(plan, duracion, preset["escena_final_desde"], preset["proporcion_seminario"])
    from .planificador import tomas

    plan = tomas(plan, preset["seminario_s"])
    avisar("Buscando los clips (Pexels y seminario)…")
    r = elegir_clips(c, plan, preset, ffmpeg(), avisar=avisar, sesion=sesion or requests)
    preset["presentador"] = encontrar(preset.get("presentador"), EXT_IMAGEN) or preset.get("presentador")
    final = ensamblar(c, ffmpeg(), avisar=avisar, progreso=progreso, musica=preset.get("musica"),
                      volumen_musica_db=preset.get("volumen_musica_db", -16.0), preset=preset)
    return {"final": final, "stock": r["stock"], "seminario": r["seminario"], "escena_final": r.get("final", 0),
            "segmentos": len(plan)}


def preparar_humano(c: CarpetaProyecto, preset: dict, duracion: float, avisar=print, sesion=None) -> dict:
    """Edición humana: huella del video, plan (seminario solo en autoridad, movimientos, transiciones, textos) y
    clips. Si el plan y los clips ya están (se está retomando o se revisó), no se rehacen."""
    import requests

    from ..config import leer_json
    from ..pipeline import ffmpeg
    from . import humano
    from .clips import elegir_clips

    if (c.ruta / "clips.json").exists() and (c.ruta / "plan_visual.json").exists() and \
            leer_json(c.ruta / "plan_visual.json").get("origen") == "humano" and \
            leer_json(c.ruta / "plan_visual.json").get("segmentos") == _huella_segmentos(c):
        clips = leer_json(c.ruta / "clips.json")["clips"]
        return {"stock": sum(1 for x in clips if x["tipo"] == "stock"),
                "seminario": sum(1 for x in clips if x["tipo"] == "seminario"),
                "escena_final": sum(1 for x in clips if x["tipo"] == "final"), "segmentos": len(clips)}
    h = humano.ajustes(preset)
    p = c.cargar()
    combo = humano.huella(p.canal, c.ruta.name, h)
    escribir_json(c.ruta / "huella_video.json", combo)
    marcas = {int(k): v for k, v in leer_json(c.ruta / "marcas_humano.json")["marcas"].items()}
    segs = leer_json(c.ruta / "segmentos.json")["segmentos"]
    inicios = {o["id"]: o["inicio"] for o in leer_json(c.ruta / "audio" / "oraciones.json")["oraciones"]}
    plan = humano.tomas(humano.planificar(segs, marcas, duracion, h, combo, c.ruta.name, inicios))
    escribir_json(c.ruta / "plan_visual.json", {"origen": "humano", "segmentos": _huella_segmentos(c), "plan": plan})
    sem = sum(1 for x in plan if x["type"] == "seminar")
    avisar(f"  plan: {sem} tomas del seminario, {len(plan) - sem} de stock o escena final")
    avisar("Buscando los clips (Pexels y seminario)…")
    r = elegir_clips(c, plan, preset, ffmpeg(), avisar=avisar, sesion=sesion or requests)
    (c.ruta / "revision_aprobada.json").unlink(missing_ok=True)       # un plan nuevo se revisa otra vez
    return {"stock": r["stock"], "seminario": r["seminario"], "escena_final": r.get("final", 0),
            "segmentos": len(plan)}


def _huella_segmentos(c: CarpetaProyecto) -> str:
    import hashlib

    return hashlib.sha256((c.ruta / "segmentos.json").read_bytes()).hexdigest()[:16]


def exportar(c: CarpetaProyecto, preset: dict | None = None, avisar=print, progreso=None) -> dict:
    """Edición humana: el video final con lo revisado, y el reporte de edición."""
    from ..pipeline import ffmpeg
    from . import humano
    from .ensamblar import ensamblar
    from .preset import EXT_AUDIO, EXT_IMAGEN, encontrar

    preset = preset or cargar_preset(c.cargar().canal)
    preset["musica"] = encontrar(preset.get("musica"), EXT_AUDIO) or preset.get("musica")
    preset["presentador"] = encontrar(preset.get("presentador"), EXT_IMAGEN) or preset.get("presentador")
    final = ensamblar(c, ffmpeg(), avisar=avisar, progreso=progreso, musica=preset.get("musica"),
                      volumen_musica_db=preset.get("volumen_musica_db", -16.0), preset=preset)
    rep = humano.reporte(c)
    avisar(f"Reporte: clips de {rep['duracion_media_s']} s en promedio (variación {rep['variacion_pct']} %), "
           f"seminario {rep['fenix_pct']} %, {rep['stock_unicos']} clips de stock distintos")
    return {"final": final, "reporte": rep}


def exportar_y_entregar(c: CarpetaProyecto, t) -> Path:
    """(01-11) «Exportar» después de revisar: el video con lo revisado, su copia en Videos, el reporte de edición y
    el cobro de los créditos apartados."""
    from ..config import leer_json
    from ..plataforma import cobro
    from .ensamblar import entregar

    escribir_json(c.ruta / "revision_aprobada.json", {"aprobada": True})
    t.paso, t.progreso = "visual", 0.5

    def avance(x: float) -> None:
        t.progreso = 0.5 + 0.45 * x

    r = exportar(c, avisar=t.avisar, progreso=avance)
    t.paso, t.progreso = "entrega", 0.97
    destino = entregar(c, r["final"])
    c.marcar("export_final", "completo", [str(destino)])
    try:
        cobro.cerrar_video(c.ruta, float(leer_json(c.ruta / "audio" / "oraciones.json")["duracion"]) / 60)
    except Exception:  # noqa: BLE001
        pass
    t.avisar(f"Video listo: {destino}")
    return destino


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
    a = paso_audio(c, proveedor=proveedor, permiso=permiso, avisar=t.avisar, voz=voz, transcriptor=transcriptor,
                   ejecutar_claude=ejecutar)
    t.avisar(f"Voz lista: {a['duracion'] / 60:.1f} min, {len(a['segmentos'])} segmentos, coincidencia con el "
             f"guion {a['confianza']:.0%}")
    t.paso, t.progreso = "visual", 0.35

    def avance(x: float) -> None:
        t.progreso = 0.5 + 0.45 * x

    r = paso_visual(c, avisar=t.avisar, ejecutar=ejecutar, sesion=sesion, progreso=avance)
    if r.get("revision"):
        t.paso, t.progreso = "revision", 1.0
        t.avisar("Listo para revisar antes de exportar")
        return c.ruta / "clips.json"
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
