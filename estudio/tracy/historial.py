"""Historial anti-repetición del modo Tracy (tabla `usos_clip` de la base).

- Stock: no se repite un clip de Pexels usado en los últimos 15 videos del mismo canal.
- Seminario: se evitan los tramos del clip base usados en los últimos 5 videos del canal.

«Últimos N videos» son los N slugs más recientes que registraron usos en ese canal (el video
que se está armando no cuenta: al rehacerlo se reemplazan sus propios usos). Sin base de datos
(pruebas sueltas, línea de comandos sin espacio) el historial queda vacío y no falla nada.
"""
from __future__ import annotations

ULTIMOS_STOCK = 15
ULTIMOS_SEMINARIO = 5


def _ultimos_slugs(s, espacio: str, canal: str, n: int, excluir: str | None) -> list[str]:
    from sqlalchemy import func, select

    from ..plataforma.modelos import UsoClip

    q = (select(UsoClip.slug, func.max(UsoClip.creado).label("ultimo"))
         .where(UsoClip.espacio_id == espacio, UsoClip.canal == canal)
         .group_by(UsoClip.slug).order_by(func.max(UsoClip.creado).desc()))
    return [slug for slug, _ in s.execute(q) if slug != excluir][:n]


def _usos(canal: str, tipo: str, n: int, excluir: str | None):
    try:
        from sqlalchemy import select

        from ..plataforma import contexto, db
        from ..plataforma.modelos import UsoClip

        esp = contexto.espacio_actual()
        if not esp:
            return []
        with db.sesion() as s:
            slugs = _ultimos_slugs(s, esp, canal, n, excluir)
            if not slugs:
                return []
            return [(u.clip, u.inicio, u.fin) for u in s.scalars(
                select(UsoClip).where(UsoClip.espacio_id == esp, UsoClip.canal == canal, UsoClip.tipo == tipo,
                                      UsoClip.slug.in_(slugs)))]
    except Exception:  # noqa: BLE001 — sin base: sin historial
        return []


def stock_usado(canal: str, excluir: str | None = None) -> set[str]:
    """Ids de Pexels usados en los últimos 15 videos del canal."""
    return {clip for clip, _, _ in _usos(canal, "stock", ULTIMOS_STOCK, excluir)}


def tramos_usados(canal: str, clip_base: str, excluir: str | None = None) -> list[tuple[float, float]]:
    """Tramos (inicio, fin) del clip base usados en los últimos 5 videos del canal."""
    return [(a, b) for clip, a, b in _usos(canal, "seminario", ULTIMOS_SEMINARIO, excluir)
            if clip == clip_base and a is not None and b is not None]


def registrar(canal: str, slug: str, usos: list[dict]) -> bool:
    """Reemplaza los usos de este video. usos = [{"tipo", "clip", "inicio"?, "fin"?}]."""
    try:
        from sqlalchemy import delete

        from ..plataforma import contexto, db
        from ..plataforma.modelos import UsoClip

        esp = contexto.espacio_actual()
        if not esp:
            return False
        with db.sesion() as s:
            s.execute(delete(UsoClip).where(UsoClip.espacio_id == esp, UsoClip.slug == slug))
            for u in usos:
                s.add(UsoClip(espacio_id=esp, canal=canal, slug=slug, tipo=u["tipo"], clip=str(u["clip"])[:200],
                              inicio=u.get("inicio"), fin=u.get("fin")))
        return True
    except Exception:  # noqa: BLE001
        return False
