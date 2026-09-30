"""Llena la biblioteca de efectos desde Freesound, SOLO con sonidos CC0 (dominio público).

Aprobado por el dueño como fuente: CC0 permite usarlos en YouTube monetizado sin pagar ni
atribuir. Por cada tipo de efecto se buscan los mejor calificados de la duración adecuada,
se bajan las vistas previas en alta calidad y se registran en la biblioteca con su enlace,
su autor y su licencia. Lo que no sea CC0 se descarta aunque aparezca en la búsqueda.
"""
from __future__ import annotations

import requests

from . import biblioteca
from .config import clave_api, leer_config

API = "https://freesound.org/apiv2/search/text/"
CAMPOS = "id,name,url,username,license,duration,previews,avg_rating,num_downloads"


class SinClaveFreesound(RuntimeError):
    pass


def _clave() -> str:
    clave = clave_api("FREESOUND_API_KEY")
    if not clave:
        raise SinClaveFreesound("falta la clave de Freesound (⚙ Ajustes)")
    return clave


def buscar(tipo: str, ajustes: dict, sesion=requests, conf: dict | None = None) -> list[dict]:
    conf = conf or ajustes["tipos"][tipo]
    lo, hi = conf["duracion"]
    r = sesion.get(API, params={"query": conf["buscar"], "filter": f'license:"Creative Commons 0" duration:[{lo} TO {hi}]',
                                "sort": "rating_desc", "fields": CAMPOS, "page_size": 30},
                   headers={"Authorization": f"Token {_clave()}"}, timeout=30)
    r.raise_for_status()
    # doble control: solo CC0 aunque el filtro fallara
    return [s for s in r.json().get("results", []) if s.get("license") == ajustes["licencia_aceptada"]
            and (s.get("previews") or {}).get("preview-hq-mp3")]


def llenar(tipos: list[str] | None = None, sesion=requests, avisar=print) -> dict:
    """Completa hasta `variantes_por_tipo` efectos por tipo. Lo ya registrado no se repite."""
    ajustes = leer_config("fuentes_audio.json")["freesound"]
    _clave()
    ya = {a["fuente"] for a in biblioteca.indice()}
    salida: dict[str, int] = {}
    for tipo in tipos or list(ajustes["tipos"]):
        tiene = len(biblioteca.utilizables("sfx", tipo))
        falta = ajustes["variantes_por_tipo"] - tiene
        salida[tipo] = 0
        if falta <= 0:
            continue
        avisar(f"Buscando «{tipo}» en Freesound (solo CC0)…")
        for s in buscar(tipo, ajustes, sesion):
            if salida[tipo] >= falta:
                break
            if s["url"] in ya:
                continue
            audio = sesion.get(s["previews"]["preview-hq-mp3"], timeout=60)
            audio.raise_for_status()
            try:
                biblioteca.registrar(audio.content, f"{s['name'][:40]}.mp3", "sfx", tipo, s["url"], "cc0",
                                     detalle_licencia=f"Freesound · autor {s['username']} · id {s['id']} · CC0 1.0")
            except ValueError:
                continue                                   # repetido u otro problema: se salta
            ya.add(s["url"])
            salida[tipo] += 1
    return salida


def llenar_musica(sesion=requests, avisar=print) -> dict:
    """Música de fondo tranquila (ánimo «suave»), también solo CC0. Lo ya registrado no se repite."""
    ajustes = leer_config("fuentes_audio.json")["freesound"]
    conf = ajustes["musica"]
    _clave()
    ya = {a["fuente"] for a in biblioteca.indice()}
    salida: dict[str, int] = {}
    for animo, busqueda in conf["animos"].items():
        falta = conf["pistas_por_animo"] - len(biblioteca.utilizables("musica", animo))
        salida[animo] = 0
        if falta <= 0:
            continue
        avisar(f"Buscando música {animo} en Freesound (solo CC0)…")
        for s in buscar(animo, ajustes, sesion, conf=busqueda):
            if salida[animo] >= falta:
                break
            if s["url"] in ya:
                continue
            audio = sesion.get(s["previews"]["preview-hq-mp3"], timeout=120)
            audio.raise_for_status()
            try:
                biblioteca.registrar(audio.content, f"{s['name'][:40]}.mp3", "musica", animo, s["url"], "cc0",
                                     detalle_licencia=f"Freesound · autor {s['username']} · id {s['id']} · CC0 1.0")
            except ValueError:
                continue
            ya.add(s["url"])
            salida[animo] += 1
    return salida


def asegurar_musica_suave(avisar=print) -> None:
    """Antes de editar: si no hay música suave y hay clave de Freesound, se busca (gratis). Si falla,
    el video sigue con la música que haya."""
    try:
        if biblioteca.utilizables("musica", "suave") or not clave_api("FREESOUND_API_KEY"):
            return
        llenar_musica(avisar=avisar)
    except Exception as ex:  # noqa: BLE001 — la música nunca frena el video
        avisar(f"Sin música nueva de Freesound ({str(ex)[:100]})")


def asegurar_efectos(tipos: list[str], avisar=print) -> None:
    """Antes de editar: los efectos que falten se buscan en Freesound (solo CC0, gratis). Si no hay clave o
    falla, se usa el provisional sintetizado."""
    try:
        faltan = [t for t in tipos if not biblioteca.utilizables("sfx", t)]
        if faltan and clave_api("FREESOUND_API_KEY"):
            llenar(faltan, avisar=avisar)
    except Exception as ex:  # noqa: BLE001 — un efecto nunca frena el video
        avisar(f"Sin efectos nuevos de Freesound ({str(ex)[:100]})")
