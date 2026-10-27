"""Claude por el CLI (`claude -p`), con la SUSCRIPCIÓN del dueño: no se paga por llamada.

Lecciones del código de referencia (pasos/cli_claude.py):
- Se quitan del entorno las variables de pago por uso (ANTHROPIC_API_KEY...):
  si están, el CLI cobra a la API en vez de a la suscripción.
- El aviso de cupo agotado llega DENTRO del JSON: se detecta y se muestra claro.
- En Windows, sin ventana negra por cada llamada.
"""
from __future__ import annotations

import contextvars
import functools
import json
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

PAGO_POR_USO = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")
# (19-10) Xandart no necesita las instrucciones de programador de Claude Code (~30.000 tokens por pedido del plan
# del dueño): va con un sistema corto y solo las herramientas que pide. Probado: «OK» pasó de ~32.000 a ~1.500 tokens.
SISTEMA_CORTO = ("Eres el asistente de Xandart, una herramienta que hace videos de YouTube en español. Responde "
                 "exactamente en el formato que pide cada mensaje. Usa una herramienta solo si el mensaje lo pide.")
_LIVIANO = {"ok": True}       # si el Claude instalado no entiende las opciones nuevas, vuelve a la forma de siempre
SIN_VENTANA = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if os.name == "nt" else {}


class ErrorClaude(RuntimeError):
    pass


# (27-10, el dueño: «un video gasta el 50 % de mi uso») cada pedido a Claude dentro de un proyecto queda anotado en
# <proyecto>/uso_claude.jsonl con el paso que lo hizo, para ver qué se come el plan (resumen_uso).
_PASO: contextvars.ContextVar[str | None] = contextvars.ContextVar("paso_claude", default=None)
USO = "uso_claude.jsonl"


@contextmanager
def paso(nombre: str):
    marca = _PASO.set(nombre)
    try:
        yield
    finally:
        _PASO.reset(marca)


def en_paso(nombre: str):
    """Decorador: todo lo que esa función le pida a Claude se anota con este paso."""
    def envolver(f):
        @functools.wraps(f)
        def con_paso(*a, **k):
            with paso(nombre):
                return f(*a, **k)
        return con_paso
    return envolver


def _anotar(cwd, modelo: str | None, sobre: dict, segundos: float) -> None:
    if not cwd or not (Path(cwd) / "proyecto.json").exists():
        return
    try:
        uso = sobre.get("usage") or {}
        usados = list((sobre.get("modelUsage") or {}).keys())
        fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "paso": _PASO.get() or "Otros",
                "modelo": modelo or (usados[0] if usados else "el de tu plan"),
                "entrada": int(uso.get("input_tokens") or 0) + int(uso.get("cache_creation_input_tokens") or 0)
                + int(uso.get("cache_read_input_tokens") or 0),
                "salida": int(uso.get("output_tokens") or 0),
                "equivalente_usd": round(float(sobre.get("total_cost_usd") or 0), 5), "segundos": round(segundos, 1)}
        with open(Path(cwd) / USO, "a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — anotar nunca frena un video
        pass


def resumen_uso(carpeta: Path) -> dict | None:
    """Cuánto del plan se llevó cada paso del video (en % del total: el peso de cada pedido según su modelo y largo)."""
    ruta = Path(carpeta) / USO
    if not ruta.exists():
        return None
    pasos: dict[str, dict] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            f = json.loads(linea)
        except json.JSONDecodeError:
            continue
        p = pasos.setdefault(f.get("paso") or "Otros", {"paso": f.get("paso") or "Otros", "pedidos": 0, "peso": 0.0,
                                                          "modelos": set(), "minutos": 0.0})
        p["pedidos"] += 1
        p["peso"] += float(f.get("equivalente_usd") or 0) or (int(f.get("entrada") or 0) + 5 * int(f.get("salida") or 0)) / 1e6
        p["modelos"].add(str(f.get("modelo")))
        p["minutos"] += float(f.get("segundos") or 0) / 60
    total = sum(p["peso"] for p in pasos.values()) or 1.0
    lista = sorted(pasos.values(), key=lambda p: -p["peso"])
    return {"pedidos": sum(p["pedidos"] for p in lista),
            "pasos": [{"paso": p["paso"], "pedidos": p["pedidos"], "porcentaje": round(100 * p["peso"] / total, 1),
                       "modelos": sorted(p["modelos"]), "minutos": round(p["minutos"], 1)} for p in lista]}


def _modelo_revisor() -> str:
    try:
        from .config import leer_config

        return (leer_config("proveedores.json").get("claude") or {}).get("modelo_revisor") or "sonnet"
    except Exception:  # noqa: BLE001
        return "sonnet"


def revisor(prompt: str, **k) -> tuple[str, dict]:
    """(27-10) Mirar imágenes (flechas y círculos, tapar al animal), revisar las fotos de Pexels, elegir lugares y
    reacciones: con el modelo liviano (Sonnet) y poco razonamiento, que gasta varias veces menos del plan. La
    historia del guion sigue con el modelo de siempre."""
    k.setdefault("modelo", _modelo_revisor())
    k.setdefault("pensamiento", 2000)
    return ejecutar(prompt, **k)


class SinCupo(ErrorClaude):
    """Se acabó el cupo de la suscripción: no se reintenta."""


class SinSesion(ErrorClaude):
    """El CLI no está instalado o no tiene sesión iniciada."""


def ejecutable() -> str | None:
    for nombre in ("claude", "claude.exe", "claude.cmd"):
        r = shutil.which(nombre)
        if r:
            return r
    for cand in (Path.home() / ".local" / "bin" / "claude.exe", Path.home() / ".local" / "bin" / "claude",
                 Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd"):
        if cand.exists():
            return str(cand)
    return None


def _sin_cupo(texto: str) -> bool:
    t = (texto or "").lower()
    return any(q in t for q in ("limit", "límite", "limite", "quota")) and \
        any(c in t for c in ("reset", "renue", "reach", "agotad", "exceed", "hit your"))


def ejecutar(prompt: str, *, cwd: Path | None = None, herramientas: list[str] | None = None,
             modelo: str | None = None, tiempo_max_s: int = 1200, pensamiento: int | None = None,
             lanzar=subprocess.run) -> tuple[str, dict]:
    """Devuelve (texto de la respuesta, sobre JSON del CLI). `pensamiento` limita los tokens de
    razonamiento (MAX_THINKING_TOKENS): con mucho razonamiento el guion tardaba ~14 minutos."""
    exe = ejecutable()
    if not exe:
        raise SinSesion("No encuentro el programa de Claude (Claude Code). Vuelve a correr el instalador de Xandart.")
    base = [exe, "-p", prompt, "--output-format", "json"]
    if modelo:
        base += ["--model", modelo]
    if herramientas:
        base += ["--allowedTools", ",".join(herramientas)]
    else:
        base += ["--disallowedTools", "Bash,Write,Edit,WebFetch,WebSearch,Task"]
    liviano = base + ["--system-prompt", SISTEMA_CORTO, "--tools", ",".join(herramientas) if herramientas else ""]
    cmd = liviano if _LIVIANO["ok"] else base
    entorno = {k: v for k, v in os.environ.items() if k not in PAGO_POR_USO}
    inicio = time.monotonic()
    if pensamiento is not None:
        entorno["MAX_THINKING_TOKENS"] = str(int(pensamiento))
    try:
        r = lanzar(cmd, cwd=str(cwd) if cwd else None, env=entorno, capture_output=True, text=True,
                   encoding="utf-8", timeout=tiempo_max_s, **SIN_VENTANA)
    except subprocess.TimeoutExpired as ex:
        raise ErrorClaude(f"Claude tardó más de {tiempo_max_s // 60} minutos y se detuvo.") from ex
    if cmd is liviano and r.returncode != 0 and _opcion_desconocida(r.stderr or r.stdout or ""):
        _LIVIANO["ok"] = False                  # Claude viejo: se repite como siempre (y ya no se vuelve a intentar)
        try:
            r = lanzar(base, cwd=str(cwd) if cwd else None, env=entorno, capture_output=True, text=True,
                       encoding="utf-8", timeout=tiempo_max_s, **SIN_VENTANA)
        except subprocess.TimeoutExpired as ex:
            raise ErrorClaude(f"Claude tardó más de {tiempo_max_s // 60} minutos y se detuvo.") from ex
    salida = (r.stdout or "").strip()
    try:
        sobre = json.loads(salida[salida.find("{"):]) if "{" in salida else {}
    except json.JSONDecodeError:
        sobre = {}
    texto = str(sobre.get("result") or "")
    if _sin_cupo(texto) or _sin_cupo(r.stderr or ""):
        raise SinCupo(f"Se acabó el cupo de tu suscripción de Claude: {texto or r.stderr}".strip())
    if r.returncode != 0 or sobre.get("is_error"):
        detalle = (texto or r.stderr or salida)[:400]
        if any(p in detalle.lower() for p in ("login", "log in", "authenticat", "/login", "sesión")):
            raise SinSesion("Claude no tiene sesión iniciada. Abre «Iniciar sesión en Claude» desde Xandart.")
        raise ErrorClaude(f"Claude devolvió un error: {detalle}")
    _anotar(cwd, modelo, sobre, time.monotonic() - inicio)
    return texto, sobre


def _opcion_desconocida(texto: str) -> bool:
    t = texto.lower()
    return "unknown option" in t or "unknown argument" in t or "unrecognized" in t


def extraer_json(texto: str):
    """El primer objeto JSON completo dentro del texto (tolera vallas ```json)."""
    t = texto.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("\n") + 1:] if "\n" in t else t
    ini = t.find("{")
    if ini < 0:
        raise ValueError("la respuesta no trae JSON")
    prof, en_cadena, escape = 0, False, False
    for i, ch in enumerate(t[ini:], ini):
        if en_cadena:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                en_cadena = False
            continue
        if ch == '"':
            en_cadena = True
        elif ch == "{":
            prof += 1
        elif ch == "}":
            prof -= 1
            if prof == 0:
                return json.loads(t[ini:i + 1])
    raise ValueError("JSON incompleto en la respuesta")
