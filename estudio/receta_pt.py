"""La receta de edición de Peligro Tropical que mandó el dueño (07-10), encima de la edición «deslizar»:

- ambiente por nivel: los niveles bajos en papel claro (sonidos graciosos); la mitad alta en fondo negro con humo,
  viñeta fuerte, temblor corto en los golpes, latido y zumbido;
- «PERO ESPERA» que crece con un triángulo vibrando y una subida, justo antes del último nivel;
- tarjeta de veredicto al final de cada nivel («Nivel de amenaza: Grave»), con sello o campanita;
- destello blanco al salir de la tira de niveles;
- subtítulos de 1 a 3 palabras con la palabra que se dice en amarillo;
- llamados a la acción: like (~1:40) con la mascota que salta, y suscripción (~3:00) pequeña sin parar el video;
- cierre: la tira pasa entera (carrusel) con una subida y, al final, la mascota al centro sobre fondo oscuro.

Se activa con `receta: true` en el perfil de edición (perfiles/peligro_tropical_v2.json).
"""
from __future__ import annotations

import random

LIKE_S = 100.0
SUSCRIBIR_S = 180.0


def veredicto(valor: int) -> tuple[str, bool]:
    """Texto de la tarjeta y si es leve (check verde) según el peligro 0–10."""
    if valor <= 1:
        return "No hay amenaza", True
    if valor <= 3:
        return "Mínimo", True
    if valor <= 5:
        return "Moderado", False
    if valor <= 7:
        return "Alto", False
    if valor <= 9:
        return "Grave", False
    return "Extremo", False


def _nivel_de_clips(clips: list, escenas: list) -> list[int | None]:
    """Nivel de cada clip: 0 en el gancho, k desde la tira del nivel k, None en el cierre."""
    salida, actual = [], 0
    for c, e in zip(clips, escenas):
        t = next((x for x in c["efectos"] if x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar")), None)
        if t:
            actual = int(t["hasta"])
        salida.append(None if e.seccion.lower().startswith("cierre") else actual)
    return salida


def _libre(c: dict) -> bool:
    """Un clip donde se puede poner algo encima (no es la tira, ni una animación, ni un video real)."""
    return c["modo"] != "tira" and not any(x["efecto"] in ("animacion", "video_real", "foto_real", "reaccion_presentador")
                                           for x in c["efectos"])


def palabras_con_tiempo(texto: str, a: float, b: float) -> list[list]:
    """[palabra, inicio, fin] repartidos por largo dentro del trozo de subtítulo."""
    ps = texto.split()
    pesos = [0.6 + len(p) for p in ps]
    total, acum, salida = sum(pesos) or 1.0, 0.0, []
    for p, w in zip(ps, pesos):
        ini = a + (b - a) * acum / total
        acum += w
        salida.append([p, round(ini, 3), round(a + (b - a) * acum / total, 3)])
    return salida


def aplicar(clips: list, textos: list, subtitulos: list, sfx: list, escenas: list, esc, sfx_fn,
            valor_de, poses: dict, rng: random.Random, total: float) -> None:
    """Aplica la receta sobre la edición ya armada (modifica las listas en su lugar)."""
    niveles = sorted(n.numero for n in esc.niveles)
    n_niv = len(niveles)
    nivel = _nivel_de_clips(clips, escenas)
    por_numero = {n.numero: n for n in esc.niveles}

    # --- ambiente por nivel
    for idx, (c, k) in enumerate(zip(clips, nivel)):
        alto = bool(k and n_niv and k > n_niv / 2)
        if not _libre(c):
            continue
        if alto:
            c["efectos"].append({"efecto": "ambiente_oscuro"})
            golpes = [x for x in sfx if x["clip"] == idx and x["tipo"] == "golpe_grave"]
            for g in golpes:
                c["efectos"].append({"efecto": "temblor_corto", "en": round(g["inicio"], 3), "dur": 0.35})
        elif k is not None and escenas[idx].intencion in ("humor", "pregunta_al_espectador") and rng.random() < 0.6:
            sfx_fn(sfx, "boing", c["inicio"] + 0.15, idx, "Boing gracioso: nivel bajo, tono ligero")
    # al entrar a un nivel alto: latido y zumbido grave
    for idx, (c, k) in enumerate(zip(clips, nivel)):
        t = next((x for x in c["efectos"] if x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar")), None)
        if t and n_niv and int(t["hasta"]) > n_niv / 2:
            sfx_fn(sfx, "latido", c["inicio"] + 0.9, idx, "Latido: empieza un nivel peligroso")

    # --- destello blanco al salir de la tira
    for idx in range(1, len(clips)):
        if clips[idx - 1]["modo"] == "tira" and clips[idx]["modo"] != "tira":
            clips[idx]["efectos"].append({"efecto": "destello_blanco", "en": clips[idx]["inicio"]})

    # --- veredicto al final de cada nivel (el último clip antes de la tira siguiente o del cierre)
    for k in niveles:
        idxs = [i for i, x in enumerate(nivel) if x == k and clips[i]["modo"] != "tira"]
        if not idxs:
            continue
        i = idxs[-1]
        c = clips[i]
        dur = c["fin"] - c["inicio"]
        if not _libre(c) or dur < 1.6:
            continue
        n = por_numero[k]
        valor = valor_de(n)
        texto, leve = veredicto(valor)
        d = round(min(1.9, dur - 0.2), 3)
        en = round(c["fin"] - d, 3)
        c["efectos"].append({"efecto": "veredicto", "en": en, "dur": d, "texto": texto, "leve": leve,
                             "nivel": k})
        sfx_fn(sfx, "campanita" if leve else "sello", en + 0.35, i,
               f"{'Campanita' if leve else 'Sello'}: veredicto del nivel {k} ({texto})")

    # --- «PERO ESPERA» antes del último nivel
    ultimo = max(niveles) if niveles else None
    tira_ultimo = next((i for i, c in enumerate(clips)
                        if any(x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar") and x.get("hasta") == ultimo
                               for x in c["efectos"])), None)
    if tira_ultimo and tira_ultimo > 0:
        c = clips[tira_ultimo - 1]
        dur = c["fin"] - c["inicio"]
        if c["modo"] != "tira" and dur >= 1.2:
            # si ahí estaba el veredicto del nivel anterior, «pero espera» va justo después
            ver = next((x for x in c["efectos"] if x["efecto"] == "veredicto"), None)
            d = round(min(1.4, dur - 0.1), 3)
            if ver:
                ver["dur"] = round(max(0.9, ver["dur"] - d), 3)
                d = round(min(d, c["fin"] - ver["en"] - ver["dur"]), 3)
            if d >= 0.7:
                en = round(c["fin"] - d, 3)
                c["efectos"].append({"efecto": "pero_espera", "en": en, "dur": d})
                sfx_fn(sfx, "subida_tension", en - 0.4, tira_ultimo - 1, "Subida antes del último nivel",
                       termina_en=c["fin"])
                sfx_fn(sfx, "tic_tac", en, tira_ultimo - 1, "Tic-tac: falta el último")

    # --- llamados a la acción
    def _hueco(desde: float, minimo: float) -> int | None:
        for i, c in enumerate(clips):
            if c["inicio"] >= desde and _libre(c) and c["fin"] - c["inicio"] >= minimo and nivel[i] is not None \
                    and not any(x["efecto"] in ("veredicto", "pero_espera", "dato") for x in c["efectos"]):
                return i
        return None

    if total > LIKE_S + 30:
        i = _hueco(LIKE_S, 2.4)
        if i is not None:
            c = clips[i]
            pose = poses.get("senalando_sorpresa") or next(iter(poses.values()), None)
            c["efectos"].append({"efecto": "cta_like", "en": round(c["inicio"] + 0.2, 3),
                                 "dur": round(min(2.6, c["fin"] - c["inicio"] - 0.3), 3), "pose": pose,
                                 "texto": "¿Te gusta? Dale like"})
            sfx_fn(sfx, "boing", c["inicio"] + 0.35, i, "Boing: la mascota salta con el like")
    if total > SUSCRIBIR_S + 30:
        i = _hueco(SUSCRIBIR_S, 2.0)
        if i is not None:
            c = clips[i]
            c["efectos"].append({"efecto": "cta_suscribir", "en": round(c["inicio"] + 0.2, 3),
                                 "dur": round(min(3.0, c["fin"] - c["inicio"] - 0.2), 3)})
            sfx_fn(sfx, "pop", c["inicio"] + 0.3, i, "Pop: botón de suscribirse (sin parar el video)")

    # --- cierre: carrusel de la tira y la mascota al centro sobre fondo oscuro
    cierre = [i for i, k in enumerate(nivel) if k is None and _libre(clips[i])]
    if cierre and esc.niveles:
        # el carrusel va en la primera escena del cierre que dure lo suficiente (no en la última)
        i0 = next((i for i in cierre[:-1] if clips[i]["fin"] - clips[i]["inicio"] >= 1.8), cierre[0])
        c = clips[i0]
        if c["fin"] - c["inicio"] >= 1.8:
            c["modo"], c["archivo"] = "tira", "assets/tira/tira_niveles.png"
            c["movimiento"] = None
            c["efectos"] = [{"efecto": "tira_deslizar_a_nivel", "pasar": True, "villano_pixelado": False}]
            textos[:] = [t for t in textos if not (c["inicio"] <= t["inicio"] < c["fin"])]
            sfx[:] = [x for x in sfx if x["clip"] != i0]
            sfx_fn(sfx, "subida_tension", c["inicio"], i0, "Subida: pasan todas las tarjetas del video",
                   termina_en=c["fin"])
        i1 = cierre[-1]
        if i1 != i0 and poses:
            c = clips[i1]
            pose = poses.get("senalando_sorpresa") or next(iter(poses.values()))
            c["efectos"] = [x for x in c["efectos"] if x["efecto"] in ("destello_blanco",)]
            c["efectos"].append({"efecto": "final_personaje", "en": c["inicio"], "dur": round(c["fin"] - c["inicio"], 3),
                                 "pose": pose})
            textos[:] = [t for t in textos if not (c["inicio"] <= t["inicio"] < c["fin"])]

    # --- subtítulos de 1 a 3 palabras con la palabra activa
    from .edicion import trozos_subtitulo

    nuevos = []
    for e in escenas:
        a, b = e.tiempo.real_inicio, e.tiempo.real_fin
        trozos = trozos_subtitulo(e.narracion, maximo=3)
        largo = sum(len(x) for x in trozos) or 1
        acum = 0
        for tr in trozos:
            t0 = a + (b - a) * acum / largo
            acum += len(tr)
            t1 = max(a + (b - a) * acum / largo, t0 + 0.2)
            nuevos.append({"inicio": round(t0, 3), "fin": round(t1, 3), "texto": tr, "escena": e.id,
                           "palabras": palabras_con_tiempo(tr, t0, t1)})
    subtitulos[:] = nuevos
