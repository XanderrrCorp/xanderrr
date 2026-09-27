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


def instruccion(encargo: Encargo, estilo: Estilo) -> str:
    palabras = int(encargo.minutos * 60 * PALABRAS_POR_SEGUNDO)
    return f"""Eres el guionista y director visual de un canal de YouTube en español latino (México y
Colombia) de formato escala: «del más inofensivo al más peligroso». Escribe el guion COMPLETO
de un video y divídelo en escenas.

== ENCARGO ==
Tema: {encargo.tema}
Giro: {encargo.giro or "(propón uno fuerte y verdadero)"}
Villano (el más peligroso, último nivel): {encargo.villano or "(elige el más peligroso y verdadero)"}
Duración: unos {encargo.minutos:g} minutos de voz = entre {int(palabras * 0.93)} y {int(palabras * 1.07)} palabras en total.
{("Notas del dueño: " + encargo.notas) if encargo.notas else ""}

== ESTRUCTURA (técnicas que retienen; escribe todo con palabras propias) ==
- Gancho de contraste (40 a 70 s), sin saludos ni «en este video»:
  1. Pregúntale al espectador qué probabilidad cree que tiene un animal de hacerle daño de verdad,
     empezando por uno que se ve inofensivo (casi cero).
  2. Luego uno que SE VE aterrador: el espectador creerá que es el peor. Primer giro: está entre
     los menos peligrosos (dilo claro).
  3. «Y ahora el verdadero susto»: anuncia que el último de la lista es alguien que no te
     esperarías (se muestra pixelado) y que hay algo de él que no sabes. Deja la pregunta abierta.
  4. Promete la escala: empezamos casi en cero y vamos subiendo hasta el más peligroso, y al final
     sabrás cómo pasa y qué hacer. Una escena del gancho presenta la lista de niveles (ahí se ve la tira).
- Entre 4 y 8 niveles de menos a más peligro. Cada nivel abre con una escena «Nivel N. Nombre.»
  (número en palabras). Luego 6 a 14 escenas, y en cada nivel usa:
  una imagen mental fuerte al presentarlo, una comparación cotidiana que se recuerde, dónde vive
  (lugares concretos), números concretos (tamaño, peso, profundidad), cómo hace daño explicado
  paso a paso y fácil, una pregunta con respuesta seca («¿Cuántos casos hay? Cero.»), qué tan
  frecuentes son los casos reales (sin exagerar: si son pocos, dilo), un remate del tipo «lo más
  aterrador no es X, es Y» y un consejo práctico.
- Cada nivel termina con una transición que deja con ganas y SUBE la escala («ahora subamos el
  miedo», «de algo gigante pasamos a algo que cabe en tu mano, y es peor»).
- Llamado a suscribirse UNA sola vez, hacia el minuto 1: justo después del gancho, cuando ya
  presentaste al primer animal y dejaste una intriga («por cierto, si ya este te sorprendió, dale
  like y suscríbete»); enseguida vuelve a la intriga («sí, vamos con la razón…»). Nunca al inicio.
- Lo más fuerte va en el último tercio. Antes de los dos últimos niveles, una frase que retenga.
- Último nivel (el villano): «el que te dije al principio»; confírmalo corto («Sí, una chinche.»);
  contrasta lo inocente que se ve con lo que hace; «no avisa»; lo más escalofriante al final.
- Cierre: qué hacer (lo prometido), repaso de un vistazo «empezamos con… y terminamos con…»,
  pregunta para comentarios y suscripción, corto.

== REGLAS DE TEXTO ==
- Español neutro cercano, frases cortas, de tú. Cada escena cierra una idea: 5 a 14 palabras
  (unos 2 a 4,5 segundos de voz; nunca más de 14). Alterna escenas muy cortas con otras medianas:
  el ritmo NO debe ser parejo. Si una idea es larga, pártela en dos escenas.
- En la primera escena con imagen propia de cada nivel, di el nombre del animal (no solo «ella» o
  «este»): el video lo encierra en un círculo rojo justo cuando lo nombras.
- Hazle al espectador 3 a 5 preguntas directas repartidas en el video («¿tú lo sabías?», «¿adivinas
  cuál es?»), cada una en su propia escena.
- Números SIEMPRE en palabras («trescientos millones», «veinte años»).
- Solo hechos verdaderos. En salud: sin dosis ni medicamentos; orienta a ir al médico o a urgencias.
- Nombres compuestos separados como se dicen. Nada de siglas deletreadas.

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
Nivel uno. <Nombre>.
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
        if secciones:
            secciones[-1][1].append(linea)
    secciones = [(n, ls) for n, ls in secciones if ls]
    if not titulo or len(niveles) < 4 or len(niveles) > 8 or len(secciones) < 3:
        raise ValueError(f"historia incompleta: título={bool(titulo)}, niveles={len(niveles)}, secciones={len(secciones)}")
    return {"titulo": titulo, "niveles": niveles, "secciones": secciones}


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
    if es_gancho:
        especiales.append('- Esta es la sección del GANCHO: la escena que presenta la lista de niveles lleva '
                          '"accion": "componer" (el sistema muestra la tira). Si una escena muestra al villano, pon '
                          '"muestra_villano": true: el sistema lo pixelará hasta su revelación.')
    if nivel:
        especiales.append(f'- Es la sección del nivel {nivel["numero"]}: la escena 1 («Nivel …») lleva "accion": "reusar", '
                          f'"reusar": "nivel:{nivel["numero"]}" e intención transicion_de_seccion.')
        if nivel["villano"]:
            especiales.append('- Es el VILLANO: marca "revelacion_villano": true en la escena donde se ve por primera vez '
                              'su aspecto (normalmente justo después de «Nivel …»).')
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
            elif ref.startswith("imagen:") and ref.split(":", 1)[1].strip() in ids_catalogo:
                vis["reusar_de"] = ref.split(":", 1)[1].strip()          # imagen ya pagada de otro video
            else:
                inicio = ref.split(":", 1)[-1].strip().lower()
                previas = [j for j, x in enumerate(crudas[:i - 1], 1)
                           if x.get("accion", "generar") == "generar" and x["narracion"].lower().startswith(inicio[:40])]
                if not previas:
                    # no encontró a qué escena se refiere: se genera una imagen propia
                    raise ValueError(f"escena {i}: no encuentro la escena a reusar «{ref}»")
                vis["reusar_de"] = previas[0]
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
        if e.get("muestra_villano") and accion == "generar":
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
    return doc, direccion, "".join(md).rstrip() + "\n"


def escribir_guion(encargo: Encargo, estilo: Estilo, carpeta: Path, canal: str,
                   ejecutar=claude_cli.ejecutar, avisar=print, en_paralelo: int = 3,
                   catalogo: list[dict] | None = None, niveles_fijos: list[dict] | None = None) -> dict:
    """Dos pasos para que ninguna respuesta sea enorme (y no pase del tiempo máximo):
    1) la historia en texto (título, niveles y lo que dice la voz, escena por escena);
    2) por sección, y varias a la vez, la intención, la imagen y los textos de cada escena."""
    from concurrent.futures import ThreadPoolExecutor

    prompt = instruccion(encargo, estilo)
    error = ""
    avisar("Claude está escribiendo la historia…")
    for intento in range(2):
        texto, sobre = ejecutar(prompt if not error else
                                prompt + f"\n\n== CORRIGE ==\nTu respuesta anterior falló: {error}. "
                                         "Devuelve la historia completa en el formato pedido.", cwd=carpeta)
        try:
            historia = leer_historia(texto)
            break
        except ValueError as ex:
            error = str(ex)[:300]
            avisar(f"  historia: intento {intento + 1} no válido ({error[:120]})")
    else:
        raise claude_cli.ErrorClaude(f"La historia no quedó válida tras dos intentos: {error}")
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
                ajustada["niveles"] = niveles_fijos
            nuevas = sum(len(x.split()) for _, ls in ajustada["secciones"] for x in ls)
            if abs(nuevas - objetivo) < abs(palabras - objetivo):
                historia, palabras = ajustada, nuevas
                avisar(f"Historia ajustada: {palabras} palabras.")
        except ValueError:
            pass
    n = len(historia["secciones"])
    avisar(f"Historia lista ({sum(len(x[1]) for x in historia['secciones'])} escenas). Claude está dirigiendo "
           f"las {n} secciones…")
    with ThreadPoolExecutor(max_workers=max(1, en_paralelo)) as pool:
        partes = list(pool.map(lambda k: _detalles(historia, k, estilo, carpeta, ejecutar, avisar, catalogo), range(n)))
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
