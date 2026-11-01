"""Graba una frase por escena con la voz del canal (MiniMax) y mide duración y silencios."""
import json, os, subprocess, sys, urllib.request, pathlib
import numpy as np
P = pathlib.Path(__file__).resolve().parent.parent
import os
PROD = os.environ.get("PROD", "avispon")
FRASES_PANTERA = {
 "s1": "La pantera negra no existe.",
 "s2": "Entonces, ¿qué es lo que te está mirando desde la oscuridad?",
 "s3": "Es un jaguar en América, o un leopardo en África y Asia. Con una mutación que llena su piel de pigmento negro.",
 "s4": "De noche es casi invisible. Camina sin romper una rama. Y si es un jaguar, su mordida atraviesa el caparazón de una tortuga.",
 "s5": "Pero lo más loco: sus manchas nunca desaparecieron. Siguen ahí, escondidas, negro sobre negro. Con buena luz, se ven.",
 "s6": "¿Tú lo sabías? Escribe sí o no.",
 "s7": "Pero hay una mutación mucho más difícil de mirar. Está en el video completo. Porque te lo repito…",
}
FRASES = {
 "s1": "Este avispón es del tamaño de tu pulgar… y acaba de encontrar una colmena.",
 "s2": "Mide unos cinco centímetros. Su armadura es tan gruesa que las picaduras de abeja casi no le hacen daño.",
 "s3": "Con sus mandíbulas, unos pocos avispones pueden acabar con una colmena entera en unas horas.",
 "s4": "Pero la abeja japonesa tiene un truco. Cuando el avispón entra, cientos lo rodean.",
 "s5": "Forman una bola apretada y empiezan a vibrar los músculos de las alas. Sin volar.",
 "s6": "Esa vibración sube el calor hasta unos cuarenta y seis grados. Las abejas lo aguantan. El avispón, no.",
 "s7": "Lo cocinan con puro calor. ¿Y el que no puede picarte ni aunque quiera? Está en el video completo.",
}
if PROD == "pantera":
    FRASES = FRASES_PANTERA
out = P / ("public/pantera/vo" if PROD == "pantera" else "public/audio/vo")
total_chars = 0
for k, t in (FRASES.items() if __name__ == "__main__" else []):
    mp3 = out / f"{k}.mp3"
    if not mp3.exists():
        body = {"model": "speech-2.6-hd", "text": t, "stream": False, "language_boost": "Spanish",
                "voice_setting": {"voice_id": "moss_audio_ebf2f8a2-b928-11f1-8f51-7270dd4a9232", "speed": 1.3, "vol": 1, "pitch": 0},
                "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1}}
        req = urllib.request.Request("https://api.minimax.io/v1/t2a_v2", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("MINIMAX_API_KEY", "x")})
        d = json.load(urllib.request.urlopen(req, timeout=180))
        if (d.get("base_resp") or {}).get("status_code") not in (0, None):
            sys.exit(f"MiniMax: {d.get('base_resp')}")
        mp3.write_bytes(bytes.fromhex(d["data"]["audio"]))
        total_chars += int((d.get("extra_info") or {}).get("usage_characters") or len(t))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mp3), "-ar", "48000", "-ac", "1", str(out / f"{k}.wav")], check=True)
print("caracteres cobrados:", total_chars)
