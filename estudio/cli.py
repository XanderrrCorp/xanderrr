"""Línea de comandos del Estudio (Fase 0).

    python -m estudio estilos
    python -m estudio nuevo "Título" --canal animales-peligrosos --estilo enciclopedia_mascota --minutos 10
    python -m estudio importar-v1 ruta/escenas_v1.json --slug alacranes --canal animales-peligrosos
    python -m estudio estimar --slug alacranes           (duración real del proyecto)
    python -m estudio estimar --minutos 10 --estilo enciclopedia_mascota
    python -m estudio validar --slug alacranes
    python -m estudio costos --slug alacranes
"""
from __future__ import annotations

import argparse
import sys

from .config import ConfigCostos, formato_cop, leer_json
from .estilos import cargar_estilo, cargar_perfil_edicion, listar_estilos
from .estimador import estimar
from .importar_v1 import convertir, duracion_escenas
from .proyecto import CarpetaProyecto, slugificar


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

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (FileNotFoundError, FileExistsError, ValueError) as ex:
        print(f"error: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
