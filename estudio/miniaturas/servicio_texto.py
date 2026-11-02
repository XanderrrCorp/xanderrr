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


def canal_de_miniatura(c: CarpetaProyecto, e: dict | None = None) -> str:
    """La plantilla que usa este video: la elegida en su página (p. ej. Tracy → «Código del Éxito Mujeres»)
    o, si no eligió ninguna, la de su canal."""
    elegido = (e if e is not None else _estado(c)).get("canal_miniatura")
    return elegido if elegido and tr.es_de_texto(elegido) else c.cargar().canal


def _config(c: CarpetaProyecto, e: dict | None = None) -> tr.ConfigTexto:
    return tr.cargar_config(canal_de_miniatura(c, e))


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


def guion_del_video(c: CarpetaProyecto) -> str:
    """Lo que dice la voz: el guion pegado (Tracy) o el escrito por Xandart."""
    for nombre in ("guion.txt", "guion.md"):
        ruta = c.ruta / nombre
        if ruta.exists():
            return ruta.read_text(encoding="utf-8")
    if c.archivo_escenas.exists():
        return " ".join(e.narracion for e in c.cargar_escenas().escenas)
    return ""


def titulo_real(c: CarpetaProyecto) -> str:
    """El título del video; vacío si salió solo de la primera frase del guion (Tracy sin título):
    así no se prohíben las palabras del tema."""
    titulo = c.cargar().titulo
    guion = " ".join(guion_del_video(c).split())
    return "" if guion and guion.startswith(" ".join(titulo.split())[:60]) else titulo


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
    elif cfg.modo_foto == "foto_completa":
        elegido = tr.siguiente_foto(cfg, evitar=e.get("fondo_origen"))
        tr._cubrir(Image.open(elegido).convert("RGB"), tr.W, tr.H).save(destino, quality=93)
        e["fondo_origen"] = elegido.name
    else:
        elegido = tr.siguiente_fondo(cfg, evitar=e.get("fondo_origen"))
        tr._cubrir(Image.open(elegido).convert("RGB"), tr.W, tr.H).save(destino, quality=92)
        e["fondo_origen"] = elegido.name


def _render(c: CarpetaProyecto, cfg: tr.ConfigTexto, e: dict, indices: list[int] | None = None) -> None:
    fondo = Image.open(carpeta(c) / "fondo.jpg").convert("RGB")
    paleta, acento = tr.color_de_acento(cfg, fondo, e.get("paleta"))
    e["paleta_usada"], e["acento"] = paleta, acento
    retrato = tr.cargar_retrato(cfg) if cfg.modo_foto == "retrato" else None
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
    e = _estado(c)
    cfg = _config(c, e)
    t.avisar("Claude está escribiendo las opciones de texto…")
    t.progreso = 0.1
    duracion = tr.duracion_texto(duracion_video(c))
    e["opciones"] = tr.planificar(titulo_real(c), duracion, ejecutar=ejecutar, cwd=c.ruta, avisar=t.avisar,
                                  guion=guion_del_video(c))
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
    e["opciones"][indice].update(texto=limpio, avisos=tr.revisar(limpio, titulo_real(c)), editada=True)
    _render(c, _config(c, e), e, [indice])
    _guardar(c, e)
    return e


def agregar(c: CarpetaProyecto, texto: str) -> dict:
    """Una opción más escrita a mano (con el mismo fondo)."""
    e = _estado(c)
    if not (carpeta(c) / "fondo.jpg").exists():
        raise ValueError("primero produce la miniatura (así queda el fondo de este video)")
    limpio = tr.formatear(tr.parsear(texto))
    e["opciones"].append({"formula": None, "texto": limpio, "avisos": tr.revisar(limpio, titulo_real(c)),
                          "editada": True})
    _render(c, _config(c, e), e, [len(e["opciones"]) - 1])
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
        _render(c, _config(c, e), e)
    _guardar(c, e)
    return e


def _otro_fondo(c: CarpetaProyecto, t, generar: bool = False, permiso: bool = False, proveedor=None) -> Path:
    e = _estado(c)
    cfg = _config(c, e)
    _nuevo_fondo(c, cfg, e, t, permiso=permiso, generar=generar, proveedor=proveedor)
    _render(c, cfg, e)
    _guardar(c, e)
    t.avisar("Fondo cambiado")
    return carpeta(c)


def estado(c: CarpetaProyecto) -> dict:
    e = _estado(c)
    cfg = _config(c, e)
    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    gastado = sum(x.get("costo_cop", 0) for x in libro.entradas() if x.get("modulo") == "miniatura")
    from .generar import costo_por_imagen

    return {"layout": tr.LAYOUT, "carpeta": CARPETA, **e,
            "fondo": f"{CARPETA}/fondo.jpg" if (carpeta(c) / "fondo.jpg").exists() else None,
            "miniatura": f"{CARPETA}/miniatura.jpg" if (carpeta(c) / "miniatura.jpg").exists() else None,
            "config": cfg.model_dump(), "canal_miniatura": cfg.canal, "plantillas": plantillas_de_texto(),
            "tiene_retrato": (tr.cargar_retrato(cfg) is not None if cfg.modo_foto == "retrato"
                              else bool(tr.fotos_disponibles(cfg))),
            "fondos_canal": tr.fondos_disponibles(cfg), "gastado": formato_cop(gastado),
            "precio_fondo_usd": round(costo_por_imagen(), 3), "version": int(time.time())}


def plantillas_de_texto() -> list[dict]:
    """Las plantillas de texto que se pueden elegir para un video (las de los canales con esta plantilla)."""
    import os

    from ..plataforma import almacen, contexto
    from .plantilla import carpeta_canales

    carpetas = []
    esp = contexto.espacio_actual()
    if esp and not os.environ.get("XANDART_CANALES"):
        carpetas.append(almacen.raiz_espacio(esp) / "plantillas_miniatura")
    carpetas.append(carpeta_canales())
    vistos, salida = set(), []
    for base in carpetas:
        for d in sorted(base.glob("*")) if base.exists() else []:
            clave = d.name
            if clave in vistos:
                continue
            try:
                if tr.es_de_texto(clave):
                    vistos.add(clave)
                    salida.append({"canal": clave, "nombre": tr.cargar_config(clave).nombre})
            except Exception:  # noqa: BLE001 — una carpeta rara no impide ver las demás
                continue
    return salida


def usar_plantilla(c: CarpetaProyecto, canal: str) -> dict:
    """Cambia la plantilla de ESTE video (p. ej. a la del canal de mujeres). La foto/fondo se vuelve a
    elegir de la nueva plantilla y las opciones ya escritas se rearman con ella (gratis)."""
    if not tr.es_de_texto(canal):
        raise ValueError("esa plantilla no existe")
    e = _estado(c)
    e["canal_miniatura"] = canal
    e.pop("fondo_origen", None)
    cfg = _config(c, e)
    if e.get("opciones"):
        _nuevo_fondo(c, cfg, e)
        _render(c, cfg, e)
    else:
        (carpeta(c) / "fondo.jpg").unlink(missing_ok=True)
    _guardar(c, e)
    return e


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
