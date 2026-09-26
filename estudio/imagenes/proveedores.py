"""Proveedores de imágenes (sección 5.4). El proveedor y el modelo salen de
`config/proveedores.json`; las tarifas, de `config/costos.json`.

El costo que se registra es el REAL de cada llamada, calculado con los tokens que
devuelve la API (`usageMetadata`), con las imágenes de referencia incluidas. Un
precio fijo por imagen esconde lo que cuestan las referencias adjuntas.
"""
from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..config import ConfigCostos, PrecioFaltante, clave_api

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
TIPOS_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


class ErrorProveedor(Exception):
    """Fallo de la llamada. `reintentable` dice si tiene sentido volver a pedir."""

    def __init__(self, mensaje: str, reintentable: bool = True, uso: "Uso | None" = None):
        super().__init__(mensaje)
        self.reintentable = reintentable
        self.uso = uso  # si la API cobró aunque no devolviera imagen


@dataclass
class Uso:
    tokens_entrada: int = 0
    tokens_entrada_imagen: int = 0
    tokens_salida: int = 0
    costo_usd: float = 0.0

    def unidades(self) -> dict[str, float]:
        return {"tokens_entrada": self.tokens_entrada,
                "tokens_entrada_imagen": self.tokens_entrada_imagen,
                "tokens_salida": self.tokens_salida}


@dataclass
class ResultadoImagen:
    png: bytes
    uso: Uso
    modelo: str
    proveedor: str
    extra: dict = field(default_factory=dict)


class Proveedor(Protocol):
    nombre: str
    modelo: str

    def estimar_usd(self, prompt: str, referencias: list[Path]) -> float: ...

    def generar(self, prompt: str, referencias: list[Path]) -> ResultadoImagen: ...


class _Tarifa:
    def __init__(self, config: ConfigCostos, modelo: str):
        t = config.precios.get("imagenes_por_modelo", {}).get(modelo)
        if not t:
            raise PrecioFaltante(f"imagenes_por_modelo:{modelo}")
        self.entrada = t["entrada_por_millon_tokens"] / 1e6
        self.salida = t["salida_por_millon_tokens"] / 1e6
        self.salida_por_imagen = t["tokens_salida_por_imagen"]
        self.por_referencia = t["tokens_por_imagen_de_referencia"]

    def costo(self, tokens_entrada: int, tokens_salida: int) -> float:
        return tokens_entrada * self.entrada + tokens_salida * self.salida

    def estimar(self, prompt: str, referencias: list[Path]) -> float:
        tin = len(prompt) / 3.5 + len(referencias) * self.por_referencia
        return self.costo(int(tin), self.salida_por_imagen)


class ProveedorGemini:
    """API de Gemini directa (familia Nano Banana), modo normal."""

    nombre = "gemini"

    def __init__(self, config: ConfigCostos, modelo: str, relacion_aspecto: str = "16:9",
                 tiempo_max_s: float = 120, variable_clave: str = "GEMINI_API_KEY", sesion=None):
        import requests  # solo hace falta con el proveedor real

        self.modelo = modelo
        self.aspecto = relacion_aspecto
        self.tiempo_max_s = tiempo_max_s
        self.tarifa = _Tarifa(config, modelo)
        self.clave = clave_api(variable_clave)
        if not self.clave:
            raise ErrorProveedor(f"Falta {variable_clave} en .env", reintentable=False)
        self.sesion = sesion or requests.Session()

    def estimar_usd(self, prompt: str, referencias: list[Path]) -> float:
        return self.tarifa.estimar(prompt, referencias)

    def _cuerpo(self, prompt: str, referencias: list[Path]) -> dict:
        partes: list[dict] = []
        for ref in referencias:
            mime = TIPOS_MIME.get(ref.suffix.lower(), "image/png")
            partes.append({"inline_data": {"mime_type": mime,
                                           "data": base64.b64encode(ref.read_bytes()).decode()}})
        partes.append({"text": prompt})
        return {
            "contents": [{"role": "user", "parts": partes}],
            "generationConfig": {"responseModalities": ["IMAGE"],
                                 "imageConfig": {"aspectRatio": self.aspecto}},
        }

    def _uso(self, datos: dict) -> Uso:
        u = datos.get("usageMetadata") or {}
        tin = int(u.get("promptTokenCount") or 0)
        tout = int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)
        timg = sum(int(d.get("tokenCount") or 0) for d in u.get("promptTokensDetails") or []
                   if d.get("modality") == "IMAGE")
        return Uso(tin, timg, tout, self.tarifa.costo(tin, tout))

    def generar(self, prompt: str, referencias: list[Path]) -> ResultadoImagen:
        r = self.sesion.post(GEMINI_URL.format(modelo=self.modelo),
                             headers={"x-goog-api-key": self.clave, "Content-Type": "application/json"},
                             data=json.dumps(self._cuerpo(prompt, referencias)),
                             timeout=self.tiempo_max_s)
        if r.status_code == 429 or r.status_code >= 500:
            espera = _espera_sugerida(r)
            if espera:
                time.sleep(min(espera, 60))
            raise ErrorProveedor(f"HTTP {r.status_code}: {r.text[:300]}", reintentable=True)
        if r.status_code >= 400:
            raise ErrorProveedor(f"HTTP {r.status_code}: {r.text[:300]}", reintentable=False)
        datos = r.json()
        uso = self._uso(datos)
        for cand in datos.get("candidates") or []:
            for parte in (cand.get("content") or {}).get("parts") or []:
                inline = parte.get("inlineData") or parte.get("inline_data")
                if inline and inline.get("data"):
                    return ResultadoImagen(base64.b64decode(inline["data"]), uso, self.modelo, self.nombre,
                                           {"finishReason": cand.get("finishReason")})
        motivo = ";".join(str(c.get("finishReason")) for c in datos.get("candidates") or []) \
            or str((datos.get("promptFeedback") or {}).get("blockReason"))
        raise ErrorProveedor(f"la respuesta no trae imagen (motivo: {motivo})", reintentable=True, uso=uso)


def _espera_sugerida(r) -> float | None:
    cab = r.headers.get("retry-after")
    if cab:
        try:
            return float(cab)
        except ValueError:
            pass
    try:
        for d in r.json().get("error", {}).get("details", []):
            if "retryDelay" in d:
                return float(str(d["retryDelay"]).rstrip("s"))
    except Exception:  # noqa: BLE001
        pass
    return None


class ProveedorTogether:
    """Together AI (google/flash-image-2.5 y otros). Cobra por imagen generada.

    Las referencias van en `reference_images`, que es el único parámetro de
    imagen que acepta este modelo en Together. Se mandan como data URI para no
    tener que subir los archivos a ningún sitio.
    """

    nombre = "together"

    def __init__(self, config: ConfigCostos, modelo: str, ancho: int = 1344, alto: int = 768,
                 tiempo_max_s: float = 120, variable_clave: str = "TOGETHER_API_KEY", sesion=None, **_):
        import requests

        t = config.precios.get("imagenes_por_modelo", {}).get(modelo) or {}
        if t.get("precio_por_imagen") is None:
            raise PrecioFaltante(f"imagenes_por_modelo:{modelo}.precio_por_imagen")
        self.precio = float(t["precio_por_imagen"])
        self.modelo, self.ancho, self.alto, self.tiempo_max_s = modelo, ancho, alto, tiempo_max_s
        self.clave = clave_api(variable_clave)
        if not self.clave:
            raise ErrorProveedor(f"Falta {variable_clave} en .env", reintentable=False)
        self.sesion = sesion or requests.Session()

    def estimar_usd(self, prompt: str, referencias: list[Path]) -> float:
        return self.precio

    def generar(self, prompt: str, referencias: list[Path]) -> ResultadoImagen:
        cuerpo: dict = {"model": self.modelo, "prompt": prompt, "n": 1,
                        "width": self.ancho, "height": self.alto, "response_format": "base64"}
        if referencias:
            cuerpo["reference_images"] = [
                f"data:{TIPOS_MIME.get(r.suffix.lower(), 'image/png')};base64,"
                + base64.b64encode(r.read_bytes()).decode() for r in referencias]
        r = self.sesion.post(TOGETHER_URL, headers={"Authorization": f"Bearer {self.clave}",
                                                    "Content-Type": "application/json"},
                             data=json.dumps(cuerpo), timeout=self.tiempo_max_s)
        if r.status_code == 429 or r.status_code >= 500:
            espera = _espera_sugerida(r)
            if espera:
                time.sleep(min(espera, 60))
            raise ErrorProveedor(f"HTTP {r.status_code}: {r.text[:300]}", reintentable=True)
        if r.status_code >= 400:
            raise ErrorProveedor(f"HTTP {r.status_code}: {r.text[:300]}", reintentable=False)
        datos = (r.json().get("data") or [{}])[0]
        uso = Uso(tokens_salida=0, costo_usd=self.precio)
        if datos.get("b64_json"):
            return ResultadoImagen(base64.b64decode(datos["b64_json"]), uso, self.modelo, self.nombre)
        if datos.get("url"):
            img = self.sesion.get(datos["url"], timeout=self.tiempo_max_s)
            if img.status_code == 200:
                return ResultadoImagen(img.content, uso, self.modelo, self.nombre)
        raise ErrorProveedor("la respuesta no trae imagen", reintentable=True)


class ProveedorSimulado:
    """Sin red ni gasto real: dibuja un cartel con el prompt y cobra lo que cobraría
    el modelo configurado, para probar el flujo, el freno y la proyección."""

    nombre = "simulado"

    def __init__(self, config: ConfigCostos, modelo: str = "simulado", fallar_cada: int = 0, **_):
        self.modelo = modelo
        self.tarifa = _Tarifa(config, modelo)
        self.fallar_cada = fallar_cada
        self.llamadas = 0

    def estimar_usd(self, prompt: str, referencias: list[Path]) -> float:
        return self.tarifa.estimar(prompt, referencias)

    def generar(self, prompt: str, referencias: list[Path]) -> ResultadoImagen:
        from PIL import Image, ImageDraw

        self.llamadas += 1
        tin = int(len(prompt) / 3.5 + len(referencias) * self.tarifa.por_referencia)
        uso = Uso(tin, len(referencias) * self.tarifa.por_referencia, self.tarifa.salida_por_imagen,
                  self.tarifa.costo(tin, self.tarifa.salida_por_imagen))
        if self.fallar_cada and self.llamadas % self.fallar_cada == 0:
            raise ErrorProveedor("fallo simulado", reintentable=True, uso=uso)
        img = Image.new("RGB", (1344, 768), (58, 58, 64))
        d = ImageDraw.Draw(img)
        d.text((40, 40), "SIMULADO", fill=(255, 200, 80))
        palabras, linea, y = prompt.split(), "", 90
        for p in palabras:
            if len(linea) + len(p) > 110:
                d.text((40, y), linea, fill=(230, 230, 230)); y += 18; linea = ""
            linea += p + " "
        d.text((40, y), linea, fill=(230, 230, 230))
        d.text((40, 720), f"{len(referencias)} referencias", fill=(160, 160, 170))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return ResultadoImagen(buf.getvalue(), uso, self.modelo, self.nombre)


def crear_proveedor(config: ConfigCostos, ajustes: dict, nombre: str | None = None) -> Proveedor:
    nombre = nombre or ajustes.get("proveedor", "gemini")
    op = (ajustes.get("opciones") or {}).get(nombre, {})
    tiempo = ajustes.get("tiempo_max_s", 120)
    if nombre == "gemini":
        return ProveedorGemini(config, op.get("modelo", "gemini-2.5-flash-image"),
                               ajustes.get("relacion_aspecto", "16:9"), tiempo,
                               op.get("variable_clave", "GEMINI_API_KEY"))
    if nombre == "together":
        return ProveedorTogether(config, op.get("modelo", "google/flash-image-2.5"),
                                 op.get("ancho", 1344), op.get("alto", 768), tiempo,
                                 op.get("variable_clave", "TOGETHER_API_KEY"))
    if nombre == "simulado":
        return ProveedorSimulado(config)
    raise ValueError(f"proveedor de imágenes desconocido: {nombre}")
