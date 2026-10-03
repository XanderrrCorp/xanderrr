"""Miniatura de un video con la plantilla «texto_izquierda_retrato_derecha".

Todo vive en <proyecto>/miniatura_texto/:
- fondo.jpg       el fondo de ESTE video (rotado o generado; editar el texto no lo cambia)
- opcion_N.jpg    una miniatura por fórmula del planificador (1 a 4)
- estado.json     opciones (fórmula, texto, avisos), paleta, la elegida y de dónde salió el fondo
- miniatura.jpg   la elegida, lista para subir (también se copia junto a los videos)
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from PIL import Image

from ..config import ConfigCostos, escribir_json, leer_json
from ..costos import LibroCostos, formato_cop
from ..proyecto import CarpetaProyecto
from . import texto_retrato as tr

CARPETA = "miniatura_texto"


def carpeta(c: CarpetaProyecto) -> Path:
    return c.ruta / CARPETA


def _estado(c: CarpetaProyecto) -> dict:
    ruta = carpeta(c) / "estado.json"
    return leer_json(ruta) if ruta.exists() else {"opciones": [], "elegida": None, "paleta": "auto"}


def _guardar(c: CarpetaProyecto, e: dict) -> None:
    escribir_json(carpeta(c) / "estado.json", e)


def _config(c: CarpetaProyecto) -> tr.ConfigTexto:
    return tr.cargar_config(c.cargar().canal)


def duracion_video(c: CarpetaProyecto) -> float:
    """La duración REAL: la del video armado; si aún no hay, la de la voz; si no, la pedida."""
    edl = c.ruta / "edl.json"
    if edl.exists():
        return float(leer_json(edl).get("duracion_total") or 0) or 60.0
    voz = c.ruta / "audio" / "voz.wav"
    if voz.exists():
        import wave

        with wave.open(str(voz)) as w:
            return w.getnframes() / w.getframerate()
    return float(c.cargar().duracion_objetivo_seg or 600)


def _nuevo_fondo(c: CarpetaProyecto, cfg: tr.ConfigTexto, e: dict, t=None, permiso: bool = False,
                 generar: bool | None = None, proveedor=None) -> None:
    """Un fondo para este video, distinto del anterior: rotado de la carpeta o generado."""
    destino = carpeta(c) / "fondo.jpg"
    destino.parent.mkdir(parents=True, exist_ok=True)
    generar = cfg.fuente_fondos == "generar" if generar is None else generar
    if generar:
        if t:
            t.avisar("Generando un fondo nuevo…")
        libro = LibroCostos(c.ruta, ConfigCostos.cargar())
        tr.generar_fondo(cfg, destino, libro, permiso=permiso, proveedor=proveedor)
        e["fondo_origen"] = "generado"
    else:
        elegido = tr.siguiente_fondo(cfg, evitar=e.get("fondo_origen"))
        tr._cubrir(Image.open(elegido).convert("RGB"), tr.W, tr.H).save(destino, quality=92)
        e["fondo_origen"] = elegido.name


def _render(c: CarpetaProyecto, cfg: tr.ConfigTexto, e: dict, indices: list[int] | None = None) -> None:
    fondo = Image.open(carpeta(c) / "fondo.jpg").convert("RGB")
    paleta, acento = tr.color_de_acento(cfg, fondo, e.get("paleta"))
    e["paleta_usada"], e["acento"] = paleta, acento
    retrato = tr.cargar_retrato(cfg)
    for i, o in enumerate(e["opciones"]):
        if indices is not None and i not in indices:
            continue
        img = tr.componer(fondo, o["texto"], cfg, retrato, acento)
        o["archivo"] = f"opcion_{i + 1}.jpg"
        tr.guardar_jpg(img, carpeta(c) / o["archivo"])
    if e.get("elegida") is not None and e["elegida"] < len(e["opciones"]):
        _copiar_elegida(c, e)


def _copiar_elegida(c: CarpetaProyecto, e: dict) -> None:
    origen = carpeta(c) / e["opciones"][e["elegida"]]["archivo"]
    shutil.copy(origen, carpeta(c) / "miniatura.jpg")
    try:                                   # una copia junto a los videos, lista para subir
        from ..pipeline import carpeta_videos, slugificar

        shutil.copy(origen, carpeta_videos() / f"{slugificar(c.cargar().titulo)[:60]}_miniatura.jpg")
    except OSError:
        pass


def _producir(c: CarpetaProyecto, t, permiso: bool = False, ejecutar=None, proveedor=None) -> Path:
    """Claude propone una opción por fórmula → fondo nuevo para este video → una miniatura por opción."""
    cfg = _config(c)
    e = _estado(c)
    t.avisar("Claude está escribiendo las opciones de texto…")
    t.progreso = 0.1
    duracion = tr.duracion_texto(duracion_video(c))
    e["opciones"] = tr.planificar(c.cargar().titulo, duracion, ejecutar=ejecutar, cwd=c.ruta, avisar=t.avisar)
    e["duracion"] = duracion
    e["elegida"] = None
    t.progreso = 0.5
    if not (carpeta(c) / "fondo.jpg").exists():
        _nuevo_fondo(c, cfg, e, t, permiso=permiso, proveedor=proveedor)
    t.avisar("Armando las miniaturas…")
    _render(c, cfg, e)
    _guardar(c, e)
    t.progreso = 1.0
    t.avisar(f"{len(e['opciones'])} opciones listas: elige una")
    return carpeta(c)


def editar(c: CarpetaProyecto, indice: int, texto: str) -> dict:
    """Texto escrito a mano: se vuelve a armar SOLO esa opción con el mismo fondo (gratis)."""
    e = _estado(c)
    if not 0 <= indice < len(e["opciones"]):
        raise IndexError("esa opción no existe")
    lineas = tr.parsear(texto)                     # error de formato → se avisa y no se arma
    limpio = tr.formatear(lineas)
    e["opciones"][indice].update(texto=limpio, avisos=tr.revisar(limpio, c.cargar().titulo), editada=True)
    _render(c, _config(c), e, [indice])
    _guardar(c, e)
    return e


def agregar(c: CarpetaProyecto, texto: str) -> dict:
    """Una opción más escrita a mano (con el mismo fondo)."""
    e = _estado(c)
    if not (carpeta(c) / "fondo.jpg").exists():
        raise ValueError("primero produce la miniatura (así queda el fondo de este video)")
    limpio = tr.formatear(tr.parsear(texto))
    e["opciones"].append({"formula": None, "texto": limpio, "avisos": tr.revisar(limpio, c.cargar().titulo),
                          "editada": True})
    _render(c, _config(c), e, [len(e["opciones"]) - 1])
    _guardar(c, e)
    return e


def elegir(c: CarpetaProyecto, indice: int) -> dict:
    e = _estado(c)
    if not 0 <= indice < len(e["opciones"]):
        raise IndexError("esa opción no existe")
    e["elegida"] = indice
    _copiar_elegida(c, e)
    _guardar(c, e)
    return e


def paleta(c: CarpetaProyecto, valor: str) -> dict:
    """Forzar la paleta de este video («fria», «calida») o volver a la automática («auto»)."""
    if valor not in ("auto", "fria", "calida"):
        raise ValueError("la paleta es auto, fria o calida")
    e = _estado(c)
    e["paleta"] = valor
    if (carpeta(c) / "fondo.jpg").exists():
        _render(c, _config(c), e)
    _guardar(c, e)
    return e


def _otro_fondo(c: CarpetaProyecto, t, generar: bool = False, permiso: bool = False, proveedor=None) -> Path:
    cfg = _config(c)
    e = _estado(c)
    _nuevo_fondo(c, cfg, e, t, permiso=permiso, generar=generar, proveedor=proveedor)
    _render(c, cfg, e)
    _guardar(c, e)
    t.avisar("Fondo cambiado")
    return carpeta(c)


def estado(c: CarpetaProyecto) -> dict:
    cfg = _config(c)
    e = _estado(c)
    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    gastado = sum(x.get("costo_cop", 0) for x in libro.entradas() if x.get("modulo") == "miniatura")
    from .generar import costo_por_imagen

    return {"layout": tr.LAYOUT, "carpeta": CARPETA, **e,
            "fondo": f"{CARPETA}/fondo.jpg" if (carpeta(c) / "fondo.jpg").exists() else None,
            "miniatura": f"{CARPETA}/miniatura.jpg" if (carpeta(c) / "miniatura.jpg").exists() else None,
            "config": cfg.model_dump(), "tiene_retrato": tr.cargar_retrato(cfg) is not None,
            "fondos_canal": tr.fondos_disponibles(cfg), "gastado": formato_cop(gastado),
            "precio_fondo_usd": round(costo_por_imagen(), 3), "version": int(time.time())}


# ------------------------------------------------------------------ con cobro en créditos

def producir(c: CarpetaProyecto, t, *args, **kw) -> Path:
    from ..plataforma import cobro

    with cobro.accion(c.ruta, "miniatura"):
        return _producir(c, t, *args, **kw)


def otro_fondo(c: CarpetaProyecto, t, generar: bool = False, *args, **kw) -> Path:
    if not generar:                                # rotar es gratis
        return _otro_fondo(c, t, False, *args, **kw)
    from ..plataforma import cobro

    with cobro.accion(c.ruta, "miniatura_variante"):
        return _otro_fondo(c, t, True, *args, **kw)
