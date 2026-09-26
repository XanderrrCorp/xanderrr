"""
El FRENO DURO de presupuesto, en pesos, por video.

El medidor (`coste.py`) anota lo gastado DESPUES de cada llamada y solo avisa al
80 %. Esto va ANTES: si lo ya gastado en el video mas lo que va a costar la
llamada pasa del maximo, la llamada no se hace y se lanza `FrenoPresupuesto`.
Nunca se sigue gastando solo (principio 3 y regla 2.6 de la especificacion).

De donde sale cada numero, por contrato y no por import:

    el maximo y la TRM   config/costos.json de la raiz del repo (o ESTUDIO_COSTOS):
                         presupuesto_maximo_cop y trm_cop_por_usd. Es el mismo
                         fichero que usa el estimador del modulo `estudio`.
    por video            proyecto.config["presupuesto_maximo_cop"] lo sobrescribe,
                         y proyecto.config["permiso_superar_maximo"] = true es el
                         permiso explicito para seguir.

Lo que NO frena: lo que va contra la suscripcion (claude_cli), que no lleva
dolares. Y una llamada sin contexto de proyecto no se puede atribuir a ningun
video, asi que tampoco: se cuenta como huerfana en el medidor, como hasta ahora.
"""
import json
import os

RAIZ_ESTUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_COSTOS = (os.environ.get("ESTUDIO_COSTOS")
               or os.path.join(os.path.dirname(RAIZ_ESTUDIO), "config", "costos.json"))

#: Si todavia no hay ninguna imagen medida en el video, lo que se supone que
#: cuesta la primera. Por lo alto a proposito: mejor frenar una llamada de mas
#: que dejar pasar una de menos.
USD_IMAGEN_SIN_HISTORIA = 0.06


class FrenoPresupuesto(RuntimeError):
    """La llamada pasaria del maximo del video: se para y se pregunta."""


def _config():
    try:
        with open(RUTA_COSTOS, "r", encoding="utf-8") as fh:
            datos = json.load(fh)
        return float(datos["presupuesto_maximo_cop"]), float(datos["trm_cop_por_usd"])
    except (OSError, ValueError, KeyError, TypeError):
        return None, None


def limites(proyecto):
    """(maximo_cop, trm, permiso) para este video. maximo None = sin freno."""
    maximo, trm = _config()
    cfg = getattr(proyecto, "config", {}) or {}
    propio = cfg.get("presupuesto_maximo_cop")
    if isinstance(propio, (int, float)) and propio > 0:
        maximo = float(propio)
    return maximo, trm, bool(cfg.get("permiso_superar_maximo"))


def gastado_usd(medidor):
    """Lo que ya cuenta contra el presupuesto: todo lo que lleva dolares."""
    return sum(float(e.get("usd") or 0) for e in medidor.eventos()
               if e.get("usd") is not None)


def usd_medio_por_imagen(medidor):
    importes = [float(e["usd"]) for e in medidor.eventos()
                if e.get("proveedor") == "openai" and e.get("usd") is not None]
    return sum(importes) / len(importes) if importes else USD_IMAGEN_SIN_HISTORIA


def autorizar(medidor, usd_estimado, que="llamada"):
    """Lanza FrenoPresupuesto si esta llamada pasaria del maximo del video."""
    if medidor is None:
        return
    maximo, trm, permiso = limites(medidor.proyecto)
    if maximo is None or not trm or permiso:
        return
    ya = gastado_usd(medidor) * trm
    proyectado = ya + max(float(usd_estimado or 0), 0.0) * trm
    if proyectado > maximo:
        raise FrenoPresupuesto(
            f"FRENO DE PRESUPUESTO: {que} llevaria el video a {round(proyectado):,} COP, "
            f"por encima del maximo de {round(maximo):,} COP (ya gastado: {round(ya):,} COP). "
            "Para seguir hace falta permiso explicito "
            "(permiso_superar_maximo en la configuracion del video).".replace(",", "."))
