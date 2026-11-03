"""Paso 1: voz con MiniMax, un audio por segmento (separados por <#1.5#> y <#3#>), silencio de la marca entre ellos,
audio_final.wav y timeline.json. Uso: python voz.py [cuantos]   (sin número: todos)."""
import json, re, subprocess, sys, time
from pathlib import Path
import requests

AQUI = Path(__file__).resolve().parent.parent
URL = "https://api.minimax.io/v1/t2a_v2"
MODELO = "speech-2.6-hd"
VOICE_ID = "moss_audio_5f02d02b-2e0e-11f1-803b-3af0d76118b0"   # voz del canal Tracy / Código del Éxito
VELOCIDAD = 1.15                                               # (el dueño: «habla muy lento»)
PAUSA_PARRAFO = 0.45                                           # entre párrafos de un mismo segmento (pausa nativa de MiniMax)
FF = "/usr/bin/ffmpeg"


def segmentos():
    crudo = (AQUI / "guion.txt").read_text(encoding="utf-8")
    partes = re.split(r"<#([\d.]+)#>", crudo)
    salida = []
    for k in range(0, len(partes), 2):
        texto = partes[k].strip()
        pausa = float(partes[k + 1]) if k + 1 < len(partes) else 0.0
        if texto:
            parrafos = [" ".join(p.split()) for p in re.split(r"\n\s*\n", texto) if p.strip()]
            salida.append({"id": len(salida) + 1, "parrafos": parrafos, "pausa_despues": pausa})
    return salida


def duracion(ruta):
    r = subprocess.run([FF, "-i", str(ruta)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def sintetizar(seg, destino):
    texto = f" <#{PAUSA_PARRAFO}#> ".join(seg["parrafos"])
    cuerpo = {"model": MODELO, "text": texto, "stream": False, "language_boost": "Spanish",
              "voice_setting": {"voice_id": VOICE_ID, "speed": VELOCIDAD, "vol": 1, "pitch": 0},
              "audio_setting": {"sample_rate": 44100, "bitrate": 128000, "format": "mp3", "channel": 1},
              "subtitle_enable": False}
    for intento in range(4):
        r = requests.post(URL, json=cuerpo, timeout=300)        # la clave la pone el proxy
        if r.status_code == 200:
            d = r.json()
            if (d.get("base_resp") or {}).get("status_code") in (0, None) and (d.get("data") or {}).get("audio"):
                break
            print("  MiniMax:", d.get("base_resp"))
        else:
            print("  HTTP", r.status_code, r.text[:200])
        time.sleep(5 * (intento + 1))
    else:
        raise SystemExit("MiniMax no devolvió audio")
    destino.write_bytes(bytes.fromhex(d["data"]["audio"]))
    extra = d.get("extra_info") or {}
    sub = None
    url_sub = (d.get("data") or {}).get("subtitle_file")
    if url_sub:
        try:
            sub = requests.get(url_sub, timeout=60).json()
        except Exception as ex:  # noqa: BLE001
            print("  sin subtítulos:", ex)
    return {"caracteres": extra.get("usage_characters") or len(texto), "subtitulos": sub}


def main():
    cuantos = int(sys.argv[1]) if len(sys.argv) > 1 else None
    segs = segmentos()
    (AQUI / "segmentos").mkdir(exist_ok=True)
    info_ruta = AQUI / "segmentos" / "info.json"
    info = json.loads(info_ruta.read_text()) if info_ruta.exists() else {}
    for seg in segs[:cuantos]:
        mp3 = AQUI / "segmentos" / f"{seg['id']:03d}.mp3"
        clave = str(seg["id"])
        texto = " ".join(seg["parrafos"])
        if not mp3.exists() or info.get(clave, {}).get("texto") != texto:
            r = sintetizar(seg, mp3)
            info[clave] = {"texto": texto, "caracteres": r["caracteres"]}
            if r["subtitulos"] is not None:
                (AQUI / "segmentos" / f"{seg['id']:03d}_sub.json").write_text(json.dumps(r["subtitulos"], ensure_ascii=False))
            info_ruta.write_text(json.dumps(info, ensure_ascii=False, indent=1))
        wav = mp3.with_suffix(".wav")
        if not wav.exists() or wav.stat().st_mtime < mp3.stat().st_mtime:
            subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1",
                            "-c:a", "pcm_s16le", str(wav)], check=True)
        seg["duracion"] = round(duracion(wav), 3)            # la duración real del audio decodificado
        print(f"segmento {seg['id']:03d}: {seg['duracion']:.2f} s · {len(texto)} caracteres · pausa después {seg['pausa_despues']} s")
    if cuantos is not None:
        return
    # unir con los silencios de las marcas
    t, lista, timeline = 0.0, [], []
    silencios = {}
    for seg in segs:
        lista.append(f"file '{AQUI / 'segmentos' / f'{seg["id"]:03d}.wav'}'")
        timeline.append({"id": seg["id"], "inicio": round(t, 3), "fin": round(t + seg["duracion"], 3),
                         "pausa_despues": seg["pausa_despues"], "texto": " ".join(seg["parrafos"]),
                         "parrafos": seg["parrafos"]})
        t += seg["duracion"]
        if seg["pausa_despues"]:
            p = seg["pausa_despues"]
            if p not in silencios:
                silencios[p] = AQUI / "segmentos" / f"silencio_{p}.wav"
                subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                f"anullsrc=r=44100:cl=mono", "-t", str(p), "-c:a", "pcm_s16le", str(silencios[p])], check=True)
            lista.append(f"file '{silencios[p]}'")
            t += p
    (AQUI / "segmentos" / "lista.txt").write_text("\n".join(lista))
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(AQUI / "segmentos" / "lista.txt"),
                    "-c", "copy", str(AQUI / "audio_final.wav")], check=True)
    (AQUI / "timeline.json").write_text(json.dumps({"duracion": round(t, 3), "segmentos": timeline},
                                                    ensure_ascii=False, indent=1))
    print(f"audio_final.wav: {duracion(AQUI / 'audio_final.wav'):.1f} s (timeline {t:.1f} s)")
    print("caracteres totales:", sum(v["caracteres"] for v in info.values()))


if __name__ == "__main__":
    main()
