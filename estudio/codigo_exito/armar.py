"""Código del Éxito híbrido (Remotion): guion etiquetado → video final de ~50 min.

Uso:  python -m estudio.codigo_exito.armar <guion.txt> <carpeta_de_trabajo> [--permiso]
Pasos (todo se retoma: lo hecho no se repite):
  1. guion.leer → bloques   2. voz.generar (MiniMax por bloque; sin --permiso no gasta)
  3. profesor.renderizar por bloque [PROFESOR]   4. stock.elegir (Pexels, sin repetir clip en el video)
  5. Remotion por PARTES (cada [PROFESOR] abre una; si una falla se repite solo esa)
  6. unión con la misma transición (fundido) + mezcla de audio (voz + música suave, -14 LUFS)
  7. final.mp4 + bloques.txt (minuto de cada bloque) + capitulos.txt (para la descripción) + creditos_pexels.txt
Si Pexels falla en un bloque, ese bloque sale como aura (el video no se frena) y se avisa.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import guion as G
from . import profesor as PR
from . import stock as ST
from . import voz as V

REMOTION = Path(__file__).resolve().parent / "remotion"
FPS = 30
T = 15 / FPS                     # la transición fija (fundido), en segundos
AURA_MAX = 150.0                 # pedido del dueño: ningún aura de más de 2-3 min seguidos
RESPIRO = 8.0


def ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _mmss(t: float) -> str:
    t = int(round(t))
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def ranuras(tl: dict) -> list[dict]:
    """cada bloque ocupa desde su inicio hasta el inicio del siguiente (con la pausa); el último hasta el final"""
    b = tl["bloques"]
    for k, x in enumerate(b):
        x["ranura"] = round((b[k + 1]["inicio"] if k + 1 < len(b) else tl["duracion"]) - x["inicio"], 3)
    return b


def respiros(dur: float) -> list[float]:
    """segundos (dentro del aura) donde entra un respiro de stock: el aura nunca pasa de AURA_MAX seguido"""
    out, t = [], AURA_MAX - RESPIRO
    while t + RESPIRO < dur - 10:
        out.append(round(t, 2))
        t += AURA_MAX
    return out


def preparar(trabajo: Path, bloques: list[dict], ff: str, avisar=print, escenas: dict | None = None) -> dict:
    """Profesor y stock de cada bloque → {id: datos del bloque para Remotion} (rutas relativas a la carpeta de trabajo)"""
    d = {}
    (trabajo / "profesor").mkdir(exist_ok=True)
    pedidos = []
    for b in bloques:
        if b["tipo"] == "stock":
            pedidos.append({"clave": f"bloque_{b['id']:03d}", "claves": b["claves"], "dur": b["ranura"] + 1.0})
        elif b["tipo"] == "aura":
            for k, _ in enumerate(respiros(b["ranura"])):
                pedidos.append({"clave": f"aura_{b['id']:03d}_{k + 1}", "claves": ["golden light nature calm"], "dur": RESPIRO, "aura": True})
    stock: dict = {}
    for p in pedidos:                                              # uno por uno: si Pexels falla, solo ese bloque cambia
        try:
            stock.update(ST.elegir(trabajo, [p], avisar))
        except Exception as ex:  # noqa: BLE001
            avisar(f"  sin stock para {p['clave']} ({str(ex)[:120]}): ese tramo va como aura")
    for b in bloques:
        if b["tipo"] == "profesor":
            wav = trabajo / "profesor" / f"bloque_{b['id']:03d}.wav"
            if not wav.exists():
                subprocess.run([ff, "-v", "error", "-y", "-i", str(trabajo / "voz" / f"{b['id']:03d}.mp3"), "-ar", "16000", "-ac", "1", str(wav)], check=True)
            firma = hashlib.sha1(f"v2|{b['texto']}|{b['ranura']}".encode()).hexdigest()[:10]
            mp4 = trabajo / "profesor" / f"bloque_{b['id']:03d}_{firma}.mp4"
            if not mp4.exists():
                avisar(f"  Profesor del bloque {b['id']} ({b['ranura']:.0f} s)…")
            dur = b["ranura"] + 1.0
            gestos = [(dur * 0.35, dur * 0.35 + 2.2)] if dur > 7 else []
            plan = escenas.get(str(b["id"])) if escenas else None
            if plan:                                   # las escenas de los primeros videos (tablas, libreta, frases…)
                from . import escenas_bloque as EB

                plan = [{**e, "inicio": round(float(e.get("inicio", e.get("en", 0) * b["ranura"])), 3)} for e in plan]
                mp4 = mp4.with_name(mp4.stem + "_esc" + hashlib.sha1(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:8] + ".mp4")
                EB.renderizar(plan, wav, b["texto"], dur, mp4, ff, gestos=gestos)
                b["_pantalla"] = [(b["inicio"] + a, b["inicio"] + z, sorted(p)) for a, z, p in EB.pantalla(EB.completar(plan, b["ranura"]))]
                b["_cortes"] = [b["inicio"] + e["inicio"] for e in plan[1:]]
            else:
                PR.renderizar(wav, b["texto"], dur, mp4, ff, gestos=gestos)
            d[b["id"]] = {"tipo": "profesor", "profesor": "@/" + mp4.relative_to(trabajo).as_posix()}
        elif b["tipo"] == "stock" and f"bloque_{b['id']:03d}" in stock:
            d[b["id"]] = {"tipo": "stock", "stock": [{"url": f"@/stock/{c['archivo']}", "dur": c["dur"]} for c in stock[f"bloque_{b['id']:03d}"]]}
        else:
            rs = []
            if b["tipo"] == "aura":
                for k, t in enumerate(respiros(b["ranura"])):
                    clave = "aura_%03d_%d" % (b["id"], k + 1)
                    if clave in stock:
                        rs.append({"t": t, "dur": RESPIRO, "url": "@/stock/" + stock[clave][0]["archivo"]})
            d[b["id"]] = {"tipo": "aura", "aura": {"respiros": rs}}
    return d


def _en_pantalla(trozo: dict, pantalla) -> bool:
    """la escena ya muestra esas palabras en grande: sin subtítulo (como en los primeros videos)"""
    if not pantalla:
        return False
    from .escenas_bloque import pantalla as _p  # noqa: F401
    import re
    import unicodedata

    s = unicodedata.normalize("NFKD", trozo["texto"].lower())
    pal = set(re.findall(r"\w+", "".join(c for c in s if not unicodedata.combining(c))))
    medio = (trozo["ini"] + trozo["fin"]) / 2
    return any(a <= medio < z and pal and pal <= set(p) for a, z, p in pantalla)


def partes(trabajo: Path, tl: dict, datos: dict, ff: str) -> list[dict]:
    """agrupa los bloques en partes (cada [PROFESOR] abre una) con sus subtítulos y su pedazo de voz"""
    grupos: dict[int, list[dict]] = {}
    for b in tl["bloques"]:
        grupos.setdefault(b["parte"], []).append(b)
    salida = []
    claves = sorted(grupos)
    (trabajo / "partes").mkdir(exist_ok=True)
    for i, k in enumerate(claves):
        bs = grupos[k]
        ini = bs[0]["inicio"]
        dur = round(sum(b["ranura"] for b in bs), 3)
        ultima = i == len(claves) - 1
        wav = trabajo / "partes" / f"voz_{k:02d}.wav"
        subprocess.run([ff, "-v", "error", "-y", "-ss", f"{ini:.3f}", "-t", f"{dur + T:.3f}", "-i", str(trabajo / "voz" / "voz.wav"),
                        "-ac", "1", "-ar", "48000", str(wav)], check=True)
        subs = [{"texto": z["texto"], "ini": round(z["ini"] - ini, 3), "fin": round(z["fin"] - ini, 3)}
                for b in bs for z in b["trozos"] if not _en_pantalla(z, b.get("_pantalla"))]
        props = {"fps": FPS, "inicio": ini, "cola": 0 if ultima else round(T * FPS),
                 "bloques": [{**datos[b["id"]], "dur": b["ranura"]} for b in bs], "subtitulos": subs,
                 "audio": "@/" + wav.relative_to(trabajo).as_posix()}
        firma = hashlib.sha1(json.dumps(props, sort_keys=True).encode()).hexdigest()[:10]
        salida.append({"nombre": f"parte_{k:02d}_{firma}", "props": props, "inicio": ini, "dur": dur, "ultima": ultima})
    return salida


def renderizar_partes(trabajo: Path, lista: list[dict], avisar=print) -> None:
    faltan = [p for p in lista if not (trabajo / "partes" / f"{p['nombre']}.mp4").exists()]
    if not faltan:
        return
    node = shutil.which("node")
    if not node:
        raise SystemExit("Falta Node.js (winget install OpenJS.NodeJS.LTS)")
    if not (REMOTION / "node_modules").exists():
        npm = shutil.which("npm") or "npm"
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=REMOTION, check=True, shell=npm.lower().endswith(".cmd"))
    archivo = trabajo / "partes" / "pendientes.json"
    archivo.write_text(json.dumps([{"nombre": p["nombre"], "props": p["props"]} for p in faltan], ensure_ascii=False), "utf-8")
    avisar(f"Armando {len(faltan)} partes en Remotion…")
    subprocess.run([node, "scripts/partes.mjs", str(trabajo.resolve()), str(archivo.resolve()), "2"], cwd=REMOTION, check=True)
    from ..pt_animado.hacer_prueba import limpiar_bundles

    limpiar_bundles()


def unir(trabajo: Path, lista: list[dict], ff: str) -> Path:
    """partes con la MISMA transición (fundido de T s) entre ellas, sin correr la imagen respecto de la voz"""
    rutas = [trabajo / "partes" / f"{p['nombre']}.mp4" for p in lista]
    video = trabajo / "video.mp4"
    if len(rutas) == 1:
        shutil.copy(rutas[0], video)
        return video
    entradas = sum([["-i", str(r)] for r in rutas], [])
    filtro, previo = [], "[0:v]"
    for k in range(1, len(rutas)):
        salida = f"[v{k}]" if k < len(rutas) - 1 else "[vout]"
        filtro.append(f"{previo}[{k}:v]xfade=transition=fade:duration={T:.4f}:offset={lista[k]['inicio']:.4f}{salida}")
        previo = salida
    subprocess.run([ff, "-y", "-v", "error", *entradas, "-filter_complex", ";".join(filtro), "-map", "[vout]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(video)], check=True)
    return video


def textos(trabajo: Path, tl: dict) -> None:
    nombre = {"profesor": "El Profesor", "stock": "Stock", "aura": "Aura"}
    filas = [f"{_mmss(b['inicio'])}  [{nombre[b['tipo']]}]  {' '.join(b['texto'].split()[:9])}…" for b in tl["bloques"]]
    (trabajo / "bloques.txt").write_text("\n".join(filas) + "\n", "utf-8")
    caps, ultimo = [], -99.0
    for b in tl["bloques"]:
        if (b["tipo"] == "profesor" or b is tl["bloques"][0]) and b["inicio"] - ultimo >= 10:
            caps.append(f"{_mmss(b['inicio'] if caps else 0)} {' '.join(b['texto'].split()[:7]).rstrip('.,:;')}")
            ultimo = b["inicio"]
    (trabajo / "capitulos.txt").write_text("\n".join(caps) + "\n", "utf-8")
    usados = trabajo / "stock" / "usados.json"
    if usados.exists():
        reg = json.loads(usados.read_text("utf-8"))
        cred = [f"Video de {c['autor']} en Pexels: {c['url']}" for c in reg["clips"]]
        (trabajo / "creditos_pexels.txt").write_text("Clips de Pexels (licencia libre, sin atribución obligatoria):\n" + "\n".join(cred) + "\n", "utf-8")


def hacer(guion_txt: Path, trabajo: Path, permiso: bool = False, avisar=print, carpeta_musica: Path | None = None,
          escenas: dict | None = None) -> Path:
    from ..pt_animado.audio import dsp

    from .mezcla import mezclar

    ff = ffmpeg()
    trabajo.mkdir(parents=True, exist_ok=True)
    bloques = G.leer(guion_txt.read_text("utf-8"))
    (trabajo / "bloques.json").write_text(json.dumps(bloques, ensure_ascii=False, indent=1), "utf-8")
    avisar(f"Guion: {len(bloques)} bloques en {len({b['parte'] for b in bloques})} partes")
    tl = V.generar(trabajo, bloques, ff, permiso, avisar)
    ranuras(tl)
    datos = preparar(trabajo, tl["bloques"], ff, avisar, escenas)
    lista = partes(trabajo, tl, datos, ff)
    renderizar_partes(trabajo, lista, avisar)
    video = unir(trabajo, lista, ff)
    v, _ = dsp.read_wav(str(trabajo / "voz" / "voz.wav"))
    efectos = [{"t": b["inicio"], "tipo": "whoosh"} for b in tl["bloques"][1:]]                   # cada corte de bloque
    efectos += [{"t": t, "tipo": "pop"} for b in tl["bloques"] for t in b.get("_cortes", [])]     # cada escena nueva
    efectos += [{"t": b["inicio"] + 0.2, "tipo": "pop"} for b in tl["bloques"] if b["tipo"] == "profesor"]
    mezcla, info = mezclar(v.mean(0) if v.ndim > 1 else v, ff, carpeta_musica, efectos=efectos)
    dsp.write_wav(str(trabajo / "mezcla.wav"), mezcla)
    final = trabajo / "final.mp4"
    subprocess.run([ff, "-y", "-v", "error", "-i", str(video), "-i", str(trabajo / "mezcla.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(final)], check=True)
    textos(trabajo, tl)
    avisar(f"Listo: {final} ({_mmss(tl['duracion'])}; música {info['musica']}, {info['lufs']} LUFS, pico {info['pico_dbtp']} dBTP)")
    return final


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("guion"); ap.add_argument("trabajo"); ap.add_argument("--permiso", action="store_true")
    ap.add_argument("--musica", default=None)
    ap.add_argument("--escenas", default=None, help="plan de escenas de los bloques [PROFESOR] (.json)")
    a = ap.parse_args()
    try:
        hacer(Path(a.guion), Path(a.trabajo), a.permiso, carpeta_musica=Path(a.musica) if a.musica else None,
              escenas=json.loads(Path(a.escenas).read_text("utf-8")) if a.escenas else None)
    except PermissionError as ex:
        sys.exit(str(ex))


if __name__ == "__main__":
    main()
