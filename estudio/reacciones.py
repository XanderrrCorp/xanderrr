"""Dónde reacciona el presentador: lo decide Claude leyendo el guion completo.

Una persona real reacciona DESPUÉS de que la frase cae (el dato que asusta, el
remate del chiste, la revelación), no al empezar la escena. Claude elige esos
momentos, la reacción que corresponde y explica por qué; el Director de edición
solo los acomoda en el tiempo respetando los límites del estilo (máximo por video,
separación mínima, máximo por reacción). Si Claude no está, se usan las reglas por
intención de siempre.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import claude_cli
from .config import escribir_json, leer_json
from .estilos import cargar_estilo


def _instruccion(escenas: list[dict], poses: dict[str, str], pr) -> str:
    lineas = "\n".join(f"{e['id']} [{e['intencion']}] {e['narracion']}" for e in escenas)
    catalogo = "\n".join(f"- {p}: {uso}" for p, uso in poses.items())
    return (
        "Eres el editor de un canal de YouTube de animales peligrosos. En el video, de vez en cuando se corta "
        f"{pr.duracion_reaccion_seg:.0f} segundos a un presentador que REACCIONA (no habla; la voz sigue) a lo que se "
        "acaba de decir, como haría una persona real viendo el video.\n\n"
        f"Reacciones disponibles:\n{catalogo}\n\n"
        f"Guion (número de escena, [intención], narración):\n{lineas}\n\n"
        f"Elige como máximo {pr.maximo_por_video} momentos donde una persona de verdad reaccionaría fuerte: justo "
        "después de un dato que da miedo o asco, de una revelación, del remate de algo chistoso o de un giro que nadie "
        "espera. La reacción debe corresponder exactamente a lo que se dijo (no pongas risa en algo grave de salud). "
        f"Reglas: al menos {pr.separacion_minima_seg:.0f} segundos de video entre una y otra (cuenta unas 2,5 escenas "
        f"por cada 10 segundos), nunca en escenas seguidas, cada reacción como máximo {pr.maximo_por_pose} veces, nunca "
        "la misma dos veces seguidas, y repártelas en todo el video, con la más fuerte en la revelación del villano.\n"
        "Responde SOLO un JSON así: "
        '{"reacciones": [{"escena": <número de la escena cuya frase provoca la reacción>, "pose": "<reacción>", '
        '"razon": "<por qué reaccionaría aquí, en una frase>"}]}'
    )


def elegir_reacciones(carpeta: Path, ejecutar=claude_cli.ejecutar, avisar=print) -> list[dict]:
    """Guarda en direccion.json["reacciones"] la lista elegida por Claude (una vez por guion)."""
    ruta = carpeta / "direccion.json"
    direccion = leer_json(ruta) if ruta.exists() else {}
    datos = leer_json(carpeta / "escenas.json")
    firma = hashlib.sha256("\n".join(e["narracion"] for e in datos["escenas"]).encode()).hexdigest()[:16]
    if direccion.get("reacciones_firma") == firma and "reacciones" in direccion:
        return direccion["reacciones"]
    proyecto = leer_json(carpeta / "proyecto.json")
    pr = cargar_estilo(proyecto["estilo"]).presentador
    if pr is None:
        return []
    poses = {p.id: p.uso for p in pr.poses if (carpeta / "assets" / "presentador" / f"{p.id}.mp4").exists()}
    if not poses:
        return []
    avisar("Claude está leyendo el guion para decidir dónde reacciona el presentador…")
    texto, _ = ejecutar(_instruccion(datos["escenas"], poses, pr), cwd=carpeta)
    salida = claude_cli.extraer_json(texto) or {}
    ids = {e["id"] for e in datos["escenas"]}
    elegidas = [{"escena": int(r["escena"]), "pose": r["pose"], "razon": str(r.get("razon", ""))[:200]}
                for r in salida.get("reacciones", [])
                if isinstance(r, dict) and str(r.get("escena", "")).isdigit() and int(r["escena"]) in ids
                and r.get("pose") in poses]
    direccion["reacciones"], direccion["reacciones_firma"] = elegidas, firma
    escribir_json(ruta, direccion)
    return elegidas
