"""Modo Tracy, fase 2: plan visual, clips (Pexels + seminario), historial y ensamblaje.
Sin red ni gasto: Pexels, Claude y la voz son simulados; FFmpeg sí corre de verdad."""
import json
import random
import subprocess

import pytest

from estudio.tracy import historial
from estudio.tracy.clips import _lugar, consultas, elegir_seminario
from estudio.tracy.ensamblar import FPS, trozos_subtitulo
from estudio.tracy.planificador import MAX_SEMINARIO_SEGUIDOS, ajustar


def _plan(tipos):
    return [{"id": i, "type": t, "keywords": ["a", "b"], "mood": "calm", "inicio": i * 10.0, "fin": i * 10.0 + 10,
             "duracion": 10.0} for i, t in enumerate(tipos)]


def _max_racha(tipos):
    m = r = 0
    for t in tipos:
        r = r + 1 if t == "seminar" else 0
        m = max(m, r)
    return m


# ------------------------------------------------------------------ reglas del plan

@pytest.mark.parametrize("tipos", [["seminar"] * 12, ["stock"] * 12, ["seminar", "stock"] * 6,
                                   ["seminar"] * 5 + ["stock"] * 7])
def test_plan_respeta_proporcion_y_rachas(tipos):
    plan = ajustar(_plan(tipos), 0.4)
    t = [p["type"] for p in plan]
    assert t.count("seminar") == round(12 * 0.4)
    assert _max_racha(t) <= MAX_SEMINARIO_SEGUIDOS


def test_plan_con_proporcion_imposible_no_rompe_rachas():
    t = [p["type"] for p in ajustar(_plan(["seminar"] * 9), 0.95)]
    assert _max_racha(t) <= MAX_SEMINARIO_SEGUIDOS and t.count("seminar") == 6


def test_consultas_van_de_lo_preciso_a_lo_general():
    q = consultas(["man running at sunrise", "city street"], "energetic")
    assert q[0] == "man running at sunrise city street" and "sunrise" in q and "business success" in q
    assert len(q) == len(set(q))


# ------------------------------------------------------------------ seminario

def test_tramos_de_seminario_no_se_solapan_ni_repiten_historial(monkeypatch):
    monkeypatch.setattr(historial, "tramos_usados", lambda *a, **k: [(0.0, 300.0)])
    plan = _plan(["seminar", "stock"] * 8)
    t = elegir_seminario(plan, "base.mp4", 900.0, "tracy", "v1", avisar=lambda *_: None)
    tramos = sorted((x["inicio"], x["fin"]) for x in t.values())
    assert len(tramos) == 8
    assert all(a >= 300.0 for a, _ in tramos)                                  # fuera de lo usado antes
    assert all(tramos[k][1] <= tramos[k + 1][0] for k in range(len(tramos) - 1))  # sin solaparse


def test_lugar_sin_espacio():
    assert _lugar(20, 30, [(5, 25)], random.Random(1)) is None
    assert _lugar(10, 30, [(0, 10), (20, 30)], random.Random(1)) == pytest.approx(10.0)


# ------------------------------------------------------------------ subtítulos

def test_trozos_de_subtitulo_cortos_y_en_orden():
    pal = [{"p": w, "inicio": i * 0.4, "fin": i * 0.4 + 0.3} for i, w in
           enumerate("El éxito no es un accidente, es el resultado de hábitos diarios y constantes.".split())]
    trozos = trozos_subtitulo([{"palabras": pal}], 10.0)
    assert all(len(t["texto"].split()) <= 4 for t in trozos)
    assert trozos[0]["texto"].endswith("accidente,") or len(trozos[0]["texto"].split()) == 4
    assert all(trozos[k]["fin"] <= trozos[k + 1]["inicio"] + 1e-9 for k in range(len(trozos) - 1))


# ------------------------------------------------------------------ historial en la base

def test_historial_de_stock_solo_mira_los_ultimos_15_videos():
    from estudio.plataforma import contexto, db
    from estudio.plataforma.cuentas import cuenta_local

    db.preparar()
    with db.sesion() as s:
        _, e = cuenta_local(s)
        contexto.fijar_espacio(e.id)
    for k in range(17):
        historial.registrar("tracy", f"v{k}", [{"tipo": "stock", "clip": f"p{k}"},
                                                {"tipo": "seminario", "clip": "base.mp4", "inicio": k, "fin": k + 1}])
    usados = historial.stock_usado("tracy", excluir="nuevo")
    assert "p16" in usados and "p2" in usados and "p1" not in usados and "p0" not in usados
    assert len(historial.tramos_usados("tracy", "base.mp4")) == 5
    assert historial.stock_usado("otro-canal") == set()
    historial.registrar("tracy", "v16", [{"tipo": "stock", "clip": "cambiado"}])   # rehacer reemplaza
    assert "p16" not in historial.stock_usado("tracy") and "cambiado" in historial.stock_usado("tracy")


# ------------------------------------------------------------------ de punta a punta con FFmpeg

def _video(ffmpeg, destino, segundos, color=True, w=1920, h=1080):
    fuente = f"testsrc2=size={w}x{h}:rate=25" if color else f"testsrc=size={w}x{h}:rate=30"
    filtro = [] if color else ["-vf", "hue=s=0"]
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"{fuente}:duration={segundos}",
                    "-f", "lavfi", "-i", f"sine=frequency=500:duration={segundos}", *filtro,
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-shortest", str(destino)],
                   check=True)
    return destino


class _Resp:
    def __init__(self, datos=None, contenido=b""):
        self.status_code, self._d, self._c = 200, datos, contenido

    def json(self):
        return self._d

    def raise_for_status(self):
        pass

    def iter_content(self, n):
        yield self._c

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Pexels:
    """Pexels simulado: 40 videos de 25 s en 1920x1080 (y uno de 720p que no debe usarse)."""

    def __init__(self, mp4: bytes):
        self.mp4, self.busquedas = mp4, []

    def get(self, url, params=None, headers=None, timeout=None, stream=False):
        if stream:
            return _Resp(contenido=self.mp4)
        self.busquedas.append(params["query"])
        base = abs(hash(params["query"])) % 1000 * 100
        videos = [{"id": 999999, "duration": 60, "url": "u", "user": {"name": "x"},
                   "video_files": [{"file_type": "video/mp4", "width": 1280, "height": 720, "link": "l720"}]}]
        videos += [{"id": base + k, "duration": 25, "url": f"https://pexels.com/video/{base + k}",
                    "user": {"name": "Autor"},
                    "video_files": [{"file_type": "video/mp4", "width": 1920, "height": 1080, "link": f"l{base + k}"},
                                    {"file_type": "video/mp4", "width": 3840, "height": 2160, "link": "4k"}]}
                   for k in range(40)]
        return _Resp({"videos": videos})


def _claude_simulado(prompt, cwd=None):
    import re
    ids = [int(x) for x in re.findall(r"^(\d+): ", prompt, flags=re.M)]
    segs = [{"id": i, "type": "seminar" if i % 2 == 0 else "stock",
             "keywords": ["man walking city", "sunrise"], "mood": "inspiring"} for i in ids]
    return json.dumps({"segmentos": segs}), {"usage": {"input_tokens": 900, "output_tokens": 300},
                                             "model": "claude-haiku", "total_cost_usd": 0.002}


def test_video_tracy_de_punta_a_punta(tmp_path, monkeypatch):
    from estudio.pipeline import Trabajo, ffmpeg
    from estudio.tracy import preset as mod_preset
    from estudio.tracy.clips import duracion_video
    from estudio.tracy.flujo import crear_proyecto, producir

    ff = ffmpeg()
    base = _video(ff, tmp_path / "seminario.mp4", 240, color=False, w=1280, h=720)
    clip = _video(ff, tmp_path / "stock.mp4", 25)
    monkeypatch.setenv("PEXELS_API_KEY", "prueba")
    musica = tmp_path / "musica.m4a"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=7",
                    "-c:a", "aac", str(musica)], check=True)                  # más corta que el video: va en bucle
    from PIL import Image, ImageDraw
    presentador = tmp_path / "presentador.png"
    im = Image.new("RGBA", (500, 800), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((120, 60, 380, 360), fill=(220, 180, 150, 255))       # una «cabeza» sin fondo
    ImageDraw.Draw(im).rectangle((60, 360, 440, 800), fill=(40, 40, 60, 255))
    im.save(presentador)
    monkeypatch.setattr(mod_preset, "POR_DEFECTO", {**mod_preset.POR_DEFECTO, "clip_base": str(base),
                                                    "musica": str(musica), "presentador": str(presentador),
                                                    "escena_final_desde": 0.5, "suscribete_cada_s": 20})
    from estudio.tracy import escena_final
    monkeypatch.setattr(escena_final, "BUCLE_PARTICULAS_S", 4)                # la prueba no arma 20 s de partículas
    guion = ("La disciplina es el puente entre las metas y los logros. " * 4 + "\n\n"
             + "Cada mañana decide qué es lo más importante y hazlo primero. " * 5
             + "El 80% de tus resultados viene del 20% de tus actividades. " * 4 + "Empieza hoy mismo.")
    c = crear_proyecto(guion, titulo="Prueba Tracy fase dos")
    t = Trabajo("tracy")
    pex = _Pexels(clip.read_bytes())
    destino = producir(c, t, proveedor="simulado", ejecutar=_claude_simulado, sesion=pex)

    final = c.ruta / "render" / "final.mp4"
    assert final.exists() and destino.exists() and final.with_suffix(".srt").exists()
    voz = json.loads((c.ruta / "audio" / "oraciones.json").read_text(encoding="utf-8"))["duracion"]
    assert duracion_video(final, ff) == pytest.approx(voz, abs=0.15)          # imagen y voz del mismo largo
    info = subprocess.run([ff, "-hide_banner", "-i", str(final)], capture_output=True, text=True).stderr
    assert "1920x1080" in info and info.count("Audio:") == 1                  # 1080p y una sola pista de audio
    assert "música de fondo" in " ".join(t.registro)

    plan = json.loads((c.ruta / "plan_visual.json").read_text(encoding="utf-8"))
    tipos = [p["type"] for p in plan["plan"]]
    assert plan["origen"] == "claude" and _max_racha(tipos) <= 2
    clips = json.loads((c.ruta / "clips.json").read_text(encoding="utf-8"))["clips"]
    stock = [x["pexels_id"] for x in clips if x["tipo"] == "stock"]
    assert len(stock) == len(set(stock)) and "999999" not in stock          # sin repetir y nunca el de 720p
    sem = sorted((x["desde"], x["desde"] + x["duracion"]) for x in clips if x["tipo"] == "seminario")
    assert all(sem[k][1] <= sem[k + 1][0] for k in range(len(sem) - 1))
    finales = [x for x in clips if x["tipo"] == "final"]
    assert finales and all(x["inicio"] >= voz * 0.5 - 20 for x in finales)          # la escena final va al final
    assert clips[-1]["tipo"] == "final" and len({x["archivo"] for x in finales}) == 1  # un solo fondo en bucle
    assert (c.ruta / "render" / "tracy" / "presentador.png").exists()
    lic = json.loads((c.ruta / "stock_licencias.json").read_text(encoding="utf-8"))
    assert "Pexels" in lic["licencia"] and len(lic["clips"]) == len(stock) + 1
    from estudio.config import ConfigCostos
    assert any(e["modulo"] == "tracy_planificador" for e in c.libro(ConfigCostos.cargar()).entradas())

    # rehacer: el plan y las descargas no se vuelven a pedir
    llamadas = []
    antes = len(pex.busquedas)
    producir(c, Trabajo("tracy"), proveedor="simulado", ejecutar=lambda *a, **k: llamadas.append(1), sesion=pex)
    assert llamadas == [] and len(pex.busquedas) >= antes


def test_sin_archivo_de_musica_sale_solo_con_la_voz():
    from estudio.tracy.preset import completar

    p = completar({"musica": "C:/no/existe.mp3", "volumen_musica_db": 5})
    assert p["volumen_musica_db"] == 0.0                   # nunca más fuerte que la voz


def test_encuentra_la_cancion_aunque_windows_esconda_la_extension(tmp_path):
    from estudio.tracy.preset import EXT_AUDIO, encontrar

    (tmp_path / "musica tracy.mp3.mp3").write_bytes(b"x")
    assert encontrar(str(tmp_path / "musica tracy.mp3"), EXT_AUDIO).endswith("musica tracy.mp3.mp3")
    (tmp_path / "otra.m4a").write_bytes(b"x")
    assert encontrar(str(tmp_path / "otra.mp3"), EXT_AUDIO).endswith("otra.m4a")
    assert encontrar(str(tmp_path / "nada.mp3"), EXT_AUDIO) is None


def test_escena_final_ocupa_el_final_y_la_proporcion_se_cuadra_antes():
    from estudio.tracy.planificador import marcar_final

    plan = _plan(["seminar", "stock"] * 10)                     # 20 segmentos de 10 s = 200 s
    p = marcar_final(plan, 200.0, 0.35, 0.4)
    tipos = [x["type"] for x in p]
    assert tipos[7:] == ["final"] * 13 and "final" not in tipos[:7]
    assert tipos[:7].count("seminar") == round(7 * 0.4) and _max_racha(tipos[:7]) <= 2
    assert marcar_final(plan, 200.0, 1.0, 0.4) == plan           # 1 = sin escena final


def test_boton_suscribete_nunca_queda_partido_y_respeta_la_pausa():
    from estudio.tracy.escena_final import DUR_SUSCRIBETE, momentos_suscribete

    segs = [{"id": i, "inicio": i * 12.0, "fin": i * 12.0 + 12} for i in range(20)]
    m = momentos_suscribete(segs, 60)
    inicios = sorted(segs[i]["inicio"] for i in m)
    assert m and all(b - a >= 60 for a, b in zip(inicios, inicios[1:]))
    assert all(en + DUR_SUSCRIBETE <= segs[i]["fin"] - segs[i]["inicio"] for i, en in m.items())


def test_presentador_sale_en_blanco_y_negro_con_fondo_transparente(tmp_path):
    from PIL import Image

    from estudio.tracy.escena_final import preparar_presentador

    origen = tmp_path / "p.png"
    im = Image.new("RGBA", (400, 600), (0, 0, 0, 0))
    im.paste((200, 50, 50, 255), (100, 100, 300, 600))
    im.save(origen)
    out = Image.open(preparar_presentador(str(origen), tmp_path / "o.png"))
    assert out.height == 1000 and out.mode == "RGBA"
    r, g, b, a = out.getpixel((out.width // 2 - 60, 600))
    assert r == g == b and a > 0 and out.getpixel((5, 5))[3] == 0
    assert preparar_presentador(str(tmp_path / "no.png"), tmp_path / "x.png") is None


def test_swoosh_solo_en_los_cambios_de_escena(tmp_path):
    import wave

    import numpy as np

    from estudio.pipeline import ffmpeg
    from estudio.tracy.ensamblar import cortes_de_escena, pista_swoosh

    clips = [{"tipo": "stock", "inicio": 0}, {"tipo": "seminario", "inicio": 10}, {"tipo": "final", "inicio": 20},
             {"tipo": "final", "inicio": 30}, {"tipo": "final", "inicio": 40}]
    cortes = cortes_de_escena(clips)
    assert cortes == [10.0, 20.0]                       # dentro de la escena final no hay swoosh
    ruta = pista_swoosh(cortes, 50.0, ffmpeg(), tmp_path / "s.wav")
    with wave.open(str(ruta)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32)
        sr = w.getframerate()
    fuerte = lambda a, b: np.abs(x[int(a * sr):int(b * sr)]).max()  # noqa: E731
    assert fuerte(9.5, 10.5) > 1000 and fuerte(19.5, 20.5) > 1000
    assert fuerte(25, 29) == 0 and fuerte(35, 39) == 0


def test_canal_viejo_recibe_voz_normal_y_musica_mas_alta():
    from estudio.tracy.preset import ajustes_voz, completar

    viejo = completar({"velocidad": None, "volumen_musica_db": -24.0})     # lo que quedó guardado antes
    assert viejo["velocidad"] == 1.0 and viejo["volumen_musica_db"] == -16.0
    elegido = completar({"velocidad": 1.1, "volumen_musica_db": -20})       # lo que el dueño elige se respeta
    assert elegido["velocidad"] == 1.1 and elegido["volumen_musica_db"] == -20
    assert ajustes_voz(viejo)["velocidad"] == 1.0                            # no la de los stickman (1,3)


def test_seminario_corto_intercalado_con_stock_hasta_la_escena_final():
    from estudio.tracy.planificador import tomas

    plan = [{"id": 0, "type": "stock", "inicio": 0.0, "fin": 15.0, "duracion": 15.0, "keywords": ["a"], "mood": "calm"},
            {"id": 1, "type": "seminar", "inicio": 15.0, "fin": 24.0, "duracion": 9.0, "keywords": ["b"], "mood": "calm"},
            {"id": 2, "type": "stock", "inicio": 24.0, "fin": 30.0, "duracion": 6.0, "keywords": ["c"], "mood": "calm"},
            {"id": 3, "type": "final", "inicio": 30.0, "fin": 45.0, "duracion": 15.0, "keywords": ["d"], "mood": "calm"}]
    t = tomas(plan, 6.0)
    assert [x["type"] for x in t] == ["seminar", "stock", "seminar", "stock", "seminar", "final"]
    assert [x["duracion"] for x in t][:2] == [6.0, 9.0]
    assert all(a["fin"] == b["inicio"] for a, b in zip(t, t[1:]))          # sin huecos
    assert [x["id"] for x in t] == list(range(len(t)))


def test_barras_de_cine_y_boton_debajo_de_ellas(tmp_path):
    from estudio.tracy.ensamblar import comando_tramo

    clip = {"id": 0, "tipo": "final", "archivo": "f.mp4", "desde": 0, "inicio": 40.0, "fin": 50.0}
    cmd = comando_tramo("ffmpeg", clip, [], tmp_path / "o.mp4",
                        {"particulas": "p.mp4", "voz": "v.wav", "presentador": None, "suscribete": ("s", 2.0)}, 130)
    filtro = cmd[cmd.index("-filter_complex") + 1]
    assert "drawbox=x=0:y=0:w=iw:h=130" in filtro and "y=ih-130" in filtro
    assert "y=140:eof_action=pass" in filtro and "y=H-h-170" in filtro       # botón y ondas fuera de las barras
    assert cmd[cmd.index("-map") + 1] == "[cine]"
