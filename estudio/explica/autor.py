"""El Calvo Explica hecho por Xandart sola (lo que antes hacía Claude a mano en la nube):

1. `escribir_guion`: Claude escribe el guion con el molde de 5 partes + la lista de dudas; el revisor lo
   comprueba y, si algo falla, Claude lo corrige (hasta 3 veces).
2. `armar_escenas`: para cada tema, Claude elige con el catálogo qué piezas salen en cada frase y en qué
   palabra; Xandart valida (piezas, palabras, máximo 4, textos que quepan) y arregla lo que pueda.
3. Revisión con los ojos: se dibuja la hoja de cuadros del tema, Claude la MIRA (herramienta Read) y devuelve
   las escenas corregidas. Así trabaja Claude a mano: armar, mirar y corregir.

Todo va por la suscripción de Claude (0 pesos). Cada paso deja sus archivos en la carpeta del video.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..calma import escenas as E
from ..calma.piezas import PIEZAS, ancho_texto, dibujar
from ..config import escribir_json, leer_json
from . import canal as C
from . import guion as G
from .catalogo import FONDOS_ESCENA, MOVIMIENTOS, texto_catalogo, texto_fondos
from .escenas import cuadricula

EJEMPLOS = Path(__file__).resolve().parent / "ejemplos"
TIPO_DE_PARTE = {"escena": "ilustracion", "bautizo": "personaje", "explicacion": "codigo", "cierre": "personaje"}
W, H = 1920, 1080


def _claude(ejecutar, prompt: str, cwd: Path, herramientas: list[str] | None = None, liviano: bool = False) -> str:
    """`liviano` (escenas y revisión): el modelo y el razonamiento del preset (17-10: gasta mucho menos del plan
    del dueño; el guion sigue con el modelo completo)."""
    if ejecutar is None:
        from .. import claude_cli

        preset = C.cargar()
        texto, _ = claude_cli.ejecutar(prompt, cwd=cwd, herramientas=herramientas, tiempo_max_s=900,
                                       modelo=preset.get("modelo_escenas") if liviano else None,
                                       pensamiento=int(preset.get("pensamiento_escenas", 2000)) if liviano else 4000)
        return texto
    texto, _ = ejecutar(prompt, cwd=cwd, herramientas=herramientas)
    return texto


# ------------------------------------------------------------------ 1. guion

EJEMPLO_TEMA = (EJEMPLOS / "sacudida.txt").read_text(encoding="utf-8") if (EJEMPLOS / "sacudida.txt").exists() else ""


def _instruccion_comentarios(n: int) -> str:
    medio = max(1, n // 2)
    return f"""- LLAMADOS A COMENTAR (obligatorios, tono natural, sin sonar a anuncio). Escribe cada uno en su propio renglón
  empezando con su etiqueta: [COMENTA:tipo|lo que escribiría un espectador, máximo 40 letras, sin emojis]. La
  etiqueta no se lee en voz alta (el sistema la quita) y esa frase no cuenta para el largo de la parte.
  1. En el CIERRE del tema 2: si el espectador también lo tiene o le ha pasado, que lo escriba con una palabra
     corta. Ej.: «[COMENTA:experiencia|YO LO TENGO] Si tú también lo tienes, escribe yo lo tengo en los comentarios.»
  2. En el CIERRE del tema {medio + 1}: una pregunta para opinar, sobre el orden o la sorpresa, nunca sobre los hechos.
     Ej.: «[COMENTA:debate|El de la muñeca, sin duda] ¿Cuál de estos te sorprendió más? Te leo.»
  3. Como última frase del FINAL: «[COMENTA:cierre|¡Uno de los sueños!] ¿Qué tema quieres en el próximo video?
     El más pedido sale pronto.»"""


def _prompt_guion(titulo: str, n: int, datos: str, preset: dict) -> str:
    p = preset["palabras_por_parte"]
    return f"""Eres el guionista del canal de YouTube «El Calvo Explica» (español latino neutro, tuteo, tono calmado y
curioso). Escribe el guion completo del video «{titulo}» con {n} temas.

ESTRUCTURA DEL VIDEO
- No hay introducción: la primera palabra del video es el nombre del primer tema. Sin transiciones entre temas.
- Orden: el tema más llamativo primero; el segundo más fuerte de último; los más flojos en el medio.
- Al final, un bloque FINAL de 5 segundos: «Y ahora ya sabes un poco más sobre <tema del video>. Si te gustó, suscríbete.»
{_instruccion_comentarios(n) if preset.get("llamados_comentar", True) else ""}

MOLDE DE CADA TEMA ({preset['palabras_tema'][0]} a {preset['palabras_tema'][1]} palabras)
1. NOMBRE ({p['nombre'][0]} a {p['nombre'][1]} palabras), solo el nombre con punto. Si el nombre técnico es raro, el cotidiano.
2. ESCENA ({p['escena'][0]} a {p['escena'][1]} palabras): segunda persona y presente. Empieza ubicando al espectador
   («Estás en…», «Vas a…»). 2 o 3 detalles concretos que se puedan dibujar. Termina en el momento raro o incómodo.
   Si se puede, invita a revisarse («junta…», «pasa el dedo…»).
3. BAUTIZO ({p['bautizo'][0]} a {p['bautizo'][1]} palabras): «Eso se llama X» o «Eso es X», más un dato corto.
4. EXPLICACIÓN ({p['explicacion'][0]} a {p['explicacion'][1]} palabras): presenta la idea como hipótesis con UNA de estas
   fórmulas: «La explicación más aceptada es…», «Se cree que…», «Lo más probable es que…», «La hipótesis principal
   es…», «Se piensa que…», «Una de las ideas más aceptadas es…». Ninguna fórmula en más de {preset['max_misma_formula']}
   temas. Un solo mecanismo, causa y efecto en 3 o 4 frases. Si algo lo empeora, una frase.
5. CIERRE ({p['cierre'][0]} a {p['cierre'][1]} palabras): una o dos frases cortas que le dan la vuelta a la escena y
   sorprenden o tranquilizan (si la parte sí sirve para algo, ese es el giro).

REGLAS
- Frases cortas (máximo {preset['max_palabras_frase']} palabras). Una idea por frase: cada frase será una imagen.
- Palabras concretas y dibujables. Números SIEMPRE en palabras.
- Prohibido: saludos, «en este video», «quédate hasta el final», «¿sabías que?», preguntas retóricas en cadena,
  listas («primero, segundo»), afirmar como hecho una hipótesis, consejos médicos, diagnósticos o tratamientos,
  nombrar personas reales (ni en nombres técnicos), películas, series, marcas o personajes con dueño, traducir o
  parafrasear guiones de otros canales.
- Verifica cada tema: que exista con ese nombre, que la explicación sea la más aceptada y no marginal, que no haya
  cifras inventadas. Si no estás seguro de un dato, quítalo.
{('- USA SOLO ESTOS DATOS (no agregues cifras):' + chr(10) + datos) if datos.strip() else ''}

FORMATO DE SALIDA (exacto, una frase por renglón; nada antes ni después):
NOMBRE
<nombre>.

ESCENA
<frase>
...
BAUTIZO
<frase>

EXPLICACIÓN
<frase>
...
CIERRE
<frase>

(… los {n} temas …)

FINAL
<frase>
<frase>

DUDAS
- <cada afirmación de la que no estés seguro, o que agregaste sin estar en los datos, con el tema>

EJEMPLO DE UN TEMA (tono y largo exactos):
{EJEMPLO_TEMA}
"""


def separar_dudas(texto: str) -> tuple[str, str]:
    partes = re.split(r"^\s*DUDAS\s*:?\s*$", texto, maxsplit=1, flags=re.M)
    return partes[0].strip() + "\n", (partes[1].strip() if len(partes) > 1 else "")


def escribir_guion(carpeta: Path, titulo: str, n: int, datos: str = "", ejecutar=None, avisar=print,
                   intentos: int = 3) -> dict:
    preset = C.cargar()
    carpeta.mkdir(parents=True, exist_ok=True)
    prompt = _prompt_guion(titulo, n, datos, preset)
    avisos: list[str] = []
    texto = dudas = ""
    for k in range(intentos):
        avisar(f"Claude está escribiendo el guion (intento {k + 1})…" if k == 0 else
               f"Corrigiendo el guion: {len(avisos)} detalle(s)…")
        respuesta = _claude(ejecutar, prompt if k == 0 else (
            prompt + "\n\nTU VERSIÓN ANTERIOR:\n" + texto + "\n\nCORRIGE ESTOS PROBLEMAS y devuelve el guion completo "
            "en el mismo formato (con DUDAS al final):\n- " + "\n- ".join(avisos)), carpeta)
        texto, dudas = separar_dudas(respuesta.strip().strip("`"))
        try:
            temas = G.leer(texto)
        except ValueError as ex:
            avisos = [str(ex)]
            continue
        avisos = G.revisar(temas, preset)
        if len(temas) != n:
            avisos.append(f"el guion tiene {len(temas)} temas y deben ser {n}")
        if not avisos:
            break
    (carpeta / "guion.txt").write_text(texto, encoding="utf-8")
    (carpeta / "dudas.md").write_text(dudas + "\n", encoding="utf-8")
    escribir_json(carpeta / "guion_info.json", {"titulo": titulo, "temas": n, "avisos": avisos})
    avisar("Guion listo" + (f" con {len(avisos)} aviso(s)" if avisos else ""))
    return {"guion": texto, "dudas": dudas, "avisos": avisos}


# ------------------------------------------------------------------ 2. escenas por tema

def _ejemplo_escenas() -> str:
    """El tema 1 del primer video (armado a mano) como modelo de lo que se espera."""
    datos = json.loads((EJEMPLOS / "tema1_muneca.json").read_text(encoding="utf-8"))
    escenas = [e for e in datos["escenas"] if e.get("tipo") != "cuadricula"]
    return json.dumps({"icono": {"pieza": "muneca", "estado": {"dedos": "pinza", "tendon": True}}, "escenas": escenas},
                      ensure_ascii=False)


def frases_del_tema(tema: dict) -> list[tuple[str, str]]:
    """(parte, frase) en orden, sin el nombre (el nombre va en la cuadrícula)."""
    return [(p, f) for p in ("escena", "bautizo", "explicacion", "cierre") for f in tema[p]]


def _prompt_escenas(tema: dict, k: int, n: int) -> str:
    frases = frases_del_tema(tema)
    lista = "\n".join(f"{i + 1}. [{TIPO_DE_PARTE[p]}] {f}" for i, (p, f) in enumerate(frases))
    return f"""Eres el animador del canal «El Calvo Explica». Video 1920x1080, fondo blanco, todo dibujado por código con
piezas de este catálogo (no hay otras; no inventes piezas):
{texto_catalogo()}

MOVIMIENTOS: {MOVIMIENTOS}

Arma las escenas del tema {k + 1} de {n}: «{' '.join(tema['nombre'])}». UNA escena por frase, en el mismo orden
({len(frases)} escenas). Tipos: ilustracion (la escena en segunda persona: el personaje viviendo la situación o el
objeto de cerca), personaje (bautizo: el Calvo con pose «tablero» a la izquierda (430,990) y la pieza «tablero» en
(1180,480) tamaño 1.45 con el nombre encima en «titulo_tema» y un texto rojo; cierre: el Calvo reaccionando),
codigo (la explicación: diagramas con íconos, flechas, corchetes y óvalos rojos, textos con palabras clave en rojo).

REGLAS (las más importantes primero)
- Cada elemento entra con «palabra»: una palabra (o dos seguidas) que la voz dice EN ESA FRASE, escrita igual.
- Algo nuevo aparece o cambia cada 1,5 segundos como máximo (la voz dice ~3,5 palabras por segundo): en frases largas
  agrega elementos o movimientos (cambiar_pose, temblor, dibujar) en palabras del medio y del final.
- Máximo 4 elementos en pantalla. Textos de máximo ~22 caracteres, nada que se salga de la pantalla ni tape la cara.
- Continuidad: si la siguiente escena sigue con el mismo objeto, repítelo con "ya_estaba": true en la misma posición
  y cambia solo lo nuevo (cambiar_pose).
- Personaje: tamaño 1.15, pies en y≈990; si va a la izquierda x≈640, el resto a la derecha x≈1330.
- Empujón de cámara («empujon»: [{{"palabra": "...", "foco": [x, y]}}]) en la palabra clave de la explicación y del bautizo.
- «temblor» de pantalla ([{{"palabra": "..."}}]) solo en golpes o sustos.
- Ilustra lo que dice la frase, no algo genérico. Pantalla limpia: mucho blanco.
- «fondo» (solo escenas ilustracion donde el personaje vive la situación en un lugar): {texto_fondos()}.
  Los dibujos del fondo son pálidos y grises; el piso queda en y≈940 (pies del personaje en y≈990 se ven bien).
  Si la escena es un objeto de cerca (mano, ojo, oreja…), deja «blanco». Si dos escenas seguidas pasan en el mismo
  lugar, repite el mismo fondo. Con «blanco», Xandart pone sola el lugar de fondo de todo el tema (y en las escenas
  codigo ese lugar muy pálido): solo elige un fondo cuando la frase pasa en un lugar distinto.

Devuelve SOLO un JSON:
{{"icono": {{"pieza": ..., "estado": {{...}}}}  ← el dibujo del tema para su círculo en la cuadrícula,
 "escenas": [{{"tipo": ..., "fondo": "blanco", "elementos": [{{"id", "pieza", "estado", "posicion": [x, y], "tamano", "palabra",
   "movimiento": [...], "retraso", "rotacion", "ya_estaba"}}], "temblor": [...], "empujon": [...]}}, ...]}}

FRASES:
{lista}

EJEMPLO (otro tema, armado a mano y aprobado por el dueño; imita su nivel y su ritmo):
{_ejemplo_escenas()}
"""


def _palabras_de_frase(frase: str) -> list[str]:
    return [E.normalizar(w) for w in frase.split() if E.normalizar(w)]


def _ancla_en(ancla: str, frase: str) -> bool:
    objetivo = [E.normalizar(x) for x in str(ancla).split() if E.normalizar(x)]
    ws = _palabras_de_frase(frase)
    return bool(objetivo) and any(ws[i:i + len(objetivo)] == objetivo for i in range(len(ws) - len(objetivo) + 1))


def _fondo_valido(fondo, tipo: str) -> str:
    """Solo las ilustraciones llevan lugar de fondo; un nombre que no existe queda en blanco."""
    return fondo if tipo == "ilustracion" and fondo in FONDOS_ESCENA else "blanco"


def limpiar_escena(crudo: dict, frase: str, tipo: str, fondo: str, notas: list[str]) -> dict:
    """Revisa y arregla UNA escena que armó Claude para una frase: piezas que existen, palabras que sí
    dice la voz, movimientos válidos, posiciones dentro de la pantalla, textos que quepan y máximo 4."""
    ws = frase.split()
    esc = {"tipo": tipo, "palabra_inicio": " ".join(ws[:2]), "fondo": fondo,
           "temblor": [m for m in crudo.get("temblor") or [] if _ancla_en(m.get("palabra", ""), frase)],
           "empujon": [m for m in crudo.get("empujon") or [] if _ancla_en(m.get("palabra", ""), frase)],
           "elementos": crudo.get("elementos") or []}
    buenos = []
    for el in esc["elementos"]:
        if el.get("pieza") not in PIEZAS:
            notas.append(f"pieza que no existe «{el.get('pieza')}» en «{frase[:40]}»: va como texto")
            el = {**el, "pieza": "texto", "estado": {"texto": str(el.get("id", ""))[:20]}}
        el.setdefault("id", f"e{len(buenos)}")
        el["estado"] = dict(el.get("estado") or {})
        if el.get("palabra") and not _ancla_en(el["palabra"], frase):
            notas.append(f"«{el['palabra']}» no está en la frase: entra con el corte")
            el.pop("palabra")
        movs = el.get("movimiento")
        movs = [movs] if isinstance(movs, (str, dict)) else list(movs or (["aparecer"] if not el.get("ya_estaba") else []))
        limpios = []
        for m in movs:
            m = {"tipo": m} if isinstance(m, str) else dict(m)
            if m.get("tipo") not in E.TIPOS_MOVIMIENTO:
                continue
            if m.get("palabra") and not _ancla_en(m["palabra"], frase):
                m.pop("palabra")
            limpios.append(m)
        el["movimiento"] = limpios
        x, y = (list(el.get("posicion") or [960, 540]) + [540])[:2]
        el["posicion"] = [min(1840, max(80, float(x))), min(1060, max(60, float(y)))]
        el["tamano"] = float(el.get("tamano") or 1.0)
        if el["pieza"] in ("texto", "titulo_tema", "rotulo"):         # que el texto quepa en pantalla
            alto = {"texto": 72, "titulo_tema": 110, "rotulo": 92}[el["pieza"]]
            ancho = ancho_texto(str(el["estado"].get("texto", "")).upper(), alto) * el["tamano"]
            maximo = 2 * min(el["posicion"][0], W - el["posicion"][0]) - 40
            if ancho > maximo:
                el["tamano"] = round(el["tamano"] * maximo / ancho, 3)
        if el["pieza"] != "imagen":                                     # la imagen se revisa al dibujar
            try:
                dibujar(el["pieza"], el["estado"])
            except Exception as ex:  # noqa: BLE001 — un estado raro: se deja la pieza sin estado
                notas.append(f"estado raro en {el['pieza']}: {ex}")
                el["estado"] = {}
        buenos.append(el)
    if len([e for e in buenos if not e.get("sale")]) > E.MAX_EN_PANTALLA:
        notas.append(f"más de {E.MAX_EN_PANTALLA} elementos en «{frase[:40]}»: se dejan los primeros")
        buenos = buenos[:E.MAX_EN_PANTALLA]
    esc["elementos"] = buenos
    return esc


def validar(respuesta: dict, tema: dict) -> tuple[list[dict], dict, list[str]]:
    """Revisa y arregla lo que Claude devolvió. Devuelve (escenas, icono, notas)."""
    frases = frases_del_tema(tema)
    escenas = list(respuesta.get("escenas") or [])
    notas: list[str] = []
    if len(escenas) != len(frases):
        raise ValueError(f"vinieron {len(escenas)} escenas para {len(frases)} frases")
    salida = []
    for (parte, frase), esc in zip(frases, escenas):
        tipo = esc.get("tipo") or TIPO_DE_PARTE[parte]
        salida.append(limpiar_escena(esc, frase, tipo, _fondo_valido(esc.get("fondo"), tipo), notas))
    icono = respuesta.get("icono") or {"pieza": "personaje", "estado": {"pose": "pensando", "gesto": "pensativo"}}
    if icono.get("pieza") not in PIEZAS:
        icono = {"pieza": "personaje", "estado": {"pose": "pensando", "gesto": "pensativo"}}
    return salida, icono, notas


def hoja_de_cuadros(escenas: list[dict], tema: dict, destino: Path) -> Path:
    """Un cuadro por escena (al final de cada una) con tiempos estimados: lo que Claude mira para corregir."""
    import cv2
    import numpy as np

    from ..calma.render import cuadro_en

    datos = {"video": {"fps": 30, "ritmo": float(C.cargar()["ritmo"])},
             "escenas": json.loads(json.dumps(escenas))}
    texto = "\n".join(f for _, f in frases_del_tema(tema))
    E.fijar_tiempos(datos, *E.tiempos_estimados(texto, 3.6))
    ims = []
    for i, e in enumerate(datos["escenas"], 1):
        im = cv2.resize(cuadro_en(datos, e["fin"] - 0.05), (480, 270), interpolation=cv2.INTER_AREA)
        cv2.rectangle(im, (0, 0), (479, 269), (160, 160, 160), 1)
        cv2.putText(im, str(i), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
        ims.append(im)
    while len(ims) % 4:
        ims.append(np.full_like(ims[0], 255))
    destino.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(destino), np.vstack([np.hstack(ims[i:i + 4]) for i in range(0, len(ims), 4)]))
    return destino


def _prompt_revision(tema: dict, escenas: list[dict], hoja: str) -> str:
    frases = frases_del_tema(tema)
    lista = "\n".join(f"{i + 1}. {f}" for i, (_, f) in enumerate(frases))
    return f"""Mira con la herramienta Read la imagen «{hoja}»: es la hoja de cuadros del tema «{' '.join(tema['nombre'])}»
(un cuadro por escena, numerados; cada cuadro es el final de su escena). Revísala como un editor exigente:
- ¿Algo se sale de la pantalla, se encima, tapa la cara del personaje o queda ilegible?
- ¿Cada escena ilustra lo que dice su frase? ¿Hay escenas pobres o vacías?
- ¿Se repite demasiado lo mismo? ¿Falta una palabra clave en rojo donde ayuda?
Frases:
{lista}

Escenas actuales (JSON):
{json.dumps({"escenas": escenas}, ensure_ascii=False)}

Catálogo de piezas (solo estas):
{texto_catalogo()}

Si todo está bien responde SOLO {{"ok": true}}. Si no, responde SOLO el JSON completo corregido
{{"escenas": [...]}} (misma cantidad de escenas, mismas reglas).
"""


def _huella(tema: dict) -> str:
    import hashlib

    return hashlib.sha1(json.dumps(frases_del_tema(tema), ensure_ascii=False).encode()).hexdigest()[:12]


def motivos_revision(escenas: list[dict], notas: list[str]) -> list[str]:
    """Lo que el sistema ve mal sin gastar Claude: si no hay nada, el tema no se revisa con la imagen (17-10)."""
    motivos = [n for n in notas if not n.startswith("revisión")]
    for i, e in enumerate(escenas, 1):
        if e.get("tipo") in ("ilustracion", "codigo") and len(e.get("elementos") or []) < 2 and not e.get("google"):
            motivos.append(f"la escena {i} se ve pobre ({len(e.get('elementos') or [])} elemento)")
        textos = [el for el in e.get("elementos") or [] if el.get("pieza") in ("texto", "titulo_tema", "rotulo")]
        if any(float(el.get("tamano", 1)) < 0.55 for el in textos):
            motivos.append(f"en la escena {i} un texto quedó muy chiquito")
    return motivos


def armar_tema(tema: dict, k: int, n: int, carpeta: Path, ejecutar=None, avisar=print, revisar: bool = True) -> dict:
    from ..claude_cli import extraer_json

    nombre = " ".join(tema["nombre"])
    hecho = carpeta / "revision" / f"tema_{k + 1:02d}.json"
    if hecho.exists():                      # si se cortó a mitad, lo ya armado no se vuelve a pedir a Claude
        previo = leer_json(hecho)
        if previo.get("nombre") == nombre and previo.get("frases") == _huella(tema):
            avisar(f"  tema {k + 1}: ya estaba armado")
            return {"icono": previo["icono"], "escenas": previo["escenas"], "notas": previo["notas"]}
    ultimo_error = ""
    for intento in range(3):
        prompt = _prompt_escenas(tema, k, n) + (f"\n\nOJO, tu respuesta anterior falló: {ultimo_error}" if ultimo_error else "")
        try:
            respuesta = extraer_json(_claude(ejecutar, prompt, carpeta, liviano=True))
            escenas, icono, notas = validar(respuesta, tema)
            break
        except (ValueError, json.JSONDecodeError) as ex:
            ultimo_error = str(ex)
            avisar(f"  tema {k + 1}: reintento ({ex})")
    else:
        raise RuntimeError(f"No se pudieron armar las escenas de «{nombre}»: {ultimo_error}")
    hoja = hoja_de_cuadros(escenas, tema, carpeta / "revision" / f"tema_{k + 1:02d}.png")
    motivos = motivos_revision(escenas, notas) if C.cargar().get("revision") == "si_hace_falta" else ["siempre"]
    if revisar and motivos:
        avisar(f"  tema {k + 1}: Claude está revisando su hoja de cuadros ({'; '.join(motivos)[:120]})…")
        try:
            r = extraer_json(_claude(ejecutar, _prompt_revision(tema, escenas, str(hoja.relative_to(carpeta)))
                                     + ("" if motivos == ["siempre"] else
                                        "\nOJO en especial con esto que vio el sistema:\n- " + "\n- ".join(motivos)),
                                     carpeta, herramientas=["Read"], liviano=True))
            if not r.get("ok") and r.get("escenas"):
                escenas, _, notas2 = validar({"escenas": r["escenas"], "icono": icono}, tema)
                notas += notas2
                hoja = hoja_de_cuadros(escenas, tema, carpeta / "revision" / f"tema_{k + 1:02d}.png")
        except (ValueError, json.JSONDecodeError) as ex:     # la revisión es una mejora: si falla, queda lo de antes
            notas.append(f"revisión sin cambios: {ex}")
    escribir_json(carpeta / "revision" / f"tema_{k + 1:02d}.json",
                  {"nombre": nombre, "frases": _huella(tema), "icono": icono, "escenas": escenas, "notas": notas})
    avisar(f"  tema {k + 1} listo: {nombre}")
    return {"icono": icono, "escenas": escenas, "notas": notas}


def escena_final(temas: list[dict]) -> dict | None:
    final = temas[-1].get("final") or []
    if not final:
        return None
    ws = final[0].split()
    clave = next((w.strip(".,") for w in final[-1].split() if E.normalizar(w).startswith("suscrib")), None)
    elementos = [{"id": "yo", "pieza": "personaje", "estado": {"pose": "senalando_contento", "gesto": "contento"},
                  "posicion": [640, 990], "tamano": 1.15, "movimiento": ["aparecer"], "palabra": ws[1] if len(ws) > 1 else ws[0]},
                 {"id": "t", "pieza": "texto", "estado": {"texto": "ya sabes un poco más"}, "posicion": [1330, 300],
                  "tamano": 0.9, "movimiento": ["aparecer"], "palabra": "sabes"}]
    if clave:
        elementos.append({"id": "r", "pieza": "rotulo", "estado": {"texto": "SUSCRÍBETE", "color": "rojo"},
                          "posicion": [1330, 560], "tamano": 1.2, "movimiento": ["aparecer"], "palabra": clave})
    return {"tipo": "personaje", "palabra_inicio": " ".join(ws[:2]), "fondo": "blanco", "temblor": [],
            "empujon": [{"palabra": clave, "foco": [1330, 560]}] if clave else [], "elementos": elementos}


def armar_escenas(carpeta: Path, ejecutar=None, avisar=print, revisar: bool = True, a_la_vez: int = 3) -> dict:
    """Escenas de todo el video (escenas.json) a partir de guion.txt."""
    temas = G.leer((carpeta / "guion.txt").read_text(encoding="utf-8"))
    n = len(temas)
    avisar(f"Armando las escenas de {n} temas con Claude ({a_la_vez} a la vez)…")
    with ThreadPoolExecutor(max_workers=max(1, a_la_vez)) as grupo:
        hechos = list(grupo.map(lambda kt: armar_tema(kt[1], kt[0], n, carpeta, ejecutar, avisar, revisar),
                                enumerate(temas)))
    cuad = [{"etiqueta": " ".join(t["nombre"]).rstrip("."), "icono": h["icono"]} for t, h in zip(temas, hechos)]
    escenas = []
    candidatas = []                     # escenas de la historia que pueden ir con ilustración de Google
    for k, (t, h) in enumerate(zip(temas, hechos)):
        ws = " ".join(t["nombre"]).rstrip(".").split()
        rojo = max(ws, key=len).upper()
        escenas.append(cuadricula(cuad, k, ws[0], ws[-1], " ".join(ws), rojo))
        escenas += h["escenas"]
        _marcar_comentarios(t, zip([f for _, f in frases_del_tema(t)], h["escenas"]))
        for (parte, frase), esc in zip(frases_del_tema(t), h["escenas"]):
            if parte == "escena" and esc.get("tipo") == "ilustracion":
                candidatas.append((esc, frase, " ".join(t["nombre"]).rstrip(".")))
    marcar_google(candidatas)
    fin = escena_final(temas)
    if fin:
        _marcar_comentarios(temas[-1], [(f, fin) for f in temas[-1].get("final", [])])
        escenas.append(fin)
    for i, e in enumerate(escenas, 1):
        e["id"] = i
    datos = {"video": {"ancho": W, "alto": H, "fps": 30}, "escenas": escenas}
    E.fijar_tiempos(json.loads(json.dumps(datos)), *E.tiempos_estimados(G.texto_para_voz(temas), 3.6))   # comprobación
    escribir_json(carpeta / "escenas.json", datos)
    notas = [x for h in hechos for x in h["notas"]]
    escribir_json(carpeta / "escenas_info.json", {"temas": n, "escenas": len(escenas), "notas": notas})
    avisar(f"Escenas listas: {len(escenas)} ({len(notas)} nota(s))")
    return datos


def _marcar_comentarios(tema: dict, pares) -> None:
    """La escena de un llamado a comentar lleva el cuadro de comentario animado (calma.render lo dibuja)."""
    from ..llamados import EJEMPLOS_POR_DEFECTO

    por_frase = {c["frase"]: c for c in tema.get("comentarios", [])}
    for frase, esc in pares:
        c = por_frase.get(frase)
        if c:
            esc["comentario"] = {"tipo": c["tipo"], "texto": c["texto"] or EJEMPLOS_POR_DEFECTO.get(c["tipo"], "¡Yo!")}


def marcar_google(candidatas: list[tuple[dict, str, str]], proporcion: float | None = None) -> int:
    """Marca 1 de cada N escenas de la historia para dibujarlas con Google (repartidas en todo el video). La imagen
    se paga al hacer el video (explica.ilustraciones.aplicar), no aquí."""
    preset = C.cargar()
    proporcion = float(preset.get("proporcion_google", 0)) if proporcion is None else proporcion
    if proporcion <= 0 or not candidatas:
        return 0
    cada = max(1, round(1 / proporcion))
    n = 0
    for i, (esc, frase, nombre) in enumerate(candidatas):
        if i % cada == cada // 2 and n < int(preset.get("max_ilustraciones", 60)):
            esc["google"] = {"descripcion": f"Tema del video: «{nombre}». La voz dice: «{frase}». Dibuja al personaje "
                                            "viviendo exactamente ese momento, en segunda persona (es el espectador)."}
            n += 1
    return n


def estado_video(carpeta: Path) -> dict:
    hojas = sorted(p.name for p in (carpeta / "revision").glob("tema_*.png")) if (carpeta / "revision").exists() else []
    return {"guion": (carpeta / "guion.txt").read_text(encoding="utf-8") if (carpeta / "guion.txt").exists() else None,
            "dudas": (carpeta / "dudas.md").read_text(encoding="utf-8") if (carpeta / "dudas.md").exists() else None,
            "guion_info": leer_json(carpeta / "guion_info.json") if (carpeta / "guion_info.json").exists() else None,
            "escenas": (carpeta / "escenas.json").exists(), "hojas": hojas,
            "escenas_info": leer_json(carpeta / "escenas_info.json") if (carpeta / "escenas_info.json").exists() else None,
            "informe": leer_json(carpeta / "informe.json") if (carpeta / "informe.json").exists() else None,
            "video": (carpeta / "final.mp4").exists()}
