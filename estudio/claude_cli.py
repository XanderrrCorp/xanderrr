"""Claude por el CLI (`claude -p`), con la SUSCRIPCIÓN del dueño: no se paga por llamada.

Lecciones del código de referencia (pasos/cli_claude.py):
- Se quitan del entorno las variables de pago por uso (ANTHROPIC_API_KEY...):
  si están, el CLI cobra a la API en vez de a la suscripción.
- El aviso de cupo agotado llega DENTRO del JSON: se detecta y se muestra claro.
- En Windows, sin ventana negra por cada llamada.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

PAGO_POR_USO = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")
SIN_VENTANA = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)} if os.name == "nt" else {}


class ErrorClaude(RuntimeError):
    pass


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
             modelo: str | None = None, tiempo_max_s: int = 1200, lanzar=subprocess.run) -> tuple[str, dict]:
    """Devuelve (texto de la respuesta, sobre JSON del CLI)."""
    exe = ejecutable()
    if not exe:
        raise SinSesion("No encuentro el programa de Claude (Claude Code). Vuelve a correr el instalador de Xandart.")
    cmd = [exe, "-p", prompt, "--output-format", "json"]
    if modelo:
        cmd += ["--model", modelo]
    if herramientas:
        cmd += ["--allowedTools", ",".join(herramientas)]
    else:
        cmd += ["--disallowedTools", "Bash,Write,Edit,WebFetch,WebSearch,Task"]
    entorno = {k: v for k, v in os.environ.items() if k not in PAGO_POR_USO}
    try:
        r = lanzar(cmd, cwd=str(cwd) if cwd else None, env=entorno, capture_output=True, text=True,
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
    return texto, sobre


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
