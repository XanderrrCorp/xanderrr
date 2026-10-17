"""Ilustraciones generadas de El Calvo Explica: mismo modelo de imagen que el resto de Xandart (Google),
estilo fijo y la imagen del personaje como referencia en cada pedido. Con freno de gasto y registro.
"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from ..config import ConfigCostos, escribir_json, leer_config, leer_json
from ..costos import LibroCostos, formato_cop
from . import canal as C

MODULO = "ilustracion_explica"

# Las 3 muestras son del primer video («Partes de tu cuerpo que YA NO SIRVEN para nada»). La de la muñeca prueba
# si un primer plano de anatomía se entiende con un personaje de palitos; si no, esos detalles van por código.
MUESTRAS = [
    ("muneca", "Plano cercano: el personaje se mira la muñeca con curiosidad. Junta la punta del pulgar con la punta "
               "del meñique y en el centro de la muñeca se marca un tendón delgado, como un cordón levantado bajo la "
               "piel. La mano y el antebrazo se ven grandes en primer plano; la cara del personaje asoma atrás."),
    ("piel_de_gallina", "El personaje tiene frío: se abraza a sí mismo, tiembla, con copos de nieve alrededor. En sus "
                        "brazos se ven muchos pelitos negros parados (piel de gallina)."),
    ("dentista", "El personaje está sentado en una silla de dentista gris, con la mejilla muy hinchada, una mano en la "
                 "cara y gesto de dolor. Al lado, una lámpara de dentista blanca."),
]
ACCESORIOS = ("Debe reconocerse siempre al mismo personaje de la referencia: cabeza redonda color crema, calvo, "
              "ojos grandes, cuerpo de palitos amarillo, mochila roja y tenis negros. La mochila roja se queda, "
              "salvo cuando está acostado o sentado de espaldas. Los accesorios van ENCIMA del personaje, sin "
              "cambiarle la cabeza, el color ni las proporciones.")


def carpeta() -> Path:
    from ..plataforma.db import carpeta_datos

    c = carpeta_datos() / "explica" / "muestras"
    c.mkdir(parents=True, exist_ok=True)
    return c


def referencia(destino: Path) -> Path:
    """Hoja del personaje (de frente y en dos poses) que va como referencia en cada generación."""
    from ..calma.raster import sprite

    img = Image.new("RGB", (1376, 768), "white")
    for i, (pose, x) in enumerate((("de_pie", 300), ("senalando_contento", 700), ("sentado", 1120))):
        s, (ax, ay) = sprite("personaje", {"pose": pose, "gesto": C.GESTO_POR_POSE[pose]}, 1.1)
        im = Image.fromarray(s[:, :, [2, 1, 0, 3]])
        img.paste(im, (int(x - ax), int(700 - ay)), im)
    img.save(destino)
    return destino


def prompt_foto(descripcion: str) -> str:
    return (f"Fotografía realista, nítida y bien iluminada, como de documental o de banco de fotos: {descripcion}\n\n"
            "Lo más fiel posible a la descripción. Formato horizontal 16:9, el sujeto grande y centrado. Sin texto, "
            "letras, marcas de agua ni logos sobre la imagen.")


def _texto_de(esc: dict, preset: dict | None = None) -> tuple[str, bool]:
    """(prompt, lleva el personaje de referencia) de una escena marcada."""
    if esc.get("foto"):
        return prompt_foto(esc["foto"]["descripcion"]), False
    return prompt(esc["google"]["descripcion"], preset), True


def prompt(descripcion: str, preset: dict | None = None) -> str:
    preset = preset or C.cargar()
    return (f"{preset['estilo_ilustracion']}\n\n{ACCESORIOS}\n\nEscena: {descripcion}\n\n"
            "Formato horizontal 16:9. Composición limpia con mucho blanco alrededor. El personaje se ve completo.")


def proveedor_imagenes(config: ConfigCostos):
    """El de Ajustes, como el resto de Xandart: Google (Together quedó descartado por el dueño)."""
    from ..imagenes.proveedores import crear_proveedor

    return crear_proveedor(config, leer_config("proveedores.json")["imagenes"])


def costo_muestras(proveedor=None) -> dict:
    config = ConfigCostos.cargar()
    p = proveedor or proveedor_imagenes(config)
    ref = carpeta() / "referencia_personaje.png"
    if not ref.exists():
        referencia(ref)
    usd = sum(p.estimar_usd(prompt(d), [ref]) for _, d in MUESTRAS)
    return {"usd": round(usd, 3), "cop": formato_cop(config.a_cop(usd)), "proveedor": p.nombre, "modelo": p.modelo}


def generar_muestras(t, permiso: bool = False, proveedor=None) -> list[str]:
    config = ConfigCostos.cargar()
    p = proveedor or proveedor_imagenes(config)
    c = carpeta()
    ref = referencia(c / "referencia_personaje.png")
    libro = LibroCostos(c, config)
    hechas = []
    for i, (nombre, desc) in enumerate(MUESTRAS):
        t.avisar(f"Generando la muestra {i + 1} de {len(MUESTRAS)} ({nombre})…")
        t.progreso = i / len(MUESTRAS)
        texto = prompt(desc)
        libro.autorizar(p.estimar_usd(texto, [ref]), permiso=permiso)
        r = p.generar(texto, [ref])
        libro.registrar(modulo=MODULO, proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                        costo_usd=r.uso.costo_usd, detalle=nombre)
        Image.open(io.BytesIO(r.png)).convert("RGB").save(c / f"{nombre}.png")
        hechas.append(f"{nombre}.png")
    total = sum(e.get("costo_usd", 0) for e in libro.entradas() if e.get("modulo") == MODULO)
    escribir_json(c / "muestras.json", {"archivos": hechas, "costo_total_usd": round(total, 4),
                                        "costo_total": formato_cop(config.a_cop(total)), "proveedor": p.nombre,
                                        "modelo": p.modelo})
    t.avisar(f"Listas las {len(hechas)} muestras · costo {formato_cop(config.a_cop(total))}")
    return hechas


def estado_muestras() -> dict | None:
    r = carpeta() / "muestras.json"
    return leer_json(r) if r.exists() else None


# ------------------------------------------------------------------ ilustraciones dentro de los videos (17-10)

def aplicar(c: Path, datos: dict, t, permiso: bool = False, proveedor=None) -> dict:
    """Dibuja con Google las escenas marcadas («google») y las cambia por esa imagen a pantalla completa (la cámara
    sigue moviéndose). Lo ya generado no se vuelve a pagar. Si se llega al máximo de gasto o falla una imagen, esa
    escena se queda con su versión por código: el video nunca se frena por esto."""
    import hashlib

    from ..costos import FrenoPresupuesto

    preset = C.cargar()
    fotos = [e for e in datos["escenas"] if e.get("foto")][:int(preset.get("max_fotos", 14))]
    marcadas = [e for e in datos["escenas"] if e.get("google") and not e.get("foto")] + fotos
    if not marcadas:
        return {"hechas": 0, "por_codigo": 0}
    config = ConfigCostos.cargar()
    dir_i = c / "ilustraciones"
    dir_i.mkdir(exist_ok=True)
    ref = dir_i / "referencia_personaje.png"
    if not ref.exists():
        referencia(ref)
    p, libro = None, LibroCostos(c, config)
    hechas = por_codigo = 0
    frenado = False
    for k, esc in enumerate(marcadas):
        texto, con_ref = _texto_de(esc, preset)
        refs = [ref] if con_ref else []
        archivo = dir_i / f"escena_{hashlib.sha1(texto.encode()).hexdigest()[:12]}.png"
        if not archivo.exists() and not frenado:
            try:
                p = p or proveedor or proveedor_imagenes(config)
                t.avisar(f"{'Foto' if esc.get('foto') else 'Ilustración'} {k + 1} de {len(marcadas)} con Google…")
                libro.autorizar(p.estimar_usd(texto, refs), permiso=permiso)
                r = p.generar(texto, refs)
                libro.registrar(modulo=MODULO, proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                                costo_usd=r.uso.costo_usd, detalle=archivo.name)
                Image.open(io.BytesIO(r.png)).convert("RGB").save(archivo)
            except FrenoPresupuesto as ex:
                frenado = True
                t.avisar(f"  {ex} Las demás ilustraciones quedan por código.")
            except Exception as ex:  # noqa: BLE001 — una imagen que falla no frena el video
                t.avisar(f"  no se pudo dibujar una escena con Google ({str(ex)[:120]}): queda por código")
        if archivo.exists():
            esc["elementos"] = [{"id": "ilustracion", "pieza": "imagen", "estado": {"archivo": str(archivo), "ancho": 1920},
                                 "posicion": [960, 540], "tamano": 1.0, "movimiento": [], "ya_estaba": True}]
            esc["fondo"] = "blanco"
            hechas += 1
        else:
            por_codigo += 1
    gastado = sum(e.get("costo_usd", 0) for e in libro.entradas() if e.get("modulo") == MODULO)
    con_fotos = any(e.get("foto") and e["elementos"] and e["elementos"][0].get("pieza") == "imagen" for e in fotos)
    t.avisar(f"Ilustraciones y fotos de Google: {hechas} (costo {formato_cop(config.a_cop(gastado))})"
             + (f"; {por_codigo} quedaron por código" if por_codigo else "")
             + (". Este video lleva fotos hechas con IA: al subirlo marca «Contenido alterado o sintético: Sí»."
                if con_fotos else ""))
    return {"hechas": hechas, "por_codigo": por_codigo, "fotos_ia": con_fotos}


def costo_estimado(c: Path, proveedor=None) -> dict | None:
    """Cuánto costarían las ilustraciones marcadas y los fondos pintados (uno por tema) que aún no se han hecho."""
    ruta = c / "escenas.json"
    if not ruta.exists():
        return None
    import json

    from .ambiente import fondos_faltantes, prompt_fondo

    escenas = json.loads(ruta.read_text(encoding="utf-8"))["escenas"]
    preset = C.cargar()
    marcadas = [e for e in escenas if e.get("google") and not e.get("foto")] + \
        [e for e in escenas if e.get("foto")][:int(preset.get("max_fotos", 14))]
    fondos = (fondos_faltantes(c, sum(1 for e in escenas if e.get("tipo") == "cuadricula"))
              if preset.get("fondos_tema", True) and preset.get("fondos_google") else 0)
    if not marcadas and not fondos:
        return None
    config = ConfigCostos.cargar()
    try:
        p = proveedor or proveedor_imagenes(config)
        usd = sum(p.estimar_usd(_texto_de(e, preset)[0], []) for e in marcadas)
        usd += fondos * p.estimar_usd(prompt_fondo("un lugar"), [])
    except Exception:  # noqa: BLE001 — sin proveedor configurado: no se puede estimar
        return {"imagenes": len(marcadas) + fondos, "fondos": fondos, "cop": "?"}
    return {"imagenes": len(marcadas) + fondos, "fondos": fondos, "cop": formato_cop(config.a_cop(usd))}
