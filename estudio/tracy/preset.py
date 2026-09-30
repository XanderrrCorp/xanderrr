"""Preset del canal «Tracy» (modo visual stock + clip base).

Se guarda en `Canal.ajustes` de la base (sin migración): `visual_mode` y un bloque `tracy`
con lo propio del modo. Lo que falte se completa con los valores por defecto de aquí, así
que un canal sin nada guardado también funciona. Los canales de siempre no tienen
`visual_mode` y se tratan como «generated» (el pipeline de imágenes generadas, sin cambios).
"""
from __future__ import annotations

from typing import Any

from ..config import leer_config

CLAVE_CANAL = "tracy"
NOMBRE_CANAL = "Canal Tracy"

POR_DEFECTO: dict[str, Any] = {
    "voz_id": None,                 # None = la voz clonada de config/proveedores.json
    "velocidad": None,              # None = la de config/proveedores.json
    "clip_base": r"C:\Users\USUARIO\Videos\el mero mero.mp4",
    "proporcion_seminario": 0.4,    # 40 % seminario / 60 % stock
    "clip_max_s": 30.0,
    "clip_objetivo_s": [8.0, 20.0],
    "bloque_tts_max": 2500,         # caracteres por llamada a MiniMax
}


def preset_por_defecto() -> dict[str, Any]:
    return {k: (list(v) if isinstance(v, list) else v) for k, v in POR_DEFECTO.items()}


def completar(tracy: dict[str, Any] | None) -> dict[str, Any]:
    """Mezcla lo guardado con los valores por defecto y valida los rangos."""
    p = preset_por_defecto()
    p.update({k: v for k, v in (tracy or {}).items() if v is not None or k in ("voz_id", "velocidad")})
    p["proporcion_seminario"] = float(p["proporcion_seminario"])
    if not 0 <= p["proporcion_seminario"] <= 1:
        raise ValueError("proporcion_seminario va de 0 a 1 (0,4 = 40 % seminario)")
    p["clip_max_s"] = float(p["clip_max_s"])
    lo, hi = (float(x) for x in p["clip_objetivo_s"])
    if not 0 < lo <= hi <= p["clip_max_s"]:
        raise ValueError(f"clip_objetivo_s {lo}-{hi} debe quedar dentro de 0 y clip_max_s ({p['clip_max_s']})")
    p["clip_objetivo_s"] = [lo, hi]
    p["bloque_tts_max"] = int(p["bloque_tts_max"])
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
