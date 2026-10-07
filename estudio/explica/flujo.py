"""Un tema de El Calvo Explica de punta a punta (lo que corre el botón «Hacer el tema de prueba»).

guion (5 partes) → revisión → voz MiniMax (la de Peligro Tropical a la velocidad del canal) → Whisper palabra por
palabra → escenas.json atado a esas palabras → render → voz + música tranquila bajita → MP4.

Todo vive en <datos>/explica/<tema>/. Reanudable: la voz ya pagada y lo ya transcrito no se repiten.
Al terminar deja `informe.json` con el costo real separado (guion, voz, imágenes) y el tiempo total.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from ..config import ConfigCostos, escribir_json, leer_json
from ..costos import formato_cop
from ..calma import escenas as E
from ..calma.flujo import Carpeta
from . import canal as C
from . import guion as G

EJEMPLOS = Path(__file__).resolve().parent / "ejemplos"
GUIONES = Path(__file__).resolve().parent / "guiones"
TEMA_PRUEBA = "tema1_muneca"
GUION_PRUEBA = "partes_que_no_sirven_tema1"


def carpeta_base() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "explica"
    c.mkdir(parents=True, exist_ok=True)
    return c


def preparar(nombre: str = TEMA_PRUEBA, guion: str = GUION_PRUEBA) -> Carpeta:
    """Copia el guion y las escenas a su carpeta de trabajo (si ya están, no las pisa)."""
    c = Carpeta(carpeta_base() / nombre)
    c.ruta.mkdir(parents=True, exist_ok=True)
    if not (c.ruta / "guion.txt").exists():
        shutil.copy(GUIONES / f"{guion}.txt", c.ruta / "guion.txt")
    if not (c.ruta / "escenas.json").exists():
        shutil.copy(EJEMPLOS / f"{nombre}.json", c.ruta / "escenas.json")
    return c


def costo_voz(nombre: str = TEMA_PRUEBA, guion: str = GUION_PRUEBA) -> dict:
    texto = G.texto_para_voz(G.leer((GUIONES / f"{guion}.txt").read_text(encoding="utf-8")))
    config = ConfigCostos.cargar()
    usd = len(texto) / 1000 * config.precio("tts_por_1000_caracteres")
    return {"caracteres": len(texto), "usd": round(usd, 4), "cop": formato_cop(config.a_cop(usd))}


def _costos(c: Carpeta, config: ConfigCostos) -> dict:
    por = {"guion": 0.0, "voz": 0.0, "imagenes": 0.0}
    for e in c.libro(config).entradas():
        m = e.get("modulo", "")
        clave = "voz" if "voz" in m else "imagenes" if ("imagen" in m or "ilustracion" in m) else "guion"
        por[clave] += float(e.get("costo_usd", 0))
    return {k: {"usd": round(v, 4), "cop": formato_cop(config.a_cop(v))} for k, v in por.items()}


def producir(c: Carpeta, t, permiso: bool = False, voz=None, transcriptor=None, proveedor: str | None = None) -> Path:
    from ..calma.musica import elegir
    from ..calma.render import render
    from ..pipeline import carpeta_videos, ffmpeg
    from ..tracy.alineacion import alinear, transcriptor_para
    from ..tracy.audio import generar_audio, voz_para

    inicio = time.time()
    preset = C.cargar()
    ff = ffmpeg()
    config = ConfigCostos.cargar()
    temas = G.leer((c.ruta / "guion.txt").read_text(encoding="utf-8"))
    avisos_guion = G.revisar(temas, preset)
    for a in avisos_guion:
        t.avisar(f"  guion: {a}")
    texto = G.texto_para_voz(temas)

    t.paso, t.progreso = "voz", 0.03
    if voz is None:
        if proveedor == "simulado":
            voz = voz_para("simulado", {}, config)
        else:
            from ..voz import VozMiniMax

            voz = VozMiniMax(config, C.ajustes_voz(preset))
    t.avisar("Generando la voz con MiniMax…" if voz.nombre != "simulado" else "Voz simulada (ensayo sin gastar)…")
    generar_audio(c, texto, ff, voz, {"bloque_tts_max": 2500}, config, permiso=permiso, avisar=t.avisar)

    t.paso, t.progreso = "whisper", 0.2
    ors = alinear(c, transcriptor or transcriptor_para(proveedor), avisar=t.avisar)
    quien = "Whisper" if ors.get("metodo") not in ("pausas", "simulado") else f"Tiempos ({ors.get('metodo')})"
    t.avisar(f"{quien}: coincidencia con el guion {ors['confianza']:.0%}")

    t.paso, t.progreso = "escenas", 0.3
    datos = json.loads((c.ruta / "escenas.json").read_text(encoding="utf-8"))
    E.fijar_tiempos(datos, E.palabras_de(ors), float(ors["duracion"]) + 0.6)
    ritmo = E.revisar(datos, max_sin_cambio=float(preset["cambio_cada_s"][1]))
    for a in ritmo:
        t.avisar(f"  ritmo: {a}")
    escribir_json(c.ruta / "escenas_con_tiempos.json", datos)

    musica = None
    if preset.get("musica"):
        musica = {"ruta": preset["musica"], "nombre_original": Path(preset["musica"]).name}
    else:
        musica = elegir(ff, avisar=t.avisar, animos=("suave", "curiosidad", "misterio"))
    if musica:
        t.avisar(f"Música: {musica['nombre_original']}")

    t.paso, t.progreso = "render", 0.35

    def avance(x: float) -> None:
        t.progreso = 0.35 + 0.6 * x

    salida = c.ruta / "final.mp4"
    r = render(datos, salida, ff, voz=c.ruta / "audio" / "voz.wav", musica=Path(musica["ruta"]) if musica else None,
               volumen_musica_db=float(preset["volumen_musica_db"]), avisar=t.avisar, progreso=avance)
    destino = carpeta_videos() / f"el_calvo_explica_{c.ruta.name}.mp4"
    shutil.copy(salida, destino)
    informe = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "duracion": datos["video"]["duracion"],
               "escenas": len(datos["escenas"]), "render": r, "tiempo_total_s": round(time.time() - inicio, 1),
               "costos": _costos(c, config), "avisos_guion": avisos_guion, "avisos_ritmo": ritmo,
               "confianza_whisper": ors["confianza"], "musica": musica, "video": str(destino)}
    escribir_json(c.ruta / "informe.json", informe)
    t.avisar(f"Listo: {destino} · render en {r['segundos_total']:.0f} s · voz {informe['costos']['voz']['cop']}")
    return destino


def estado(nombre: str = TEMA_PRUEBA) -> dict:
    c = carpeta_base() / nombre
    return {"informe": leer_json(c / "informe.json") if (c / "informe.json").exists() else None,
            "video": (c / "final.mp4").exists()}
