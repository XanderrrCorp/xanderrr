"""Guionista y director visual (sección 5.1, 5.2, 14 y 15) con la suscripción de Claude.

De un tema, un giro y un villano sale el guion completo en formato escala, ya
dividido en escenas con su intención, su tipo de imagen (solo tipos del estilo)
y la descripción de la imagen en inglés. De ahí se arman `escenas.json` v2,
`guion.md` y `direccion.json` (revelación del villano y textos en pantalla).
Después de generar las imágenes, `ubicar_villano` mira las escenas previas a la
revelación y devuelve las zonas a pixelar.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import claude_cli
from .config import escribir_json, leer_json
from .esquemas import INTENCIONES, EscenasV2, Estilo

def _palabras_por_segundo() -> float:
    """Ritmo real de la voz (depende de la velocidad configurada), de config/costos.json."""
    from .config import ConfigCostos

    return float(ConfigCostos.cargar().consumo.get("palabras_por_segundo_voz", 2.9))


PALABRAS_POR_SEGUNDO = _palabras_por_segundo()


@dataclass
class Encargo:
    tema: str
    giro: str = ""
    villano: str = ""
    minutos: float = 9.0
    notas: str = ""
    formula: str = "escala_peligro"          # la estructura del guion (dato del catálogo o del espacio)


def cargar_formula(clave: str = "escala_peligro") -> dict:
    """La fórmula del guion es un dato (catálogo público o del espacio), no texto en el código."""
    from .config import leer_json
    from .plataforma import contexto

    ruta = contexto.buscar("formulas", clave, "formula.json")
    if ruta is None:
        raise FileNotFoundError(f"no existe la fórmula de guion «{clave}»")
    return leer_json(ruta)


def instruccion(encargo: Encargo, estilo: Estilo, niveles_fijos: list[dict] | None = None,
                formula: dict | None = None, narrador: str | None = None) -> str:
    formula = formula or cargar_formula(encargo.formula or "escala_peligro")
    palabras = int(encargo.minutos * 60 * PALABRAS_POR_SEGUNDO)
    if not formula.get("usa_niveles", True):
        return _instruccion_sin_niveles(encargo, formula, palabras, narrador)
    fijos = ""
    if niveles_fijos:
        lista = "\n".join(f"  {n['numero']}. {n['nombre']}{' (VILLANO, último)' if n.get('villano') else ''}"
                          for n in sorted(niveles_fijos, key=lambda x: x["numero"]))
        fijos = ("\nNIVELES OBLIGATORIOS (usa EXACTAMENTE estos animales, con estos nombres y en este orden; "
                 f"ni uno más ni uno menos):\n{lista}\n")
    presentacion = formula["presentacion"]
    estructura = formula["estructura"].replace("<<narrador>>", narrador or formula.get("narrador_por_defecto", "el narrador"))
    return f"""{presentacion}

== ENCARGO ==
Tema: {encargo.tema}
Giro: {encargo.giro or "(propón uno fuerte y verdadero)"}
Villano (el más peligroso, último nivel): {encargo.villano or "(elige el más peligroso y verdadero)"}{fijos}
Duración: unos {encargo.minutos:g} minutos de voz = entre {int(palabras * 0.93)} y {int(palabras * 1.07)} palabras en total.
{("Notas del dueño: " + encargo.notas) if encargo.notas else ""}

{estructura}
== FORMATO DE SALIDA (texto, no JSON) ==
Responde SOLO con esto, sin nada antes ni después:
TITULO: <título del video, gancho de YouTube>
NIVEL: 1 | <nombre del animal> | <english description of the animal for a card: species, colors, pose, magnified, whole body visible and centered> | no
NIVEL: 2 | ... | ... | no
(uno por nivel, en orden; en el último, el villano, pon «si» al final)
SECCION: Gancho
<una escena por línea: solo lo que dice la voz>
<otra escena>
SECCION: Nivel 1 · <nombre>
<escena que presenta al animal por su nombre>
<escenas del nivel, una por línea>
... (una SECCION por nivel)
SECCION: Cierre
<escenas del cierre>"""


def _instruccion_sin_niveles(encargo: Encargo, formula: dict, palabras: int, narrador: str | None) -> str:
    estructura = formula["estructura"].replace("<<narrador>>", narrador or formula.get("narrador_por_defecto", "el narrador"))
    return f"""{formula["presentacion"]}

== ENCARGO ==
Tema: {encargo.tema}
{("Enfoque o giro: " + encargo.giro) if encargo.giro else ""}
Duración: unos {encargo.minutos:g} minutos de voz = entre {int(palabras * 0.93)} y {int(palabras * 1.07)} palabras en total.
{("Notas del dueño: " + encargo.notas) if encargo.notas else ""}

{estructura}
== FORMATO DE SALIDA (texto, no JSON) ==
Responde SOLO con esto, sin nada antes ni después:
{formula["formato_salida"]}"""


def leer_historia(texto: str, usa_niveles: bool = True) -> dict:
    """Lee la respuesta de la fase 1 (texto con TITULO / NIVEL / SECCION)."""
    import re

    titulo, niveles, secciones = None, [], []
    for linea in (texto or "").splitlines():
        linea = linea.strip().strip("`").strip()
        if not linea or linea.startswith("("):
            continue
        m = re.match(r"(?i)^t[íi]tulo\s*:\s*(.+)$", linea)
        if m:
            titulo = m.group(1).strip()
            continue
        m = re.match(r"(?i)^nivel\s*:\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(s[ií]|no)\s*$", linea)
        if m:
            niveles.append({"numero": int(m.group(1)), "nombre": m.group(2), "sujeto": m.group(3),
                            "villano": m.group(4).lower().startswith("s")})
            continue
        m = re.match(r"(?i)^secci[oó]n\s*:\s*(.+)$", linea)
        if m:
            secciones.append((m.group(1).strip(), []))
            continue
        if secciones and not re.search(r"(?i)pixel", linea):    # lo pixelado es visual, la voz no lo dice
            secciones[-1][1].append(linea)
    secciones = [(n, ls) for n, ls in secciones if ls]
    if not usa_niveles and titulo and len(secciones) >= 3:
        return {"titulo": titulo, "niveles": [], "secciones": secciones}
    if not titulo or len(niveles) < 4 or len(niveles) > 8 or len(secciones) < 3:
        raise ValueError(f"historia incompleta: título={bool(titulo)}, niveles={len(niveles)}, secciones={len(secciones)}")
    return {"titulo": titulo, "niveles": niveles, "secciones": secciones}


def _niveles_coinciden(historia: dict, fijos: list[dict]) -> None:
    """Con niveles fijos, la historia debe tener una sección por cada uno, con su nombre."""
    import unicodedata

    def norm(t):
        return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if not unicodedata.combining(c))

    nombres = [norm(n) for n, _ in historia["secciones"]]
    faltan = [n["nombre"] for n in fijos
              if not any(x.startswith(f"nivel {n['numero']}") and norm(n["nombre"]).split()[0] in x for x in nombres)]
    if faltan or len([x for x in nombres if x.startswith("nivel ")]) != len(fijos):
        raise ValueError(f"los niveles no son los pedidos (faltan o sobran): {', '.join(faltan) or 'hay niveles de más'}")


def instruccion_detalles(historia: dict, k: int, estilo: Estilo, catalogo: list[dict] | None = None) -> str:
    """Fase 2, por sección: intención, imagen y textos de cada escena (la narración ya está)."""
    nombre, lineas = historia["secciones"][k]
    tipos = "\n".join(f"  - {t.id}: {t.descripcion}" for t in estilo.tipos_de_escena)
    ejemplo = estilo.tipos_de_escena[0].id
    solo_mascota = next((t.id for t in estilo.tipos_de_escena if "{personaje}" in t.plantilla_prompt
                         and "{bloque_estilo}" not in t.plantilla_prompt), None)
    nota_mascota = (f" En escenas de tipo {solo_mascota} describe solo su pose y su cara." if solo_mascota else "")
    con_niveles = bool(historia["niveles"])
    villano = next((n for n in historia["niveles"] if n["villano"]), historia["niveles"][-1] if con_niveles else None)
    niveles = "\n".join(f"  {n['numero']}. {n['nombre']}{' (VILLANO)' if n['villano'] else ''}" for n in historia["niveles"])
    numeradas = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(lineas))
    es_gancho = k == 0
    nivel = next((n for n in historia["niveles"] if nombre.lower().startswith(f"nivel {n['numero']} ")
                  or nombre.lower().startswith(f"nivel {n['numero']}·")), None)
    especiales = []
    especiales.append('- Si la escena es parte de una anécdota del narrador (habla en primera persona: «yo», «me», '
                      '«mi amigo»), usa pov_personaje para lo que él vio con sus ojos, o escena_cartoon_completa con él '
                      'en ese lugar reaccionando (por ejemplo congelado del susto en una calle).')
    if es_gancho and con_niveles:
        especiales.append('- Esta es la sección del GANCHO: la escena que presenta la lista de niveles lleva '
                          '"accion": "componer" (el sistema muestra la tira). Si una escena muestra al villano, pon '
                          '"muestra_villano": true: el sistema lo oculta en pantalla hasta su revelación (la narración '
                          'nunca menciona que está pixelado u oculto).')
    if nivel:
        especiales.append(f'- Es la sección del nivel {nivel["numero"]}: la escena 1 (la que lo presenta por su nombre) lleva "accion": "reusar", '
                          f'"reusar": "nivel:{nivel["numero"]}" e intención transicion_de_seccion.')
        if nivel["villano"]:
            especiales.append('- Es el VILLANO: marca "revelacion_villano": true en la escena donde se ve por primera vez '
                              'su aspecto (normalmente justo después de la escena que lo presenta).')
    # el tipo «en primera persona» del estilo (el que pide ver por los ojos del personaje), si tiene
    pov = next((t.id for t in estilo.tipos_de_escena if "first-person" in t.plantilla_prompt.lower()), None)
    if estilo.con_personaje:
        # (03-10) como la competencia: la cara del personaje cambia con lo que dice la voz
        especiales.append('- Cuando aparece "the cartoon man", la descripción dice SIEMPRE su expresión según la emoción de '
                          'esa frase, nunca una cara neutra: susto (eyes wide open, sweat drops, hand on his head), '
                          'sorpresa (raised eyebrows, mouth wide open), asco (tongue out, squinting), alegría o alivio '
                          '(big smile), duda (hand on his chin, one eyebrow raised), alerta (pointing at the animal, '
                          'worried face). Si señala algo, que señale hacia el animal o el dato.')
    if pov:
        especiales.append('- Si la voz describe una ACCIÓN con el animal o el objeto («si lo tocas», «si lo aplastas», '
                          '«si lo agarras», «al quitarlo de la piel»), '
                          f'muéstrala en primera persona con {pov}: '
                          'solo se ven las manos del personaje haciendo esa acción. Si la misma acción sigue en la '
                          'escena siguiente, la primera muestra la mano acercándose y la segunda la mano ya encima '
                          '(mismo lugar y encuadre), como dos momentos seguidos. Sin heridas ni nada gráfico.')
    # tipos especiales que el estilo pueda tener (se reconocen por su plantilla, no por su nombre)
    pizarra = next((t.id for t in estilo.tipos_de_escena if "chalk" in t.plantilla_prompt.lower()), None)
    rayos = next((t.id for t in estilo.tipos_de_escena if "x-ray" in t.plantilla_prompt.lower()), None)
    if pizarra:
        especiales.append(f'- Cuando la voz explica CÓMO funciona algo o qué efecto causa (lo que pasa en la piel, cómo '
                          f'actúa un veneno, las partes de algo), usa {pizarra} (como mucho 1 por sección): la '
                          f'descripción es un dibujo simple de tiza. Ponle "rotulos": 2 o 3 palabras cortas en español '
                          f'que nombran partes del dibujo («Burbujas», «Irritación»); salen escritas a mano con '
                          f'flechitas. En las demás escenas "rotulos" es null.')
    if rayos:
        especiales.append(f'- Si la voz habla de un daño DENTRO del cuerpo (un órgano, los huesos, la sangre, un veneno '
                          f'que ataca por dentro), usa {rayos}: se ve por dentro como radiografía, sin heridas ni sangre.')
    if estilo.con_personaje:
        especiales.append('- Mini historias: cuando la voz cuenta lo que le pasa a alguien en el tiempo («estás tranquilo '
                          'en tu patio… y horas después…»), muéstralo con "the cartoon man" viviendo esa historia en '
                          'escenas completas seguidas (antes tranquilo, después asustado). En la escena donde el tiempo '
                          'salta, pon "salto_tiempo": un rótulo corto («Unas horas después», «Al día siguiente»); en las '
                          'demás, null.')
    especiales = "\n".join(especiales)
    bloque_catalogo = ""
    if catalogo:
        filas = "\n".join(f"  - {c['id']}: {c['descripcion'][:140]}" for c in catalogo)
        bloque_catalogo = f"""
IMÁGENES YA HECHAS (gratis): úsala con "accion": "reusar", "reusar": "imagen:<id>" SOLO si muestra
exactamente lo que dice la voz en esa escena (el mismo animal y la misma acción o situación). Si solo se
parece, o hay duda, pide imagen nueva ("generar"): una imagen que no cuadra con la voz se nota.
No pongas la misma imagen en dos escenas seguidas.
{filas}
"""
    nota_real = ("" if con_niveles else
                 '- "real": si la escena muestra algo REAL que se vería mejor con una foto o un video de verdad (un animal, '
                 'un lugar, un paisaje, un río, un fenómeno), la búsqueda corta en inglés para un banco de fotos '
                 '(«congo river rapids», «barn owl flying»); si es una idea, una comparación, una persona o algo '
                 'imaginado, null. Más o menos en una de cada tres escenas.\n')
    contexto = (f"""Niveles (de menos a más peligro):
{niveles}
El villano ({villano['nombre']}) no se muestra claramente antes de su revelación.
""" if con_niveles else "Es un documental de curiosidad: cada imagen muestra con claridad lo que explica la voz.\n")
    return f"""Eres el director visual de un video de YouTube en español: «{historia['titulo']}».
{contexto}
Sección «{nombre}». Estas son sus escenas (lo que dice la voz), numeradas:
{numeradas}

Para CADA escena, en orden, decide:
- "intencion": una de {", ".join(INTENCIONES)} (las preguntas al espectador son pregunta_al_espectador).
- "intensidad": 1 a 5.
- "accion": "generar" (imagen nueva), "reusar" o "componer". Alrededor del 70 % generan imagen; reusa con
  "reusar": "escena:<primeras palabras exactas de una escena anterior de esta sección>" solo cuando la voz
  vuelve sobre EXACTAMENTE lo mismo que ya se vio en esa escena.
- "tipo" (solo si generar), de esta lista del estilo «{estilo.nombre}»:
{tipos}
- "descripcion" (solo si generar) en INGLÉS: la imagen tiene que mostrar LO QUE DICE LA VOZ en esa escena,
  no una imagen genérica del tema. Si la voz nombra un animal, ese animal exacto por su nombre común en inglés
  y con su aspecto real (pelo, plumas, piel o escamas como los tiene la especie; nunca armaduras ni placas si
  el animal no las tiene). Si habla de personas (agricultores, cazadores, pescadores, niños, turistas…), se
  ven esas personas haciendo lo que dice la voz, con su ropa y su lugar (un agricultor en su cultivo, un
  cazador en el monte), usando un tipo de escena completa. Si habla de una acción, un dato o una situación
  (cazar, esconderse, un tamaño, un lugar), eso es lo que se ve. Concreto: sujeto, acción, lugar, luz. Nunca texto, letras, números ni letreros
  en la imagen. Nada de sangre ni heridas gráficas. Nunca termómetros, medidores
  ni barras de peligro: la escala de peligro 0–10 la pone el montaje a pantalla completa.
- "con_mascota": true si aparece el personaje fijo del canal ({(estilo.personaje_por_defecto or "la mascota")[:110]}…);
  en la descripción llámalo "the cartoon man".{nota_mascota}
{nota_real}- "palabra_clave": la palabra MÁS importante de esa escena, copiada tal cual (sustantivo o número en palabras).
- "texto_pantalla": solo en 1 o 2 escenas fuertes de la sección, un título corto de 2 a 6 palabras escrito
  normal, como lo diría una persona («Si lo ves, huye»); y "palabra": la palabra de la escena donde aparece.
  En las demás, null.
- "dato": en 1 o 2 escenas de la sección donde la voz afirma o niega algo concreto del sujeto (si muerde, si
  es venenoso, si se come, si es peligroso), {{"texto": "No muerde", "icono": "no"}}: texto de 1 a 3 palabras
  e icono "no" (✕ roja), "si" (✓ verde) o "alerta" (⚠). Se ve grande al lado del dibujo con una flecha.
  En las demás, null. Nunca en la misma escena que "texto_pantalla".
- "termino": si la voz dice un término técnico o raro que el espectador no conoce (el nombre de una toxina,
  de una sustancia o un nombre científico), cópialo tal cual como lo dice la voz; sale solo, grande, a
  pantalla completa. Como mucho en 1 escena de la sección; en las demás, null.
- "lugar": si la voz habla de un lugar o una época REAL concreta (el Coliseo romano, el desierto del Sahara,
  un hospital, la selva del Amazonas), una búsqueda corta en inglés para una foto de ese lugar («roman
  colosseum», «amazon rainforest»): sale desenfocada de fondo detrás del dibujo. Como mucho en 1 escena de la
  sección; en las demás, null.
{especiales}
{bloque_catalogo}
Responde SOLO un JSON: {{"escenas": [{{"n": 1, "intencion": "...", "intensidad": 3, "accion": "generar",
"tipo": "{ejemplo}", "descripcion": "...", "con_mascota": false, "palabra_clave": "...", "texto_pantalla": null,
"palabra": null, "dato": null, "termino": null, "lugar": null, "rotulos": null, "salto_tiempo": null}}, ...]}} con exactamente {len(lineas)} escenas."""


def _detalles(historia: dict, k: int, estilo: Estilo, carpeta: Path, ejecutar, avisar,
              catalogo: list[dict] | None = None) -> list[dict]:
    nombre, lineas = historia["secciones"][k]
    prompt = instruccion_detalles(historia, k, estilo, catalogo)
    error = ""
    for intento in range(2):
        texto, _ = ejecutar(prompt if not error else prompt + f"\n\nTu respuesta anterior falló: {error}. Corrígela.",
                            cwd=carpeta)
        try:
            datos = claude_cli.extraer_json(texto)
            lista = datos["escenas"] if isinstance(datos, dict) else datos
            por_n = {int(d["n"]): d for d in lista if isinstance(d, dict) and "n" in d}
            if len(por_n) < len(lineas):
                raise ValueError(f"faltan escenas: {len(por_n)} de {len(lineas)}")
            salida = []
            for i, narr in enumerate(lineas):
                d = {k2: v for k2, v in por_n[i + 1].items() if k2 != "n"}
                salida.append({"seccion": nombre, "narracion": narr, **d})
            return salida
        except (ValueError, KeyError, TypeError) as ex:
            error = str(ex)[:300]
            avisar(f"  sección «{nombre}»: intento {intento + 1} no válido ({error[:100]})")
    raise claude_cli.ErrorClaude(f"La sección «{nombre}» no quedó válida: {error}")


def _id_catalogo(texto: str, ids: set) -> str | None:
    """«img012», «012», «12» o «img12» → el id del catálogo que exista."""
    import re

    t = texto.strip().strip("«»\"' ")
    if t in ids:
        return t
    m = re.search(r"(\d+)", t)
    if m:
        cand = f"img{int(m.group(1)):03d}"
        if cand in ids:
            return cand
    return None


def _clave_en(clave, narracion: str) -> str | None:
    """La palabra clave solo si está tal cual en la narración (si no, se descarta)."""
    import re

    if not clave or not isinstance(clave, str):
        return None
    for w in re.findall(r"[\wáéíóúñü]+", narracion):
        if w.lower() == clave.strip().lower():
            return w
    return None


ACCIONES = ("generar", "reusar", "componer", "solo_edicion")


def _accion(e: dict) -> str:
    """La acción de la escena, aunque Claude la escriba pegada a la referencia («reusar:escena:Lo que…»):
    se separa y lo de después queda como «reusar». Algo irreconocible se dibuja (generar)."""
    crudo = str(e.get("accion") or "generar").strip()
    base = crudo.split(":", 1)[0].strip().lower()
    if base == "reusar" and ":" in crudo and not e.get("reusar"):
        e["reusar"] = crudo.split(":", 1)[1].strip()
    if base not in ACCIONES:
        base = "generar"
    if base == "generar" and not e.get("tipo") and e.get("reusar"):
        base = "reusar"
    e["accion"] = base
    return base


def a_escenas(datos: dict, estilo: Estilo, canal: str) -> tuple[dict, dict, str]:
    """JSON del guionista → (escenas.json v2, direccion.json, guion.md)."""
    niveles_in = sorted(datos["niveles"], key=lambda n: n["numero"])
    if niveles_in and not any(n.get("villano") for n in niveles_in):
        niveles_in[-1]["villano"] = True
    assets = [{"id": "mascota_base", "tipo": "personaje", "archivo": "assets/mascota_base.png",
               "quitar_fondo": True, "prompt": None}]
    niveles = []
    for n in niveles_in:
        aid = f"tira_{n['numero']}"
        assets.append({"id": aid, "tipo": "animal", "nombre": f"Nivel {n['numero']} · {n['nombre']}",
                       "archivo": f"assets/{aid}.png", "quitar_fondo": True, "prompt": n["sujeto"]})
        niveles.append({"numero": n["numero"], "nombre": n["nombre"], "asset": aid,
                        "villano": bool(n.get("villano"))})
    for img in datos.get("catalogo") or []:
        assets.append({"id": img["id"], "tipo": img.get("tipo") or "catalogo", "archivo": img["archivo"],
                       "quitar_fondo": bool(img.get("quitar_fondo")), "prompt": img.get("descripcion") or img["id"]})
    ids_catalogo = {img["id"] for img in datos.get("catalogo") or []}
    crudas = datos["escenas"]
    escenas, direccion = [], {"pixelar_pendiente": [], "textos": {}}
    t = 0.0
    for i, e in enumerate(crudas, 1):
        accion = _accion(e)
        vis = {"accion": accion, "tipo": e.get("tipo") if accion == "generar" else None,
               "archivo": f"imagenes/escena_{i:03d}.png" if accion == "generar" else None,
               "referencias": ["mascota_base"] if e.get("con_mascota") else [], "quitar_fondo": False}
        notas = ""
        if accion == "generar":
            if vis["tipo"] not in estilo.ids_tipos:
                raise ValueError(f"escena {i}: tipo '{vis['tipo']}' no existe en el estilo")
            vis["quitar_fondo"] = estilo.tipo(vis["tipo"]).quitar_fondo
            vis["prompt"] = e["descripcion"]
        elif accion == "reusar":
            ref = str(e.get("reusar", ""))
            if ref.startswith("nivel:"):
                vis["reusar_de"] = f"tira_{int(ref.split(':')[1])}"
            elif ref.startswith("imagen:") and _id_catalogo(ref.split(":", 1)[1], ids_catalogo):
                vis["reusar_de"] = _id_catalogo(ref.split(":", 1)[1], ids_catalogo)   # imagen ya pagada
            else:
                inicio = ref.split(":", 1)[-1].strip().lower()
                previas = [j for j, x in enumerate(crudas[:i - 1], 1)
                           if _accion(x) == "generar" and x["narracion"].lower().startswith(inicio[:40])]
                if previas:
                    vis["reusar_de"] = previas[0]
                else:
                    # referencia rara: se reusa la última imagen propia anterior en vez de fallar
                    anteriores = [j for j, x in enumerate(crudas[:i - 1], 1) if _accion(x) == "generar"]
                    if not anteriores:
                        raise ValueError(f"escena {i}: no encuentro la escena a reusar «{ref}»")
                    vis["reusar_de"] = anteriores[-1]
        else:
            notas = "Tira de niveles"
        intencion = e.get("intencion") if e.get("intencion") in INTENCIONES else "explicacion"
        escenas.append({"id": i, "seccion": e["seccion"], "narracion": e["narracion"].strip(),
                        "intencion": intencion, "intensidad": max(1, min(5, int(e.get("intensidad") or 3))),
                        "tiempo": {"estimado_inicio": round(t, 2),
                                   "estimado_duracion": round(max(1.5, len(e["narracion"].split()) / PALABRAS_POR_SEGUNDO), 2)},
                        "visual": vis, "notas_edicion": notas,
                        "palabra_clave": _clave_en(e.get("palabra_clave"), e["narracion"])})
        t += escenas[-1]["tiempo"]["estimado_duracion"]
        if e.get("revelacion_villano") and "villano_revelacion" not in direccion:
            direccion["villano_revelacion"] = i
        if e.get("muestra_villano") and accion == "generar" and estilo.ocultar_villano:
            direccion["pixelar_pendiente"].append(i)
        real = str(e.get("real") or "").strip()
        if real and not niveles_in and accion == "generar":
            direccion.setdefault("reales", {})[str(i)] = real[:60]
        if e.get("texto_pantalla"):
            direccion["textos"][str(i)] = {"texto": str(e["texto_pantalla"]).strip()[:48],
                                           "palabra": e.get("palabra") or ""}
        dato = e.get("dato") if isinstance(e.get("dato"), dict) else None
        if dato and str(dato.get("texto") or "").strip():
            icono = str(dato.get("icono") or "no").strip().lower()
            direccion.setdefault("datos", {})[str(i)] = {
                "texto": str(dato["texto"]).strip()[:28],
                "icono": icono if icono in ("si", "no", "alerta") else "no"}
        # el término técnico solo vale si la voz lo dice tal cual (una palabra o varias seguidas)
        crudo = str(e.get("termino") or "").strip().strip('"«»“”\'')
        if " " in crudo:
            termino = crudo if crudo.lower() in e["narracion"].lower() else None
        else:
            termino = _clave_en(crudo, e["narracion"]) if crudo else None
        if termino:
            direccion.setdefault("terminos", {})[str(i)] = termino[:32]
        lugar = str(e.get("lugar") or "").strip()
        if lugar and accion == "generar":
            direccion.setdefault("lugares", {})[str(i)] = lugar[:50]
        rotulos = e.get("rotulos") if isinstance(e.get("rotulos"), list) else []
        rotulos = [str(r).strip()[:18] for r in rotulos if str(r).strip()][:3]
        if rotulos:
            direccion.setdefault("rotulos", {})[str(i)] = rotulos
        salto = str(e.get("salto_tiempo") or "").strip()
        if salto:
            direccion.setdefault("saltos", {})[str(i)] = salto[:30]
    direccion["pixelar_pendiente"] = [i for i in direccion["pixelar_pendiente"]
                                      if i < direccion.get("villano_revelacion", 10 ** 6)]
    doc = {"version": 2, "video": datos.get("titulo") or "Sin título", "canal": canal, "estilo": estilo.id,
           "idioma": "es", "relacion_aspecto": "16:9", "assets": assets, "niveles": niveles, "escenas": escenas}
    EscenasV2.model_validate(doc)
    palabras = sum(len(e["narracion"].split()) for e in escenas)
    md, seccion = [f"# {doc['video']}\n\n*{palabras} palabras · unos {t / 60:.1f} minutos de voz*\n"], None
    for e in escenas:
        if e["seccion"] != seccion:
            md.append(f"\n## {e['seccion']}\n\n")
            seccion = e["seccion"]
        md.append(e["narracion"] + " ")
    if "villano_revelacion" not in direccion:
        villano = next((n for n in niveles if n["villano"]), None)
        if villano:
            entrada = next((e for e in escenas if e["visual"].get("reusar_de") == villano["asset"]), None)
            siguiente = next((e for e in escenas if entrada and e["id"] > entrada["id"]
                              and e["seccion"] == entrada["seccion"]), None)
            if siguiente:
                direccion["villano_revelacion"] = siguiente["id"]
    return doc, direccion, "".join(md).rstrip() + "\n"


def _velocidad() -> dict:
    from .config import leer_config

    return leer_config("proveedores.json").get("claude") or {}


def _con(ejecutar, modelo, pensamiento):
    """El mismo ejecutor con el modelo y el límite de razonamiento de cada paso (si los acepta)."""
    if ejecutar is not claude_cli.ejecutar:
        return ejecutar                      # en las pruebas se usa un Claude simulado
    import functools

    return functools.partial(claude_cli.ejecutar, modelo=modelo, pensamiento=pensamiento)


def escribir_guion(encargo: Encargo, estilo: Estilo, carpeta: Path, canal: str,
                   ejecutar=claude_cli.ejecutar, avisar=print, en_paralelo: int | None = None,
                   catalogo: list[dict] | None = None, niveles_fijos: list[dict] | None = None) -> dict:
    """Dos pasos para que ninguna respuesta sea enorme (y no pase del tiempo máximo):
    1) la historia en texto (título, niveles y lo que dice la voz, escena por escena);
    2) por sección, y varias a la vez, la intención, la imagen y los textos de cada escena."""
    from concurrent.futures import ThreadPoolExecutor

    v = _velocidad()
    en_paralelo = en_paralelo or int(v.get("secciones_en_paralelo", 8))
    base = ejecutar
    ejecutar = _con(base, v.get("modelo_historia"), v.get("pensamiento_historia_tokens"))
    ejecutar_detalles = _con(base, v.get("modelo_detalles"), v.get("pensamiento_detalles_tokens"))
    tolerancia = float(v.get("tolerancia_largo", 0.15))
    usa_niveles = cargar_formula(encargo.formula or "escala_peligro").get("usa_niveles", True)
    if not usa_niveles:
        niveles_fijos = None
    prompt = instruccion(encargo, estilo, niveles_fijos)
    error = ""
    borrador = carpeta / "_borrador_guion"
    borrador.mkdir(parents=True, exist_ok=True)
    historia = None
    if (borrador / "historia.json").exists():            # se retoma lo ya escrito
        historia = leer_json(borrador / "historia.json")
        historia["secciones"] = [tuple(x) for x in historia["secciones"]]
        avisar("Retomando la historia ya escrita…")
    else:
        avisar("Claude está escribiendo la historia…")
    for intento in range(0 if historia else 2):
        texto, sobre = ejecutar(prompt if not error else
                                prompt + f"\n\n== CORRIGE ==\nTu respuesta anterior falló: {error}. "
                                         "Devuelve la historia completa en el formato pedido.", cwd=carpeta)
        try:
            historia = leer_historia(texto, usa_niveles)
            if niveles_fijos:
                _niveles_coinciden(historia, niveles_fijos)
            break
        except ValueError as ex:
            error = str(ex)[:300]
            avisar(f"  historia: intento {intento + 1} no válido ({error[:120]})")
    else:
        if historia is None:
            raise claude_cli.ErrorClaude(f"La historia no quedó válida tras dos intentos: {error}")
    sobre = locals().get("sobre") or {}
    if niveles_fijos:
        # mismo tema que un video anterior: los niveles (y sus tarjetas ya hechas) se conservan
        historia["niveles"] = niveles_fijos
    palabras = sum(len(x.split()) for _, ls in historia["secciones"] for x in ls)
    objetivo = encargo.minutos * 60 * PALABRAS_POR_SEGUNDO
    avisar(f"Historia: {palabras} palabras (objetivo {int(objetivo)}).")
    if abs(palabras - objetivo) / objetivo > tolerancia:
        # Xandart cuenta las palabras (no Claude): si se aleja mucho, un solo ajuste (es otra
        # vuelta completa de la historia, por eso solo cuando de verdad hace falta)
        texto2, _ = ejecutar(prompt + f"\n\n== AJUSTA EL LARGO ==\nEsta es tu historia, con {palabras} palabras. Debe tener "
                                      f"entre {int(objetivo * 0.95)} y {int(objetivo * 1.05)}. "
                                      f"{'Alárgala con más datos concretos y escenas' if palabras < objetivo else 'Acórtala'} "
                                      "sin cambiar la estructura ni los niveles, y devuélvela completa en el mismo formato.\n\n"
                                      + texto, cwd=carpeta)
        try:
            ajustada = leer_historia(texto2, usa_niveles)
            if niveles_fijos:
                _niveles_coinciden(ajustada, niveles_fijos)
                ajustada["niveles"] = niveles_fijos
            nuevas = sum(len(x.split()) for _, ls in ajustada["secciones"] for x in ls)
            if abs(nuevas - objetivo) < abs(palabras - objetivo):
                historia, palabras = ajustada, nuevas
                avisar(f"Historia ajustada: {palabras} palabras.")
        except ValueError:
            pass
    escribir_json(borrador / "historia.json", {**historia, "secciones": [list(x) for x in historia["secciones"]]})
    n = len(historia["secciones"])
    avisar(f"Historia lista ({sum(len(x[1]) for x in historia['secciones'])} escenas). Claude está dirigiendo "
           f"las {n} secciones…")
    with ThreadPoolExecutor(max_workers=max(1, en_paralelo)) as pool:
        def seccion(k):
            guardada = borrador / f"seccion_{k:02d}.json"
            if guardada.exists():
                return leer_json(guardada)
            hecha = _detalles(historia, k, estilo, carpeta, ejecutar_detalles, avisar, catalogo)
            escribir_json(guardada, hecha)
            return hecha

        partes = list(pool.map(seccion, range(n)))
    datos = {"titulo": historia["titulo"], "niveles": historia["niveles"], "escenas": [e for p in partes for e in p],
             "catalogo": catalogo or []}
    doc, direccion, md = a_escenas(datos, estilo, canal)
    escribir_json(carpeta / "escenas.json", doc)
    escribir_json(carpeta / "direccion.json", direccion)
    (carpeta / "guion.md").write_text(md, encoding="utf-8")
    return {"escenas": len(doc["escenas"]), "palabras": sum(len(e["narracion"].split()) for e in doc["escenas"]),
            "tokens": (sobre.get("usage") or {})}


def ubicar_villano(carpeta: Path, ejecutar=claude_cli.ejecutar) -> dict:
    """Mira las escenas previas a la revelación que muestran al villano y
    guarda en direccion.json las zonas a pixelar (15.4)."""
    ruta = carpeta / "direccion.json"
    direccion = leer_json(ruta)
    pendientes = direccion.get("pixelar_pendiente") or []
    if not pendientes:
        return direccion
    esc = {e["id"]: e for e in leer_json(carpeta / "escenas.json")["escenas"]}
    niveles = leer_json(carpeta / "escenas.json").get("niveles", [])
    villano = next((n["nombre"] for n in niveles if n.get("villano")), "el animal peligroso")
    lista = "\n".join(f"- escena {i}: {esc[i]['visual']['archivo']}" for i in pendientes if esc[i]['visual'].get('archivo'))
    prompt = (f"Mira cada imagen con la herramienta Read (rutas relativas a esta carpeta):\n{lista}\n\n"
              f"En cada una, ubica a {villano}. Devuelve SOLO un JSON {{\"<numero de escena>\": [[x0, y0, x1, y1]]}} "
              "con cajas en coordenadas normalizadas de 0 a 1 (x hacia la derecha, y hacia abajo) que cubran al "
              "animal con un margen del 10 %. Si no aparece en una imagen, pon una lista vacía.")
    texto, _ = ejecutar(prompt, cwd=carpeta, herramientas=["Read"])
    cajas = claude_cli.extraer_json(texto)
    direccion["pixelar"] = {str(k): [[round(min(max(float(c), 0), 1), 3) for c in caja] for caja in v]
                            for k, v in cajas.items() if v}
    escribir_json(ruta, direccion)
    return direccion
