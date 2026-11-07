"""Video de prueba de Peligro Tropical ANIMADO, hecho en el PC del dueño (tarjeta NVIDIA).

Uso (desde la carpeta de Xandart Nueva, con su Python):
    python -m estudio.pt_animado.hacer_prueba                 # muestra el plan y lo que cuesta, NO gasta
    python -m estudio.pt_animado.hacer_prueba --permiso       # voz (MiniMax) + 6 animales (Google) + clips + video final
    python -m estudio.pt_animado.hacer_prueba --sin-google    # los animales quedan como la serpiente de prueba (no paga imágenes)

Guion: prueba/guion_granja.json (idea del dueño). Todo queda en Videos/Xandart/PT animado prueba/ y se puede retomar:
lo ya pagado (voz por frase, imagen por animal) no se vuelve a pedir. Pasos: voz → animales → plan → clips (Remotion) →
audio de la Fase 1 (música por sección, efectos, -14 LUFS) → subtítulos → video final + revisión (short_qa) + 3 cuadros.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
REMOTION = AQUI / "remotion"
GUION = AQUI / "prueba" / "guion_granja.json"
SR = 48000

# cada animal: dónde y con qué luz pasa su escena, alto en metros y cómo se pide la imagen
ANIMALES = {
    "gallina": {"escenario": "finca", "luz": "dia", "alto": 0.55, "en": "a hen (chicken)"},
    "ganso": {"escenario": "rio", "luz": "dia", "alto": 0.8, "en": "an angry white goose with open beak"},
    "chivo": {"escenario": "finca", "luz": "dia", "alto": 0.95, "en": "a goat with horns, head lowered ready to charge"},
    "cerdo": {"escenario": "finca", "luz": "amanecer", "alto": 0.95, "en": "a big pink pig"},
    "toro": {"escenario": "finca", "luz": "amanecer", "alto": 1.55, "en": "a big black bull with horns, snorting"},
    "caballo": {"escenario": "finca", "luz": "dia", "alto": 1.75, "en": "a brown horse rearing up on its hind legs"},
}
PROMPT = ("Cartoon illustration of {en}, full body, side view facing LEFT, thick clean black outlines, flat bright colors, "
          "simple two-tone cel shading, friendly 2D animation style, isolated on a pure white background, no ground, "
          "no shadow, no text")


def carpeta_trabajo() -> Path:
    c = Path.home() / "Videos" / "Xandart" / "PT animado prueba"
    c.mkdir(parents=True, exist_ok=True)
    return c


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ------------------------------------------------------------------------------------------------------------ voz
def leer_pcm(ruta: Path) -> np.ndarray:
    r = subprocess.run([ffmpeg(), "-v", "error", "-i", str(ruta), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768
    a = np.abs(x) > 0.01
    if not a.any():
        return x
    i, j = int(np.argmax(a)), len(x) - int(np.argmax(a[::-1]))
    return x[max(0, i - 480): j + 480]                                # sin silencios en los bordes


def pausa(f: dict, sig: dict | None) -> float:
    if sig is None:
        return 1.2
    if f["intencion"] == "revelacion" or sig["seccion"] != f["seccion"]:
        return 0.55
    return 0.25


def paso_voz(trabajo: Path, frases: list[dict], permiso: bool) -> tuple[np.ndarray, list[dict]]:
    from ..config import ConfigCostos, leer_config
    from ..voz import VozMiniMax
    d = trabajo / "voz"; d.mkdir(exist_ok=True)
    faltan = [k for k in range(len(frases)) if not (d / f"{k:02d}.mp3").exists()]
    if faltan:
        if not permiso:
            raise SystemExit(f"Faltan {len(faltan)} frases de voz (~{sum(len(frases[k]['texto']) for k in faltan)} letras, unos 20 pesos). "
                             "Corre con --permiso.")
        voz = VozMiniMax(ConfigCostos.cargar(), leer_config("proveedores.json")["voz"])
        for k in faltan:
            print(f"  voz {k + 1}/{len(frases)}")
            mp3, _ = voz.sintetizar(frases[k]["texto"])
            (d / f"{k:02d}.mp3").write_bytes(mp3)
    pista, t, salida = [], 0.0, []
    for k, f in enumerate(frases):
        x = leer_pcm(d / f"{k:02d}.mp3")
        salida.append({**f, "ini": round(t, 3), "fin": round(t + len(x) / SR, 3)})
        p = pausa(f, frases[k + 1] if k + 1 < len(frases) else None)
        pista += [x, np.zeros(int(p * SR), np.float32)]
        t += len(x) / SR + p
    return np.concatenate(pista), salida


# -------------------------------------------------------------------------------------------------------- animales
def sin_fondo(png: bytes, destino: Path) -> None:
    """fondo blanco → transparente (relleno desde los bordes, así el blanco de adentro del animal se queda)"""
    import cv2
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    mascara = np.zeros((h + 2, w + 2), np.uint8)
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        if img[y, x].min() > 225:
            cv2.floodFill(img.copy(), mascara, (x, y), 0, (18, 18, 18), (18, 18, 18), cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    fondo = mascara[1:-1, 1:-1] > 0
    fondo = cv2.morphologyEx(fondo.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    rgba[..., 3] = np.where(fondo, 0, 255).astype(np.uint8)
    rgba[..., 3] = cv2.GaussianBlur(rgba[..., 3], (3, 3), 0)
    cv2.imwrite(str(destino), rgba)


def paso_animales(trabajo: Path, nombres: list[str], permiso: bool, sin_google: bool) -> dict[str, str]:
    d = trabajo / "animales"; d.mkdir(exist_ok=True)
    rutas: dict[str, str] = {}
    faltan = [n for n in nombres if not (d / f"{n}.png").exists()]
    if faltan and not sin_google:
        if not permiso:
            raise SystemExit(f"Faltan {len(faltan)} imágenes de animales (~120 pesos c/u). Corre con --permiso o --sin-google.")
        from ..config import ConfigCostos, leer_config
        from ..imagenes.proveedores import crear_proveedor
        prov = crear_proveedor(ConfigCostos.cargar(), {**leer_config("proveedores.json")["imagenes"], "relacion_aspecto": "1:1"})
        for n in faltan:
            print(f"  imagen de {n}")
            res = prov.generar(PROMPT.format(en=ANIMALES[n]["en"]), [])
            (d / f"{n}_original.png").write_bytes(res.png)
            sin_fondo(res.png, d / f"{n}.png")
    for n in nombres:
        p = d / f"{n}.png"
        rutas[n] = p.resolve().as_uri() if p.exists() else "prueba"
    return rutas


# ------------------------------------------------------------------------------------------------------------ plan
def _clave(palabras: list[dict], patron: str, desde: float, hasta: float, defecto: float) -> float:
    import re
    from .audio.capa import _norm
    for p in palabras:
        if desde <= p["ini"] < hasta and re.match(patron, _norm(p["w"])):
            return p["ini"]
    return defecto


def planear(frases: list[dict], dur: float, imagenes: dict[str, str], animales: list[str]) -> list[dict]:
    """INTRO (gancho) → un ENCUENTRO por animal (de su frase a la siguiente) → CIERRE. Los clips cubren la voz sin huecos."""
    from .audio.capa import palabras_estimadas
    palabras = palabras_estimadas(frases)
    grupos: list[tuple[str, float]] = []                          # (sección, inicio)
    for f in frases:
        if not grupos or grupos[-1][0] != f["seccion"]:
            grupos.append((f["seccion"], f["ini"]))
    clips = []
    for k, (sec, ini) in enumerate(grupos):
        fin = grupos[k + 1][1] if k + 1 < len(grupos) else dur
        largo = round(fin - ini, 3)
        if sec == "gancho":
            clips.append({"comp": "Intro", "escenario": "finca", "luz": "amanecer", "animal": imagenes[animales[0]], "altoAnimal": ANIMALES[animales[0]]["alto"],
                          "claves": {"fin": largo, "gancho_fin": frases[0]["fin"] - ini, "botas": largo * 0.42, "revela": largo * 0.62, "susto": largo * 0.8}})
        elif sec.startswith("nivel_"):
            n = animales[int(sec.split("_")[1]) - 1]; a = ANIMALES[n]
            ap = _clave(palabras, r"(gallina|ganso|chivo|cerdo|toro|caballo)", ini, fin, ini + 0.6) - ini
            ataque = _clave(palabras, r"(picot|persig|embist|mordid|muert|patad|caid)", ini, fin, ini + largo * 0.7) - ini
            clips.append({"comp": "Encuentro", "escenario": a["escenario"], "luz": a["luz"], "animal": imagenes[n], "altoAnimal": a["alto"],
                          "claves": {"fin": largo, "aparece": max(0.3, ap), "reaccion": max(ap + 1.0, min(ataque - 0.8, largo - 1.5)),
                                     "muerde": min(max(ataque, ap + 1.8), largo - 0.4)}})
        else:
            com = _clave(palabras, r"(coment|cuent)", ini, fin, ini + largo * 0.55) - ini
            clips.append({"comp": "Cierre", "escenario": "casa", "luz": "noche", "animal": None,
                          "claves": {"fin": largo, "remate": 0.6, "comenta": com}})
    for k, c in enumerate(clips):
        c["nombre"] = f"{k:02d}_{c['comp'].lower()}"
        c["props"] = {"escenario": c.pop("escenario"), "luz": c.pop("luz"), "animal": c.pop("animal"), "formato": "16:9",
                      "claves": {kk: round(v, 2) for kk, v in c.pop("claves").items()}, **({"altoAnimal": c.pop("altoAnimal")} if "altoAnimal" in c else {})}
    return clips


# ----------------------------------------------------------------------------------------------------------- clips
def paso_clips(trabajo: Path, clips: list[dict]) -> list[Path]:
    d = trabajo / "clips"; d.mkdir(exist_ok=True)
    faltan = [c for c in clips if not (d / f"{c['nombre']}.mp4").exists()]
    if faltan:
        node = shutil.which("node")
        if not node:
            raise SystemExit("No encuentro Node.js. Instálalo (winget install OpenJS.NodeJS.LTS) y vuelve a correr.")
        if not (REMOTION / "node_modules").exists():
            subprocess.run([shutil.which("npm") or "npm", "install", "--no-audit", "--no-fund"], cwd=REMOTION, check=True, shell=sys.platform == "win32")
        lista = trabajo / "lista_clips.json"
        lista.write_text(json.dumps([{"comp": c["comp"], "nombre": c["nombre"], "props": c["props"]} for c in faltan], ensure_ascii=False), encoding="utf-8")
        subprocess.run([node, "scripts/clips.mjs", str(d), str(lista), "2", "1"], cwd=REMOTION, check=True)
        limpiar_bundles()
    return [d / f"{c['nombre']}.mp4" for c in clips]


def limpiar_bundles() -> None:
    """borra solo los bundles viejos de Remotion (remotion-webpack-bundle-*) de la carpeta temporal (regla del dueño)"""
    import tempfile
    for p in Path(tempfile.gettempdir()).glob("remotion-webpack-bundle-*"):
        shutil.rmtree(p, ignore_errors=True)


# ------------------------------------------------------------------------------------------------------ subtítulos
def ass(frases: list[dict], destino: Path) -> None:
    from .audio.capa import palabras_estimadas
    def ts(t):
        return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
    L = ["[Script Info]", "PlayResX: 1920", "PlayResY: 1080", "", "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
         "Style: Sub,Arial Black,86,&H00FFFFFF,&H00000000,&H64000000,1,1,7,3,2,80,80,120", "", "[Events]",
         "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    pal = palabras_estimadas(frases)
    k = 0
    while k < len(pal):                                            # de 1 a 3 palabras por subtítulo
        g = pal[k:k + 3]
        if len(g) > 1 and any(p["w"].endswith((".", ",", "?", ":")) for p in g[:-1]):
            g = g[:next(i for i, p in enumerate(g) if p["w"].endswith((".", ",", "?", ":"))) + 1]
        L.append(f"Dialogue: 0,{ts(g[0]['ini'])},{ts(g[-1]['fin'])},Sub,,0,0,0,,{' '.join(p['w'] for p in g).upper()}")
        k += len(g)
    destino.write_text("\n".join(L), encoding="utf-8")


# ------------------------------------------------------------------------------------------------------------ todo
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--permiso", action="store_true", help="deja gastar en voz e imágenes")
    ap.add_argument("--sin-google", action="store_true", help="animales con la serpiente de prueba (no paga imágenes)")
    a = ap.parse_args()
    from .audio import capa, dsp
    g = json.loads(GUION.read_text(encoding="utf-8"))
    trabajo = carpeta_trabajo()
    print("Carpeta:", trabajo)
    letras = sum(len(f["texto"]) for f in g["frases"])
    print(f"Costo: voz ~{letras} letras (unos 20 pesos) + {len(g['animales'])} imágenes de Google (~120 pesos c/u)"
          + (" — sin Google" if a.sin_google else ""))
    if not a.permiso and not (trabajo / "voz").exists():
        print("Nada gastado. Para hacerlo: python -m estudio.pt_animado.hacer_prueba --permiso"); return
    voz, frases = paso_voz(trabajo, g["frases"], a.permiso)
    dur = len(voz) / SR
    (trabajo / "frases.json").write_text(json.dumps({"duracion": dur, "frases": frases}, ensure_ascii=False, indent=1), encoding="utf-8")
    imagenes = paso_animales(trabajo, g["animales"], a.permiso, a.sin_google)
    clips = planear(frases, dur, imagenes, g["animales"])
    (trabajo / "plan.json").write_text(json.dumps(clips, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Plan: {len(clips)} clips, {dur:.1f} s todo animado")
    rutas = paso_clips(trabajo, clips)
    # imagen: clips pegados
    (trabajo / "concat.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in rutas), encoding="utf-8")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "imagen.mp4"], cwd=trabajo, check=True)
    # sonido: capa de la Fase 1 sobre la voz
    res = capa.construir(voz, frases)
    capa.guardar(res, trabajo / "audio")
    print(f"Audio: {res.lufs} LUFS, pico {res.pico_dbtp} dBTP")
    ass(frases, trabajo / "subs.ass")
    final = trabajo / "peligro_tropical_animado_prueba.mp4"
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", "imagen.mp4", "-i", str(Path("audio") / "mezcla.wav"), "-vf", "ass=subs.ass",
                    "-map", "0:v", "-map", "1:a", *__import__("estudio.render", fromlist=["x"])._argumentos_codificador(ffmpeg(), "medium", "18", None), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", final.name], cwd=trabajo, check=True)
    # revisión automática (cuadros negros, congelados, saltos) y 3 cuadros para el dueño
    subprocess.run([sys.executable, str(REMOTION / "scripts" / "short_qa.py"), str(final), str(trabajo / "revision")], check=False)
    for k, t in enumerate([dur * 0.15, dur * 0.5, dur * 0.85]):
        subprocess.run([ffmpeg(), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", final.name, "-frames:v", "1", f"cuadro_{k + 1}.jpg"], cwd=trabajo, check=True)
    print("LISTO:", final)
    _ = dsp


if __name__ == "__main__":
    main()
