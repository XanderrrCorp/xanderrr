"""Arma un video de La Libreta de Inés a partir de un plan de escenas (JSON).

Uso:
  python engine/make_video.py proyectos/<slug>/plan.json            # video completo con voz MiniMax
  python engine/make_video.py plan.json --sin-voz                    # prueba sin voz (duración estimada)
  python engine/make_video.py plan.json --escenas 0-5                # solo esas escenas (vista previa)
  python engine/make_video.py plan.json --fotos                      # solo un PNG por escena para revisar

Salida en la carpeta del plan: voz/, escenas/, video_final.mp4
Las escenas ya renderizadas se reutilizan si no cambiaron (caché por contenido).
"""
import sys, os, json, hashlib, subprocess, argparse, math, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ink
from ink import W, H, FPS, frame
from PIL import Image
import shots

SR = 44100
KICK_TYPES = {"numero", "dinero", "titulo", "cuenta"}

def sh(cmd): return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
def dur_of(path): return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())
def h(obj): return hashlib.md5(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]

def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def pop_sfx():
    n = int(SR * 0.09); t = np.arange(n) / SR
    f = 500 + 900 * (t / t[-1]); ph = 2 * np.pi * np.cumsum(f) / SR
    return 0.35 * np.sin(ph) * np.exp(-t * 38)

def whoosh():
    n = int(SR * 0.28); t = np.arange(n) / SR
    noise = np.random.default_rng(3).standard_normal(n)
    env = np.sin(np.pi * t / t[-1]) ** 2
    out = np.convolve(noise, np.ones(30) / 30, "same") * env
    return 0.18 * out / (np.abs(out).max() + 1e-9)

def music(total):
    """Cama musical suave (ukelele sintético), loop I–V–vi–IV a 96 bpm."""
    bpm = 96; beat = 60 / bpm; n = int(total * SR) + SR
    out = np.zeros(n, np.float32)
    chords = [[261.6, 329.6, 392.0], [196.0, 246.9, 293.7], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6]]
    pat = [0, 1, 2, 1, 0, 2, 1, 2]
    t_note = np.arange(int(SR * beat * 1.5)) / SR
    k = 0; tt = 0.0
    while tt < total:
        ch = chords[(k // 8) % 4]; f = ch[pat[k % 8]] * (2 if k % 8 in (2, 6) else 1)
        tone = (np.sin(2 * np.pi * f * t_note) + 0.3 * np.sin(4 * np.pi * f * t_note)) * np.exp(-t_note * 5)
        i = int(tt * SR); seg = out[i:i + len(tone)]; seg += tone[:len(seg)] * 0.05
        if k % 4 == 0:
            bass = np.sin(2 * np.pi * ch[0] / 2 * t_note) * np.exp(-t_note * 3) * 0.06
            seg += bass[:len(seg)]
        k += 1; tt += beat / 2
    return out

def scene_hits(fn, dur, p):
    img = Image.new("RGBA", (W * ink.SS, H * ink.SS), (255, 255, 255, 255))
    pen = ink.Pen(ink.ImageDraw.Draw(img), 0, img)
    return sorted(set(round(x, 3) for x in (fn(img, pen, max(0, dur - 0.01), dur, p) or []) if 0 <= x < dur))

def render_scene(idx, sc, dur, out):
    fn = shots.TEMPLATES[sc["tipo"]]
    p = sc.get("p", {})
    kick = p.get("sacudida", sc["tipo"] in KICK_TYPES)
    sub = sc.get("subtitulo")
    def wrapped(img, pen, t):
        r = fn(img, pen, t, dur, p) or []
        if sub: ink.CAP["s"] = sub
        return r if kick else []
    tmp = out[:-4] + ".part.mp4"
    pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(int(round(dur * FPS))):
        pr.stdin.write(frame(wrapped, i / FPS, idx).convert("RGB").resize((W, H), Image.LANCZOS).tobytes())
    pr.stdin.close()
    if pr.wait() == 0: os.replace(tmp, out)
    else: raise RuntimeError(f"ffmpeg falló en la escena {idx}")

def still(idx, sc, dur, out, at=0.75):
    fn = shots.TEMPLATES[sc["tipo"]]; p = sc.get("p", {})
    def wrapped(img, pen, t):
        r = fn(img, pen, t, dur, p) or []
        if sc.get("subtitulo"): ink.CAP["s"] = sc["subtitulo"]
        return []
    frame(wrapped, dur * at, 99).convert("RGB").resize((W // 2, H // 2), Image.LANCZOS).save(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--sin-voz", action="store_true")
    ap.add_argument("--escenas", default=None); ap.add_argument("--fotos", action="store_true")
    ap.add_argument("--velocidad", type=float, default=None); ap.add_argument("--nucleos", type=int, default=None); ap.add_argument("--textos", action="store_true")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8")); base = os.path.dirname(os.path.abspath(a.plan))
    scenes = plan["escenas"]; speed = a.velocidad or plan.get("velocidad_voz", 1.0)
    for d in ("voz", "escenas", "fotos"): os.makedirs(os.path.join(base, d), exist_ok=True)
    rng = range(len(scenes))
    if a.escenas:
        x, y = a.escenas.split("-") if "-" in a.escenas else (a.escenas, a.escenas)
        rng = range(int(x), int(y) + 1)

    if a.textos:  # lista de textos y nombres de MP3 esperados, para generar la voz con otra herramienta
        out = [{"escena": i, "archivo": os.path.join("voz", f"v{i:03d}_{h([sc['texto'].strip(), speed])}.mp3"), "texto": sc["texto"].strip()} for i, sc in enumerate(scenes)]
        json.dump(out, open(os.path.join(base, "voz", "textos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("escrito", os.path.join(base, "voz", "textos.json")); return
    # 1) voz y duraciones
    durs, voices = [], []
    for i, sc in enumerate(scenes):
        text = sc["texto"].strip(); pad = sc.get("pausa", 0.35)
        vp = os.path.join(base, "voz", f"v{i:03d}_{h([text, speed])}.mp3")
        if not a.sin_voz and i in rng and not os.path.exists(vp):
            import tts
            print(f"voz {i + 1}/{len(scenes)}", flush=True); tts.speak(text, vp, speed)
        if os.path.exists(vp) and not a.sin_voz:
            dv = dur_of(vp); voices.append(vp)
        else:
            dv = len(text.split()) / (2.7 * speed); voices.append(None)
        durs.append(max(sc.get("min", 1.6), dv + pad))

    # 2) fotos de revisión
    if a.fotos:
        for i in rng:
            still(i, scenes[i], durs[i], os.path.join(base, "fotos", f"f{i:03d}.png"))
        print("fotos listas en", os.path.join(base, "fotos")); return

    # 3) render de escenas (con caché)
    files, todo = [], []
    for i in rng:
        sc = scenes[i]
        out = os.path.join(base, "escenas", f"e{i:03d}_{h([sc['tipo'], sc.get('p', {}), sc.get('subtitulo'), round(durs[i], 2), i == 1])}.mp4")
        if not os.path.exists(out): todo.append((i, sc, durs[i], out))
        files.append(out)
    workers = a.nucleos or max(1, (os.cpu_count() or 2) - 1)
    print(f"{len(todo)} escenas por renderizar con {workers} núcleos", flush=True)
    from concurrent.futures import ProcessPoolExecutor, as_completed
    with ProcessPoolExecutor(workers) as ex:
        futs = {ex.submit(render_scene, *job): job[0] for job in todo}
        for n, f in enumerate(as_completed(futs), 1):
            f.result(); print(f"  escena {futs[f] + 1} lista ({n}/{len(todo)})", flush=True)
    lst = os.path.join(base, "escenas", "lista.txt")
    open(lst, "w", encoding="utf-8").write("".join("file '" + f.replace(chr(92), "/") + "'\n" for f in files))
    silent = os.path.join(base, "video_sin_audio.mp4")
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])

    # 4) audio: voz + efectos + música
    total = sum(durs[i] for i in rng)
    track = np.zeros(int(total * SR) + SR, np.float32)
    pop, wh = pop_sfx(), whoosh(); t0 = 0.0
    for i in rng:
        sc = scenes[i]
        if voices[i]:
            v = load_audio(voices[i]); s = int((t0 + 0.05) * SR); track[s:s + len(v)] += v[:len(track) - s]
        if sc.get("efectos", True):
            for hx in scene_hits(shots.TEMPLATES[sc["tipo"]], durs[i], sc.get("p", {})):
                s = int((t0 + hx) * SR); track[s:s + len(pop)] += pop[:len(track) - s]
            if sc["tipo"] in ("numero", "titulo", "comparar"):
                s = int(t0 * SR); track[s:s + len(wh)] += wh[:len(track) - s]
        t0 += durs[i]
    if plan.get("musica", True): m = music(total); track[:len(m)] += m[:len(track)]
    track = np.clip(track, -1, 1)
    wav = os.path.join(base, "audio_mezcla.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((track * 32767).astype(np.int16).tobytes())
    final = os.path.join(base, plan.get("salida", "video_final.mp4"))
    tmp = final[:-4] + ".part.mp4"
    sh(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", tmp])
    os.replace(tmp, final)
    print(f"LISTO: {final}  ({total / 60:.1f} min)")

if __name__ == "__main__":
    main()
