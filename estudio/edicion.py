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
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from .config import escribir_json, leer_json
from .esquemas import EDL, EscenasV2, Estilo
from .estilos import cargar_gramatica
from .proyecto import CarpetaProyecto

FPS = 30
ADELANTO = 3 / FPS
MAX_SIN_CAMBIO = 4.5
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


def construir_edl(carpeta: CarpetaProyecto) -> dict:
    proyecto = carpeta.cargar()
    from .estilos import cargar_estilo

    estilo: Estilo = cargar_estilo(proyecto.estilo)
    gram = cargar_gramatica(estilo)["reglas"]
    esc: EscenasV2 = carpeta.cargar_escenas()
    direccion = leer_json(carpeta.ruta / "direccion.json") if (carpeta.ruta / "direccion.json").exists() else {}
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
    previo_golpe = False
    nivel_actual = 0
    for idx, e in enumerate(escenas):
        ini, fin = round(inicios[idx], 3), round(finales[idx], 3)
        dur = fin - ini
        v = e.visual
        efectos: list[dict] = []
        razon = ""
        # --- de dónde sale la imagen
        origen, tipo = v, v.tipo
        archivo = v.archivo
        modo = None
        if v.accion == "reusar":
            if isinstance(v.reusar_de, str) and v.reusar_de in nivel_de_asset:
                n = nivel_de_asset[v.reusar_de]
                modo, archivo = "tira", "assets/tira/tira_niveles.png"
                efectos.append({"efecto": "tira_deslizar_a_nivel", "desde": max(1, nivel_actual or 1),
                                "hasta": n.numero, "villano_pixelado": True,
                                "temblor": bool(n.villano)})
                nivel_actual = n.numero
                razon = f"Transición al nivel {n.numero}: la tira se desliza y se detiene en su tarjeta"
                sfx.append({"tipo": "barrido", "inicio": ini + 0.02})
                if n.villano:
                    razon += "; el villano sigue pixelado y tiembla antes de la revelación"
                    sfx.append({"tipo": "zumbido", "inicio": ini + 0.8})
            elif isinstance(v.reusar_de, str):
                archivo, tipo = assets[v.reusar_de].archivo, assets[v.reusar_de].tipo
            else:
                fuente = por_id[int(v.reusar_de)]
                archivo, tipo = fuente.visual.archivo, fuente.visual.tipo
                razon = f"Reuso de la imagen de la escena {fuente.id} (referencia a lo ya visto, 14.8)"
        elif v.accion == "componer":
            modo, archivo = "tira", "assets/tira/tira_niveles_pixelada.png"
            efectos.append({"efecto": "tira_deslizar_a_nivel", "pasar": True, "villano_pixelado": True})
            razon = "Presentación de los niveles: la tira completa pasa con el villano pixelado"
            sfx.append({"tipo": "barrido", "inicio": ini + 0.05})
        if modo is None:
            t_estilo = estilo.tipo(tipo) if tipo in estilo.ids_tipos else None
            if t_estilo is None:
                # asset reutilizado: el modo del primer tipo del estilo que trata el fondo igual
                quitar = next((a.quitar_fondo for a in esc.assets if a.archivo == archivo), True)
                t_estilo = next((x for x in estilo.tipos_de_escena if x.quitar_fondo == quitar),
                                estilo.tipos_de_escena[0])
            modo = t_estilo.modo_montaje
        # --- villano pixelado antes de su revelación (15.4)
        zonas = (direccion.get("pixelar") or {}).get(str(e.id))
        if zonas and (revelacion is None or e.id < revelacion):
            efectos.append({"efecto": "pixelar", "zonas": zonas, "bloque": 26})
            razon = (razon + "; " if razon else "") + "El villano va pixelado hasta su revelación"
        if revelacion and e.id == revelacion and villano:
            efectos.append({"efecto": "revelar_pixelado", "duracion": 1.3, "nivel": villano.numero})
            efectos.append({"efecto": "destello_rojo", "en": ini + 0.55})
            sfx.append({"tipo": "golpe", "inicio": ini + 0.55})
            razon = "Revelación del villano: se despixela en la tira con destello rojo y golpe grave tras un silencio"
        # --- movimiento (14.4)
        regla = gram.get(e.intencion, {})
        mov_nombre = regla.get("movimiento")
        movimiento = None
        transicion = "corte"
        if modo != "tira":
            if mov_nombre == "zoom_golpe" and previo_golpe:
                mov_nombre = "zoom_lento"
            sutil = False
            if mov_nombre is None and rng.random() < 0.6:
                mov_nombre, sutil = "zoom_lento", True    # la gramática no pide nada: un respiro muy leve
            elif mov_nombre and rng.random() < 0.12 and mov_nombre != "zoom_golpe":
                mov_nombre = None      # algunas quietas para que se noten las demás
            foco = [round(rng.uniform(0.42, 0.58), 3), round(rng.uniform(0.40, 0.54), 3)]
            amp = round(rng.uniform(0.025, estilo.movimiento_maximo), 3)
            if sutil:
                amp = round(rng.uniform(0.012, 0.022), 3)
            if mov_nombre in ("zoom_lento", "entrada_rebote"):
                movimiento = {"tipo": "zoom_lento", "de": 1.0, "a": round(1 + amp, 3), "punto_foco": foco}
            elif mov_nombre == "alejamiento_lento":
                movimiento = {"tipo": "alejamiento_lento", "de": round(1 + amp, 3), "a": 1.0, "punto_foco": foco}
            elif mov_nombre == "paneo_lento":
                d = rng.choice([-1, 1])
                movimiento = {"tipo": "paneo_lento", "de": 1.06, "a": 1.06,
                              "punto_foco": [round(0.5 - 0.03 * d, 3), foco[1]]}
                efectos.append({"efecto": "paneo_lento", "hasta": [round(0.5 + 0.03 * d, 3), foco[1]]})
            elif mov_nombre == "zoom_golpe":
                movimiento = {"tipo": "zoom_golpe", "de": 1.0, "a": 1.07, "punto_foco": foco}
                efectos.append({"efecto": "zoom_golpe", "en": round(min(ini + 0.35 * dur, fin - 0.4), 3)})
                sfx.append({"tipo": "golpe_suave", "inicio": round(min(ini + 0.35 * dur, fin - 0.4), 3)})
            # 14.4: temblor leve solo en amenaza o tensión creciente, y no siempre
            if e.intencion in ("amenaza", "tension_creciente") and rng.random() < 0.5:
                efectos.append({"efecto": "temblor_leve", "amplitud": 3})
            if regla.get("transicion") in ("fundido_corto", "fundido") and idx > 0:
                transicion = "fundido_corto"
            if dur > MAX_SIN_CAMBIO:
                efectos.append({"efecto": "reencuadre", "en": round(ini + dur / 2, 3),
                                "escala": round(rng.uniform(1.12, 1.18), 3),
                                "punto_foco": [round(rng.uniform(0.38, 0.62), 3), round(rng.uniform(0.38, 0.55), 3)]})
            if e.intencion == "dato_impactante" and rng.random() < 0.5:
                sfx.append({"tipo": "pop", "inicio": ini + 0.05})
        previo_golpe = bool(movimiento and movimiento["tipo"] == "zoom_golpe")
        if not razon:
            razon = f"{e.intencion.replace('_', ' ').capitalize()}: {mov_nombre or 'sin movimiento'} y {transicion}"
        clip = {"id": f"c{e.id:03d}", "escena": e.id, "inicio": ini, "fin": fin, "archivo": archivo,
                "modo": modo, "movimiento": movimiento, "transicion_entrada": transicion, "efectos": efectos,
                "razon": razon}
        clips.append(clip)
        # --- texto en pantalla al decir la palabra (14.3)
        t = (direccion.get("textos") or {}).get(str(e.id))
        if t:
            ti = _en_texto(e.narracion, t.get("palabra", ""), e.tiempo.real_inicio, e.tiempo.real_fin)
            textos.append({"id": f"t{e.id:03d}", "inicio": round(ti, 3), "fin": fin, "texto": t["texto"],
                           "estilo": "titulo_contorno", "posicion": "arriba_centro",
                           "razon": "Refuerza la idea clave cuando la voz la dice"})
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
    # sfx con variante y tono (14.7): nunca la misma variante dos veces seguidas
    pistas_sfx, ultima = [], {}
    for k, s in enumerate(sfx):
        variante = rng.choice([x for x in range(1, 4) if x != ultima.get(s["tipo"])])
        ultima[s["tipo"]] = variante
        pistas_sfx.append({"id": f"s{k:03d}", "inicio": round(s["inicio"], 3),
                           "archivo": f"render/sfx/{s['tipo']}_{variante}.wav", "variante": f"{s['tipo']}_{variante}",
                           "tono": round(rng.uniform(0.96, 1.04), 3),
                           "volumen": {"barrido": 0.45, "golpe": 0.9, "golpe_suave": 0.5, "pop": 0.35,
                                       "zumbido": 0.35}.get(s["tipo"], 0.5)})
    edl = {"version": 1, "duracion_total": total,
           "pistas": {"fondo": [{"id": "f1", "inicio": 0, "fin": total, "tipo": "textura",
                                 "archivo": "assets/papel_arrugado.png"}],
                      "escenas": clips, "elementos": [], "textos": textos, "subtitulos": subtitulos,
                      "voz": [{"inicio": 0, "archivo": "audio/voz.wav"}], "musica": [], "sfx": pistas_sfx},
           "historial": [{"version": 1, "autor": "director_edicion_reglas", "cambio": "primera EDL",
                          "razon": "Construida desde las intenciones, la voz real y direccion.json"}]}
    EDL.model_validate(edl)
    escribir_json(carpeta.ruta / "edl.json", edl)
    return edl


def validar(edl: dict) -> list[str]:
    """Reglas fijas del Validador (4.3) que se pueden comprobar sobre la EDL."""
    avisos = []
    clips = edl["pistas"]["escenas"]
    for c in clips:
        dur = c["fin"] - c["inicio"]
        cambia = any(x["efecto"] in ("reencuadre", "zoom_golpe", "tira_deslizar_a_nivel",
                                     "revelar_pixelado") for x in c["efectos"])
        if dur > MAX_SIN_CAMBIO and not cambia:
            avisos.append(f"{c['id']}: {dur:.1f} s sin cambio visual")
    for a, b in zip(clips, clips[1:]):
        if (a.get("movimiento") or {}).get("tipo") == "zoom_golpe" and (b.get("movimiento") or {}).get("tipo") == "zoom_golpe":
            avisos.append(f"{a['id']} y {b['id']}: zoom_golpe seguidos")
    huecos = [(a["id"], b["id"]) for a, b in zip(clips, clips[1:]) if b["inicio"] - a["fin"] > 0.01]
    avisos += [f"hueco entre {x} y {y}" for x, y in huecos]
    return avisos
