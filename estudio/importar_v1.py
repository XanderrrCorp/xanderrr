"""Conversión de `escenas.json` v1 (pipeline anterior) a v2 (sección 3.1).

Los tres cambios de v2: intención + intensidad por escena, efectos estructurados
en lugar de texto libre, y tiempos (estimados ahora, reales tras el Alineador).

El lector es tolerante con los nombres de campo porque v1 no tenía esquema. La
intención se infiere con reglas simples y queda marcada para que la Pasada de
estructura del Director de edición (4, paso 1) la revise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .esquemas import EscenasV2, Estilo

# texto libre de v1 → efecto del catálogo (el orden importa: lo específico primero)
_EFECTOS_TEXTO: list[tuple[str, dict[str, Any]]] = [
    (r"zoom\s*(golpe|punch|r[aá]pido)|punch\s*in", {"efecto": "zoom_golpe", "intensidad": 0.06}),
    (r"destello\s*rojo|flash\s*rojo|red\s*flash", {"efecto": "destello_rojo"}),
    (r"destello|flash", {"efecto": "destello"}),
    (r"revelar|despixel|quitar\s*pixel", {"efecto": "revelar_pixelado"}),
    (r"pixel", {"efecto": "pixelar"}),
    (r"alej|zoom\s*out", {"efecto": "alejamiento_lento"}),
    (r"zoom|acerc", {"efecto": "zoom_lento"}),
    (r"pane|pan\b", {"efecto": "paneo_lento"}),
    (r"corte\s*seco|hard\s*cut", {"efecto": "corte_seco"}),
    (r"fundido|fade", {"efecto": "fundido_corto"}),
    (r"rebote|bounce|pop\s*in", {"efecto": "entrada_rebote"}),
    (r"temblor|shake|sacud", {"efecto": "temblor_leve"}),
    (r"tinte\s*rojo|fondo\s*rojo|rojo", {"efecto": "tinte_rojo"}),
    (r"oscurec|dark", {"efecto": "oscurecer_fondo"}),
    (r"tira|nivel", {"efecto": "tira_deslizar_a_nivel"}),
    (r"lado\s*a\s*lado|split|compar", {"efecto": "lado_a_lado"}),
    (r"flecha|arrow", {"efecto": "flecha"}),
    (r"c[ií]rculo|circle", {"efecto": "circulo_rojo"}),
    (r"advertencia|⚠|warning|alerta", {"efecto": "icono_advertencia"}),
    (r"golpe|impact|boom|whoosh|sonido|sfx", {"efecto": "sfx", "sonido": "golpe_grave"}),
]

_INTENCIONES_TEXTO: list[tuple[str, str, int]] = [
    (r"suscr[ií]b|like|comenta", "llamado_accion", 2),
    (r"\?|¿", "pregunta_al_espectador", 3),
    (r"\bgiro\b|pero aqu[ií]|sin embargo|lo que nadie", "giro", 4),
    (r"urgencias|m[eé]dico|hospital|si te pica|qu[eé] hacer", "consejo_practico", 3),
    (r"mortal|muerte|mata|letal|peligros|veneno|neurot[oó]x", "amenaza", 4),
    (r"cuidado|nunca|no toques|evita", "advertencia", 3),
    (r"\b(m[aá]s que|menos que|compar|a diferencia)\b", "comparacion", 2),
    (r"\b(mil|millones|cient|por ciento|veces)\b", "dato_impactante", 3),
    (r"jaja|curiosamente|imagina", "humor", 2),
]

_CAMPOS_NARRACION = ("narracion", "texto", "voz", "guion", "locucion")
_CAMPOS_TIPO = ("tipo", "tipo_visual", "tipo_escena")
_CAMPOS_PROMPT = ("prompt", "prompt_imagen", "image_prompt")
_CAMPOS_ARCHIVO = ("archivo", "archivo_salida", "imagen", "image", "ruta_imagen")
_CAMPOS_EFECTOS = ("efectos", "efecto", "efectos_texto", "edicion", "fx")
_CAMPOS_INICIO = ("inicio", "inicio_seg", "tiempo_inicio", "start", "estimado_inicio")
_CAMPOS_DURACION = ("duracion", "duracion_seg", "duracion_estimada", "duration", "estimado_duracion")
_CAMPOS_REFERENCIAS = ("referencias", "imagen_referencia", "imagenes_referencia")
_CAMPOS_REUSO = ("reusar_de", "reusar_imagen")


@dataclass
class ResultadoImportacion:
    escenas: EscenasV2 | None
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    efectos_no_reconocidos: dict[int, list[str]] = field(default_factory=dict)


def _primero(d: dict[str, Any], claves: tuple[str, ...], defecto: Any = None) -> Any:
    for c in claves:
        if c in d and d[c] not in (None, ""):
            return d[c]
    return defecto


def efectos_desde_texto(texto: str | list | None) -> tuple[list[dict[str, Any]], list[str]]:
    if not texto:
        return [], []
    partes = texto if isinstance(texto, list) else re.split(r"[,;+\n]|\by\b", str(texto))
    efectos, sobrantes = [], []
    for parte in partes:
        if isinstance(parte, dict) and "efecto" in parte:
            efectos.append(parte)
            continue
        p = str(parte).strip()
        if not p:
            continue
        for patron, efecto in _EFECTOS_TEXTO:
            if re.search(patron, p, re.IGNORECASE):
                if efecto not in efectos:
                    efectos.append(dict(efecto))
                break
        else:
            sobrantes.append(p)
    return efectos, sobrantes


def inferir_intencion(narracion: str, seccion: str, indice: int, total: int,
                      seccion_anterior: str | None) -> tuple[str, int]:
    s = seccion.lower()
    if indice == total - 1 or "cierre" in s or "final" in s or "conclus" in s:
        return "cierre", 3
    if seccion_anterior is not None and seccion != seccion_anterior:
        return "transicion_de_seccion", 3
    for patron, intencion, intensidad in _INTENCIONES_TEXTO:
        if re.search(patron, narracion, re.IGNORECASE):
            return intencion, intensidad
    if "gancho" in s or "intro" in s or "hook" in s:
        return "gancho", 4
    return "explicacion", 2


def convertir(v1: dict[str, Any] | list[Any], estilo: Estilo, canal: str | None = None,
              video: str | None = None) -> ResultadoImportacion:
    datos = {"escenas": v1} if isinstance(v1, list) else dict(v1)
    crudas = datos.get("escenas") or datos.get("scenes") or []
    res = ResultadoImportacion(None)
    if not crudas:
        res.errores.append("El archivo v1 no tiene escenas")
        return res

    from .imagenes import prompts as _prompts

    personaje = (estilo.personaje_por_defecto or "").strip()
    refs_usadas = {str(r) for e in crudas for r in (_primero(e, _CAMPOS_REFERENCIAS) or [])}
    assets = []
    for a in datos.get("assets", []):
        aid = str(a.get("id"))
        archivo = a.get("archivo") or a.get("archivo_salida") or f"assets/{aid}.png"
        tipo_a = a.get("tipo") or ("personaje" if ("mascota" in aid or "personaje" in aid or archivo in refs_usadas)
                                   else "animal")
        # Los assets de v1 traen el prompt completo: se envía tal cual.
        assets.append({"id": aid, "tipo": tipo_a, "nombre": a.get("nombre"), "prompt": a.get("prompt"),
                       "prompt_literal": bool(a.get("prompt")), "archivo": archivo,
                       "quitar_fondo": bool(a.get("quitar_fondo", False))})
    # rutas -> ids: v1 referencia por ruta de archivo, v2 por id
    asset_por_archivo = {a["archivo"]: a["id"] for a in assets}
    escena_por_archivo = {str(_primero(e, _CAMPOS_ARCHIVO)): int(_primero(e, ("id", "numero", "escena", "n"), i + 1))
                          for i, e in enumerate(crudas) if _primero(e, _CAMPOS_ARCHIVO)}

    def _a_id(ref):
        if ref is None:
            return None
        r = str(ref)
        if r in asset_por_archivo:
            return asset_por_archivo[r]
        if r in escena_por_archivo:
            return escena_por_archivo[r]
        return int(r) if r.isdigit() else r

    escenas, anterior, t_acum = [], None, 0.0
    for i, e in enumerate(crudas):
        eid = int(_primero(e, ("id", "numero", "escena", "n"), i + 1))
        seccion = str(e.get("seccion") or anterior or "Sin sección")
        narr = str(_primero(e, _CAMPOS_NARRACION, "")).strip()
        vis_v1 = e.get("visual") if isinstance(e.get("visual"), dict) else {}
        fuente_vis = {**e, **vis_v1}

        tipo = _primero(fuente_vis, _CAMPOS_TIPO)
        prompt = _primero(fuente_vis, _CAMPOS_PROMPT)
        reusar = _a_id(_primero(fuente_vis, _CAMPOS_REUSO))
        accion = fuente_vis.get("accion") or ("reusar" if reusar is not None else "generar")
        if tipo is None and accion == "generar":
            res.errores.append(f"escena {eid}: sin tipo visual")
            tipo = ""
        tipo_estilo = estilo.tipo(tipo) if tipo else None
        # El prompt de v1 es completo. Si encaja EXACTO en la plantilla del estilo,
        # se guarda solo la descripción y el prompt sale del estilo; si no, se
        # envía tal cual (prompt_literal) y se avisa.
        literal = False
        if prompt and tipo_estilo:
            medio = _prompts.descomponer(prompt, tipo_estilo.plantilla_prompt, estilo, personaje)
            if medio is None:
                literal = True
                res.avisos.append(f"escena {eid}: el prompt no encaja en la plantilla de '{tipo}': se enviará tal cual")
            else:
                prompt = medio
        quitar = fuente_vis.get("quitar_fondo")
        if quitar is None:
            quitar = tipo_estilo.quitar_fondo if tipo_estilo else False

        intencion = e.get("intencion")
        intensidad = e.get("intensidad")
        if intencion is None:
            intencion, inten_inf = inferir_intencion(narr, seccion, i, len(crudas), anterior)
            intensidad = intensidad or inten_inf
        intensidad = int(intensidad or 2)

        efectos, sobrantes = efectos_desde_texto(_primero(e, _CAMPOS_EFECTOS))
        if sobrantes:
            res.efectos_no_reconocidos[eid] = sobrantes

        tiempo_v1 = e.get("tiempo") if isinstance(e.get("tiempo"), dict) else {}
        fuente_t = {**e, **tiempo_v1}
        dur = _primero(fuente_t, _CAMPOS_DURACION)
        ini = _primero(fuente_t, _CAMPOS_INICIO, t_acum)
        dur = float(dur) if dur is not None else None
        ini = float(ini)
        t_acum = ini + (dur or 0.0)

        revision = []
        if re.search(r"\d", narr):
            res.avisos.append(f"escena {eid}: números en dígitos en la narración (el TTS los lee mal)")
            revision.append("numeros_en_digitos")
        if re.search(r"dosis|mg\b|antiveneno|antídoto|tratamiento|medicamento", narr, re.IGNORECASE):
            revision.append("dato_medico")

        escenas.append({
            "id": eid, "seccion": seccion, "narracion": narr or "(vacía)",
            "intencion": intencion, "intensidad": max(1, min(5, intensidad)),
            "tiempo": {"estimado_inicio": ini, "estimado_duracion": dur,
                       "real_inicio": fuente_t.get("real_inicio"), "real_fin": fuente_t.get("real_fin")},
            "visual": {
                "accion": accion, "tipo": tipo or None, "prompt": prompt, "prompt_literal": literal,
                "archivo": _primero(fuente_vis, _CAMPOS_ARCHIVO) or f"imagenes/escena_{eid:03d}.png",
                "quitar_fondo": bool(quitar),
                "referencias": [str(_a_id(r)) for r in (_primero(fuente_vis, _CAMPOS_REFERENCIAS) or [])],
                "reusar_de": reusar,
            },
            "efectos_sugeridos": efectos,
            "palabra_clave": e.get("palabra_clave"),
            "pausa_despues_seg": float(e.get("pausa_despues_seg") or 0),
            "revision_humana": revision,
            "notas_edicion": str(e.get("notas_edicion") or ""),
        })
        if not narr:
            res.errores.append(f"escena {eid}: narración vacía")
        anterior = seccion

    doc = {
        "video": video or datos.get("video") or datos.get("titulo") or "Sin título",
        "canal": canal or datos.get("canal") or "sin-canal",
        "estilo": estilo.id,
        "idioma": datos.get("idioma", "es"),
        "relacion_aspecto": datos.get("relacion_aspecto", "16:9"),
        "assets": assets,
        "escenas": escenas,
    }
    try:
        res.escenas = EscenasV2.model_validate(doc)
    except Exception as ex:  # noqa: BLE001
        res.errores.append(f"esquema v2: {ex}")
        return res
    res.errores += res.escenas.errores_contra_estilo(estilo)
    inferidas = sum(1 for e in crudas if "intencion" not in e)
    if inferidas:
        res.avisos.append(f"{inferidas} intenciones inferidas por reglas; el Director de edición debe revisarlas")
    return res


def duracion_escenas(esc: EscenasV2, caracteres_por_segundo: float = 15.0) -> tuple[float, str]:
    """Duración del video: real si hay alineación; si no, estimada; si no, por caracteres."""
    fines = [e.tiempo.real_fin for e in esc.escenas if e.tiempo.real_fin is not None]
    if len(fines) == len(esc.escenas):
        return max(fines), "real (alineación)"
    if all(e.tiempo.estimado_duracion for e in esc.escenas):
        fin = max((e.tiempo.estimado_inicio or 0) + e.tiempo.estimado_duracion for e in esc.escenas)
        return fin, "estimada (escenas.json)"
    chars = sum(len(e.narracion) for e in esc.escenas)
    return chars / caracteres_por_segundo, "estimada (caracteres de narración)"
