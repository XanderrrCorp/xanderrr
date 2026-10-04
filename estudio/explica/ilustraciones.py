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
