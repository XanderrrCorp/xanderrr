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
import re
import unicodedata

LIKE_S = 100.0
SUSCRIBIR_S = 180.0

# (23-10) «más dopamina»: cada cuánto puede saltar una palabra grande y cuánto dura en pantalla
CADA_PALABRA_S = 4.5
# (24-10, el dueño: «que de vez en cuando salgan más flechas rodeando la imagen») una vez cada ~15 s como máximo
CADA_FLECHAS_S = 15.0
DUR_PALABRA_S = 1.0
_NUMEROS = (r"cero|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|"
            r"dieci\w+|veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|"
            r"\w*cientos|miles|\w+cientas|mil|millon|millones|medio|media|doble|triple")
_UNIDADES = ("kilos?|kilogramos?|gramos?|toneladas?|metros?|centimetros?|kilometros?|litros?|anos|dias|horas|"
             "minutos|segundos|grados|veces|dientes|patas|ojos|especies|personas|ataques|por ciento|kilometros por hora")
CIFRA = re.compile(rf"\b((?:(?:{_NUMEROS})\b(?:\s+(?:y|de)\s+)?\s*)+(?:{_UNIDADES})\b)", re.I)
TEXTOS_SUBE = ("SUBE EL PELIGRO", "MÁS PELIGROSO", "ESTO SE PONE SERIO", "CUIDADO AQUÍ")


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
            valor_de, poses: dict, rng: random.Random, total: float, dopamina: bool = False,
            veredictos: bool = True) -> None:
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
    for k in niveles if veredictos else ():
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
                    and not any(x["efecto"] in ("veredicto", "pero_espera", "dato", "comentario") for x in c["efectos"]):
                return i
        return None

    # (24-10) con la v2 el like va donde la VOZ lo pide (la pausa en el momento de más intriga), no a un minuto fijo
    pide_like = next((k for k, e in enumerate(escenas) if dopamina and re.search(r"(?i)\blike\b", e.narracion)
                      and _libre(clips[k]) and clips[k]["fin"] - clips[k]["inicio"] >= 2.0
                      and not any(x["efecto"] in ("veredicto", "pero_espera", "dato", "comentario")
                                  for x in clips[k]["efectos"])), None)
    if pide_like is not None:
        c = clips[pide_like]
        pose = poses.get("senalando_sorpresa") or next(iter(poses.values()), None)
        c["efectos"].append({"efecto": "cta_like", "en": round(c["inicio"] + 0.2, 3),
                             "dur": round(min(2.6, c["fin"] - c["inicio"] - 0.3), 3), "pose": pose,
                             "texto": "¿Te gusta? Dale like"})
        sfx_fn(sfx, "boing", c["inicio"] + 0.35, pide_like, "Boing: la mascota salta con el like (la voz lo pide)")
    elif total > LIKE_S + 30:
        i = _hueco(LIKE_S, 2.4)
        if i is not None:
            c = clips[i]
            pose = poses.get("senalando_sorpresa") or next(iter(poses.values()), None)
            c["efectos"].append({"efecto": "cta_like", "en": round(c["inicio"] + 0.2, 3),
                                 "dur": round(min(2.6, c["fin"] - c["inicio"] - 0.3), 3), "pose": pose,
                                 "texto": "¿Te gusta? Dale like"})
            sfx_fn(sfx, "boing", c["inicio"] + 0.35, i, "Boing: la mascota salta con el like")
    if pide_like is not None or total > SUSCRIBIR_S + 30:
        # con la v2 el botón de suscribirse sale justo después del like (la voz pide las dos cosas juntas)
        i = _hueco(clips[pide_like]["fin"] - 0.01, 1.6) if pide_like is not None else _hueco(SUSCRIBIR_S, 2.0)
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

    if dopamina:
        aplicar_dopamina(clips, escenas, sfx, sfx_fn, nivel, n_niv, rng, textos)

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
    if dopamina:
        # mientras salta la palabra grande o la cinta de «sube el peligro» no se repite el subtítulo debajo
        ventanas = [(x["en"], x["en"] + x["dur"]) for c in clips for x in c["efectos"]
                    if x["efecto"] in ("palabra_golpe", "sube_nivel")]
        def tapado(s: dict) -> bool:
            return any(min(s["fin"], b) - max(s["inicio"], a) > min(0.3, 0.5 * (s["fin"] - s["inicio"]))
                       for a, b in ventanas)

        nuevos = [s for s in nuevos if not tapado(s)]
    subtitulos[:] = nuevos


# ------------------------------------------------------------------ (23-10) más dopamina

def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def palabra_fuerte(narracion: str, palabra_clave: str | None, intencion: str) -> tuple[str, float] | None:
    """La palabra (o frase corta) que salta en grande y en qué parte de la frase se dice (0 a 1):
    1) una cifra con su unidad («ochenta kilos»); 2) una frase de golpe de 1 a 3 palabras («Cero.», «Nada.»);
    3) la palabra clave en una revelación, amenaza o dato fuerte. Si no hay nada fuerte, None."""
    plano = _sin_tildes(narracion)
    m = CIFRA.search(plano)
    if m and len(m.group(1).split()) <= 4:
        a, b = m.span(1)
        return narracion[a:b].strip().upper(), a / max(1, len(narracion))
    palabras = narracion.split()
    if 1 <= len(palabras) <= 3 and narracion.rstrip()[-1:] in ".!":
        return narracion.strip().rstrip(".!").upper(), 0.0
    if palabra_clave and intencion in ("revelacion", "amenaza", "dato_impactante", "giro", "advertencia"):
        i = plano.lower().find(_sin_tildes(palabra_clave).lower())
        if i >= 0:
            return palabra_clave.upper(), i / max(1, len(narracion))
    return None


_OCUPADO = ("veredicto", "pero_espera", "cta_like", "cta_suscribir", "comentario", "final_personaje", "dato",
            "etiqueta")


def aplicar_dopamina(clips: list, escenas: list, sfx: list, sfx_fn, nivel: list, n_niv: int,
                     rng: random.Random, textos: list | None = None) -> None:
    """Encima de la receta: palabra grande que salta, golpe con zoom en los remates y «sube el peligro» al pasar de un
    animal al siguiente. Todo por código: no hay imágenes nuevas ni costo extra."""
    ultima = -99.0
    for idx, (c, e) in enumerate(zip(clips, escenas)):
        if not _libre(c) or nivel[idx] is None:
            continue
        if any(x["efecto"] in _OCUPADO for x in c["efectos"]):
            continue
        fuerte = palabra_fuerte(e.narracion, e.palabra_clave, e.intencion)
        if not fuerte:
            continue
        texto, donde = fuerte
        a, b = e.tiempo.real_inicio, e.tiempo.real_fin
        en = round(max(c["inicio"], a + (b - a) * donde - 0.05), 3)
        dur = round(min(DUR_PALABRA_S, c["fin"] - en - 0.05), 3)
        if dur < 0.6 or en - ultima < CADA_PALABRA_S or len(texto) > 26:
            continue
        # (24-10, el dueño: que no tape la imagen) va arriba: si ahí ya hay un título en ese momento, no sale
        if any(t["inicio"] < en + dur and en < t["fin"] for t in (textos or [])):
            continue
        ultima = en
        corta = len(e.narracion.split()) <= 3
        c["efectos"].append({"efecto": "palabra_golpe", "en": en, "dur": dur, "texto": texto,
                             "cifra": bool(CIFRA.search(_sin_tildes(e.narracion))), "giro": round(rng.uniform(-5, 5), 1)})
        if corta or e.intencion in ("revelacion", "giro", "dato_impactante"):
            # remate: golpe con zoom y una sacudida corta
            c["efectos"].append({"efecto": "golpe", "en": en, "dur": 0.35})
            sfx_fn(sfx, "golpe_grave", en, idx, f"Golpe: remate «{texto}»")
        else:
            sfx_fn(sfx, "pop", en, idx, f"Pop: salta en grande «{texto}»")
    # flechas que rodean la imagen, de vez en cuando (en las escenas con más fuerza primero)
    ultima_f = -99.0
    for idx, (c, e) in enumerate(zip(clips, escenas)):
        dur = c["fin"] - c["inicio"]
        if not _libre(c) or nivel[idx] is None or dur < 2.0 or c["inicio"] - ultima_f < CADA_FLECHAS_S:
            continue
        if any(x["efecto"] in ("flecha", "lupa", "circulo_rojo", "palabra_golpe", "escala_peligro", "presentacion_especie",
                               "palabra_completa", "capitulo") + _OCUPADO for x in c["efectos"]):
            continue
        fuerte = e.intencion in ("amenaza", "revelacion", "dato_impactante", "advertencia", "giro", "explicacion")
        if not fuerte and rng.random() < 0.5:
            continue
        ultima_f = c["inicio"]
        base = rng.choice([(200, -20, 250), (160, 20, 290), (210, -30, 90), (180, 300, 0)])
        en = round(c["inicio"] + min(0.5, dur * 0.2), 3)
        c["efectos"].append({"efecto": "flechas_alrededor", "en": en, "angulos": list(base),
                             "caja": [0.3, 0.22, 0.7, 0.78]})
        for k in range(len(base)):
            sfx_fn(sfx, "pop", en + 0.14 * k, idx, "Pop: entra una flecha que rodea la imagen")
    # sube el peligro: al pasar al siguiente animal (no en el primero ni al repasar la tira del cierre)
    vistos = 0
    for idx, c in enumerate(clips):
        t = next((x for x in c["efectos"] if x["efecto"] == "tira_deslizar_a_nivel" and not x.get("pasar")), None)
        if not t:
            continue
        k = int(t["hasta"])
        if k <= 1 or c["fin"] - c["inicio"] < 1.2:
            continue
        ultimo = n_niv and k == n_niv
        texto = "EL ÚLTIMO DE LA LISTA" if ultimo else TEXTOS_SUBE[vistos % len(TEXTOS_SUBE)]
        vistos += 0 if ultimo else 1
        en = round(c["inicio"] + 0.15, 3)
        c["efectos"].append({"efecto": "sube_nivel", "en": en, "dur": round(min(1.3, c["fin"] - en - 0.05), 3),
                             "texto": texto, "alto": bool(n_niv and k > n_niv / 2)})
        sfx_fn(sfx, "barrido", en, idx, f"Swoosh: {texto.lower()}")
