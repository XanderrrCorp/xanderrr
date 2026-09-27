"""La página de Xandart: un servidor local (solo en este computador) que maneja
los pasos del video. Se abre con `python -m estudio.app` o con el acceso directo."""
from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from . import claude_cli, pipeline
from .config import RAIZ, _leer_env, clave_api, ruta_proyectos
from .proyecto import CarpetaProyecto

WEB = Path(__file__).parent / "web"


def _version() -> str:
    """Huella del código instalado: si cambia (se actualizó), el Xandart viejo que siga
    abierto se cierra y se abre el nuevo."""
    import hashlib

    h = hashlib.sha256()
    base = Path(__file__).parent
    for f in sorted(list(base.rglob("*.py")) + list(WEB.glob("*"))):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


VERSION = _version()
PUERTO = int(os.environ.get("XANDART_PUERTO", "8030"))
app = FastAPI(title="Xandart")


def _proyecto(slug: str) -> CarpetaProyecto:
    try:
        return CarpetaProyecto.abrir(slug)
    except FileNotFoundError as ex:
        raise HTTPException(404, "Ese video no existe") from ex


# ------------------------------------------------------------------ página

# la página nunca se guarda en la memoria del navegador: tras actualizar Xandart se ve lo nuevo
SIN_CACHE = {"Cache-Control": "no-store, max-age=0"}


@app.get("/", response_class=HTMLResponse)
def portada():
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"), headers=SIN_CACHE)


@app.get("/web/{nombre}")
def recurso(nombre: str):
    ruta = (WEB / nombre).resolve()
    if ruta.parent != WEB.resolve() or not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta, headers=SIN_CACHE)


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


@app.get("/api/version")
def version():
    return {"version": VERSION}


@app.post("/api/apagar")
def apagar():
    """Solo lo usa el acceso directo cuando hay una versión nueva instalada."""
    import threading

    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"ok": True}


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
    return {"claves": {"together": bool(clave_api("TOGETHER_API_KEY")), "minimax": bool(clave_api("MINIMAX_API_KEY")),
                       "pexels": bool(clave_api("PEXELS_API_KEY")), "freesound": bool(clave_api("FREESOUND_API_KEY"))},
            "claude": bool(claude_cli.ejecutable()), "videos": videos,
            "carpeta_videos": str(pipeline.carpeta_videos())}


class Claves(BaseModel):
    together: str | None = None
    minimax: str | None = None
    pexels: str | None = None
    freesound: str | None = None


@app.post("/api/claves")
def guardar_claves(c: Claves):
    valores = _leer_env()
    if c.together and c.together.strip():
        valores["TOGETHER_API_KEY"] = c.together.strip()
    if c.minimax and c.minimax.strip():
        valores["MINIMAX_API_KEY"] = c.minimax.strip()
    if c.pexels and c.pexels.strip():
        valores["PEXELS_API_KEY"] = c.pexels.strip()
    if c.freesound and c.freesound.strip():
        valores["FREESOUND_API_KEY"] = c.freesound.strip()
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
        if servicio == "pexels":
            r = requests.get("https://api.pexels.com/v1/search", params={"query": "scorpion", "per_page": 1}, timeout=30,
                             headers={"Authorization": clave_api("PEXELS_API_KEY") or ""})
            return {"ok": r.status_code == 200, "detalle": "funciona" if r.status_code == 200 else f"HTTP {r.status_code}"}
        if servicio == "freesound":
            r = requests.get("https://freesound.org/apiv2/search/text/", params={"query": "pop", "page_size": 1},
                             headers={"Authorization": f"Token {clave_api('FREESOUND_API_KEY') or ''}"}, timeout=30)
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


def _escenas_de_archivo(nombre: str, datos: bytes):
    """Acepta un escenas.json o un .zip que lo tenga adentro (como video_alacranes.zip)."""
    import io
    import json
    import zipfile

    if nombre.lower().endswith(".zip") or datos[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            candidatos = sorted((n for n in z.namelist() if n.lower().endswith("escenas.json")), key=len)
            if not candidatos:
                raise HTTPException(400, "Ese .zip no tiene un escenas.json adentro")
            datos = z.read(candidatos[0])
    try:
        return json.loads(datos.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as ex:
        raise HTTPException(400, "El archivo no es un escenas.json válido") from ex


@app.post("/api/importar")
async def importar(archivo: UploadFile = File(...)):
    v1 = _escenas_de_archivo(archivo.filename or "", await archivo.read())
    try:
        c, avisos = pipeline.importar_guion(v1)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    return {**pipeline.resumen(c), "avisos": avisos[:20]}


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


class Prueba(BaseModel):
    escenas: int = Field(10, ge=1, le=30)
    permiso: bool = False


@app.post("/api/videos/{slug}/prueba")
def prueba(slug: str, p: Prueba = Prueba()):
    c = _proyecto(slug)
    return _lanzar(slug, "prueba", lambda t: pipeline.paso_prueba(c, t, p.escenas, permiso=p.permiso))


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


@app.post("/api/videos/{slug}/short")
def short(slug: str, p: Permiso = Permiso()):
    """Short vertical del nivel del villano: guion con Claude, mismas imágenes, voz y render.
    Queda como un video más en la lista."""
    c = _proyecto(slug)
    return _lanzar(slug, "short", lambda t: pipeline.paso_short(c, t, permiso=p.permiso))


# ------------------------------------------------------------------ biblioteca de audio (sección 6)

@app.get("/api/biblioteca")
def ver_biblioteca():
    from . import biblioteca

    return biblioteca.resumen()


@app.post("/api/biblioteca")
async def subir_audio(archivo: UploadFile = File(...), clase: str = Form(...), tipo: str = Form(...),
                      fuente: str = Form(...), licencia: str = Form(...), detalle_licencia: str = Form(""),
                      atribucion: str = Form("")):
    from . import biblioteca

    datos = await archivo.read()
    if len(datos) > 60 * 1024 * 1024:
        raise HTTPException(400, "El archivo pesa más de 60 MB")
    try:
        biblioteca.registrar(datos, archivo.filename or "audio.wav", clase, tipo, fuente, licencia,
                             detalle_licencia, atribucion)
    except ValueError as ex:
        raise HTTPException(400, str(ex)) from ex
    return biblioteca.resumen()


class DeEntrada(BaseModel):
    nombre: str
    clase: str
    tipo: str
    fuente: str
    licencia: str
    detalle_licencia: str = ""
    atribucion: str = ""


@app.post("/api/biblioteca/freesound")
def llenar_freesound():
    """Completa los efectos que falten con sonidos CC0 de Freesound (tarda cerca de un minuto)."""
    from . import biblioteca, freesound

    try:
        agregados = freesound.llenar(avisar=lambda *_: None)
    except freesound.SinClaveFreesound as ex:
        raise HTTPException(400, str(ex)) from ex
    except Exception as ex:  # noqa: BLE001
        raise HTTPException(502, f"Freesound no respondió bien: {str(ex)[:200]}") from ex
    return {**biblioteca.resumen(), "agregados": agregados}


@app.post("/api/biblioteca/entrada")
def registrar_entrada(d: DeEntrada):
    from . import biblioteca

    try:
        biblioteca.registrar_de_entrada(d.nombre, clase=d.clase, tipo=d.tipo, fuente=d.fuente, licencia=d.licencia,
                                        detalle_licencia=d.detalle_licencia, atribucion=d.atribucion)
    except (ValueError, FileNotFoundError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return biblioteca.resumen()


@app.delete("/api/biblioteca/{huella}")
def borrar_audio(huella: str):
    from . import biblioteca

    try:
        biblioteca.quitar(huella)
    except KeyError as ex:
        raise HTTPException(404) from ex
    return biblioteca.resumen()


@app.get("/api/biblioteca/{huella}/escuchar")
def escuchar(huella: str):
    from . import biblioteca

    a = next((x for x in biblioteca.indice() if x["huella"] == huella), None)
    if not a:
        raise HTTPException(404)
    return FileResponse(biblioteca.raiz() / a["archivo"])


@app.post("/api/biblioteca/abrir-entrada")
def abrir_entrada():
    from . import biblioteca

    d = biblioteca.raiz() / "entrada"
    d.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(d)  # type: ignore[attr-defined]
    return {"carpeta": str(d)}


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


def _cerrar_puerto() -> None:
    """Último recurso en Windows: cierra el proceso que ocupa el puerto de Xandart
    (un Xandart muy viejo que no sabe apagarse solo)."""
    import time

    salida = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) >= 5 and partes[1].endswith(f":{PUERTO}") and partes[3].upper() in ("LISTENING", "ESCUCHANDO"):
            subprocess.run(["taskkill", "/F", "/T", "/PID", partes[4]], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    time.sleep(1.5)


def main():
    import uvicorn

    if sys.stdout is None or sys.stderr is None:  # pythonw (acceso directo): sin consola
        (RAIZ / "logs").mkdir(exist_ok=True)
        salida = open(RAIZ / "logs" / "xandart.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or salida
        sys.stderr = sys.stderr or salida
    if _ya_abierto():
        import json
        import time
        import urllib.request

        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/api/version", timeout=3) as r:
                abierta = json.load(r).get("version")
        except Exception:  # noqa: BLE001 — un Xandart muy viejo no tiene /api/version
            abierta = None
        if abierta == VERSION:     # segundo clic en el acceso directo: solo abre la página
            webbrowser.open(f"http://127.0.0.1:{PUERTO}/")
            return
        try:                       # quedó abierto el Xandart de antes de actualizar: se cierra
            urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PUERTO}/api/apagar", method="POST"),
                                   timeout=3)
        except Exception:  # noqa: BLE001
            pass
        for _ in range(20):
            time.sleep(0.5)
            if not _ya_abierto():
                break
        if _ya_abierto() and os.name == "nt":
            _cerrar_puerto()
    if "--sin-navegador" not in sys.argv:
        import threading

        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}/")).start()
    uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
