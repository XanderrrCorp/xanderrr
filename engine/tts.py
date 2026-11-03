"""Voz con MiniMax (T2A v2). Usa MINIMAX_API_KEY si existe; en un entorno de nube con "network secret" para api.minimax.io no hace falta.
Opcionales: MINIMAX_GROUP_ID, MINIMAX_MODEL (por defecto speech-02-hd), MINIMAX_HOST (por defecto api.minimax.io).
Si tu cuenta usa otro host o modelo (por ejemplo api.minimaxi.chat o speech-2.6-hd), cámbialo con esas variables."""
import os, json, urllib.request

VOICE = os.environ.get("INES_VOICE_ID", "Spanish_Fussyhostess")

def speak(text, out_mp3, speed=1.0):
    key = os.environ.get("MINIMAX_API_KEY")  # en la nube puede faltar: el proxy agrega la clave (network secret)
    host = os.environ.get("MINIMAX_HOST", "api.minimax.io")
    url = f"https://{host}/v1/t2a_v2"
    if os.environ.get("MINIMAX_GROUP_ID"): url += "?GroupId=" + os.environ["MINIMAX_GROUP_ID"]
    body = {"model": os.environ.get("MINIMAX_MODEL", "speech-02-hd"), "text": text, "stream": False,
            "language_boost": "Spanish",
            "voice_setting": {"voice_id": VOICE, "speed": speed, "vol": 1.0, "pitch": 0},
            "audio_setting": {"sample_rate": 44100, "bitrate": 128000, "format": "mp3", "channel": 1}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={**({"Authorization": f"Bearer {key}"} if key else {}), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        res = json.loads(r.read())
    st = res.get("base_resp", {})
    if st.get("status_code", 0) != 0: raise RuntimeError(f"MiniMax: {st}")
    open(out_mp3, "wb").write(bytes.fromhex(res["data"]["audio"]))
    return out_mp3
