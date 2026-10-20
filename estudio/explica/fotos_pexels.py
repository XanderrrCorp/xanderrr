"""Fotos REALES de Pexels para las escenas «foto» de El Calvo Explica (19-10, pedido del dueño: «usa Pexels cuando
sea necesario»). Gratis (Licencia de Pexels). Va antes que Google: solo lo que Pexels no tenga se pinta con IA.
Desde el 20-10 también Wikimedia Commons (..wikimedia: licencias libres, con crédito) en la misma hoja.

Por cada foto que pide una escena se traen hasta 4 candidatas; todas van en UNA hoja de contacto numerada y Claude
(modelo liviano) la mira UNA sola vez y elige, por escena, la que muestra exactamente lo que dice la voz, o ninguna.
La decisión queda guardada (ilustraciones/pexels.json): al rehacer el video no se vuelve a buscar ni a preguntar.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import requests

from .. import claude_cli, wikimedia
from ..config import escribir_json, leer_json

POR_FOTO = 4
POR_FOTO_WIKIMEDIA = 4         # (20-10) Pexels falla en cosas específicas: Commons suma candidatas a la misma hoja


def _clave(esc: dict) -> str:
    f = esc["foto"]
    return hashlib.sha1(f"{f.get('busqueda')}|{f['descripcion']}".encode()).hexdigest()[:12]


def _liviano(prompt: str, **k):
    return claude_cli.ejecutar(prompt, modelo="sonnet", pensamiento=1500, **k)


def buscar(c: Path, fotos: list[dict], t, sesion=requests, ejecutar=None) -> dict[str, Path]:
    """{clave de la escena: archivo} de las fotos aprobadas. Nunca frena el video: si algo falla, Google o código."""
    from ..stock import SinClavePexels, _hoja
    from ..stock import buscar as buscar_pexels

    d = c / "ilustraciones"
    d.mkdir(exist_ok=True)
    guardado_ruta = d / "pexels.json"
    guardado = leer_json(guardado_ruta) if guardado_ruta.exists() else {}
    salida: dict[str, Path] = {k: d / v for k, v in guardado.items() if v and (d / v).exists()}
    pendientes = [e for e in fotos if e["foto"].get("busqueda") and _clave(e) not in guardado]
    if not pendientes:
        return salida
    t.avisar(f"Buscando {len(pendientes)} foto(s) reales en Pexels y Wikimedia Commons…")
    candidatos, grupos = [], []
    con_pexels = True
    for e in pendientes:
        fotos_e = []
        if con_pexels:
            try:
                fotos_e = [x for x in buscar_pexels(e["foto"]["busqueda"], sesion) if x["tipo"] == "foto"][:POR_FOTO]
            except SinClavePexels:
                t.avisar("  sin clave de Pexels: solo se busca en Wikimedia Commons")
                con_pexels = False
            except Exception as ex:  # noqa: BLE001
                t.avisar(f"  Pexels no respondió ({str(ex)[:80]})")
        fotos_e += wikimedia.buscar(e["foto"]["busqueda"], sesion, POR_FOTO_WIKIMEDIA)   # (20-10)
        grupos.append((e, list(range(len(candidatos) + 1, len(candidatos) + 1 + len(fotos_e)))))
        candidatos += fotos_e
    elegidas: dict[str, int] = {}
    if candidatos:
        hoja = _hoja(candidatos, d / "pexels_hoja.png", sesion)
        lista = "\n".join(f"- escena {i + 1}: números {nums[0]} a {nums[-1]}. Debe mostrar: {e['foto']['descripcion'][:220]}"
                          for i, (e, nums) in enumerate(grupos) if nums)
        try:
            texto, _ = (ejecutar or _liviano)(
                f"Mira con la herramienta Read la imagen «{hoja.relative_to(c).as_posix()}»: fotos numeradas de un banco "
                f"de imágenes. Para cada escena elige la foto que muestra EXACTAMENTE lo que se pide (el mismo animal, "
                f"objeto o lugar; no uno parecido; sin texto grande ni marcas). Si ninguna sirve, null.\n{lista}\n"
                'Responde SOLO un JSON: {"escena 1": <número o null>, ...}', cwd=c, herramientas=["Read"])
            datos = claude_cli.extraer_json(texto) or {}
        except Exception as ex:  # noqa: BLE001
            t.avisar(f"  no se pudieron revisar las fotos de Pexels ({str(ex)[:80]})")
            datos = {}
        for i, (e, nums) in enumerate(grupos):
            n = datos.get(f"escena {i + 1}")
            if isinstance(n, int) and n in nums:
                elegidas[_clave(e)] = n
    creditos = []
    for e, nums in grupos:
        k = _clave(e)
        n = elegidas.get(k)
        guardado[k] = None
        if n is None:
            continue
        cand = candidatos[n - 1]
        try:
            from PIL import Image

            im = Image.open(io.BytesIO(sesion.get(cand["descarga"], timeout=60).content)).convert("RGB")
            nombre = (f"wikimedia_{cand['wikimedia_id']}.jpg" if cand.get("fuente") == "wikimedia"
                      else f"pexels_{cand['pexels_id']}.jpg")
            im.save(d / nombre, quality=92)
            guardado[k] = nombre
            salida[k] = d / nombre
            creditos.append(wikimedia.credito(cand))
        except Exception as ex:  # noqa: BLE001
            t.avisar(f"  no se pudo bajar una foto de Pexels ({str(ex)[:80]})")
    escribir_json(guardado_ruta, guardado)
    if creditos:
        with open(d / "creditos_pexels.txt", "a", encoding="utf-8") as f:
            f.write("\n".join(creditos) + "\n")
    t.avisar(f"Fotos reales de Pexels y Wikimedia: {len(elegidas)} de {len(pendientes)} (gratis)")
    return salida
