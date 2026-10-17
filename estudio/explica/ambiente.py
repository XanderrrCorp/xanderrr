"""El lugar de cada tema de El Calvo Explica (17-10, pedido del dueño: «fondos más acordes, no solo blanco»).

Al hacer el video, cada tema recibe un ambiente: un escenario (playa, volcán, bosque…), partículas que se mueven
(lluvia, ceniza, nieve…) y una luz (día, noche, atardecer, tormenta). Lo elige Claude leyendo el guion (gratis); sin
Claude, por palabras del tema. Con `fondos_google`, el escenario de cada tema se pinta UNA vez con Google (≈120 COP
c/u) y queda guardado; si se llega al máximo de gasto o falla, se usa el escenario por código.

Dónde va cada cosa:
- ilustración y personaje: el escenario del tema, con partículas y luz (si Claude ya eligió un lugar concreto para
  esa frase —el baño, la cocina—, se respeta);
- código (diagramas): el mismo escenario muy pálido («lavado:»), sin partículas, para que se lea el diagrama;
- cuadrícula: queda en blanco (es el mapa del video).
"""
from __future__ import annotations

import hashlib
import io
import unicodedata
from pathlib import Path

from ..calma.escenarios import ESCENARIOS
from ..calma.render import LUCES, PARTICULAS
from ..config import ConfigCostos, escribir_json, leer_json
from ..costos import LibroCostos, formato_cop
from . import canal as C

MODULO = "fondo_explica"
POR_DEFECTO = {"escenario": "sala", "particulas": None, "luz": "dia"}

# sin Claude: palabras del tema → ambiente (el primero que coincida)
PALABRAS = [
    (("volcan", "lava", "erupcion"), {"escenario": "volcan", "particulas": "ceniza", "luz": "atardecer"}),
    (("tsunami", "ola", "playa", "mar ", "tiburon"), {"escenario": "playa", "particulas": None, "luz": "dia"}),
    (("oceano", "submarin", "ahog", "bucear", "profundidad"), {"escenario": "oceano", "particulas": "burbujas", "luz": "dia"}),
    (("huracan", "tormenta", "rayo", "tornado", "inundacion", "lluvia"), {"escenario": "tormenta", "particulas": "lluvia", "luz": "tormenta"}),
    (("avalancha", "nieve", "frio", "hipotermia", "glaciar", "congel"), {"escenario": "montana_nieve", "particulas": "nieve", "luz": "dia"}),
    (("incendio", "fuego", "quemadura"), {"escenario": "bosque", "particulas": "chispas", "luz": "atardecer"}),
    (("desierto", "calor", "sequia", "insolacion", "sol "), {"escenario": "desierto", "particulas": "polvo", "luz": "dia"}),
    (("terremoto", "sismo", "edificio", "ciudad"), {"escenario": "ciudad", "particulas": "polvo", "luz": "dia"}),
    (("selva", "jungla", "serpiente", "mosquito"), {"escenario": "selva", "particulas": "hojas", "luz": "dia"}),
    (("bosque", "oso", "camping", "perdido"), {"escenario": "bosque", "particulas": "hojas", "luz": "dia"}),
    (("dormir", "sueno", "noche", "pesadilla"), {"escenario": "cuarto_noche", "particulas": None, "luz": "noche"}),
    (("meteorito", "asteroide", "espacio", "planeta"), {"escenario": "espacio", "particulas": None, "luz": "noche"}),
]
LUGARES_PINTADOS = {
    "volcan": "un volcán humeante a lo lejos, tierra volcánica oscura y rocas", "playa": "una playa tropical con mar y "
    "palmeras", "oceano": "el fondo del mar con rayos de luz, arena y algas", "tormenta": "un campo abierto bajo nubes "
    "de tormenta", "montana_nieve": "montañas nevadas y pinos con nieve", "bosque": "un bosque de pinos",
    "desierto": "un desierto con dunas y cactus", "ciudad": "una calle de ciudad con edificios", "selva": "una selva "
    "con hojas grandes y lianas", "cuarto_noche": "una habitación de noche con la ventana abierta",
    "espacio": "el espacio con estrellas y planetas lejanos", "sala": "la sala de una casa", "cielo": "un campo verde "
    "con cielo azul", "parque": "un parque con árboles", "cocina": "una cocina", "bano": "un baño",
    "cuarto": "una habitación de día", "clase": "un salón de clases", "consultorio": "un consultorio médico",
    "piscina": "una piscina",
}


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def por_palabras(nombre: str, frases: str = "") -> dict:
    texto = f" {_norm(nombre)} {_norm(frases)} "
    for claves, amb in PALABRAS:
        if any(k in texto for k in claves):
            return dict(amb)
    return dict(POR_DEFECTO)


def _limpio(a: dict | None, respaldo: dict) -> dict:
    a = a if isinstance(a, dict) else {}
    esc = a.get("escenario") if a.get("escenario") in ESCENARIOS else respaldo["escenario"]
    part = a.get("particulas") if a.get("particulas") in PARTICULAS else None
    return {"escenario": esc, "particulas": part, "luz": a.get("luz") if a.get("luz") in LUCES else "dia",
            "lugar": str(a.get("lugar") or LUGARES_PINTADOS.get(esc, esc))[:200]}


def _prompt(temas: list[dict]) -> str:
    lista = "\n".join(f"{k + 1}. {' '.join(t['nombre'])} — {' '.join(t.get('escena') or [])[:220]}"
                      for k, t in enumerate(temas))
    return f"""Eres el director de arte de «El Calvo Explica» (animación 2D sencilla). Para cada tema elige el
lugar donde pasa (el fondo de sus escenas), partículas que se mueven y la luz.
Escenarios posibles: {", ".join(ESCENARIOS)}.
Partículas: {", ".join(PARTICULAS)} o null. Luz: {", ".join(LUCES)}.
«lugar»: una frase corta en español que describa ese lugar para pintarlo (sin personas ni animales).
Varía: dos temas seguidos no deberían tener el mismo escenario si se puede evitar.

TEMAS:
{lista}

Devuelve SOLO un JSON: {{"temas": [{{"n": 1, "escenario": "...", "particulas": null, "luz": "dia", "lugar": "..."}}, ...]}}"""


def elegir(temas: list[dict], ejecutar=None) -> list[dict]:
    """Un ambiente por tema. Con `ejecutar` (Claude) lo decide leyendo el guion; si falla o no hay, por palabras."""
    respaldo = [por_palabras(" ".join(t["nombre"]), " ".join(t.get("escena") or [])) for t in temas]
    if ejecutar is not None:
        try:
            from .. import claude_cli

            texto, _ = ejecutar(_prompt(temas))
            datos = claude_cli.extraer_json(texto)
            por_n = {int(x["n"]): x for x in datos.get("temas", []) if isinstance(x, dict) and "n" in x}
            return [_limpio(por_n.get(k + 1), respaldo[k]) for k in range(len(temas))]
        except Exception:  # noqa: BLE001 — sin Claude el video sale igual, con el ambiente por palabras
            pass
    return [_limpio(r, r) for r in respaldo]


# ------------------------------------------------------------------ fondos pintados (Google)

def prompt_fondo(lugar: str) -> str:
    return (f"Fondo ilustrado para una animación 2D sencilla: {lugar}. Estilo plano y limpio, colores pastel suaves y "
            "poco saturados, línea fina gris oscura, sin degradados fuertes. SIN personas, sin animales, sin "
            "personajes, sin texto, letras, números, marcas ni logos. El centro de la imagen queda despejado y "
            "simple (ahí se para el personaje); los detalles van en las orillas. El piso o el horizonte va en el "
            "tercio de abajo. Formato horizontal 16:9.")


def _pintar(c: Path, ambientes: list[dict], t, permiso: bool, proveedor) -> dict[int, Path]:
    from PIL import Image

    from ..costos import FrenoPresupuesto
    from .ilustraciones import proveedor_imagenes

    config = ConfigCostos.cargar()
    d = c / "fondos"
    d.mkdir(exist_ok=True)
    libro, p, frenado = LibroCostos(c, config), proveedor, False
    salida = {}
    for k, a in enumerate(ambientes):
        texto = prompt_fondo(a["lugar"])
        archivo = d / f"fondo_{hashlib.sha1(texto.encode()).hexdigest()[:12]}.png"
        if not archivo.exists() and not frenado:
            try:
                p = p or proveedor_imagenes(config)
                t.avisar(f"Fondo del tema {k + 1} de {len(ambientes)} con Google…")
                libro.autorizar(p.estimar_usd(texto, []), permiso=permiso)
                r = p.generar(texto, [])
                libro.registrar(modulo=MODULO, proveedor=r.proveedor, modelo=r.modelo, unidades=r.uso.unidades(),
                                costo_usd=r.uso.costo_usd, detalle=archivo.name)
                img = Image.open(io.BytesIO(r.png)).convert("RGB").resize((1920, 1080))
                Image.blend(img, Image.new("RGB", img.size, "white"), 0.18).save(archivo)   # un poco más pálido
            except FrenoPresupuesto as ex:
                frenado = True
                t.avisar(f"  {ex} Los demás fondos van por código.")
            except Exception as ex:  # noqa: BLE001 — un fondo que falla no frena el video
                t.avisar(f"  no se pudo pintar el fondo del tema {k + 1} ({str(ex)[:120]}): va por código")
        if archivo.exists():
            salida[k] = archivo
    gastado = sum(e.get("costo_usd", 0) for e in libro.entradas() if e.get("modulo") == MODULO)
    t.avisar(f"Fondos pintados: {len(salida)} de {len(ambientes)} (costo {formato_cop(config.a_cop(gastado))})")
    return salida


def fondos_faltantes(c: Path, n_temas: int) -> int:
    """Cuántos fondos faltan por pintar (lo ya pintado no se vuelve a pagar)."""
    d = c / "fondos"
    hechos = len(list(d.glob("fondo_*.png"))) if d.exists() else 0
    return max(0, n_temas - hechos)


# ------------------------------------------------------------------ aplicar al video

def _es_imagen_completa(esc: dict) -> bool:
    return any(e.get("pieza") == "imagen" and float((e.get("estado") or {}).get("ancho", 0)) >= 1900
               for e in esc.get("elementos", []))


def aplicar(c: Path, datos: dict, temas: list[dict], t, permiso: bool = False, proveedor=None, ejecutar=None,
            preset: dict | None = None) -> list[dict]:
    """Pone el ambiente de cada tema en sus escenas (modifica `datos`). Devuelve los ambientes usados."""
    preset = preset or C.cargar()
    if not preset.get("fondos_tema", True):
        return []
    guardado = c / "ambientes.json"
    nombres = [" ".join(x["nombre"]) for x in temas]
    previos = leer_json(guardado) if guardado.exists() else {}
    if previos.get("temas") == nombres:
        ambientes = previos["ambientes"]
    else:
        t.avisar("Eligiendo el lugar de cada tema…")
        ambientes = elegir(temas, ejecutar)
        escribir_json(guardado, {"temas": nombres, "ambientes": ambientes})
    pintados = _pintar(c, ambientes, t, permiso, proveedor) if preset.get("fondos_google") else {}
    k = -1
    for esc in datos["escenas"]:
        if esc.get("tipo") == "cuadricula":
            k = min(k + 1, len(ambientes) - 1)
            continue
        if k < 0 or _es_imagen_completa(esc):
            continue
        a = ambientes[k]
        lugar = f"archivo:{pintados[k]}" if k in pintados else a["escenario"]
        propio = esc.get("fondo") not in (None, "blanco")       # Claude eligió un lugar concreto para esa frase
        if esc.get("tipo") == "codigo":
            esc["fondo"] = f"lavado:{lugar}"
            continue
        if not propio:
            esc["fondo"] = lugar
        esc["ambiente"] = {"particulas": a["particulas"] if preset.get("particulas", True) else None,
                           "luz": a["luz"]}
    return ambientes


def resumen(ambientes: list[dict]) -> str:
    return "; ".join(f"{k + 1}: {a['escenario']}" + (f" + {a['particulas']}" if a.get("particulas") else "")
                     for k, a in enumerate(ambientes))
