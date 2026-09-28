"""Paso 4: control de calidad con Claude (visión) antes de mostrar la miniatura.

Primero van los controles que el código mide solo (gratis): que el sujeto ocupe su
espacio en la imagen generada y que el recorte no traiga restos de fondo. Luego Claude
mira la miniatura final y una hoja con los 6 sujetos y dice cuál falla y cómo arreglarlo.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .. import claude_cli
from .plan import Plan
from .recorte import restos_de_fondo

MIN_OCUPACION = 0.30        # el sujeto debe llenar al menos ~1/3 de la imagen generada
MAX_RESTOS = 0.10


def medir(carpeta: Path, plan: Plan) -> dict[int, list[str]]:
    from .composicion import cargar_recorte

    problemas: dict[int, list[str]] = {}
    for i, c in enumerate(plan.cells):
        if not c.archivo or not (carpeta / c.archivo).exists():
            problemas[i] = ["falta la imagen"]
            continue
        if plan.hook_mode == "scene":
            continue                              # la escena va completa: no hay fondo blanco que medir
        img = np.asarray(Image.open(carpeta / c.archivo).convert("L").resize((256, 256)))
        ys, xs = np.nonzero(img < 235)
        ocupa = ((xs.max() - xs.min()) * (ys.max() - ys.min()) / 256 ** 2) if len(xs) else 0
        if ocupa < MIN_OCUPACION:
            problemas.setdefault(i, []).append(f"el sujeto es pequeño en su imagen (ocupa {ocupa:.0%})")
        rec = cargar_recorte(carpeta, c.archivo)
        if restos_de_fondo(rec) > MAX_RESTOS:
            problemas.setdefault(i, []).append("el recorte trae restos del fondo blanco")
    return problemas


def hoja(carpeta: Path, plan: Plan) -> Path:
    """Los 6 sujetos generados, numerados del 1 al 6, para que Claude los mire de un vistazo."""
    from ..render import _fuente

    lado = 300
    lienzo = Image.new("RGB", (3 * lado + 40, 2 * (lado + 36) + 20), (230, 230, 230))
    d = ImageDraw.Draw(lienzo)
    for i, c in enumerate(plan.cells):
        x, y = 10 + (i % 3) * (lado + 10), 10 + (i // 3) * (lado + 36)
        if c.archivo and (carpeta / c.archivo).exists():
            im = Image.open(carpeta / c.archivo).convert("RGB")
            im.thumbnail((lado, lado))
            lienzo.paste(im, (x, y))
        d.text((x + 4, y + lado + 4), f"#{i + 1} {c.name}{' (protagonista)' if c.is_hero else ''}", fill=(0, 0, 0),
               font=_fuente(22))
    ruta = carpeta / "qa_hoja.png"
    lienzo.save(ruta)
    return ruta


def revisar(carpeta: Path, plan: Plan, final: Path, ejecutar=claude_cli.ejecutar, medidas: dict | None = None) -> dict:
    medidos = medir(carpeta, plan)
    h = hoja(carpeta, plan)
    lista = "\n".join(f"#{i + 1} {c.name} · etiqueta «{c.label}»" for i, c in enumerate(plan.cells))
    gancho = f"\n- ¿Se ve el gancho visual «{plan.hook_visual}» en los 6?" if plan.hook_mode == "scene" else ""
    texto, _ = ejecutar(
        f"Revisa una miniatura de YouTube de formato escala. Mira con la herramienta Read la miniatura final "
        f"{final.relative_to(carpeta).as_posix()} y la hoja de sujetos {h.relative_to(carpeta).as_posix()}.\n"
        f"Sujetos:\n{lista}\nEscala: {plan.scale_type}. Texto del protagonista: «{plan.hero_text}».\n"
        "Para CADA sujeto responde:\n- ¿Es grande y ocupa casi todo su espacio?\n- ¿Es reconocible como ese animal "
        "(ej. un candirú no debe parecer un banco de sardinas)?\n- ¿Tiene pose o expresión amenazante (salvo el #6, "
        "que debe ser tierno, inofensivo o sorprendente)?\n- ¿El recorte quedó limpio (sin restos de fondo ni bordes "
        f"blancos raros)?\n- ¿Trae texto, marcos o bordes (no debe)?{gancho}\nY en conjunto: ¿el #1 es claramente "
        "el más llamativo? ¿El estilo es coherente entre los 6? ¿Hay DOS sujetos con silueta y color parecidos "
        "(ej. dos peces plateados alargados)? Si los hay, ponlos en «parecidos».\n"
        "Si un sujeto falla, da en «arreglo» una instrucción corta EN INGLÉS para regenerarlo.\n"
        'Responde SOLO un JSON: {"sujetos": [{"numero": 1, "ok": true, "problemas": [], "arreglo": ""}], '
        '"protagonista_destaca": true, "estilo_coherente": true, "parecidos": [[2, 5]], "resumen": "<una frase en español>"}',
        cwd=carpeta, herramientas=["Read"])
    datos = claude_cli.extraer_json(texto) or {}
    sujetos = {}
    for s in datos.get("sujetos") or []:
        try:
            i = int(s["numero"]) - 1
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= i < 6:
            sujetos[i] = {"ok": bool(s.get("ok", True)), "problemas": [str(p)[:160] for p in s.get("problemas") or []],
                          "arreglo": str(s.get("arreglo") or "")[:300]}
    for i, probs in medidos.items():
        s = sujetos.setdefault(i, {"ok": True, "problemas": [], "arreglo": ""})
        s["ok"] = False
        s["problemas"] = probs + s["problemas"]
        if not s["arreglo"]:
            s["arreglo"] = "Make the subject much bigger so it fills almost the whole frame."
    for par in datos.get("parecidos") or []:
        try:
            a, b = sorted(int(x) - 1 for x in par)[:2]
        except (TypeError, ValueError):
            continue
        cual = b if b != 0 else a                  # se cambia el que no es protagonista
        if 0 <= cual < 6:
            s = sujetos.setdefault(cual, {"ok": True, "problemas": [], "arreglo": ""})
            s["ok"] = False
            s["problemas"].append(f"se parece mucho al #{(a if cual == b else b) + 1} en silueta y color")
            s["arreglo"] = (s["arreglo"] + " " if s["arreglo"] else "") + \
                "Use a clearly different color palette and a different pose so it cannot be confused with the others."
    if datos.get("protagonista_destaca") is False and 0 in sujetos:
        sujetos[0]["ok"] = False
        sujetos[0]["problemas"].append("el protagonista no es el más llamativo")
        sujetos[0]["arreglo"] = sujetos[0]["arreglo"] or "Make it more dramatic and threatening, mouth open, facing camera."
    return {"sujetos": {str(k): v for k, v in sorted(sujetos.items())},
            "protagonista_destaca": datos.get("protagonista_destaca"),
            "estilo_coherente": datos.get("estilo_coherente"), "resumen": str(datos.get("resumen") or "")[:300],
            "medidas": medidas or {},
            "claude_respondio": bool(datos)}


def ubicar_herida(carpeta: Path, archivo: str, ejecutar=claude_cli.ejecutar) -> list[float] | None:
    """Caja (0..1) de la herida o mordida del protagonista, para que el código la pixele."""
    texto, _ = ejecutar(
        f"Mira la imagen {archivo} con la herramienta Read. Ubica la herida, mordida o marca de sangre. Responde SOLO un "
        'JSON: {"caja": [x0, y0, x1, y1]} con valores de 0 a 1 (esquina superior izquierda y inferior derecha), '
        'un poco más grande que la herida; o {"caja": null} si no hay ninguna.', cwd=carpeta, herramientas=["Read"])
    caja = (claude_cli.extraer_json(texto) or {}).get("caja")
    try:
        x0, y0, x1, y1 = (min(max(float(v), 0.0), 1.0) for v in caja)
    except (TypeError, ValueError):
        return None
    return [x0, y0, x1, y1] if x1 - x0 > 0.02 and y1 - y0 > 0.02 else None
