"""Plantilla de miniatura «texto_izquierda_retrato_derecha» (configurable por canal).

Capas, de atrás hacia adelante, en un lienzo de 1280x720:
1. Fondo 16:9 oscuro, distinto en cada video: se rota entre los fondos de la carpeta del canal
   (nunca el mismo dos veces seguidas) o se genera uno nuevo con el proveedor de imágenes actual.
   Si la carpeta está vacía, Xandart dibuja 3 fondos de red neuronal con código (gratis).
2. Degradado negro de izquierda a derecha (80 % a la izquierda, 0 % al 60 % del ancho).
3. Retrato PNG con transparencia del canal (cabeza y hombros), anclado a la derecha, del 45 % al
   50 % del ancho, con un resplandor suave del color de acento detrás.
4. Texto: 3 o 4 líneas en MAYÚSCULAS, fuente Anton, máximo 3 palabras por línea; el tamaño se
   ajusta para que la línea más larga llene la zona izquierda. Cada línea es blanca o del color
   de acento (en la entrada, una línea entre asteriscos va completa en color).
5. Rótulo opcional del canal debajo del bloque (Barlow Light, blanco al 80 %).

El color de acento sale de dos paletas según el fondo: azul o morado → turquesa; negro, dorado o
cálido → amarillo. Se puede forzar a mano (en el canal o en cada video).

Entrada del texto: líneas separadas por «/», la línea de color entre asteriscos:
«ENFÓCATE EN / *EMPEZAR* / NO EN TENER GANAS».
"""
from __future__ import annotations

import colorsys
import io
import json
import math
import random
import re
import unicodedata
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pydantic import BaseModel, ConfigDict, field_validator

from ..config import escribir_json, leer_json

LAYOUT = "texto_izquierda_retrato_derecha"
W, H = 1280, 720
MARGEN = 48
ZONA_TEXTO = 0.56            # fracción del ancho para el bloque de texto (desde la izquierda)
INTERLINEADO = 0.95
BORDE = 6
RETRATO_MIN, RETRATO_MAX = 0.45, 0.50
TURQUESA, AMARILLO = "#19D3C5", "#FFD400"
PROMPT_FONDO = ("fondo oscuro azul profundo con red neuronal luminosa y destellos, sin texto, sin personas, "
                "espacio limpio a la izquierda")
MAX_JPG = 2 * 1024 * 1024
FUENTES = Path(__file__).resolve().parent.parent / "fuentes"
FUENTE_TEXTO = FUENTES / "Anton-Regular.ttf"
FUENTE_ROTULO = FUENTES / "Barlow-Light.ttf"
EXT_FONDO = (".jpg", ".jpeg", ".png", ".webp")

# reglas del texto (planificador y revisión de lo que se escribe a mano)
MIN_LINEAS, MAX_LINEAS = 3, 4
MAX_PALABRAS_LINEA = 3
MIN_PALABRAS, MAX_PALABRAS = 4, 7
MAX_CARACTERES_LINEA = 14


class ConfigTexto(BaseModel):
    """Lo que cada canal configura de esta plantilla (vive en su carpeta de plantilla de miniatura)."""
    model_config = ConfigDict(extra="forbid")
    canal: str
    nombre: str
    layout: Literal["texto_izquierda_retrato_derecha"] = LAYOUT
    acento: str = TURQUESA                 # paleta fría: fondos azules o morados
    acento_calido: str = AMARILLO          # segunda paleta: fondos negros, dorados o cálidos
    paleta: Literal["auto", "fria", "calida"] = "auto"
    retrato: str | None = None             # PNG con transparencia dentro de la carpeta del canal
    rotulo: str = ""
    fuente_fondos: Literal["carpeta", "generar"] = "carpeta"
    carpeta_fondos: str = "fondos"         # dentro de la carpeta del canal
    prompt_fondo: str = PROMPT_FONDO

    @field_validator("acento", "acento_calido")
    @classmethod
    def _color(cls, v: str) -> str:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError(f"color no válido: {v} (usa #RRGGBB)")
        return v.upper()

    @field_validator("rotulo")
    @classmethod
    def _rotulo(cls, v: str) -> str:
        return " ".join(v.split())[:60]


# ------------------------------------------------------------------ configuración del canal

def carpeta_canal(canal: str) -> Path:
    from .plantilla import ruta_plantilla

    return ruta_plantilla(canal)


def es_de_texto(canal: str) -> bool:
    try:
        ruta = carpeta_canal(canal) / "plantilla.json"
    except ValueError:
        return False
    return ruta.exists() and leer_json(ruta).get("layout") == LAYOUT


def cargar_config(canal: str) -> ConfigTexto:
    ruta = carpeta_canal(canal) / "plantilla.json"
    if not ruta.exists() or leer_json(ruta).get("layout") != LAYOUT:
        raise ValueError(f"el canal «{canal}» no usa la plantilla {LAYOUT}")
    return ConfigTexto.model_validate(leer_json(ruta))


def guardar_config(cfg: ConfigTexto) -> Path:
    from .plantilla import _para_escribir

    carpeta = _para_escribir(cfg.canal)
    escribir_json(carpeta / "plantilla.json", cfg.model_dump())
    return carpeta


def cambiar_config(canal: str, cambios: dict) -> ConfigTexto:
    permitidos = {"nombre", "acento", "acento_calido", "paleta", "rotulo", "fuente_fondos", "prompt_fondo"}
    datos = cargar_config(canal).model_dump()
    datos.update({k: v for k, v in cambios.items() if k in permitidos})
    cfg = ConfigTexto.model_validate(datos)
    guardar_config(cfg)
    return cfg


def subir_retrato(canal: str, datos: bytes) -> ConfigTexto:
    """El retrato tiene que traer transparencia (PNG sin fondo): se guarda recortado a lo visible."""
    cfg = cargar_config(canal)
    im = Image.open(io.BytesIO(datos))
    im.load()
    if im.mode not in ("RGBA", "LA", "P") or im.convert("RGBA").getchannel("A").getextrema()[0] > 250:
        raise ValueError("el retrato tiene que ser un PNG sin fondo (con transparencia)")
    im = im.convert("RGBA")
    caja = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if caja:
        im = im.crop(caja)
    if im.height > 1600:
        im = im.resize((round(im.width * 1600 / im.height), 1600), Image.Resampling.LANCZOS)
    carpeta = guardar_config(cfg)
    im.save(carpeta / "retrato.png")
    cfg.retrato = "retrato.png"
    guardar_config(cfg)
    return cfg


def carpeta_fondos(cfg: ConfigTexto) -> Path:
    from .plantilla import _para_escribir

    return _para_escribir(cfg.canal) / cfg.carpeta_fondos


def subir_fondo(canal: str, datos: bytes, nombre: str) -> list[str]:
    cfg = cargar_config(canal)
    im = Image.open(io.BytesIO(datos)).convert("RGB")
    im = _cubrir(im, W, H)
    base = re.sub(r"[^\w\-]+", "_", Path(nombre).stem).strip("_")[:40] or "fondo"
    carpeta = carpeta_fondos(cfg)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino, k = carpeta / f"{base}.jpg", 2
    while destino.exists():
        destino, k = carpeta / f"{base}_{k}.jpg", k + 1
    im.save(destino, quality=92)
    return fondos_disponibles(cfg)


def fondos_disponibles(cfg: ConfigTexto) -> list[str]:
    c = carpeta_fondos(cfg)
    return sorted(p.name for p in c.glob("*") if p.suffix.lower() in EXT_FONDO) if c.exists() else []


def crear_canal(clave: str = "mentalidad-imparable", nombre: str = "Mentalidad Imparable") -> ConfigTexto:
    """Crea el canal (si no existe) con esta plantilla y deja 3 fondos dibujados con código. Lo que el
    canal ya tenga configurado no se toca."""
    from .plantilla import _validar

    _validar(clave)
    ruta = carpeta_canal(clave) / "plantilla.json"
    if ruta.exists():
        if leer_json(ruta).get("layout") != LAYOUT:
            raise ValueError(f"el canal «{clave}» ya tiene otra plantilla de miniatura")
        cfg = cargar_config(clave)
    else:
        cfg = ConfigTexto(canal=clave, nombre=nombre)
        guardar_config(cfg)
    asegurar_fondos(cfg)
    _registrar_canal(clave, nombre, cfg)
    return cfg


def _registrar_canal(clave: str, nombre: str, cfg: ConfigTexto) -> None:
    """En la base (si la plataforma está activa): el canal y su plantilla de miniatura."""
    try:
        from sqlalchemy import select

        from ..plataforma import contexto, db
        from ..plataforma.modelos import Canal, PlantillaMiniatura
    except ImportError:
        return
    esp = contexto.espacio_actual()
    if not esp:
        return
    with db.sesion() as s:
        p = s.scalar(select(PlantillaMiniatura).where(PlantillaMiniatura.espacio_id == esp,
                                                      PlantillaMiniatura.clave == clave))
        if p is None:
            p = PlantillaMiniatura(espacio_id=esp, clave=clave, nombre=f"{nombre} · texto + retrato",
                                   descripcion="Texto grande a la izquierda y retrato a la derecha",
                                   datos=cfg.model_dump(), origen={"creado": "plantilla texto_retrato"})
            s.add(p)
            s.flush()
        c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave))
        if c is None:
            c = Canal(espacio_id=esp, clave=clave, nombre=nombre, ajustes={"miniatura": LAYOUT})
            s.add(c)
        if c.plantilla_miniatura_id is None:
            c.plantilla_miniatura_id = p.id
        s.flush()


# ------------------------------------------------------------------ texto

def _sin_tildes(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def parsear(texto: str) -> list[tuple[str, bool]]:
    """«ENFÓCATE EN / *EMPEZAR* / NO EN TENER GANAS» → [(línea, en_color), …] en mayúsculas."""
    lineas = []
    for parte in (texto or "").split("/"):
        p = " ".join(parte.split())
        if not p:
            continue
        color = len(p) > 2 and p.startswith("*") and p.endswith("*")
        dentro = p[1:-1].strip() if color else p
        if "*" in dentro:
            raise ValueError("el color va por línea completa: escribe la línea entera entre asteriscos (*ASÍ*)")
        if not dentro:
            raise ValueError("hay una línea vacía")
        lineas.append((dentro.upper(), color))
    if not lineas:
        raise ValueError("escribe el texto de la miniatura (las líneas se separan con «/»)")
    if len(lineas) > MAX_LINEAS + 1:
        raise ValueError(f"demasiadas líneas (máximo {MAX_LINEAS})")
    return lineas


def formatear(lineas: list[tuple[str, bool]]) -> str:
    return " / ".join(f"*{t}*" if c else t for t, c in lineas)


# tildes que se escapan seguido en las órdenes de las miniaturas (palabra entera, en mayúsculas)
TILDES = {
    "ENFOCATE": "ENFÓCATE", "VUELVETE": "VUÉLVETE", "OBLIGATE": "OBLÍGATE", "CONCENTRATE": "CONCÉNTRATE",
    "DEJATE": "DÉJATE", "ATREVETE": "ATRÉVETE", "LEVANTATE": "LEVÁNTATE", "OLVIDATE": "OLVÍDATE",
    "ACOSTUMBRATE": "ACOSTÚMBRATE", "COMPROMETETE": "COMPROMÉTETE", "DEDICATE": "DEDÍCATE", "EXIGETE": "EXÍGETE",
    "PREPARATE": "PREPÁRATE", "ALEJATE": "ALÉJATE", "MUEVETE": "MUÉVETE", "ENTRENATE": "ENTRÉNATE",
    "MAS": "MÁS", "DIAS": "DÍAS", "DIA": "DÍA", "EXITO": "ÉXITO", "ACCION": "ACCIÓN", "PASION": "PASIÓN",
    "DECISION": "DECISIÓN", "OBSESION": "OBSESIÓN", "TU": "TÚ", "MINIMO": "MÍNIMO", "MAXIMO": "MÁXIMO",
    "HABITO": "HÁBITO", "HABITOS": "HÁBITOS", "ANO": "AÑO", "ANOS": "AÑOS", "MANANA": "MAÑANA",
    "DISCIPLINATE": "DISCIPLÍNATE", "OLVIDALO": "OLVÍDALO", "HAZLO": "HAZLO", "LAMENTATE": "LAMÉNTATE",
}


def corregir_tildes(texto: str) -> tuple[str, list[str]]:
    """Arregla las tildes que más se escapan (ENFOCATE → ENFÓCATE). Devuelve el texto y lo cambiado."""
    cambios = []

    def arreglo(m: re.Match) -> str:
        palabra = m.group(0)
        bien = TILDES.get(palabra.upper())
        if bien and bien != palabra.upper():
            cambios.append(f"{palabra} → {bien}")
            return bien
        return palabra

    return re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", arreglo, texto), cambios


VACIAS = {"de", "la", "el", "los", "las", "un", "una", "y", "o", "en", "a", "que", "por", "para", "con", "sin",
          "no", "tu", "su", "lo", "al", "del", "es", "se", "mi", "te", "como", "mas", "muy", "este", "esta"}


def _raiz(p: str) -> str:
    return _sin_tildes(p.lower())[:5]


def palabras_principales(titulo: str) -> set[str]:
    return {_raiz(w) for w in re.findall(r"[\wáéíóúñü]+", titulo.lower()) if len(w) > 3 and w not in VACIAS}


def revisar(texto: str, titulo: str = "") -> list[str]:
    """Problemas del texto según las reglas de la plantilla (lista vacía = cumple)."""
    try:
        lineas = parsear(texto)
    except ValueError as ex:
        return [str(ex)]
    problemas = []
    if not MIN_LINEAS <= len(lineas) <= MAX_LINEAS:
        problemas.append(f"tiene {len(lineas)} líneas (van de {MIN_LINEAS} a {MAX_LINEAS})")
    palabras = [w for t, _ in lineas for w in t.split()]
    if not MIN_PALABRAS <= len(palabras) <= MAX_PALABRAS:
        problemas.append(f"tiene {len(palabras)} palabras (van de {MIN_PALABRAS} a {MAX_PALABRAS})")
    for t, _ in lineas:
        if len(t.split()) > MAX_PALABRAS_LINEA:
            problemas.append(f"«{t}» tiene más de {MAX_PALABRAS_LINEA} palabras")
        if len(t) > MAX_CARACTERES_LINEA:
            problemas.append(f"«{t}» pasa de {MAX_CARACTERES_LINEA} letras")
    en_color = sum(1 for _, c in lineas if c)
    if not 1 <= en_color <= 2:
        problemas.append("va 1 o 2 líneas en color (entre asteriscos)")
    if en_color == len(lineas):
        problemas.append("no todas las líneas pueden ir en color")
    repetidas = sorted({w for w in palabras if len(w) > 3 and w.lower() not in VACIAS
                        and _raiz(w) in palabras_principales(titulo)})
    if repetidas:
        problemas.append(f"repite palabras del título: {', '.join(repetidas)}")
    _, tildes = corregir_tildes(formatear(lineas))
    if tildes:
        problemas.append("faltan tildes: " + ", ".join(tildes))
    return problemas


# ------------------------------------------------------------------ fondos

def _cubrir(im: Image.Image, w: int, h: int) -> Image.Image:
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * k)), max(h, round(im.height * k))), Image.Resampling.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


TONOS = {   # fondo, nodos/líneas, destellos
    "azul": ((3, 8, 28), (10, 46, 110), (90, 200, 255)),
    "morado": ((10, 4, 26), (52, 18, 110), (200, 120, 255)),
    "dorado": ((6, 5, 4), (60, 40, 10), (255, 196, 70)),
}


def fondo_neuronal(semilla: int = 1, tono: str = "azul") -> Image.Image:
    """Fondo oscuro con una red neuronal luminosa y destellos, dibujado con código (gratis). Lo
    brillante va a la derecha; la izquierda queda limpia para el texto."""
    rng = random.Random(semilla)
    base_c, medio_c, luz_c = (np.array(c, np.float32) for c in TONOS[tono])
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W * 0.72, H * 0.42
    d = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    mezcla = np.clip(1 - d * 1.5, 0, 1)[..., None] ** 1.6
    img = base_c + (medio_c - base_c) * mezcla
    lienzo = Image.fromarray(np.clip(img, 0, 255).astype("uint8"), "RGB")
    # red: nodos sobre todo a la derecha, unidos con sus vecinos
    nodos = [(rng.uniform(W * 0.30, W * 1.02) if rng.random() < 0.85 else rng.uniform(0, W * 0.3),
              rng.uniform(-20, H + 20)) for _ in range(70)]
    capa = Image.new("RGB", (W, H), (0, 0, 0))
    dr = ImageDraw.Draw(capa)
    luz = tuple(int(v) for v in luz_c)
    for i, (x, y) in enumerate(nodos):
        vecinos = sorted(nodos, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)[1:4]
        for vx, vy in vecinos:
            fuerza = 0.25 + 0.75 * min(1.0, x / W) * rng.uniform(0.4, 1.0)
            dr.line([(x, y), (vx, vy)], fill=tuple(int(c * fuerza * 0.55) for c in luz), width=1)
    for x, y in nodos:
        r = rng.choice((2, 2, 3, 4))
        fuerza = 0.3 + 0.7 * min(1.0, x / W)
        dr.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * fuerza) for c in luz))
    brillo = capa.filter(ImageFilter.GaussianBlur(6))
    capa = Image.fromarray(np.clip(np.asarray(capa, np.float32) + np.asarray(brillo, np.float32) * 1.6, 0, 255)
                           .astype("uint8"))
    # destellos suaves
    destellos = np.zeros((H, W), np.float32)
    for _ in range(5):
        fx, fy, fr = rng.uniform(W * 0.5, W), rng.uniform(H * 0.1, H * 0.9), rng.uniform(30, 120)
        destellos += np.exp(-(((xx - fx) ** 2 + (yy - fy) ** 2) / (2 * fr ** 2))) * rng.uniform(0.25, 0.6)
    total = np.asarray(lienzo, np.float32) + np.asarray(capa, np.float32) + destellos[..., None] * luz_c * 0.55
    # la izquierda más oscura y limpia
    total *= (0.55 + 0.45 * np.clip(xx / (W * 0.55), 0, 1))[..., None]
    return Image.fromarray(np.clip(total, 0, 255).astype("uint8"), "RGB")


def asegurar_fondos(cfg: ConfigTexto) -> list[str]:
    """Si la carpeta de fondos del canal está vacía, deja 3 dibujados con código (azul, morado y
    dorado: así las dos paletas se usan)."""
    if fondos_disponibles(cfg):
        return fondos_disponibles(cfg)
    carpeta = carpeta_fondos(cfg)
    carpeta.mkdir(parents=True, exist_ok=True)
    for k, tono in enumerate(("azul", "morado", "dorado"), 1):
        fondo_neuronal(k * 17, tono).save(carpeta / f"red_neuronal_{tono}.jpg", quality=92)
    return fondos_disponibles(cfg)


def _rotacion(cfg: ConfigTexto) -> Path:
    return carpeta_fondos(cfg) / "rotacion.json"


def siguiente_fondo(cfg: ConfigTexto, evitar: str | None = None) -> Path:
    """El siguiente fondo de la carpeta, en rueda: nunca el mismo dos veces seguidas en el canal."""
    nombres = asegurar_fondos(cfg)
    ruta = _rotacion(cfg)
    estado = leer_json(ruta) if ruta.exists() else {}
    ultimo = estado.get("ultimo")
    i = (nombres.index(ultimo) + 1) if ultimo in nombres else 0
    elegido = nombres[i % len(nombres)]
    if len(nombres) > 1 and elegido in (ultimo, evitar):
        elegido = nombres[(i + 1) % len(nombres)]
        if elegido in (ultimo, evitar) and len(nombres) > 2:
            elegido = nombres[(i + 2) % len(nombres)]
    escribir_json(ruta, {"ultimo": elegido})
    return carpeta_fondos(cfg) / elegido


def generar_fondo(cfg: ConfigTexto, destino: Path, libro, permiso: bool = False, proveedor=None) -> Path:
    """Un fondo nuevo con el proveedor de imágenes actual (Google). Frena antes de gastar si pasa el
    máximo. Se guarda también en la carpeta del canal para poder rotarlo después."""
    from ..config import ConfigCostos, leer_config
    from ..imagenes.proveedores import crear_proveedor

    proveedor = proveedor or crear_proveedor(ConfigCostos.cargar(), leer_config("proveedores.json")["imagenes"])
    pedido = f"{cfg.prompt_fondo}. Relación de aspecto 16:9, sin texto, sin letras, sin personas."
    libro.autorizar(proveedor.estimar_usd(pedido, []), permiso=permiso)
    r = proveedor.generar(pedido, [])
    libro.registrar(modulo="miniatura", proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                    costo_usd=r.uso.costo_usd, detalle="miniatura texto+retrato · fondo nuevo")
    im = _cubrir(Image.open(io.BytesIO(r.png)).convert("RGB"), W, H)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, quality=92)
    carpeta = carpeta_fondos(cfg)
    carpeta.mkdir(parents=True, exist_ok=True)
    k = len(list(carpeta.glob("generado_*.jpg"))) + 1
    im.save(carpeta / f"generado_{k:03d}.jpg", quality=92)
    escribir_json(_rotacion(cfg), {"ultimo": f"generado_{k:03d}.jpg"})
    return destino


def paleta_del_fondo(fondo: Image.Image) -> Literal["fria", "calida"]:
    """Azul o morado → fría (turquesa). Negro, dorado o cálido → cálida (amarillo)."""
    peq = np.asarray(fondo.convert("RGB").resize((96, 54)), np.float32) / 255
    hsv = np.array([colorsys.rgb_to_hsv(*px) for px in peq.reshape(-1, 3)])
    peso = hsv[:, 1] * hsv[:, 2]                    # lo que tiene color de verdad
    if peso.sum() < 0.04 * len(peso) * 0.25:        # casi sin color: fondo negro o gris
        return "calida"
    angulo = hsv[:, 0] * 2 * math.pi
    tono = math.degrees(math.atan2((np.sin(angulo) * peso).sum(), (np.cos(angulo) * peso).sum())) % 360
    return "fria" if 175 <= tono <= 320 else "calida"


def color_de_acento(cfg: ConfigTexto, fondo: Image.Image, forzada: str | None = None) -> tuple[str, str]:
    paleta = forzada if forzada in ("fria", "calida") else (cfg.paleta if cfg.paleta != "auto" else None)
    paleta = paleta or paleta_del_fondo(fondo)
    return paleta, (cfg.acento if paleta == "fria" else cfg.acento_calido)


# ------------------------------------------------------------------ composición

def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _degradado() -> Image.Image:
    x = np.arange(W, dtype=np.float32)
    alfa = np.clip(1 - x / (W * 0.60), 0, 1) * 0.80 * 255
    capa = np.zeros((H, W, 4), np.uint8)
    capa[..., 3] = np.broadcast_to(alfa.astype(np.uint8), (H, W))
    return Image.fromarray(capa, "RGBA")


def _poner_retrato(lienzo: Image.Image, retrato: Image.Image, acento: str) -> int:
    """Cabeza y hombros anclados a la derecha, del 45 % al 50 % del ancho. Devuelve dónde empieza."""
    caja = retrato.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if caja:
        retrato = retrato.crop(caja)
    ancho = W * (RETRATO_MIN + RETRATO_MAX) / 2
    k = ancho / retrato.width
    if retrato.height * k < H * 0.72:              # retrato muy apaisado: que no quede chiquito
        k = min(W * RETRATO_MAX / retrato.width, H * 0.72 / retrato.height)
    k = max(k, W * RETRATO_MIN / retrato.width)
    r = retrato.resize((max(1, round(retrato.width * k)), max(1, round(retrato.height * k))), Image.Resampling.LANCZOS)
    x = W - r.width
    y = H - r.height if r.height <= H else 0       # muy alto: se ve la cabeza y se cortan los hombros
    # resplandor del color de acento detrás (blur 40 px)
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    color = Image.new("RGBA", r.size, _rgb(acento) + (255,))
    color.putalpha(r.getchannel("A").point(lambda a: int(a * 0.9)))
    halo.alpha_composite(color.crop((0, 0, r.width, min(r.height, H - y))), (x, y))
    lienzo.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40)))
    recorte = r.crop((0, 0, r.width, min(r.height, H - y)))
    lienzo.alpha_composite(recorte, (x, y))
    return x


def _fuente(ruta: Path, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ruta), max(8, int(tam)))


def _medidas_texto(lineas: list[tuple[str, bool]], ancho_zona: float, alto_max: float) -> int:
    """Tamaño para que la línea más larga llene la zona (sin pasar del alto disponible)."""
    ref = _fuente(FUENTE_TEXTO, 200)
    mayor = max(ref.getbbox(t)[2] - ref.getbbox(t)[0] for t, _ in lineas)
    tam = 200 * (ancho_zona - 2 * BORDE) / max(1, mayor)          # el borde suma 6 px a cada lado
    alto = tam * (INTERLINEADO * (len(lineas) - 1) + 1.0)
    if alto > alto_max:
        tam *= alto_max / alto
    return int(tam)


def componer(fondo: Image.Image, texto: str, cfg: ConfigTexto, retrato: Image.Image | None,
             acento: str) -> Image.Image:
    lineas = parsear(texto)
    img = _cubrir(fondo.convert("RGB"), W, H).convert("RGBA")
    img.alpha_composite(_degradado())
    inicio_retrato = W
    if retrato is not None:
        inicio_retrato = _poner_retrato(img, retrato.convert("RGBA"), acento)
    x0 = MARGEN
    x1 = min(W * ZONA_TEXTO, inicio_retrato + 40)          # que el texto no se meta en la cara
    rot_tam = 30
    alto_rotulo = (rot_tam + 22) if cfg.rotulo else 0
    tam = _medidas_texto(lineas, x1 - x0, H - 2 * MARGEN - alto_rotulo)
    f = _fuente(FUENTE_TEXTO, tam)
    paso = tam * INTERLINEADO
    caja_ref = f.getbbox("ÁNG", stroke_width=BORDE)        # de lo más alto (tildes) a la base
    alto_linea = caja_ref[3] - caja_ref[1]
    bloque = paso * (len(lineas) - 1) + alto_linea
    y0 = (H - bloque - alto_rotulo) / 2 - caja_ref[1]
    texto_capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dt, ds = ImageDraw.Draw(texto_capa), ImageDraw.Draw(sombra)
    for k, (linea, color) in enumerate(lineas):
        y = y0 + k * paso
        x = x0 - f.getbbox(linea, stroke_width=BORDE)[0]
        relleno = _rgb(acento) if color else (255, 255, 255)
        ds.text((x + 4, y + 8), linea, font=f, fill=(0, 0, 0, 170), stroke_width=BORDE, stroke_fill=(0, 0, 0, 170))
        dt.text((x, y), linea, font=f, fill=relleno + (255,), stroke_width=BORDE, stroke_fill=(0, 0, 0, 255))
    img.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(7)))
    img.alpha_composite(texto_capa)
    if cfg.rotulo:
        fr = _fuente(FUENTE_ROTULO, rot_tam)
        yr = y0 + caja_ref[1] + bloque + 22
        ImageDraw.Draw(img).text((x0, yr), cfg.rotulo, font=fr, fill=(255, 255, 255, 204))
    return img.convert("RGB")


def guardar_jpg(img: Image.Image, destino: Path) -> Path:
    """JPG final de menos de 2 MB."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    for calidad in (92, 88, 84, 80, 75, 70):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=calidad, optimize=True, progressive=True)
        if buf.tell() < MAX_JPG:
            break
    destino.write_bytes(buf.getvalue())
    return destino


def cargar_retrato(cfg: ConfigTexto) -> Image.Image | None:
    if not cfg.retrato:
        return None
    ruta = carpeta_canal(cfg.canal) / cfg.retrato
    return Image.open(ruta).convert("RGBA") if ruta.exists() else None


# ------------------------------------------------------------------ planificador (Claude)

FORMULAS = [
    (1, "ENFÓCATE EN X / NO EN Y", "contraste: en qué enfocarse y en qué no"),
    (2, "VUÉLVETE X / EN {duracion}", "transformación en el tiempo real del video"),
    (3, "DE LA X / A LA Y", "el cambio de un estado malo a uno bueno"),
    (4, "OBLÍGATE A X", "una orden directa de acción"),
]


def instruccion(titulo: str, duracion: str) -> str:
    formulas = "\n".join(f'  {n}. "{f.format(duracion=duracion)}" ({d})' for n, f, d in FORMULAS)
    return f"""Eres el editor de miniaturas de un canal de YouTube de mentalidad y disciplina en español.
Título del video: «{titulo}». Duración real del video: {duracion}.

Escribe el texto grande de la miniatura: UNA opción por cada fórmula, en este orden:
{formulas}

Reglas (todas):
- Orden directa en imperativo, como en las fórmulas.
- De {MIN_PALABRAS} a {MAX_PALABRAS} palabras en total; de {MIN_LINEAS} a {MAX_LINEAS} líneas; máximo {MAX_PALABRAS_LINEA} palabras y {MAX_CARACTERES_LINEA} letras por línea. TODO EN MAYÚSCULAS.
- Las líneas se separan con " / ". El color va por LÍNEA completa: 1 o 2 líneas (las de mayor carga) van
  entre asteriscos, p. ej. "ENFÓCATE EN / *EMPEZAR* / NO EN TENER GANAS". Nunca todas.
- No repitas las palabras principales del título: el texto es una segunda idea que lo complementa.
- Prefiere el contraste «esto, no aquello» cuando encaje.
- No inventes citas ni atribuyas frases a personas reales.
- Antes de responder, revisa tildes y ortografía de cada palabra (ENFÓCATE, VUÉLVETE, OBLÍGATE, MÁS, DÍAS…).

Responde SOLO un JSON: {{"opciones": [{{"formula": 1, "texto": "..."}}, {{"formula": 2, "texto": "..."}},
{{"formula": 3, "texto": "..."}}, {{"formula": 4, "texto": "..."}}]}}"""


def planificar(titulo: str, duracion: str, ejecutar=None, cwd=None, avisar=print) -> list[dict]:
    """Una opción por fórmula, en orden. Se corrigen las tildes que se escapan y, si alguna no cumple
    las reglas, se le pide a Claude una vez más con los problemas. Devuelve [{formula, texto, avisos}]."""
    from .. import claude_cli

    ejecutar = ejecutar or claude_cli.ejecutar
    pedido = instruccion(titulo, duracion)
    opciones: dict[int, dict] = {}
    for intento in range(2):
        extra = ""
        if intento:
            malas = {n: o for n, o in opciones.items() if o["avisos"]}
            if not malas:
                break
            extra = "\n\nEstas opciones no cumplen las reglas; corrígelas (y devuelve las 4):\n" + "\n".join(
                f'- fórmula {n}: "{o["texto"]}" → {"; ".join(o["avisos"])}' for n, o in malas.items())
        texto, _ = ejecutar(pedido + extra, cwd=cwd)
        for o in (claude_cli.extraer_json(texto) or {}).get("opciones") or []:
            try:
                n = int(o.get("formula"))
                crudo = str(o.get("texto") or "").strip()
            except (TypeError, ValueError, AttributeError):
                continue
            if n not in {f[0] for f in FORMULAS} or not crudo:
                continue
            arreglado, _ = corregir_tildes(crudo)
            try:
                arreglado = formatear(parsear(arreglado))
            except ValueError:
                pass
            avisos = revisar(arreglado, titulo)
            if n not in opciones or len(avisos) < len(opciones[n]["avisos"]):
                opciones[n] = {"formula": n, "texto": arreglado, "avisos": avisos}
    if not opciones:
        raise claude_cli.ErrorClaude("Claude no devolvió opciones de texto para la miniatura")
    return [opciones[n] for n in sorted(opciones)]


def duracion_texto(segundos: float) -> str:
    minutos = max(1, round(segundos / 60))
    return f"{minutos} MINUTO" if minutos == 1 else f"{minutos} MINUTOS"


def a_json(x) -> str:  # para depurar
    return json.dumps(x, ensure_ascii=False, indent=1)
