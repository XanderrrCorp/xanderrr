"""Liberar espacio: muestra cuánto ocupa Xandart y borra SOLO lo que Xandart puede volver a hacer solo.

Se borra (únicamente en videos TERMINADOS y sin trabajo en marcha):
- los pedazos de video del render (render/tramos, render/tracy/tramo_*.mp4), el video sin sonido
  (video_mudo.mp4), los subtítulos en imagen y los temporales (*.video.mp4, *.tmp.mp4, *.ffmpeg.log);
- los clips de Pexels guardados (datos/cache/pexels) que ya no usa ningún video sin terminar.

- las capas de profundidad (assets/capas) de videos terminados: se vuelven a hacer solas si se rehace el video.

Además (16-10, «me consumen toda la memoria de la PC con archivos»):
- el video final se guardaba DOS veces (en el proyecto y en «Videos › Xandart»): ahora la segunda es un enlace al
  mismo archivo (ocupa una sola vez) y «liberar» convierte las copias viejas en enlaces;
- «copias de seguridad viejas»: cada copia guarda TODOS los proyectos; con permiso del dueño se borran todas menos
  la más reciente;
- «archivos de trabajo de videos ya subidos»: con permiso, en videos terminados hace más de N días se borran las
  imágenes, voces y clips (queda el video final en «Videos › Xandart» y el guion). Ese video ya no se puede rehacer.

Nunca se borra un video terminado ni nada de un video sin terminar o haciéndose.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def _tamano(ruta: Path) -> int:
    if not ruta.exists():
        return 0
    if ruta.is_file():
        return ruta.stat().st_size
    return sum(f.stat().st_size for f in ruta.rglob("*") if f.is_file())


def _gb(b: int) -> str:
    return f"{b / 2**30:.2f} GB" if b >= 2**30 else f"{b / 2**20:.0f} MB"


def _proyectos() -> list[Path]:
    from .config import ruta_proyectos

    base = ruta_proyectos()
    return [d for d in base.iterdir() if (d / "proyecto.json").exists()] if base.exists() else []


def _terminado(d: Path) -> bool:
    if (d / "render" / "final.mp4").exists():
        return True
    try:
        datos = json.loads((d / "proyecto.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (datos.get("pasos") or {}).get("export_final", {}).get("estado") == "completo"


def _final_entregado(d: Path) -> Path | None:
    """El video que quedó en «Videos › Xandart» (según el proyecto)."""
    try:
        datos = json.loads((d / "proyecto.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for x in (datos.get("pasos") or {}).get("export_final", {}).get("salida") or []:
        if str(x).lower().endswith(".mp4") and Path(x).exists():
            return Path(x)
    return None


def copiar_o_enlazar(origen: Path, destino: Path) -> None:
    """Deja `destino` con el mismo contenido que `origen` ocupando el espacio UNA vez (enlace duro, si los dos
    están en el mismo disco); si no se puede, copia normal."""
    import os

    tmp = destino.with_name(destino.name + ".enlace")
    try:
        tmp.unlink(missing_ok=True)
        os.link(origen, tmp)
        os.replace(tmp, destino)
    except OSError:
        tmp.unlink(missing_ok=True)
        shutil.copy(origen, destino)


def _mismo_archivo(a: Path, b: Path) -> bool:
    try:
        return a.samefile(b)
    except OSError:
        return False


def _ocupado(d: Path) -> bool:
    from . import pipeline

    t = pipeline.TRABAJOS.get(d.name)
    return bool(t and t.activo)


def intermedios(d: Path) -> list[Path]:
    """Lo que el render deja y se puede volver a hacer (solo dentro de render/)."""
    r = d / "render"
    if not r.exists():
        return []
    salida = [p for p in (r / "tramos",) if p.exists()]
    tracy = r / "tracy"
    if tracy.exists():
        salida += sorted(tracy.glob("tramo_*.mp4")) + sorted(tracy.glob("subs_*"))
        salida += [p for p in (tracy / "video_mudo.mp4", tracy / "lista.txt", tracy / "swoosh.wav") if p.exists()]
    for patron in ("*.video.mp4", "*.tmp.mp4", "*.ffmpeg.log", "*_pedazos", "*.mezcla.wav"):
        salida += sorted(r.glob(patron))
    capas = d / "assets" / "capas"
    if capas.exists():
        salida.append(capas)
    return salida


def limpiar_proyecto(slug: str) -> int:
    """Al terminar un video (la cola lo llama sola): borra sus pedazos de render. Devuelve los bytes liberados."""
    from .config import ruta_proyectos

    d = ruta_proyectos() / slug
    if not d.exists() or not _terminado(d) or _ocupado(d):
        return 0
    liberado = 0
    for p in intermedios(d):
        b = _tamano(p)
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        except OSError:
            continue
        liberado += b
    return liberado


def duplicados() -> list[tuple[Path, Path]]:
    """(final del proyecto, copia en Videos) que ocupan dos veces lo mismo."""
    salida = []
    for d in _proyectos():
        final, entregado = d / "render" / "final.mp4", _final_entregado(d)
        if final.exists() and entregado and not _mismo_archivo(final, entregado) \
                and final.stat().st_size == entregado.stat().st_size and not _ocupado(d):
            salida.append((final, entregado))
    return salida


# ------------------------------------------------------------------ con permiso del dueño

def copias_viejas() -> list[Path]:
    """Todas las copias de seguridad menos la más reciente."""
    from .plataforma.copias import carpeta_copias

    base = carpeta_copias()
    copias = sorted((c.parent for c in base.glob("*/copia.json")), key=lambda c: c.name) if base.exists() else []
    return copias[:-1]


PESADOS = ("imagenes", "audio", "assets", "render")


def archivables(dias: int = 30) -> list[Path]:
    """Videos terminados hace más de `dias` días, con su video final a salvo en «Videos › Xandart»."""
    import time

    limite = time.time() - dias * 86400
    salida = []
    for d in _proyectos():
        if not _terminado(d) or _ocupado(d) or (d / "archivado.json").exists():
            continue
        if _final_entregado(d) is None:
            continue                     # sin el video a salvo afuera, no se toca
        if (d / "proyecto.json").stat().st_mtime < limite:
            salida.append(d)
    return salida


def archivar(d: Path) -> int:
    """Borra los archivos de trabajo de un video ya subido (queda el guion y el video en «Videos › Xandart»)."""
    entregado = _final_entregado(d)
    if entregado is None:
        return 0
    if (d / "render" / "final.mp4").exists() and _mismo_archivo(d / "render" / "final.mp4", entregado):
        pass                                     # el enlace se borra, el video de Videos queda
    liberado = 0
    for nombre in PESADOS:
        p = d / nombre
        if p.exists():
            b = _tamano(p)
            shutil.rmtree(p, ignore_errors=True)
            liberado += b - _tamano(p)
    (d / "archivado.json").write_text(json.dumps({"video": str(entregado)}, ensure_ascii=False), encoding="utf-8")
    return liberado


def _clips_en_uso() -> set[str]:
    """Clips de Pexels que usa algún video SIN terminar (esos no se tocan)."""
    usados: set[str] = set()
    for d in _proyectos():
        if _terminado(d):
            continue
        for nombre in ("clips.json", "plan_visual.json"):
            ruta = d / nombre
            if ruta.exists():
                try:
                    texto = ruta.read_text(encoding="utf-8")
                except OSError:
                    continue
                usados |= {Path(x).name for x in _rutas_en(json.loads(texto))}
    return usados


def _rutas_en(dato) -> list[str]:
    if isinstance(dato, dict):
        return [v for k, v in dato.items() if k == "archivo" and isinstance(v, str)] + \
            [x for v in dato.values() for x in _rutas_en(v)]
    if isinstance(dato, list):
        return [x for v in dato for x in _rutas_en(v)]
    return []


def _pexels() -> Path:
    from .plataforma.db import carpeta_datos

    return carpeta_datos() / "cache" / "pexels"


def que_se_puede_borrar() -> list[Path]:
    salida = []
    for d in _proyectos():
        if _terminado(d) and not _ocupado(d):
            salida += intermedios(d)
    cache = _pexels()
    if cache.exists():
        en_uso = _clips_en_uso()
        salida += [f for f in sorted(cache.glob("*.mp4")) if f.name not in en_uso]
    return salida


def inventario() -> dict:
    from .config import ruta_proyectos
    from .pipeline import carpeta_videos
    from .plataforma.copias import carpeta_copias

    borrable = que_se_puede_borrar()
    dobles = duplicados()
    libera = sum(_tamano(p) for p in borrable) + sum(f.stat().st_size for f, _ in dobles)
    viejas = copias_viejas()
    archivo = archivables()
    partes = [
        {"nombre": "Proyectos (tus videos con sus imágenes y voces)", "carpeta": str(ruta_proyectos()),
         "bytes": _tamano(ruta_proyectos())},
        {"nombre": "Clips de Pexels guardados (Tracy)", "carpeta": str(_pexels()), "bytes": _tamano(_pexels())},
        {"nombre": "Copias de seguridad", "carpeta": str(carpeta_copias()), "bytes": _tamano(carpeta_copias())},
        {"nombre": "Videos terminados (Videos › Xandart)", "carpeta": str(carpeta_videos()),
         "bytes": _tamano(carpeta_videos())},
    ]
    for p in partes:
        p["texto"] = _gb(p["bytes"])
    b_viejas = sum(_tamano(c) for c in viejas)
    b_archivo = sum(_tamano(d / n) for d in archivo for n in PESADOS)
    return {"partes": partes, "se_puede_liberar": libera, "se_puede_liberar_texto": _gb(libera),
            "archivos": len(borrable) + len(dobles), "hay_trabajo": _hay_trabajo(),
            "copias_viejas": len(viejas), "copias_viejas_texto": _gb(b_viejas),
            "videos_viejos": len(archivo), "videos_viejos_texto": _gb(b_archivo),
            "videos_viejos_lista": [d.name for d in archivo][:50]}


def _hay_trabajo() -> bool:
    from . import pipeline

    return any(t.activo for t in pipeline.TRABAJOS.values())


def liberar() -> dict:
    """Borra lo de `que_se_puede_borrar`. No corre si hay un video haciéndose."""
    if _hay_trabajo():
        raise RuntimeError("Hay un video haciéndose: espera a que termine y vuelve a intentarlo")
    liberado, n = 0, 0
    for p in que_se_puede_borrar():
        b = _tamano(p)
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
        except OSError:
            continue                              # algo abierto en otro programa: se deja
        liberado += b
        n += 1
    for final, entregado in duplicados():          # el video guardado dos veces pasa a ocupar una sola
        b = final.stat().st_size
        try:
            copiar_o_enlazar(final, entregado)
        except OSError:
            continue
        if _mismo_archivo(final, entregado):
            liberado += b
            n += 1
    return {"liberado": liberado, "liberado_texto": _gb(liberado), "archivos": n}


def borrar_copias_viejas() -> dict:
    if _hay_trabajo():
        raise RuntimeError("Hay un video haciéndose: espera a que termine y vuelve a intentarlo")
    liberado = 0
    for c in copias_viejas():
        b = _tamano(c)
        shutil.rmtree(c, ignore_errors=True)
        liberado += b - _tamano(c)
    return {"liberado": liberado, "liberado_texto": _gb(liberado)}


def archivar_viejos(dias: int = 30) -> dict:
    if _hay_trabajo():
        raise RuntimeError("Hay un video haciéndose: espera a que termine y vuelve a intentarlo")
    liberado, n = 0, 0
    for d in archivables(dias):
        liberado += archivar(d)
        n += 1
    return {"liberado": liberado, "liberado_texto": _gb(liberado), "videos": n}
