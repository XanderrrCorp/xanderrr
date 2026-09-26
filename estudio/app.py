"""La página de Xandart: un servidor local (solo en este computador) que maneja
los pasos del video. Se abre con `python -m estudio.app` o con el acceso directo."""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from . import claude_cli, pipeline
from .config import RAIZ, _leer_env, clave_api, ruta_proyectos
from .proyecto import CarpetaProyecto

WEB = Path(__file__).parent / "web"
PUERTO = int(os.environ.get("XANDART_PUERTO", "8030"))
app = FastAPI(title="Xandart")


def _proyecto(slug: str) -> CarpetaProyecto:
    try:
        return CarpetaProyecto.abrir(slug)
    except FileNotFoundError as ex:
        raise HTTPException(404, "Ese video no existe") from ex


# ------------------------------------------------------------------ página

@app.get("/", response_class=HTMLResponse)
def portada():
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/web/{nombre}")
def recurso(nombre: str):
    ruta = (WEB / nombre).resolve()
    if ruta.parent != WEB.resolve() or not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta)


@app.get("/archivos/{slug}/{ruta:path}")
def archivo(slug: str, ruta: str, descargar: bool = False):
    base = _proyecto(slug).ruta.resolve()
    destino = (base / ruta).resolve()
    if base not in destino.parents or not destino.exists():
        raise HTTPException(404)
    nombre = None
    if descargar:
        nombre = f"{pipeline.slugificar(_proyecto(slug).cargar().titulo)[:60]}{destino.suffix}"
    return FileResponse(destino, filename=nombre)


# ------------------------------------------------------------------ estado y claves

@app.get("/api/estado")
def estado():
    videos = []
    raiz = ruta_proyectos()
    if raiz.exists():
        for d in sorted(raiz.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if (d / "proyecto.json").exists():
                try:
                    r = pipeline.resumen(CarpetaProyecto(d))
                    videos.append({k: r[k] for k in ("slug", "titulo", "minutos", "pasos", "costo", "video")})
                except Exception:  # noqa: BLE001 — un proyecto roto no tumba la lista
                    continue
    return {"claves": {"together": bool(clave_api("TOGETHER_API_KEY")), "minimax": bool(clave_api("MINIMAX_API_KEY"))},
            "claude": bool(claude_cli.ejecutable()), "videos": videos,
            "carpeta_videos": str(pipeline.carpeta_videos())}


class Claves(BaseModel):
    together: str | None = None
    minimax: str | None = None


@app.post("/api/claves")
def guardar_claves(c: Claves):
    valores = _leer_env()
    if c.together and c.together.strip():
        valores["TOGETHER_API_KEY"] = c.together.strip()
    if c.minimax and c.minimax.strip():
        valores["MINIMAX_API_KEY"] = c.minimax.strip()
    (RAIZ / ".env").write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
    return estado()


@app.post("/api/probar/{servicio}")
def probar(servicio: str):
    import requests

    try:
        if servicio == "together":
            r = requests.get("https://api.together.xyz/v1/models", timeout=30,
                             headers={"Authorization": f"Bearer {clave_api('TOGETHER_API_KEY')}"})
            return {"ok": r.status_code == 200, "detalle": "funciona" if r.status_code == 200 else f"HTTP {r.status_code}"}
        if servicio == "minimax":
            from .config import ConfigCostos, leer_config
            from .voz import VozMiniMax

            VozMiniMax(ConfigCostos.cargar(), leer_config("proveedores.json")["voz"]).sintetizar("Hola.")
            return {"ok": True, "detalle": "funciona"}
        if servicio == "claude":
            texto, _ = claude_cli.ejecutar("Responde solo con la palabra: listo", tiempo_max_s=120)
            return {"ok": "listo" in texto.lower(), "detalle": texto[:80]}
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "detalle": str(ex)[:300]}
    raise HTTPException(404)


@app.post("/api/claude/sesion")
def sesion_claude():
    """Abre una ventana con Claude para iniciar sesión (solo la primera vez)."""
    exe = claude_cli.ejecutable()
    if not exe:
        raise HTTPException(400, "Claude no está instalado: corre de nuevo el instalador")
    if os.name == "nt":
        subprocess.Popen(["cmd", "/c", "start", "Claude", "cmd", "/k", exe])
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", exe])
    return {"ok": True}


# ------------------------------------------------------------------ videos

class Nuevo(BaseModel):
    tema: str = Field(min_length=3)
    giro: str = ""
    villano: str = ""
    minutos: float = Field(9, ge=4, le=11)
    notas: str = ""


@app.post("/api/videos")
def nuevo(n: Nuevo):
    c = pipeline.crear_video(n.tema, n.giro, n.villano, n.minutos, n.notas)
    pipeline.lanzar(c.ruta.name, "guion", lambda t: pipeline.paso_guion(c, t))
    return pipeline.resumen(c)


@app.get("/api/videos/{slug}")
def ver(slug: str):
    return pipeline.resumen(_proyecto(slug))


def _lanzar(slug, paso, f):
    try:
        pipeline.lanzar(slug, paso, f)
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return pipeline.resumen(_proyecto(slug))


@app.post("/api/videos/{slug}/guion")
def rehacer_guion(slug: str):
    c = _proyecto(slug)
    return _lanzar(slug, "guion", lambda t: pipeline.paso_guion(c, t))


class Texto(BaseModel):
    narracion: str = Field(min_length=1)


@app.put("/api/videos/{slug}/escenas/{escena_id}")
def editar_escena(slug: str, escena_id: int, cuerpo: Texto):
    c = _proyecto(slug)
    esc = c.cargar_escenas()
    e = next((x for x in esc.escenas if x.id == escena_id), None)
    if not e:
        raise HTTPException(404)
    e.narracion = cuerpo.narracion.strip()
    c.guardar_escenas(esc)
    return pipeline.resumen(c)


class Permiso(BaseModel):
    permiso: bool = False


@app.post("/api/videos/{slug}/imagenes")
def imagenes(slug: str, p: Permiso = Permiso()):
    c = _proyecto(slug)
    return _lanzar(slug, "imagenes", lambda t: pipeline.paso_imagenes(c, t, permiso=p.permiso))


class Instruccion(BaseModel):
    instruccion: str = ""


@app.post("/api/videos/{slug}/escenas/{escena_id}/regenerar")
def regenerar(slug: str, escena_id: int, cuerpo: Instruccion):
    c = _proyecto(slug)
    return _lanzar(slug, "regenerar", lambda t: pipeline.regenerar_imagen(c, t, escena_id, cuerpo.instruccion))


@app.post("/api/videos/{slug}/video")
def video(slug: str, p: Permiso = Permiso()):
    c = _proyecto(slug)
    return _lanzar(slug, "video", lambda t: pipeline.paso_video(c, t, permiso=p.permiso))


@app.post("/api/abrir-carpeta")
def abrir_carpeta():
    destino = pipeline.carpeta_videos()
    if os.name == "nt":
        os.startfile(destino)  # type: ignore[attr-defined]
    return {"carpeta": str(destino)}


def _ya_abierto() -> bool:
    import socket

    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PUERTO)) == 0


def main():
    import uvicorn

    if sys.stdout is None or sys.stderr is None:  # pythonw (acceso directo): sin consola
        (RAIZ / "logs").mkdir(exist_ok=True)
        salida = open(RAIZ / "logs" / "xandart.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or salida
        sys.stderr = sys.stderr or salida
    if _ya_abierto():  # segundo clic en el acceso directo: solo abre la página
        webbrowser.open(f"http://127.0.0.1:{PUERTO}/")
        return
    if "--sin-navegador" not in sys.argv:
        import threading

        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}/")).start()
    uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
