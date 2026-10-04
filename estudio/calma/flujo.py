"""El video de prueba de Hazlo con Calma, de punta a punta (lo que corre el botón de la página).

guion + escenas.json → voz MiniMax (la del canal) → Whisper palabra por palabra → cada elemento entra
cuando el narrador dice su palabra → render de los cuadros → voz + música de fondo bajita → MP4.

Todo vive aparte, en <datos>/calma/<video>/ (no toca los proyectos ni el pipeline de siempre).
Reanudable: la voz ya pagada y lo ya transcrito no se repiten.
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from ..config import ConfigCostos, escribir_json, leer_config, leer_json
from ..costos import LibroCostos
from . import escenas as E

EJEMPLOS = Path(__file__).resolve().parent / "ejemplos"
POR_DEFECTO = {
    "voz_id": None,               # la voz de MiniMax del canal (el código que muestra MiniMax)
    "velocidad": 1.0,
    "musica": None,               # None = la elige sola de la biblioteca (tensión, ritmo bajo, sin melodía)
    "volumen_musica_db": -27.0,   # bajita: la voz siempre manda
    "segundos": 60.0,             # largo de la prueba: corta al final de la última oración que cabe
}


def carpeta_base() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "calma"
    c.mkdir(parents=True, exist_ok=True)
    return c


def ajustes() -> dict:
    ruta = carpeta_base() / "ajustes.json"
    guardado = leer_json(ruta) if ruta.exists() else {}
    return {**POR_DEFECTO, **{k: v for k, v in guardado.items() if k in POR_DEFECTO}}


def guardar_ajustes(cambios: dict) -> dict:
    a = ajustes()
    a.update({k: v for k, v in cambios.items() if k in POR_DEFECTO})
    escribir_json(carpeta_base() / "ajustes.json", a)
    return a


class Carpeta:
    """Lo mínimo que piden la voz y Whisper de Tracy: la ruta y el libro de costos."""

    def __init__(self, ruta: Path):
        self.ruta = ruta

    def libro(self, config: ConfigCostos) -> LibroCostos:
        return LibroCostos(self.ruta, config)


def preparar(nombre: str = "garrapata_60s") -> Carpeta:
    """Copia el guion y las escenas de ejemplo a su carpeta de trabajo (si ya están, no las pisa)."""
    c = Carpeta(carpeta_base() / nombre)
    c.ruta.mkdir(parents=True, exist_ok=True)
    for ext in (".txt", ".json"):
        destino = c.ruta / ("guion.txt" if ext == ".txt" else "escenas.json")
        if not destino.exists():
            shutil.copy(EJEMPLOS / f"{nombre}{ext}", destino)
    return c


def ajustes_voz(a: dict) -> dict:
    base = dict(leer_config("proveedores.json")["voz"])
    if a.get("voz_id"):
        base["voz_id"] = a["voz_id"]
    base["velocidad"] = float(a.get("velocidad") or 1.0)
    return base


def costo_estimado(nombre: str = "garrapata_60s") -> dict:
    texto = (EJEMPLOS / f"{nombre}.txt").read_text(encoding="utf-8")
    config = ConfigCostos.cargar()
    usd = len(texto) / 1000 * config.precio("tts_por_1000_caracteres")
    from ..costos import formato_cop

    return {"caracteres": len(texto), "usd": round(usd, 3), "cop": formato_cop(config.a_cop(usd))}


def fin_de_oracion(palabras: list[dict], hasta: float) -> float:
    """El final de la última oración que termina antes de `hasta` (más un respiro)."""
    fin = None
    for w in palabras:
        if w["p"].endswith((".", "?", "!", "…")) and w["fin"] <= hasta - 0.4:
            fin = w["fin"]
    return min(hasta, (fin if fin is not None else hasta - 0.4) + 0.4)


def producir(c: Carpeta, t, permiso: bool = False, voz=None, transcriptor=None, proveedor: str | None = None) -> Path:
    from ..pipeline import carpeta_videos, ffmpeg
    from ..tracy.alineacion import alinear, transcriptor_para
    from ..tracy.audio import generar_audio, voz_para
    from .musica import elegir
    from .render import render

    a = ajustes()
    ff = ffmpeg()
    config = ConfigCostos.cargar()
    guion = (c.ruta / "guion.txt").read_text(encoding="utf-8")
    informe: dict = {"inicio": time.strftime("%Y-%m-%d %H:%M:%S")}

    t.paso, t.progreso = "voz", 0.03
    if voz is None:
        if proveedor != "simulado" and not a.get("voz_id"):
            raise RuntimeError("Falta el código de la voz de Hazlo con Calma (MiniMax): pégalo en la página")
        if proveedor == "simulado":
            voz = voz_para("simulado", {}, config)
        else:
            from ..voz import VozMiniMax

            voz = VozMiniMax(config, ajustes_voz(a))
    t.avisar("Generando la voz con MiniMax…" if voz.nombre != "simulado" else "Voz simulada (ensayo sin gastar)…")
    r = generar_audio(c, guion, ff, voz, {"bloque_tts_max": 2500}, config, permiso=permiso, avisar=t.avisar)
    informe["costo_voz_usd"] = round(r["costo_usd"], 4)

    t.paso, t.progreso = "whisper", 0.2
    ors = alinear(c, transcriptor or transcriptor_para(proveedor), avisar=t.avisar)
    t.avisar(f"Whisper: coincidencia con el guion {ors['confianza']:.0%}")
    palabras = E.palabras_de(ors)

    t.paso, t.progreso = "escenas", 0.3
    datos = json.loads((c.ruta / "escenas.json").read_text(encoding="utf-8"))
    E.fijar_tiempos(datos, palabras, float(ors["duracion"]))
    largo = fin_de_oracion(palabras, float(a["segundos"]) + 0.5)
    E.recortar(datos, largo)
    avisos = E.revisar(datos)
    for x in avisos:
        t.avisar(f"  ritmo: {x}")
    escribir_json(c.ruta / "escenas_con_tiempos.json", datos)

    musica = None
    if a.get("musica"):
        musica = {"ruta": a["musica"], "nombre_original": Path(a["musica"]).name, "elegida": "a mano"}
    else:
        musica = elegir(ff, avisar=t.avisar)
    if musica:
        t.avisar(f"Música: {musica['nombre_original']}")

    t.paso, t.progreso = "render", 0.35

    def avance(x: float) -> None:
        t.progreso = 0.35 + 0.6 * x

    salida = c.ruta / "final.mp4"
    r_render = render(datos, salida, ff, voz=c.ruta / "audio" / "voz.wav",
                      musica=Path(musica["ruta"]) if musica else None,
                      volumen_musica_db=float(a["volumen_musica_db"]), avisar=t.avisar, progreso=avance)
    destino = carpeta_videos() / f"hazlo_con_calma_{c.ruta.name}.mp4"
    shutil.copy(salida, destino)
    informe.update(render=r_render, duracion=round(largo, 2), escenas=len(datos["escenas"]), avisos_ritmo=avisos,
                   musica=musica, confianza_whisper=ors["confianza"], video=str(destino))
    escribir_json(c.ruta / "informe.json", informe)
    t.avisar(f"Video listo: {destino} · render de {largo:.0f} s de video en {r_render['segundos_total']:.0f} s")
    return destino
