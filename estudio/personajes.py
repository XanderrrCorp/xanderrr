"""Asistente de personaje: de una descripción (o una referencia subida) a un personaje fijo.

Pasos: describir → 3 variantes → elegir → afinar con texto → hoja de referencia (frente, perfil,
3/4) con la descripción fija (character lock) → 3 escenas de prueba para confirmar que se mantiene
igual → asignarlo a un canal. Desde ahí, cada video nuevo del canal lo usa como referencia sin
volver a pagarlo.

Cada personaje vive en su carpeta del espacio (datos/espacios/<id>/personajes/<clave>/) con su
`personaje.json`, las imágenes y su propio libro de costos. Cada imagen pasa por el freno.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel

from .config import ConfigCostos, escribir_json, leer_json

ARCHIVO = "personaje.json"
VISTAS = {"frente": "front view, facing the camera", "perfil": "side profile view, facing right",
          "tres_cuartos": "three-quarter view, turned slightly to the side"}
ESCENAS_DE_PRUEBA = [
    "walking through a dense green jungle, curious, looking at a butterfly",
    "sitting at a wooden desk reading a huge old book, surprised with wide eyes",
    "running away scared from a big dark shadow, dynamic pose, motion lines",
]
PLANTILLA_ESCENA = ("{bloque_estilo}. The same character as the reference images, identical face, proportions, "
                    "colors and outfit: {personaje}. Scene: {descripcion}. Full 16:9 illustrated background. "
                    "No text, no letters.")


class Imagen(BaseModel):
    archivo: str
    nota: str = ""


class EstadoPersonaje(BaseModel):
    clave: str
    nombre: str
    tipo: Literal["mascota", "presentador"] = "mascota"
    estilo: str
    descripcion: str
    referencia: str | None = None
    bloqueo: str | None = None                   # descripción fija en inglés que va en cada prompt
    variantes: list[Imagen] = []
    elegida: str | None = None
    hoja: dict[str, str] = {}                    # frente / perfil / tres_cuartos / hoja
    pruebas: list[Imagen] = []

    @property
    def paso(self) -> str:
        if not self.variantes:
            return "describir"
        if not self.elegida:
            return "elegir"
        if not self.hoja.get("hoja"):
            return "afinar"
        if not self.pruebas:
            return "probar"
        return "listo"


def carpeta(espacio_id: str, clave: str) -> Path:
    from .plataforma import almacen

    return almacen.ruta(espacio_id, "personajes", clave)


def cargar(ruta: Path) -> EstadoPersonaje:
    return EstadoPersonaje.model_validate(leer_json(ruta / ARCHIVO))


def guardar(ruta: Path, e: EstadoPersonaje) -> None:
    escribir_json(ruta / ARCHIVO, e.model_dump())


def clave_de(nombre: str) -> str:
    from .proyecto import slugificar

    return (slugificar(nombre) or "personaje")[:40].replace("-", "_")


def crear(ruta: Path, nombre: str, estilo: str, descripcion: str, tipo: str = "mascota",
          referencia: tuple[bytes, str] | None = None) -> EstadoPersonaje:
    """Solo guarda lo que pidió la persona (gratis). La referencia subida se normaliza a PNG."""
    from .estilos import cargar_estilo

    cargar_estilo(estilo)                                # que exista
    if len(descripcion.strip()) < 5 and referencia is None:
        raise ValueError("Describe el personaje o sube una imagen de referencia")
    ruta.mkdir(parents=True, exist_ok=True)
    e = EstadoPersonaje(clave=ruta.name, nombre=nombre.strip() or ruta.name, tipo=tipo, estilo=estilo,
                        descripcion=descripcion.strip())
    if referencia is not None:
        import io

        from PIL import Image

        im = Image.open(io.BytesIO(referencia[0]))
        im.load()
        im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").save(ruta / "referencia.png")
        e.referencia = "referencia.png"
    guardar(ruta, e)
    return e


# ------------------------------------------------------------------ piezas

def _proveedor(config: ConfigCostos):
    from .config import leer_config
    from .imagenes.proveedores import crear_proveedor

    return crear_proveedor(config, leer_config("proveedores.json")["imagenes"])


def _bloqueo(e: EstadoPersonaje, ejecutar=None, cambio: str = "") -> str:
    """La descripción fija en inglés la escribe Claude con la suscripción (no cuesta)."""
    from . import claude_cli

    if cambio:
        pedido = (f"Esta es la descripción fija de un personaje de dibujo (en inglés):\n«{e.bloqueo}»\n"
                  f"Aplícale este cambio que pidió el dueño: «{cambio}».\n")
    else:
        pedido = (f"Un creador de YouTube quiere este personaje fijo para su canal ({e.tipo}):\n«{e.descripcion}»\n"
                  + ("También subió una imagen de referencia.\n" if e.referencia else ""))
    pedido += ("Escribe la descripción literal en inglés que se copiará igual en cada prompt de imagen para que el "
               "personaje salga siempre idéntico: especie o tipo, forma de la cabeza y el cuerpo, proporciones, "
               "colores exactos, ropa y accesorios, rasgos que lo distinguen. Sin poses, sin fondo, sin estilo de "
               "dibujo, sin nombres de personajes reales o famosos. Máximo 70 palabras. Responde SOLO un JSON: "
               '{"bloqueo": "..."}')
    texto, _ = (ejecutar or claude_cli.ejecutar)(pedido, tiempo_max_s=240)
    datos = claude_cli.extraer_json(texto) or {}
    bloqueo = re.sub(r"\s+", " ", str(datos.get("bloqueo") or "")).strip().rstrip(".")
    if len(bloqueo) < 15:
        raise RuntimeError("Claude no escribió la descripción del personaje; intenta de nuevo")
    return bloqueo


def _generar(ruta: Path, e: EstadoPersonaje, prompt: str, refs: list[Path], nombre: str, detalle: str,
             proveedor, config: ConfigCostos, permiso: bool) -> str:
    from .costos import LibroCostos

    libro = LibroCostos(ruta, config)
    libro.autorizar(proveedor.estimar_usd(prompt, refs), permiso=permiso)
    r = proveedor.generar(prompt, refs)
    libro.registrar(modulo="personaje", proveedor=r.proveedor, modelo=r.modelo, unidades={"imagenes": 1},
                    costo_usd=r.uso.costo_usd, detalle=detalle)
    (ruta / "imagenes").mkdir(exist_ok=True)
    destino = ruta / "imagenes" / f"{nombre}.png"
    destino.write_bytes(r.png)
    return f"imagenes/{nombre}.png"


def _siguiente(ruta: Path, base: str) -> str:
    n = 1
    while (ruta / "imagenes" / f"{base}_{n}.png").exists():
        n += 1
    return f"{base}_{n}"


def _plantilla(e: EstadoPersonaje, cual: str) -> tuple[str, object]:
    from .estilos import cargar_estilo

    estilo = cargar_estilo(e.estilo)
    p = estilo.plantillas_assets
    if e.tipo == "presentador" and "presentador" in p:
        return p["presentador"].replace("{persona}", "{personaje}"), estilo
    return (p.get(cual) or p.get("personaje") or "{bloque_estilo}. {personaje}. {descripcion}"), estilo


# ------------------------------------------------------------------ pasos (cada uno se cobra por imagen)

Aviso = Callable[[str], None]


def variantes(ruta: Path, n: int = 3, permiso: bool = False, proveedor=None, ejecutar=None,
              avisar: Aviso = print) -> list[str]:
    from .imagenes import prompts

    e = cargar(ruta)
    config = ConfigCostos.cargar()
    proveedor = proveedor or _proveedor(config)
    if not e.bloqueo:
        avisar("Escribiendo la descripción fija del personaje…")
        e.bloqueo = _bloqueo(e, ejecutar)
        guardar(ruta, e)
    plantilla, estilo = _plantilla(e, "personaje")
    refs = [ruta / e.referencia] if e.referencia else []
    nota = "Based on the reference image, redrawn in this style." if refs else ""
    hechas = []
    for k in range(n):
        avisar(f"Dibujando la variante {k + 1} de {n}…")
        prompt = prompts.armar(plantilla, estilo, e.bloqueo, nota, escenario="a simple neutral studio")
        archivo = _generar(ruta, e, prompt, refs, _siguiente(ruta, "variante"), "variante", proveedor, config, permiso)
        e.variantes.append(Imagen(archivo=archivo))
        guardar(ruta, e)
        hechas.append(archivo)
    return hechas


def elegir(ruta: Path, archivo: str) -> EstadoPersonaje:
    e = cargar(ruta)
    if archivo not in {v.archivo for v in e.variantes}:
        raise ValueError("esa imagen no es de este personaje")
    if e.elegida != archivo:
        e.elegida, e.hoja, e.pruebas = archivo, {}, []     # otra base: la hoja y las pruebas se rehacen
    guardar(ruta, e)
    return e


def afinar(ruta: Path, instruccion: str, permiso: bool = False, proveedor=None, ejecutar=None,
           avisar: Aviso = print) -> str:
    """Una imagen nueva a partir de la elegida con el cambio pedido; la descripción fija se actualiza."""
    from .imagenes import prompts

    instruccion = instruccion.strip()
    e = cargar(ruta)
    if not e.elegida:
        raise ValueError("Primero elige una variante")
    if len(instruccion) < 3:
        raise ValueError("Escribe qué quieres cambiar")
    config = ConfigCostos.cargar()
    proveedor = proveedor or _proveedor(config)
    avisar("Ajustando la descripción fija…")
    e.bloqueo = _bloqueo(e, ejecutar, cambio=instruccion)
    plantilla, estilo = _plantilla(e, "pose")
    avisar("Dibujando el personaje con el cambio…")
    prompt = prompts.armar(plantilla, estilo, e.bloqueo, f"Change only this: {instruccion}. Keep everything else "
                           "identical to the reference.", escenario="a simple neutral studio")
    archivo = _generar(ruta, e, prompt, [ruta / e.elegida], _siguiente(ruta, "afinada"), instruccion[:80],
                       proveedor, config, permiso)
    e.variantes.append(Imagen(archivo=archivo, nota=instruccion))
    e.elegida, e.hoja, e.pruebas = archivo, {}, []
    guardar(ruta, e)
    return archivo


def hoja(ruta: Path, permiso: bool = False, proveedor=None, avisar: Aviso = print) -> str:
    """Frente, perfil y 3/4 con la elegida como referencia, y la hoja armada en una sola imagen."""
    from .imagenes import prompts

    e = cargar(ruta)
    if not e.elegida or not e.bloqueo:
        raise ValueError("Primero elige una variante")
    config = ConfigCostos.cargar()
    proveedor = proveedor or _proveedor(config)
    plantilla, estilo = _plantilla(e, "pose")
    vistas = {}
    for k, (vista, texto) in enumerate(VISTAS.items(), 1):
        avisar(f"Hoja de referencia: vista {k} de {len(VISTAS)}…")
        prompt = prompts.armar(plantilla, estilo, e.bloqueo, f"Full body, {texto}, standing relaxed, neutral expression.",
                               escenario="a simple neutral studio")
        vistas[vista] = _generar(ruta, e, prompt, [ruta / e.elegida], f"hoja_{vista}", vista, proveedor, config, permiso)
    vistas["hoja"] = _armar_hoja(ruta, [vistas[v] for v in VISTAS], e.nombre)
    e.hoja, e.pruebas = vistas, []
    guardar(ruta, e)
    return vistas["hoja"]


def _armar_hoja(ruta: Path, archivos: list[str], nombre: str) -> str:
    """Las tres vistas lado a lado sobre gris, con su rótulo (gratis, por código)."""
    from PIL import Image, ImageDraw

    alto = 720
    ims = []
    for a in archivos:
        im = Image.open(ruta / a).convert("RGB")
        ims.append(im.resize((round(im.width * alto / im.height), alto)))
    margen = 24
    lienzo = Image.new("RGB", (sum(i.width for i in ims) + margen * (len(ims) + 1), alto + 2 * margen + 40), (128, 128, 128))
    d = ImageDraw.Draw(lienzo)
    x = margen
    for im, rotulo in zip(ims, ("FRENTE", "PERFIL", "3/4")):
        lienzo.paste(im, (x, margen))
        d.text((x + 8, alto + margen + 10), rotulo, fill=(255, 255, 255))
        x += im.width + margen
    d.text((lienzo.width - margen - 8 * len(nombre), alto + margen + 10), nombre, fill=(230, 230, 230))
    lienzo.save(ruta / "imagenes" / "hoja.png")
    return "imagenes/hoja.png"


def probar(ruta: Path, permiso: bool = False, proveedor=None, avisar: Aviso = print) -> list[str]:
    """3 escenas distintas con la elegida y la hoja como referencia: se ve si se mantiene igual."""
    from .imagenes import prompts

    e = cargar(ruta)
    if not e.hoja.get("hoja"):
        raise ValueError("Primero haz la hoja de referencia")
    config = ConfigCostos.cargar()
    proveedor = proveedor or _proveedor(config)
    _, estilo = _plantilla(e, "pose")
    refs = [ruta / e.elegida, ruta / e.hoja["hoja"]]
    e.pruebas = []
    for k, escena in enumerate(ESCENAS_DE_PRUEBA, 1):
        avisar(f"Escena de prueba {k} de {len(ESCENAS_DE_PRUEBA)}…")
        prompt = prompts.armar(PLANTILLA_ESCENA, estilo, e.bloqueo, escena)
        archivo = _generar(ruta, e, prompt, refs, f"prueba_{k}", escena[:60], proveedor, config, permiso)
        e.pruebas.append(Imagen(archivo=archivo, nota=escena))
        guardar(ruta, e)
    return [p.archivo for p in e.pruebas]


def editar_bloqueo(ruta: Path, bloqueo: str) -> EstadoPersonaje:
    e = cargar(ruta)
    bloqueo = re.sub(r"\s+", " ", bloqueo).strip()
    if len(bloqueo) < 15:
        raise ValueError("La descripción fija es muy corta")
    e.bloqueo = bloqueo
    guardar(ruta, e)
    return e


def imagenes_por_paso() -> dict[str, int]:
    return {"variantes": 3, "afinar": 1, "hoja": len(VISTAS), "probar": len(ESCENAS_DE_PRUEBA)}


def gastado_usd(ruta: Path) -> float:
    from .costos import LibroCostos

    return sum(x["costo_usd"] for x in LibroCostos(ruta, ConfigCostos.cargar()).entradas())


# ------------------------------------------------------------------ en los videos del canal

def usar_en_video(ruta_personaje: Path, carpeta_video: Path) -> bool:
    """Copia la imagen base al video (mascota_base.png) y deja la descripción fija en su perfil,
    así las escenas con el personaje lo usan como referencia sin volver a pagarlo."""
    e = cargar(ruta_personaje)
    if not e.elegida or not e.bloqueo:
        return False
    (carpeta_video / "assets").mkdir(parents=True, exist_ok=True)
    # las reacciones guardadas del estilo son de OTRO personaje: en este video no se usan
    shutil.rmtree(carpeta_video / "assets" / ("presentador" if e.tipo == "presentador" else "poses"),
                  ignore_errors=True)
    shutil.copy(ruta_personaje / e.elegida, carpeta_video / "assets" / "mascota_base.png")
    if e.hoja.get("hoja"):
        shutil.copy(ruta_personaje / e.hoja["hoja"], carpeta_video / "assets" / "personaje_hoja.png")
    perfil_ruta = carpeta_video / "perfil_canal.json"
    perfil = leer_json(perfil_ruta) if perfil_ruta.exists() else {}
    perfil.setdefault("personaje", {})["bloqueo"] = e.bloqueo
    perfil["personaje"]["imagen_referencia"] = "assets/mascota_base.png"
    escribir_json(perfil_ruta, perfil)
    return True
