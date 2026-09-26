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
    tipos = "\n".join(f"  - {t.id}: {t.descripcion}" for t in estilo.tipos_de_escena)
    ejemplo = estilo.tipos_de_escena[0].id
    solo_mascota = next((t.id for t in estilo.tipos_de_escena if "{personaje}" in t.plantilla_prompt
                         and "{bloque_estilo}" not in t.plantilla_prompt), None)
    nota_mascota = (f" En escenas de tipo {solo_mascota} describe solo su pose y su cara." if solo_mascota else "")
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
     sabrás cómo pasa y qué hacer. Una escena del gancho es la tira de niveles (accion "componer").
- Entre 4 y 8 niveles de menos a más peligro. Cada nivel abre con una escena «Nivel N. Nombre.»
  que es accion "reusar" con "reusar": "nivel:N". Luego 6 a 14 escenas, y en cada nivel usa:
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
  cuál es?»), cada una en su propia escena con intención pregunta_al_espectador.
- Números SIEMPRE en palabras («trescientos millones», «veinte años»).
- Solo hechos verdaderos. En salud: sin dosis ni medicamentos; orienta a ir al médico o a urgencias.
- Nombres compuestos separados como se dicen. Nada de siglas deletreadas.

== REGLAS DE IMAGEN ==
- tipo solo de esta lista (del estilo «{estilo.nombre}»):
{tipos}
- "descripcion" en INGLÉS: qué se ve, concreto (sujeto, acción, lugar, luz). Nunca pidas texto,
  letras, números ni letreros en la imagen. Nada de sangre ni heridas gráficas.
- La mascota del canal (un hombre de dibujo con cabeza blanca redonda) aparece en muchas escenas:
  pon "con_mascota": true y descríbela en la escena como "the cartoon man" (su aspecto lo pone
  el sistema).{nota_mascota}
- Alrededor del 70 % de las escenas generan imagen nueva; el resto reusa: "reusar": "nivel:N" en
  las entradas de nivel, o "reusar": "escena:<primeras palabras exactas de la narración de una
  escena anterior>" cuando la narración vuelve sobre algo ya visto (cierre, recordatorios).
- El villano NO se muestra claramente antes de su revelación. Si una escena anterior lo muestra
  (por ejemplo en el gancho), pon "muestra_villano": true: el sistema lo pixelará.
- Marca con "revelacion_villano": true la escena donde se ve al villano por primera vez en su
  nivel (normalmente la que describe su aspecto, justo después de «Nivel N. ...»).
- En 8 a 14 momentos clave (giros, datos fuertes) pon "texto_pantalla": un título corto de 2 a 6
  palabras escrito normal, como lo diría una persona («Puede posarse en tu cabeza», «Es aterrador»),
  y "palabra": la palabra de la narración en la que debe aparecer.
- En cada escena pon "palabra_clave": la palabra MÁS importante de esa narración, copiada tal cual
  (un sustantivo o número dicho en palabras: «veneno», «colchón», «trescientos»). Sale como etiqueta.

== INTENCIONES (una por escena) ==
{", ".join(INTENCIONES)}

== FORMATO DE SALIDA ==
Responde SOLO con un objeto JSON, sin texto antes ni después:
{{"titulo": "...",
  "niveles": [{{"numero": 1, "nombre": "...", "sujeto": "english description of the animal for a card: species, colors, pose, magnified, whole body visible and centered", "villano": false}}, ...],
  "escenas": [{{"seccion": "Gancho", "narracion": "...", "intencion": "gancho", "intensidad": 3,
               "accion": "generar", "tipo": "{ejemplo}", "descripcion": "...", "con_mascota": true,
               "muestra_villano": false, "revelacion_villano": false, "texto_pantalla": null, "palabra": null,
               "palabra_clave": "..."}},
              {{"seccion": "Nivel 1 · ...", "narracion": "Nivel uno. ...", "intencion": "transicion_de_seccion",
               "intensidad": 2, "accion": "reusar", "reusar": "nivel:1"}}, ...]}}
Antes de responder, cuenta las palabras de todas las narraciones y ajusta al rango pedido."""


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
                   ejecutar=claude_cli.ejecutar, avisar=print) -> dict:
    prompt = instruccion(encargo, estilo)
    ultimo_error = ""
    for intento in range(2):
        texto, sobre = ejecutar(prompt if not ultimo_error else
                                prompt + f"\n\n== CORRIGE ==\nTu respuesta anterior falló: {ultimo_error}. "
                                         "Devuelve el JSON completo corregido.", cwd=carpeta)
        try:
            datos = claude_cli.extraer_json(texto)
            doc, direccion, md = a_escenas(datos, estilo, canal)
            break
        except (ValueError, KeyError, TypeError) as ex:
            ultimo_error = str(ex)[:500]
            avisar(f"  guion: intento {intento + 1} no válido ({ultimo_error[:120]})")
    else:
        raise claude_cli.ErrorClaude(f"El guion no quedó válido tras dos intentos: {ultimo_error}")
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
