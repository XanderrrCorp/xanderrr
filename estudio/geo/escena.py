"""La escena de MAPA completa (18-10): mapa por código + animación + marcador (HUD) + El Calvo reaccionando.

Una escena de mapa (dentro de escenas.json, tipo «mapa») lleva:
  {"tipo": "mapa", "mapa": {"accion": "highlight|arrow|zoom_region|compare", "pais": "MEX", "origen": "COL",
   "sentimiento": "very_friendly|normal|complicated|tension", "region": "SUDAMÉRICA", "etiqueta": "MÉXICO",
   "estado": "MEJORANDO|ESTABLE|EMPEORANDO|HISTÓRICO", "linea": [{"anio": "2008", "texto": "..."}],
   "calvo": "happy|worried|scared|angry|thinking|shocked", "calvo_lado": "left|right|none"}}
Los nombres en inglés que manda el director visual (focus_country, map_action…) se aceptan igual (validar).

El marcador acumula lo que pasó en las escenas de mapa ANTERIORES del mismo video: `preparar` lo calcula una vez
para todo el video (se llama solo la primera vez que se dibuja un mapa). Los países ya clasificados quedan pintados
suave del color de su categoría; el país base del video (Colombia por defecto) siempre con su bandera y borde blanco.
"""
from __future__ import annotations

import math
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import mapa as M

W, H = M.W, M.H
ACCIONES = ("highlight", "arrow", "zoom_region", "compare")
ESTADOS = ("MEJORANDO", "ESTABLE", "EMPEORANDO", "HISTÓRICO")
POSES = {"happy": ("senalando_contento", "contento"), "worried": ("hombros", "duda"),
         "scared": ("asustado", "susto"), "angry": ("brazos_cruzados", "disgusto"),
         "thinking": ("pensando", "pensativo"), "shocked": ("manos_cabeza", "sorpresa")}
POSE_POR_SENTIMIENTO = {"very_friendly": "happy", "normal": "happy", "complicated": "worried", "tension": "scared"}
HUD_FONDO = (30, 34, 48, 230)
ZOOM_S = 1.2
FLECHA_S = 0.8
CLASIFICA_S = 0.5            # el país se «clasifica» (contadores, barra) medio segundo después de empezar la escena
PAIS_BASE = "COL"
MAX_LINEA = 50


# ------------------------------------------------------------------ validación (lo que manda el director visual)

def validar(crudo: dict, pais_base: str = PAIS_BASE) -> tuple[dict | None, str]:
    """Normaliza una escena de mapa. Devuelve (mapa, nota); mapa None si un país no existe (cae a ilustración)."""
    g = lambda *ks: next((crudo.get(k) for k in ks if crudo.get(k) not in (None, "")), None)  # noqa: E731
    accion = str(g("accion", "map_action") or "highlight").lower()
    accion = accion if accion in ACCIONES else "highlight"
    crudo_pais = g("pais", "focus_country")
    pais = M.codigo(crudo_pais)
    if not pais:
        return None, f"mapa: el país «{crudo_pais}» no existe en el mapa; la escena va como ilustración"
    origen_crudo = g("origen", "origin_country")
    origen = M.codigo(origen_crudo) if origen_crudo else None
    if accion in ("arrow", "compare"):
        if origen_crudo and not origen:
            return None, f"mapa: el país «{origen_crudo}» no existe en el mapa; la escena va como ilustración"
        origen = origen or M.codigo(pais_base)
        if origen == pais:
            accion = "highlight"
    sent = str(g("sentimiento", "sentiment") or "normal").lower()
    sent = sent if sent in M.SENTIMIENTOS else "normal"
    estado = str(g("estado", "status_tag") or "").upper()
    linea = []
    for x in (g("linea", "timeline") or [])[:2]:
        if isinstance(x, dict):
            anio = str(x.get("anio") or x.get("year") or "").strip()[:9]
            texto = str(x.get("texto") or x.get("text") or "").strip()
            if texto:
                linea.append({"anio": anio, "texto": texto[:MAX_LINEA]})
    calvo = str(g("calvo", "calvo_pose") or POSE_POR_SENTIMIENTO[sent]).lower()
    lado = str(g("calvo_lado", "calvo_position") or "left").lower()
    reg = M.region(g("region") or "") or _region_de(pais)
    return {"accion": accion, "pais": pais, "origen": origen, "sentimiento": sent, "region": reg,
            "etiqueta": str(g("etiqueta", "label_text") or M.nombre(pais)).upper()[:26],
            "estado": estado if estado in ESTADOS else "", "linea": linea,
            "calvo": calvo if calvo in POSES else POSE_POR_SENTIMIENTO[sent],
            "calvo_lado": lado if lado in ("left", "right", "none") else "left"}, ""


def _region_de(clave: str) -> str:
    p = M.paises()[clave]
    sub, cont = p["subregion"], p["continente"]
    if clave == "MEX":                                     # Natural Earth lo pone en Centroamérica; se dice Norteamérica
        return "NORTEAMÉRICA"
    if sub == "South America":
        return "SUDAMÉRICA"
    if sub in ("Central America", "Caribbean"):
        return "CENTROAMÉRICA Y CARIBE"
    if sub == "Northern America":
        return "NORTEAMÉRICA"
    if sub == "Western Asia":
        return "MEDIO ORIENTE"
    return {"Europe": "EUROPA", "Asia": "ASIA", "Africa": "ÁFRICA", "Oceania": "OCEANÍA"}.get(cont, "MUNDO")


# ------------------------------------------------------------------ el marcador a lo largo del video

def preparar(datos: dict) -> None:
    """Calcula, en orden, el marcador de cada escena de mapa (antes y después de clasificar su país)."""
    pais_base = M.codigo(datos.get("video", {}).get("pais_base") or PAIS_BASE) or PAIS_BASE
    clasificados: dict[str, str] = {}
    historial = None
    region = None
    for esc in datos["escenas"]:
        if esc.get("tipo") != "mapa":
            continue
        m = esc["mapa"]
        antes = _conteo(clasificados)
        nuevo = m["pais"] != pais_base and m["pais"] not in clasificados
        previos = dict(clasificados)
        if nuevo:
            clasificados[m["pais"]] = m["sentimiento"]
        region = m.get("region") or region
        m["_estado"] = {"antes": antes, "despues": _conteo(clasificados), "nuevo": nuevo, "previos": previos,
                        "historial": historial, "region": region or "MUNDO", "pais_base": pais_base}
        if nuevo:
            historial = [m["pais"], m["sentimiento"]]
    datos.setdefault("video", {})["_mapas_listos"] = True


def _conteo(clasificados: dict[str, str]) -> dict[str, int]:
    return {k: sum(1 for v in clasificados.values() if v == k) for k in M.SENTIMIENTOS}


# ------------------------------------------------------------------ cámara

def _suave(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


def vistas(m: dict) -> tuple[M.Vista, M.Vista]:
    """(vista inicial, vista final) de la escena."""
    a = m["accion"]
    if a == "zoom_region":
        fin = M.vista_region(m["region"]) if m.get("region") and m["region"] != "MUNDO" else M.vista_paises(m["pais"])
        return M.vista_region("MUNDO"), fin
    if a in ("arrow", "compare") and m.get("origen"):
        v = M.vista_paises(m["origen"], m["pais"])
    else:
        v = M.vista_paises(m["pais"])
    return v, v


def camara(m: dict, loc: float, dur: float) -> M.Vista:
    v0, v1 = vistas(m)
    if m["accion"] == "zoom_region" and loc < ZOOM_S:
        return v0.hacia(v1, _suave(loc / ZOOM_S))
    # Ken Burns muy suave: se acerca un 4 % durante la escena
    p = _suave((loc - (ZOOM_S if m["accion"] == "zoom_region" else 0)) / max(0.5, dur))
    return M.Vista(v1.cx, v1.cy, v1.ancho * (1 - 0.04 * p))


def _afin(desde: M.Vista, hacia: M.Vista) -> np.ndarray:
    """Matriz que lleva píxeles de la vista `hacia` (pantalla) a la imagen dibujada en `desde`."""
    k = desde.escala / hacia.escala
    return np.array([[k, 0, (hacia.cx - desde.cx) * desde.escala + W / 2 - k * W / 2],
                     [0, k, (hacia.cy - desde.cy) * desde.escala + H / 2 - k * H / 2]], np.float32)


def _px(desde: M.Vista, hacia: M.Vista, x: float, y: float) -> tuple[float, float]:
    """Un punto dibujado en `desde` → dónde cae en la pantalla con la cámara en `hacia`."""
    k = hacia.escala / desde.escala
    return ((x - W / 2) * k + (desde.cx - hacia.cx) * hacia.escala + W / 2,
            (y - H / 2) * k + (desde.cy - hacia.cy) * hacia.escala + H / 2)


# ------------------------------------------------------------------ capas del mapa (se dibujan una vez por escena)

def _aclarar(rgb, k: float = 0.45) -> tuple:
    return tuple(int(c + (t - c) * k) for c, t in zip(rgb, M.TIERRA))


_CACHE: dict = {}


def _capas(esc: dict) -> dict:
    """Imágenes de la escena (en caché): mapa inicial y final con los colores del marcador, el país en foco
    (relleno y brillo, recortados) y el país base con su bandera."""
    clave = (esc.get("id"), str(sorted(esc["mapa"].items(), key=lambda x: x[0])))
    if clave in _CACHE:
        return _CACHE[clave]
    m = esc["mapa"]
    st = m["_estado"]
    v0, v1 = vistas(m)
    colores = {c: _aclarar(M.SENTIMIENTOS[s]) for c, s in st["previos"].items()}
    if m["accion"] == "compare" and m.get("origen") and m["origen"] != st["pais_base"]:
        colores[m["origen"]] = M.SENTIMIENTOS[m["sentimiento"]]
    fin = M.base(v1, colores).copy()
    _pais_base(fin, st["pais_base"], v1)
    capas = {"v0": v0, "v1": v1, "fin": np.ascontiguousarray(fin[..., ::-1])}     # BGR, como el render
    if v0 != v1:
        ini = M.base(v0, colores).copy()
        _pais_base(ini, st["pais_base"], v0)
        capas["ini"] = np.ascontiguousarray(ini[..., ::-1])
    if m["pais"] != st["pais_base"]:
        capas["foco"] = _foco(m["pais"], v1, M.SENTIMIENTOS[m["sentimiento"]])
    if len(_CACHE) > 12:
        _CACHE.clear()
    _CACHE[clave] = capas
    return capas


def _pais_base(img: np.ndarray, clave: str, v: M.Vista) -> None:
    """El país base del video: su bandera recortada a su forma y un borde blanco que brilla."""
    if not M._visible(clave, v):
        return
    mask = M.mascara(clave, v)
    ys, xs = np.nonzero(mask > 8)
    if not len(xs):
        return
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    b = M.bandera(clave, 300)
    if b is not None:
        franjas = np.asarray(b.convert("RGB").resize((x1 - x0, y1 - y0), Image.Resampling.BILINEAR), np.float32)
        a = mask[y0:y1, x0:x1, None].astype(np.float32) / 255
        img[y0:y1, x0:x1] = (img[y0:y1, x0:x1] * (1 - a) + franjas * a).astype(np.uint8)
    borde = cv2.dilate(mask, np.ones((7, 7), np.uint8)) - cv2.erode(mask, np.ones((3, 3), np.uint8))
    brillo = cv2.GaussianBlur(borde, (0, 0), 3).astype(np.float32) / 255
    a = np.clip(borde.astype(np.float32) / 255 + brillo * 0.8, 0, 1)[..., None]
    img[:] = (img * (1 - a) + 255 * a).astype(np.uint8)


def _foco(clave: str, v: M.Vista, color) -> dict:
    """El país en foco: relleno de su color y un brillo alrededor, recortados con margen (RGBA) y su centro."""
    mask = M.mascara(clave, v)
    ys, xs = np.nonzero(mask > 8)
    if not len(xs):
        return {}
    m = 40
    x0, x1 = max(0, xs.min() - m), min(W, xs.max() + m)
    y0, y1 = max(0, ys.min() - m), min(H, ys.max() + m)
    sub = mask[y0:y1, x0:x1]
    color = tuple(color)[::-1]                                  # BGR
    relleno = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    relleno[..., :3] = color
    relleno[..., 3] = sub
    contorno = cv2.dilate(sub, np.ones((3, 3), np.uint8)) - sub
    relleno[contorno > 0, :3] = M.BORDE[::-1]
    relleno[..., 3] = np.maximum(sub, contorno)
    brillo = np.zeros_like(relleno)
    brillo[..., :3] = color
    brillo[..., 3] = np.clip(cv2.GaussianBlur(cv2.dilate(sub, np.ones((15, 15), np.uint8)), (0, 0), 14) * 1.6,
                             0, 255).astype(np.uint8)
    cx, cy = M.etiqueta_px(clave, v)
    return {"relleno": relleno, "brillo": brillo, "x0": x0, "y0": y0, "centro": (cx, cy)}


def _mezclar(cuadro: np.ndarray, capa: np.ndarray, x: int, y: int, alfa: float = 1.0) -> None:
    """Mezcla una capa BGRA (ya del tamaño final) en el cuadro BGR, solo en su rectángulo (rápido)."""
    if alfa <= 0.01:
        return
    h, w = capa.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sub = capa[y0 - y:y1 - y, x0 - x:x1 - x]
    a = sub[..., 3:4].astype(np.uint16)
    if alfa < 0.999:
        a = (a * int(alfa * 256)) >> 8
    dst = cuadro[y0:y1, x0:x1]
    dst[:] = ((sub[..., :3].astype(np.uint16) * a + dst.astype(np.uint16) * (255 - a) + 127) // 255).astype(np.uint8)


def _pegar_rgba(cuadro: np.ndarray, capa: np.ndarray, m: np.ndarray, alfa: float = 1.0) -> None:
    """Pega `capa` (BGRA) en el cuadro con la afín `m` (de capa a pantalla), dibujando solo donde cae."""
    if alfa <= 0.01:
        return
    h, w = capa.shape[:2]
    esq = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ m.T
    x0, y0 = int(max(0, np.floor(esq[:, 0].min()) - 1)), int(max(0, np.floor(esq[:, 1].min()) - 1))
    x1, y1 = int(min(W, np.ceil(esq[:, 0].max()) + 1)), int(min(H, np.ceil(esq[:, 1].max()) + 1))
    if x0 >= x1 or y0 >= y1:
        return
    mm = m.copy()
    mm[0, 2] -= x0
    mm[1, 2] -= y0
    trozo = cv2.warpAffine(capa, mm, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                           borderValue=(0, 0, 0, 0))
    _mezclar(cuadro, trozo, x0, y0, alfa)


# ------------------------------------------------------------------ el cuadro

def cuadro(datos: dict, esc: dict, t: float) -> np.ndarray:
    if not datos.get("video", {}).get("_mapas_listos") or "_estado" not in esc["mapa"]:
        preparar(datos)
    m = esc["mapa"]
    loc, dur = t - esc["inicio"], max(0.5, esc["fin"] - esc["inicio"])
    capas = _capas(esc)
    cam = camara(m, loc, dur)
    v1 = capas["v1"]
    a1 = _afin(v1, cam)
    inv = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP          # las matrices van de la pantalla a la imagen dibujada
    img = cv2.warpAffine(capas["fin"], a1, (W, H), flags=inv, borderMode=cv2.BORDER_REPLICATE)
    if "ini" in capas and loc < ZOOM_S:
        # zoom de la vista mundial a la región: el mapa lejano se funde con el cercano (que tiene más detalle)
        a0 = _afin(capas["v0"], cam)
        lejos = cv2.warpAffine(capas["ini"], a0, (W, H), flags=inv, borderMode=cv2.BORDER_REPLICATE)
        cubre = cv2.warpAffine(np.full((H, W), 255, np.uint8), a1, (W, H), flags=inv,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        w = (_suave((loc / ZOOM_S - 0.25) / 0.6) * cubre.astype(np.float32) / 255)[..., None]
        img = (lejos * (1 - w) + img * w).astype(np.uint8)
    listo = ZOOM_S if m["accion"] == "zoom_region" else 0.0     # lo del país pasa cuando la cámara llega
    foco = capas.get("foco")
    if foco:
        p = loc - listo
        pulso = 1 + 0.04 * math.sin(math.pi * min(1.0, max(0.0, p / 0.7)))
        brillo = (0.55 + 0.25 * math.sin(loc * 3.2)) * min(1.0, max(0.0, p / 0.3))
        cx, cy = foco["centro"]
        sx, sy = _px(v1, cam, cx, cy)
        k = cam.escala / v1.escala
        for capa, alfa, esc_k in ((foco["brillo"], brillo, 1.0), (foco["relleno"], min(1.0, max(0.0, p / 0.25)), pulso)):
            kk = k * esc_k
            mat = np.array([[kk, 0, sx - kk * (cx - foco["x0"])], [0, kk, sy - kk * (cy - foco["y0"])]], np.float32)
            _pegar_rgba(img, capa, mat, alfa)
    if m["accion"] == "arrow" and m.get("origen"):
        _flecha(img, m, v1, cam, (loc - listo) / FLECHA_S)
    _tarjetas_mapa(img, m, v1, cam, loc - listo)
    _calvo(img, m, loc)
    return _hud(img, m, loc, dur)


def _flecha(img: np.ndarray, m: dict, v1: M.Vista, cam: M.Vista, p: float) -> None:
    """Flecha curva que se dibuja del país de origen al país en foco, del color del sentimiento."""
    if p <= 0:
        return
    a = _px(v1, cam, *M.etiqueta_px(m["origen"], v1))
    b = _px(v1, cam, *M.etiqueta_px(m["pais"], v1))
    dx, dy = b[0] - a[0], b[1] - a[1]
    nx, ny = -dy, dx                                           # perpendicular; la curva siempre hacia arriba
    if ny > 0:
        nx, ny = -nx, -ny
    c = ((a[0] + b[0]) / 2 + nx * 0.3, (a[1] + b[1]) / 2 + ny * 0.3)
    n = 60
    hasta = max(2, int(n * min(1.0, _suave(p))))
    pts = [((1 - s) ** 2 * a[0] + 2 * (1 - s) * s * c[0] + s ** 2 * b[0],
            (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * c[1] + s ** 2 * b[1]) for s in (i / n for i in range(hasta + 1))]
    arr = np.array(pts, np.int32).reshape(-1, 1, 2)
    color = M.SENTIMIENTOS[m["sentimiento"]][::-1]
    cv2.polylines(img, [arr], False, (255, 255, 255), 20, cv2.LINE_AA)
    cv2.polylines(img, [arr], False, color, 11, cv2.LINE_AA)
    cv2.circle(img, (int(a[0]), int(a[1])), 13, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(img, (int(a[0]), int(a[1])), 8, color, -1, cv2.LINE_AA)
    if len(pts) >= 2:
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        ang = math.atan2(y2 - y1, x2 - x1)
        punta = [(x2 + 10 * math.cos(ang), y2 + 10 * math.sin(ang)),
                 (x2 - 34 * math.cos(ang - 0.5), y2 - 34 * math.sin(ang - 0.5)),
                 (x2 - 34 * math.cos(ang + 0.5), y2 - 34 * math.sin(ang + 0.5))]
        tri = np.array(punta, np.int32)
        cv2.fillPoly(img, [tri], (255, 255, 255), cv2.LINE_AA)
        cv2.fillPoly(img, [np.array([(x + (x2 - x) * 0.25, y + (y2 - y) * 0.25) for x, y in punta], np.int32)],
                     color, cv2.LINE_AA)


# ------------------------------------------------------------------ textos y tarjetas (Pillow, fuente del canal)

@lru_cache(maxsize=16)
def fuente(tam: int):
    from ..calma.piezas import FUENTE

    return ImageFont.truetype(str(FUENTE), tam)


def _bgra(capa: Image.Image) -> np.ndarray:
    a = np.asarray(capa.convert("RGBA"))
    return np.ascontiguousarray(a[..., [2, 1, 0, 3]])


def _pegar_pil(img: np.ndarray, capa: Image.Image, x: float, y: float, alfa: float = 1.0) -> None:
    """Pega una imagen RGBA de Pillow en el cuadro BGR (x, y = esquina de arriba a la izquierda)."""
    _mezclar(img, _bgra(capa), int(round(x)), int(round(y)), alfa)


@lru_cache(maxsize=64)
def _tarjeta_bandera(clave: str, borde: tuple) -> Image.Image:
    """La tarjeta que sale junto al país: bandera real y su nombre en español."""
    b = M.bandera(clave, 120)
    nombre = M.nombre(clave).upper()
    f = fuente(34)
    tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(nombre, font=f))
    w = max(b.width if b else 0, tw) + 40
    h = (b.height if b else 0) + 80
    im = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 10, w + 10, h + 14), radius=22, fill=(0, 0, 0, 70))
    d.rounded_rectangle((2, 2, w + 2, h + 2), radius=22, fill=(255, 255, 255, 255), outline=borde + (255,), width=5)
    if b:
        im.alpha_composite(b, ((w - b.width) // 2 + 2, 20))
    d.text((w // 2 + 2, h - 26), nombre, font=f, fill=(25, 25, 25), anchor="mm")
    return im


@lru_cache(maxsize=32)
def _tarjeta_vs(a: str, b: str, borde: tuple) -> Image.Image:
    fa, fb = M.bandera(a, 150), M.bandera(b, 150)
    f = fuente(30)
    im = Image.new("RGBA", (680, 270), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 12, 676, 266), radius=28, fill=(0, 0, 0, 70))
    d.rounded_rectangle((2, 2, 670, 258), radius=28, fill=HUD_FONDO, outline=borde + (255,), width=5)
    for x, fl, clave in ((40, fa, a), (430, fb, b)):
        if fl:
            im.alpha_composite(fl, (x, 30))
        d.text((x + 100, 222), M.nombre(clave).upper()[:16], font=f, fill=(255, 255, 255), anchor="mm")
    d.ellipse((290, 60, 380, 150), fill=borde + (255,))
    d.text((335, 106), "VS", font=fuente(40), fill=(255, 255, 255), anchor="mm")
    return im


def _entrada(p: float) -> float:
    """0 → 1 con un rebote corto (pop)."""
    if p <= 0:
        return 0.0
    q = min(1.0, p)
    return (1 - (1 - q) ** 3) * (1 + 0.12 * math.exp(-p * 7) * math.cos(p * 12))


def _tarjetas_mapa(img: np.ndarray, m: dict, v1: M.Vista, cam: M.Vista, p: float) -> None:
    color = M.SENTIMIENTOS[m["sentimiento"]]
    if m["accion"] == "compare" and m.get("origen"):
        t = _tarjeta_vs(m["origen"], m["pais"], color)
        k = _entrada(p / 0.35)
        if k > 0:                                  # del lado contrario al Calvo, para no tapar los países
            ti = t.resize((max(1, int(t.width * k)), max(1, int(t.height * k))))
            cx = 420 if m.get("calvo_lado") == "right" else W - 420
            _pegar_pil(img, ti, cx - ti.width / 2, 330 + (t.height - ti.height) / 2)
        return
    if m["accion"] not in ("highlight", "zoom_region") or p < 0.35:
        return
    t = _tarjeta_bandera(m["pais"], color)
    x, y = _px(v1, cam, *M.etiqueta_px(m["pais"], v1))
    k = _entrada((p - 0.35) / 0.35)
    ti = t.resize((max(1, int(t.width * k)), max(1, int(t.height * k))))
    dx = 110 if x + 110 + t.width < W - 40 else -110 - t.width
    _pegar_pil(img, ti, min(W - ti.width - 20, max(20, x + dx)), min(560, max(150, y - t.height / 2)))


# ------------------------------------------------------------------ El Calvo reaccionando

def _calvo(img: np.ndarray, m: dict, loc: float) -> None:
    if m.get("calvo_lado") == "none":
        return
    from ..calma.raster import sprite
    from ..calma.render import _pegar

    pose, gesto = POSES[m["calvo"]]
    s, ancla = sprite("personaje", {"pose": pose, "gesto": gesto}, 0.9, sombra=True)
    x = 230 if m["calvo_lado"] == "left" else W - 230
    y = 830
    respira = 1 + 0.01 * (1 + math.sin(loc * 2 * math.pi / 2.2))
    entra = _entrada(loc / 0.4)
    sombra = img.copy()
    cv2.ellipse(sombra, (x, y + 4), (100, 17), 0, 0, 360, (40, 40, 40), -1, cv2.LINE_AA)
    cv2.addWeighted(sombra, 0.35 * min(1.0, entra), img, 1 - 0.35 * min(1.0, entra), 0, dst=img)
    _pegar(img, s, ancla, x, y + (1 - min(1.0, entra)) * 120, respira * max(0.05, min(1.0, entra)), 0)


# ------------------------------------------------------------------ el marcador (HUD)

_HUD: dict = {}


def _pildora(d: ImageDraw.ImageDraw, x: int, y: int, texto: str, color, tam: int = 26, alto: int = 46) -> int:
    f = fuente(tam)
    w = int(d.textlength(texto, font=f)) + 36
    d.rounded_rectangle((x, y, x + w, y + alto), radius=alto // 2, fill=tuple(color) + (255,))
    d.text((x + w / 2, y + alto / 2 + 1), texto, font=f, fill=(255, 255, 255), anchor="mm")
    return w


def _panel(d: ImageDraw.ImageDraw, caja, borde) -> None:
    d.rounded_rectangle(caja, radius=22, fill=HUD_FONDO, outline=tuple(borde) + (255,), width=4)


def _hud(img: np.ndarray, m: dict, loc: float, dur: float) -> np.ndarray:
    st = m["_estado"]
    color = M.SENTIMIENTOS[m["sentimiento"]]
    clas = loc - CLASIFICA_S - (ZOOM_S if m["accion"] == "zoom_region" else 0)
    p_barra = _suave(clas / 0.6) if st["nuevo"] else 1.0
    pop = 1 + 0.25 * math.sin(math.pi * min(1.0, max(0.0, clas / 0.35))) if st["nuevo"] and clas > 0 else 1.0
    tarjeta = _suave((loc - 0.1) / 0.4)
    clave = (id(m), round(p_barra, 2), round(pop, 2), round(tarjeta, 2), clas > 0)
    franjas = _HUD.get(clave)
    if franjas is None:                       # solo las franjas de arriba y de abajo tienen marcador
        capa = _bgra(_dibujar_hud(m, st, color, p_barra, pop, tarjeta, clas > 0))
        franjas = [(capa[:150].copy(), 0), (capa[840:].copy(), 840)]
        if len(_HUD) > 200:
            _HUD.clear()
        _HUD[clave] = franjas
    for trozo, y in franjas:
        _mezclar(img, trozo, 0, y)
    return img


def _dibujar_hud(m, st, color, p_barra, pop, tarjeta, clasificado) -> Image.Image:
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    antes, despues = st["antes"], st["despues"] if clasificado else st["antes"]
    # etiquetas de contexto (arriba a la izquierda)
    _pildora(d, 30, 28, M.nombre(st["pais_base"]).upper(), (232, 180, 0))
    _pildora(d, 30, 84, st["region"], (52, 120, 200))
    # barra de balance (arriba al centro)
    amigos = lambda c: c["very_friendly"] + c["normal"]  # noqa: E731
    problemas = lambda c: c["complicated"] + c["tension"]  # noqa: E731
    a0, a1 = amigos(antes), amigos(despues)
    b0, b1 = problemas(antes), problemas(despues)
    fa = (a0 + (a1 - a0) * p_barra)
    fb = (b0 + (b1 - b0) * p_barra)
    total = max(1e-6, fa + fb)
    bx0, bx1, by = 560, 1360, 30
    _panel(d, (bx0 - 20, by - 10, bx1 + 20, by + 86), color)
    f = fuente(24)
    d.text((bx0, by), f"AMIGOS {a1 if clasificado else a0}", font=f, fill=(255, 255, 255))
    t = f"CON PROBLEMAS {b1 if clasificado else b0}"
    d.text((bx1 - d.textlength(t, font=f), by), t, font=f, fill=(255, 255, 255))
    corte = bx0 + (bx1 - bx0) * (fa / total if fa + fb > 0 else 0.5)
    d.rounded_rectangle((bx0, by + 38, bx1, by + 66), radius=14, fill=(224, 69, 58, 255))
    if corte > bx0 + 14:
        d.rounded_rectangle((bx0, by + 38, int(corte), by + 66), radius=14, fill=(61, 190, 107, 255))
        d.rounded_rectangle((bx0, by + 38, int(bx0 + (corte - bx0) * 0.5), by + 66), radius=14,
                            fill=(255, 111, 163, 255))
    # marcador por categorías (abajo a la izquierda)
    px0, py0 = 30, 860
    _panel(d, (px0, py0, px0 + 380, py0 + 196), color)
    for i, s in enumerate(M.SENTIMIENTOS):
        y = py0 + 22 + i * 43
        d.ellipse((px0 + 22, y + 4, px0 + 46, y + 28), fill=M.SENTIMIENTOS[s] + (255,))
        d.text((px0 + 60, y + 2), M.NOMBRE_SENTIMIENTO[s], font=fuente(24), fill=(255, 255, 255))
        n = despues[s]
        k = pop if (s == m["sentimiento"] and st["nuevo"] and clasificado) else 1.0
        d.text((px0 + 348, y + 16), str(n), font=fuente(int(30 * k)), fill=(255, 255, 255), anchor="mm")
    # tarjeta del país (abajo al centro), entra deslizando
    _tarjeta_pais(im, m, color, tarjeta)
    # historial (abajo a la derecha)
    if st["historial"]:
        hp, hs = st["historial"]
        hx0, hy0 = W - 410, 940
        _panel(d, (hx0, hy0, hx0 + 380, hy0 + 116), M.SENTIMIENTOS[hs])
        d.text((hx0 + 20, hy0 + 14), "ANTERIOR", font=fuente(20), fill=(170, 175, 190))
        b = M.bandera(hp, 46)
        x = hx0 + 20
        if b:
            im.alpha_composite(b, (x, hy0 + 50))
            x += b.width + 14
        d.text((x, hy0 + 48), M.nombre(hp).upper()[:14], font=fuente(24), fill=(255, 255, 255))
        d.text((x, hy0 + 80), M.NOMBRE_SENTIMIENTO[hs], font=fuente(18), fill=M.SENTIMIENTOS[hs] + (255,))
    return im


def _tarjeta_pais(im: Image.Image, m: dict, color, p: float) -> None:
    if p <= 0:
        return
    w, h = 820, 200
    x0 = (W - w) // 2
    y0 = int(H - 20 - h + (1 - p) * (h + 40))
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    _panel(d, (0, 0, w - 1, h - 1), color)
    b = M.bandera(m["pais"], 120)
    x = 24
    if b:
        capa.alpha_composite(b, (x, (h - b.height) // 2))
        x += b.width + 26
    f_nombre = fuente(44)
    nombre = m.get("etiqueta") or M.nombre(m["pais"]).upper()
    while d.textlength(nombre, font=f_nombre) > w - x - 30 and f_nombre.size > 26:
        f_nombre = fuente(f_nombre.size - 2)
    d.text((x, 20), nombre, font=f_nombre, fill=(255, 255, 255))
    y = 20 + f_nombre.size + 12
    if m.get("estado"):
        _pildora(d, x, y, m["estado"], color, 20, 34)
        y += 44
    for linea in m.get("linea", [])[:2]:
        fx = x
        if linea.get("anio"):
            d.text((fx, y), linea["anio"], font=fuente(22), fill=color + (255,))
            fx += d.textlength(linea["anio"], font=fuente(22)) + 12
        texto = linea["texto"]
        f = fuente(20)
        while d.textlength(texto, font=f) > w - fx - 24 and len(texto) > 8:
            texto = texto[:-2].rstrip() + "…"
        d.text((fx, y + 2), texto, font=f, fill=(225, 228, 235))
        y += 30
    if y0 < H:
        im.alpha_composite(capa.crop((0, 0, w, min(h, H - y0))), (x0, y0))
