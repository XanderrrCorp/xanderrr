"""Biblioteca de movimientos (reutilizables). Ninguno es lineal: todos aceleran y frenan suave,
y los de entrada rematan con un rebote leve.

Cada movimiento de un elemento es un dict con «tipo» y su segundo de inicio «t» (si falta, el
segundo en que entra el elemento). La función `estado_en(elemento, t)` junta todos y dice cómo se
ve el elemento en ese instante: posición, escala, giro, desplazamiento por temblor y el estado
interno de la pieza (pose, ojos, relleno de la barra, aguja, color).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# ------------------------------------------------------------------ curvas de aceleración


def suave(p: float) -> float:
    """Arranca despacio, acelera y frena despacio (cúbica de entrada y salida)."""
    p = min(1.0, max(0.0, p))
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def frenar(p: float) -> float:
    """Sale rápido y frena al final (cúbica de salida)."""
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def rebote(p: float, fuerza: float = 1.70158) -> float:
    """Llega, se pasa un poco y vuelve (ease-out-back). fuerza 1,7 ≈ 10 % de pasada."""
    p = min(1.0, max(0.0, p))
    c3 = fuerza + 1
    return 1 + c3 * (p - 1) ** 3 + fuerza * (p - 1) ** 2


def resorte(p: float) -> float:
    """Pasada y un segundo rebote chiquito (para escalas de entrada)."""
    p = min(1.0, max(0.0, p))
    if p >= 1:
        return 1.0
    return 1 - math.exp(-6.5 * p) * math.cos(p * math.pi * 2.6) * (1 - p) ** 0.4


# ------------------------------------------------------------------ duraciones por defecto

DURACION = {"aparecer": 0.42, "deslizar": 0.55, "girar": 0.8, "crecer": 2.5, "llenar_barra": 1.2,
            "temblor": 0.4, "alternar_color": 0.0, "cambiar_pose": 0.0}
TIPOS = tuple(DURACION) + ("parpadear",)
PASADA_MAX = 1.14          # cuánto puede pasarse una escala de entrada (para dibujar nítido)


@dataclass
class Aspecto:
    visible: bool = False
    x: float = 0.0
    y: float = 0.0
    escala: float = 1.0
    giro: float = 0.0
    estado: dict = field(default_factory=dict)


def _p(t: float, t0: float, dur: float) -> float:
    return 1.0 if dur <= 0 else (t - t0) / dur


def _parpadeos(semilla: str, desde: float, hasta: float) -> list[float]:
    """Momentos de parpadeo cada 2-4 s (siempre los mismos para el mismo elemento)."""
    rng = random.Random(semilla)
    t, salida = desde + rng.uniform(0.6, 1.8), []
    while t < hasta:
        salida.append(t)
        if rng.random() < 0.15:                      # a veces un parpadeo doble
            salida.append(t + 0.3)
        t += rng.uniform(2.0, 4.0)
    return salida


PARPADEO_S = 0.13


def estado_en(el: dict, t: float, fin_escena: float) -> Aspecto:
    a = Aspecto()
    entra = float(el.get("entra", 0.0))
    if t < entra or (el.get("sale") is not None and t >= float(el["sale"])):
        return a
    a.visible = True
    a.x, a.y = (float(v) for v in el.get("posicion", (960, 540)))
    a.escala = float(el.get("tamano", 1.0))
    a.giro = float(el.get("rotacion", 0.0))
    a.estado = dict(el.get("estado") or {})
    movs = el.get("movimiento") or []
    if isinstance(movs, (str, dict)):
        movs = [movs]
    movs = [{"tipo": m} if isinstance(m, str) else m for m in movs]
    dx = dy = 0.0
    for m in sorted(movs, key=lambda m: float(m.get("t", entra))):
        tipo = m["tipo"]
        t0 = float(m.get("t", entra))
        dur = float(m.get("duracion", DURACION.get(tipo, 0.5)))
        if t < t0 and tipo not in ("aparecer", "deslizar"):
            continue
        p = _p(t, t0, dur)
        if tipo == "aparecer":
            a.escala *= max(0.0, resorte(p)) if t >= t0 else 0.0
        elif tipo == "deslizar":
            if "desde" in m:                         # entra deslizando desde un punto
                x0, y0 = m["desde"]
                k = rebote(p, float(m.get("fuerza", 1.1))) if t >= t0 else 0.0
                dx += (float(x0) - a.x) * (1 - k)
                dy += (float(y0) - a.y) * (1 - k)
            elif "hasta" in m and t >= t0:           # se va hacia un punto (sale con aceleración)
                x1, y1 = m["hasta"]
                k = suave(p) if m.get("suave", True) else frenar(p)
                dx += (float(x1) - a.x) * k
                dy += (float(y1) - a.y) * k
        elif tipo == "girar":
            if "velocidad" in m:                     # vueltas continuas (grados por segundo), arranque suave
                v, dt, rampa = float(m["velocidad"]), t - t0, 0.5
                giro = v * dt * dt / (2 * rampa) if dt < rampa else v * (dt - rampa / 2)
            else:
                giro = float(m.get("grados", 360)) * rebote(p, 1.2)
            if m.get("parte"):                       # gira algo de adentro (la aguja del cronómetro)
                a.estado[m["parte"]] = round((float(a.estado.get(m["parte"], 0)) + giro) / 3) * 3 % 360
            else:
                a.giro += giro
        elif tipo == "crecer":
            a.escala *= 1 + (float(m.get("hasta", 1.35)) - 1) * suave(p)
        elif tipo == "llenar_barra":
            r0, r1 = float(m.get("desde", 0.0)), float(m.get("hasta", 1.0))
            a.estado["relleno"] = round((r0 + (r1 - r0) * suave(p)) * 100) / 100
        elif tipo == "alternar_color":
            periodo = float(m.get("periodo", 0.3))
            valores = m.get("valores", ["amarillo", "rojo"])
            a.estado[m.get("campo", "color")] = valores[int((t - t0) / periodo) % len(valores)]
        elif tipo == "cambiar_pose":
            a.estado.update(m.get("estado") or {})
        elif tipo == "temblor":
            if p < 1:
                amp = float(m.get("fuerza", 16)) * (1 - p) ** 2
                dx += amp * math.sin((t - t0) * 2 * math.pi * 13)
                dy += amp * 0.6 * math.cos((t - t0) * 2 * math.pi * 17)
    if el.get("pieza") in ("personaje", "vecino"):
        # nunca congelado: parpadea cada 2-4 s y respira (sube y baja un poquito)
        if a.estado.get("ojos", "abiertos") != "cerrados":
            for tp in _parpadeos(str(el.get("id", "")), entra, fin_escena):
                if tp <= t < tp + PARPADEO_S:
                    a.estado["ojos"] = "cerrados"
                    break
        a.escala *= 1 + 0.008 * math.sin((t - entra) * 2 * math.pi / 2.6)
    a.x += dx
    a.y += dy
    return a


def temblor_pantalla(temblores: list[dict], t: float) -> tuple[float, float]:
    dx = dy = 0.0
    for m in temblores:
        t0 = float(m.get("t", 0))
        dur = float(m.get("duracion", 0.35))
        if t0 <= t < t0 + dur:
            amp = float(m.get("fuerza", 14)) * (1 - (t - t0) / dur) ** 2
            dx += amp * math.sin((t - t0) * 2 * math.pi * 14)
            dy += amp * math.cos((t - t0) * 2 * math.pi * 11)
    return dx, dy


def escala_maxima(el: dict) -> float:
    """La escala más grande que tendrá el elemento (para dibujarlo una vez nítido a ese tamaño)."""
    movs = el.get("movimiento") or []
    if isinstance(movs, (str, dict)):
        movs = [movs]
    k = 1.0
    for m in movs:
        m = {"tipo": m} if isinstance(m, str) else m
        if m["tipo"] == "aparecer":
            k = max(k, PASADA_MAX)
        elif m["tipo"] == "crecer":
            k *= float(m.get("hasta", 1.35))
    return float(el.get("tamano", 1.0)) * k * (1.01 if el.get("pieza") in ("personaje", "vecino") else 1.0)
