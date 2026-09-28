"""Shorts verticales (9:16) sacados de un video largo ya hecho, casi gratis.

Cada nivel del video largo alcanza para un short de unos 40 segundos:
1. Claude reescribe ese nivel como short: gancho en el primer segundo, un dato por
   frase, sin «suscríbete» al minuto, y un final que empalma con el inicio (bucle).
   Cada frase reutiliza una imagen que ya salió en el video largo: no se genera nada.
2. Se crea un proyecto nuevo con relacion_aspecto 9:16 que copia las imágenes, los
   focos y los clips del presentador del video largo.
3. Voz, edición y render salen por el mismo camino que el video largo; el render
   arma el cuadro vertical (ver render._vertical).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import claude_cli
from .config import escribir_json, leer_json
from .esquemas import INTENCIONES
from .proyecto import CarpetaProyecto, slugificar

SEGUNDOS_OBJETIVO = 40
PALABRAS_OBJETIVO = (125, 155)          # a ~3,8 palabras por segundo con la voz a 1,3
COPIAR = ("assets", "imagenes")


def _escenas_de_nivel(datos: dict, nivel: int) -> list[dict]:
    nombre = next(n["nombre"] for n in datos["niveles"] if n["numero"] == nivel)
    tira = {n["asset"] for n in datos["niveles"]}
    return [e for e in datos["escenas"] if nombre.lower() in e["seccion"].lower()
            and e["visual"]["accion"] == "reusar" and e["visual"].get("reusar_de") not in tira]


def elegir_nivel(datos: dict) -> int:
    """Por defecto el villano: es el nivel con el dato más fuerte del video."""
    villano = next((n["numero"] for n in datos["niveles"] if n.get("villano")), None)
    return villano or datos["niveles"][-1]["numero"]


def instruccion(nivel: dict, escenas: list[dict], titulo_largo: str, canal: str = "") -> str:
    lineas = "\n".join(f"{e['id']} [{e['intencion']}] {e['narracion']}" for e in escenas)
    return (
        f"Eres guionista de YouTube Shorts del canal «{canal or 'este canal'}», en español "
        "latino, tono cercano y con ritmo. Vas a convertir este tramo de un video largo "
        f"(«{titulo_largo}»), sobre «{nivel['nombre']}», en UN short vertical de unos {SEGUNDOS_OBJETIVO} "
        "segundos.\n\n"
        f"Tramo del video largo (número de escena, [intención], narración):\n{lineas}\n\n"
        "Reglas del short:\n"
        "- La primera frase es el gancho: un dato o una pregunta que asusta o da curiosidad en menos de 2 "
        "segundos. Nada de «hola», «hoy veremos» ni presentaciones.\n"
        f"- Entre {PALABRAS_OBJETIVO[0]} y {PALABRAS_OBJETIVO[1]} palabras en total, frases cortas de 6 a 14 "
        "palabras, una por escena, cada una con un dato nuevo.\n"
        "- Solo datos que ya están en el tramo (no inventes cifras). Temas de salud: sin dosis ni tratamientos.\n"
        "- Sin «suscríbete» ni llamados a la acción.\n"
        "- La última frase empalma con la primera para que el short se vea en bucle.\n"
        "- Cada escena reutiliza la imagen de UNA escena del tramo (campo «fuente»): elige la que muestra lo que "
        "dice la frase y no repitas la misma imagen en escenas seguidas.\n"
        f"- «intencion» es una de: {', '.join(INTENCIONES)}.\n"
        "- «palabra_clave» es UNA palabra de la frase, escrita igual, que sale en pantalla como etiqueta "
        "(ej.: «anestésico», «corazón»).\n"
        "- «titulo» es el texto fijo arriba del short: 2 a 6 palabras, en mayúsculas, que den ganas de verlo "
        "hasta el final (no repitas el gancho palabra por palabra).\n"
        "Responde SOLO un JSON así: "
        '{"titulo": "<texto de arriba>", "titulo_youtube": "<título para subirlo, con #shorts>", '
        '"escenas": [{"fuente": <número de escena del tramo>, "narracion": "<frase>", "intencion": "<intención>", "palabra_clave": "<la palabra más fuerte de la frase, tal cual>"}]}'
    )


def _palabras(escenas: list[dict]) -> int:
    return sum(len(e["narracion"].split()) for e in escenas)


def crear_short(largo: Path, base: Path, nivel: int | None = None, ejecutar=claude_cli.ejecutar,
                avisar=print) -> CarpetaProyecto:
    """Proyecto de short (9:16) a partir de un nivel del video largo. Solo usa Claude
    (suscripción) y archivos que ya existen: la voz se paga después, al producirlo."""
    datos = leer_json(largo / "escenas.json")
    proyecto_largo = leer_json(largo / "proyecto.json")
    nivel = nivel or elegir_nivel(datos)
    info = next(n for n in datos["niveles"] if n["numero"] == nivel)
    tramo = _escenas_de_nivel(datos, nivel)
    if not tramo:
        raise ValueError(f"el nivel {nivel} no tiene escenas en el video largo")
    avisar(f"Claude está escribiendo el short de «{info['nombre']}»…")
    por_id = {e["id"]: e for e in tramo}
    guion = {}
    for _ in range(2):
        from .plataforma.consultas import nombre_canal

        texto, _uso = ejecutar(instruccion(info, tramo, proyecto_largo["titulo"],
                                           nombre_canal(proyecto_largo.get("canal", ""))), cwd=largo)
        guion = claude_cli.extraer_json(texto) or {}
        filas = [f for f in guion.get("escenas", []) if isinstance(f, dict) and str(f.get("narracion", "")).strip()
                 and str(f.get("fuente", "")).isdigit() and int(f["fuente"]) in por_id]
        if len(filas) >= 6 and PALABRAS_OBJETIVO[0] * 0.85 <= _palabras(filas) <= PALABRAS_OBJETIVO[1] * 1.15:
            break
    else:
        if not filas:
            raise claude_cli.ErrorClaude("Claude no devolvió un guion de short utilizable")

    titulo = str(guion.get("titulo") or info["nombre"]).strip().upper()[:40]
    titulo_yt = str(guion.get("titulo_youtube") or f"{info['nombre']} #shorts").strip()[:100]
    destino = base / slugificar(f"short {info['nombre']} {proyecto_largo['slug']}")[:60]
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    for nombre in COPIAR:
        if (largo / nombre).exists():
            shutil.copytree(largo / nombre, destino / nombre)

    escenas, focos_largo = [], (leer_json(largo / "direccion.json").get("focos") or {}) \
        if (largo / "direccion.json").exists() else {}
    focos = {}
    for k, f in enumerate(filas, 1):
        fuente = por_id[int(f["fuente"])]
        e = json.loads(json.dumps(fuente))
        intencion = f.get("intencion") if f.get("intencion") in INTENCIONES else fuente["intencion"]
        e.update({"id": k, "seccion": "Gancho" if k == 1 else ("Cierre" if k == len(filas) else "Short"),
                  "narracion": str(f["narracion"]).strip(), "intencion": intencion, "efectos_sugeridos": [],
                  "pausa_despues_seg": 0.0, "notas_edicion": f"imagen de la escena {fuente['id']} del video largo",
                  "tiempo": {}})
        clave = str(f.get("palabra_clave") or fuente.get("palabra_clave") or "").strip()
        e["palabra_clave"] = clave if clave and clave.lower() in e["narracion"].lower() else None
        e["visual"] = _resolver_visual(fuente, {x["id"]: x for x in datos["escenas"]})
        foco = focos_largo.get(str(fuente["id"]))
        if foco:
            focos[str(k)] = foco
        escenas.append(e)

    nuevas = dict(datos, video=destino.name, relacion_aspecto="9:16", niveles=[], escenas=escenas)
    escribir_json(destino / "escenas.json", nuevas)
    escribir_json(destino / "direccion.json", {"focos": focos, "focos_revisados": list(range(1, len(escenas) + 1)),
                                               "textos": {}, "pixelar": {},
                                               "short": {"titulo": titulo, "titulo_youtube": titulo_yt,
                                                         "nivel": nivel, "video_largo": proyecto_largo["slug"]}})
    p = dict(proyecto_largo, slug=destino.name, titulo=titulo_yt, duracion_objetivo_seg=SEGUNDOS_OBJETIVO,
             pasos={}, notas=[f"Short sacado del nivel {nivel} de «{proyecto_largo['titulo']}»"])
    escribir_json(destino / "proyecto.json", p)
    c = CarpetaProyecto(destino)
    c.cargar_escenas()                                        # valida el esquema antes de gastar en voz
    for paso in ("guionista", "assets"):
        c.marcar(paso, "completo")
    (destino / "guion.md").write_text(f"# {titulo_yt}\n\nArriba: {titulo}\n\n" +
                                      "\n".join(e["narracion"] for e in escenas) + "\n", encoding="utf-8")
    avisar(f"Short listo para producir: {len(escenas)} escenas, {_palabras(escenas)} palabras")
    return c


def _resolver_visual(escena: dict, por_id: dict) -> dict:
    """Sigue la cadena de reusos del video largo (escena que reusa otra escena) hasta la
    imagen del catálogo: en el short los números de escena ya no son los mismos."""
    vistas, actual = set(), escena
    while actual["visual"]["accion"] == "reusar" and isinstance(actual["visual"].get("reusar_de"), int) \
            and actual["id"] not in vistas:
        vistas.add(actual["id"])
        actual = por_id[actual["visual"]["reusar_de"]]
    return json.loads(json.dumps(actual["visual"]))
