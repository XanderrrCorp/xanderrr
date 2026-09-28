"""Modo local (un computador, un dueño): la instalación se convierte en datos del espacio del dueño.

Orden, siempre: 1) copia de seguridad completa (base, proyectos, imágenes, audios, videos,
biblioteca, estilos y canales), 2) migración (solo agrega: nunca borra ni mueve los proyectos).
Corre en segundo plano al abrir Xandart; mientras tanto todo funciona como antes (sin espacio:
se buscan las carpetas de siempre). Si la copia falla, NO se migra y queda el aviso.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime

_CERROJO = threading.Lock()
_estado: dict = {}


def activo() -> bool:
    return os.environ.get("XANDART_SIN_MIGRAR", "") not in ("1", "true", "si")


def _clave() -> tuple[str, str]:
    return os.environ.get("XANDART_DATOS", ""), os.environ.get("XANDART_DB", "")


def _marca():
    from pathlib import Path

    from ..config import RAIZ

    return Path(os.environ.get("XANDART_DATOS") or RAIZ / "datos") / "copia_previa.json"


def _preparar() -> None:
    from .copias import CopiaFallida, hacer_copia
    from .migrar import migrar_instalacion

    try:
        marca = _marca()
        if not marca.exists():
            _estado.update(fase="copiando", detalle="Haciendo la copia de seguridad completa antes de preparar la plataforma…")
            info = hacer_copia("antes_de_la_plataforma")
            marca.parent.mkdir(parents=True, exist_ok=True)
            marca.write_text(json.dumps({"carpeta": info["carpeta"], "fecha": datetime.now().isoformat(timespec="seconds"),
                                         "bytes": info["total_bytes"]}, ensure_ascii=False), encoding="utf-8")
        _estado.update(fase="migrando", detalle="Registrando tus canales y videos…")
        from ..config import raiz_origen

        r = migrar_instalacion(raiz_origen())
        _estado.update(espacio=r["espacio"], resumen=r, error=None, fase="listo", detalle="")
    except CopiaFallida as ex:
        _estado.update(espacio=None, error=str(ex), fase="error", detalle=str(ex))
    except Exception as ex:  # noqa: BLE001 — la versión de siempre sigue sirviendo
        _estado.update(espacio=None, error=f"{ex.__class__.__name__}: {ex}", fase="error", detalle=str(ex))


def preparar(esperar: bool = True) -> None:
    """Arranca (una vez por base de datos) la copia y la migración; con esperar=False no bloquea."""
    if not activo():
        return
    clave = _clave()
    with _CERROJO:
        if _estado.get("clave") != clave:
            _estado.clear()
            hilo = threading.Thread(target=_preparar, daemon=True)
            _estado.update(clave=clave, hilo=hilo, fase="empezando", detalle="")
            hilo.start()
        hilo = _estado["hilo"]
    if esperar:
        hilo.join()


def espacio(esperar: bool = True) -> str | None:
    """Id del espacio del dueño, o None mientras se prepara (o si no se pudo)."""
    if not activo():
        return None
    preparar(esperar)
    return _estado.get("espacio") if _estado.get("clave") == _clave() else None


def estado() -> dict:
    return {"activo": activo(), "fase": _estado.get("fase", "sin_empezar" if activo() else "apagado"),
            "detalle": _estado.get("detalle", ""), "error": _estado.get("error")}


def error() -> str | None:
    return _estado.get("error")


def olvidar() -> None:
    """Para pruebas: la próxima llamada vuelve a preparar."""
    h = _estado.get("hilo")
    if h:
        h.join()
    _estado.clear()
