"""Director de edición por reglas (sección 4, 14 y 15) → edl.json.

La EDL es la única fuente de verdad del render. Aquí se decide, con reglas
deterministas (semilla del proyecto) y las decisiones puntuales del director en
`direccion.json` (zonas a pixelar del villano, textos en pantalla):

- cada corte entra 3 fotogramas ANTES de la primera palabra de la escena (14.3)
- movimiento según la intención (gramática del estilo), con curva suave, punto
  de foco y porcentaje variados; algunas escenas quietas para dar contraste (14.4)
- zoom_golpe solo en giros/advertencias y nunca en dos escenas seguidas
- ninguna imagen más de 4,5 s sin cambio visual: se reencuadra a mitad (4.3)
- la tira de niveles en cada transición a un nivel (15.3) y el villano siempre
  pixelado hasta su revelación (15.4)
- subtítulos de 1 a 4 palabras sin dejar artículos o preposiciones colgando (14.9)
- sonido con intención (4.2, 14.7): barrido en cambios de sección y transiciones de
  la tira, golpe grave en giros y revelación, pop solo cuando entra un dato clave
  (texto o círculo), latidos solo en las ráfagas de tension_creciente; variantes sin
  repetir, tono y volumen variados, y recortado por uso_maximo_por_recurso,
  sfx_por_minuto y el detector de periodicidad (14.10)
- foco: cuando la voz nombra a un animal que se ve, el resto se oscurece y se
  encierra en un círculo rojo; de vez en cuando una flecha señala un detalle
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from .config import escribir_json, leer_json
from .esquemas import EDL, EscenasV2, Estilo
from .estilos import cargar_gramatica, cargar_perfil_edicion
from .proyecto import CarpetaProyecto

FPS = 30
ADELANTO = 3 / FPS
MAX_SIN_CAMBIO = 4.5
# prioridad al recortar efectos de sonido por frecuencia: se quitan primero los bajos
PRIORIDAD = {"golpe_grave": 6, "stinger_terror": 6, "subida_tension": 5, "piano_miedo": 5, "ruleta": 5, "barrido": 4,
             "alerta": 3, "pop": 3, "comico": 3, "zumbido": 2, "latido": 2}
VOLUMEN = {"barrido": 0.42, "golpe_grave": 0.9, "pop": 0.32, "zumbido": 0.33, "latido": 0.55,
           "subida_tension": 0.45, "alerta": 0.4, "comico": 0.45, "stinger_terror": 0.75, "piano_miedo": 0.6,
           "ruleta": 0.5}
VARIANTES = 4
# recursos estructurales (tira, pixelado) que no cuentan para uso_maximo_por_recurso
ESTRUCTURALES = {"tira_deslizar_a_nivel", "pixelar", "revelar_pixelado", "destello_rojo", "paneo_lento", "zoom_golpe",
                 "vaiven"}
DEBILES = {"el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "a", "al", "y", "o", "en", "que",
           "por", "con", "se", "te", "tu", "su", "sus", "lo", "le", "no", "es", "más", "muy", "mi", "para", "ni"}


def trozos_subtitulo(texto: str, maximo: int = 4) -> list[str]:
    """Bloques de 1 a `maximo` palabras cortados en pausas naturales; un bloque
    nunca termina en artículo, preposición o conjunción (esas pasan al siguiente)."""
    def debil(p: str) -> bool:
        return re.sub(r"[^\wáéíóúñü]", "", p.lower()) in DEBILES and not p.endswith((",", ".", "?", "!", ":", ";", "…"))

    palabras = texto.split()
    trozos, actual = [], []
    for p in palabras:
        actual.append(p)
        if p.endswith((",", ".", "?", "!", ":", ";", "…")):
            trozos.append(" ".join(actual))
            actual = []
        elif len(actual) >= maximo:
            corte = len(actual)
            while corte > 1 and debil(actual[corte - 1]):
                corte -= 1
            if corte == 1 and debil(actual[0]):
                continue                       # todo débil: se sigue acumulando
            trozos.append(" ".join(actual[:corte]))
            actual = actual[corte:]
    if actual:
        trozos.append(" ".join(actual))
    return trozos


def _en_texto(narracion: str, palabra: str, ini: float, fin: float) -> float:
    i = narracion.lower().find(palabra.lower())
    if i < 0:
        return ini
    return ini + (fin - ini) * i / max(1, len(narracion))


def _sfx(lista: list, tipo: str, inicio: float, clip: int, razon: str, termina_en: float | None = None,
         duracion_max: float | None = None) -> None:
    lista.append({"tipo": tipo, "inicio": max(0.0, inicio), "clip": clip, "razon": razon,
                  "prioridad": PRIORIDAD.get(tipo, 1), "termina_en": termina_en, "duracion_max": duracion_max})


PERFIL_SHORT = "perfiles/short_vertical.json"
# en el short casi cada corte suena: el tipo sale de la intención de la frase
SONIDO_DE_CORTE = {
    "gancho": ("golpe_grave", "stinger_terror"), "revelacion": ("golpe_grave", "stinger_terror"),
    "giro": ("stinger_terror", "golpe_grave"), "dato_impactante": ("golpe_grave", "pop"),
    "amenaza": ("zumbido", "subida_tension"), "tension_creciente": ("subida_tension", "latido"),
    "advertencia": ("alerta", "zumbido"), "pregunta_al_espectador": ("comico", "pop"),
    "humor": ("comico", "pop"), "cierre": ("piano_miedo", "golpe_grave"),
}


def _sonido_en_cada_corte(sfx: list, escenas: list, clips: list, rng: random.Random) -> None:
    """A cada escena que quedó muda se le propone un sonido en el corte, alternando para que
    nunca suene el mismo tipo dos cortes seguidos. Tienen la prioridad más baja: el recorte
    por sfx_por_minuto del perfil decide cuántos quedan (muchos en el short, menos en el largo)."""
    con_sonido = {x["clip"] for x in sfx}
    previo = None
    for idx, (e, c) in enumerate(zip(escenas, clips)):
        tipos_aqui = {x["tipo"] for x in sfx if x["clip"] == idx}
        if idx in con_sonido:
            previo = next(iter(tipos_aqui))
            continue
        anterior = escenas[idx - 1].narracion.strip() if idx else ""
        if anterior.endswith("?") and len(e.narracion.split()) <= 4:
            # «¿Cuántos ataques tiene?» «Cero.»: la respuesta seca cae con un golpe
            _sfx(sfx, "golpe_grave", c["inicio"] + 0.05, idx, "Golpe con la respuesta seca a la pregunta")
            previo = "golpe_grave"
            continue
        opciones = list(SONIDO_DE_CORTE.get(e.intencion, ("barrido", "pop")))
        opciones += ["barrido", "pop"]
        tipo = next((t for t in opciones if t != previo), "barrido")
        _sfx(sfx, tipo, c["inicio"] + rng.uniform(0.0, 0.08), idx,
             f"Sonido en el corte ({tipo}) para que el ritmo no se caiga")
        sfx[-1]["prioridad"] = 0
        previo = tipo


def _recortar_sonidos(sfx: list, n_clips: int, total: float, perfil, rng: random.Random) -> list:
    """Sonido con intención, no en cada corte (14.7, 14.10):
    - nunca el mismo tipo en dos escenas seguidas
    - ningún tipo en más de uso_maximo_por_recurso de las escenas
    - no más de sfx_por_minuto (con holgura del 25 %)
    - sin periodicidad: 4 o más del mismo tipo a intervalos casi iguales se rompen
    Se quitan primero los de menor prioridad y, entre iguales, los más tardíos."""
    vivos = sorted(sfx, key=lambda x: x["inicio"])
    # un mismo sonido una sola vez por escena (los latidos de una ráfaga sí van juntos)
    vistos: set = set()
    unicos = []
    for x in sorted(vivos, key=lambda x: (-x["prioridad"], x["inicio"])):
        clave = (x["tipo"], x["clip"])
        if x["tipo"] != "latido" and clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(x)
    vivos = sorted(unicos, key=lambda x: x["inicio"])

    def quitar(cand):
        cand.sort(key=lambda x: (x["prioridad"], -x["inicio"]))
        vivos.remove(cand[0])

    # mismo tipo en escenas consecutivas (una serie de latidos en un mismo clip cuenta como una)
    cambio = True
    while cambio:
        cambio = False
        por_tipo: dict = {}
        for x in vivos:
            por_tipo.setdefault(x["tipo"], set()).add(x["clip"])
        for x in list(vivos):
            if x["clip"] - 1 in por_tipo.get(x["tipo"], ()) and x["prioridad"] < 5:
                vivos.remove(x)
                cambio = True
                break
    tope = max(1, int(perfil.uso_maximo_por_recurso * n_clips))
    for tipo in {x["tipo"] for x in vivos}:
        while len({x["clip"] for x in vivos if x["tipo"] == tipo}) > tope:
            clips = {}
            for x in vivos:
                if x["tipo"] == tipo:
                    clips.setdefault(x["clip"], []).append(x)
            peor = min(clips.values(), key=lambda g: (g[0]["prioridad"], -g[0]["inicio"]))
            for x in peor:
                vivos.remove(x)
    maximo = perfil.sfx_por_minuto * total / 60 * 1.15
    eventos = lambda: len({(x["tipo"], x["clip"]) for x in vivos})
    while eventos() > maximo:
        quitables = [x for x in vivos if x["prioridad"] < 5]
        if not quitables:
            break
        quitar(quitables)
    for tipo in {x["tipo"] for x in vivos}:
        ts = [x for x in vivos if x["tipo"] == tipo and x["prioridad"] < 5]
        for k in range(len(ts) - 3):
            gaps = [ts[k + j + 1]["inicio"] - ts[k + j]["inicio"] for j in range(3)]
            media = sum(gaps) / 3
            if media > 0 and (max(gaps) - min(gaps)) / media < 0.12 and ts[k + 1] in vivos:
                vivos.remove(ts[k + 1])           # rompe la periodicidad
    return vivos


def _pistas_sfx(vivos: list, rng: random.Random) -> list:
    """14.7: variante de un grupo sin repetir dos veces seguidas, tono ±5 % y volumen variado."""
    pistas, ultima = [], {}
    for k, s in enumerate(sorted(vivos, key=lambda x: x["inicio"])):
        variante = rng.choice([x for x in range(1, VARIANTES + 1) if x != ultima.get(s["tipo"])])
        ultima[s["tipo"]] = variante
        pista = {"id": f"s{k:03d}", "inicio": round(s["inicio"], 3), "tipo": s["tipo"],
                 "archivo": f"biblioteca/sfx/{s['tipo']}", "variante": f"{s['tipo']}_{variante}",
                 "tono": round(rng.uniform(0.955, 1.045), 3),
                 "volumen": round(min(1.0, VOLUMEN.get(s["tipo"], 0.5) * rng.uniform(0.85, 1.1)), 3),
                 "razon": s["razon"]}
        if s.get("termina_en") is not None:
            pista["termina_en"] = round(s["termina_en"], 3)
        if s.get("duracion_max"):
            pista["duracion_max"] = s["duracion_max"]
        pistas.append(pista)
    return pistas


def _mov(tipo: str | None, rng: random.Random, maximo: float) -> tuple[dict | None, list]:
    foco = [round(rng.uniform(0.42, 0.58), 3), round(rng.uniform(0.40, 0.54), 3)]
    amp = round(rng.uniform(0.025, maximo), 3)
    if tipo == "zoom_lento":
        return {"tipo": "zoom_lento", "de": 1.0, "a": round(1 + amp, 3), "punto_foco": foco}, []
    if tipo == "alejamiento_lento":
        return {"tipo": "alejamiento_lento", "de": round(1 + amp, 3), "a": 1.0, "punto_foco": foco}, []
    if tipo == "paneo_lento":
        d = rng.choice([-1, 1])
        return ({"tipo": "paneo_lento", "de": 1.06, "a": 1.06, "punto_foco": [round(0.5 - 0.03 * d, 3), foco[1]]},
                [{"efecto": "paneo_lento", "hasta": [round(0.5 + 0.03 * d, 3), foco[1]]}])
    if tipo == "entrada_rebote":
        return {"tipo": "entrada_rebote", "de": 1.045, "a": 1.0, "curva": "ease_out", "punto_foco": foco}, []
    return None, []


def _equilibrar_movimientos(clips: list, perfil, rng: random.Random, maximo: float) -> None:
    """14.10: ningún movimiento en más de uso_maximo_por_recurso de las escenas y
    nunca el mismo movimiento tres veces seguidas. Se cambian los movimientos de
    relleno por el alternativo menos usado; zoom_golpe y ráfagas no se tocan."""
    exentos = set(perfil.recursos_exentos_de_uso_maximo) | {"zoom_golpe"}
    alternativos = ["zoom_lento", "alejamiento_lento", "paneo_lento", None]
    movibles = [c for c in clips if c["modo"] != "tira" and not any(e["efecto"] == "rafaga" for e in c["efectos"])
                and (c["movimiento"] or {}).get("tipo") not in exentos]
    tope = max(1, int(perfil.uso_maximo_por_recurso * len(clips)))

    def tipo(c):
        return (c["movimiento"] or {}).get("tipo")

    def cambiar(c, nuevo):
        c["efectos"] = [e for e in c["efectos"] if e["efecto"] != "paneo_lento"]
        mov, ef = _mov(nuevo, rng, maximo)
        c["movimiento"] = mov
        c["efectos"] += ef
        c["razon"] += f"; movimiento cambiado a {nuevo or 'quieto'} para no repetir el mismo recurso (14.10)"

    def uso(t):
        return sum(1 for c in clips if tipo(c) == t)

    for t in ("zoom_lento", "alejamiento_lento", "paneo_lento", "entrada_rebote"):
        exceso = [c for c in movibles if tipo(c) == t]
        rng.shuffle(exceso)
        while uso(t) > tope and exceso:
            c = exceso.pop()
            destino = min((a for a in alternativos if a != t), key=lambda a: uso(a) if a else tope - 1)
            cambiar(c, destino)
    for a, b, c in zip(clips, clips[1:], clips[2:]):
        if tipo(a) and tipo(a) == tipo(b) == tipo(c) and c in movibles:
            cambiar(c, next(x for x in alternativos if x != tipo(c)))
        tr = a["transicion_entrada"]
        if tr not in exentos and tr == b["transicion_entrada"] == c["transicion_entrada"]:
            c["transicion_entrada"] = "corte"
            c["razon"] += "; corte en vez de otro fundido para no repetir la transición tres veces (14.10)"


# estado de ánimo alternativo si la biblioteca no tiene el pedido
CERCANOS = {"tension": ["misterio", "epico"], "misterio": ["tension", "curiosidad"], "epico": ["tension", "final"],
            "alivio": ["curiosidad", "final"], "curiosidad": ["misterio", "alivio"], "final": ["alivio", "epico"]}


def _animo_de_seccion(escenas: list, k: int, n: int) -> str:
    intenciones = [e.intencion for e in escenas]
    media = sum(e.intensidad for e in escenas) / len(escenas)
    if k == 0:
        return "misterio"
    if k == n - 1 and ("cierre" in intenciones or "llamado_accion" in intenciones):
        return "final"
    if "revelacion" in intenciones:
        return "epico"
    if intenciones.count("alivio") * 2 >= len(intenciones):
        return "alivio"
    return "tension" if media >= 3.2 or "tension_creciente" in intenciones else "curiosidad"


ASCO = ("asco", "sucio", "sucia", "basura", "excremento", "heces", "caca", "vómito", "vomita", "podrido", "coladera")


def _stock(esc: EscenasV2, escenas: list, clips: list, raiz: Path, revelacion: int | None, rng: random.Random,
           sfx: list, maximo: int = 6, separacion: float = 30.0) -> int:
    """De vez en cuando (no siempre), cuando la voz nombra a un animal que tiene fotos o
    videos reales VERIFICADOS, se muestra lo real: la foto en un marco rojo con la mascota
    señalándola, o el video a pantalla completa. Una vez por animal, separadas y sin pisar
    el círculo, la lupa ni al presentador. El villano, solo después de su revelación."""
    from .foco import claves_de_nombre, palabra_en

    ruta = raiz / "assets" / "stock" / "stock.json"
    if not ruta.exists():
        return 0
    aprobados = [a for a in leer_json(ruta)["archivos"] if a.get("verificado") and (raiz / a["archivo"]).exists()]
    if not aprobados:
        return 0
    niveles = [n.model_dump() for n in esc.niveles]
    claves = claves_de_nombre(niveles)
    villano = next((n.numero for n in esc.niveles if n.villano), None)
    poses = {p.stem: p for p in (raiz / "assets" / "poses").glob("*.png")}
    usados_nivel: set = set()
    tiempos: list[float] = []
    ultimo_tipo = rng.choice(["foto", "video"])
    for i, (e, c) in enumerate(zip(escenas, clips)):
        if len(tiempos) >= maximo or c["modo"] == "tira":
            continue
        if any(x["efecto"] in ("circulo_rojo", "lupa", "flecha", "pixelar", "rafaga", "reaccion_presentador")
               for x in c["efectos"]):
            continue
        for n in esc.niveles:
            if n.numero in usados_nivel or n.numero not in claves:
                continue
            if n.numero == villano and (revelacion is None or e.id <= revelacion):
                continue
            palabra = palabra_en(e.narracion, claves[n.numero])
            if not palabra:
                continue
            t0 = _en_texto(e.narracion, palabra, e.tiempo.real_inicio, e.tiempo.real_fin)
            t0 = max(c["inicio"] + 0.1, t0 - 0.1)
            dur = min(c["fin"] - t0, 3.2)
            if dur < 1.8 or any(abs(t0 - t) < separacion for t in tiempos):
                continue
            propios = [a for a in aprobados if a["nivel"] == n.numero]
            tipo = "foto" if ultimo_tipo == "video" else "video"
            elegido = next((a for a in propios if a["tipo"] == tipo), None) or (propios[0] if propios else None)
            if not elegido:
                continue
            if elegido["tipo"] == "video":
                c["efectos"].append({"efecto": "video_real", "en": round(t0, 3), "dur": round(dur, 3),
                                     "archivo": elegido["archivo"], "desde": round(rng.uniform(0.3, 1.5), 2),
                                     "origen": elegido["url_origen"]})
                c["razon"] += f"; video REAL de {n.nombre} (verificado) al nombrarlo"
            else:
                clave = "senalando_asco" if any(w in e.narracion.lower() for w in ASCO) else \
                    "senalando_susto" if e.intencion in ("amenaza", "advertencia", "tension_creciente", "revelacion") \
                    else "senalando_sorpresa"
                pose = poses.get(clave) or next(iter(poses.values()), None)
                c["efectos"].append({"efecto": "foto_real", "en": round(t0, 3), "dur": round(dur, 3),
                                     "archivo": elegido["archivo"], "origen": elegido["url_origen"],
                                     "sintetica": bool(elegido.get("sintetica")),
                                     "pose": pose.relative_to(raiz).as_posix() if pose else None})
                c["razon"] += f"; foto REAL de {n.nombre} (verificada) con la mascota señalándola"
            _sfx(sfx, "pop", t0, i, f"Pop al mostrar a {n.nombre} de verdad")
            ultimo_tipo = elegido["tipo"]
            usados_nivel.add(n.numero)
            tiempos.append(t0)
            break
    return len(tiempos)


def _reacciones(estilo: Estilo, escenas: list, clips: list, raiz: Path, revelacion: int | None,
                rng: random.Random, elegidas: list | None = None, sfx: list | None = None) -> int:
    """Cortes de ~2 s al presentador reaccionando (la voz sigue). Solo en las intenciones
    que el estilo manda, con prioridad en su orden (revelación, giro, humor…), separados
    por separacion_minima_seg, nunca en escenas seguidas y como máximo maximo_por_video."""
    pr = estilo.presentador
    if pr is None or not pr.reacciones or pr.maximo_por_video == 0:
        return 0
    disponibles = {pose for pose in set(pr.reacciones.values()) if (raiz / "assets" / "presentador" / f"{pose}.mp4").exists()}
    if not disponibles:
        return 0
    orden = list(pr.reacciones)
    d = pr.duracion_reaccion_seg
    candidatos = []
    if elegidas:
        # Claude eligió los momentos leyendo el guion: la reacción entra justo DESPUÉS de que
        # la frase cae (al empezar la escena siguiente) o, si no cabe, al final de la misma
        por_id = {e.id: k for k, e in enumerate(escenas)}
        for prioridad, r in enumerate(elegidas):
            k = por_id.get(r["escena"])
            if k is None or r["pose"] not in disponibles:
                continue
            opciones = []
            if k + 1 < len(clips) and clips[k + 1]["modo"] != "tira":
                opciones.append((k + 1, clips[k + 1]["inicio"] + 0.08))
            if revelacion and escenas[k].id == revelacion:
                opciones.insert(0, (k, clips[k]["inicio"] + 1.5))
            opciones.append((k, clips[k]["fin"] - d - 0.15))
            for i, t0 in opciones:
                if any(x["efecto"] in ("foto_real", "video_real") for x in clips[i]["efectos"]):
                    continue
                if t0 >= clips[i]["inicio"] + 0.05 and clips[i]["fin"] - t0 >= d + 0.1:
                    candidatos.append((prioridad, 0.0, i, t0, r["pose"], r.get("razon", "")))
                    break
    for i, (e, c) in enumerate(zip(escenas, clips)):
        if elegidas:
            break
        pose = pr.reacciones.get(e.intencion)
        if pose not in disponibles or any(x["efecto"] in ("foto_real", "video_real") for x in c["efectos"]):
            continue
        # en la revelación, justo después de que se despixela el villano; en las demás, al empezar
        t0 = c["inicio"] + (1.5 if (revelacion and e.id == revelacion) else rng.uniform(0.25, 0.5))
        if c["fin"] - t0 < d + 0.3:
            continue
        candidatos.append((orden.index(e.intencion), rng.random(), i, t0, pose, ""))
    elegidos: list[tuple[int, float, str]] = []
    for _, _, i, t0, pose, por_que in sorted(candidatos):
        if len(elegidos) >= pr.maximo_por_video:
            break
        if any(abs(t0 - t) < pr.separacion_minima_seg or abs(i - j) <= 1 for j, t, _ in elegidos):
            continue
        if sum(1 for *_, p in elegidos if p == pose) >= pr.maximo_por_pose:
            continue
        vecinos = sorted(elegidos + [(i, t0, pose)], key=lambda x: x[1])
        k = next(n for n, x in enumerate(vecinos) if x[0] == i)
        if any(0 <= n < len(vecinos) and n != k and vecinos[n][2] == pose for n in (k - 1, k + 1)):
            continue                                    # nunca la misma reacción dos veces seguidas
        elegidos.append((i, t0, pose))
        c = clips[i]
        pregunta = pose == "pensativo" or "?" in escenas[i].narracion or (i and "?" in escenas[i - 1].narracion)
        c["efectos"].append({"efecto": "reaccion_presentador", "en": round(t0, 3), "dur": d,
                             "archivo": f"assets/presentador/{pose}.mp4", "desde": round(rng.uniform(0.3, 1.2), 2),
                             "pose": pose, "globo": bool(pregunta)})
        c["razon"] += f"; corte de {d:.0f} s al presentador reaccionando ({pose})" + (f": {por_que}" if por_que else "")
        sonido = pr.sonidos.get(pose)
        if sonido and sfx is not None:
            _sfx(sfx, sonido, t0 + 0.05, i, f"{sonido.replace('_', ' ')} con la reacción de {pose}")
    return len(elegidos)


def _musica(escenas: list, clips: list, revelacion: int | None, total: float, rng: random.Random) -> list:
    """Una pista por sección según su ánimo, sin repetir la misma pista seguida. Los
    cambios empiezan un poco antes del corte (J) y terminan un poco después (L) (14.5).
    Sin música registrada con licencia, el video va sin música."""
    from . import biblioteca

    disponibles = {a: [p.relative_to(biblioteca.raiz()).as_posix() for p in biblioteca.utilizables("musica", a)]
                   for a in biblioteca.ANIMOS_MUSICA}
    if not any(disponibles.values()):
        return []
    secciones: list[list] = []
    for e, c in zip(escenas, clips):
        if not secciones or secciones[-1][0][0].seccion != e.seccion:
            secciones.append([])
        secciones[-1].append((e, c))
    caida = None
    if revelacion:
        c_rev = next((c for e, c in zip(escenas, clips) if e.id == revelacion), None)
        if c_rev:
            caida = (round(c_rev["inicio"] + 0.55 - rng.uniform(0.3, 0.8), 3), round(c_rev["inicio"] + 0.55, 3))
    salida, ultima = [], None
    for k, sec in enumerate(secciones):
        animo = _animo_de_seccion([e for e, _ in sec], k, len(secciones))
        elegido = animo if disponibles[animo] else next((a for a in CERCANOS[animo] if disponibles[a]), None) \
            or next(a for a in biblioteca.ANIMOS_MUSICA if disponibles[a])
        opciones = [p for p in disponibles[elegido] if p != ultima] or disponibles[elegido]
        pista = rng.choice(opciones)
        ultima = pista
        ini = max(0.0, sec[0][1]["inicio"] - (0.4 if k else 0))
        fin = min(total, sec[-1][1]["fin"] + (0.6 if k < len(secciones) - 1 else 0))
        clip = {"id": f"m{k:02d}", "inicio": round(ini, 3), "fin": round(fin, 3), "archivo": pista,
                "volumen": 0.2, "ducking": True, "animo": elegido, "desde": 0.0,
                "razon": f"Sección «{sec[0][0].seccion}»: música de {elegido}"
                         + (f" (no hay de {animo})" if elegido != animo else "")}
        if caida and ini <= caida[0] < fin:
            clip["caidas"] = [caida]
            clip["razon"] += "; cae antes de la revelación"
        salida.append(clip)
    return salida


def construir_edl(carpeta: CarpetaProyecto) -> dict:
    proyecto = carpeta.cargar()
    from .estilos import cargar_estilo

    estilo: Estilo = cargar_estilo(proyecto.estilo)
    gram = cargar_gramatica(estilo)["reglas"]
    esc: EscenasV2 = carpeta.cargar_escenas()
    vertical = esc.relacion_aspecto == "9:16"
    perfil = cargar_perfil_edicion(estilo, PERFIL_SHORT if vertical else None)
    direccion = leer_json(carpeta.ruta / "direccion.json") if (carpeta.ruta / "direccion.json").exists() else {}
    focos = direccion.get("focos") or {}
    rng = random.Random(proyecto.semilla)

    escenas = esc.escenas
    if any(e.tiempo.real_inicio is None for e in escenas):
        raise ValueError("faltan los tiempos reales: genera primero la voz (generar-voz)")
    por_id = {e.id: e for e in escenas}
    assets = {a.id: a for a in esc.assets}
    nivel_de_asset = {n.asset: n for n in esc.niveles}
    villano = next((n for n in esc.niveles if n.villano), None)
    revelacion = int(direccion.get("villano_revelacion", 0)) or None
    fin_voz = max(e.tiempo.real_fin for e in escenas)
    total = round(fin_voz + 1.2, 3)

    inicios = [0.0] + [max(0.0, e.tiempo.real_inicio - ADELANTO) for e in escenas[1:]]
    finales = inicios[1:] + [total]

    clips, textos, subtitulos, sfx = [], [], [], []
    previo_golpe = previo_rafaga = previo_circulo = False
    nivel_actual = 0
    ultimo_circulo = ultima_flecha = ultimo_icono = ultima_pregunta = -99.0
    secciones_con_circulo: set = set()
    tope_recurso = perfil.uso_maximo_por_recurso
    usos_cambio = {"reencuadre": 0, "icono_advertencia": 0, "flecha": 0, "etiqueta": 0, "lupa": 0}
    respiros_por_minuto: dict[int, int] = {}
    usos_entrada = {"entrada_abajo": 0, "entrada_lado": 0, "entrada_rebote": 0}
    ultima_entrada = None
    for idx, e in enumerate(escenas):
        ini, fin = round(inicios[idx], 3), round(finales[idx], 3)
        dur = fin - ini
        v = e.visual
        efectos: list[dict] = []
        razon = ""
        nueva_seccion = idx > 0 and e.seccion != escenas[idx - 1].seccion
        # --- de dónde sale la imagen
        tipo = v.tipo
        archivo = v.archivo
        modo = None
        if v.accion == "reusar":
            if isinstance(v.reusar_de, str) and v.reusar_de in nivel_de_asset:
                n = nivel_de_asset[v.reusar_de]
                modo, archivo = "tira", "assets/tira/tira_niveles.png"
                efectos.append({"efecto": "tira_deslizar_a_nivel", "desde": max(1, nivel_actual or 1),
                                "hasta": n.numero, "villano_pixelado": estilo.ocultar_villano,
                                "temblor": bool(n.villano)})
                nivel_actual = n.numero
                razon = f"Transición al nivel {n.numero}: la tira se desliza y se detiene en su tarjeta"
                frena = ini + min(0.8, dur * 0.5)          # la tira se detiene en la tarjeta (ver render)
                _sfx(sfx, "ruleta", ini, idx, "Ruleta: la tira gira y sus clics se frenan justo en la tarjeta del nivel",
                     termina_en=frena, duracion_max=round(frena - ini, 3))
                if n.villano:
                    razon += "; la tarjeta del villano tiembla antes de la revelación"
                    _sfx(sfx, "zumbido", ini + 0.8, idx, "Zumbido grave: el último nivel es el peligroso")
            elif isinstance(v.reusar_de, str):
                archivo, tipo = assets[v.reusar_de].archivo, assets[v.reusar_de].tipo
            else:
                # se sigue la cadena: una escena puede reusar a otra que a su vez reusa una imagen
                fuente = por_id[int(v.reusar_de)]
                vistas = set()
                while fuente.visual.accion == "reusar" and fuente.id not in vistas:
                    vistas.add(fuente.id)
                    ref = fuente.visual.reusar_de
                    if isinstance(ref, str):
                        break
                    fuente = por_id[int(ref)]
                ref = fuente.visual.reusar_de if fuente.visual.accion == "reusar" else None
                if isinstance(ref, str) and ref in assets:
                    archivo, tipo = assets[ref].archivo, assets[ref].tipo
                else:
                    archivo, tipo = fuente.visual.archivo, fuente.visual.tipo
                razon = f"Reuso de la imagen de la escena {fuente.id} (referencia a lo ya visto, 14.8)"
        elif v.accion == "componer":
            oculto = estilo.ocultar_villano
            modo, archivo = "tira", f"assets/tira/tira_niveles{'_pixelada' if oculto else ''}.png"
            efectos.append({"efecto": "tira_deslizar_a_nivel", "pasar": True, "villano_pixelado": oculto})
            razon = "Presentación de los niveles: la tira completa pasa" + (" con el villano pixelado" if oculto else "")
            _sfx(sfx, "ruleta", ini, idx, "Ruleta: la lista completa pasa girando y frena en el último nivel",
                 termina_en=fin - 0.05, duracion_max=round(max(0.5, dur - 0.05), 3))
        if modo is None:
            t_estilo = estilo.tipo(tipo) if tipo in estilo.ids_tipos else None
            if t_estilo is None:
                # asset reutilizado: el modo del primer tipo del estilo que trata el fondo igual
                quitar = next((a.quitar_fondo for a in esc.assets if a.archivo == archivo), True)
                t_estilo = next((x for x in estilo.tipos_de_escena if x.quitar_fondo == quitar),
                                estilo.tipos_de_escena[0])
            modo = t_estilo.modo_montaje
            if nueva_seccion:
                _sfx(sfx, "barrido", ini, idx, f"Barrido de cambio de sección: empieza «{e.seccion}»")
        # --- villano pixelado antes de su revelación (15.4)
        zonas = (direccion.get("pixelar") or {}).get(str(e.id))
        if zonas and estilo.ocultar_villano and (revelacion is None or e.id < revelacion):
            efectos.append({"efecto": "pixelar", "zonas": zonas, "bloque": 26})
            razon = (razon + "; " if razon else "") + "El villano va pixelado hasta su revelación"
        if revelacion and e.id == revelacion and villano:
            if estilo.ocultar_villano:
                efectos.append({"efecto": "revelar_pixelado", "duracion": 1.3, "nivel": villano.numero})
            efectos.append({"efecto": "destello_rojo", "en": ini + 0.55})
            _sfx(sfx, "golpe_grave", ini + 0.55, idx, "Golpe grave de la revelación, justo tras el silencio")
            _sfx(sfx, "subida_tension", ini - 1.6, idx - 1, "Subida de tensión que termina en la revelación",
                 termina_en=ini + 0.55)
            razon = ("Revelación del villano: " + ("se despixela en la tira con " if estilo.ocultar_villano else "")
                     + "destello rojo y golpe grave tras un silencio")
        # --- movimiento (14.4)
        regla = gram.get(e.intencion, {})
        mov_nombre = regla.get("movimiento")
        movimiento = None
        transicion = "corte"
        respiro = False
        if modo != "tira":
            if mov_nombre == "zoom_golpe" and previo_golpe:
                mov_nombre = "zoom_lento"
            sutil = False
            if mov_nombre is None and rng.random() < 0.8:
                mov_nombre, sutil = "zoom_lento", True    # la gramática no pide nada: un respiro muy leve
            elif mov_nombre and rng.random() < 0.07 and mov_nombre not in ("zoom_golpe", "entrada_rebote"):
                mov_nombre = None      # algunas quietas para que se noten las demás
            if mov_nombre == "zoom_golpe":
                foco = [round(rng.uniform(0.42, 0.58), 3), round(rng.uniform(0.40, 0.54), 3)]
                golpe = round(min(ini + 0.35 * dur, fin - 0.4), 3)
                movimiento = {"tipo": "zoom_golpe", "de": 1.0, "a": 1.07, "punto_foco": foco}
                efectos.append({"efecto": "zoom_golpe", "en": golpe})
                _sfx(sfx, "golpe_grave", golpe, idx, f"Golpe con el zoom de {e.intencion.replace('_', ' ')}")
            else:
                movimiento, extra = _mov(mov_nombre, rng, estilo.movimiento_maximo)
                efectos += extra
                if sutil and movimiento:
                    movimiento["a"] = round(1 + rng.uniform(0.012, 0.022), 3)
            # ráfaga: 2 o 3 acercamientos cortos al ritmo de un latido, solo en tension_creciente
            if (e.intencion == "tension_creciente" and dur >= 1.8 and not previo_rafaga
                    and not zonas and rng.random() < 0.75):
                n_golpes = 3 if dur >= 2.6 else 2
                t, tiempos = ini + rng.uniform(0.2, 0.35), []
                for _ in range(n_golpes):
                    tiempos.append(round(t, 3))
                    t += rng.uniform(0.42, 0.62)
                tiempos = [x for x in tiempos if x < fin - 0.25]
                if len(tiempos) >= 2:
                    movimiento = None
                    efectos = [x for x in efectos if x["efecto"] != "paneo_lento"]
                    efectos.append({"efecto": "rafaga", "tiempos": tiempos,
                                    "escalas": [round(1 + 0.045 * (k + 1) + rng.uniform(-0.008, 0.008), 3)
                                                for k in range(len(tiempos))],
                                    "punto_foco": [round(rng.uniform(0.44, 0.56), 3), round(rng.uniform(0.42, 0.52), 3)]})
                    for k, tt in enumerate(tiempos):
                        _sfx(sfx, "latido", tt - 0.03, idx, f"Latido {k + 1} de la ráfaga de tensión")
                    razon = (razon + "; " if razon else "") + "Ráfaga de acercamientos con latidos: la tensión sube"
            # 14.4: temblor leve solo en amenaza o tensión creciente, y no siempre
            if e.intencion in ("amenaza", "tension_creciente") and rng.random() < 0.5 \
                    and not any(x["efecto"] == "rafaga" for x in efectos):
                efectos.append({"efecto": "temblor_leve", "amplitud": 3})
            if regla.get("transicion") in ("fundido_corto", "fundido") and idx > 0:
                transicion = "fundido_corto"
            # --- foco: círculo rojo con el resto oscurecido, o una flecha al detalle
            f = focos.get(str(e.id))
            area = ((f["caja"][2] - f["caja"][0]) * (f["caja"][3] - f["caja"][1])) if f and f.get("caja") else 1
            # si el animal ya llena la imagen, encerrarlo no aporta nada
            if f and f.get("caja") and not zonas and dur >= 1.2 and not (f.get("tipo") == "nombre" and area > 0.45):
                t0 = _en_texto(e.narracion, f.get("palabra") or "", e.tiempo.real_inicio, e.tiempo.real_fin)
                t0 = round(min(max(t0, ini + 0.15), fin - 1.0), 3)
                if (f.get("tipo") == "nombre" and not previo_circulo
                        and (e.seccion not in secciones_con_circulo or t0 - ultimo_circulo >= 12)):
                    efectos.append({"efecto": "oscurecer_fondo", "en": t0, "caja": f["caja"], "nivel": 0.62})
                    efectos.append({"efecto": "circulo_rojo", "en": t0, "caja": f["caja"],
                                    "giro": round(rng.uniform(-14, 14), 1), "trazo": round(rng.uniform(0.34, 0.46), 2)})
                    _sfx(sfx, "pop", t0, idx, f"Pop al encerrar «{f.get('palabra')}»: entra un dato clave")
                    secciones_con_circulo.add(e.seccion)
                    ultimo_circulo = t0
                    razon = (razon + "; " if razon else "") + \
                        f"La voz nombra «{f.get('palabra')}»: se oscurece el resto y se encierra en un círculo"
                elif (t0 - ultima_flecha >= 15 or (dur > MAX_SIN_CAMBIO and t0 - ultima_flecha >= 8)) \
                        and (f.get("tipo") == "detalle" or e.intencion == "explicacion"):
                    x0, y0, x1, y1 = f["caja"]
                    lado = "izquierda" if (x0 + x1) / 2 > 0.5 else "derecha"
                    # detalle chico (garras, aguijón, ojos): lupa con zoom; si no, flecha
                    if area < 0.08 and usos_cambio["lupa"] <= usos_cambio["flecha"]:
                        efectos.append({"efecto": "lupa", "en": t0, "caja": f["caja"]})
                        usos_cambio["lupa"] += 1
                        razon = (razon + "; " if razon else "") + f"Lupa con el detalle «{f.get('palabra') or ''}»"
                    else:
                        efectos.append({"efecto": "flecha", "en": t0, "caja": f["caja"], "desde": lado})
                        usos_cambio["flecha"] += 1
                        razon = (razon + "; " if razon else "") + f"Flecha que señala «{f.get('palabra') or 'el detalle'}»"
                    ultima_flecha = t0
                    _sfx(sfx, "pop", t0, idx, "Pop suave con la flecha o la lupa")
            respiro = False
            # algo nuevo en pantalla cada interrupcion_de_patron_cada_seg (el corte cuenta): se
            # llenan los huecos del plano rotando recursos para que ninguno pase del uso máximo
            cada = perfil.interrupcion_de_patron_cada_seg
            ya = sorted([x["en"] for x in efectos if x["efecto"] in ("circulo_rojo", "flecha", "lupa", "zoom_golpe")]
                        + [tt for x in efectos if x["efecto"] == "rafaga" for tt in x["tiempos"]])
            puntos, cursor = [], ini
            for m in ya + [fin]:
                while m - cursor > cada + 0.4:
                    punto = cursor + rng.uniform(cada - 0.5, cada + 0.2)
                    if fin - punto < 0.9 or m - punto < 0.6:
                        break
                    puntos.append(round(punto, 3))
                    cursor = punto
                cursor = max(cursor, m)
            tiene_texto = str(e.id) in (direccion.get("textos") or {})
            en_clip: set = set()
            minuto = int(ini // 60)
            for punto in puntos:
                opciones = ["reencuadre"]
                if e.palabra_clave and not tiene_texto:
                    opciones.append("etiqueta")
                if e.intencion in ("amenaza", "advertencia", "tension_creciente") and punto - ultimo_icono >= 15:
                    opciones.append("icono_advertencia")
                opciones = [o for o in opciones if o not in en_clip]
                con_cupo = [o for o in opciones if usos_cambio[o] / (idx + 1) < tope_recurso]
                if not con_cupo and dur <= 6.0 and not respiro \
                        and respiros_por_minuto.get(minuto, 0) < perfil.respiros_max_por_minuto:
                    respiro = True
                    respiros_por_minuto[minuto] = respiros_por_minuto.get(minuto, 0) + 1
                    razon = (razon + "; " if razon else "") + "Respiro: plano sin cambio para dar contraste (14.2)"
                    continue
                elegibles = con_cupo or opciones
                if not elegibles:
                    continue
                o = min(elegibles, key=lambda r: (usos_cambio[r] / (idx + 1), rng.random()))
                en_clip.add(o)
                usos_cambio[o] += 1
                if o == "reencuadre":
                    efectos.append({"efecto": "reencuadre", "en": punto, "escala": round(rng.uniform(1.12, 1.18), 3),
                                    "punto_foco": [round(rng.uniform(0.38, 0.62), 3), round(rng.uniform(0.38, 0.55), 3)]})
                elif o == "etiqueta":
                    t_clave = _en_texto(e.narracion, e.palabra_clave, e.tiempo.real_inicio, e.tiempo.real_fin)
                    t_et = round(t_clave if abs(t_clave - punto) < 1.2 and t_clave < fin - 0.8 else punto, 3)
                    efectos.append({"efecto": "etiqueta", "en": t_et, "texto": e.palabra_clave.upper(),
                                    "lado": rng.choice(["izquierda", "derecha"]), "giro": round(rng.uniform(-7, 7), 1)})
                    _sfx(sfx, "pop", t_et, idx, f"Pop con la etiqueta «{e.palabra_clave}»: entra un dato clave")
                    razon = (razon + "; " if razon else "") + f"Etiqueta con la palabra clave «{e.palabra_clave}»"
                else:
                    ultimo_icono = punto
                    efectos.append({"efecto": "icono_advertencia", "en": punto, "lado": rng.choice(["izquierda", "derecha"])})
                    razon = (razon + "; " if razon else "") + "Aparece el ícono de advertencia"
            # signos de pregunta cuando la voz le pregunta algo al espectador (no seguidos)
            pregunta = e.intencion == "pregunta_al_espectador" or "?" in e.narracion
            if pregunta and ini - ultima_pregunta >= 10 and dur >= 1.2:
                efectos.append({"efecto": "signos_pregunta", "en": round(ini + rng.uniform(0.1, 0.3), 3),
                                "cantidad": rng.choice([2, 3]), "semilla": rng.randint(0, 10 ** 6)})
                ultima_pregunta = ini
                razon = (razon + "; " if razon else "") + "Signos de pregunta: la voz le pregunta al espectador"
            sonido = regla.get("sonido")
            if sonido == "alerta":
                _sfx(sfx, "alerta", ini + 0.1, idx, "Alerta corta: advertencia")
            elif sonido == "comico":
                _sfx(sfx, "comico", ini + 0.15, idx, "Efecto cómico corto: momento de humor")
            elif sonido == "zumbido" and rng.random() < 0.5:
                _sfx(sfx, "zumbido", ini + 0.3, idx, "Zumbido grave: amenaza")
        # --- entrada del objeto al cortar (sale de abajo, de un lado o con rebote) y vaivén suave
        if modo != "tira" and idx > 0 and archivo != clips[-1]["archivo"] and not zonas \
                and not any(x["efecto"] == "revelar_pixelado" for x in efectos):
            opciones = ["entrada_abajo", "entrada_lado", "entrada_rebote"]
            con_cupo = [o for o in opciones if usos_entrada[o] / (idx + 1) < tope_recurso and o != ultima_entrada]
            if con_cupo and rng.random() < 0.85:
                o = min(con_cupo, key=lambda r: (usos_entrada[r], rng.random()))
                usos_entrada[o] += 1
                ultima_entrada = o
                datos = {"efecto": o, "dur": round(rng.uniform(0.36, 0.48), 2)}
                if o == "entrada_lado":
                    datos["desde"] = rng.choice(["izquierda", "derecha"])
                efectos.append(datos)
                _sfx(sfx, "pop", ini + datos["dur"] * 0.7, idx, "Pop cuando la imagen entra y se asienta")
                razon = (razon + "; " if razon else "") + {"entrada_abajo": "la imagen sale desde abajo",
                                                           "entrada_lado": "la imagen entra de lado",
                                                           "entrada_rebote": "la imagen aparece con rebote"}[o]
        if modo != "tira":
            efectos.append({"efecto": "vaiven", "hz": round(rng.uniform(0.55, 0.85), 2), "px": round(rng.uniform(4, 7), 1),
                            "fase": round(rng.uniform(0, 6.28), 2)})
        previo_golpe = bool(movimiento and movimiento["tipo"] == "zoom_golpe")
        previo_rafaga = any(x["efecto"] == "rafaga" for x in efectos)
        previo_circulo = any(x["efecto"] == "circulo_rojo" for x in efectos)
        if not razon:
            razon = f"{e.intencion.replace('_', ' ').capitalize()}: {(movimiento or {}).get('tipo') or 'sin movimiento'} y {transicion}"
        clip = {"id": f"c{e.id:03d}", "escena": e.id, "inicio": ini, "fin": fin, "archivo": archivo,
                "modo": modo, "movimiento": movimiento, "transicion_entrada": transicion, "efectos": efectos,
                "razon": razon}
        if modo != "tira" and respiro:
            clip["respiro"] = True
        clips.append(clip)
        # --- texto en pantalla al decir la palabra (14.3), con pop: entra un dato clave
        t = (direccion.get("textos") or {}).get(str(e.id))
        if t:
            ti = _en_texto(e.narracion, t.get("palabra", ""), e.tiempo.real_inicio, e.tiempo.real_fin)
            textos.append({"id": f"t{e.id:03d}", "inicio": round(ti, 3), "fin": fin, "texto": t["texto"],
                           "estilo": "titulo_contorno", "posicion": "arriba_centro",
                           "razon": "Refuerza la idea clave cuando la voz la dice"})
            _sfx(sfx, "pop", ti, idx, f"Pop con el texto «{t['texto']}»: entra un dato clave")
        # --- subtítulos por trozos
        trozos = trozos_subtitulo(e.narracion)
        a, b = e.tiempo.real_inicio, e.tiempo.real_fin
        largo = sum(len(x) for x in trozos)
        acum = 0
        for tr in trozos:
            t0 = a + (b - a) * acum / largo
            acum += len(tr)
            t1 = a + (b - a) * acum / largo
            subtitulos.append({"inicio": round(t0, 3), "fin": round(max(t1, t0 + 0.2), 3), "texto": tr})
    for e, c in zip(escenas, clips):
        v = (direccion.get("video_escena") or {}).get(str(e.id))
        if v and (carpeta.ruta / v["archivo"]).exists():
            # escena hecha con un video REAL verificado de Pexels: se ve a pantalla completa
            c["efectos"].append({"efecto": "video_real", "en": c["inicio"], "dur": round(c["fin"] - c["inicio"], 3),
                                 "archivo": v["archivo"], "desde": v.get("desde", 0.5), "origen": v.get("origen", "")})
            c["razon"] += "; escena con video REAL de Pexels (verificado)"
    _stock(esc, escenas, clips, carpeta.ruta, revelacion, rng, sfx)
    reacciones = _reacciones(estilo, escenas, clips, carpeta.ruta, revelacion, rng, direccion.get("reacciones"), sfx)
    if reacciones:
        p = carpeta.cargar()
        if not p.requiere_divulgacion_contenido_sintetico:
            p.requiere_divulgacion_contenido_sintetico = True
            carpeta.guardar(p)
    musica = _musica(escenas, clips, revelacion, total, rng)
    _equilibrar_movimientos(clips, perfil, rng, estilo.movimiento_maximo)
    _sonido_en_cada_corte(sfx, escenas, clips, rng)       # el recorte deja solo sfx_por_minuto
    vivos = _recortar_sonidos(sfx, len(clips), total, perfil, rng)
    pistas_sfx = _pistas_sfx(vivos, rng)
    edl = {"version": 1, "duracion_total": total,
           "pistas": {"fondo": [{"id": "f1", "inicio": 0, "fin": total, "tipo": "textura",
                                 "archivo": "assets/papel_arrugado.png"}],
                      "escenas": clips, "elementos": [], "textos": textos, "subtitulos": subtitulos,
                      "voz": [{"inicio": 0, "archivo": "audio/voz.wav"}], "musica": musica, "sfx": pistas_sfx},
           "historial": [{"version": 1, "autor": "director_edicion_reglas", "cambio": "primera EDL",
                          "razon": "Construida desde las intenciones, la voz real y direccion.json"}]}
    EDL.model_validate(edl)
    escribir_json(carpeta.ruta / "edl.json", edl)
    return edl


def validar(edl: dict, perfil=None) -> list[str]:
    """Reglas fijas del Validador (4.3) y el detector de patrones mecánicos (14.10)."""
    maximo = getattr(perfil, "uso_maximo_por_recurso", 0.35)
    exentos = set(getattr(perfil, "recursos_exentos_de_uso_maximo", ["corte"])) | ESTRUCTURALES
    avisos = []
    clips = edl["pistas"]["escenas"]
    for c in clips:
        dur = c["fin"] - c["inicio"]
        cambia = any(x["efecto"] in ("reencuadre", "zoom_golpe", "tira_deslizar_a_nivel", "revelar_pixelado",
                                     "rafaga", "circulo_rojo", "flecha", "icono_advertencia", "signos_pregunta",
                                     "reaccion_presentador", "etiqueta", "lupa", "foto_real", "video_real")
                     for x in c["efectos"])
        if dur > MAX_SIN_CAMBIO and not cambia and not c.get("respiro"):
            avisos.append(f"{c['id']}: {dur:.1f} s sin cambio visual")
    for a, b in zip(clips, clips[1:]):
        if (a.get("movimiento") or {}).get("tipo") == "zoom_golpe" and (b.get("movimiento") or {}).get("tipo") == "zoom_golpe":
            avisos.append(f"{a['id']} y {b['id']}: zoom_golpe seguidos")
    huecos = [(a["id"], b["id"]) for a, b in zip(clips, clips[1:]) if b["inicio"] - a["fin"] > 0.01]
    avisos += [f"hueco entre {x} y {y}" for x, y in huecos]
    # 14.10 · uso máximo por recurso (movimientos, transiciones, efectos y sonidos)
    if clips:
        uso: dict[str, set] = {}
        for c in clips:
            for r in [(c.get("movimiento") or {}).get("tipo"), c.get("transicion_entrada")] + \
                     [x["efecto"] for x in c["efectos"]]:
                if r and r not in exentos:
                    uso.setdefault(r, set()).add(c["id"])
        for s in edl["pistas"].get("sfx", []):
            clip_id = next((c["id"] for c in clips if c["inicio"] <= s["inicio"] < c["fin"]), None)
            uso.setdefault("sfx:" + (s.get("tipo") or s["variante"].rsplit("_", 1)[0]), set()).add(clip_id)
        for r, ids in sorted(uso.items()):
            if len(ids) / len(clips) > maximo + 1e-9:
                avisos.append(f"{r} en {len(ids)} de {len(clips)} escenas (máximo {maximo:.0%})")
        # nunca la misma transición ni el mismo movimiento tres veces seguidas
        for a, b, c in zip(clips, clips[1:], clips[2:]):
            ta = (a.get("movimiento") or {}).get("tipo")
            if ta and ta not in exentos and ta == (b.get("movimiento") or {}).get("tipo") == (c.get("movimiento") or {}).get("tipo"):
                avisos.append(f"{a['id']}–{c['id']}: {ta} tres veces seguidas")
            tr = a.get("transicion_entrada")
            if tr and tr not in exentos and tr == b.get("transicion_entrada") == c.get("transicion_entrada"):
                avisos.append(f"{a['id']}–{c['id']}: transición {tr} tres veces seguidas")
    return avisos
