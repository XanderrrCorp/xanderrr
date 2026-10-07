"""Configuración del canal «El Calvo Explica» (se guarda en Canal.ajustes["explica"], sin migración).

Lo que falte en lo guardado se completa con POR_DEFECTO, así que un cambio de valor por defecto
llega solo a los canales que no lo eligieron.
"""
from __future__ import annotations

from typing import Any

CLAVE_CANAL = "el-calvo-explica"
NOMBRE_CANAL = "El Calvo Explica"          # provisional: el nombre público lo da el dueño después

# Cara por defecto de cada pose en este canal (pedido del dueño): amable; preocupada solo en confundido,
# encogido de hombros y acostado. Ojos y cara siguen siendo piezas aparte (parpadeo y cambios de gesto).
GESTO_POR_POSE = {
    "de_pie": "amable", "senalando": "amable", "sentado": "amable", "corriendo": "concentrado",
    "agachado": "concentrado", "asustado": "susto",
    "tablero": "seguro", "pensando": "pensativo", "confundido": "duda", "hombros": "neutral",
    "sorprendido": "sorpresa", "aliviado": "aliviado", "idea": "contento", "acostado": "neutral",
    "rechazo": "disgusto", "senalando_contento": "contento",
}
OJOS_POR_POSE = {"acostado": "cerrados", "rechazo": "otro_lado"}

POR_DEFECTO: dict[str, Any] = {
    "voz_id": None,                 # None = la de proveedores.json (la misma de Peligro Tropical)
    "velocidad": 1.3,               # igual de rápida que Peligro Tropical (a 1,0 el dueño lo sintió lento)
    "pausa_max_s": 0.22,            # los silencios entre frases se recortan a esto (ritmo de editor)
    "pausa_tras_nombre_s": 0.6,     # tras el nombre de cada tema sí queda una pausa (para la cuadrícula)
    "musica": None,                 # None = tranquila y constante, elegida de la biblioteca
    "volumen_musica_db": -27.0,
    "efectos_sonido": True,         # pop, swoosh, rayón, golpe, X y chulo, generados por código (sin licencias)
    "fondo": "blanco",
    # molde del guion
    "temas": [8, 9],
    "palabras_video": [1200, 1500],
    "palabras_tema": [150, 170],
    "palabras_por_parte": {"nombre": [1, 4], "escena": [50, 60], "bautizo": [10, 15],
                           "explicacion": [60, 70], "cierre": [10, 20]},
    "max_palabras_frase": 20,
    "max_misma_formula": 2,         # la misma fórmula de hipótesis en máximo dos temas por video
    "cierre_video": "Y ahora ya sabes un poco más sobre {tema}. Si te gustó, suscríbete.",
    # escenas
    "segundos_escena": [1.0, 3.0],
    "cambio_cada_s": [2.0, 3.0],
    "ilustraciones_por_tema": [6, 7],
    "max_ilustraciones": 60,        # las que sobren pasan a escenas de código
    "estilo_ilustracion": (
        "Ilustración simple de explicación: línea negra gruesa tipo marcador, ligeramente temblorosa, colores "
        "planos (negro, blanco, gris, amarillo, rojo, verde), fondo blanco liso, sin sombras ni degradados. "
        "El personaje es el de la imagen de referencia: cabeza redonda color crema, calvo, cejas neutras y cara amable, "
        "ojos grandes, cuerpo de palitos amarillo, mochila roja y tenis negros; no lo cambies (la mochila no va "
        "cuando está acostado o sentado de espaldas). "
        "Sin texto, letras ni números dentro de la imagen. Sin personas reales, sin personajes de películas, "
        "series o videojuegos, sin marcas ni logos."),
    "titulo": "TODAS las {x} explicadas en {n} minutos",
    "ritmo": 0.75,                  # animaciones un 25 % más cortas
    "deriva_camara": 0.04,          # cada escena se acerca o se aleja un 4 % mientras dura (nada queda quieto)
}


def completar(guardado: dict[str, Any] | None) -> dict[str, Any]:
    p = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in POR_DEFECTO.items()}
    p.update({k: v for k, v in (guardado or {}).items() if v is not None and k in POR_DEFECTO})
    return p


def _canal(s, clave: str):
    from ..tracy.preset import _canal as buscar

    return buscar(s, clave)


def cargar(clave: str = CLAVE_CANAL) -> dict[str, Any]:
    try:
        from ..plataforma import db

        with db.sesion() as s:
            c = _canal(s, clave)
            return completar((c.ajustes or {}).get("explica") if c else None)
    except Exception:  # noqa: BLE001 — sin base: los valores por defecto
        return completar(None)


def crear_canal(clave: str = CLAVE_CANAL, nombre: str = NOMBRE_CANAL, **cambios) -> dict[str, Any]:
    """Crea el canal en el espacio actual (si ya existe, lo configurado no se toca salvo `cambios`)."""
    from ..plataforma import contexto, db
    from ..plataforma.modelos import Canal

    esp = contexto.espacio_actual()
    if not esp:
        raise RuntimeError("no hay espacio de trabajo: abre Xandart una vez para prepararlo")
    with db.sesion() as s:
        c = _canal(s, clave)
        if c is None:
            c = Canal(espacio_id=esp, clave=clave, nombre=nombre)
            s.add(c)
        ajustes = dict(c.ajustes or {})
        preset = completar({**(ajustes.get("explica") or {}), **{k: v for k, v in cambios.items() if v is not None}})
        ajustes["visual_mode"] = "explica"
        ajustes["explica"] = {k: v for k, v in preset.items() if v != POR_DEFECTO.get(k)}   # solo lo elegido
        c.ajustes = ajustes
        s.flush()
        return preset


def ajustes_voz(preset: dict[str, Any]) -> dict[str, Any]:
    """Ajustes para VozMiniMax: la voz de proveedores.json (Peligro Tropical) a la velocidad del canal."""
    from ..config import leer_config

    base = dict(leer_config("proveedores.json")["voz"])
    if preset.get("voz_id"):
        base["voz_id"] = preset["voz_id"]
    base["velocidad"] = float(preset.get("velocidad") or 1.0)
    return base
