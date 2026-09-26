"""Línea de comandos del Estudio (Fase 0).

    python -m estudio estilos
    python -m estudio nuevo "Título" --canal animales-peligrosos --estilo enciclopedia_mascota --minutos 10
    python -m estudio importar-v1 ruta/escenas_v1.json --slug alacranes --canal animales-peligrosos
    python -m estudio estimar --slug alacranes           (duración real del proyecto)
    python -m estudio estimar --minutos 10 --estilo enciclopedia_mascota
    python -m estudio validar --slug alacranes
    python -m estudio costos --slug alacranes
    python -m estudio generar-imagenes --slug alacranes --primeras 10
    python -m estudio generar-imagenes --slug prueba --primeras 10 --proveedor simulado
"""
from __future__ import annotations

import argparse
import sys

from .config import ConfigCostos, formato_cop, leer_json
from .estilos import cargar_estilo, cargar_perfil_edicion, listar_estilos
from .estimador import estimar
from .importar_v1 import convertir, duracion_escenas
from .proyecto import CarpetaProyecto, slugificar


def _perfil(c):
    return cargar_perfil_edicion(cargar_estilo(c.cargar().estilo))


def _cmd_estilos(_: argparse.Namespace) -> int:
    for e in listar_estilos():
        personaje = "con personaje" if e.con_personaje is True else "sin personaje"
        print(f"{e.id:<24} {e.nombre} ({personaje}) · tipos: {', '.join(sorted(e.ids_tipos))}")
    return 0


def _cmd_nuevo(a: argparse.Namespace) -> int:
    c = CarpetaProyecto.crear(a.titulo, a.canal, a.estilo, a.minutos * 60, slug=a.slug)
    print(f"Proyecto creado en {c.ruta}")
    return _estimar_proyecto(c)


def _cmd_importar(a: argparse.Namespace) -> int:
    v1 = leer_json(a.archivo)
    estilo = cargar_estilo(a.estilo)
    res = convertir(v1, estilo, canal=a.canal, video=a.titulo)
    for av in res.avisos:
        print(f"aviso: {av}")
    for eid, textos in res.efectos_no_reconocidos.items():
        print(f"aviso: escena {eid}: efectos sin equivalente en el catálogo: {textos}")
    if res.errores or res.escenas is None:
        for err in res.errores:
            print(f"error: {err}", file=sys.stderr)
        return 1
    esc = res.escenas
    config = ConfigCostos.cargar()
    dur, _ = duracion_escenas(esc, config.consumo["caracteres_por_segundo_narracion"])
    slug = a.slug or slugificar(esc.video)
    c = CarpetaProyecto.crear(esc.video, esc.canal, estilo.id, dur, slug=slug)
    c.guardar_escenas(esc)
    print(f"Importadas {len(esc.escenas)} escenas en {c.archivo_escenas}")
    return _estimar_proyecto(c)


def _estimar_proyecto(c: CarpetaProyecto) -> int:
    config = ConfigCostos.cargar()
    p = c.cargar()
    estilo = cargar_estilo(p.estilo)
    perfil = cargar_perfil_edicion(estilo)
    dur, fuente = p.duracion_objetivo_seg, "objetivo del proyecto"
    if c.archivo_escenas.exists():
        dur, fuente = duracion_escenas(c.cargar_escenas(), config.consumo["caracteres_por_segundo_narracion"])
    print(f"Duración usada: {dur:.0f} s ({fuente})")
    rango = config.datos.get("duracion_video_seg") or {}
    if rango and not (rango["minimo"] <= dur <= rango["maximo"]):
        print(f"AVISO: el video dura {dur / 60:.1f} min y la regla es de {rango['minimo'] / 60:.0f} a "
              f"{rango['maximo'] / 60:.0f} min. Acórtalo antes de generar.")
    est = estimar(dur, estilo, perfil, config, gastado_cop=c.libro(config).total_cop())
    print(est.resumen())
    return 0


def _cmd_estimar(a: argparse.Namespace) -> int:
    if a.slug:
        return _estimar_proyecto(CarpetaProyecto.abrir(a.slug))
    if not a.minutos:
        print("error: indica --slug o --minutos", file=sys.stderr)
        return 2
    estilo = cargar_estilo(a.estilo)
    est = estimar(a.minutos * 60, estilo, cargar_perfil_edicion(estilo), ConfigCostos.cargar())
    print(est.resumen())
    return 0


def _cmd_validar(a: argparse.Namespace) -> int:
    errores = CarpetaProyecto.abrir(a.slug).validar()
    for e in errores:
        print(f"error: {e}")
    print("OK: todos los contratos son válidos" if not errores else f"{len(errores)} errores")
    return 1 if errores else 0


def _cmd_costos(a: argparse.Namespace) -> int:
    c = CarpetaProyecto.abrir(a.slug)
    libro = c.libro(ConfigCostos.cargar())
    for modulo, cop in sorted(libro.por_modulo().items()):
        print(f"{modulo:<20} {formato_cop(cop):>12}")
    print(f"{'TOTAL base':<20} {formato_cop(libro.total_cop()):>12}")
    print(f"{'Animación (aparte)':<20} {formato_cop(libro.total_cop('animacion')):>12}")
    print(f"Siguiente paso: {c.siguiente_paso() or 'ninguno (terminado)'}")
    return 0


def _cmd_generar_imagenes(a: argparse.Namespace) -> int:
    from .imagenes.generador import generar_imagenes, hoja_de_contacto, proyectar

    c = CarpetaProyecto.abrir(a.slug)
    config = ConfigCostos.cargar()
    ids = [int(x) for x in a.ids.split(",")] if a.ids else None
    solo = [x.strip() for x in a.assets.split(",")] if a.assets else None
    if a.niveles:
        solo = [n.asset for n in c.cargar_escenas().niveles]
    antes = c.libro(config).total_cop()
    r = generar_imagenes(c, primeras=a.primeras, ids=ids, solo_assets=solo, nombre_proveedor=a.proveedor,
                         permiso=a.permiso, config=config)
    print()
    print(f"Proveedor: {r.proveedor} · modelo {r.modelo}")
    print(f"Generadas: {len(r.generadas)} · ya estaban: {len(r.ya_estaban)} · reusadas: {len(r.reusadas)} "
          f"· fallidas: {len(r.fallidas)} · llamadas pagadas: {r.llamadas}")
    for k, v in r.fallidas.items():
        print(f"  fallida {k}: {v}")
    for av in r.avisos:
        print(f"  aviso: {av}")
    for pend in r.pendientes:
        print(f"  pendiente: {pend}")
    gastado = c.libro(config).total_cop() - antes
    print(f"Costo real de esta corrida: {formato_cop(gastado)} ({r.costo_usd:.4f} USD)")
    if r.costos_por_imagen:
        medio = sum(r.costos_por_imagen.values()) / len(r.costos_por_imagen)
        print(f"Costo medio por imagen en esta corrida: {medio:.4f} USD · {formato_cop(config.a_cop(medio))}")
    print(f"Total del proyecto hasta ahora: {formato_cop(c.libro(config).total_cop())}")
    pr = proyectar(c, config)
    if pr:
        print(f"Proyección de imágenes del video completo ({pr.base}): {pr.imagenes_video} imágenes x "
              f"{pr.costo_medio_usd:.4f} USD = {pr.total_usd:.2f} USD · {formato_cop(pr.total_cop)}")
    claves = r.generadas + r.ya_estaban
    hoja = hoja_de_contacto(c, [k for k in claves if k.startswith("escena:")] or claves,
                            c.ruta / "render" / "hoja_imagenes.png")
    if hoja:
        print(f"Hoja de contacto: {hoja}")
    if r.frenado:
        print(f"FRENO: {r.frenado}", file=sys.stderr)
        return 3
    return 1 if r.fallidas else 0


def _cmd_armar_tira(a: argparse.Namespace) -> int:
    from .tira import armar_tira

    c = CarpetaProyecto.abrir(a.slug)
    p = c.cargar()
    armada = armar_tira(c.cargar_escenas(), cargar_estilo(p.estilo), c.ruta, seed=p.semilla)
    print(f"Tira de {len(armada.centros_x)} niveles en {c.ruta / 'assets' / 'tira'}")
    return 0


def _cmd_clip_tira(a: argparse.Namespace) -> int:
    import imageio_ffmpeg

    from .tira import armar_tira, clip_tira

    c = CarpetaProyecto.abrir(a.slug)
    p = c.cargar()
    armada = armar_tira(c.cargar_escenas(), cargar_estilo(p.estilo), c.ruta, seed=p.semilla)
    destino = clip_tira(armada, c.ruta / "render" / "clip_tira.mp4", imageio_ffmpeg.get_ffmpeg_exe())
    print(f"Clip: {destino}")
    return 0


def _cmd_generar_voz(a: argparse.Namespace) -> int:
    import imageio_ffmpeg

    from .voz import generar_voz

    c = CarpetaProyecto.abrir(a.slug)
    config = ConfigCostos.cargar()
    antes = c.libro(config).total_cop()
    r = generar_voz(c, imageio_ffmpeg.get_ffmpeg_exe(), config=config, permiso=a.permiso)
    print(f"Voz: {r['duracion'] / 60:.2f} min en {r['grupos']} oraciones · {r['archivo']}")
    print(f"Costo de esta corrida: {formato_cop(c.libro(config).total_cop() - antes)}")
    return 0


def _cmd_editar(a: argparse.Namespace) -> int:
    from .edicion import construir_edl, validar

    c = CarpetaProyecto.abrir(a.slug)
    edl = construir_edl(c)
    avisos = validar(edl, _perfil(c))
    p = edl["pistas"]
    print(f"EDL: {edl['duracion_total'] / 60:.2f} min · {len(p['escenas'])} clips · {len(p['textos'])} textos · "
          f"{len(p['subtitulos'])} subtítulos · {len(p['sfx'])} efectos de sonido")
    for x in avisos:
        print(f"  validador: {x}")
    return 1 if avisos else 0


def _cmd_render(a: argparse.Namespace) -> int:
    import imageio_ffmpeg

    from .render import renderizar

    c = CarpetaProyecto.abrir(a.slug)
    destino = c.ruta / "render" / (a.salida or "final.mp4")
    r = renderizar(c, imageio_ffmpeg.get_ffmpeg_exe(), destino, desde=a.desde, hasta=a.hasta)
    print(f"Video: {r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="estudio", description="Estudio de producción · Buscanichos")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("estilos", help="lista el catálogo de estilos").set_defaults(fn=_cmd_estilos)

    n = sub.add_parser("nuevo", help="crea un proyecto vacío y muestra la estimación")
    n.add_argument("titulo")
    n.add_argument("--canal", required=True)
    n.add_argument("--estilo", default="enciclopedia_mascota")
    n.add_argument("--minutos", type=float, required=True)
    n.add_argument("--slug")
    n.set_defaults(fn=_cmd_nuevo)

    i = sub.add_parser("importar-v1", help="convierte un escenas.json v1 en un proyecto v2")
    i.add_argument("archivo")
    i.add_argument("--slug")
    i.add_argument("--canal")
    i.add_argument("--titulo")
    i.add_argument("--estilo", default="enciclopedia_mascota")
    i.set_defaults(fn=_cmd_importar)

    e = sub.add_parser("estimar", help="estimación previa del costo en pesos y dólares")
    e.add_argument("--slug")
    e.add_argument("--minutos", type=float)
    e.add_argument("--estilo", default="enciclopedia_mascota")
    e.set_defaults(fn=_cmd_estimar)

    v = sub.add_parser("validar", help="valida los contratos del proyecto")
    v.add_argument("--slug", required=True)
    v.set_defaults(fn=_cmd_validar)

    k = sub.add_parser("costos", help="muestra el libro de costos del proyecto")
    k.add_argument("--slug", required=True)
    k.set_defaults(fn=_cmd_costos)

    g = sub.add_parser("generar-imagenes", help="genera las imágenes de las escenas (reanudable, con freno)")
    g.add_argument("--slug", required=True)
    g.add_argument("--primeras", type=int, help="solo las N primeras escenas")
    g.add_argument("--ids", help="ids de escena separados por coma")
    g.add_argument("--proveedor", help="gemini | simulado (por defecto, config/proveedores.json)")
    g.add_argument("--permiso", action="store_true", help="permite pasar el máximo y el tope de llamadas")
    g.add_argument("--assets", help="solo estos assets, separados por coma")
    g.add_argument("--niveles", action="store_true", help="solo los assets de la tira de niveles")
    g.set_defaults(fn=_cmd_generar_imagenes)

    t = sub.add_parser("armar-tira", help="arma la tira de niveles (sección 15) con código")
    t.add_argument("--slug", required=True)
    t.set_defaults(fn=_cmd_armar_tira)
    k2 = sub.add_parser("clip-tira", help="clip de prueba: desliza del nivel 1 al último y revela al villano")
    k2.add_argument("--slug", required=True)
    k2.set_defaults(fn=_cmd_clip_tira)

    vz = sub.add_parser("generar-voz", help="voz con MiniMax y tiempos reales por escena")
    vz.add_argument("--slug", required=True)
    vz.add_argument("--permiso", action="store_true")
    vz.set_defaults(fn=_cmd_generar_voz)

    ed = sub.add_parser("editar", help="Director de edición por reglas: construye y valida edl.json")
    ed.add_argument("--slug", required=True)
    ed.set_defaults(fn=_cmd_editar)
    rd = sub.add_parser("render", help="renderiza edl.json a MP4 (voz y efectos mezclados y normalizados)")
    rd.add_argument("--slug", required=True)
    rd.add_argument("--desde", type=float, default=0.0)
    rd.add_argument("--hasta", type=float)
    rd.add_argument("--salida")
    rd.set_defaults(fn=_cmd_render)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (FileNotFoundError, FileExistsError, ValueError) as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
