"""Fotos y videos REALES de los animales, de Pexels (gratis, Licencia de Pexels).

1. Claude da, por cada nivel, cómo buscar al animal en inglés (nombre común y científico).
2. Se buscan fotos y videos en Pexels y se arma una hoja de contacto numerada por nivel.
3. Claude mira la hoja (herramienta Read) y aprueba SOLO los que muestran con claridad esa
   especie. Lo no verificado nunca se usa: el video no afirma una especie sobre algo dudoso.
4. Se bajan los aprobados a assets/stock/ con su registro: enlace de origen en Pexels,
   autor, licencia y por qué se aprobó (assets/stock/stock.json).

El Director de edición los usa de vez en cuando (no siempre) cuando la voz nombra al animal.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import requests

from . import claude_cli
from .config import clave_api, escribir_json, leer_json

API_FOTOS = "https://api.pexels.com/v1/search"
API_VIDEOS = "https://api.pexels.com/videos/search"
LICENCIA = "Licencia de Pexels: uso gratis, también comercial; sin atribución obligatoria (pexels.com/license)"
FOTOS_POR_NIVEL, VIDEOS_POR_NIVEL = 10, 6
APROBADAS_POR_NIVEL = {"foto": 2, "video": 1}


class SinClavePexels(RuntimeError):
    pass


def _cabeceras() -> dict:
    clave = clave_api("PEXELS_API_KEY")
    if not clave:
        raise SinClavePexels("falta la clave de Pexels (⚙ Ajustes)")
    return {"Authorization": clave}


def buscar(consulta: str, sesion=requests) -> list[dict]:
    """Candidatos de foto y video para una búsqueda, en un formato común."""
    salida = []
    r = sesion.get(API_FOTOS, params={"query": consulta, "per_page": FOTOS_POR_NIVEL, "orientation": "landscape"},
                   headers=_cabeceras(), timeout=30)
    r.raise_for_status()
    for f in r.json().get("photos", []):
        salida.append({"tipo": "foto", "pexels_id": f["id"], "url_origen": f["url"], "autor": f.get("photographer", ""),
                       "autor_url": f.get("photographer_url", ""), "miniatura": f["src"]["medium"],
                       "descarga": f["src"].get("large2x") or f["src"]["large"], "descripcion": f.get("alt", "")})
    r = sesion.get(API_VIDEOS, params={"query": consulta, "per_page": VIDEOS_POR_NIVEL, "orientation": "landscape"},
                   headers=_cabeceras(), timeout=30)
    r.raise_for_status()
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


def _busquedas(niveles: list[dict], carpeta: Path, ejecutar) -> dict[str, str]:
    lista = "\n".join(f"- nivel {n['numero']}: {n['nombre']}" for n in niveles)
    texto, _ = ejecutar("Para buscar fotos reales en un banco de imágenes en inglés, da para cada animal la búsqueda "
                        "más precisa (nombre común en inglés y, si ayuda, el científico). Animales:\n" + lista +
                        '\nResponde SOLO un JSON: {"<numero de nivel>": "<búsqueda en inglés>"}', cwd=carpeta)
    datos = claude_cli.extraer_json(texto) or {}
    return {str(k): str(v)[:80] for k, v in datos.items() if str(v).strip()}


def _verificar(nivel: dict, hoja: Path, candidatos: list[dict], carpeta: Path, ejecutar) -> dict[int, str]:
    texto, _ = ejecutar(
        f"Mira la hoja de contacto {hoja.relative_to(carpeta).as_posix()} con la herramienta Read. Tiene {len(candidatos)} "
        f"candidatos numerados (fotos y VIDEOS de un banco de imágenes). El video es sobre: «{nivel['nombre']}».\n"
        "Aprueba SOLO los que muestran con claridad ESA especie (no una parecida, no un dibujo, no un juguete, sin "
        "texto ni marcas de agua grandes, que se vea bien el animal). Si dudas, no lo apruebes.\n"
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


def preparar_stock(carpeta: Path, ejecutar=claude_cli.ejecutar, avisar=print, sesion=requests) -> dict:
    """Busca, verifica y baja fotos y videos reales por nivel. Reanudable: los niveles
    ya revisados no se vuelven a buscar."""
    ruta = carpeta / "assets" / "stock" / "stock.json"
    indice = leer_json(ruta) if ruta.exists() else {"archivos": [], "niveles_revisados": []}
    niveles = leer_json(carpeta / "escenas.json").get("niveles", [])
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
        candidatos = buscar(consulta, sesion)
        if not candidatos:
            indice["niveles_revisados"].append(n["numero"])
            continue
        hoja = _hoja(candidatos, carpeta / "assets" / "stock" / f"hoja_nivel_{n['numero']}.png", sesion)
        aprobados = _verificar(n, hoja, candidatos, carpeta, ejecutar)
        cuenta = {"foto": 0, "video": 0}
        for k, razon in sorted(aprobados.items()):
            c = candidatos[k]
            if cuenta[c["tipo"]] >= APROBADAS_POR_NIVEL[c["tipo"]]:
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
                "autor_url": c["autor_url"], "pexels_id": c["pexels_id"], "licencia": LICENCIA,
                "verificado": True, "razon": razon, "duracion": c.get("duracion")})
        indice["niveles_revisados"].append(n["numero"])
        escribir_json(ruta, indice)
        avisar(f"  «{n['nombre']}»: {cuenta['foto']} fotos y {cuenta['video']} videos verificados")
    escribir_json(ruta, indice)
    return indice


def creditos(carpeta: Path) -> str:
    """Créditos opcionales para la descripción (Pexels no los exige, pero se agradecen)."""
    ruta = carpeta / "assets" / "stock" / "stock.json"
    if not ruta.exists():
        return ""
    usados = leer_json(ruta)["archivos"]
    return "\n".join(sorted({f"{a['tipo'].capitalize()} de {a['autor']} en Pexels: {a['url_origen']}" for a in usados}))


def _json(x) -> str:  # para depurar
    return json.dumps(x, ensure_ascii=False, indent=1)
