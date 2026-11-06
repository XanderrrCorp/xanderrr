"""Plan de escenas AUTOMÁTICO de los bloques [PROFESOR] (06-11, el dueño aprobó la prueba hecha a mano: «si me gusta»).

Claude (modelo liviano, va por la suscripción: 0 pesos) lee el guion y, para cada bloque del Profesor, elige escenas
del motor de los primeros videos (tipografía, frase, número de la regla, libreta, lista, dato, cita, preguntas, camino
y la TABLA del video) con sus textos cortos y la frase de la voz donde entra cada una. Xandart valida todo (tipos,
largos, letras que la fuente no tiene), pone cada escena en el segundo exacto en que la voz dice esa frase, y si algo
no sirve lo cambia por una escena segura. Sin Claude: plan por reglas. Se guarda en plan_escenas.json (no se repite).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

SEG_POR_ESCENA = 4.2                    # ninguna escena muy larga (los primeros videos: ≤9 s; aquí más dopamina)
MIN_ESCENA = 2.2
TIPOS = {"tipografia", "fondo_frase", "numero", "libreta", "lista3", "dato", "cita", "preguntas", "camino", "tabla", "burbujas"}
SIN_PROFESOR = {"libreta", "lista3", "tabla", "preguntas", "cita", "camino", "burbujas", "dato", "fondo_frase"}  # su texto es ancho
MODOS_TABLA = {"presentar", "columnas", "filas", "fila", "escribir", "completa"}

CATALOGO = """ESCENAS (campos exactos; textos en español, cortos; sin emojis, sin flechas ni símbolos raros):
- tipografia: {"lineas": [["TEXTO", "blanco"|"dorado"], …] 1-3 líneas de ≤16 letras, MAYÚSCULAS; "fondo": "noche"|"vino"}
- fondo_frase: {"frase": "frase de ≤60 letras con UNA *palabra* entre asteriscos", "fondo": "noche"|"vino"}
- numero: {"n_punto": 1-8, "etiqueta": "REGLA"|"PASO"|"CLAVE", "titulo": ["LÍNEA 1", "LÍNEA 2"] (≤20 letras c/u), "fondo": "vino"}
- libreta: {"titulo": "≤12 letras", "lineas": ["≤22 letras", …] 1-3}
- lista3: {"titulo": "≤24 letras", "items": [["TÍTULO ≤14", "explicación ≤40"], …] exactamente 3}
- dato: {"valor": número entero, "unidad": "≤14 letras", "texto": "≤80 letras"}
- cita: {"frase": "≤110 letras", "autor": "≤50 letras" (si no es una cita real conocida: "Una idea del canal")}
- preguntas: {"preguntas": ["pregunta ≤70 letras", …] 1-3}
- camino: {"paradas": ["≤8 letras", …] 3-6, "actual": 0 (todo el camino) o el número de la parada}
- burbujas: {"titulo": "≤24 letras", "frases": ["≤30 letras", …] 2-4}  (lo que la gente piensa o se dice)
- tabla: {"modo": "presentar"|"columnas"|"filas"|"fila"|"escribir"|"completa", "fila": 1-5 (fila/escribir),
          "columnas": [1,2,3] (escribir), "llenas": cuántas filas ya están escritas}
  La TABLA es una sola para todo el video y SOLO si el video tiene exactamente 5 reglas: 5 filas (una por regla) y
  3 columnas. Va en "tabla_video": {"titulo": "TU TABLA DE …", "columnas": [3 títulos ≤16], "filas": [5 nombres ≤16],
  "celdas": [[3 textos ≤40] × 5]}. Si no hay 5 reglas, "tabla_video": null y no uses escenas tabla."""

REGLAS = """REGLAS:
- Cada bloque [PROFESOR] lleva una escena cada ~{seg} s (un bloque de 20 s ≈ 5 escenas). Nunca dos del mismo tipo seguidas.
- "desde": las primeras 3-6 palabras EXACTAS de la voz donde entra la escena (copiadas del texto del bloque). La primera
  escena de cada bloque: "desde": "" (empieza con el bloque).
- "profesor": "lado" (el Profesor grande a la izquierda; la escena se corre a la derecha) en la primera escena del bloque y
  en los llamados (suscribirse, comentar); "esquina" en algunas tipografías y frases; null en libreta, lista3, tabla,
  preguntas, cita, camino, burbujas y dato.
- Lo que va en pantalla RESUME la voz con fuerza (no la copia entera): la palabra clave en dorado, cifras grandes, la regla
  con su número. Al inicio de cada regla, una escena «numero».
- Varía: tipografía y frases para el ritmo; libreta, lista, dato, camino, preguntas o cita cuando la voz lo pide."""


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", "".join(c for c in s if not unicodedata.combining(c)))).strip()


def _corta(s, n: int) -> str:
    s = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ¿?¡!.,:;*'\"%$-]", "", str(s or "")).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0]


def prompt(bloques: list[dict]) -> str:
    lineas = []
    for b in bloques:
        if b["tipo"] == "profesor":
            lineas.append(f'[PROFESOR id={b["id"]} dura={b["ranura"]:.0f}s] {b["texto"]}')
        else:
            lineas.append(f'[{b["tipo"].upper()}] {" ".join(b["texto"].split()[:25])}…')
    return ("Eres el editor de un canal de YouTube de desarrollo personal (Código del Éxito). Arma las escenas animadas "
            "de los bloques [PROFESOR] de este guion (los demás bloques van con stock o aura y no llevan escenas).\n\n"
            + CATALOGO + "\n\n" + REGLAS.format(seg=SEG_POR_ESCENA) + "\n\nGUION:\n" + "\n".join(lineas)
            + '\n\nResponde SOLO el JSON: {"tabla_video": … o null, "bloques": {"<id>": [{"tipo": …, "desde": …, '
              '"profesor": …, …campos}]}}')


def _tiempo_de(desde: str, b: dict) -> float | None:
    """segundo (dentro del bloque) en que la voz dice `desde`, por los trozos con tiempo del bloque"""
    if not desde:
        return 0.0
    objetivo = _norm(desde).split()[:4]
    palabras = []
    for z in b.get("trozos", []):
        ws = _norm(z["texto"]).split()
        for k, w in enumerate(ws):
            palabras.append((w, z["ini"] + (z["fin"] - z["ini"]) * k / max(1, len(ws))))
    for i in range(len(palabras) - len(objetivo) + 1):
        if [p[0] for p in palabras[i:i + len(objetivo)]] == objetivo:
            return round(palabras[i][1] - b["inicio"], 3)
    return None


def _segura(texto: str, k: int) -> dict:
    """escena de respaldo: una tipografía con las palabras más largas de la frase"""
    ws = [w for w in re.findall(r"[\wáéíóúñÁÉÍÓÚÑ]+", texto) if len(w) > 3][:6] or ["CÓDIGO DEL ÉXITO"]
    lineas, linea = [], ""
    for w in ws:
        if len(linea) + len(w) + 1 > 16 and linea:
            lineas.append(linea); linea = w
        else:
            linea = (linea + " " + w).strip()
    lineas.append(linea)
    lineas = lineas[:3]
    return {"tipo": "tipografia", "lineas": [[l.upper(), "dorado" if i == len(lineas) - 1 else "blanco"] for i, l in enumerate(lineas)],
            "fondo": "noche" if k % 2 else "vino"}


def _arreglar(e: dict, k: int, texto: str, tabla_ok: bool) -> dict:
    tipo = e.get("tipo")
    try:
        if tipo == "tipografia":
            ls = [[_corta(l[0], 18).upper(), "dorado" if l[1] == "dorado" else "blanco"] for l in e["lineas"][:3] if _corta(l[0], 18)]
            assert ls
            return {"tipo": tipo, "lineas": ls, "fondo": e.get("fondo") if e.get("fondo") in ("noche", "vino") else "noche"}
        if tipo == "fondo_frase":
            f = _corta(e["frase"], 64)
            assert f
            return {"tipo": tipo, "frase": f if "*" in f else f, "fondo": e.get("fondo") if e.get("fondo") in ("noche", "vino") else "vino"}
        if tipo == "numero":
            return {"tipo": tipo, "n_punto": max(1, min(8, int(e["n_punto"]))), "etiqueta": _corta(e.get("etiqueta") or "REGLA", 10).upper(),
                    "titulo": [_corta(x, 22).upper() for x in (e.get("titulo") or [])[:2]] or ["REGLA"], "fondo": "vino", "lado": True}
        if tipo == "libreta":
            return {"tipo": tipo, "titulo": _corta(e.get("titulo") or "NOTA", 12).upper(), "lineas": [_corta(x, 24) for x in e["lineas"][:3]]}
        if tipo == "lista3":
            items = [[_corta(a, 16).upper(), _corta(b2, 44)] for a, b2 in e["items"][:3]]
            assert len(items) == 3
            return {"tipo": tipo, "titulo": _corta(e.get("titulo"), 26).upper(), "items": items}
        if tipo == "dato":
            return {"tipo": tipo, "valor": int(e["valor"]), "unidad": _corta(e.get("unidad"), 14).upper(), "texto": _corta(e.get("texto"), 84)}
        if tipo == "cita":
            return {"tipo": tipo, "frase": _corta(e["frase"], 115), "autor": _corta(e.get("autor") or "Una idea del canal", 52)}
        if tipo == "preguntas":
            ps = [_corta(p, 72) for p in e["preguntas"][:3] if _corta(p, 72)]
            assert ps
            return {"tipo": tipo, "preguntas": ps}
        if tipo == "camino":
            ps = [_corta(p, 8).upper() for p in e["paradas"][:6]]
            assert 3 <= len(ps)
            return {"tipo": tipo, "paradas": ps, "actual": max(0, min(len(ps), int(e.get("actual") or 0)))}
        if tipo == "burbujas":
            fs = [_corta(f, 32) for f in e["frases"][:4]]
            assert len(fs) >= 2
            return {"tipo": tipo, "titulo": _corta(e.get("titulo"), 26).upper(), "frases": fs}
        if tipo == "tabla" and tabla_ok and e.get("modo") in MODOS_TABLA:
            out = {"tipo": tipo, "modo": e["modo"], "llenas": max(0, min(5, int(e.get("llenas") or 0)))}
            if e["modo"] in ("fila", "escribir"):
                out["fila"] = max(1, min(5, int(e["fila"])))
            if e["modo"] == "escribir":
                out["columnas"] = sorted({max(1, min(3, int(c))) for c in (e.get("columnas") or [1, 2, 3])})
            return out
    except (KeyError, TypeError, ValueError, AssertionError, IndexError):
        pass
    return _segura(texto, k)


def _tabla_valida(t) -> dict | None:
    try:
        tab = {"titulo": _corta(t.get("titulo") or "TU TABLA", 30).upper(), "columnas": [_corta(c, 18) for c in t["columnas"][:3]],
               "filas": [_corta(f, 18) for f in t["filas"][:5]], "celdas": [[_corta(c, 42) for c in fila[:3]] for fila in t["celdas"][:5]]}
        assert len(tab["columnas"]) == 3 and len(tab["filas"]) == 5 and all(len(f) == 3 for f in tab["celdas"]) and len(tab["celdas"]) == 5
        return tab
    except (KeyError, TypeError, AssertionError, AttributeError):
        return None


def validar(datos: dict, bloques: list[dict]) -> dict:
    """{id: [escenas con «inicio» en segundos del bloque]} listo para escenas_bloque"""
    tabla = _tabla_valida(datos.get("tabla_video")) if isinstance(datos.get("tabla_video"), dict) else None
    salida = {}
    for b in bloques:
        if b["tipo"] != "profesor":
            continue
        crudas = (datos.get("bloques") or {}).get(str(b["id"])) or []
        escenas, ultimo_tipo = [], None
        for k, e in enumerate(crudas if isinstance(crudas, list) else []):
            if not isinstance(e, dict):
                continue
            t = 0.0 if not escenas else _tiempo_de(str(e.get("desde") or ""), b)
            if t is None or (escenas and t - escenas[-1]["inicio"] < MIN_ESCENA) or t > b["ranura"] - MIN_ESCENA:
                continue
            x = _arreglar(e, k, b["texto"], tabla is not None)
            if x["tipo"] == ultimo_tipo and x["tipo"] != "tabla":
                continue
            if x["tipo"] == "tabla":
                x["tabla"] = tabla
            prof = e.get("profesor") if e.get("profesor") in ("lado", "esquina") else None
            if x["tipo"] in SIN_PROFESOR:
                prof = None
            if prof == "lado" and x["tipo"] in ("tipografia", "numero"):
                x["lado"] = True
            x["profesor"] = prof
            x["inicio"] = round(t, 3)
            escenas.append(x)
            ultimo_tipo = x["tipo"]
        if not escenas:
            escenas = respaldo(b)
        escenas[0]["inicio"] = 0.0
        salida[str(b["id"])] = escenas
    return salida


def respaldo(b: dict) -> list[dict]:
    """sin Claude: una escena por oración (o cada ~SEG_POR_ESCENA s), tipografía y frase alternadas, el Profesor al inicio"""
    oraciones = [o for o in re.split(r"(?<=[.!?])\s+", b["texto"]) if o.strip()]
    out = []
    for k, o in enumerate(oraciones):
        t = 0.0 if k == 0 else _tiempo_de(" ".join(o.split()[:4]), b)
        if t is None or (out and t - out[-1]["inicio"] < MIN_ESCENA) or t > b["ranura"] - MIN_ESCENA:
            continue
        if k % 2 == 1 and len(o) <= 64:
            ws = o.split()
            clave = max(ws, key=len)
            e = {"tipo": "fondo_frase", "frase": o.replace(clave, f"*{clave}*", 1), "fondo": "noche"}
        else:
            e = _segura(o, k)
        e["profesor"] = "lado" if k == 0 and e["tipo"] == "tipografia" else ("esquina" if e["tipo"] == "tipografia" else None)
        if e["profesor"] == "lado":
            e["lado"] = True
        e["inicio"] = round(t, 3)
        out.append(e)
    return out or [{**_segura(b["texto"], 0), "profesor": "lado", "lado": True, "inicio": 0.0}]


def planear(trabajo: Path, bloques: list[dict], avisar=print, ejecutar=None) -> dict:
    profes = [b for b in bloques if b["tipo"] == "profesor"]
    huella = hashlib.sha1(json.dumps([[b["id"], b["texto"], round(b["ranura"], 1)] for b in profes], ensure_ascii=False).encode()).hexdigest()[:12]
    ruta = trabajo / "plan_escenas.json"
    if ruta.exists():
        guardado = json.loads(ruta.read_text("utf-8"))
        if guardado.get("huella") == huella:
            return guardado["bloques"]
    datos: dict = {}
    try:
        from .. import claude_cli

        avisar("Claude está armando las escenas de los bloques del Profesor…")
        texto, _ = (ejecutar or claude_cli.revisor)(prompt(bloques), cwd=trabajo)
        datos = claude_cli.extraer_json(texto) or {}
    except Exception as ex:  # noqa: BLE001 — sin Claude, plan por reglas
        avisar(f"  sin Claude esta vez ({str(ex)[:120]}): escenas por reglas")
    plan = validar(datos if isinstance(datos, dict) else {}, bloques)
    ruta.write_text(json.dumps({"huella": huella, "bloques": plan, "crudo": datos}, ensure_ascii=False, indent=1), "utf-8")
    return plan
