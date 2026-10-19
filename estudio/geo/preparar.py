"""Prepara los datos de los mapas UNA vez (no corre en el PC del dueño: el resultado va en el repositorio).

- Fronteras: Natural Earth, Admin 0 – Countries 1:50m (dominio público), GeoJSON de
  github.com/nvkelso/natural-earth-vector. Se guardan por código ADM0_A3 (casi siempre el ISO-3166 alpha-3), con el
  nombre en español de Natural Earth (NAME_ES), el código alpha-2, la subregión, el punto para la etiqueta y los
  polígonos con coordenadas redondeadas a 0,02° (~2 km: de sobra a 1920 px).
- Banderas: flag-icons (licencia MIT), los SVG 4x3 por alpha-2 en minúscula.

Uso: python -m estudio.geo.preparar ne_50m_admin_0_countries.geojson carpeta/de/flag-icons
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

DATOS = Path(__file__).parent / "recursos"

# nombres de Natural Earth que en español latino se dicen distinto
NOMBRES = {"USA": "Estados Unidos", "GBR": "Reino Unido", "RUS": "Rusia", "KOR": "Corea del Sur",
           "PRK": "Corea del Norte", "COD": "República Democrática del Congo", "COG": "República del Congo",
           "CZE": "Chequia", "IRN": "Irán", "SYR": "Siria", "LAO": "Laos", "VNM": "Vietnam", "BOL": "Bolivia",
           "VEN": "Venezuela", "TZA": "Tanzania", "MDA": "Moldavia", "BRN": "Brunéi", "MKD": "Macedonia del Norte",
           "CIV": "Costa de Marfil", "TWN": "Taiwán", "PSX": "Palestina", "VAT": "Ciudad del Vaticano"}


def _redondear(anillo, paso=0.02):
    salida = []
    for x, y in anillo:
        p = [round(round(x / paso) * paso, 2), round(round(y / paso) * paso, 2)]
        if not salida or p != salida[-1]:
            salida.append(p)
    return salida if len(salida) >= 4 else None


def preparar(geojson: Path, flag_icons: Path) -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    datos = json.loads(geojson.read_text(encoding="utf-8"))
    paises = {}
    for f in datos["features"]:
        p = f["properties"]
        clave = p["ADM0_A3"]
        g = f["geometry"]
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        anillos = [r for poli in polis for r in [_redondear(poli[0])] if r]          # solo el borde exterior
        if not anillos:
            continue
        xs = [x for r in anillos for x, _ in r]
        ys = [y for r in anillos for _, y in r]
        a2 = p["ISO_A2_EH"] if p["ISO_A2_EH"] not in ("-99", None) else None
        paises[clave] = {"nombre": NOMBRES.get(clave, p["NAME_ES"]), "a2": a2,
                         "iso3": p["ISO_A3_EH"] if p["ISO_A3_EH"] != "-99" else clave,
                         "continente": p["CONTINENT"], "subregion": p["SUBREGION"],
                         "etiqueta": [round(p["LABEL_X"], 2), round(p["LABEL_Y"], 2)],
                         "caja": [min(xs), min(ys), max(xs), max(ys)], "anillos": anillos}
    (DATOS / "paises.json").write_text(json.dumps(paises, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    destino = DATOS / "banderas"
    destino.mkdir(exist_ok=True)
    usadas = {v["a2"].lower() for v in paises.values() if v["a2"]}
    for svg in (flag_icons / "flags" / "4x3").glob("*.svg"):
        if svg.stem in usadas:
            shutil.copy(svg, destino / svg.name)
    shutil.copy(flag_icons / "LICENSE", destino / "LICENSE-flag-icons.txt")
    print(f"{len(paises)} países, {len(list(destino.glob('*.svg')))} banderas")


if __name__ == "__main__":
    preparar(Path(sys.argv[1]), Path(sys.argv[2]))
