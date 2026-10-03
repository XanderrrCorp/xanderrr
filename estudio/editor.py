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
  musica      [{id, archivo, inicio, fin, desde, volumen}] | null   la pista de música tal como la dejó el
                                   usuario (null = la automática). archivo es la ruta dentro de la biblioteca
  sfx         [{id, inicio, tipo, volumen}] | null   los efectos de sonido (null = los automáticos)
  recortes    [[ini, fin], …]      tramos que se quitan del video al exportar (imagen, voz y todo)
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
            "animaciones": d.get("animaciones", {}), "musica": d.get("musica"), "sfx": d.get("sfx"),
            "recortes": d.get("recortes", []), "version": d.get("version", 0),
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
    # --- música y efectos tal como los dejó el usuario
    total = float(edl["duracion_total"])
    if ed.get("musica") is not None:
        edl["pistas"]["musica"] = [
            {"id": str(m.get("id") or f"u{k:02d}"), "archivo": m["archivo"],
             "inicio": round(max(0.0, float(m["inicio"])), 3),
             "fin": round(min(total, max(float(m["inicio"]) + 0.5, float(m["fin"]))), 3),
             "desde": round(max(0.0, float(m.get("desde", 0))), 3),
             "volumen": round(min(1.0, max(0.0, float(m.get("volumen", 0.18)))), 3), "ducking": True,
             "animo": m.get("animo")}
            for k, m in enumerate(ed["musica"]) if m.get("archivo") and float(m["inicio"]) < total]
    if ed.get("sfx") is not None:
        edl["pistas"]["sfx"] = [
            {"id": str(x.get("id") or f"u{k:03d}"), "inicio": round(min(max(0.0, float(x["inicio"])), total), 3),
             "tipo": x["tipo"], "archivo": f"biblioteca/sfx/{x['tipo']}",
             "variante": x.get("variante") or f"{x['tipo']}_1",
             "volumen": round(min(1.0, max(0.0, float(x.get("volumen", 0.7)))), 3),
             **({"duracion_max": x["duracion_max"]} if x.get("duracion_max") else {})}
            for k, x in enumerate(ed["sfx"]) if x.get("tipo")]
    if ed.get("version"):
        edl.setdefault("historial", []).append({"version": len(edl.get("historial", [])) + 1, "autor": "editor",
                                                "cambio": f"cambios del editor (v{ed['version']})",
                                                "razon": "Ajustes hechos a mano en el editor"})
    return edl


def edl_con_ediciones(raiz: Path) -> dict:
    edl = leer_json(raiz / "edl.json")
    ed = cargar(raiz)
    if not (ed["cortes"] or ed["subtitulos"] or ed["animaciones"] or ed["musica"] is not None
            or ed["sfx"] is not None):
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

    musica = [{"id": m.get("id"), "inicio": m["inicio"], "fin": m["fin"], "nombre": _nombre(m["archivo"]),
               "animo": m.get("animo"), "archivo": m["archivo"], "desde": m.get("desde", 0),
               "volumen": m.get("volumen", 0.18)} for m in edl["pistas"].get("musica", [])]
    sfx = []
    for k, x in enumerate(edl["pistas"].get("sfx", [])):
        dur = float(x.get("duracion_max") or 0.8)
        # los que «terminan en» un corte se muestran (y se guardan) por su comienzo real
        ini = float(x["termina_en"]) - dur if x.get("termina_en") is not None else float(x["inicio"])
        sfx.append({"id": x.get("id") or f"s{k:03d}", "inicio": round(max(0.0, ini), 3),
                    "tipo": x.get("tipo") or (x.get("variante") or "pop").rsplit("_", 1)[0], "dur": dur,
                    "variante": x.get("variante"), "volumen": x.get("volumen", 0.7),
                    "duracion_max": x.get("duracion_max")})
    final = raiz / "render" / "final.mp4"
    return {"duracion": edl["duracion_total"], "escenas": escenas, "voz": voces, "musica": musica, "sfx": sfx,
            "subtitulos": [{**s, "editado": str(s.get("escena")) in ed["subtitulos"]} for s in edl["pistas"]["subtitulos"]],
            "video": "render/final.mp4" if final.exists() else None,
            "video_version": int(final.stat().st_mtime) if final.exists() else 0,
            "recortes": ed["recortes"], "musica_editada": ed["musica"] is not None,
            "sfx_editados": ed["sfx"] is not None,
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


# ------------------------------------------------------------------ música, efectos y recortes

def cambiar_musica(raiz: Path, lista: list[dict] | None) -> dict:
    """La pista de música completa como la dejó el usuario (None = volver a la automática)."""
    from . import biblioteca

    ed = cargar(raiz)
    if lista is None:
        ed["musica"] = None
        return guardar(raiz, ed)
    validos = {a["archivo"] for a in biblioteca.indice() if a["clase"] == "musica" and not a.get("revisar_licencia")}
    limpia = []
    for k, m in enumerate(lista):
        if m["archivo"] not in validos:
            raise ValueError("esa canción no está en la biblioteca (o su licencia falta por revisar)")
        limpia.append({"id": str(m.get("id") or f"u{k:02d}"), "archivo": m["archivo"],
                       "inicio": round(float(m["inicio"]), 3), "fin": round(float(m["fin"]), 3),
                       "desde": round(float(m.get("desde", 0)), 3), "volumen": round(float(m.get("volumen", 0.18)), 3)})
    ed["musica"] = limpia
    return guardar(raiz, ed)


def cambiar_sfx(raiz: Path, lista: list[dict] | None) -> dict:
    from .biblioteca import TIPOS_SFX

    ed = cargar(raiz)
    if lista is None:
        ed["sfx"] = None
        return guardar(raiz, ed)
    limpia = []
    for k, x in enumerate(lista):
        if x["tipo"] not in TIPOS_SFX:
            raise ValueError(f"efecto desconocido: {x['tipo']}")
        limpia.append({"id": str(x.get("id") or f"u{k:03d}"), "inicio": round(float(x["inicio"]), 3), "tipo": x["tipo"],
                       "variante": x.get("variante"), "volumen": round(float(x.get("volumen", 0.7)), 3),
                       **({"duracion_max": float(x["duracion_max"])} if x.get("duracion_max") else {})})
    ed["sfx"] = sorted(limpia, key=lambda x: x["inicio"])
    return guardar(raiz, ed)


def unir_recortes(recortes: list) -> list[list[float]]:
    """Ordena, descarta los de menos de 0,1 s y une los que se tocan."""
    salida: list[list[float]] = []
    for a, b in sorted((min(float(a), float(b)), max(float(a), float(b))) for a, b in recortes):
        if b - a < 0.1:
            continue
        if salida and a <= salida[-1][1] + 0.05:
            salida[-1][1] = max(salida[-1][1], round(b, 3))
        else:
            salida.append([round(a, 3), round(b, 3)])
    return salida


def cambiar_recortes(raiz: Path, recortes: list) -> dict:
    ed = cargar(raiz)
    ed["recortes"] = unir_recortes(recortes)
    return guardar(raiz, ed)


def _quedan(recortes: list[list[float]], total: float) -> list[tuple[float, float]]:
    tramos, cursor = [], 0.0
    for a, b in recortes:
        if a > cursor:
            tramos.append((cursor, min(a, total)))
        cursor = max(cursor, b)
    if cursor < total:
        tramos.append((cursor, total))
    return [(a, b) for a, b in tramos if b - a > 0.02]


def nuevo_tiempo(t: float, recortes: list[list[float]]) -> float | None:
    """Dónde cae el segundo `t` del video original después de quitar los recortes (None si se quitó)."""
    quitado = 0.0
    for a, b in recortes:
        if t >= b:
            quitado += b - a
        elif t > a:
            return None
    return t - quitado


def aplicar_recortes(raiz: Path, video: Path, ffmpeg: str) -> Path:
    """Quita del video exportado los tramos marcados (imagen y sonido juntos) y corre los subtítulos."""
    import re
    import subprocess

    recortes = unir_recortes(cargar(raiz)["recortes"])
    if not recortes:
        return video
    r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr or "")
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 1e9
    quedan = _quedan(recortes, total)
    filtro, partes = "", []
    for k, (a, b) in enumerate(quedan):
        filtro += (f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{k}];"
                   f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{k}];")
        partes.append(f"[v{k}][a{k}]")
    filtro += "".join(partes) + f"concat=n={len(quedan)}:v=1:a=1[v][a]"
    from .render import _argumentos_codificador

    tmp = video.with_name(video.stem + ".recortado.mp4")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-filter_complex", filtro,
                    "-map", "[v]", "-map", "[a]", *_argumentos_codificador(ffmpeg, "medium", "18", None),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(tmp)],
                   check=True, capture_output=True)
    tmp.replace(video)
    srt = video.with_suffix(".srt")
    if srt.exists():
        srt.write_text(_srt_recortado(srt.read_text(encoding="utf-8"), recortes), encoding="utf-8")
    return video


def _srt_recortado(texto: str, recortes: list[list[float]]) -> str:
    import re

    def seg(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    def reloj(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    bloques, n = [], 0
    for b in re.split(r"\n\s*\n", texto.strip()):
        lineas = b.strip().splitlines()
        if len(lineas) < 2:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+)\s*-->\s*(\d+):(\d+):(\d+),(\d+)", lineas[1])
        if not m:
            continue
        a, z = nuevo_tiempo(seg(*m.groups()[:4]), recortes), nuevo_tiempo(seg(*m.groups()[4:]), recortes)
        if a is None or z is None or z <= a:
            continue
        n += 1
        bloques.append("\n".join([str(n), f"{reloj(a)} --> {reloj(z)}", *lineas[2:]]))
    return "\n\n".join(bloques) + "\n"
