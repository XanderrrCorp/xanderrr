"""Orquestación de un video de punta a punta, con trabajos en segundo plano.

Pasos que ve el dueño en la página:
    guion    → Claude (suscripción) escribe el guion y las escenas
    imagenes → imágenes, sujetos de la tira, tira armada y villano ubicado
    video    → voz, edición (edl.json) y render del MP4 a calidad completa

Cada paso deja su resultado en disco y se puede repetir: lo ya pagado no se
vuelve a pagar (huellas por imagen y por oración de voz).
"""
from __future__ import annotations

import shutil
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .config import RAIZ, ConfigCostos, formato_cop, leer_config, leer_json
from .estilos import cargar_estilo
from .proyecto import CarpetaProyecto, slugificar

ESTILO_POR_DEFECTO = "enciclopedia_mascota"


@dataclass
class Trabajo:
    paso: str
    mensaje: str = "empezando…"
    progreso: float = 0.0
    activo: bool = True
    error: str | None = None
    inicio: float = field(default_factory=time.time)
    registro: list[str] = field(default_factory=list)

    def avisar(self, texto: str) -> None:
        self.mensaje = texto.strip()
        self.registro = (self.registro + [self.mensaje])[-60:]


TRABAJOS: dict[str, Trabajo] = {}
_CERROJO = threading.Lock()


def ocupado(slug: str) -> bool:
    t = TRABAJOS.get(slug)
    return bool(t and t.activo)


def lanzar(slug: str, paso: str, funcion) -> Trabajo:
    with _CERROJO:
        if ocupado(slug):
            raise RuntimeError("Ya hay un trabajo en marcha para este video")
        t = Trabajo(paso)
        TRABAJOS[slug] = t

    def correr():
        try:
            funcion(t)
            t.progreso = 1.0
            t.avisar("listo")
        except Exception as ex:  # noqa: BLE001 — se muestra en la página
            t.error = str(ex) or ex.__class__.__name__
            t.avisar(f"error: {t.error}")
            t.registro.append(traceback.format_exc()[-1500:])
        finally:
            t.activo = False

    threading.Thread(target=correr, daemon=True).start()
    return t


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def carpeta_videos() -> Path:
    base = Path.home() / "Videos"
    destino = (base if base.exists() else Path.home()) / "Xandart"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


# ------------------------------------------------------------------ pasos

def crear_video(tema: str, giro: str, villano: str, minutos: float, notas: str = "",
                canal: str = "animales-peligrosos", estilo_id: str = ESTILO_POR_DEFECTO) -> CarpetaProyecto:
    base = slugificar(tema)[:40] or "video"
    slug, n = base, 2
    from .config import ruta_proyectos

    while (ruta_proyectos() / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    c = CarpetaProyecto.crear(tema, canal, estilo_id, minutos * 60, slug=slug)
    p = c.cargar()
    p.notas = [f"giro: {giro}", f"villano: {villano}", f"notas: {notas}"]
    c.guardar(p)
    _copiar_mascota(c, estilo_id)
    return c


def _copiar_mascota(c: CarpetaProyecto, estilo_id: str) -> None:
    # el personaje del canal se reutiliza (5.3): no se vuelve a pagar
    mascota = RAIZ / "estilos" / estilo_id / "assets" / "mascota_base.png"
    if mascota.exists():
        (c.ruta / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copy(mascota, c.ruta / "assets" / "mascota_base.png")


def importar_guion(v1: dict | list, canal: str = "animales-peligrosos",
                   estilo_id: str = ESTILO_POR_DEFECTO) -> tuple[CarpetaProyecto, list[str]]:
    """Trae un escenas.json hecho antes (formato v1) como un video listo para imágenes."""
    from .config import ruta_proyectos
    from .importar_v1 import convertir, duracion_escenas

    estilo = cargar_estilo(estilo_id)
    res = convertir(v1, estilo, canal=canal)
    if res.errores or res.escenas is None:
        raise ValueError("No se pudo leer ese guion: " + "; ".join(res.errores[:3]))
    esc = res.escenas
    config = ConfigCostos.cargar()
    dur, _ = duracion_escenas(esc, config.consumo["caracteres_por_segundo_narracion"])
    base = slugificar(esc.video)[:40] or "video"
    slug, n = base, 2
    while (ruta_proyectos() / slug).exists():
        slug, n = f"{base}-{n}", n + 1
    c = CarpetaProyecto.crear(esc.video, esc.canal, estilo.id, dur, slug=slug)
    c.guardar_escenas(esc)
    _copiar_mascota(c, estilo.id)
    c.marcar("guionista", "completo", ["escenas.json"])
    avisos = list(res.avisos) + [f"escena {k}: efectos sin equivalente: {v}"
                                 for k, v in res.efectos_no_reconocidos.items()]
    return c, avisos


def paso_prueba(c: CarpetaProyecto, t: Trabajo, n: int = 10, permiso: bool = False) -> dict:
    """Prueba real de imágenes (Fase 1): las primeras n escenas, costo real medido
    y proyección del video completo. No arma la tira ni marca las imágenes como listas."""
    from .config import escribir_json
    from .imagenes.generador import generar_imagenes, hoja_de_contacto, proyectar

    config = ConfigCostos.cargar()
    antes = c.libro(config).total_cop()
    esc = c.cargar_escenas()
    objetivo = sum(1 for e in esc.escenas[:n] if e.visual.accion == "generar")
    hechas = [0]

    def avisar(txt):
        if ": lista" in txt:
            hechas[0] += 1
            t.progreso = min(0.95, hechas[0] / max(1, objetivo))
        t.avisar(txt)

    r = generar_imagenes(c, primeras=n, permiso=permiso, avisar=avisar, config=config)
    if r.frenado:
        raise RuntimeError(r.frenado)
    claves = [k for k in r.generadas + r.ya_estaban if k.startswith("escena:")]
    hoja = hoja_de_contacto(c, claves, c.ruta / "render" / "hoja_prueba.png")
    pr = proyectar(c, config)
    medio = (sum(r.costos_por_imagen.values()) / len(r.costos_por_imagen)) if r.costos_por_imagen else None
    datos = {"escenas": n, "generadas": len(r.generadas), "ya_estaban": len(r.ya_estaban),
             "fallidas": r.fallidas, "llamadas": r.llamadas, "proveedor": r.proveedor, "modelo": r.modelo,
             "costo_corrida": formato_cop(c.libro(config).total_cop() - antes),
             "costo_medio_imagen": formato_cop(config.a_cop(medio)) if medio is not None else None,
             "proyeccion": ({"imagenes": pr.imagenes_video, "texto": formato_cop(pr.total_cop), "base": pr.base}
                            if pr else None),
             "hoja": "render/hoja_prueba.png" if hoja else None, "avisos": r.avisos[:5]}
    escribir_json(c.ruta / "render" / "prueba.json", datos)
    if r.fallidas:
        raise RuntimeError(f"{len(r.fallidas)} imágenes fallaron: " + "; ".join(f"{k}: {v}" for k, v in list(r.fallidas.items())[:3]))
    return datos


def paso_guion(c: CarpetaProyecto, t: Trabajo, ejecutar=None) -> None:
    from . import claude_cli
    from .guionista import Encargo, escribir_guion

    p = c.cargar()
    notas = {x.split(":", 1)[0]: x.split(":", 1)[1].strip() for x in p.notas if ":" in x}
    encargo = Encargo(p.titulo, notas.get("giro", ""), notas.get("villano", ""),
                      p.duracion_objetivo_seg / 60, notas.get("notas", ""))
    t.avisar("Claude está escribiendo el guion (unos minutos)…")
    t.progreso = 0.1
    c.marcar("guionista", "en_curso")
    r = escribir_guion(encargo, cargar_estilo(p.estilo), c.ruta, p.canal,
                       ejecutar=ejecutar or claude_cli.ejecutar, avisar=t.avisar)
    esc = c.cargar_escenas()
    p = c.cargar()
    p.titulo = esc.video
    c.guardar(p)
    c.marcar("guionista", "completo", ["escenas.json", "guion.md", "direccion.json"])
    t.avisar(f"Guion listo: {r['escenas']} escenas, {r['palabras']} palabras")


def estimar_imagenes(c: CarpetaProyecto) -> dict:
    from .imagenes.generador import total_a_generar

    config = ConfigCostos.cargar()
    ajustes = leer_config("proveedores.json")["imagenes"]
    op = ajustes["opciones"][ajustes["proveedor"]]
    precio = (config.precios["imagenes_por_modelo"].get(op["modelo"]) or {}).get("precio_por_imagen", 0.04)
    esc = c.cargar_escenas()
    hechas = 0
    man = c.ruta / "imagenes" / "manifiesto.json"
    if man.exists():
        hechas = sum(1 for v in leer_json(man).values() if v.get("proveedor") != "existente")
    total = total_a_generar(esc) - (1 if (c.ruta / "assets" / "mascota_base.png").exists() else 0)
    faltan = max(0, total - hechas)
    ya = set(leer_json(man)) if man.exists() else set()
    prueba = sum(1 for e in esc.escenas[:10] if e.visual.accion == "generar" and f"escena:{e.id}" not in ya)
    return {"total": total, "faltan": faltan, "cop": round(config.a_cop(faltan * precio)),
            "texto": formato_cop(config.a_cop(faltan * precio)),
            "prueba": prueba, "prueba_texto": formato_cop(config.a_cop(prueba * precio)),
            "maximo_texto": formato_cop(config.maximo_cop),
            "pasa_maximo": config.a_cop(faltan * precio) + c.libro(config).total_cop() > config.maximo_cop}


def paso_imagenes(c: CarpetaProyecto, t: Trabajo, permiso: bool = False, ejecutar_claude=None) -> None:
    from .guionista import ubicar_villano
    from .imagenes.generador import generar_imagenes
    from .tira import armar_tira

    esc = c.cargar_escenas()
    total = sum(1 for e in esc.escenas if e.visual.accion == "generar") + len(esc.assets)
    hechas = [0]

    def avisar(txt):
        if ": lista" in txt:
            hechas[0] += 1
            t.progreso = min(0.9, 0.9 * hechas[0] / max(1, total))
        t.avisar(txt)

    c.marcar("assets", "en_curso")
    r = generar_imagenes(c, permiso=permiso, avisar=avisar)
    if r.frenado:
        raise RuntimeError(r.frenado)
    if esc.niveles:
        r2 = generar_imagenes(c, solo_assets=[n.asset for n in esc.niveles], permiso=permiso, avisar=avisar)
        if r2.frenado:
            raise RuntimeError(r2.frenado)
        t.avisar("Armando la tira de niveles…")
        p = c.cargar()
        armar_tira(c.cargar_escenas(), cargar_estilo(p.estilo), c.ruta, seed=p.semilla)
    fallidas = {**r.fallidas}
    if fallidas:
        raise RuntimeError(f"{len(fallidas)} imágenes fallaron: " + "; ".join(f"{k}: {v}" for k, v in list(fallidas.items())[:3]))
    if (c.ruta / "direccion.json").exists() and leer_json(c.ruta / "direccion.json").get("pixelar_pendiente"):
        t.avisar("Claude está ubicando al villano para pixelarlo antes de su revelación…")
        from . import claude_cli

        ubicar_villano(c.ruta, ejecutar=ejecutar_claude or claude_cli.ejecutar)
    c.marcar("assets", "completo", ["imagenes/", "assets/tira/"])


def regenerar_imagen(c: CarpetaProyecto, t: Trabajo, escena_id: int, instruccion: str) -> None:
    from .imagenes.generador import generar_imagenes

    esc = c.cargar_escenas()
    e = next(x for x in esc.escenas if x.id == escena_id)
    if e.visual.accion != "generar":
        raise RuntimeError("Esa escena reutiliza otra imagen: regenera la original")
    if instruccion.strip():
        e.visual.prompt = f"{e.visual.prompt}. {instruccion.strip()}"
        c.guardar_escenas(esc)
    else:
        # misma descripción: se fuerza una imagen nueva quitándola del manifiesto
        man = c.ruta / "imagenes" / "manifiesto.json"
        datos = leer_json(man)
        datos.pop(f"escena:{escena_id}", None)
        from .config import escribir_json

        escribir_json(man, datos)
    t.avisar(f"Regenerando la escena {escena_id}…")
    r = generar_imagenes(c, ids=[escena_id], avisar=t.avisar)
    if r.fallidas or r.frenado:
        raise RuntimeError(r.frenado or next(iter(r.fallidas.values())))


def paso_video(c: CarpetaProyecto, t: Trabajo, permiso: bool = False) -> Path:
    from .edicion import construir_edl, validar
    from .render import renderizar
    from .voz import generar_voz

    c.marcar("voz", "en_curso")
    t.avisar("Grabando la voz…")
    t.progreso = 0.05
    generar_voz(c, ffmpeg(), permiso=permiso, avisar=t.avisar)
    c.marcar("voz", "completo", ["audio/voz.wav"])
    t.progreso = 0.2
    t.avisar("Editando: cortes, movimientos, textos y subtítulos…")
    edl = construir_edl(c)
    avisos = validar(edl)
    if avisos:
        t.avisar("validador: " + "; ".join(avisos[:3]))
    c.marcar("director_edicion", "completo", ["edl.json"])
    total = edl["duracion_total"]

    def avisar(txt):
        t.avisar(txt)
        if "render" in txt and "/" in txt:
            try:
                hecho = float(txt.split("render")[1].split("/")[0])
                t.progreso = 0.25 + 0.7 * hecho * 60 / total
            except ValueError:
                pass

    t.avisar("Renderizando el video en 1080p…")
    final = renderizar(c, ffmpeg(), c.ruta / "render" / "final.mp4", avisar=avisar)
    destino = carpeta_videos() / f"{slugificar(c.cargar().titulo)[:60]}.mp4"
    shutil.copy(final, destino)
    shutil.copy(final.with_suffix(".srt"), destino.with_suffix(".srt"))
    c.marcar("export_final", "completo", [str(destino)])
    t.avisar(f"Video listo: {destino}")
    return destino


def resumen(c: CarpetaProyecto) -> dict:
    """Todo lo que la página necesita para pintar un video."""
    p = c.cargar()
    config = ConfigCostos.cargar()
    datos = {"slug": c.ruta.name, "titulo": p.titulo, "minutos": round(p.duracion_objetivo_seg / 60, 1),
             "pasos": {k: v.estado for k, v in p.pasos.items()},
             "costo": formato_cop(c.libro(config).total_cop()), "escenas": [], "guion": None,
             "video": None, "trabajo": None, "prueba": None}
    if c.archivo_escenas.exists():
        esc = c.cargar_escenas()
        man = leer_json(c.ruta / "imagenes" / "manifiesto.json") if (c.ruta / "imagenes" / "manifiesto.json").exists() else {}
        archivos = {e.id: e.visual.archivo for e in esc.escenas}
        for e in esc.escenas:
            img = None
            if e.visual.accion == "generar" and f"escena:{e.id}" in man:
                img = man[f"escena:{e.id}"]["archivo"]
            elif e.visual.accion == "reusar" and isinstance(e.visual.reusar_de, int):
                ref = man.get(f"escena:{e.visual.reusar_de}")
                img = ref["archivo"] if ref else None
            elif e.visual.accion == "reusar" and isinstance(e.visual.reusar_de, str):
                n = next((x for x in esc.niveles if x.asset == e.visual.reusar_de), None)
                img = f"assets/tira/tarjeta_{n.numero}{'_pixelada' if n and n.villano else ''}.png" if n else None
            datos["escenas"].append({"id": e.id, "seccion": e.seccion, "narracion": e.narracion,
                                     "accion": e.visual.accion, "imagen": img,
                                     "puede_regenerar": e.visual.accion == "generar",
                                     "medico": "dato_medico" in e.revision_humana})
        datos["estimacion_imagenes"] = estimar_imagenes(c)
        if (c.ruta / "guion.md").exists():
            datos["guion"] = (c.ruta / "guion.md").read_text(encoding="utf-8")
    if (c.ruta / "render" / "prueba.json").exists():
        datos["prueba"] = leer_json(c.ruta / "render" / "prueba.json")
    if (c.ruta / "render" / "final.mp4").exists():
        datos["video"] = "render/final.mp4"
    t = TRABAJOS.get(c.ruta.name)
    if t:
        datos["trabajo"] = {"paso": t.paso, "mensaje": t.mensaje, "progreso": round(t.progreso, 3),
                            "activo": t.activo, "error": t.error, "segundos": int(time.time() - t.inicio)}
    return datos
