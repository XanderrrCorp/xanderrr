"""Preset del canal «Tracy» (modo visual stock + clip base).

Se guarda en `Canal.ajustes` de la base (sin migración): `visual_mode` y un bloque `tracy`
con lo propio del modo. Lo que falte se completa con los valores por defecto de aquí, así
que un canal sin nada guardado también funciona. Los canales de siempre no tienen
`visual_mode` y se tratan como «generated» (el pipeline de imágenes generadas, sin cambios).
"""
from __future__ import annotations

import re
from typing import Any

from ..config import leer_config

CLAVE_CANAL = "tracy"
NOMBRE_CANAL = "Canal Tracy"

POR_DEFECTO: dict[str, Any] = {
    "voz_id": "moss_audio_5f02d02b-2e0e-11f1-803b-3af0d76118b0",   # voz del canal Tracy (None = la de proveedores.json)
    "velocidad": 1.0,               # ritmo natural de seminario (los stickman van a 1,3; aquí sonaba muy rápido)
    "clip_base": r"C:\Users\USUARIO\Videos\el mero mero.mp4",
    "proporcion_seminario": 0.4,    # 40 % seminario / 60 % stock
    "musica": r"C:\Users\USUARIO\Videos\musica tracy.mp3",   # de fondo, bajita; si no existe, sin música
    "volumen_musica_db": -16.0,     # respecto a la voz: se oye bien y no tapa (a -24 se oía muy bajo)
    "clip_max_s": 30.0,
    "clip_objetivo_s": [8.0, 20.0],
    "bloque_tts_max": 2500,         # caracteres por llamada a MiniMax
    # escena final fija: desde este punto del video (0,35 = desde el 35 %) hasta el final va el fondo de
    # naturaleza en blanco y negro con partículas, el presentador a un lado, el botón Suscríbete y las
    # ondas de la voz. 1 = sin escena final.
    "escena_final_desde": 0.35,
    "presentador": r"C:\Users\USUARIO\Videos\presentador tracy.png",
    "suscribete_cada_s": 60.0,
    "color_subtitulos": "#FFE21F",  # amarillo en todo el video
}


EXT_VIDEO = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v")
EXT_AUDIO = (".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac", ".wma")
EXT_IMAGEN = (".png", ".webp", ".jpg", ".jpeg")


def encontrar(ruta: str | None, extensiones: tuple[str, ...]) -> str | None:
    """La ruta tal cual o, si no está, la variante que dejó Windows al esconder las extensiones
    («musica tracy.mp3.mp3») o con otra extensión («musica tracy.m4a»). None si no hay nada."""
    if not ruta:
        return None
    from pathlib import Path

    r = Path(ruta)
    if r.is_file():
        return str(r)
    base = r.with_suffix("") if r.suffix.lower() in extensiones else r
    candidatos = [Path(f"{r}{e}") for e in extensiones] + [base.with_suffix(e) for e in extensiones]
    candidatos += [Path(f"{base.with_suffix(e)}{e2}") for e in extensiones for e2 in extensiones]
    return next((str(c) for c in candidatos if c.is_file()), None)


def preset_por_defecto() -> dict[str, Any]:
    return {k: (list(v) if isinstance(v, list) else v) for k, v in POR_DEFECTO.items()}


# valores por defecto de antes que quedaron guardados en el canal sin que el dueño los eligiera: se toman
# como «sin elegir» para que le lleguen los nuevos (voz más pausada y música más audible, 01-10)
VIEJOS_POR_DEFECTO = {"volumen_musica_db": (-22.0, -24.0)}


def completar(tracy: dict[str, Any] | None) -> dict[str, Any]:
    """Mezcla lo guardado con los valores por defecto y valida los rangos."""
    p = preset_por_defecto()
    p.update({k: v for k, v in (tracy or {}).items()
              if v is not None and v not in VIEJOS_POR_DEFECTO.get(k, ())})   # sin elegir = lo de por defecto
    p["proporcion_seminario"] = float(p["proporcion_seminario"])
    if not 0 <= p["proporcion_seminario"] <= 1:
        raise ValueError("proporcion_seminario va de 0 a 1 (0,4 = 40 % seminario)")
    p["clip_max_s"] = float(p["clip_max_s"])
    lo, hi = (float(x) for x in p["clip_objetivo_s"])
    if not 0 < lo <= hi <= p["clip_max_s"]:
        raise ValueError(f"clip_objetivo_s {lo}-{hi} debe quedar dentro de 0 y clip_max_s ({p['clip_max_s']})")
    p["clip_objetivo_s"] = [lo, hi]
    p["bloque_tts_max"] = int(p["bloque_tts_max"])
    p["volumen_musica_db"] = max(-40.0, min(0.0, float(p["volumen_musica_db"])))
    p["velocidad"] = max(0.7, min(1.5, float(p["velocidad"])))
    p["escena_final_desde"] = float(p["escena_final_desde"])
    if not 0.05 <= p["escena_final_desde"] <= 1:
        raise ValueError("escena_final_desde va de 0,05 a 1 (1 = sin escena final)")
    p["suscribete_cada_s"] = max(20.0, float(p["suscribete_cada_s"]))
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(p["color_subtitulos"])):
        p["color_subtitulos"] = POR_DEFECTO["color_subtitulos"]
    return p


def ajustes_voz(preset: dict[str, Any]) -> dict[str, Any]:
    """Ajustes para `VozMiniMax`: los de proveedores.json con la voz y la velocidad del canal."""
    base = dict(leer_config("proveedores.json")["voz"])
    if preset.get("voz_id"):
        base["voz_id"] = preset["voz_id"]
    if preset.get("velocidad"):
        base["velocidad"] = preset["velocidad"]
    return base


# ------------------------------------------------------------------ base de datos

def _canal(s, clave: str):
    from sqlalchemy import select

    from ..plataforma import contexto
    from ..plataforma.modelos import Canal

    esp = contexto.espacio_actual()
    if not esp:
        return None
    return s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave))


def visual_mode(clave_canal: str) -> str:
    """«stock» para los canales Tracy; «generated» para todos los demás (y si no hay base)."""
    try:
        from ..plataforma import db

        with db.sesion() as s:
            c = _canal(s, clave_canal)
            return (c.ajustes or {}).get("visual_mode", "generated") if c else "generated"
    except Exception:  # noqa: BLE001
        return "generated"


def cargar_preset(clave_canal: str = CLAVE_CANAL) -> dict[str, Any]:
    """Preset del canal (lo guardado + valores por defecto)."""
    guardado: dict[str, Any] | None = None
    try:
        from ..plataforma import db

        with db.sesion() as s:
            c = _canal(s, clave_canal)
            guardado = (c.ajustes or {}).get("tracy") if c else None
    except Exception:  # noqa: BLE001 — sin base: los valores por defecto
        guardado = None
    return completar(guardado)


def crear_canal_tracy(clave: str = CLAVE_CANAL, nombre: str = NOMBRE_CANAL, **cambios) -> dict[str, Any]:
    """Crea (o actualiza) el canal Tracy del espacio actual con visual_mode «stock».
    `cambios` son claves del preset (voz_id, clip_base, proporcion_seminario, …)."""
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
        preset = completar({**(ajustes.get("tracy") or {}), **{k: v for k, v in cambios.items() if v is not None}})
        ajustes["visual_mode"] = "stock"
        ajustes["tracy"] = preset
        c.ajustes = ajustes            # se reasigna entero para que SQLAlchemy note el cambio del JSON
        s.flush()
        return preset
