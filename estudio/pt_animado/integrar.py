"""Fase 4 (aprobada por el dueño el 06-11): partes ANIMADAS dentro del video normal de Peligro Tropical.

Después de la voz (paso_video), solo en el canal de Peligro Tropical y solo si hay Node.js + la carpeta de Remotion:
  1. plan.planear elige INTRO, un ENCUENTRO por animal y CIERRE sobre las frases con su tiempo real (y Whisper si está);
     cada tramo se ajusta a los bordes de las escenas que cubre.
  2. El dibujo de cada animal se pide UNA vez a Google (caricatura de lado, fondo blanco → recortado), con el freno de
     gasto del proyecto; si frena o falla, ese animal no lleva encuentro animado (sale como siempre).
  3. Los clips se hacen con Remotion (tarjeta NVIDIA en el PC) en assets/pt_animado/clips, por huella (no se repiten).
  4. direccion.json «animacion_escena» marca las escenas cubiertas: la EDL las pone a pantalla completa con su
     «desde» dentro del clip (los subtítulos siguen encima). La capa de audio de la Fase 1 va sobre todo el video.
Si algo falla, el video sale igual que antes: esto nunca frena un video.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..config import escribir_json, leer_json
from .audio import capa
from .audio.capa import _norm

AJUSTE = "animado"                 # Canal.ajustes["animado"] = False lo apaga para ese canal
PRENDIDO_POR_DEFECTO = True        # el dueño aprobó las Fases 1-3 viendo el video de la granja (06-11)
REMOTION = Path(__file__).resolve().parent / "remotion"
CARPETA = Path("assets") / "pt_animado"
MODULO = "pt_animado"
PROMPT = ("Cartoon illustration of the animal «{nombre}» (its Spanish name), full body, side view facing LEFT, thick clean "
          "black outlines, flat bright colors, simple two-tone cel shading, friendly 2D animation style, anatomically "
          "recognizable, isolated on a pure white background, no ground, no shadow, no text, no people")
GRANDES = r"(toro|vaca|buey|caballo|yegua|burro|mula|oso|cocodril|caim|tibur|jaguar|leon|tigre|puma|hipop|rinoc|elefant|gorila|anaconda|alce|bufalo|camello|avestruz|jabali)"
PEQUENOS = r"(arana|alacran|escorpi|avispa|abeja|hormiga|oruga|ciempi|mosquit|zancud|garrapata|chinche|rana|sapo|raton|murcielago|pez|medusa)"


def activa(canal: str | None, ajustes: dict | None = None) -> bool:
    if canal != capa.CANAL_PT:
        return False
    if ajustes is not None:
        valor = ajustes.get(AJUSTE)
    else:
        from ..plataforma.consultas import ajuste_canal

        valor = ajuste_canal(canal, AJUSTE)
    return PRENDIDO_POR_DEFECTO if valor is None else bool(valor)


def listo_para_animar() -> str | None:
    """None si se puede; si no, el motivo en palabras simples."""
    if os.environ.get("XANDART_SIN_ANIMACION_PT"):
        return "apagada en este equipo"
    if not (REMOTION / "package.json").exists():
        return "falta la carpeta de animación"
    if not shutil.which("node"):
        return "falta Node.js en este PC"
    return None


def alto_de(nombre: str) -> float:
    n = _norm(nombre)
    if re.search(GRANDES, n):
        return 1.55
    if re.search(PEQUENOS, n):
        return 0.55
    return 0.9


def _animal_de_seccion(seccion: str | None, niveles) -> str | None:
    s = (seccion or "").lower()
    for n in niveles:
        if re.match(rf"nivel\s*{n.numero}\b", s):
            return n.nombre
    return None


def planear(escenas, niveles, palabras: list[dict] | None = None) -> list[dict]:
    """Tramos animados ya ajustados a las escenas: [{plantilla, a, b, escenas:[(id, desde)], props sin animal, animal}]"""
    from ..edicion import ADELANTO
    from .plan import planear as plan_tramos

    escenas = [e for e in escenas if e.tiempo.real_inicio is not None and e.tiempo.real_fin is not None]
    if len(escenas) < 3:
        return []
    frases = capa.frases_de_escenas(escenas)
    fin_total = round(max(e.tiempo.real_fin for e in escenas) + 1.2, 3)
    inicios = [0.0] + [max(0.0, e.tiempo.real_inicio - ADELANTO) for e in escenas[1:]]
    finales = inicios[1:] + [fin_total]
    primero = niveles[0].nombre if niveles else None
    salida = []
    for t in plan_tramos(frases, palabras, fin_total):
        idx = [i for i in range(len(escenas)) if t["inicio"] - 0.05 <= inicios[i] < t["fin"] - 0.5]
        if not idx:
            continue
        a, b = inicios[idx[0]], finales[idx[-1]]
        if b - a < 3.0:
            continue
        animal = None
        if t["plantilla"] == "encuentro":
            animal = _animal_de_seccion(t.get("capitulo"), niveles)
            if not animal:
                continue
        elif t["plantilla"] == "intro":
            animal = primero
        corr = t["inicio"] - a
        claves = {k: round(min(max(0.0, v + corr), b - a), 2) for k, v in t["claves"].items() if k != "fin"}
        claves["fin"] = round(b - a, 2)
        props = {"escenario": t["escenario"], "luz": t["luz"], "formato": "16:9", "claves": claves}
        if t.get("nivel") is not None:
            props["nivel"] = t["nivel"]
        if animal:
            props["altoAnimal"] = alto_de(animal)
        salida.append({"plantilla": t["plantilla"], "a": round(a, 3), "b": round(b, 3), "animal": animal, "props": props,
                       "escenas": [(escenas[i].id, round(inicios[i] - a, 3)) for i in idx]})
    return salida


def _slug(n: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(n)).strip("_") or "animal"


def dibujar_animales(carpeta: Path, nombres: list[str], permiso: bool, avisar=print, proveedor=None) -> dict[str, Path]:
    """Un dibujo por animal (caché por nombre). Respeta el freno de gasto: lo que no se pueda, queda fuera."""
    from ..config import ConfigCostos, leer_config
    from ..costos import FrenoPresupuesto, LibroCostos
    from .hacer_prueba import sin_fondo

    d = carpeta / CARPETA / "animales"
    d.mkdir(parents=True, exist_ok=True)
    listos: dict[str, Path] = {}
    config, libro, prov, frenado = ConfigCostos.cargar(), None, proveedor, False
    for n in dict.fromkeys(nombres):
        destino = d / f"{_slug(n)}.png"
        if not destino.exists() and not frenado:
            texto = PROMPT.format(nombre=n)
            try:
                if prov is None:
                    from ..imagenes.proveedores import crear_proveedor

                    prov = crear_proveedor(config, {**leer_config("proveedores.json")["imagenes"], "relacion_aspecto": "1:1"})
                libro = libro or LibroCostos(carpeta, config)
                libro.autorizar(prov.estimar_usd(texto, []), permiso=permiso)
                avisar(f"  dibujando el animal «{n}» para la animación…")
                r = prov.generar(texto, [])
                libro.registrar(modulo=MODULO, proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                                costo_usd=r.uso.costo_usd, detalle=destino.name)
                (d / f"{_slug(n)}_original.png").write_bytes(r.png)
                sin_fondo(r.png, destino)
            except FrenoPresupuesto as ex:
                frenado = True
                avisar(f"  {ex} Los demás animales van sin animación.")
            except Exception as ex:  # noqa: BLE001 — un animal que falla no frena el video
                avisar(f"  no se pudo dibujar «{n}» ({str(ex)[:120]}): sin animación para ese animal")
        if destino.exists():
            listos[n] = destino
    return listos


def renderizar_clips(lista: list[dict], salida: Path, avisar=print, timeout: int = 4 * 3600) -> None:
    """Remotion (scripts/clips.mjs): instala lo de Node la primera vez."""
    node = shutil.which("node")
    if not (REMOTION / "node_modules").exists():
        avisar("Preparando la animación por primera vez (instalando sus piezas)…")
        npm = shutil.which("npm") or "npm"
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=REMOTION, check=True, shell=npm.lower().endswith(".cmd"))
    archivo = salida / "lista.json"
    archivo.write_text(json.dumps(lista, ensure_ascii=False), encoding="utf-8")
    subprocess.run([node, "scripts/clips.mjs", str(salida), str(archivo), "2", "1"], cwd=REMOTION, check=True, timeout=timeout)
    from .hacer_prueba import limpiar_bundles

    limpiar_bundles()


def preparar(c, avisar=print, permiso: bool = False, render=renderizar_clips, proveedor=None) -> int:
    """Hace (o reusa) las partes animadas del video y las marca en direccion.json. Devuelve cuántas escenas cubren."""
    p = c.cargar()
    esc = c.cargar_escenas()
    direccion_ruta = c.ruta / "direccion.json"
    direccion = leer_json(direccion_ruta) if direccion_ruta.exists() else {}
    anteriores = direccion.get("animacion_escena") or {}
    propias = {k for k, v in anteriores.items() if v.get("origen") == MODULO}
    base = {k: v for k, v in anteriores.items() if k not in propias}        # las del video híbrido se respetan
    if not activa(p.canal) or esc.relacion_aspecto == "9:16":
        if propias:
            direccion["animacion_escena"] = base
            escribir_json(direccion_ruta, direccion)
        return 0
    motivo = listo_para_animar() if render is renderizar_clips else None
    if motivo:
        avisar(f"Sin partes animadas esta vez ({motivo}); el video sale como siempre.")
        return 0
    palabras = capa.palabras_whisper(c.ruta / "audio" / "voz.wav", capa.frases_de_escenas(esc.escenas))
    tramos = planear(esc.escenas, esc.niveles, palabras)
    if not tramos:
        return 0
    animales = dibujar_animales(c.ruta, [t["animal"] for t in tramos if t["animal"]], permiso, avisar, proveedor)
    tramos = [t for t in tramos if not t["animal"] or t["animal"] in animales]
    d = c.ruta / CARPETA / "clips"
    d.mkdir(parents=True, exist_ok=True)
    pedidos = []
    for t in tramos:
        props = dict(t["props"])
        props["animal"] = animales[t["animal"]].resolve().as_uri() if t["animal"] else None
        firma = hashlib.sha1(json.dumps([t["plantilla"], props], sort_keys=True).encode()).hexdigest()[:12]
        t["archivo"] = (CARPETA / "clips" / f"{t['plantilla']}_{firma}.mp4").as_posix()
        if not (c.ruta / t["archivo"]).exists():
            pedidos.append({"comp": t["plantilla"].capitalize(), "nombre": Path(t["archivo"]).stem, "props": props})
    if pedidos:
        minutos = sum(t["b"] - t["a"] for t in tramos) / 60
        avisar(f"Animando {len(pedidos)} partes del video ({minutos:.1f} min animados)…")
        try:
            render(pedidos, d, avisar)
        except Exception as ex:  # noqa: BLE001 — sin animación el video sale como siempre
            avisar(f"No se pudieron hacer las partes animadas ({str(ex)[:160]}); el video sale como siempre.")
    hechas = dict(base)
    for t in tramos:
        if not (c.ruta / t["archivo"]).exists():
            continue
        for eid, desde in t["escenas"]:
            hechas[str(eid)] = {"archivo": t["archivo"], "desde": desde, "efectos": [], "origen": MODULO}
    direccion["animacion_escena"] = hechas
    escribir_json(direccion_ruta, direccion)
    n = sum(1 for v in hechas.values() if v.get("origen") == MODULO)
    if n:
        avisar(f"Partes animadas listas: {n} escenas del video van animadas.")
    return n
