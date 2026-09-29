"""La página de Xandart: un servidor local (solo en este computador) que maneja
los pasos del video. Se abre con `python -m estudio.app` o con el acceso directo."""
from __future__ import annotations

import os
import re
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
    for f in sorted(list(base.rglob("*.py")) + list(WEB.glob("*")) + list((base / "web_app").rglob("*.*"))):
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:12]


VERSION = _version()
from .config import aplicar_ajustes_de_instalacion  # noqa: E402

aplicar_ajustes_de_instalacion()
PUERTO = int(os.environ.get("XANDART_PUERTO", "8030"))
app = FastAPI(title="Xandart")


class EspacioDeLaPeticion:
    """Cada petición corre dentro del espacio de trabajo de quien la hace. En modo local
    es siempre el del dueño (su instalación ya migrada a datos)."""

    def __init__(self, siguiente):
        self.siguiente = siguiente

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.siguiente(scope, receive, send)
        from starlette.concurrency import run_in_threadpool

        from .plataforma import contexto, local

        espacio = await run_in_threadpool(local.espacio, False)   # no espera la copia: mientras, modo de siempre
        with contexto.usar_espacio(espacio):
            await self.siguiente(scope, receive, send)


app.add_middleware(EspacioDeLaPeticion)

from .plataforma.api import api as api_v2  # noqa: E402 — la API de la plataforma (cuenta, créditos, admin)
from .plataforma.api_personajes import rutas as api_personajes  # noqa: E402 — asistente de personaje

app.include_router(api_v2)
app.include_router(api_personajes)


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


@app.get("/admin", response_class=HTMLResponse)
def administracion():
    return HTMLResponse((WEB / "admin.html").read_text(encoding="utf-8"), headers=SIN_CACHE)


APP = Path(__file__).parent / "web_app"      # la interfaz nueva (React), construida en GitHub Actions


@app.get("/app", response_class=HTMLResponse)
@app.get("/app/{ruta:path}", response_class=HTMLResponse)
def interfaz_nueva(ruta: str = ""):
    """Interfaz nueva. Los archivos construidos se sirven tal cual; cualquier otra ruta es la
    aplicación (sus páginas las resuelve el navegador)."""
    base = APP.resolve()
    if ruta:
        destino = (base / ruta).resolve()
        if base in destino.parents and destino.is_file():
            return FileResponse(destino)
    indice = base / "index.html"
    if not indice.exists():
        raise HTTPException(404, "La interfaz nueva no está construida en esta instalación")
    return HTMLResponse(indice.read_text(encoding="utf-8"), headers=SIN_CACHE)


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
                       "pexels": bool(clave_api("PEXELS_API_KEY")), "freesound": bool(clave_api("FREESOUND_API_KEY")),
                       "correo": bool(clave_api("XANDART_SMTP_USUARIO") and clave_api("XANDART_SMTP_CLAVE"))},
            "claude": bool(claude_cli.ejecutable()), "videos": videos,
            "carpeta_videos": str(pipeline.carpeta_videos())}


class Claves(BaseModel):
    together: str | None = None
    minimax: str | None = None
    pexels: str | None = None
    freesound: str | None = None
    smtp_usuario: str | None = None     # Gmail que manda los avisos
    smtp_clave: str | None = None       # contraseña de aplicación de ese Gmail


@app.post("/api/claves")
def guardar_claves(c: Claves):
    from .config import limpiar_clave

    valores = _leer_env()
    for campo, nombre in NOMBRES_CLAVE.items():
        v = limpiar_clave(getattr(c, campo))
        if v:
            valores[nombre] = v
    (RAIZ / ".env").write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
    return estado()


NOMBRES_CLAVE = {"together": "TOGETHER_API_KEY", "minimax": "MINIMAX_API_KEY", "pexels": "PEXELS_API_KEY",
                 "freesound": "FREESOUND_API_KEY", "smtp_usuario": "XANDART_SMTP_USUARIO",
                 "smtp_clave": "XANDART_SMTP_CLAVE"}


DONDE_CLAVE = {"together": "api.together.ai → Settings → API keys", "pexels": "pexels.com/api → Your API key",
               "freesound": "freesound.org/apiv2/apply → tu clave (Client secret/API key)"}


def _explicar(servicio: str, codigo: int) -> str:
    if codigo == 200:
        return "funciona"
    if codigo in (401, 403):
        return (f"La clave no es válida (HTTP {codigo}). Cópiala otra vez desde {DONDE_CLAVE.get(servicio, 'la página del servicio')}, "
                "pégala sin espacios, dale Guardar y vuelve a Probar.")
    if codigo == 429:
        return "El servicio dice que hiciste demasiadas consultas (HTTP 429). Espera unos minutos y prueba de nuevo."
    return f"El servicio respondió con un error (HTTP {codigo}). Prueba de nuevo en unos minutos."


class Prueba_clave(BaseModel):
    clave: str | None = None     # la que está escrita en Ajustes (aún sin guardar)


def _forma_pexels(clave: str) -> str | None:
    """Pista si lo pegado no tiene la forma de una clave de Pexels (sin mostrar la clave)."""
    if not re.fullmatch(r"[A-Za-z0-9]+", clave):
        return ("Lo que se pegó tiene símbolos que una clave de Pexels no lleva (¿se copió un enlace o un correo?). "
                "En pexels.com/api, con tu cuenta abierta, copia solo el texto largo de «Your API Key».")
    if len(clave) != 56:
        return (f"Lo que se pegó tiene {len(clave)} caracteres y las claves de Pexels suelen tener 56: "
                "puede que se haya copiado incompleta. Cópiala completa desde «Your API Key» en pexels.com/api.")
    return None


@app.post("/api/probar/{servicio}")
def probar(servicio: str, p: Prueba_clave = Prueba_clave()):
    import requests

    from .config import limpiar_clave

    escrita = limpiar_clave(p.clave)
    nombre = NOMBRES_CLAVE.get(servicio)
    if escrita and nombre:
        # se prueba lo que está escrito; si funciona, queda guardado de una vez
        valores = _leer_env()
        anterior = valores.get(nombre)
        valores[nombre] = escrita
        (RAIZ / ".env").write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
        r = probar(servicio)
        if not r.get("ok"):
            if anterior:
                valores[nombre] = anterior
            else:
                valores.pop(nombre, None)
            (RAIZ / ".env").write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
        else:
            r["detalle"] = "funciona y quedó guardada"
        return r
    try:
        if servicio == "together":
            r = requests.get("https://api.together.xyz/v1/models", timeout=30,
                             headers={"Authorization": f"Bearer {clave_api('TOGETHER_API_KEY')}"})
            return {"ok": r.status_code == 200, "detalle": _explicar("together", r.status_code)}
        if servicio == "pexels":
            clave = clave_api("PEXELS_API_KEY") or ""
            if not clave:
                return {"ok": False, "detalle": "No hay clave de Pexels guardada: pégala arriba y dale Probar."}
            r = requests.get("https://api.pexels.com/v1/search", params={"query": "scorpion", "per_page": 1}, timeout=30,
                             headers={"Authorization": clave, "User-Agent": "Xandart/1.0"})
            detalle = _explicar("pexels", r.status_code)
            if r.status_code in (401, 403):
                detalle = _forma_pexels(clave) or ("Pexels dice que esa clave no existe. Entra a pexels.com/api con "
                                                   "la cuenta donde la pediste y copia el texto de «Your API Key».")
            return {"ok": r.status_code == 200, "detalle": detalle}
        if servicio == "freesound":
            r = requests.get("https://freesound.org/apiv2/search/text/", params={"query": "pop", "page_size": 1},
                             headers={"Authorization": f"Token {clave_api('FREESOUND_API_KEY') or ''}"}, timeout=30)
            return {"ok": r.status_code == 200, "detalle": _explicar("freesound", r.status_code)}
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
        # esta ventana sí se ve: es para que la persona inicie sesión en Claude
        subprocess.Popen(["cmd", "/c", "start", "Claude", "cmd", "/k", exe], creationflags=subprocess.CREATE_NEW_CONSOLE)
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
    canal: str | None = None        # clave del canal; si no, el primero del espacio
    disfraz: bool = False           # mascota con hoodie del animal del tema (una imagen extra)


@app.post("/api/videos")
def nuevo(n: Nuevo):
    c = pipeline.crear_video(n.tema, n.giro, n.villano, n.minutos, n.notas, canal=n.canal or None, disfraz=n.disfraz)
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


@app.post("/api/videos/{slug}/ajustar-imagenes")
def ajustar_imagenes(slug: str):
    c = _proyecto(slug)
    return _lanzar(slug, "ajustar", lambda t: pipeline.ajustar_al_presupuesto(c, t))


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


# ------------------------------------------------------------------ editor (tipo CapCut)

def _editor(slug: str):
    c = _proyecto(slug)
    if not (c.ruta / "edl.json").exists():
        raise HTTPException(409, "El editor se abre cuando el video ya está armado")
    return c


@app.get("/api/videos/{slug}/editor")
def editor_ver(slug: str):
    from . import editor

    import time

    c = _editor(slug)
    t = pipeline.TRABAJOS.get(slug)
    trabajo = ({"paso": t.paso, "mensaje": t.mensaje, "progreso": round(t.progreso, 3), "activo": t.activo,
                "error": t.error, "segundos": int(time.time() - t.inicio)} if t else None)
    return {**editor.linea_de_tiempo(c.ruta), "slug": slug, "titulo": c.cargar().titulo, "trabajo": trabajo}


class Corte(BaseModel):
    inicio: float = Field(ge=0)


@app.put("/api/videos/{slug}/editor/escenas/{escena_id}/corte")
def editor_corte(slug: str, escena_id: int, p: Corte):
    from . import editor

    c = _editor(slug)
    try:
        editor.mover_corte(c.ruta, escena_id, p.inicio)
    except KeyError as ex:
        raise HTTPException(404, str(ex)) from ex
    return editor_ver(slug)


class SubtituloEditado(BaseModel):
    inicio: float = Field(ge=0)
    fin: float = Field(ge=0)
    texto: str = Field(max_length=200)


class Subtitulos(BaseModel):
    subtitulos: list[SubtituloEditado]


@app.put("/api/videos/{slug}/editor/escenas/{escena_id}/subtitulos")
def editor_subtitulos(slug: str, escena_id: int, p: Subtitulos):
    from . import editor

    c = _editor(slug)
    try:
        editor.cambiar_subtitulos(c.ruta, escena_id, [s.model_dump() for s in p.subtitulos])
    except KeyError as ex:
        raise HTTPException(404, str(ex)) from ex
    return editor_ver(slug)


@app.delete("/api/videos/{slug}/editor/escenas/{escena_id}/{que}")
def editor_deshacer(slug: str, escena_id: int, que: str):
    from . import editor

    if que not in ("corte", "subtitulos", "animacion"):
        raise HTTPException(404)
    editor.deshacer_escena(_editor(slug).ruta, escena_id, que)
    return editor_ver(slug)


class Animar(BaseModel):
    instruccion: str = Field("", max_length=400)
    permiso: bool = False


@app.post("/api/videos/{slug}/escenas/{escena_id}/animar")
def editor_animar(slug: str, escena_id: int, p: Animar = Animar()):
    c = _editor(slug)
    _lanzar(slug, "animar", lambda t: pipeline.animar_escena(c, t, escena_id, p.instruccion, p.permiso))
    return editor_ver(slug)


class VozEscena(BaseModel):
    texto: str | None = Field(None, max_length=2000)
    permiso: bool = False


@app.post("/api/videos/{slug}/escenas/{escena_id}/voz")
def editor_voz(slug: str, escena_id: int, p: VozEscena = VozEscena()):
    c = _editor(slug)
    _lanzar(slug, "voz", lambda t: pipeline.regenerar_voz_escena(c, t, escena_id, p.texto, p.permiso))
    return editor_ver(slug)


@app.post("/api/videos/{slug}/escenas/{escena_id}/regenerar")
def regenerar(slug: str, escena_id: int, cuerpo: Instruccion):
    c = _proyecto(slug)
    return _lanzar(slug, "regenerar", lambda t: pipeline.regenerar_imagen(c, t, escena_id, cuerpo.instruccion))


class HacerVideo(BaseModel):
    permiso: bool = False
    fps: int | None = None          # 60 = más fluido (tarda el doble), 30 = rápido


@app.post("/api/videos/{slug}/video")
def video(slug: str, p: HacerVideo = HacerVideo()):
    c = _proyecto(slug)
    return _lanzar(slug, "video", lambda t: pipeline.paso_video(c, t, permiso=p.permiso, fps=p.fps))


@app.post("/api/videos/{slug}/short")
def short(slug: str, p: Permiso = Permiso()):
    """Short vertical del nivel del villano: guion con Claude, mismas imágenes, voz y render.
    Queda como un video más en la lista."""
    c = _proyecto(slug)
    return _lanzar(slug, "short", lambda t: pipeline.paso_short(c, t, permiso=p.permiso))


# ------------------------------------------------------------------ miniaturas (escala 2x3)

def _mini_clave(slug: str) -> str:
    return f"{slug}~miniatura"          # trabajo aparte: se puede hacer la miniatura mientras se renderiza


def _mini_estado(slug: str) -> dict:
    import time

    from .miniaturas import servicio

    datos = servicio.estado(_proyecto(slug))
    t = pipeline.TRABAJOS.get(_mini_clave(slug))
    datos["trabajo"] = None if t is None else {
        "paso": t.paso, "mensaje": t.mensaje, "progreso": round(t.progreso, 3), "activo": t.activo,
        "error": t.error, "segundos": int(time.time() - t.inicio)}
    datos["slug"] = slug
    return datos


def _mini_lanzar(slug: str, paso: str, f):
    try:
        pipeline.lanzar(_mini_clave(slug), paso, f)
    except RuntimeError as ex:
        raise HTTPException(409, str(ex)) from ex
    return _mini_estado(slug)


@app.get("/api/videos/{slug}/miniatura")
def mini_ver(slug: str):
    return _mini_estado(slug)


class MiniProducir(BaseModel):
    permiso: bool = False
    rehacer_plan: bool = False


@app.post("/api/videos/{slug}/miniatura/producir")
def mini_producir(slug: str, p: MiniProducir = MiniProducir()):
    from .miniaturas import servicio

    c = _proyecto(slug)
    return _mini_lanzar(slug, "miniatura", lambda t: servicio.producir(c, t, permiso=p.permiso,
                                                                         rehacer_plan=p.rehacer_plan))


class MiniRegenerar(BaseModel):
    instruccion: str = ""
    permiso: bool = False


@app.post("/api/videos/{slug}/miniatura/sujetos/{indice}/regenerar")
def mini_regenerar(slug: str, indice: int, p: MiniRegenerar = MiniRegenerar()):
    from .miniaturas import servicio

    if not 0 <= indice < 6:
        raise HTTPException(404)
    c = _proyecto(slug)
    return _mini_lanzar(slug, "regenerar", lambda t: servicio.regenerar(c, t, indice, p.instruccion, p.permiso))


class MiniVariantes(BaseModel):
    n: int = Field(2, ge=1, le=3)
    permiso: bool = False


@app.post("/api/videos/{slug}/miniatura/variantes")
def mini_variantes(slug: str, p: MiniVariantes = MiniVariantes()):
    from .miniaturas import servicio

    c = _proyecto(slug)
    return _mini_lanzar(slug, "variantes", lambda t: servicio.variantes_protagonista(c, t, p.n, p.permiso))


class MiniElegir(BaseModel):
    archivo: str


@app.post("/api/videos/{slug}/miniatura/sujetos/{indice}/elegir")
def mini_elegir(slug: str, indice: int, p: MiniElegir):
    from .miniaturas import servicio

    try:
        servicio.elegir(_proyecto(slug), indice, p.archivo)
    except (ValueError, IndexError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return _mini_estado(slug)


@app.put("/api/videos/{slug}/miniatura")
def mini_editar(slug: str, cambios: dict):
    from .miniaturas import servicio

    try:
        servicio.editar(_proyecto(slug), cambios)
    except (ValueError, IndexError, KeyError) as ex:
        errores = ex.errors() if hasattr(ex, "errors") else None
        mensaje = errores[0]["msg"].removeprefix("Value error, ") if errores else str(ex)
        raise HTTPException(400, mensaje) from ex
    return _mini_estado(slug)


@app.post("/api/videos/{slug}/miniatura/sujetos/{indice}/referencia")
def mini_referencia(slug: str, indice: int):
    from .miniaturas import servicio

    try:
        servicio.usar_como_referencia(_proyecto(slug), indice)
    except (ValueError, IndexError) as ex:
        raise HTTPException(400, str(ex)) from ex
    return _mini_estado(slug)


@app.get("/api/canales/{canal}/miniatura")
def plantilla_ver(canal: str):
    from .miniaturas import plantilla

    return plantilla.cargar(canal).model_dump()


@app.post("/api/canales/{canal}/miniatura/referencias")
async def plantilla_subir(canal: str, archivo: UploadFile = File(...)):
    from .miniaturas import plantilla

    try:
        return plantilla.agregar_referencia(canal, await archivo.read(), archivo.filename or "ref.png").model_dump()
    except Exception as ex:  # noqa: BLE001 — imagen rota o formato raro: se explica en la página
        raise HTTPException(400, f"No se pudo usar esa imagen: {ex}") from ex


class Activa(BaseModel):
    activa: bool


@app.put("/api/canales/{canal}/miniatura/referencias/{archivo}")
def plantilla_marcar(canal: str, archivo: str, p: Activa):
    from .miniaturas import plantilla

    try:
        return plantilla.marcar_referencia(canal, archivo, p.activa).model_dump()
    except KeyError as ex:
        raise HTTPException(404) from ex


@app.delete("/api/canales/{canal}/miniatura/referencias/{archivo}")
def plantilla_borrar(canal: str, archivo: str):
    from .miniaturas import plantilla

    try:
        return plantilla.quitar_referencia(canal, archivo).model_dump()
    except KeyError as ex:
        raise HTTPException(404) from ex


@app.get("/canales/{canal}/referencias/{archivo}")
def plantilla_imagen(canal: str, archivo: str):
    from .miniaturas.plantilla import ruta_plantilla

    base = (ruta_plantilla(canal) / "referencias").resolve()
    ruta = (base / archivo).resolve()
    if ruta.parent != base or not ruta.exists():
        raise HTTPException(404)
    return FileResponse(ruta)


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
            webbrowser.open(f"http://127.0.0.1:{PUERTO}{os.environ.get('XANDART_ABRIR', '/')}")
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
    from .plataforma import local

    local.preparar(esperar=False)  # copia de seguridad y migración en segundo plano (la primera vez tarda)
    if "--sin-navegador" not in sys.argv:
        import threading

        abrir = os.environ.get("XANDART_ABRIR", "/")     # la versión nueva abre directo en /app/
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PUERTO}{abrir}")).start()
    uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
