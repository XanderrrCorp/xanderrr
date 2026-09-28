"""Editor de videos terminados (tipo CapCut).

La edición automática sigue en edl.json (la arma el Director de edición). Lo que el usuario cambia
en el editor va aparte, en ediciones.json, y se aplica encima al exportar: así nunca se pisa lo
automático, cada cambio se puede deshacer y sobrevive a que se regenere una imagen o un audio.

ediciones.json:
  cortes      {escena: segundos}   corre el corte con la escena anterior (+ más tarde, − más temprano);
                                   la voz no se mueve
  subtitulos  {escena: [{texto, ini, fin}]}   los subtítulos de esa escena, con tiempos relativos al
                                   inicio de su voz (siguen en su sitio si la voz se regenera)
  animaciones {escena: archivo}    la escena se ve como clip animado en vez de imagen fija
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

from .config import escribir_json, leer_json

ARCHIVO = "ediciones.json"
MIN_CLIP = 0.4          # ninguna escena queda más corta que esto al mover un corte


def cargar(raiz: Path) -> dict:
    ruta = raiz / ARCHIVO
    d = leer_json(ruta) if ruta.exists() else {}
    return {"cortes": d.get("cortes", {}), "subtitulos": d.get("subtitulos", {}),
            "animaciones": d.get("animaciones", {}), "version": d.get("version", 0),
            "actualizado": d.get("actualizado")}


def guardar(raiz: Path, ed: dict) -> dict:
    ed = {**ed, "version": int(ed.get("version", 0)) + 1,
          "actualizado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    escribir_json(raiz / ARCHIVO, ed)
    return ed


def _voz_de_escenas(raiz: Path) -> dict[int, tuple[float, float]]:
    ruta = raiz / "escenas.json"
    if not ruta.exists():
        return {}
    salida = {}
    for e in leer_json(ruta).get("escenas", []):
        t = e.get("tiempo") or {}
        if t.get("real_inicio") is not None:
            salida[int(e["id"])] = (float(t["real_inicio"]), float(t["real_fin"]))
    return salida


def aplicar(edl: dict, ed: dict, voz: dict[int, tuple[float, float]], raiz: Path | None = None) -> dict:
    """La EDL automática con los cambios del editor (no modifica la original)."""
    edl = copy.deepcopy(edl)
    clips = edl["pistas"]["escenas"]
    idx = {c["escena"]: k for k, c in enumerate(clips)}
    # --- cortes: se mueve el límite entre una escena y la anterior
    for sid, delta in sorted(((int(k), float(v)) for k, v in ed.get("cortes", {}).items()), key=lambda x: x[0]):
        k = idx.get(sid)
        if not k:                               # la primera escena empieza siempre en 0
            continue
        prev, c = clips[k - 1], clips[k]
        nuevo = min(max(c["inicio"] + delta, prev["inicio"] + MIN_CLIP), c["fin"] - MIN_CLIP)
        prev["fin"] = c["inicio"] = round(nuevo, 3)
    for c in clips:                             # los efectos quedan dentro de su escena
        for ef in c.get("efectos", []):
            if "en" in ef:
                ef["en"] = round(min(max(ef["en"], c["inicio"]), max(c["inicio"], c["fin"] - 0.05)), 3)
            if ef.get("efecto") in ("video_real",) and "dur" in ef:
                ef["dur"] = round(max(0.1, c["fin"] - ef["en"]), 3)
    # --- animaciones: la escena se ve como clip (el mismo camino que un video real)
    for sid, archivo in ed.get("animaciones", {}).items():
        k = idx.get(int(sid))
        if k is None or (raiz is not None and not (raiz / archivo).exists()):
            continue
        c = clips[k]
        c["efectos"] = [x for x in c.get("efectos", []) if x.get("efecto") != "video_real"]
        c["efectos"].append({"efecto": "video_real", "en": c["inicio"], "dur": round(c["fin"] - c["inicio"], 3),
                             "archivo": archivo, "desde": 0, "origen": "animacion"})
    # --- subtítulos corregidos, escena por escena
    subs = edl["pistas"].get("subtitulos", [])
    for sid, lista in ed.get("subtitulos", {}).items():
        sid = int(sid)
        if sid not in voz:
            continue
        base = voz[sid][0]
        subs = [s for s in subs if s.get("escena") != sid]
        for s in lista:
            ini = round(base + float(s["ini"]), 3)
            fin = round(max(base + float(s["fin"]), ini + 0.2), 3)
            if s.get("texto", "").strip():
                subs.append({"inicio": ini, "fin": fin, "texto": s["texto"].strip(), "escena": sid})
    edl["pistas"]["subtitulos"] = sorted(subs, key=lambda s: s["inicio"])
    if ed.get("version"):
        edl.setdefault("historial", []).append({"version": len(edl.get("historial", [])) + 1, "autor": "editor",
                                                "cambio": f"cambios del editor (v{ed['version']})",
                                                "razon": "Ajustes hechos a mano en el editor"})
    return edl


def edl_con_ediciones(raiz: Path) -> dict:
    edl = leer_json(raiz / "edl.json")
    ed = cargar(raiz)
    if not (ed["cortes"] or ed["subtitulos"] or ed["animaciones"]):
        return edl
    return aplicar(edl, ed, _voz_de_escenas(raiz), raiz)


# ------------------------------------------------------------------ lo que ve el editor

def linea_de_tiempo(raiz: Path) -> dict:
    """Las pistas del video tal como quedarían al exportar (con los cambios ya aplicados)."""
    edl = edl_con_ediciones(raiz)
    esc = {int(e["id"]): e for e in leer_json(raiz / "escenas.json").get("escenas", [])}
    man_ruta = raiz / "imagenes" / "manifiesto.json"
    ed = cargar(raiz)
    voz = _voz_de_escenas(raiz)
    escenas = []
    for c in edl["pistas"]["escenas"]:
        e = esc.get(c["escena"], {})
        animado = next((x["archivo"] for x in c.get("efectos", []) if x.get("efecto") == "video_real"), None)
        escenas.append({"id": c["escena"], "inicio": c["inicio"], "fin": c["fin"], "imagen": c["archivo"],
                        "animacion": animado if str(c["escena"]) in ed["animaciones"] else None,
                        "video_real": animado if str(c["escena"]) not in ed["animaciones"] else None,
                        "narracion": e.get("narracion", ""), "seccion": e.get("seccion", ""),
                        "puede_regenerar": (e.get("visual") or {}).get("accion") == "generar",
                        "modo": c.get("modo"), "corte_movido": str(c["escena"]) in ed["cortes"]})
    voces = [{"escena": sid, "inicio": a, "fin": b} for sid, (a, b) in sorted(voz.items(), key=lambda x: x[1][0])]

    def _nombre(archivo: str) -> str:
        return Path(archivo).stem.replace("_", " ")

    musica = [{"inicio": m["inicio"], "fin": m["fin"], "nombre": _nombre(m["archivo"]), "animo": m.get("animo")}
              for m in edl["pistas"].get("musica", [])]
    sfx = [{"inicio": s["inicio"], "tipo": s.get("tipo") or _nombre(s["archivo"]),
            "dur": float(s.get("duracion_max") or 0.8)} for s in edl["pistas"].get("sfx", [])]
    final = raiz / "render" / "final.mp4"
    return {"duracion": edl["duracion_total"], "escenas": escenas, "voz": voces, "musica": musica, "sfx": sfx,
            "subtitulos": [{**s, "editado": str(s.get("escena")) in ed["subtitulos"]} for s in edl["pistas"]["subtitulos"]],
            "video": "render/final.mp4" if final.exists() else None,
            "video_version": int(final.stat().st_mtime) if final.exists() else 0,
            "ediciones": {"version": ed["version"], "actualizado": ed["actualizado"],
                          "pendientes": bool(ed["actualizado"]) and (not final.exists() or
                                                                   (raiz / ARCHIVO).stat().st_mtime > final.stat().st_mtime)}}


def mover_corte(raiz: Path, escena: int, nuevo_inicio: float) -> dict:
    """Arrastrar el borde izquierdo de una escena: se guarda cuánto se movió respecto a lo automático."""
    base = {c["escena"]: c for c in leer_json(raiz / "edl.json")["pistas"]["escenas"]}
    if escena not in base:
        raise KeyError("esa escena no está en el video")
    ed = cargar(raiz)
    delta = round(float(nuevo_inicio) - base[escena]["inicio"], 3)
    if abs(delta) < 0.01:
        ed["cortes"].pop(str(escena), None)
    else:
        ed["cortes"][str(escena)] = delta
    return guardar(raiz, ed)


def cambiar_subtitulos(raiz: Path, escena: int, lista: list[dict]) -> dict:
    """lista con tiempos ABSOLUTOS (como se ven en la línea de tiempo); se guardan relativos a la voz."""
    voz = _voz_de_escenas(raiz)
    if escena not in voz:
        raise KeyError("esa escena no tiene voz")
    base = voz[escena][0]
    ed = cargar(raiz)
    ed["subtitulos"][str(escena)] = [{"texto": str(s["texto"]), "ini": round(float(s["inicio"]) - base, 3),
                                      "fin": round(float(s["fin"]) - base, 3)} for s in lista]
    return guardar(raiz, ed)


def deshacer_escena(raiz: Path, escena: int, que: str) -> dict:
    ed = cargar(raiz)
    ed.get({"corte": "cortes", "subtitulos": "subtitulos", "animacion": "animaciones"}[que], {}).pop(str(escena), None)
    return guardar(raiz, ed)
