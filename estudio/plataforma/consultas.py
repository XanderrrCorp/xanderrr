"""Consultas pequeñas que el motor de video necesita sin saber de la base de datos."""
from __future__ import annotations


def nombre_canal(clave: str) -> str:
    """Nombre visible de un canal del espacio actual (si la base no está lista, la clave)."""
    try:
        from sqlalchemy import select

        from . import contexto, db
        from .modelos import Canal

        esp = contexto.espacio_actual()
        if not esp:
            return clave
        with db.sesion() as s:
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave))
            return c.nombre if c else clave
    except Exception:  # noqa: BLE001 — en modo viejo (sin base) basta la clave
        return clave


def canal_por_defecto() -> tuple[str, str] | None:
    """(clave del canal, clave de su estilo) del primer canal del espacio actual, o None."""
    try:
        from sqlalchemy import select

        from . import contexto, db
        from .modelos import Canal, Estilo

        esp = contexto.espacio_actual()
        if not esp:
            return None
        with db.sesion() as s:
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp).order_by(Canal.creado))
            if c is None:
                return None
            est = s.get(Estilo, c.estilo_id) if c.estilo_id else None
            return c.clave, (est.clave if est else "")
    except Exception:  # noqa: BLE001
        return None


def registrar_video(slug: str, titulo: str, carpeta: str, canal: str, minutos: float | None,
                    formato: str = "16:9", estado: str = "borrador") -> None:
    """Deja constancia en la base del video creado en el espacio actual (si hay espacio)."""
    try:
        from sqlalchemy import select

        from . import contexto, db
        from .modelos import Canal, Video

        esp = contexto.espacio_actual()
        if not esp:
            return
        with db.sesion() as s:
            v = s.scalar(select(Video).where(Video.espacio_id == esp, Video.slug == slug))
            if v is None:
                v = Video(espacio_id=esp, slug=slug, titulo=titulo, carpeta=carpeta)
                s.add(v)
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == canal))
            v.canal_id = c.id if c else None
            v.minutos, v.formato, v.estado = minutos, formato, estado
    except Exception:  # noqa: BLE001 — el video existe igual en su carpeta
        pass


def ajuste_canal(clave_canal: str, ajuste: str):
    """Un valor de Canal.ajustes del canal (por su clave) en el espacio actual; None si no lo eligió o no hay base."""
    try:
        from sqlalchemy import select

        from . import contexto, db
        from .modelos import Canal

        esp = contexto.espacio_actual()
        if not esp:
            return None
        with db.sesion() as s:
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave_canal))
            return (c.ajustes or {}).get(ajuste) if c else None
    except Exception:  # noqa: BLE001 — sin base: el valor por defecto de quien pregunta
        return None


def personaje_del_canal(clave_canal: str):
    """Carpeta del personaje hecho con el asistente que el canal tiene asignado, o None
    (los personajes que vienen del estilo, como la mascota de Peligro Tropical, siguen igual)."""
    try:
        from sqlalchemy import select

        from . import almacen, contexto, db
        from .modelos import Canal, Personaje

        esp = contexto.espacio_actual()
        if not esp:
            return None
        with db.sesion() as s:
            c = s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave_canal))
            p = s.get(Personaje, c.personaje_id) if c and c.personaje_id else None
            if p is None or not (p.datos or {}).get("asistente"):
                return None
            ruta = almacen.ruta(esp, "personajes", p.clave)
            return ruta if (ruta / "personaje.json").exists() else None
    except Exception:  # noqa: BLE001 — sin base, el video usa el personaje del estilo
        return None


def _canal(clave_canal: str):
    from sqlalchemy import select

    from . import contexto
    from .modelos import Canal

    esp = contexto.espacio_actual()
    return (lambda s: s.scalar(select(Canal).where(Canal.espacio_id == esp, Canal.clave == clave_canal))) if esp else None


def estilo_del_canal(clave_canal: str) -> str | None:
    """(21-10) Clave del estilo que el canal tiene elegido (el asistente de canal lo guarda), o None."""
    try:
        from . import db
        from .modelos import Estilo

        buscar = _canal(clave_canal)
        if buscar is None:
            return None
        with db.sesion() as s:
            c = buscar(s)
            est = s.get(Estilo, c.estilo_id) if c and c.estilo_id else None
            return est.clave if est else None
    except Exception:  # noqa: BLE001
        return None


def voz_del_canal(clave_canal: str) -> dict | None:
    """(21-10) Voz elegida para el canal ({voz_id, velocidad…} de la tabla de voces), o None = la de siempre."""
    try:
        from . import db
        from .modelos import Voz

        buscar = _canal(clave_canal)
        if buscar is None:
            return None
        with db.sesion() as s:
            c = buscar(s)
            v = s.get(Voz, c.voz_id) if c and c.voz_id else None
            if v is not None and v.clave == "voz_principal":
                return None        # la voz de siempre (copia de proveedores.json): se sigue leyendo de allá, igual que antes
            datos = dict(v.datos or {}) if v else {}
            return {k: datos[k] for k in ("voz_id", "velocidad", "modelo", "idioma") if datos.get(k)} or None
    except Exception:  # noqa: BLE001
        return None
