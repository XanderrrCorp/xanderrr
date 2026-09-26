"""Estimación previa obligatoria del costo de un video (sección 2).

Todo sale de la duración objetivo, del estilo y del perfil de edición:
    escenas         = duración ÷ segundos promedio por imagen del perfil
    imágenes nuevas = escenas × proporción de imágenes únicas × costo relativo del estilo
                      + assets fijos, con un margen de reintentos de control de calidad
Si la proyección supera el objetivo se degrada (regla 2.4); si queda claramente por
debajo se mejora (regla 2.5). Nunca se incluye animación (regla 2.7).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .config import ConfigCostos, PrecioFaltante, formato_cop, formato_usd
from .esquemas import Estilo, PerfilEdicion

BLOQUES = {
    "claude_guion": "Estratega + Guionista + Director visual (Claude)",
    "claude_edicion": "Director de edición + Revisor (Claude, texto y visión)",
    "voz": "Voz (TTS)",
    "imagenes": "Imágenes",
    "local": "Alineador, FFmpeg, música y efectos locales",
}


@dataclass
class Plan:
    proporcion_unicas: float
    vueltas_revisor: int


@dataclass
class Calculo:
    plan: Plan
    escenas: int
    imagenes_nuevas: int
    caracteres_voz: int
    hojas_contacto_por_vuelta: int
    desglose_usd: dict[str, float]
    faltantes: list[str]

    @property
    def total_usd(self) -> float:
        return sum(self.desglose_usd.values())


@dataclass
class Ajuste:
    regla: str
    cambio: str
    razon: str


@dataclass
class Estimacion:
    duracion_seg: float
    estilo: str
    calculo: Calculo
    inicial: Calculo
    ajustes: list[Ajuste] = field(default_factory=list)
    estado: str = ""
    gastado_cop: float = 0.0
    config: ConfigCostos | None = None

    @property
    def total_cop(self) -> float:
        return self.config.a_cop(self.calculo.total_usd)

    def resumen(self) -> str:
        c, cfg = self.calculo, self.config
        lineas = [
            f"Estimación · {self.duracion_seg / 60:.1f} min · estilo '{self.estilo}'",
            f"  Escenas: {c.escenas} · imágenes nuevas: {c.imagenes_nuevas} "
            f"(proporción única {c.plan.proporcion_unicas:.0%}) · vueltas del Revisor: {c.plan.vueltas_revisor}",
        ]
        for clave, usd in c.desglose_usd.items():
            lineas.append(f"  {BLOQUES[clave]:<55} {formato_usd(usd):>10}  {formato_cop(cfg.a_cop(usd)):>12}")
        lineas.append(f"  {'TOTAL':<55} {formato_usd(c.total_usd):>10}  {formato_cop(self.total_cop):>12}")
        lineas.append(
            f"  Objetivo {formato_cop(cfg.objetivo_cop)} · máximo {formato_cop(cfg.maximo_cop)} · TRM {cfg.trm:g}"
        )
        if self.gastado_cop:
            lineas.append(f"  Ya gastado en este proyecto: {formato_cop(self.gastado_cop)}")
        lineas.append("  Animación: no incluida (opcional, se confirma escena por escena).")
        for a in self.ajustes:
            lineas.append(f"  Ajuste [{a.regla}] {a.cambio}: {a.razon}")
        if c.faltantes:
            lineas.append(f"  ⚠ Precios faltantes en config/costos.json: {', '.join(c.faltantes)}. "
                          "La estimación está incompleta.")
        lineas.append(f"  Estado: {self.estado}")
        return "\n".join(lineas)


def _costo(faltantes: list[str], fn) -> float:
    try:
        return fn()
    except PrecioFaltante as e:
        faltantes.append(str(e))
        return 0.0


def calcular(duracion_seg: float, estilo: Estilo, perfil: PerfilEdicion,
             config: ConfigCostos, plan: Plan) -> Calculo:
    cons = config.consumo
    escenas = max(1, math.ceil(duracion_seg / perfil.segundos_promedio_por_imagen))
    faltantes: list[str] = []
    modelo = lambda modulo: config.modelos.get(modulo, "claude-opus-5")  # noqa: E731

    # Claude: estratega (fijo) + guionista y director visual (por escena)
    def claude_guion() -> float:
        f = cons["tokens_fijos"]["estratega"]
        total = config.costo_claude(modelo("estratega"), f["input"], f["output"])
        for modulo in ("guionista", "director_visual"):
            t = cons["tokens_por_escena"][modulo]
            total += config.costo_claude(modelo(modulo), t["input"] * escenas, t["output"] * escenas)
        return total

    # Claude: director de edición (por escena) + revisor con hojas de contacto (4.4)
    rev = cons["revisor"]
    extra = 1.0 if perfil.segundos_promedio_por_imagen > rev["segundos_para_fotograma_extra"] \
        else rev["proporcion_escenas_largas"]
    fotogramas = escenas + math.ceil(escenas * extra)
    hojas = math.ceil(fotogramas / rev["fotogramas_por_hoja"])

    def claude_edicion() -> float:
        t = cons["tokens_por_escena"]["director_edicion"]
        total = config.costo_claude(modelo("director_edicion"), t["input"] * escenas, t["output"] * escenas)
        tin = hojas * (rev["tokens_imagen_por_hoja"] + rev["tokens_texto_por_hoja"])
        tout = hojas * rev["tokens_salida_por_hoja"]
        total += plan.vueltas_revisor * config.costo_claude(modelo("revisor"), tin, tout)
        return total

    caracteres = math.ceil(duracion_seg * cons["caracteres_por_segundo_narracion"])
    unicas = min(escenas, math.ceil(escenas * plan.proporcion_unicas * estilo.costo_relativo))
    imagenes = math.ceil((unicas + estilo.imagenes_fijas_por_video) * (1 + cons["tasa_reintentos_imagen"]))

    desglose = {
        "claude_guion": _costo(faltantes, claude_guion),
        "claude_edicion": _costo(faltantes, claude_edicion),
        "voz": _costo(faltantes, lambda: caracteres / 1000 * config.precio("tts_por_1000_caracteres")),
        "imagenes": _costo(faltantes, lambda: imagenes * config.precio("imagen_por_unidad")),
        "local": 0.0,
    }
    return Calculo(plan, escenas, imagenes, caracteres, hojas, desglose, sorted(set(faltantes)))


def estimar(duracion_seg: float, estilo: Estilo, perfil: PerfilEdicion, config: ConfigCostos,
            gastado_cop: float = 0.0) -> Estimacion:
    aj = config.ajustes
    paso = aj.get("paso_proporcion_unicas", 0.05)
    objetivo_usd = (config.objetivo_cop - gastado_cop) / config.trm
    vueltas = config.consumo["revisor"]["vueltas"]

    plan = Plan(estilo.proporcion_imagenes_unicas, vueltas)
    inicial = actual = calcular(duracion_seg, estilo, perfil, config, plan)
    ajustes: list[Ajuste] = []
    calc = lambda p: calcular(duracion_seg, estilo, perfil, config, p)  # noqa: E731

    if actual.total_usd > objetivo_usd:
        # 1) más reutilización de imágenes (recortes sobre fondo gris)
        p = plan.proporcion_unicas
        while actual.total_usd > objetivo_usd and p - paso >= estilo.proporcion_minima_unicas - 1e-9:
            p = round(p - paso, 4)
            actual = calc(Plan(p, vueltas))
        if p < plan.proporcion_unicas:
            ajustes.append(Ajuste("2.4-1", f"proporción de imágenes únicas {plan.proporcion_unicas:.0%} → {p:.0%}",
                                  "Más reutilización de recortes para acercarse al objetivo"))
        # 2) bajar escenas completas a recorte sobre papel (permite reutilizar aún más)
        if actual.total_usd > objetivo_usd:
            p2 = max(0.1, round(estilo.proporcion_minima_unicas - aj.get("reuso_extra_por_recortes", 0.1), 4))
            if p2 < p:
                actual = calc(Plan(p2, vueltas))
                ajustes.append(Ajuste("2.4-2", f"proporción de imágenes únicas {p:.0%} → {p2:.0%}",
                                      "Escenas completas pasan a recorte sobre papel, reutilizables"))
                p = p2
        # 3) revisor a una sola vuelta
        if actual.total_usd > objetivo_usd and vueltas > 1:
            actual = calc(Plan(p, 1))
            ajustes.append(Ajuste("2.4-3", f"vueltas del Revisor {vueltas} → 1",
                                  "Último recurso antes de pedir permiso"))

    elif actual.total_usd < objetivo_usd * aj.get("umbral_mejora", 0.85):
        # Mejora: subir imágenes únicas sin pasar del objetivo
        p = plan.proporcion_unicas
        while p + paso <= 1.0 + 1e-9:
            candidato = calc(Plan(round(p + paso, 4), vueltas))
            if candidato.total_usd > objetivo_usd:
                break
            p, actual = round(p + paso, 4), candidato
        if p > plan.proporcion_unicas:
            ajustes.append(Ajuste(
                "2.5", f"proporción de imágenes únicas {plan.proporcion_unicas:.0%} → {p:.0%}",
                "Margen bajo el objetivo: imágenes únicas extra para el gancho (primeros 30 a 60 s), "
                "luego escenas de revelación o amenaza, luego transiciones de sección"))

    total_cop = config.a_cop(actual.total_usd) + gastado_cop
    if total_cop <= config.objetivo_cop:
        estado = "dentro del objetivo"
    elif total_cop <= config.maximo_cop:
        estado = "supera el objetivo: requiere permiso para continuar"
    else:
        estado = "supera el máximo: FRENO, no se puede empezar sin permiso explícito"
    if actual.faltantes:
        estado += " (incompleta: faltan precios)"

    return Estimacion(duracion_seg, estilo.id, actual, inicial, ajustes, estado, gastado_cop, config)
