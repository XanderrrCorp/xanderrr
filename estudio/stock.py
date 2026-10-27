"""Fotos y videos REALES de los animales, de Pexels (gratis, Licencia de Pexels) y, desde el 20-10, también fotos
de Wikimedia Commons (wikimedia.py: licencias libres, con crédito) en la misma hoja de contacto.

1. Claude da, por cada nivel, cómo buscar al animal en inglés (nombre común y científico).
2. Se buscan fotos y videos en Pexels y se arma una hoja de contacto numerada por nivel.
3. Claude mira la hoja (herramienta Read) y aprueba SOLO los que muestran con claridad esa
   especie. Lo no verificado nunca se usa: el video no afirma una especie sobre algo dudoso.
4. Se bajan los aprobados a assets/stock/ con su registro: enlace de origen en Pexels,
   autor, licencia y por qué se aprobó (assets/stock/stock.json).

El Director de edición los usa de vez en cuando (no siempre) cuando la voz nombra al animal.

5. Si Pexels no tiene ni una foto ni un video verificado de un animal, Gemini crea UNA
   recreación ultra realista (unos 0,05 USD, dentro del freno). Claude la revisa igual que
   las fotos; en el video lleva la etiqueta «Recreación IA», nunca se presenta como foto real.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import requests

from . import claude_cli, wikimedia
from .config import clave_api, escribir_json, leer_json

API_FOTOS = "https://api.pexels.com/v1/search"
API_VIDEOS = "https://api.pexels.com/videos/search"
LICENCIA = "Licencia de Pexels: uso gratis, también comercial; sin atribución obligatoria (pexels.com/license)"
FOTOS_POR_NIVEL, VIDEOS_POR_NIVEL = 10, 6
APROBADAS_POR_NIVEL = {"foto": 2, "video": 1}
LICENCIA_IA = "Recreación generada con IA (Gemini Flash Image): no es una foto real"
PROMPT_REALISTA = ("Ultra-realistic wildlife photograph of a {especie} ({busqueda}), anatomically accurate, true natural "
                   "colors and textures, in its natural habitat, whole animal visible and centered, sharp focus on the "
                   "animal, shallow depth of field, soft natural light, shot on a professional camera with a macro "
                   "lens. No text, no watermark, no people, no logos. Aspect ratio 16:9.")


class SinClavePexels(RuntimeError):
    pass


def ajustes_pexels(proyecto) -> dict:
    """(27-10, el dueño: «quiero que salgan más videos de Pexels») la fórmula del video puede pedir Pexels antes que
    Google, videos de lugares, más videos por animal y más apariciones en el montaje. Sin fórmula guardada (videos de
    antes) o sin la clave «pexels»: {} y todo queda como siempre."""
    if not getattr(proyecto, "formula", None):
        return {}
    from .guionista import cargar_formula

    try:
        return dict(cargar_formula(proyecto.formula).get("pexels") or {})
    except FileNotFoundError:
        return {}


def _cabeceras() -> dict:
    clave = clave_api("PEXELS_API_KEY")
    if not clave:
        raise SinClavePexels("falta la clave de Pexels (⚙ Ajustes)")
    return {"Authorization": clave, "User-Agent": "Xandart/1.0"}


def _revisar(r) -> None:
    if r.status_code in (401, 403):
        raise SinClavePexels(f"Pexels rechazó la clave (HTTP {r.status_code}): cópiala otra vez desde pexels.com/api "
                             "y guárdala en ⚙ Ajustes")
    r.raise_for_status()


def buscar(consulta: str, sesion=requests, fotos: int = FOTOS_POR_NIVEL, videos: int = VIDEOS_POR_NIVEL) -> list[dict]:
    """Candidatos de foto y video para una búsqueda, en un formato común."""
    salida = []
    r = sesion.get(API_FOTOS, params={"query": consulta, "per_page": fotos, "orientation": "landscape"},
                   headers=_cabeceras(), timeout=30) if fotos else None
    if r is not None:
        _revisar(r)
    for f in (r.json().get("photos", []) if r is not None else []):
        salida.append({"tipo": "foto", "pexels_id": f["id"], "url_origen": f["url"], "autor": f.get("photographer", ""),
                       "autor_url": f.get("photographer_url", ""), "miniatura": f["src"]["medium"],
                       "descarga": f["src"].get("large2x") or f["src"]["large"], "descripcion": f.get("alt", "")})
    r = sesion.get(API_VIDEOS, params={"query": consulta, "per_page": videos, "orientation": "landscape"},
                   headers=_cabeceras(), timeout=30)
    _revisar(r)
    for v in r.json().get("videos", []):
        archivos = [a for a in v.get("video_files", []) if a.get("file_type") == "video/mp4" and a.get("width")]
        if not archivos or v.get("duration", 0) < 3:
            continue
        # el más grande que no pase de 1920 de ancho
        mejor = max((a for a in archivos if a["width"] <= 1920), key=lambda a: a["width"], default=archivos[0])
        salida.append({"tipo": "video", "pexels_id": v["id"], "url_origen": v["url"],
                       "autor": (v.get("user") or {}).get("name", ""), "autor_url": (v.get("user") or {}).get("url", ""),
                       "miniatura": v.get("image", ""), "descarga": mejor["link"], "duracion": v.get("duration", 0)})
    return salida


def _hoja(candidatos: list[dict], destino: Path, sesion=requests) -> Path:
    """Hoja de contacto numerada (como la del Revisor), para verificar de un vistazo."""
    from PIL import Image, ImageDraw

    from .render import _fuente

    celdas, lado = [], (320, 200)
    for c in candidatos:
        try:
            im = Image.open(io.BytesIO(sesion.get(c["miniatura"], timeout=30).content)).convert("RGB")
            im.thumbnail(lado)
        except Exception:  # noqa: BLE001 — una miniatura rota no tumba la hoja
            im = Image.new("RGB", lado, (40, 40, 40))
        celdas.append(im)
    cols = 4
    filas = (len(celdas) + cols - 1) // cols
    hoja = Image.new("RGB", (cols * (lado[0] + 10), filas * (lado[1] + 40)), (18, 16, 24))
    d = ImageDraw.Draw(hoja)
    for k, (c, im) in enumerate(zip(candidatos, celdas)):
        x, y = (k % cols) * (lado[0] + 10), (k // cols) * (lado[1] + 40)
        hoja.paste(im, (x, y))
        d.text((x + 6, y + lado[1] + 6), f"#{k + 1} {'VIDEO' if c['tipo'] == 'video' else 'foto'}", fill=(255, 210, 120),
               font=_fuente(22))
    destino.parent.mkdir(parents=True, exist_ok=True)
    hoja.save(destino)
    return destino


@claude_cli.en_paso("Pexels: preparar las búsquedas")
def _busquedas(niveles: list[dict], carpeta: Path, ejecutar) -> dict[str, str]:
    lista = "\n".join(f"- nivel {n['numero']}: {n['nombre']}" for n in niveles)
    texto, _ = ejecutar("Para buscar fotos reales en un banco de imágenes en inglés, da para cada animal la búsqueda "
                        "más precisa (nombre común en inglés y, si ayuda, el científico). Animales:\n" + lista +
                        '\nResponde SOLO un JSON: {"<numero de nivel>": "<búsqueda en inglés>"}', cwd=carpeta)
    datos = claude_cli.extraer_json(texto) or {}
    return {str(k): str(v)[:80] for k, v in datos.items() if str(v).strip()}


@claude_cli.en_paso("Pexels: revisar fotos y videos (mira imágenes)")
def _verificar(nivel: dict, hoja: Path, candidatos: list[dict], carpeta: Path, ejecutar) -> dict[int, str]:
    texto, _ = ejecutar(
        f"Mira la hoja de contacto {hoja.relative_to(carpeta).as_posix()} con la herramienta Read. Tiene {len(candidatos)} "
        f"candidatos numerados (fotos y VIDEOS de un banco de imágenes). Tienen que mostrar: «{nivel['nombre']}».\n"
        "Aprueba SOLO los que muestran con claridad ESO (si es un animal, ESA especie y no una parecida; no un dibujo, "
        "no un juguete, sin texto ni marcas de agua grandes, que se vea bien). Si dudas, no lo apruebes.\n"
        'Responde SOLO un JSON: {"aprobados": [{"numero": <n>, "razon": "<por qué es esa especie>"}]}',
        cwd=carpeta, herramientas=["Read"])
    datos = claude_cli.extraer_json(texto) or {}
    salida = {}
    for a in datos.get("aprobados", []):
        try:
            n = int(a["numero"])
        except (KeyError, TypeError, ValueError):
            continue
        if 1 <= n <= len(candidatos):
            salida[n - 1] = str(a.get("razon", ""))[:200]
    return salida


@claude_cli.en_paso("Pexels: revisar la recreación (mira una imagen)")
def _verificar_recreacion(nivel: dict, archivo: Path, carpeta: Path, ejecutar) -> str | None:
    texto, _ = ejecutar(
        f"Mira la imagen {archivo.relative_to(carpeta).as_posix()} con la herramienta Read. Debe ser una recreación "
        f"fotográfica realista de «{nivel['nombre']}». Apruébala SOLO si la anatomía es correcta para ESA especie (patas, "
        "antenas, alas, colores), se ve como una foto y no tiene texto, deformaciones ni partes de más. Si dudas, no.\n"
        'Responde SOLO un JSON: {"aprobada": true|false, "razon": "<por qué>"}', cwd=carpeta, herramientas=["Read"])
    datos = claude_cli.extraer_json(texto) or {}
    return str(datos.get("razon", ""))[:200] if datos.get("aprobada") is True else None


def recrear(carpeta: Path, nivel: dict, busqueda: str, ejecutar, avisar=print, proveedor=None,
            permiso: bool = False, intentos: int = 2) -> dict | None:
    """Recreación ultra realista cuando Pexels no tiene nada verificado del animal."""
    from .config import ConfigCostos, leer_config
    from .costos import LibroCostos
    from .imagenes.proveedores import crear_proveedor

    config = ConfigCostos.cargar()
    proveedor = proveedor or crear_proveedor(config, leer_config("proveedores.json")["imagenes"])
    libro = LibroCostos(carpeta, config)
    prompt = PROMPT_REALISTA.format(especie=nivel["nombre"], busqueda=busqueda)
    destino = carpeta / "assets" / "stock" / f"nivel_{nivel['numero']}_foto_ia.png"
    for intento in range(intentos):
        libro.autorizar(proveedor.estimar_usd(prompt, []), permiso=permiso)      # freno: nunca pasa el máximo
        avisar(f"  Pexels no tiene «{nivel['nombre']}»: Gemini hace una recreación realista…")
        r = proveedor.generar(prompt, [])
        libro.registrar(modulo="imagenes", proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                        costo_usd=r.uso.costo_usd, detalle=f"recreación realista nivel {nivel['numero']}")
        destino.write_bytes(r.png)
        razon = _verificar_recreacion(nivel, destino, carpeta, ejecutar)
        if razon is not None:
            return {"archivo": destino.relative_to(carpeta).as_posix(), "tipo": "foto", "nivel": nivel["numero"],
                    "especie": nivel["nombre"], "busqueda": busqueda, "url_origen": "", "autor": "",
                    "autor_url": "", "pexels_id": None, "licencia": LICENCIA_IA, "verificado": True,
                    "sintetica": True, "razon": razon, "duracion": None}
        avisar(f"  la recreación de «{nivel['nombre']}» no pasó la revisión (intento {intento + 1})")
    destino.unlink(missing_ok=True)
    return None


def preparar_stock(carpeta: Path, ejecutar=claude_cli.revisor, avisar=print, sesion=requests,
                   recrear_faltantes: bool = True, proveedor=None, permiso: bool = False,
                   pex: dict | None = None) -> dict:
    """Busca, verifica y baja fotos y videos reales por nivel. Reanudable: los niveles
    ya revisados no se vuelven a buscar. `pex` (ajustes_pexels) puede pedir más videos por animal."""
    pex = pex or {}
    videos_buscar = int(pex.get("buscar_videos") or VIDEOS_POR_NIVEL)
    aprobadas = {**APROBADAS_POR_NIVEL, "video": int(pex.get("videos_por_animal") or APROBADAS_POR_NIVEL["video"])}
    ruta = carpeta / "assets" / "stock" / "stock.json"
    indice = leer_json(ruta) if ruta.exists() else {"archivos": [], "niveles_revisados": []}
    niveles = leer_json(carpeta / "escenas.json").get("niveles", [])
    if not niveles:
        return _stock_por_temas(carpeta, indice, ruta, ejecutar, avisar, sesion)
    pendientes = [n for n in niveles if n["numero"] not in indice["niveles_revisados"]]
    if not pendientes:
        return indice
    _cabeceras()                                            # sin clave, se avisa antes de gastar tiempo
    avisar("Claude está preparando las búsquedas de fotos y videos reales…")
    busquedas = _busquedas(pendientes, carpeta, ejecutar)
    for n in pendientes:
        consulta = busquedas.get(str(n["numero"]))
        if not consulta:
            continue
        avisar(f"Buscando fotos y videos reales de «{n['nombre']}» ({consulta})…")
        candidatos = buscar(consulta, sesion, videos=videos_buscar) + wikimedia.buscar(consulta, sesion)   # (20-10) + Wikimedia
        aprobados = {}
        if candidatos:
            hoja = _hoja(candidatos, carpeta / "assets" / "stock" / f"hoja_nivel_{n['numero']}.png", sesion)
            aprobados = _verificar(n, hoja, candidatos, carpeta, ejecutar)
        cuenta = {"foto": 0, "video": 0}
        for k, razon in sorted(aprobados.items()):
            c = candidatos[k]
            if cuenta[c["tipo"]] >= aprobadas[c["tipo"]]:
                continue
            cuenta[c["tipo"]] += 1
            ext = ".mp4" if c["tipo"] == "video" else ".jpg"
            destino = carpeta / "assets" / "stock" / f"nivel_{n['numero']}_{c['tipo']}_{cuenta[c['tipo']]}{ext}"
            r = sesion.get(c["descarga"], timeout=300)
            r.raise_for_status()
            destino.write_bytes(r.content)
            indice["archivos"].append({
                "archivo": destino.relative_to(carpeta).as_posix(), "tipo": c["tipo"], "nivel": n["numero"],
                "especie": n["nombre"], "busqueda": consulta, "url_origen": c["url_origen"], "autor": c["autor"],
                "autor_url": c["autor_url"], "pexels_id": c["pexels_id"], "licencia": c.get("licencia", LICENCIA),
                "fuente": c.get("fuente", "pexels"),
                "verificado": True, "razon": razon, "duracion": c.get("duracion")})
        if not any(cuenta.values()) and recrear_faltantes:
            (carpeta / "assets" / "stock").mkdir(parents=True, exist_ok=True)
            hecha = recrear(carpeta, n, consulta, ejecutar, avisar, proveedor, permiso)
            if hecha:
                indice["archivos"].append(hecha)
                cuenta["foto"] += 1
        indice["niveles_revisados"].append(n["numero"])
        escribir_json(ruta, indice)
        avisar(f"  «{n['nombre']}»: {cuenta['foto']} fotos y {cuenta['video']} videos verificados")
    escribir_json(ruta, indice)
    return indice


MAX_TEMAS = 24
VIDEOS_POR_LUGAR, VIDEOS_APROBADOS_LUGAR = 8, 2
MAX_LUGARES, MAX_ESCENAS_LUGAR = 6, 12


@claude_cli.en_paso("Pexels: elegir los lugares")
def elegir_lugares(carpeta: Path, escenas: list[dict], ejecutar) -> dict[str, str]:
    """(27-10) Claude elige las escenas cuya voz habla de un LUGAR (costa, selva, río, desierto, páramo, ciudad…) donde
    un video real del paisaje queda bien, sin animal ni personaje. Devuelve {id de escena: búsqueda en inglés}."""
    lista = "\n".join(f"- {e['id']}: {e['narracion'][:140]}" for e in escenas)
    if not lista:
        return {}
    texto, _ = ejecutar(
        "Estas son escenas de un video de animales (id: lo que dice la voz). Elige las que hablan de un LUGAR o paisaje "
        "(una región, costa, selva, río, desierto, páramo, montaña, ciudad, pueblo) donde mostrar un VIDEO REAL de ese "
        "paisaje queda bien. NO elijas escenas que necesitan ver al animal, a una persona o al personaje. "
        f"Máximo {MAX_LUGARES} lugares distintos y {MAX_ESCENAS_LUGAR} escenas en total; si no hay, devuelve la lista "
        "vacía. Para cada lugar da una búsqueda corta en inglés para un banco de videos, solo del paisaje y sin "
        'animales (ej.: "caribbean desert coast cactus").\nEscenas:\n' + lista +
        '\nResponde SOLO un JSON: {"lugares": [{"busqueda": "<inglés>", "escenas": [<id>, ...]}]}', cwd=carpeta)
    datos = claude_cli.extraer_json(texto) or {}
    validos = {str(e["id"]) for e in escenas}
    salida: dict[str, str] = {}
    for lugar in (datos.get("lugares") or [])[:MAX_LUGARES] if isinstance(datos, dict) else []:
        busqueda = str((lugar or {}).get("busqueda") or "").strip()[:80]
        for i in (lugar or {}).get("escenas") or []:
            if busqueda and str(i) in validos and len(salida) < MAX_ESCENAS_LUGAR:
                salida[str(i)] = busqueda
    return salida


def preparar_lugares(carpeta: Path, lugares: dict[str, str], ejecutar=claude_cli.revisor, avisar=print,
                     sesion=requests) -> dict:
    """Videos REALES de los lugares elegidos (solo videos, verificados en la hoja de contacto como todo lo demás)."""
    ruta = carpeta / "assets" / "stock" / "stock.json"
    indice = leer_json(ruta) if ruta.exists() else {"archivos": [], "niveles_revisados": []}
    if not lugares:
        return indice
    return _stock_por_temas(carpeta, indice, ruta, ejecutar, avisar, sesion, reales=lugares, solo_videos=True,
                            prefijo="lugar")


def _stock_por_temas(carpeta: Path, indice: dict, ruta: Path, ejecutar, avisar, sesion, reales: dict | None = None,
                     solo_videos: bool = False, prefijo: str = "tema") -> dict:
    """Videos sin niveles (documentales): lo que el director visual marcó como real en cada escena
    («congo river rapids»). Mismo cuidado: solo se usa lo que Claude aprueba en la hoja de contacto.
    Sin recreaciones con IA: si Pexels no tiene algo bueno, esa escena se dibuja."""
    if reales is None:
        dir_ruta = carpeta / "direccion.json"
        reales = (leer_json(dir_ruta).get("reales") or {}) if dir_ruta.exists() else {}
    revisados = set(indice.setdefault("temas_revisados", []))
    temas = [t for t in dict.fromkeys(reales.values()) if t not in revisados][:MAX_TEMAS]
    if not temas:
        return indice
    _cabeceras()
    for k, tema in enumerate(temas, 1):
        avisar(f"Buscando fotos y videos reales de «{tema}» ({k} de {len(temas)})…")
        candidatos = buscar(tema, sesion, fotos=0, videos=VIDEOS_POR_LUGAR) if solo_videos else \
            buscar(tema, sesion) + wikimedia.buscar(tema, sesion)
        aprobados = {}
        if candidatos:
            hoja = _hoja(candidatos, carpeta / "assets" / "stock" / f"hoja_{prefijo}_{len(revisados) + k}.png", sesion)
            aprobados = _verificar({"nombre": tema}, hoja, candidatos, carpeta, ejecutar)
        cuenta = {"foto": 0, "video": 0}
        for n, razon in sorted(aprobados.items()):
            c = candidatos[n]
            if cuenta[c["tipo"]] >= (VIDEOS_APROBADOS_LUGAR if solo_videos else APROBADAS_POR_NIVEL[c["tipo"]]):
                continue
            cuenta[c["tipo"]] += 1
            ext = ".mp4" if c["tipo"] == "video" else ".jpg"
            destino = carpeta / "assets" / "stock" / f"{prefijo}_{len(revisados) + k}_{c['tipo']}_{cuenta[c['tipo']]}{ext}"
            r = sesion.get(c["descarga"], timeout=300)
            r.raise_for_status()
            destino.write_bytes(r.content)
            indice["archivos"].append({
                "archivo": destino.relative_to(carpeta).as_posix(), "tipo": c["tipo"], "tema": tema, "nivel": None,
                "especie": tema, "busqueda": tema, "url_origen": c["url_origen"], "autor": c["autor"],
                "autor_url": c["autor_url"], "pexels_id": c["pexels_id"], "licencia": c.get("licencia", LICENCIA),
                "fuente": c.get("fuente", "pexels"),
                "verificado": True, "razon": razon, "duracion": c.get("duracion")})
        indice["temas_revisados"].append(tema)
        escribir_json(ruta, indice)
    return indice


def creditos(carpeta: Path) -> str:
    """Créditos para la descripción (Pexels no los exige; las fotos de Wikimedia con CC BY sí)."""
    ruta = carpeta / "assets" / "stock" / "stock.json"
    lineas = set()
    if ruta.exists():
        usados = [a for a in leer_json(ruta)["archivos"] if not a.get("sintetica")]
        lineas |= {wikimedia.credito(a) for a in usados}
    direccion = carpeta / "direccion.json"
    if direccion.exists():
        lineas |= {f"Foto de {f['autor']} en Pexels: {f['origen']}"
                   for f in (leer_json(direccion).get("fondos_lugar") or {}).values()}
    return "\n".join(sorted(lineas))


def _json(x) -> str:  # para depurar
    return json.dumps(x, ensure_ascii=False, indent=1)


def fondos_de_lugar(carpeta: Path, sesion=requests, avisar=print) -> int:
    """Fotos del LUGAR del que habla la voz (direccion.json → «lugares»: búsqueda en inglés), que salen
    desenfocadas de fondo detrás del dibujo, como en la competencia (el Coliseo detrás del animal).
    Pexels es gratis; una foto por escena, se baja una sola vez (reanudable). Es solo ambiente: no
    afirma nada sobre un animal, así que no necesita la verificación de Claude."""
    import re

    ruta = carpeta / "direccion.json"
    if not ruta.exists():
        return 0
    direccion = leer_json(ruta)
    lugares = direccion.get("lugares") or {}
    hechos = direccion.setdefault("fondos_lugar", {})
    nuevos = 0
    for eid, busqueda in lugares.items():
        if eid in hechos and (carpeta / hechos[eid]["archivo"]).exists():
            continue
        r = sesion.get(API_FOTOS, params={"query": busqueda, "per_page": 3, "orientation": "landscape"},
                       headers=_cabeceras(), timeout=30)
        _revisar(r)
        fotos = r.json().get("photos") or []
        if not fotos:
            avisar(f"  sin foto de «{busqueda}» en Pexels: esa escena queda sobre el papel")
            continue
        f = fotos[0]
        nombre = re.sub(r"[^a-z0-9]+", "_", busqueda.lower()).strip("_")[:40] or "lugar"
        destino = carpeta / "assets" / "lugares" / f"{nombre}_{f['id']}.jpg"
        if not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            datos = sesion.get(f["src"].get("large") or f["src"]["original"], timeout=60)
            datos.raise_for_status()
            destino.write_bytes(datos.content)
        hechos[eid] = {"archivo": destino.relative_to(carpeta).as_posix(), "busqueda": busqueda,
                       "origen": f["url"], "autor": f.get("photographer", ""), "licencia": LICENCIA}
        nuevos += 1
    if nuevos:
        escribir_json(ruta, direccion)
        avisar(f"{nuevos} fotos de lugares para el fondo (Pexels, gratis)")
    return nuevos
