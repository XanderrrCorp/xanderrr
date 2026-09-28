"""Orquestación de un video de punta a punta, con trabajos en segundo plano.

Pasos que ve el dueño en la página:
    guion    → Claude (suscripción) escribe el guion y las escenas
    imagenes → imágenes, sujetos de la tira, tira armada y villano ubicado
    video    → voz, edición (edl.json) y render del MP4 a calidad completa

Cada paso deja su resultado en disco y se puede repetir: lo ya pagado no se
vuelve a pagar (huellas por imagen y por oración de voz).
"""
from __future__ import annotations

import math
import os

import shutil
import subprocess
import contextvars
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .config import RAIZ, ConfigCostos, formato_cop, leer_config, leer_json, escribir_json
from .estilos import cargar_estilo, carpeta_estilo
from .proyecto import CarpetaProyecto, slugificar

# solo para una instalación sin canales registrados (la versión de un usuario)
ESTILO_POR_DEFECTO = "enciclopedia_mascota"
CANAL_POR_DEFECTO = "animales-peligrosos"


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


def _perfil(c):
    from .estilos import cargar_estilo, cargar_perfil_edicion

    return cargar_perfil_edicion(cargar_estilo(c.cargar().estilo))


def ocupado(slug: str) -> bool:
    t = TRABAJOS.get(slug)
    return bool(t and t.activo)


def despierto(activo: bool) -> None:
    """En Windows: mientras un trabajo corre, el PC no se suspende (la pantalla sí puede apagarse).
    Vale para el hilo que lo pide; al terminar se devuelve el permiso de suspender."""
    if os.name != "nt":
        return
    try:
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if activo else 0))
    except Exception:  # noqa: BLE001 — si no se puede, el trabajo sigue igual
        pass


def lanzar(slug: str, paso: str, funcion) -> Trabajo:
    with _CERROJO:
        if ocupado(slug):
            raise RuntimeError("Ya hay un trabajo en marcha para este video")
        t = Trabajo(paso)
        TRABAJOS[slug] = t

    def correr():
        despierto(True)
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
            despierto(False)

    # el trabajo corre en el mismo espacio de trabajo que la petición que lo lanzó
    contexto_actual = contextvars.copy_context()
    threading.Thread(target=contexto_actual.run, args=(correr,), daemon=True).start()
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

def _canal_y_estilo(canal: str | None, estilo_id: str | None) -> tuple[str, str]:
    """Si no se dice, el canal (y su estilo) es el primero del espacio de trabajo."""
    from .plataforma.consultas import canal_por_defecto

    por_defecto = canal_por_defecto() or (CANAL_POR_DEFECTO, ESTILO_POR_DEFECTO)
    canal = canal or por_defecto[0]
    return canal, estilo_id or (por_defecto[1] if canal == por_defecto[0] else "") or ESTILO_POR_DEFECTO


def crear_video(tema: str, giro: str, villano: str, minutos: float, notas: str = "",
                canal: str | None = None, estilo_id: str | None = None) -> CarpetaProyecto:
    canal, estilo_id = _canal_y_estilo(canal, estilo_id)
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
    from .plataforma.consultas import registrar_video

    registrar_video(slug, tema, str(c.ruta), canal, minutos)
    return c


def _copiar_mascota(c: CarpetaProyecto, estilo_id: str) -> None:
    # el personaje del canal se reutiliza (5.3): no se vuelve a pagar
    mascota = carpeta_estilo(estilo_id) / "assets" / "mascota_base.png"
    if mascota.exists():
        (c.ruta / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copy(mascota, c.ruta / "assets" / "mascota_base.png")
    from .poses import copiar_a_proyecto

    copiar_a_proyecto(estilo_id, c.ruta)     # poses del canal: gratis, ya pagadas una vez
    from .poses import copiar_presentador

    copiar_presentador(estilo_id, c.ruta)    # reacciones animadas del presentador


def importar_guion(v1: dict | list, canal: str | None = None,
                   estilo_id: str | None = None) -> tuple[CarpetaProyecto, list[str]]:
    """Trae un escenas.json hecho antes (formato v1) como un video listo para imágenes."""
    canal, estilo_id = _canal_y_estilo(canal, estilo_id)
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
    from .plataforma.consultas import registrar_video

    registrar_video(slug, esc.video, str(c.ruta), esc.canal, round(dur / 60, 1),
                    formato=esc.relacion_aspecto, estado="en_proceso")
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


# escenas que pueden repetir una imagen cercana sin que se note (primero las más «de relleno»)
REUSABLES = ("explicacion", "transicion_de_seccion", "comparacion", "consejo_practico", "alivio",
             "pregunta_al_espectador", "humor", "tension_creciente", "advertencia", "dato_impactante", "amenaza")
PROTEGIDAS = ("gancho", "revelacion", "giro", "cierre", "llamado_accion")
MARGEN_COP = 1200            # voz y miniatura también cuentan dentro del máximo


USOS_POR_TOMA = 2


def usar_pexels_en_escenas(c: CarpetaProyecto, t=None, ejecutar_claude=None) -> int:
    """Antes de generar: las escenas que solo muestran al animal y lo nombran usan una foto o un
    video REAL verificado de Pexels (gratis) en vez de una imagen nueva. Cada toma se usa como
    mucho 2 veces y nunca en escenas seguidas; el villano oculto no se muestra antes de tiempo."""
    from . import claude_cli
    from .esquemas import EscenasV2
    from .foco import claves_de_nombre, palabra_en
    from .stock import SinClavePexels, preparar_stock

    avisar = t.avisar if t else print
    try:
        indice = preparar_stock(c.ruta, ejecutar=ejecutar_claude or claude_cli.ejecutar, avisar=avisar,
                                recrear_faltantes=False)
    except SinClavePexels as ex:
        avisar(f"⚠ Sin fotos reales de Pexels: {ex}. Se ajusta solo reusando imágenes.")
        return 0
    tomas = [a for a in indice["archivos"] if a.get("verificado") and not a.get("sintetica")
             and (c.ruta / a["archivo"]).exists()]
    if not tomas:
        return 0
    esc = c.cargar_escenas()
    direccion = leer_json(c.ruta / "direccion.json") if (c.ruta / "direccion.json").exists() else {}
    revelacion = int(direccion.get("villano_revelacion", 0)) or None
    villano = next((n.numero for n in esc.niveles if n.villano), None)
    ocultas = set(direccion.get("pixelar_pendiente") or []) | {int(k) for k in (direccion.get("pixelar") or {})}
    man = leer_json(c.ruta / "imagenes" / "manifiesto.json") if (c.ruta / "imagenes" / "manifiesto.json").exists() else {}
    claves = claves_de_nombre([n.model_dump() for n in esc.niveles])
    solo_animal = set(cargar_estilo(c.cargar().estilo).tipos_reemplazables_por_foto_real)
    usos = {a["archivo"]: 0 for a in tomas}
    datos = esc.model_dump()
    assets = {a["id"] for a in datos["assets"]}
    videos = direccion.setdefault("video_escena", {})
    cambiadas, ultima = 0, -9
    for k, e in enumerate(datos["escenas"]):
        v = e["visual"]
        if (v["accion"] != "generar" or f"escena:{e['id']}" in man or v.get("tipo") not in solo_animal
                or e["id"] in ocultas or e["intencion"] in PROTEGIDAS or k - ultima < 2):
            continue
        nivel = next((n for n in esc.niveles if e["seccion"].lower().startswith(f"nivel {n.numero} ")
                      or n.nombre.lower() in e["seccion"].lower()), None)
        if nivel is None or nivel.numero not in claves or not palabra_en(e["narracion"], claves[nivel.numero]):
            continue
        if nivel.numero == villano and (revelacion is None or e["id"] <= revelacion):
            continue                                  # el villano va oculto hasta su revelación
        propias = sorted((a for a in tomas if a["nivel"] == nivel.numero and usos[a["archivo"]] < USOS_POR_TOMA),
                         key=lambda a: (usos[a["archivo"]], a["tipo"] != "video"))
        if not propias:
            continue
        toma = propias[0]
        usos[toma["archivo"]] += 1
        foto = toma["archivo"]
        if toma["tipo"] == "video":
            foto = _cuadro_de_video(c.ruta, toma["archivo"])
            videos[str(e["id"])] = {"archivo": toma["archivo"], "desde": round(0.5 + 1.2 * (usos[toma["archivo"]] - 1), 2),
                                    "origen": toma.get("url_origen", "")}
        aid = "pexels_" + Path(foto).stem
        if aid not in assets:
            datos["assets"].append({"id": aid, "tipo": "foto_pexels", "archivo": foto, "quitar_fondo": False,
                                    "prompt": f"Pexels: {toma.get('url_origen', '')}"})
            assets.add(aid)
        e["visual"] = {**v, "accion": "reusar", "reusar_de": aid, "prompt": None, "tipo": None, "referencias": []}
        e["notas_edicion"] = ((e.get("notas_edicion") or "") + f" · {toma['tipo']} real de Pexels").strip(" ·")
        cambiadas += 1
        ultima = k
    c.guardar_escenas(EscenasV2.model_validate(datos))
    escribir_json(c.ruta / "direccion.json", direccion)
    avisar(f"{cambiadas} escenas usan fotos o videos reales de Pexels en vez de imágenes nuevas")
    return cambiadas


def _cuadro_de_video(raiz: Path, archivo: str) -> str:
    """Un cuadro del video como imagen fija (para la vista del guion y el montaje)."""
    destino = (raiz / archivo).with_suffix(".jpg")
    if not destino.exists():
        subprocess.run([ffmpeg(), "-v", "error", "-y", "-ss", "1", "-i", str(raiz / archivo), "-frames:v", "1",
                        "-vf", "scale=1600:-2", str(destino)], check=True)
    return destino.relative_to(raiz).as_posix()


def ajustar_al_presupuesto(c: CarpetaProyecto, t=None, ejecutar_claude=None, usar_pexels: bool = True) -> dict:
    """Si las imágenes pasan el máximo, algunas escenas pasan a reusar la imagen de una escena
    anterior de la misma sección (el texto no cambia). Nunca se tocan el gancho, la revelación,
    el giro, el cierre, la primera imagen de cada sección ni las escenas del villano oculto."""
    from .esquemas import EscenasV2

    avisos: list[str] = []
    if t:
        original = t.avisar

        def _capturar(texto, _o=original):
            if texto.startswith("⚠"):
                avisos.append(texto)
            _o(texto)
        t.avisar = _capturar
    pexels = usar_pexels_en_escenas(c, t, ejecutar_claude) if usar_pexels else 0
    if t:
        t.avisar = original
    config = ConfigCostos.cargar()
    est = estimar_imagenes(c)
    precio_cop = est["cop"] / est["faltan"] if est["faltan"] else 0
    disponible = config.maximo_cop - MARGEN_COP - c.libro(config).total_cop()
    sobran = 0 if not precio_cop else max(0, math.ceil((est["cop"] - disponible) / precio_cop))
    if sobran == 0:
        return {"pexels": pexels, "convertidas": 0, **estimar_imagenes(c)}
    esc = c.cargar_escenas()
    direccion = leer_json(c.ruta / "direccion.json") if (c.ruta / "direccion.json").exists() else {}
    ocultas = set(direccion.get("pixelar_pendiente") or []) | {int(k) for k in (direccion.get("pixelar") or {})}
    man = leer_json(c.ruta / "imagenes" / "manifiesto.json") if (c.ruta / "imagenes" / "manifiesto.json").exists() else {}
    candidatas = []
    previa: dict[str, int] = {}              # sección → última escena con imagen propia
    racha = 0
    for k, e in enumerate(esc.escenas):
        if e.visual.accion != "generar":
            racha = 0
            continue
        fuente = previa.get(e.seccion)
        hecha = f"escena:{e.id}" in man       # ya pagada: se deja
        if (fuente is not None and not hecha and e.intencion not in PROTEGIDAS and e.id not in ocultas
                and fuente not in ocultas and e.intencion in REUSABLES):
            candidatas.append((REUSABLES.index(e.intencion), k, e.id, fuente))
        previa[e.seccion] = e.id
    elegidas: set[int] = set()
    usadas_como_fuente: dict[int, int] = {}
    for _, k, eid, fuente in sorted(candidatas):
        if len(elegidas) >= sobran:
            break
        # nunca dos seguidas y cada imagen se repite como mucho 2 veces más: que no se note
        if eid - 1 in elegidas or eid + 1 in elegidas or usadas_como_fuente.get(fuente, 0) >= 2:
            continue
        elegidas.add(eid)
        usadas_como_fuente[fuente] = usadas_como_fuente.get(fuente, 0) + 1
    datos = esc.model_dump()
    fuentes = {eid: f for _, _, eid, f in candidatas}
    for e in datos["escenas"]:
        if e["id"] in elegidas:
            e["visual"] = {**e["visual"], "accion": "reusar", "reusar_de": fuentes[e["id"]], "prompt": None,
                           "tipo": None, "referencias": []}
            e["notas_edicion"] = ((e.get("notas_edicion") or "") + " · reusa imagen para cuidar el presupuesto").strip(" ·")
    c.guardar_escenas(EscenasV2.model_validate(datos))
    r = {"pexels": pexels, "convertidas": len(elegidas), **estimar_imagenes(c)}
    if t:
        t.avisar(f"Listo: {pexels} escenas con Pexels y {len(elegidas)} que reusan una imagen cercana. "
                 f"Imágenes nuevas: {r['faltan']} (≈ {r['texto']})" + (" · " + avisos[0] if avisos else ""))
    return r


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
    _ubicar_focos(c, t, ejecutar_claude)
    _stock(c, t, ejecutar_claude)
    c.marcar("assets", "completo", ["imagenes/", "assets/tira/"])


def _stock(c: CarpetaProyecto, t: Trabajo, ejecutar_claude=None) -> None:
    """Fotos y videos reales verificados (Pexels). Sin clave o si falla, el video sale igual."""
    from . import claude_cli
    from .stock import SinClavePexels, preparar_stock

    try:
        preparar_stock(c.ruta, ejecutar=ejecutar_claude or claude_cli.ejecutar, avisar=t.avisar)
    except SinClavePexels as ex:
        t.avisar(f"⚠ Sin fotos reales de Pexels: {ex}")
    except Exception as ex:  # noqa: BLE001 — no es imprescindible
        t.avisar(f"Sin fotos reales esta vez: {str(ex)[:160]}")


def _ubicar_focos(c: CarpetaProyecto, t: Trabajo, ejecutar_claude=None) -> None:
    """Claude mira las imágenes donde la voz nombra un animal o un detalle (círculo y
    flechas). Si falla, el video sale igual, solo sin esos focos."""
    from . import claude_cli
    from .foco import ubicar_focos

    try:
        ubicar_focos(c.ruta, ejecutar=ejecutar_claude or claude_cli.ejecutar, avisar=t.avisar)
    except Exception as ex:  # noqa: BLE001 — no es imprescindible
        t.avisar(f"Sin círculo ni flechas esta vez: {str(ex)[:160]}")


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


def paso_video(c: CarpetaProyecto, t: Trabajo, permiso: bool = False, fps: int | None = None) -> Path:
    from .edicion import construir_edl, validar
    from .render import renderizar
    from .voz import generar_voz

    c.marcar("voz", "en_curso")
    t.avisar("Grabando la voz…")
    t.progreso = 0.05
    generar_voz(c, ffmpeg(), permiso=permiso, avisar=t.avisar)
    c.marcar("voz", "completo", ["audio/voz.wav"])
    t.progreso = 0.2
    direccion = c.ruta / "direccion.json"
    if not direccion.exists() or "focos_revisados" not in leer_json(direccion):
        _ubicar_focos(c, t)
    _stock(c, t)                               # reanudable: solo busca los niveles que falten
    from .poses import copiar_presentador

    if copiar_presentador(c.cargar().estilo, c.ruta):
        try:
            from .reacciones import elegir_reacciones

            elegir_reacciones(c.ruta, avisar=t.avisar)
        except Exception as ex:  # noqa: BLE001 — sin Claude se usan las reglas por intención
            t.avisar(f"Reacciones por reglas (Claude no respondió: {str(ex)[:120]})")
    t.avisar("Editando: cortes, movimientos, textos y subtítulos…")
    edl = construir_edl(c)
    avisos = validar(edl, _perfil(c))
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

    vertical = c.cargar_escenas().relacion_aspecto == "9:16"
    t.avisar("Renderizando el short vertical…" if vertical else "Renderizando el video…")
    from .render import _salida

    ancho, alto, fps_config = _salida()
    salida = (ancho, alto, fps if fps in (30, 60) else fps_config)
    final = renderizar(c, ffmpeg(), c.ruta / "render" / "final.mp4", avisar=avisar, calidad="maxima",
                       vertical=vertical, salida=salida)
    destino = carpeta_videos() / f"{slugificar(c.cargar().titulo)[:60]}.mp4"
    shutil.copy(final, destino)
    shutil.copy(final.with_suffix(".srt"), destino.with_suffix(".srt"))
    c.marcar("export_final", "completo", [str(destino)])
    t.avisar(f"Video listo: {destino}")
    return destino


def paso_short(c: CarpetaProyecto, t: Trabajo, permiso: bool = False) -> Path:
    """Short vertical (9:16) sacado del video largo: no genera imágenes, solo voz."""
    from .short import crear_short

    corto = crear_short(c.ruta, c.ruta.parent, avisar=t.avisar)
    t.progreso = 0.05
    return paso_video(corto, t, permiso=permiso)


def resumen(c: CarpetaProyecto) -> dict:
    """Todo lo que la página necesita para pintar un video."""
    p = c.cargar()
    config = ConfigCostos.cargar()
    datos = {"slug": c.ruta.name, "titulo": p.titulo, "minutos": round(p.duracion_objetivo_seg / 60, 1),
             "pasos": {k: v.estado for k, v in p.pasos.items()},
             "costo": formato_cop(c.libro(config).total_cop()), "escenas": [], "guion": None,
             "video": None, "trabajo": None, "prueba": None,
             "divulgacion": p.requiere_divulgacion_contenido_sintetico, "vertical": False}
    if c.archivo_escenas.exists():
        esc = c.cargar_escenas()
        datos["vertical"] = esc.relacion_aspecto == "9:16"
        datos["puede_short"] = bool(esc.niveles)
        man = leer_json(c.ruta / "imagenes" / "manifiesto.json") if (c.ruta / "imagenes" / "manifiesto.json").exists() else {}
        archivos = {e.id: e.visual.archivo for e in esc.escenas}
        for e in esc.escenas:
            img = None
            if e.visual.accion == "generar" and f"escena:{e.id}" in man:
                img = man[f"escena:{e.id}"]["archivo"]
            elif e.visual.accion == "reusar" and isinstance(e.visual.reusar_de, int):
                ref = man.get(f"escena:{e.visual.reusar_de}")
                img = ref["archivo"] if ref else None
            elif e.visual.accion == "reusar" and isinstance(e.visual.reusar_de, str) \
                    and e.visual.reusar_de.startswith("pexels_"):
                img = next((a.archivo for a in esc.assets if a.id == e.visual.reusar_de), None)
            elif e.visual.accion == "reusar" and isinstance(e.visual.reusar_de, str):
                n = next((x for x in esc.niveles if x.asset == e.visual.reusar_de), None)
                oculto = n and n.villano and cargar_estilo(p.estilo).ocultar_villano
                img = f"assets/tira/tarjeta_{n.numero}{'_pixelada' if oculto else ''}.png" if n else None
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
