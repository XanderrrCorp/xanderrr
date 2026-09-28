"""Orquesta la producción de la miniatura de un video y lo que se hace desde la página
(regenerar un sujeto, variantes del protagonista, editar textos sin regenerar...)."""
from __future__ import annotations

import shutil
from pathlib import Path

from .. import claude_cli
from ..config import ConfigCostos, escribir_json, leer_json
from ..costos import LibroCostos, formato_cop
from ..proyecto import CarpetaProyecto
from . import composicion, generar, qa
from .plan import Ajuste, Plan, planificar
from .plantilla import Plantilla, agregar_referencia, cargar, referencias_activas

CARPETA = "miniatura_escala"
REINTENTOS_QA = 2


def carpeta(c: CarpetaProyecto) -> Path:
    return c.ruta / CARPETA


def _plan(c: CarpetaProyecto) -> Plan | None:
    ruta = carpeta(c) / "plan.json"
    return Plan.model_validate(leer_json(ruta)) if ruta.exists() else None


def _guardar_plan(c: CarpetaProyecto, plan: Plan) -> None:
    escribir_json(carpeta(c) / "plan.json", plan.model_dump())


def _plantilla(c: CarpetaProyecto) -> Plantilla:
    return cargar(c.cargar().canal)


def estimacion(proveedor=None) -> dict:
    config = ConfigCostos.cargar()
    usd = generar.costo_por_imagen(proveedor)
    base, tope = 6 * usd, 6 * usd * (1 + REINTENTOS_QA)
    return {"imagenes": 6, "por_imagen_usd": round(usd, 3), "base_usd": round(base, 2), "tope_usd": round(tope, 2),
            "texto": f"6 imágenes ≈ {formato_cop(base * config.trm)}; con reintentos del control de calidad, como "
                     f"mucho {formato_cop(tope * config.trm)}. Claude (planificar y revisar) va por tu suscripción: 0 pesos."}


def _entrada(c: CarpetaProyecto) -> tuple[str, str, list[str]]:
    p = c.cargar()
    guion = (c.ruta / "guion.md").read_text(encoding="utf-8") if (c.ruta / "guion.md").exists() else ""
    niveles = []
    if c.archivo_escenas.exists():
        # la escala del video va de inofensivo a peligroso; la miniatura, del extremo al más inofensivo
        niveles = [n.nombre for n in reversed(c.cargar_escenas().niveles)]
    return p.titulo, guion, niveles


def componer(c: CarpetaProyecto, plan: Plan | None = None) -> dict:
    plan = plan or _plan(c)
    img, mapa = composicion.componer(carpeta(c), plan, _plantilla(c))
    composicion.guardar_jpg(img, carpeta(c) / "miniatura.jpg")
    composicion.vista_feed(img, carpeta(c) / "feed.jpg")
    escribir_json(carpeta(c) / "mapa.json", mapa)
    return mapa


def producir(c: CarpetaProyecto, t, permiso: bool = False, rehacer_plan: bool = False,
             ejecutar=None, proveedor=None) -> Path:
    """Plan → 6 sujetos en paralelo → recorte y composición → control de calidad (regenera lo que
    falle, máx. 2 veces por sujeto). Lo ya generado no se vuelve a pagar."""
    ejecutar = ejecutar or claude_cli.ejecutar
    base = carpeta(c)
    base.mkdir(parents=True, exist_ok=True)
    plantilla = _plantilla(c)
    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    plan = None if rehacer_plan else _plan(c)
    if plan is None:
        t.avisar("Claude está planificando la miniatura…")
        tema, guion, niveles = _entrada(c)
        plan = planificar(tema, plantilla, guion, niveles, ejecutar=ejecutar, cwd=c.ruta)
        _guardar_plan(c, plan)
    t.progreso = 0.1
    faltan = [i for i, k in enumerate(plan.cells) if not k.archivo or not (base / k.archivo).exists()]
    if faltan:
        n_refs = len(referencias_activas(plantilla))
        t.avisar(f"Gemini está dibujando {len(faltan)} sujetos por separado ({n_refs} referencias de estilo)…")
        generar.generar(base, plan, plantilla, faltan, libro, proveedor, permiso=permiso, avisar=t.avisar)
        _guardar_plan(c, plan)
    t.progreso = 0.5
    _censura(c, plan, ejecutar)
    t.avisar("Armando la miniatura…")
    mapa = componer(c, plan)
    informe = {"rondas": []}
    for ronda in range(REINTENTOS_QA + 1):
        t.avisar("Claude está revisando la miniatura…" if ronda == 0 else f"Revisando otra vez (ronda {ronda + 1})…")
        r = qa.revisar(base, plan, base / "miniatura.jpg", ejecutar, medidas=mapa.get("medidas"))
        informe["rondas"].append(r)
        malos = [int(k) for k, v in r["sujetos"].items()
                 if not v["ok"] and plan.cells[int(k)].intentos_qa < REINTENTOS_QA]
        if not malos or ronda == REINTENTOS_QA:
            break
        t.avisar(f"Regenerando {len(malos)} sujeto(s) que no pasaron la revisión…")
        for i in malos:
            plan.cells[i].intentos_qa += 1
        generar.generar(base, plan, plantilla, malos, libro, proveedor, permiso=permiso, avisar=t.avisar,
                        extras={i: r["sujetos"][str(i)]["arreglo"] for i in malos})
        _guardar_plan(c, plan)
        if 0 in malos:
            plan.hero_censor_box = None
            _censura(c, plan, ejecutar)
        mapa = componer(c, plan)
        t.progreso = min(0.95, t.progreso + 0.15)
    informe["aprobada"] = all(v["ok"] for v in informe["rondas"][-1]["sujetos"].values())
    escribir_json(base / "qa.json", informe)
    _guardar_plan(c, plan)
    try:                                   # una copia junto a los videos, lista para subir
        from ..pipeline import carpeta_videos, slugificar

        shutil.copy(base / "miniatura.jpg", carpeta_videos() / f"{slugificar(c.cargar().titulo)[:60]}_miniatura.jpg")
    except OSError:
        pass
    t.avisar("Miniatura lista" + ("" if informe["aprobada"] else " (con observaciones del control de calidad)"))
    return base / "miniatura.jpg"


def _censura(c: CarpetaProyecto, plan: Plan, ejecutar) -> None:
    hero = plan.cells[0]
    if plan.hero_censor and hero.archivo and plan.hero_censor_box is None:
        plan.hero_censor_box = qa.ubicar_herida(carpeta(c), hero.archivo, ejecutar)
        _guardar_plan(c, plan)


def regenerar(c: CarpetaProyecto, t, indice: int, instruccion: str = "", permiso: bool = False,
              ejecutar=None, proveedor=None) -> None:
    ejecutar = ejecutar or claude_cli.ejecutar
    plan = _plan(c)
    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    t.avisar(f"Regenerando «{plan.cells[indice].name}»…")
    generar.generar(carpeta(c), plan, _plantilla(c), [indice], libro, proveedor, extras={indice: instruccion},
                    permiso=permiso, avisar=t.avisar)
    if indice == 0:
        plan.hero_censor_box = None
        _censura(c, plan, ejecutar)
    _guardar_plan(c, plan)
    componer(c, plan)


def variantes_protagonista(c: CarpetaProyecto, t, n: int = 2, permiso: bool = False, proveedor=None) -> list[str]:
    """2-3 versiones más del protagonista para elegir; la elegida no cambia sola."""
    plan = _plan(c)
    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    t.avisar(f"Dibujando {n} variantes del protagonista…")
    hechas = []
    for _ in range(n):
        hechas += list(generar.generar(carpeta(c), plan, _plantilla(c), [0], libro, proveedor, permiso=permiso,
                                       avisar=t.avisar, elegir=False).values())
    _guardar_plan(c, plan)
    return hechas


def elegir(c: CarpetaProyecto, indice: int, archivo: str, ejecutar=None) -> dict:
    ejecutar = ejecutar or claude_cli.ejecutar
    plan = _plan(c)
    if archivo not in plan.cells[indice].variantes:
        raise ValueError("esa imagen no es de este sujeto")
    plan.cells[indice].archivo = archivo
    if indice == 0:
        plan.hero_censor_box = None
        _censura(c, plan, ejecutar)
    _guardar_plan(c, plan)
    return componer(c, plan)


def editar(c: CarpetaProyecto, cambios: dict) -> dict:
    """Textos, ícono, color del aura, orden y ajustes manuales: solo se recompone (gratis)."""
    plan = _plan(c)
    datos = plan.model_dump()
    for k in ("hero_text", "hero_icon", "hero_glow_color", "hero_censor"):
        if k in cambios:
            datos[k] = cambios[k]
    if "orden" in cambios:
        orden = [int(i) for i in cambios["orden"]]
        if sorted(orden) != list(range(6)):
            raise ValueError("el orden debe tener los 6 sujetos")
        datos["cells"] = [datos["cells"][i] for i in orden]
        for k, celda in enumerate(datos["cells"]):
            celda["is_hero"] = k == 0                    # el de arriba a la izquierda es el protagonista
        if orden[0] != 0:
            datos["hero_censor_box"] = None
    for i, label in (cambios.get("labels") or {}).items():
        datos["cells"][int(i)]["label"] = label
    for i, ajuste in (cambios.get("ajustes") or {}).items():
        datos["cells"][int(i)]["ajuste"] = Ajuste.model_validate(ajuste).model_dump()
    if datos["hero_icon"] not in _plantilla(c).iconos_permitidos:
        from .iconos import disponibles
        from .plantilla import ruta_plantilla

        if datos["hero_icon"] not in disponibles(ruta_plantilla(c.cargar().canal)):
            raise ValueError("ese ícono no existe")
    plan = Plan.model_validate(datos)
    _guardar_plan(c, plan)
    return componer(c, plan)


def usar_como_referencia(c: CarpetaProyecto, indice: int) -> Plantilla:
    plan = _plan(c)
    archivo = plan.cells[indice].archivo
    if not archivo:
        raise ValueError("ese sujeto aún no tiene imagen")
    ruta = carpeta(c) / archivo
    return agregar_referencia(c.cargar().canal, ruta.read_bytes(), f"{plan.cells[indice].name}{ruta.suffix}")


def estado(c: CarpetaProyecto) -> dict:
    base = carpeta(c)
    plan = _plan(c)
    plantilla = _plantilla(c)
    from .iconos import disponibles
    from .plantilla import ruta_plantilla

    libro = LibroCostos(c.ruta, ConfigCostos.cargar())
    gastado = sum(e.get("costo_cop", 0) for e in libro.entradas() if e.get("modulo") == "miniatura")
    return {"plan": plan.model_dump() if plan else None,
            "mapa": leer_json(base / "mapa.json") if (base / "mapa.json").exists() else None,
            "qa": leer_json(base / "qa.json") if (base / "qa.json").exists() else None,
            "miniatura": f"{CARPETA}/miniatura.jpg" if (base / "miniatura.jpg").exists() else None,
            "feed": f"{CARPETA}/feed.jpg" if (base / "feed.jpg").exists() else None,
            "estimacion": estimacion(), "gastado": formato_cop(gastado),
            "iconos": [i for i in disponibles(ruta_plantilla(plantilla.canal)) if i in plantilla.iconos_permitidos],
            "plantilla": plantilla.model_dump(), "carpeta": CARPETA}


def borrar_plan(c: CarpetaProyecto) -> None:
    """Empieza de cero (las imágenes ya pagadas se conservan en sujetos/)."""
    (carpeta(c) / "plan.json").unlink(missing_ok=True)
    shutil.rmtree(carpeta(c) / "recortes", ignore_errors=True)
