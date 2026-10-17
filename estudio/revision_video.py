"""Revisión del video terminado antes de subirlo (17-10, pedido del dueño).

Una sola mirada de Claude a una hoja con 24 cuadros del MP4 final (con el minuto y lo que dice la voz en cada uno):
avisa de errores que se ven, como el personaje dentro de una escena en primera persona, un texto cortado, una imagen
que no corresponde a la voz o el villano a la vista antes de tiempo. Solo se corre con el botón (gasta del plan de
Claude, no pesos) y queda guardada en render/revision.json.
"""
from __future__ import annotations

from pathlib import Path

from . import claude_cli
from .config import escribir_json, leer_json

CUADROS = 24
COLUMNAS = 4


def _minuto(s: float) -> str:
    return f"{int(s // 60)}:{int(s % 60):02d}"


def momentos(duracion: float, n: int = CUADROS) -> list[float]:
    """Repartidos en todo el video, sin el primer ni el último medio segundo."""
    return [round(0.5 + (duracion - 1.0) * (i + 0.5) / n, 2) for i in range(n)]


def hoja(video: Path, destino: Path, n: int = CUADROS) -> list[float]:
    """La hoja de cuadros numerados (1 a n) con su minuto. Devuelve los segundos de cada cuadro."""
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    duracion = (cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) / fps
    if duracion <= 1:
        raise ValueError("El video está vacío o no se puede leer")
    ts = momentos(duracion, n)
    celdas = []
    for k, t in enumerate(ts, 1):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, cuadro = cap.read()
        c = cv2.resize(cuadro, (480, 270)) if ok else np.zeros((270, 480, 3), np.uint8)
        cv2.rectangle(c, (0, 0), (150, 34), (0, 0, 0), -1)
        cv2.putText(c, f"{k}  {_minuto(t)}", (8, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        celdas.append(c)
    cap.release()
    while len(celdas) % COLUMNAS:
        celdas.append(np.zeros_like(celdas[0]))
    filas = [np.hstack(celdas[i:i + COLUMNAS]) for i in range(0, len(celdas), COLUMNAS)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), np.vstack(filas), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return ts


def _voz_en(escenas, t: float) -> str:
    e = next((x for x in escenas if x.tiempo.real_inicio is not None and x.tiempo.real_inicio <= t
              < (x.tiempo.real_fin or 0)), None)
    return e.narracion if e else ""


def prompt(hoja_rel: str, ts: list[float], voces: list[str], titulo: str) -> str:
    lista = "\n".join(f"{k}. ({_minuto(t)}) {v[:120]}" for k, (t, v) in enumerate(zip(ts, voces), 1))
    return f"""Mira con la herramienta Read la imagen «{hoja_rel}»: {len(ts)} cuadros numerados del video terminado
«{titulo}», listo para subir a YouTube. Esto dice la voz en cada cuadro:
{lista}

Revísalo como un editor exigente y busca SOLO errores que se ven:
- en una escena en primera persona (solo se ven manos) aparece el personaje completo dentro de la imagen;
- un texto cortado, encimado, ilegible o con faltas;
- una imagen que no tiene nada que ver con lo que dice la voz (otro animal, otra cosa);
- el animal más peligroso (el último de la lista) se ve claro antes de su revelación;
- cuadros negros, vacíos, rotos o deformes (manos raras, caras deformes);
- algo que pueda dar problemas en YouTube (sangre, heridas gráficas, caras de personas reales, marcas o logos).
No opines de gustos ni de estilo. Si un cuadro está bien, no lo menciones.

Responde SOLO un JSON: {{"problemas": [{{"cuadro": 3, "minuto": "0:42", "que": "en español, corto y claro",
"gravedad": "alta" | "media"}}], "resumen": "una frase para el dueño"}}"""


def revisar(carpeta, ejecutar=claude_cli.ejecutar, avisar=print) -> dict:
    """Arma la hoja, le pide a Claude que la mire y guarda render/revision.json."""
    video = carpeta.ruta / "render" / "final.mp4"
    if not video.exists():
        raise FileNotFoundError("Primero haz el video")
    avisar("Sacando cuadros del video…")
    destino = carpeta.ruta / "render" / "revision_cuadros.jpg"
    ts = hoja(video, destino)
    esc = carpeta.cargar_escenas()
    voces = [_voz_en(esc.escenas, t) for t in ts]
    avisar("Claude está mirando el video…")
    texto, _ = ejecutar(prompt(str(destino.relative_to(carpeta.ruta)), ts, voces, esc.video),
                        cwd=carpeta.ruta, herramientas=["Read"])
    datos = claude_cli.extraer_json(texto)
    problemas = [p for p in (datos.get("problemas") or []) if isinstance(p, dict) and p.get("que")]
    r = {"problemas": problemas, "resumen": str(datos.get("resumen") or ""), "cuadros": len(ts)}
    escribir_json(carpeta.ruta / "render" / "revision.json", r)
    avisar(f"Revisión lista: {len(problemas)} cosa(s) para mirar" if problemas else "Revisión lista: todo bien")
    return r


def leer(carpeta) -> dict | None:
    ruta = carpeta.ruta / "render" / "revision.json"
    return leer_json(ruta) if ruta.exists() else None
