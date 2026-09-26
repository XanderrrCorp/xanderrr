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

PALABRAS_POR_SEGUNDO = 2.9          # medido con la voz del dueño en MiniMax


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

== ESTRUCTURA ==
- Gancho (40 a 70 s): abre con el momento más fuerte y concreto, sin saludos ni «en este video».
  Deja una pregunta abierta que se paga al final. Presenta el giro. Una escena del gancho es la
  tira de niveles (accion "componer"). Cierra el gancho prometiendo algo para el final.
- Entre 4 y 8 niveles de menos a más peligro. Cada nivel abre con una escena «Nivel N. Nombre.»
  que es accion "reusar" con "reusar": "nivel:N". Luego 6 a 14 escenas con datos concretos,
  curiosidades verdaderas y un consejo práctico. Cada sección abre con su tensión.
- Lo más fuerte va en el último tercio. Antes de los dos últimos niveles, una frase que retenga.
- Después del último nivel: qué hacer (lo prometido) y cierre corto (resumen, pregunta para
  comentarios, suscripción).

== REGLAS DE TEXTO ==
- Español neutro cercano, frases cortas, de tú. Cada escena cierra una idea: 7 a 18 palabras
  (unos 3 a 5 segundos de voz). Alterna frases cortas y alguna más larga.
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
- En 8 a 14 momentos clave (giros, datos fuertes) pon "texto_pantalla" (2 a 5 palabras en
  MAYÚSCULAS) y "palabra": la palabra de la narración en la que debe aparecer.

== INTENCIONES (una por escena) ==
{", ".join(INTENCIONES)}

== FORMATO DE SALIDA ==
Responde SOLO con un objeto JSON, sin texto antes ni después:
{{"titulo": "...",
  "niveles": [{{"numero": 1, "nombre": "...", "sujeto": "english description of the animal for a card: species, colors, pose, magnified, whole body visible and centered", "villano": false}}, ...],
  "escenas": [{{"seccion": "Gancho", "narracion": "...", "intencion": "gancho", "intensidad": 3,
               "accion": "generar", "tipo": "{ejemplo}", "descripcion": "...", "con_mascota": true,
               "muestra_villano": false, "revelacion_villano": false, "texto_pantalla": null, "palabra": null}},
              {{"seccion": "Nivel 1 · ...", "narracion": "Nivel uno. ...", "intencion": "transicion_de_seccion",
               "intensidad": 2, "accion": "reusar", "reusar": "nivel:1"}}, ...]}}
Antes de responder, cuenta las palabras de todas las narraciones y ajusta al rango pedido."""


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
                        "visual": vis, "notas_edicion": notas})
        t += escenas[-1]["tiempo"]["estimado_duracion"]
        if e.get("revelacion_villano") and "villano_revelacion" not in direccion:
            direccion["villano_revelacion"] = i
        if e.get("muestra_villano") and accion == "generar":
            direccion["pixelar_pendiente"].append(i)
        if e.get("texto_pantalla"):
            direccion["textos"][str(i)] = {"texto": str(e["texto_pantalla"]).upper()[:40],
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
