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


def instruccion(encargo: Encargo, estilo: Estilo, niveles_fijos: list[dict] | None = None) -> str:
    palabras = int(encargo.minutos * 60 * PALABRAS_POR_SEGUNDO)
    fijos = ""
    if niveles_fijos:
        lista = "\n".join(f"  {n['numero']}. {n['nombre']}{' (VILLANO, último)' if n.get('villano') else ''}"
                          for n in sorted(niveles_fijos, key=lambda x: x["numero"]))
        fijos = ("\nNIVELES OBLIGATORIOS (usa EXACTAMENTE estos animales, con estos nombres y en este orden; "
                 f"ni uno más ni uno menos):\n{lista}\n")
    return f"""Eres el guionista y director visual de un canal de YouTube en español latino (México y
Colombia) de formato escala: «del más inofensivo al más peligroso». Escribe el guion COMPLETO
de un video y divídelo en escenas.

== ENCARGO ==
Tema: {encargo.tema}
Giro: {encargo.giro or "(propón uno fuerte y verdadero)"}
Villano (el más peligroso, último nivel): {encargo.villano or "(elige el más peligroso y verdadero)"}{fijos}
Duración: unos {encargo.minutos:g} minutos de voz = entre {int(palabras * 0.93)} y {int(palabras * 1.07)} palabras en total.
{("Notas del dueño: " + encargo.notas) if encargo.notas else ""}

== ESTRUCTURA (técnicas que retienen; escribe todo con palabras propias) ==
El video es UNA historia contada por alguien que le habla de tú al espectador, como un amigo que
le cuenta algo increíble, no una enciclopedia que lista datos. Toda la escala se mide con UN solo
eje que se repite en todo el video (por ejemplo «la probabilidad de que te mande al hospital» o
«de quitarte la vida»), y cada nivel existe para explicar POR QUÉ está en ese puesto.

- Gancho de contraste (40 a 70 s), sin saludos ni «en este video»:
  1. «¿Qué probabilidad crees que tiene este animal de…?» con uno que se ve inofensivo; di lo
     poco que podría hacerte («a lo mucho te muerde un dedo…») y concluye: prácticamente cero.
  2. «Ahora mira este otro.» Uno que SE VE aterrador; el espectador cree que pasa del cincuenta
     por ciento. «Pero aquí viene el primer giro»: está entre los MENOS peligrosos.
  3. «Y ahora el verdadero susto. Agárrate.» El último de la lista, el de mayor probabilidad, es
     alguien que nadie se espera: «al verlo no lo vas a creer, pero hay algo de él que no sabes».
     No digas su nombre todavía. En pantalla va oculto, pero la voz NUNCA dice que está pixelado,
     borroso, tapado u oculto: eso lo resuelve la imagen, no el guion.
  4. Promesa: «hoy empezamos casi en cero y vamos a ver hasta dónde sube esa probabilidad, y cómo
     de verdad podría pasar». Una escena del gancho presenta la lista de niveles (ahí se ve la tira).
- Entre 5 y 7 niveles, de menos a más. Cada nivel es una mini historia de un minuto aprox.:
  1. Lo presentas por su nombre con una imagen mental fuerte, SIN «nivel uno» ni números de nivel
     («Empezamos con algo que parece salido de una pesadilla: la cucaracha.»).
  2. Una pregunta que abre la intriga («¿por qué crees que está tan abajo? Hay una razón que
     sorprende.»).
  3. Dónde vive y cómo es, con UNA comparación cotidiana que se quede («parece un bolso de lujo»,
     «para que te hagas una idea…»).
  4. El mecanismo central de cómo hace daño, explicado paso a paso, cada frase apoyándose en la
     anterior (y por eso…, pero…, entonces…, y aquí viene lo raro…). UN mecanismo bien contado, no
     diez datos sueltos.
  5. La pregunta con respuesta seca y repetida: «¿Cuántos ataques documentados tiene? Cero. Ni uno.
     Ni antes, ni ahora. Cero, así de simple.»
  6. El veredicto en el eje del video (por qué queda en este puesto y no más arriba) y un remate
     «lo más aterrador no es X, es Y».
  7. Transición que abre un bucle con el siguiente SIN nombrarlo: qué puede hacer y qué tiene de
     raro («el siguiente sí te puede picar, y lo curioso es que no es la picadura lo que te
     enferma; cuando sepas cómo lo hace, vas a cambiar de opinión»; «de algo gigante pasamos a algo
     que cabe en tu mano, y kilo por kilo es muchísimo peor»).
  Nada de consejos de limpieza o de prevención en cada nivel: eso aplana el video.
- Una o dos anécdotas del narrador en primera persona, contadas como un recuerdo suyo (el
  explorador del canal): un momento concreto, con lugar y persona («la primera vez que vi uno fue
  en la casa de un amigo en Cartagena; estaba sentado en el sofá y de pronto…»), lo que sintió
  («me quedé congelado») y cómo lo lleva al dato. De 3 a 6 escenas, para abrir un nivel o antes
  del villano. La anécdota es solo el marco: todos los datos que vienen después siguen siendo
  verdaderos y no se inventan cifras ni casos dentro de ella.
- Llamado a suscribirse UNA sola vez, hacia el minuto 1, pegado a la intriga del primer animal:
  «Por cierto, si hasta este primero te tomó por sorpresa, dale like y suscríbete. Sí, vamos con la
  razón…». Nunca al inicio.
- Antes del último nivel: «y ahora llegamos al final de la lista, al que te mencioné al principio,
  el que te va a hacer decir "¿de verdad es este?"». Confírmalo corto («Sí, una chinche.»);
  contrasta lo inocente que se ve con lo que hace; «no avisa»; lo más escalofriante al final.
- Cierre corto: «Ahora ya lo sabes. Empezamos con…, que casi no puede hacerte nada, y terminamos
  con…, capaz de…». En salud, solo orientar a ir al médico. Luego like y notificaciones.

== REGLAS DE TEXTO ==
- Español neutro cercano, de tú, como se habla en voz alta. Las frases FLUYEN y se encadenan; mezcla
  frases cortas de golpe («Cero.») con otras medianas. Cada escena lleva 3 a 16 palabras; si una
  frase es más larga, pártela entre dos escenas seguidas en una pausa natural (en una coma).
- En la primera escena con imagen propia de cada nivel, di el nombre del animal (no solo «ella» o
  «este»): el video lo encierra en un círculo rojo justo cuando lo nombras.
- Hazle al espectador 4 a 6 preguntas directas repartidas en el video, cada una en su escena.
- Números SIEMPRE en palabras («trescientos millones», «veinte años»).
- Solo hechos verdaderos. Si los casos reales son pocos, dilo. En salud: sin dosis ni
  medicamentos; orienta a ir al médico o a urgencias.
- Nombres compuestos separados como se dicen. Nada de siglas deletreadas.
- La voz NUNCA dice «villano», «villano final», «nivel uno», «nivel dos», «escala» ni otras palabras
  de cómo está armado el video: el último animal se presenta como «el último de la lista», «el que te
  dije al principio». Villano es solo una palabra interna para ti.

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


def leer_historia(texto: str) -> dict:
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
    villano = next((n for n in historia["niveles"] if n["villano"]), historia["niveles"][-1])
    niveles = "\n".join(f"  {n['numero']}. {n['nombre']}{' (VILLANO)' if n['villano'] else ''}" for n in historia["niveles"])
    numeradas = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(lineas))
    es_gancho = k == 0
    nivel = next((n for n in historia["niveles"] if nombre.lower().startswith(f"nivel {n['numero']} ")
                  or nombre.lower().startswith(f"nivel {n['numero']}·")), None)
    especiales = []
    especiales.append('- Si la escena es parte de una anécdota del narrador (habla en primera persona: «yo», «me», '
                      '«mi amigo»), usa pov_personaje para lo que él vio con sus ojos, o escena_cartoon_completa con él '
                      'en ese lugar reaccionando (por ejemplo congelado del susto en una calle).')
    if es_gancho:
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
    especiales = "\n".join(especiales)
    bloque_catalogo = ""
    if catalogo:
        filas = "\n".join(f"  - {c['id']}: {c['descripcion'][:140]}" for c in catalogo)
        bloque_catalogo = f"""
IMÁGENES YA HECHAS (gratis): prefiere SIEMPRE una de estas si encaja con lo que dice la escena, con
"accion": "reusar", "reusar": "imagen:<id>". Solo pide imagen nueva ("generar") si ninguna encaja de verdad.
No pongas la misma imagen en dos escenas seguidas.
{filas}
"""
    return f"""Eres el director visual de un video de YouTube en español: «{historia['titulo']}».
Niveles (de menos a más peligro):
{niveles}
El villano ({villano['nombre']}) no se muestra claramente antes de su revelación.

Sección «{nombre}». Estas son sus escenas (lo que dice la voz), numeradas:
{numeradas}

Para CADA escena, en orden, decide:
- "intencion": una de {", ".join(INTENCIONES)} (las preguntas al espectador son pregunta_al_espectador).
- "intensidad": 1 a 5.
- "accion": "generar" (imagen nueva), "reusar" o "componer". Alrededor del 70 % generan imagen; reusa con
  "reusar": "escena:<primeras palabras exactas de una escena anterior de esta sección>" cuando la voz vuelve
  sobre algo ya visto.
- "tipo" (solo si generar), de esta lista del estilo «{estilo.nombre}»:
{tipos}
- "descripcion" (solo si generar) en INGLÉS: qué se ve, concreto (sujeto, acción, lugar, luz). Nunca texto,
  letras, números ni letreros en la imagen. Nada de sangre ni heridas gráficas.
- "con_mascota": true si aparece la mascota (un hombre de dibujo de cabeza blanca redonda); en la descripción
  llámala "the cartoon man".{nota_mascota}
- "palabra_clave": la palabra MÁS importante de esa escena, copiada tal cual (sustantivo o número en palabras).
- "texto_pantalla": solo en 1 o 2 escenas fuertes de la sección, un título corto de 2 a 6 palabras escrito
  normal, como lo diría una persona («Es aterrador»); y "palabra": la palabra de la escena donde aparece.
  En las demás, null.
{especiales}
{bloque_catalogo}
Responde SOLO un JSON: {{"escenas": [{{"n": 1, "intencion": "...", "intensidad": 3, "accion": "generar",
"tipo": "{ejemplo}", "descripcion": "...", "con_mascota": false, "palabra_clave": "...", "texto_pantalla": null,
"palabra": null}}, ...]}} con exactamente {len(lineas)} escenas."""


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


def a_escenas(datos: dict, estilo: Estilo, canal: str) -> tuple[dict, dict, str]:
    """JSON del guionista → (escenas.json v2, direccion.json, guion.md)."""
    niveles_in = sorted(datos["niveles"], key=lambda n: n["numero"])
    if not any(n.get("villano") for n in niveles_in):
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
        accion = e.get("accion", "generar")
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
                           if x.get("accion", "generar") == "generar" and x["narracion"].lower().startswith(inicio[:40])]
                if previas:
                    vis["reusar_de"] = previas[0]
                else:
                    # referencia rara: se reusa la última imagen propia anterior en vez de fallar
                    anteriores = [j for j, x in enumerate(crudas[:i - 1], 1) if x.get("accion", "generar") == "generar"]
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
        if e.get("texto_pantalla"):
            direccion["textos"][str(i)] = {"texto": str(e["texto_pantalla"]).strip()[:48],
                                           "palabra": e.get("palabra") or ""}
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


def escribir_guion(encargo: Encargo, estilo: Estilo, carpeta: Path, canal: str,
                   ejecutar=claude_cli.ejecutar, avisar=print, en_paralelo: int = 3,
                   catalogo: list[dict] | None = None, niveles_fijos: list[dict] | None = None) -> dict:
    """Dos pasos para que ninguna respuesta sea enorme (y no pase del tiempo máximo):
    1) la historia en texto (título, niveles y lo que dice la voz, escena por escena);
    2) por sección, y varias a la vez, la intención, la imagen y los textos de cada escena."""
    from concurrent.futures import ThreadPoolExecutor

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
            historia = leer_historia(texto)
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
    if abs(palabras - objetivo) / objetivo > 0.10:
        # Xandart cuenta las palabras (no Claude): si se aleja más de 10 %, un solo ajuste
        texto2, _ = ejecutar(prompt + f"\n\n== AJUSTA EL LARGO ==\nEsta es tu historia, con {palabras} palabras. Debe tener "
                                      f"entre {int(objetivo * 0.95)} y {int(objetivo * 1.05)}. "
                                      f"{'Alárgala con más datos concretos y escenas' if palabras < objetivo else 'Acórtala'} "
                                      "sin cambiar la estructura ni los niveles, y devuélvela completa en el mismo formato.\n\n"
                                      + texto, cwd=carpeta)
        try:
            ajustada = leer_historia(texto2)
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
            hecha = _detalles(historia, k, estilo, carpeta, ejecutar, avisar, catalogo)
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
