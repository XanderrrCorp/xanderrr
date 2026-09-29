"""Generador de imágenes por escena (sección 5.4), reanudable y con freno.

- Solo regenera lo que cambió: cada imagen guarda la huella de su prompt, sus
  referencias y el modelo en `imagenes/manifiesto.json`.
- Antes de cada llamada pagada pide permiso al libro de costos (freno en pesos)
  y respeta un tope de llamadas por video.
- Registra el costo REAL de cada llamada, también de los intentos fallidos que la
  API haya cobrado.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..config import ConfigCostos, escribir_json, formato_cop, formato_usd, leer_config, leer_json
from ..costos import FrenoPresupuesto, LibroCostos
from ..esquemas import AssetDef, Escena, EscenasV2, Estilo
from ..estilos import cargar_estilo
from ..proyecto import CarpetaProyecto
from . import prompts
from .proveedores import ErrorProveedor, Proveedor, crear_proveedor

MODULO = "imagenes"


@dataclass
class Trabajo:
    clave: str                 # "asset:<id>" o "escena:<id>"
    prompt: str
    referencias: list[Path]
    destino: Path
    quitar_fondo: bool


@dataclass
class Reporte:
    proveedor: str
    modelo: str
    generadas: list[str] = field(default_factory=list)
    ya_estaban: list[str] = field(default_factory=list)
    reusadas: list[str] = field(default_factory=list)
    pendientes: list[str] = field(default_factory=list)
    fallidas: dict[str, str] = field(default_factory=dict)
    llamadas: int = 0
    costo_usd: float = 0.0
    frenado: str | None = None
    avisos: list[str] = field(default_factory=list)
    costos_por_imagen: dict[str, float] = field(default_factory=dict)


def _huella(t: Trabajo, modelo: str) -> str:
    h = hashlib.sha256()
    h.update(modelo.encode())
    h.update(t.prompt.encode())
    for r in t.referencias:
        h.update(hashlib.sha256(r.read_bytes()).digest())
    return h.hexdigest()[:16]


def _misma_de_antes(t: Trabajo, modelo: str, previo: dict) -> bool:
    from dataclasses import replace

    from .arreglos import prompt_anterior

    antes = prompt_anterior(t.prompt)
    return antes is not None and _huella(replace(t, prompt=antes), modelo) == previo.get("huella")


def _validar_png(datos: bytes, aspecto: str) -> tuple[bytes, str | None]:
    """Control de calidad barato: que la imagen abra y tenga la proporción pedida.
    El control visual (letras, anatomía, personaje) lo hace el Revisor."""
    from PIL import Image

    img = Image.open(io.BytesIO(datos))
    img.load()
    if img.width < 256 or img.height < 256:
        return b"", f"imagen demasiado pequeña ({img.width}x{img.height})"
    aviso = None
    try:
        a, b = (float(x) for x in aspecto.split(":"))
        if abs(img.width / img.height - a / b) > 0.12:
            aviso = f"proporción {img.width}x{img.height} distinta de {aspecto}"
    except ValueError:
        pass
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), aviso


def _quitar_fondo(origen: Path, destino: Path) -> bool:
    """Por defecto NO: el montaje recorta el fondo liso por su cuenta (rápido). rembg está
    instalado para las miniaturas, pero en las escenas tardaría minutos por imagen en un PC
    normal; solo se usa si se pide con XANDART_REMBG_ESCENAS=1."""
    import os

    if os.environ.get("XANDART_REMBG_ESCENAS") != "1":
        return False
    try:
        from rembg import remove
    except Exception:  # noqa: BLE001
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(remove(origen.read_bytes()))
    return True


def _seleccion(esc: EscenasV2, primeras: int | None, ids: list[int] | None) -> list[Escena]:
    if ids:
        quiero = set(ids)
        return [e for e in esc.escenas if e.id in quiero]
    return esc.escenas[:primeras] if primeras else list(esc.escenas)


def total_a_generar(esc: EscenasV2) -> int:
    """Imágenes nuevas que pide el video completo: escenas con accion 'generar' + assets."""
    return sum(1 for e in esc.escenas if e.visual.accion == "generar") + len(esc.assets)


def tope_llamadas(esc: EscenasV2, config: ConfigCostos, reintentos: int) -> int:
    tasa = config.consumo.get("tasa_reintentos_imagen", 0.1)
    return math.ceil(total_a_generar(esc) * (1 + max(tasa, 0.0))) + reintentos


def generar_imagenes(carpeta: CarpetaProyecto, *, primeras: int | None = None, ids: list[int] | None = None,
                     solo_assets: list[str] | None = None,
                     proveedor: Proveedor | None = None, nombre_proveedor: str | None = None,
                     permiso: bool = False, config: ConfigCostos | None = None,
                     avisar: Callable[[str], None] = print) -> Reporte:
    config = config or ConfigCostos.cargar()
    ajustes = leer_config("proveedores.json")["imagenes"]
    proveedor = proveedor or crear_proveedor(config, ajustes, nombre_proveedor)
    reintentos = int(ajustes.get("reintentos_por_escena", 2))
    aspecto = ajustes.get("relacion_aspecto", "16:9")

    proyecto = carpeta.cargar()
    estilo: Estilo = cargar_estilo(proyecto.estilo)
    esc = carpeta.cargar_escenas()
    errores = esc.errores_contra_estilo(estilo)
    if errores:
        raise ValueError("escenas.json no cuadra con el estilo: " + "; ".join(errores[:5]))
    personaje = prompts.personaje_del_proyecto(carpeta.ruta, estilo)
    libro = carpeta.libro(config)
    ruta_manifiesto = carpeta.ruta / "imagenes" / "manifiesto.json"
    manifiesto: dict = leer_json(ruta_manifiesto) if ruta_manifiesto.exists() else {}
    reporte = Reporte(proveedor.nombre, proveedor.modelo)

    seleccion = [] if solo_assets is not None else _seleccion(esc, primeras, ids)
    assets = {a.id: a for a in esc.assets}
    asset_personaje = next((a for a in esc.assets if a.tipo == "personaje"), None)

    # 1) assets que necesitan las escenas elegidas (primero, porque son referencia)
    necesarios: list[AssetDef] = []
    for e in seleccion:
        if e.visual.accion != "generar":
            continue
        refs = list(e.visual.referencias)
        if asset_personaje and prompts.usa_personaje(e, estilo) and asset_personaje.id not in refs:
            refs.append(asset_personaje.id)
        for r in refs:
            if r in assets and assets[r] not in necesarios:
                necesarios.append(assets[r])

    if solo_assets is not None:
        faltan = [x for x in solo_assets if x not in assets]
        if faltan:
            raise ValueError(f"assets no declarados: {faltan}")
        necesarios = [assets[x] for x in solo_assets]
    trabajos: list[Trabajo] = []
    for a in necesarios:
        trabajos.append(Trabajo(f"asset:{a.id}", prompts.prompt_de_asset(a, estilo, personaje), [],
                                carpeta.ruta / a.archivo, a.quitar_fondo))
    for e in seleccion:
        if e.visual.accion == "reusar":
            reporte.reusadas.append(f"escena:{e.id}")
            continue
        if e.visual.accion == "componer":
            reporte.pendientes.append(f"escena:{e.id} (composición con Pillow: pendiente)")
            continue
        refs = [r for r in e.visual.referencias if r in assets]
        if asset_personaje and prompts.usa_personaje(e, estilo) and asset_personaje.id not in refs:
            refs.append(asset_personaje.id)
        trabajos.append(Trabajo(f"escena:{e.id}", prompts.prompt_de_escena(e, estilo, personaje),
                                [carpeta.ruta / assets[r].archivo for r in refs],
                                carpeta.ruta / (e.visual.archivo or f"imagenes/escena_{e.id:03d}.png"),
                                e.visual.quitar_fondo))

    tope = tope_llamadas(esc, config, reintentos)
    llamadas_previas = sum(1 for x in libro.entradas() if x["modulo"] == MODULO)

    for t in trabajos:
        faltan = [r for r in t.referencias if not r.exists()]
        if faltan:
            reporte.fallidas[t.clave] = f"falta la referencia {faltan[0].name}"
            continue
        huella = _huella(t, proveedor.modelo)
        previo = manifiesto.get(t.clave)
        if previo is None and t.clave.startswith("asset:") and t.destino.exists():
            # Asset del canal que ya existe (p. ej. la mascota de un video anterior):
            # se adopta tal cual y no se vuelve a pagar (5.3: los assets se reutilizan).
            manifiesto[t.clave] = {"archivo": str(t.destino.relative_to(carpeta.ruta)), "sin_fondo": None,
                                   "huella": huella, "prompt": t.prompt, "referencias": [],
                                   "proveedor": "existente", "modelo": "", "intentos": 0,
                                   "costo_usd": 0.0, "aviso": None}
            escribir_json(ruta_manifiesto, manifiesto)
            reporte.ya_estaban.append(t.clave)
            continue
        if previo and previo.get("huella") != huella and t.destino.exists() and _misma_de_antes(t, proveedor.modelo, previo):
            # pagada con la plantilla de antes de un arreglo (ver arreglos.py): es la misma imagen
            manifiesto[t.clave] = {**previo, "huella": huella, "prompt": t.prompt}
            escribir_json(ruta_manifiesto, manifiesto)
            previo = manifiesto[t.clave]
        if previo and previo.get("huella") == huella and t.destino.exists():
            reporte.ya_estaban.append(t.clave)
            continue

        costo_trabajo, aviso_calidad, ultimo_error, exito = 0.0, None, "", False
        for intento in range(1 + reintentos):
            if not permiso and llamadas_previas + reporte.llamadas >= tope:
                reporte.frenado = (f"se alcanzó el tope de {tope} llamadas de imagen para este video; "
                                   "hace falta permiso explícito para seguir")
                break
            estimado = proveedor.estimar_usd(t.prompt, t.referencias)
            try:
                libro.autorizar(estimado, permiso=permiso)
            except FrenoPresupuesto as ex:
                reporte.frenado = str(ex)
                break
            reporte.llamadas += 1
            try:
                res = proveedor.generar(t.prompt, t.referencias)
            except ErrorProveedor as ex:
                ultimo_error = str(ex)
                if ex.uso and ex.uso.costo_usd:
                    libro.registrar(modulo=MODULO, proveedor=proveedor.nombre, modelo=proveedor.modelo,
                                    unidades=ex.uso.unidades(), costo_usd=ex.uso.costo_usd,
                                    detalle=f"{t.clave} intento {intento + 1} fallido")
                    costo_trabajo += ex.uso.costo_usd
                avisar(f"  {t.clave}: intento {intento + 1} falló ({ex})")
                if not ex.reintentable:
                    break
                continue
            libro.registrar(modulo=MODULO, proveedor=res.proveedor, modelo=res.modelo,
                            unidades={**res.uso.unidades(), "referencias": len(t.referencias)},
                            costo_usd=res.uso.costo_usd, detalle=f"{t.clave} intento {intento + 1}")
            costo_trabajo += res.uso.costo_usd
            try:
                png, aviso_calidad = _validar_png(res.png, aspecto)
            except Exception as ex:  # noqa: BLE001
                ultimo_error = f"la imagen no se puede abrir: {ex}"
                continue
            if not png:
                ultimo_error = aviso_calidad or "imagen inválida"
                continue
            t.destino.parent.mkdir(parents=True, exist_ok=True)
            t.destino.write_bytes(png)
            sin_fondo = None
            if t.quitar_fondo:
                sf = t.destino.parent / "sin_fondo" / t.destino.name
                if _quitar_fondo(t.destino, sf):
                    sin_fondo = str(sf.relative_to(carpeta.ruta))
            manifiesto[t.clave] = {
                "archivo": str(t.destino.relative_to(carpeta.ruta)), "sin_fondo": sin_fondo,
                "huella": huella, "prompt": t.prompt, "referencias": [r.name for r in t.referencias],
                "proveedor": res.proveedor, "modelo": res.modelo, "intentos": intento + 1,
                "costo_usd": round(costo_trabajo, 6), "aviso": aviso_calidad,
            }
            escribir_json(ruta_manifiesto, manifiesto)  # reanudable tras cada imagen
            reporte.generadas.append(t.clave)
            reporte.costos_por_imagen[t.clave] = costo_trabajo
            if aviso_calidad:
                reporte.avisos.append(f"{t.clave}: {aviso_calidad}")
            if t.quitar_fondo and not sin_fondo:
                pass                                    # el montaje recorta el fondo liso
            avisar(f"  {t.clave}: lista · {formato_usd(costo_trabajo)} · {formato_cop(config.a_cop(costo_trabajo))}")
            exito = True
            break
        reporte.costo_usd += costo_trabajo
        if reporte.frenado and not exito:
            reporte.pendientes.append(t.clave)
            break
        if not exito:
            reporte.fallidas[t.clave] = ultimo_error or "sin imagen tras los reintentos"
    return reporte


@dataclass
class Proyeccion:
    imagenes_video: int
    costo_medio_usd: float
    total_usd: float
    total_cop: float
    base: str


def proyectar(carpeta: CarpetaProyecto, config: ConfigCostos | None = None) -> Proyeccion | None:
    """Costo de imágenes del video completo con el costo REAL medido por imagen
    (con referencias y reintentos incluidos)."""
    config = config or ConfigCostos.cargar()
    libro = carpeta.libro(config)
    ruta = carpeta.ruta / "imagenes" / "manifiesto.json"
    if not ruta.exists():
        return None
    hechas = len(leer_json(ruta))
    gastado = sum(x["costo_usd"] for x in libro.entradas() if x["modulo"] == MODULO)
    if not hechas:
        return None
    medio = gastado / hechas
    total = total_a_generar(carpeta.cargar_escenas())
    reales = {x["proveedor"] for x in libro.entradas() if x["modulo"] == MODULO}
    base = "SIMULADO (no es un costo real)" if reales == {"simulado"} else f"medido en {hechas} imágenes"
    return Proyeccion(total, medio, medio * total, config.a_cop(medio * total), base)


def _fuente(tamano: int):
    """Una fuente con tildes y eñes; la de Pillow por defecto no las tiene."""
    from PIL import ImageFont

    for ruta in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/System/Library/Fonts/Supplemental/Arial.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def hoja_de_contacto(carpeta: CarpetaProyecto, claves: list[str], destino: Path, columnas: int = 2) -> Path | None:
    """Una sola imagen con las generadas, su escena, su costo y la narración."""
    from PIL import Image, ImageDraw

    ruta = carpeta.ruta / "imagenes" / "manifiesto.json"
    if not ruta.exists() or not claves:
        return None
    manifiesto = leer_json(ruta)
    narr = {f"escena:{e.id}": e.narracion for e in carpeta.cargar_escenas().escenas}
    config = ConfigCostos.cargar()
    ancho, alto, pie = 640, 360, 58
    filas = math.ceil(len(claves) / columnas)
    hoja = Image.new("RGB", (columnas * ancho, filas * (alto + pie)), (18, 16, 24))
    d = ImageDraw.Draw(hoja)
    fuente = _fuente(15)
    for i, clave in enumerate(claves):
        m = manifiesto.get(clave)
        if not m:
            continue
        x, y = (i % columnas) * ancho, (i // columnas) * (alto + pie)
        img = Image.open(carpeta.ruta / m["archivo"]).convert("RGB")
        img.thumbnail((ancho, alto))
        hoja.paste(img, (x + (ancho - img.width) // 2, y))
        costo = formato_cop(config.a_cop(m.get("costo_usd", 0)))
        d.text((x + 8, y + alto + 6), f"{clave} · {costo} · {m['intentos']} intento(s)", fill=(255, 210, 120), font=fuente)
        d.text((x + 8, y + alto + 26), (narr.get(clave) or "")[:80], fill=(225, 222, 235), font=fuente)
    destino.parent.mkdir(parents=True, exist_ok=True)
    hoja.save(destino)
    return destino
