"""Cola de la semana (16-10, pedido del dueño: «hacer los videos de la semana de un canal en un día»).

Se pegan varios guiones de Tracy o varias ideas de Peligro Tropical y Xandart los hace UNO DETRÁS DE OTRO, solo
(p. ej. de noche): así el PC nunca arma dos videos a la vez y no se traba. La cola queda guardada en disco: si se
cierra Xandart, lo que estaba haciéndose vuelve a «esperando» y sigue cuando se abre otra vez (lo pagado no se
repite: cada paso es reanudable).

- Tracy: guion pegado → voz, Whisper, plan, clips y armado (tracy.flujo.producir).
- Peligro Tropical: idea + notas → guion (Claude) → imágenes → voz y video (pipeline.paso_*), sin parar a revisar.
- El Calvo Explica: tema + datos → guion (Claude) → escenas (Claude) → voz y video (explica.flujo.producir).

Cada video puede llevar una «etiqueta» (p. ej. el canal de YouTube al que va) para organizarse.
"""
from __future__ import annotations

import contextvars
import threading
import time
import uuid
from pathlib import Path

from .config import escribir_json, leer_json

TIPOS = ("tracy", "peligro", "explica")
_CERROJO = threading.Lock()
_HILO: dict = {"hilo": None}


def _archivo() -> Path:
    from .plataforma.db import carpeta_datos

    return carpeta_datos() / "cola.json"


def leer() -> list[dict]:
    ruta = _archivo()
    return list(leer_json(ruta).get("videos") or []) if ruta.exists() else []


def _guardar(items: list[dict]) -> None:
    escribir_json(_archivo(), {"videos": items})


def _cambiar(id_: str, **campos) -> None:
    with _CERROJO:
        items = leer()
        for x in items:
            if x["id"] == id_:
                x.update(campos)
        _guardar(items)


def _item(tipo: str, slug: str, titulo: str, permiso: bool, etiqueta: str = "", trabajo: str | None = None) -> dict:
    return {"id": uuid.uuid4().hex[:10], "tipo": tipo, "slug": slug, "titulo": titulo, "etiqueta": etiqueta.strip(),
            "trabajo": trabajo or slug, "estado": "esperando", "permiso": bool(permiso), "creado": time.time(),
            "error": None}


def agregar_tracy(guiones: list[dict], permiso: bool, etiqueta: str = "") -> list[dict]:
    """guiones: [{titulo, guion}]. Cada uno queda creado como video (se ve en Mis videos) y en la cola."""
    from .tracy.flujo import crear_proyecto
    from .tracy.preset import CLAVE_CANAL, crear_canal_tracy

    crear_canal_tracy()
    nuevos = []
    for g in guiones:
        texto = (g.get("guion") or "").strip()
        if len(texto) < 40:
            continue
        c = crear_proyecto(texto, canal=CLAVE_CANAL, titulo=(g.get("titulo") or "").strip() or None)
        nuevos.append(_item("tracy", c.ruta.name, c.cargar().titulo, permiso, g.get("etiqueta") or etiqueta))
    return _encolar(nuevos)


def agregar_peligro(ideas: list[dict], permiso: bool, canal: str | None = None, minutos: float = 9,
                    etiqueta: str = "") -> list[dict]:
    """ideas: [{tema, notas?, giro?, villano?, minutos?}]."""
    from . import pipeline

    nuevos = []
    for i in ideas:
        tema = (i.get("tema") or "").strip()
        if len(tema) < 3:
            continue
        c = pipeline.crear_video(tema, (i.get("giro") or "").strip(), (i.get("villano") or "").strip(),
                                 float(i.get("minutos") or minutos), (i.get("notas") or "").strip(), canal=canal or None)
        nuevos.append(_item("peligro", c.ruta.name, tema, permiso, etiqueta or "Peligro Tropical"))
    return _encolar(nuevos)


def agregar_explica(ideas: list[dict], permiso: bool, temas: int = 9, etiqueta: str = "") -> list[dict]:
    """ideas: [{tema, notas?}] (las notas van como datos para el guion)."""
    from .explica.api import crear_carpeta

    nuevos = []
    for i in ideas:
        tema = (i.get("tema") or "").strip()
        if len(tema) < 4:
            continue
        slug, _ = crear_carpeta(tema, int(i.get("temas") or temas), (i.get("notas") or "").strip())
        nuevos.append(_item("explica", slug, tema, permiso, etiqueta or "El Calvo Explica", trabajo=f"explica-{slug}"))
    return _encolar(nuevos)


def _encolar(nuevos: list[dict]) -> list[dict]:
    if not nuevos:
        raise ValueError("No había nada para agregar (revisa que cada guion o idea tenga texto)")
    with _CERROJO:
        _guardar(leer() + nuevos)
    arrancar()
    return nuevos


def quitar(id_: str) -> None:
    """Saca un video que todavía espera (el que se está haciendo no se puede quitar)."""
    with _CERROJO:
        items = leer()
        x = next((x for x in items if x["id"] == id_), None)
        if x is None:
            raise KeyError(id_)
        if x["estado"] == "haciendo":
            raise ValueError("Ese video se está haciendo ahora: espera a que termine")
        _guardar([y for y in items if y["id"] != id_])


def reintentar(id_: str, permiso: bool = False) -> None:
    """Vuelve a la cola (con `permiso`, el video puede pasar el máximo de gasto que lo frenó)."""
    with _CERROJO:
        items = leer()
        for x in items:
            if x["id"] == id_ and x["estado"] != "haciendo":
                x.update(estado="esperando", error=None, permiso=bool(x.get("permiso") or permiso))
        _guardar(items)
    arrancar()


def limpiar_terminados() -> None:
    with _CERROJO:
        _guardar([x for x in leer() if x["estado"] not in ("listo",)])


def recuperar() -> None:
    """Al abrir Xandart: lo que quedó «haciendo» (se cerró a mitad) vuelve a esperar, y la cola sigue."""
    with _CERROJO:
        items = leer()
        for x in items:
            if x["estado"] == "haciendo":
                x["estado"] = "esperando"
        _guardar(items)
    if any(x["estado"] == "esperando" for x in leer()):
        arrancar()


def arrancar() -> None:
    """Prende el trabajador de la cola si no está prendido (uno solo: un video a la vez)."""
    with _CERROJO:
        h = _HILO["hilo"]
        if h is not None and h.is_alive():
            return
        ctx = contextvars.copy_context()           # el mismo espacio de trabajo de quien lo pidió
        h = threading.Thread(target=ctx.run, args=(_trabajar,), daemon=True, name="cola")
        _HILO["hilo"] = h
        h.start()


def _funcion(x: dict):
    from . import pipeline
    from .proyecto import CarpetaProyecto

    if x["tipo"] == "explica":
        import json

        from .calma.flujo import Carpeta
        from .explica import autor
        from .explica import flujo as F

        ce = F.carpeta_base() / "videos" / x["slug"]
        meta = json.loads((ce / "video.json").read_text(encoding="utf-8"))

        def explica(t):
            if not (ce / "guion.txt").exists():
                autor.escribir_guion(ce, meta["titulo"], int(meta.get("temas", 9)), meta.get("datos", ""), avisar=t.avisar)
            if not (ce / "escenas.json").exists():
                autor.armar_escenas(ce, avisar=t.avisar)
            F.producir(Carpeta(ce), t, permiso=x["permiso"])

        return "explica", explica
    c = CarpetaProyecto.abrir(x["slug"])
    if x["tipo"] == "tracy":
        from .tracy.flujo import producir

        return "tracy", lambda t: producir(c, t, permiso=x["permiso"])

    def todo(t):
        estados = {k: v.estado for k, v in c.cargar().pasos.items()}
        if estados.get("guionista") != "completo":
            pipeline.paso_guion(c, t)
        pipeline.paso_imagenes(c, t, permiso=x["permiso"])
        pipeline.paso_video(c, t, permiso=x["permiso"])

    return "video", todo


def _trabajar() -> None:
    from . import pipeline

    while True:
        with _CERROJO:
            x = next((y for y in leer() if y["estado"] == "esperando"), None)
        if x is None:
            return
        _cambiar(x["id"], estado="haciendo", error=None, inicio=time.time())
        try:
            paso, f = _funcion(x)
            t = pipeline.lanzar(x.get("trabajo") or x["slug"], paso, f)
        except Exception as ex:  # noqa: BLE001 — p. ej. ya había un trabajo en ese video
            _cambiar(x["id"], estado="error", error=str(ex)[:300])
            continue
        while t.activo:
            time.sleep(2)
        if t.error:
            _cambiar(x["id"], estado="error", error=t.error[:300], fin=time.time())
        else:
            _cambiar(x["id"], estado="listo", fin=time.time())


def estado() -> dict:
    """La cola con el avance del que se está haciendo."""
    from . import pipeline

    items = leer()
    for x in items:
        t = pipeline.TRABAJOS.get(x.get("trabajo") or x["slug"])
        if x["estado"] == "haciendo" and t is not None:
            x["progreso"] = round(t.progreso, 3)
            x["mensaje"] = t.error or t.mensaje
    h = _HILO["hilo"]
    return {"videos": items, "trabajando": bool(h is not None and h.is_alive()),
            "esperando": sum(1 for x in items if x["estado"] == "esperando")}
