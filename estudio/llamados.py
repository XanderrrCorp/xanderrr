"""Llamados a comentar en los guiones de escala (17-10, pedido del dueño para Peligro Tropical).

Cinco llamados fijos, integrados en la narración (sin escenas ni imágenes nuevas, máximo ~30 s en total):
apuesta (adivinar el último de la lista con 3 opciones), experiencia personal, debate sobre el orden, país y cierre
(«¿qué animal quieres en la próxima escala?»). Claude marca cada línea de un llamado con «[COMENTA:<tipo>]»; Xandart
revisa que estén los 5 y que no pasen de MAX_PALABRAS, y QUITA las etiquetas antes de guardar el guion: nunca llegan
a la voz, los subtítulos ni a la pantalla. Junto al guion queda el comentario fijado (respuesta de la apuesta + la
pregunta del cierre), con el emoji: la voz no lee emojis.

Se activa por canal: Canal.ajustes["llamados_comentar"]; si el canal no lo eligió, queda encendido solo en los
canales del estilo de Peligro Tropical.
"""
from __future__ import annotations

import hashlib
import re

TIPOS = ("apuesta", "experiencia", "debate", "pais", "cierre")
MAX_PALABRAS = 85               # ≈30 s de voz a 2,9 palabras por segundo
MAX_REINTENTOS = 2
AJUSTE = "llamados_comentar"
ESTILOS_POR_DEFECTO = ("enciclopedia_mascota",)
PREGUNTA_CIERRE = "¿Qué animal quieres en la próxima escala?"
ETIQUETA = re.compile(r"\[\s*COMENTA\s*:\s*([a-záéíóúñ_]+)\s*\]\s*", re.I)
FIJADO = re.compile(r"(?i)^comentario[_ ]fijado\s*:\s*(.+)$")
EJEMPLO = re.compile(r"(?i)^ejemplo\s*:\s*([a-záéíóúñ_]+)\s*\|\s*(.+)$")
MAX_EJEMPLO = 42
# (17-10) lo que se escribe solo en el cuadro de comentario animado cuando Claude no dio un ejemplo
EJEMPLOS_POR_DEFECTO = {"apuesta": "Mi apuesta: ¡la primera!", "experiencia": "¡SOBREVIVIENTE!",
                        "debate": "Yo lo pondría más arriba", "pais": "¡Desde Colombia!",
                        "cierre": "¡Quiero ver más escalas!"}
ORDINALES = {1: "primera", 2: "segunda", 3: "tercera"}


def activos(canal: str | None, estilo_id: str | None) -> bool:
    from .plataforma.consultas import ajuste_canal

    valor = ajuste_canal(canal, AJUSTE) if canal else None
    return bool(valor) if valor is not None else estilo_id in ESTILOS_POR_DEFECTO


def posicion_correcta(tema: str) -> int:
    """Dónde va la respuesta correcta entre las 3 opciones (1, 2 o 3): cambia de un video a otro."""
    return int(hashlib.sha1(tema.strip().lower().encode()).hexdigest(), 16) % 3 + 1


def instruccion(tema: str) -> str:
    pos = posicion_correcta(tema)
    return f"""
== LLAMADOS A COMENTAR (OBLIGATORIOS, aunque las notas no los pidan) ==
Mete EXACTAMENTE estos 5 llamados dentro de la narración, en tono natural de amigo, sin sonar a anuncio y sin
cortar el ritmo. No agregan secciones ni animales: van dentro de la sección que se indica. Escribe CADA línea que
forme parte de un llamado empezando con su etiqueta, por ejemplo «[COMENTA:apuesta] Antes de seguir…» (la etiqueta
no se lee en voz alta: el sistema la quita). Entre los 5 llamados, máximo {MAX_PALABRAS} palabras en total.
1. [COMENTA:apuesta] Al final de la sección Gancho (justo antes del primer animal): pide adivinar cuál es el último
   de la lista con 3 opciones ya escritas para copiar; una es la correcta (el último animal de verdad) y va en la
   {ORDINALES[pos]} posición. Solo aquí puedes decir «el último de la lista, el número ocho» (o el número que sea).
   Ejemplo: «Antes de seguir, escribe en los comentarios cuál crees que es el último de la lista, el número ocho:
   ¿pitón, anaconda o cachalote? Al final vemos quién acertó.»
2. [COMENTA:experiencia] En la sección del animal más cotidiano o conocido de la lista: pide que comenten una
   experiencia propia CON ESE MISMO ANIMAL (nómbralo) con una palabra corta lista para copiar, dicha en voz (sin
   emojis: la voz no los lee).
   Ejemplo: «Si alguna vez te picó una avispa, escribe sobreviviente en los comentarios.»
3. [COMENTA:debate] En el puesto más discutible del orden: reconoce en voz alta que habrá desacuerdo y pregunta
   «¿tú dónde lo pondrías?». El debate es sobre el ORDEN, nunca sobre los hechos: no metas datos falsos a propósito.
4. [COMENTA:pais] En la sección del animal que cae a mitad del video: «Escribe desde qué país nos ves y te digo cuál
   de estos animales vive cerca de ti.»
5. [COMENTA:cierre] En la sección Cierre, como pregunta final (en lugar de «¿cuál te dio más miedo?»), con estas
   palabras exactas (aquí SÍ se dice «escala», es pedido del dueño):
   «¿Qué animal quieres en la próxima escala? El más pedido sale en el siguiente video.»
Después del TITULO escribe además, para el cuadro de comentario animado que sale en pantalla, UNA línea por llamado
con lo que escribiría un espectador (máximo {MAX_EJEMPLO} caracteres, sin emojis; en la apuesta, una opción que NO
sea la correcta, para no regalar la respuesta):
EJEMPLO: apuesta | Yo digo que es la anaconda
EJEMPLO: experiencia | SOBREVIVIENTE
EJEMPLO: debate | Yo lo pondría de primero
EJEMPLO: pais | Desde México
EJEMPLO: cierre | ¡Quiero ver los tiburones!
Y escribe UNA línea:
COMENTARIO_FIJADO: <revela la respuesta de la apuesta con un emoji del animal y repite la pregunta del cierre>
Ejemplo: «COMENTARIO_FIJADO: El número 8 era el cachalote 🐋 ¿Acertaste? Y dime: ¿qué animal quieres en la próxima
escala?»
"""


def quitar_etiquetas(texto: str) -> str:
    return re.sub(r"\s{2,}", " ", ETIQUETA.sub("", texto)).strip()


def separar_fijado(texto: str) -> tuple[str, str | None, dict[str, str]]:
    """Saca las líneas COMENTARIO_FIJADO y EJEMPLO del texto de Claude (no son narración)."""
    fijado, lineas, ejemplos = None, [], {}
    for linea in (texto or "").splitlines():
        limpia = linea.strip().strip("`").strip()
        m, e = FIJADO.match(limpia), EJEMPLO.match(limpia)
        if m:
            fijado = m.group(1).strip()
        elif e:
            ejemplos[e.group(1).lower().replace("í", "i")] = e.group(2).strip()[:MAX_EJEMPLO]
        else:
            lineas.append(linea)
    return "\n".join(lineas), fijado, ejemplos


def comentarios_en_pantalla(llamados: list, partes: list[list], ejemplos: dict[str, str]) -> dict[str, dict]:
    """{id de escena: {tipo, texto, grupo}} para el cuadro de comentario animado. `partes` son las escenas de cada
    sección en orden (el id de escena es su posición en el video, desde 1). Las líneas de un mismo llamado comparten
    «grupo»: el cuadro dura todas."""
    inicio, acum = [], 1
    for p in partes:
        inicio.append(acum)
        acum += len(p)
    salida = {}
    for seccion, i, tipo in llamados:
        if seccion < len(inicio):
            texto = (ejemplos or {}).get(tipo) or EJEMPLOS_POR_DEFECTO.get(tipo, "")
            salida[str(inicio[seccion] + i)] = {"tipo": tipo, "texto": texto[:MAX_EJEMPLO], "grupo": tipo}
    return salida


def encontrar(historia: dict) -> list[dict]:
    """Las líneas marcadas: [{tipo, seccion (índice), escena (índice en la sección), texto (sin etiqueta)}]."""
    salida = []
    for k, (_, lineas) in enumerate(historia["secciones"]):
        for i, linea in enumerate(lineas):
            m = ETIQUETA.search(linea)
            if m:
                tipo = m.group(1).lower().replace("í", "i")
                salida.append({"tipo": tipo, "seccion": k, "escena": i, "texto": quitar_etiquetas(linea)})
    return salida


def _palabras(texto: str) -> int:
    return len(texto.split())


def problemas(historia: dict, fijado: str | None = None) -> list[str]:
    """Lo que falla en los llamados (vacío = todo bien)."""
    marcados = encontrar(historia)
    tipos = {x["tipo"] for x in marcados}
    salida = [f"falta el llamado «{t}»" for t in TIPOS if t not in tipos]
    total = sum(_palabras(x["texto"]) for x in marcados)
    if total > MAX_PALABRAS:
        salida.append(f"los llamados suman {total} palabras y el máximo es {MAX_PALABRAS}: acórtalos")
    villano = next((n for n in historia.get("niveles", []) if n.get("villano")), None)
    apuesta = " ".join(x["texto"] for x in marcados if x["tipo"] == "apuesta").lower()
    if villano and apuesta and not _menciona(apuesta, villano["nombre"]):
        salida.append(f"la apuesta no incluye la respuesta correcta ({villano['nombre']}) entre sus 3 opciones")
    return salida


def _menciona(texto: str, nombre: str) -> bool:
    import unicodedata

    def n(t):
        return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")

    palabras = [w for w in re.findall(r"\w+", n(nombre)) if len(w) > 3]
    return any(w in n(texto) for w in palabras) if palabras else True


def limpiar(historia: dict) -> dict:
    """Quita las etiquetas de toda la narración (lo que se guarda, se lee en voz y se subtitula)."""
    return {**historia, "secciones": [(nombre, [quitar_etiquetas(x) for x in lineas])
                                      for nombre, lineas in historia["secciones"]]}


def comentario_fijado(fijado: str | None, historia: dict) -> str:
    """Respuesta de la apuesta + la pregunta del cierre (si Claude no lo escribió o le faltó algo, se completa)."""
    niveles = historia.get("niveles", [])
    villano = next((n for n in niveles if n.get("villano")), niveles[-1] if niveles else None)
    texto = (fijado or "").strip()
    if not texto and villano:
        texto = f"El número {len(niveles)} era {villano['nombre']} ¿Acertaste?"
    if "qué animal quieres" not in texto.lower():
        texto = f"{texto} Y dime: {PREGUNTA_CIERRE[0].lower()}{PREGUNTA_CIERRE[1:]}".strip()
    return texto


def correccion(lista: list[str]) -> str:
    return ("\n\n== CORRIGE LOS LLAMADOS A COMENTAR ==\nTu guion anterior tiene estos problemas con los llamados:\n- "
            + "\n- ".join(lista) + "\nDevuelve la historia completa en el mismo formato, con los 5 llamados "
            "etiquetados y la línea COMENTARIO_FIJADO. No cambies los animales ni el resto del texto.")
