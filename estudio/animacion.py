"""Clips animados del presentador (reacciones de ~2 s en giro, revelación y humor).

Cada pose aprobada se anima UNA vez con un modelo de imagen a video de Together
(la foto es el primer cuadro, así la persona, la ropa y el cuarto no cambian) y el
clip queda en `estilos/<estilo>/assets/presentador/clips/`. Todos los videos lo
reutilizan gratis. El gasto va al mismo libro de costos del presentador, con freno.
"""
from __future__ import annotations

import base64
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import ConfigCostos, clave_api, escribir_json, formato_cop, leer_json
from .costos import LibroCostos
from .poses import carpeta_presentador

URL = "https://api.together.xyz/v2/videos"
# precio de lista de Together por clip de 5 s (sin audio), en dólares
MODELOS = {"Wan-AI/wan2.7-i2v": 0.10, "kwaivgI/kling-2.1-standard": 0.1848}
# qué se mueve en cada pose: gesto corto y natural, sin hablar ni salir de cuadro
MOVIMIENTO = {
    "sorpresa": "he reacts with genuine surprise, eyebrows rise, he leans slightly toward the camera and blinks",
    "shock": "he keeps both hands on his head, shakes his head slowly in disbelief and exhales",
    "serio": "he nods slowly with a serious look, arms crossed, a subtle frown",
    "susurro": "he leans in and whispers a secret to the camera behind his hand, glancing to the side",
    "risa": "he bursts out laughing naturally, shoulders shaking, hand on his chest",
    "alivio": "he exhales in relief, shoulders drop, a small smile appears",
    "senalando": "he points to the right side of the frame and looks there, intrigued, then back to the camera",
    "pensativo": "he strokes his chin, eyes up and to the side, thinking",
    "alarmado": "he pulls back in alarm raising both palms toward the camera",
}
BASE = ("Static locked-off camera, realistic subtle motion, the same man, same clothes and same room as the image, "
        "natural lighting, no camera movement, no text, no new objects, no speech. ")


def _cabeceras() -> dict:
    clave = clave_api("TOGETHER_API_KEY")
    return {"Authorization": f"Bearer {clave}"} if clave else {}


def animar(estilo_id: str, pose: str, modelo: str = "Wan-AI/wan2.7-i2v", *, permiso: bool = False,
           segundos: int = 5, avisar=print, sesion=requests) -> Path:
    carpeta = carpeta_presentador(estilo_id)
    foto = carpeta / f"{pose}.png"
    if not foto.exists():
        raise FileNotFoundError(f"no existe la pose «{pose}»")
    destino = carpeta / "clips" / f"{pose}__{modelo.split('/')[-1]}.mp4"
    if destino.exists():
        return destino
    config = ConfigCostos.cargar()
    libro = LibroCostos(carpeta, config)
    precio = MODELOS.get(modelo, 0.3) * max(1, segundos / 5)
    libro.autorizar(precio, permiso=permiso)
    datos = "data:image/png;base64," + base64.b64encode(foto.read_bytes()).decode()
    cuerpo = {"model": modelo, "prompt": BASE + MOVIMIENTO.get(pose, "subtle natural reaction"),
              "frame_images": [{"input_image": datos, "frame": "first"}], "seconds": str(segundos)}
    r = sesion.post(URL, json=cuerpo, headers=_cabeceras(), timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"Together no aceptó el video: HTTP {r.status_code} {r.text[:300]}")
    trabajo = r.json()["id"]
    avisar(f"Animando «{pose}» con {modelo} (trabajo {trabajo})…")
    for _ in range(180):                               # hasta 30 min
        time.sleep(10)
        d = sesion.get(f"{URL}/{trabajo}", headers=_cabeceras(), timeout=60).json()
        if d.get("status") in ("completed", "succeeded"):
            break
        if d.get("status") in ("failed", "cancelled", "error"):
            raise RuntimeError(f"el video falló: {d.get('error') or d}")
    else:
        raise TimeoutError(f"el video {trabajo} no terminó en 30 minutos")
    salida = d.get("outputs") or d.get("output") or {}
    url = salida.get("video_url") or salida.get("url") or d.get("video_url")
    if not url:
        raise RuntimeError(f"el video terminó pero no trae enlace: {d}")
    costo = float(salida.get("cost") or d.get("cost") or precio)
    # el enlace corto sale en api.together.ai; el mismo camino sirve en api.together.xyz
    url = url.replace("://api.together.ai/", "://api.together.xyz/")
    video = sesion.get(url, timeout=300)
    video.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(video.content)
    libro.registrar(modulo="presentador_animado", proveedor="together", modelo=modelo,
                    unidades={"segundos": segundos}, costo_usd=costo, detalle=pose)
    ruta_idx = carpeta / "clips" / "clips.json"
    idx = leer_json(ruta_idx) if ruta_idx.exists() else {}
    idx[destino.name] = {"pose": pose, "modelo": modelo, "segundos": segundos, "costo_usd": costo,
                         "trabajo": trabajo, "generado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    escribir_json(ruta_idx, idx)
    avisar(f"  «{pose}» animada · {formato_cop(config.a_cop(costo))}")
    return destino
