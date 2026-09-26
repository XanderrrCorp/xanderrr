"""Biblioteca local de música y efectos de sonido (sección 6).

La biblioteca se llena A MANO: el dueño suelta los archivos (por la página o en la
carpeta `biblioteca/entrada/`) y les asigna tipo o estado de ánimo, la fuente y la
licencia. Nada se descarga solo. Cada archivo queda registrado en
`biblioteca/indice.json` con su fuente, licencia, huella y fecha, y el Estudio solo
usa en los videos lo que tiene licencia registrada.

    biblioteca/
      indice.json
      sfx/<tipo>/<archivo>        tipos: golpe_grave, pop, zumbido, latido, subida_tension, alerta, comico, barrido
      musica/<animo>/<archivo>    ánimos: tension, misterio, epico, alivio, curiosidad, final
      entrada/                    carpeta para soltar archivos antes de registrarlos
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import RAIZ, escribir_json, leer_json

TIPOS_SFX = ("golpe_grave", "pop", "zumbido", "latido", "subida_tension", "alerta", "comico", "barrido")
ANIMOS_MUSICA = ("tension", "misterio", "epico", "alivio", "curiosidad", "final")
EXTENSIONES = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac")
# Licencias que permiten usar el audio en un video de YouTube monetizado. «Otra»
# obliga a escribir el detalle y queda marcada para que el dueño la revise.
LICENCIAS = {
    "youtube_audio_library": "Biblioteca de audio de YouTube (uso libre en YouTube)",
    "youtube_audio_library_atribucion": "Biblioteca de audio de YouTube · requiere atribución en la descripción",
    "cc0": "Dominio público (CC0)",
    "cc_by": "Creative Commons Atribución (CC BY) · requiere atribución",
    "propia": "Grabación o composición propia",
    "comprada": "Licencia comprada (guarda el comprobante)",
    "otra": "Otra (escribe el detalle)",
}
REQUIERE_ATRIBUCION = {"youtube_audio_library_atribucion", "cc_by"}


def raiz() -> Path:
    return Path(os.environ.get("XANDART_BIBLIOTECA") or RAIZ / "biblioteca")


def _indice_ruta() -> Path:
    return raiz() / "indice.json"


def indice() -> list[dict]:
    r = _indice_ruta()
    return leer_json(r).get("archivos", []) if r.exists() else []


def _guardar(archivos: list[dict]) -> None:
    escribir_json(_indice_ruta(), {"version": 1, "archivos": archivos})


def _nombre_seguro(nombre: str) -> str:
    base, ext = os.path.splitext(os.path.basename(nombre))
    base = re.sub(r"[^\w\-]+", "_", base, flags=re.UNICODE).strip("_")[:60] or "audio"
    return base + ext.lower()


def registrar(datos: bytes, nombre: str, clase: str, tipo: str, fuente: str, licencia: str,
              detalle_licencia: str = "", atribucion: str = "") -> dict:
    """Guarda un archivo en la biblioteca con su registro de fuente y licencia."""
    if clase not in ("sfx", "musica"):
        raise ValueError("clase debe ser sfx o musica")
    validos = TIPOS_SFX if clase == "sfx" else ANIMOS_MUSICA
    if tipo not in validos:
        raise ValueError(f"tipo no válido para {clase}: usa uno de {', '.join(validos)}")
    if not os.path.splitext(nombre)[1].lower() in EXTENSIONES:
        raise ValueError(f"formato no soportado: usa {', '.join(EXTENSIONES)}")
    if licencia not in LICENCIAS:
        raise ValueError("elige una licencia de la lista")
    if not fuente.strip():
        raise ValueError("escribe de dónde sale el archivo (enlace o nombre de la fuente)")
    if licencia == "otra" and not detalle_licencia.strip():
        raise ValueError("con licencia «Otra» escribe el detalle de la licencia")
    if licencia in REQUIERE_ATRIBUCION and not atribucion.strip():
        raise ValueError("esta licencia pide atribución: escribe el texto que va en la descripción del video")
    huella = hashlib.sha256(datos).hexdigest()[:16]
    archivos = indice()
    if any(a["huella"] == huella for a in archivos):
        raise ValueError("ese archivo ya está en la biblioteca")
    destino = raiz() / clase / tipo / f"{huella[:6]}_{_nombre_seguro(nombre)}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    registro = {"archivo": destino.relative_to(raiz()).as_posix(), "clase": clase, "tipo": tipo,
                "nombre_original": os.path.basename(nombre), "fuente": fuente.strip(), "licencia": licencia,
                "detalle_licencia": detalle_licencia.strip(), "atribucion": atribucion.strip(),
                "revisar_licencia": licencia == "otra", "huella": huella,
                "registrado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _guardar(archivos + [registro])
    return registro


def quitar(huella: str) -> None:
    archivos = indice()
    a = next((x for x in archivos if x["huella"] == huella), None)
    if not a:
        raise KeyError(huella)
    (raiz() / a["archivo"]).unlink(missing_ok=True)
    _guardar([x for x in archivos if x["huella"] != huella])


def pendientes_entrada() -> list[str]:
    """Archivos soltados en biblioteca/entrada/ que aún no tienen registro."""
    d = raiz() / "entrada"
    return sorted(p.name for p in d.iterdir() if p.suffix.lower() in EXTENSIONES) if d.exists() else []


def registrar_de_entrada(nombre: str, **kw) -> dict:
    origen = raiz() / "entrada" / os.path.basename(nombre)
    r = registrar(origen.read_bytes(), origen.name, **kw)
    origen.unlink()
    return r


def utilizables(clase: str, tipo: str) -> list[Path]:
    """Archivos de un tipo con licencia registrada (los «otra» sin revisar no se usan)."""
    return [raiz() / a["archivo"] for a in indice()
            if a["clase"] == clase and a["tipo"] == tipo and not a.get("revisar_licencia")
            and (raiz() / a["archivo"]).exists()]


def atribuciones(usados: list[str]) -> list[str]:
    """Textos de atribución de los archivos usados en un video (para la descripción)."""
    por_archivo = {a["archivo"]: a for a in indice()}
    return sorted({por_archivo[u]["atribucion"] for u in usados if u in por_archivo and por_archivo[u].get("atribucion")})


_CACHE: dict[str, np.ndarray] = {}


def leer_audio(ruta: Path, ffmpeg: str, sr: int = 48000) -> np.ndarray:
    """Decodifica cualquier formato a mono float32 con FFmpeg (con caché en memoria)."""
    clave = f"{ruta}|{ruta.stat().st_mtime}|{sr}"
    if clave not in _CACHE:
        crudo = subprocess.run([ffmpeg, "-v", "error", "-i", str(ruta), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                               capture_output=True, check=True).stdout
        _CACHE[clave] = np.frombuffer(crudo, np.float32).copy()
    return _CACHE[clave]


def resumen() -> dict:
    archivos = indice()
    cuenta = {f"{c}:{t}": 0 for c, ts in (("sfx", TIPOS_SFX), ("musica", ANIMOS_MUSICA)) for t in ts}
    for a in archivos:
        cuenta[f"{a['clase']}:{a['tipo']}"] = cuenta.get(f"{a['clase']}:{a['tipo']}", 0) + 1
    return {"archivos": archivos, "cuenta": cuenta, "licencias": LICENCIAS, "tipos_sfx": TIPOS_SFX,
            "animos_musica": ANIMOS_MUSICA, "entrada": pendientes_entrada(), "carpeta": str(raiz())}
