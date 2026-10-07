"""Animaciones por código dentro de los videos de imágenes (Peligro Tropical): el video híbrido.

El guion NO cambia. Después de escribirlo, Claude elige las frases que EXPLICAN algo (cómo funciona el veneno,
una comparación, un número, causa y efecto) y arma para cada una una escena animada con las piezas del motor
de El Calvo Explica (calma/): medidores, flechas, termómetros, gráficas, el animal del nivel como imagen…
Esas escenas NO pagan imagen (reusan la de una escena anterior, que queda tapada), y al hacer el video se dibujan
con los tiempos reales de la voz y van a pantalla completa sobre el mismo papel del canal.

1. `disenar` (después del guion, antes de las imágenes): assets/animaciones/disenos.json.
2. `renderizar` (después de la voz): assets/animaciones/escena_<id>.mp4 y direccion.json → «animacion_escena».
3. La edición (edicion.construir_edl) pone el efecto «animacion» en esa escena y la render lo muestra.

Todo con la suscripción de Claude (0 pesos) y el motor propio (0 pesos).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import escribir_json, leer_json

CARPETA = Path("assets") / "animaciones"
DISENOS = CARPETA / "disenos.json"
# el personaje de El Calvo Explica no sale en otro canal (cada canal tiene su mascota)
PIEZAS_FUERA = {"personaje", "estirado", "tablero", "garrapata", "pinzas", "brazo", "dedos", "titulo_tema",
                "circulo_tema"}
NO_ANIMAR = {"gancho", "revelacion", "giro", "cierre", "humor", "pregunta_al_espectador"}


def candidatas(esc) -> list:
    """Escenas que se pueden animar: con imagen propia, que no abren el video, no siguen a la tira (ahí
    va la tarjeta del animal) y que tienen antes otra escena con imagen para reusar."""
    salida, hay_imagen_antes = [], False
    escenas = esc.escenas
    for i, e in enumerate(escenas):
        v = e.visual
        previa = escenas[i - 1].visual if i else None
        tras_tira = previa is not None and previa.accion == "reusar" and isinstance(previa.reusar_de, str) \
            and any(n.asset == previa.reusar_de for n in esc.niveles)
        if (v.accion == "generar" and i >= 3 and hay_imagen_antes and not tras_tira
                and e.intencion not in NO_ANIMAR and len(e.narracion.split()) >= 6):
            salida.append(e)
        if v.accion == "generar":
            hay_imagen_antes = True
    return salida


def _prompt(cands: list, n: int, niveles: list) -> str:
    from .explica.catalogo import MOVIMIENTOS, texto_catalogo

    catalogo = "\n".join(x for x in texto_catalogo().splitlines()
                         if not any(x.startswith(f"- {p}:") for p in PIEZAS_FUERA))
    lista = "\n".join(f"{e.id}. [{e.intencion}] {e.narracion}" for e in cands)
    animales = "\n".join(f"- «{x.asset}»: {x.nombre}" for x in niveles) or "- (este video no tiene niveles)"
    return f"""Eres el animador de un canal de YouTube de animales peligrosos que usa imágenes ilustradas. Queremos un
video HÍBRIDO: algunas frases que EXPLICAN algo se cambian por una animación hecha por código (diagramas que se
mueven), el resto sigue con imágenes. Video 1920x1080 sobre papel cuadriculado claro.

Elige EXACTAMENTE {n} frases de esta lista (o menos si no hay tantas buenas). Las mejores: explican cómo funciona
algo (el veneno, el ataque, el cuerpo), comparan (más grande que, más rápido que), dan un número o una escala,
o muestran causa y efecto. NO elijas frases que presentan al animal por primera vez ni que solo describen cómo se
ve: esas quedan mejor con la ilustración. Repártelas a lo largo del video (no todas seguidas).

FRASES (id. [intención] narración):
{lista}

PIEZAS (no hay otras; no inventes piezas; NO hay personaje: este canal tiene su propia mascota):
{catalogo}
- imagen: la ilustración de un animal del video. estado {{"asset": "<id del animal>", "ancho": 500-900}}.
  Úsala para que se vea DE QUÉ animal se habla junto al diagrama. Animales disponibles:
{animales}

MOVIMIENTOS: {MOVIMIENTOS}

REGLAS
- Cada elemento entra con «palabra»: una palabra (o dos seguidas) que la voz dice EN ESA FRASE, escrita igual.
- Algo nuevo aparece o cambia cada 1,5 segundos como máximo (la voz dice ~3,5 palabras por segundo).
- Máximo 4 elementos en pantalla. Textos de máximo ~22 caracteres, en mayúsculas, palabras clave en rojo.
- Nada se sale de la pantalla. Deja libre la franja de abajo (y > 930): ahí van los subtítulos.
- Empujón de cámara («empujon»: [{{"palabra": "...", "foco": [x, y]}}]) en la palabra más fuerte.
- Sin sangre ni heridas; nada de consejos de salud.

Devuelve SOLO un JSON:
{{"animaciones": [{{"escena": <id>, "elementos": [{{"id", "pieza", "estado", "posicion": [x, y], "tamano",
  "palabra", "movimiento": [...], "retraso", "rotacion"}}], "temblor": [...], "empujon": [...]}}, ...]}}
"""


def disenar(carpeta, ejecutar=None, avisar=print, proporcion: float | None = None) -> dict:
    """Elige las frases y arma sus animaciones. Las escenas elegidas dejan de pagar imagen (reusan una
    anterior). Si ya está hecho, no hace nada."""
    from .claude_cli import extraer_json
    from .estilos import cargar_estilo
    from .explica.autor import _claude, limpiar_escena

    ruta = carpeta.ruta / DISENOS
    if ruta.exists():
        return leer_json(ruta)
    p = carpeta.cargar()
    proporcion = cargar_estilo(p.estilo).animaciones_codigo if proporcion is None else proporcion
    esc = carpeta.cargar_escenas()
    if esc.relacion_aspecto == "9:16":                  # el short vertical sigue solo con imágenes
        return {}
    cands = candidatas(esc)
    n = min(len(cands), round(len(esc.escenas) * proporcion))
    if n <= 0:
        return {}
    avisar(f"Claude está eligiendo {n} frases para animar por código…")
    por_id = {e.id: e for e in cands}
    assets = {x.asset for x in esc.niveles}
    notas: list[str] = []
    ultimo_error = ""
    for intento in range(3):
        prompt = _prompt(cands, n, esc.niveles) + (f"\n\nOJO, tu respuesta anterior falló: {ultimo_error}"
                                                   if ultimo_error else "")
        try:
            respuesta = extraer_json(_claude(ejecutar, prompt, carpeta.ruta))
            elegidas = [a for a in respuesta.get("animaciones") or [] if int(a.get("escena", -1)) in por_id]
            if not elegidas:
                raise ValueError("no elegiste ninguna frase de la lista")
            break
        except (ValueError, TypeError, json.JSONDecodeError) as ex:
            ultimo_error = str(ex)
            avisar(f"  reintento ({ex})")
    else:
        raise RuntimeError(f"Claude no pudo armar las animaciones: {ultimo_error}")
    disenos: dict[str, dict] = {}
    for a in elegidas[:n]:
        e = por_id[int(a["escena"])]
        crudo = {**a, "elementos": [x for x in a.get("elementos") or [] if x.get("pieza") not in PIEZAS_FUERA]}
        for x in crudo["elementos"]:
            if x.get("pieza") == "imagen" and (x.get("estado") or {}).get("asset") not in assets:
                x["pieza"], x["estado"] = "texto", {"texto": ""}
        escena = limpiar_escena(crudo, e.narracion, "codigo", "blanco", notas)
        escena["elementos"] = [x for x in escena["elementos"]
                               if not (x["pieza"] == "texto" and not str(x["estado"].get("texto", "")).strip())]
        if escena["elementos"]:
            disenos[str(e.id)] = {"narracion": e.narracion, "escena": escena}
    # las escenas animadas no pagan imagen: reusan la imagen de la escena anterior con imagen
    anterior = None
    cambiadas = 0
    for e in esc.escenas:
        if str(e.id) in disenos and anterior is not None:
            disenos[str(e.id)]["visual_original"] = e.visual.model_dump()
            e.visual.accion, e.visual.reusar_de = "reusar", anterior
            cambiadas += 1
        elif e.visual.accion == "generar":
            anterior = e.id
    disenos = {k: v for k, v in disenos.items() if "visual_original" in v}
    carpeta.guardar_escenas(esc)
    datos = {"version": 1, "escenas": disenos, "notas": notas}
    escribir_json(ruta, datos)
    avisar(f"Animaciones por código: {cambiadas} escenas (esas imágenes ya no se pagan)")
    return datos


def _palabras(narracion: str, a: float, b: float) -> list[dict]:
    """Tiempos de cada palabra dentro de la frase (repartidos por largo: la frase es corta)."""
    from .calma.alinear_pausas import _peso
    from .calma.escenas import normalizar

    ps = narracion.split()
    pesos = [_peso(x) for x in ps]
    total, acum, salida = sum(pesos) or 1.0, 0.0, []
    for x, w in zip(ps, pesos):
        ini = a + (b - a) * acum / total
        acum += w
        if normalizar(x):
            salida.append({"p": x, "n": normalizar(x), "inicio": round(ini, 3), "fin": round(a + (b - a) * acum / total, 3)})
    return salida


def _datos_de(diseno: dict, inicio_voz: float, fin_voz: float, dur: float, raiz: Path, fondo: Path,
              assets: dict) -> dict:
    from .calma import escenas as E
    from .explica import canal as C

    escena = json.loads(json.dumps(diseno["escena"]))
    escena["id"] = 1
    escena["fondo"] = f"archivo:{fondo}"
    escena.pop("palabra_inicio", None)
    for el in escena["elementos"]:
        if el["pieza"] == "imagen":
            archivo = assets.get(el["estado"].get("asset"))
            el["estado"] = {"archivo": str(raiz / archivo), "ancho": float(el["estado"].get("ancho", 700))} \
                if archivo and (raiz / archivo).exists() else None
    escena["elementos"] = [x for x in escena["elementos"] if x.get("estado") is not None]
    preset = C.completar(None)
    datos = {"video": {"ancho": 1920, "alto": 1080, "fps": 30, "ritmo": float(preset["ritmo"]),
                       "deriva": float(preset["deriva_camara"])},
             "escenas": [{**escena, "inicio": 0.0}]}
    E.fijar_tiempos(datos, _palabras(diseno["narracion"], inicio_voz, fin_voz), dur)
    return datos


def renderizar(carpeta, ffmpeg: str, avisar=print) -> int:
    """Dibuja cada animación con los tiempos reales de la voz (después de generar-voz). Las ya dibujadas con
    los mismos tiempos no se repiten. Devuelve cuántas hay."""
    from .calma.render import render
    from .edicion import ADELANTO
    from .estilos import cargar_estilo
    from .render import asegurar_fondo

    ruta = carpeta.ruta / DISENOS
    if not ruta.exists():
        return 0
    disenos = leer_json(ruta).get("escenas") or {}
    direccion_ruta = carpeta.ruta / "direccion.json"
    if not disenos:
        if direccion_ruta.exists() and "animacion_escena" in (d := leer_json(direccion_ruta)):
            d.pop("animacion_escena")
            escribir_json(direccion_ruta, d)
        return 0
    p = carpeta.cargar()
    esc = carpeta.cargar_escenas()
    escenas = esc.escenas
    if any(e.tiempo.real_inicio is None for e in escenas):
        raise ValueError("faltan los tiempos reales de la voz")
    fin_total = round(max(e.tiempo.real_fin for e in escenas) + 1.2, 3)
    inicios = [0.0] + [max(0.0, e.tiempo.real_inicio - ADELANTO) for e in escenas[1:]]
    finales = inicios[1:] + [fin_total]
    fondo = asegurar_fondo(carpeta.ruta, cargar_estilo(p.estilo), p.semilla)
    assets = {a.id: a.archivo for a in esc.assets}
    direccion = leer_json(direccion_ruta) if direccion_ruta.exists() else {}
    hechas = {}
    for i, e in enumerate(escenas):
        d = disenos.get(str(e.id))
        if not d:
            continue
        ini, fin = inicios[i], finales[i]
        datos = _datos_de(d, e.tiempo.real_inicio - ini, e.tiempo.real_fin - ini, round(fin - ini, 3),
                          carpeta.ruta, fondo, assets)
        firma = hashlib.sha1(json.dumps(datos, sort_keys=True).encode()).hexdigest()[:12]
        archivo = CARPETA / f"escena_{e.id}_{firma}.mp4"
        if not (carpeta.ruta / archivo).exists():
            avisar(f"  animando la escena {e.id} ({fin - ini:.1f} s)…")
            render(datos, carpeta.ruta / archivo, ffmpeg, avisar=lambda *_: None, en_paralelo=1)
        hechas[str(e.id)] = {"archivo": archivo.as_posix(), "efectos": _sonidos(datos)}
    direccion["animacion_escena"] = hechas
    escribir_json(direccion_ruta, direccion)
    if hechas:
        avisar(f"Animaciones por código listas: {len(hechas)}")
    return len(hechas)


# sonidos del motor → sonidos de la biblioteca del canal (los de Peligro Tropical)
SONIDO_CANAL = {"pop": "pop", "swoosh": "barrido", "swoosh_suave": "barrido", "golpe": "golpe_grave",
                "error": "pop", "ding": "pop", "rayon": None, "golpe_suave": None}


def _sonidos(datos: dict) -> list[dict]:
    from .calma import sonidos

    return [{"t": round(t, 3), "tipo": SONIDO_CANAL[n]} for t, n, _ in sonidos.eventos(datos) if SONIDO_CANAL.get(n)]


def deshacer(carpeta) -> int:
    """Devuelve las escenas animadas a su imagen original (por si el dueño no quiere animaciones en un video)."""
    ruta = carpeta.ruta / DISENOS
    if not ruta.exists():
        return 0
    from .esquemas import Visual

    disenos = leer_json(ruta).get("escenas") or {}
    esc = carpeta.cargar_escenas()
    n = 0
    for e in esc.escenas:
        d = disenos.get(str(e.id))
        if d and d.get("visual_original"):
            e.visual = Visual(**d["visual_original"])
            n += 1
    carpeta.guardar_escenas(esc)
    escribir_json(ruta, {"version": 1, "escenas": {}, "notas": ["deshecho por el dueño"]})
    return n
