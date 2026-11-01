"""(01-11) «Edición humana» del modo Tracy: cortes variables, seminario en autoridad, huella por video, voz con
pausas, revisión antes de exportar y reporte. Sin gasto: voz y Claude simulados, Pexels falso."""
import json
import random
import statistics
import subprocess

import pytest

from estudio.tracy import humano

H = humano.ajustes({"humano": {"activo": True}})


def _oraciones(n=40, roles=None):
    """Oraciones de 2,5-6 s seguidas, con su papel."""
    rng = random.Random(3)
    ors, marcas, t = [], {}, 0.0
    for i in range(n):
        d = rng.uniform(2.5, 6.0)
        ors.append({"id": i, "texto": f"Oración número {i} del guion.", "inicio": round(t, 3),
                    "fin": round(t + d, 3), "palabras": []})
        rol = (roles or {}).get(i) or ("gancho" if t < 60 else "normal")
        marcas[i] = {"rol": rol, "keywords": ["piggy bank coins"], "palabra": None, "grande": None}
        t += d + 0.3
    return ors, marcas, round(t, 3)


def test_cortes_variables_al_final_de_una_oracion_y_mas_rapidos_en_el_gancho():
    roles = {12: "regla", 20: "frase_fuerte", 25: "reflexiva", 26: "reflexiva", 27: "reflexiva", 28: "reflexiva",
             33: "revelacion", 38: "cierre", 39: "cierre"}
    ors, marcas, dur = _oraciones(40, roles)
    segs = humano.segmentar(ors, dur, marcas, H, "v1")
    inicios = {o["inicio"] for o in ors} | {0.0}
    assert all(s["inicio"] in inicios for s in segs)                       # siempre al empezar una oración
    assert segs[0]["inicio"] == 0 and segs[-1]["fin"] == dur
    assert all(a["fin"] == b["inicio"] for a, b in zip(segs, segs[1:]))   # sin huecos
    assert all(s["duracion"] <= 30 for s in segs)
    assert all(s["duracion"] >= H["clip_min_s"] for s in segs[:-1])          # nunca menos de 3 s (salvo el último)
    duraciones = [s["duracion"] for s in segs]
    assert statistics.pstdev(duraciones) > 1.5                               # nada de cortes cada X segundos
    gancho = [s["duracion"] for s in segs if s["inicio"] < 60]
    resto = [s["duracion"] for s in segs if s["inicio"] >= 60]
    assert statistics.mean(gancho) < statistics.mean(resto)
    assert any(s["abre"] == "regla" for s in segs)                           # la regla abre su propio clip


def test_seminario_solo_en_autoridad_bajo_el_maximo_y_sin_patron():
    roles = {k: "regla" for k in (15, 22, 29)} | {k: "frase_fuerte" for k in (18, 25, 33)} | {36: "cta", 39: "cierre"}
    ors, marcas, dur = _oraciones(40, roles)
    segs = humano.segmentar(ors, dur, marcas, H, "v2")
    combo = {"musica": {}, "estilo_texto": 2, "transiciones": ["fundido", "destello"], "movimiento": "suave"}
    plan = humano.planificar(segs, marcas, dur, {**H, "escena_final_desde": 1.0}, combo, "v2")
    sem = [p for p in plan if p["type"] == "seminar"]
    assert sem and all(p["rol"] in humano.PRIORIDAD_FENIX for p in sem)
    assert sum(p["duracion"] for p in sem) <= H["fenix_max"] * dur + 1e-6
    tipos = [p["type"] for p in plan]
    assert "seminar,seminar,seminar" not in ",".join(tipos)
    assert tipos != (["seminar", "stock"] * len(tipos))[:len(tipos)]            # no es Fénix, stock, Fénix, stock…
    movs = [p["movimiento"] for p in plan]
    assert all(a != b for a, b in zip(movs, movs[1:]))                          # nunca el mismo dos veces seguidas
    suaves = [p for p in plan if p["transicion"] != "corte"]
    assert len(suaves) <= len(plan) * 0.4                                        # casi todo corte seco
    assert sum(p["whoosh"] for p in plan) < len(plan) / 2                        # sonidos escasos


def test_el_texto_grande_sale_cuando_la_voz_dice_su_frase():
    roles = {14: "regla"}
    ors, marcas, dur = _oraciones(30, roles)
    marcas[14]["grande"] = "REGLA 2: LO DIFÍCIL PRIMERO"
    segs = humano.segmentar(ors, dur, marcas, H, "v3")
    combo = {"musica": {}, "estilo_texto": 1, "transiciones": ["fundido"], "movimiento": "suave"}
    inicios = {o["id"]: o["inicio"] for o in ors}
    plan = humano.planificar(segs, marcas, dur, {**H, "escena_final_desde": 1.0}, combo, "v3", inicios)
    toma = next(p for p in plan if 14 in p["oraciones"])
    assert toma["grande"] == "REGLA 2: LO DIFÍCIL PRIMERO"
    assert toma["grande_en"] == round(inicios[14] - toma["inicio"], 3)


def test_cada_video_tiene_su_huella_y_no_repite_la_del_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(humano, "_archivo_huellas", lambda: tmp_path / "huellas.json")
    anteriores = [humano.huella("tracy", f"video-{k}", H) for k in range(12)]
    assert all(a != b for a, b in zip(anteriores, anteriores[1:]))
    assert len({json.dumps(x, sort_keys=True) for x in anteriores}) > 3


def test_prueba_de_tres_minutos_solo_toma_el_comienzo():
    guion = " ".join(f"Esta es la oración número {k} del guion de prueba." for k in range(200))
    corto = humano.recortar_guion(guion, 30, 13.5)
    assert guion.startswith(corto) and 30 * 13.5 * 0.7 < len(corto) <= 30 * 13.5 + 60


def test_apagada_el_preset_sigue_igual():
    from estudio.tracy.preset import completar

    p = completar(None)
    assert p["humano"]["activo"] is False and not humano.activo(p)
    assert humano.activo(completar({"humano": {"activo": True}}))


# ------------------------------------------------------------------ de punta a punta

def _claude_humano(prompt, cwd=None, **_):
    import re

    ids = [int(x) for x in re.findall(r"^(\d+): ", prompt, flags=re.M)]
    roles = ["gancho", "frase_fuerte", "regla", "normal", "revelacion", "pregunta", "cta", "producto", "reflexiva",
             "cierre"]
    salida = []
    for i in ids:
        rol = roles[min(i * len(roles) // max(1, len(ids)), len(roles) - 1)]
        salida.append({"id": i, "rol": rol, "keywords": ["piggy bank coins", "saving money jar"],
                       "palabra": "disciplina" if rol in ("frase_fuerte", "regla") else None,
                       "grande": "REGLA 1: DECIDE" if rol == "regla" else None})
    return json.dumps({"oraciones": salida}), {"usage": {}, "total_cost_usd": 0.0}


def test_video_con_edicion_humana_de_punta_a_punta(tmp_path, monkeypatch):
    from estudio.pipeline import Trabajo, ffmpeg
    from estudio.tracy import preset as mod_preset
    from estudio.tracy import revision
    from estudio.tracy.clips import duracion_video
    from estudio.tracy.flujo import crear_proyecto, exportar_y_entregar, producir
    from tests.test_tracy_fase2 import _Pexels, _video

    ff = ffmpeg()
    base = _video(ff, tmp_path / "seminario.mp4", 240, color=False, w=1280, h=720)
    clip = _video(ff, tmp_path / "stock.mp4", 25)
    monkeypatch.setenv("PEXELS_API_KEY", "prueba")
    monkeypatch.setattr(humano, "_archivo_huellas", lambda: tmp_path / "huellas.json")
    carpeta_m = tmp_path / "musica"
    carpeta_m.mkdir()
    for nombre, f in (("gancho 1.m4a", 330), ("cuerpo.m4a", 220), ("cierre.m4a", 440)):
        subprocess.run([ff, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency={f}:duration=6",
                        "-c:a", "aac", str(carpeta_m / nombre)], check=True)
    monkeypatch.setattr(mod_preset, "POR_DEFECTO", {
        **mod_preset.POR_DEFECTO, "clip_base": str(base), "musica": "", "presentador": "",
        "humano": {**humano.POR_DEFECTO, "activo": True, "carpeta_musica": str(carpeta_m), "gancho_s": 10.0,
                   "escena_final_desde": 1.0}})
    guion = ("La disciplina es el puente entre las metas y los logros. " * 3 + "\n\n"
             + "Regla número uno: decide qué es lo más importante y hazlo primero. " * 3
             + "El ochenta por ciento de tus resultados viene del veinte por ciento de lo que haces. " * 3
             + "¿Y si mañana empiezas distinto? Escribe en los comentarios: yo decido. " * 2
             + "Hoy puede ser el día en que todo cambia. Empieza ya.")
    c = crear_proyecto(guion, titulo="Prueba Tracy humana")
    pex = _Pexels(clip.read_bytes())
    producir(c, Trabajo("tracy"), proveedor="simulado", ejecutar=_claude_humano, sesion=pex)
    assert not (c.ruta / "render" / "final.mp4").exists()                   # se detuvo para revisar
    r = revision.ver(c, ff)
    assert r["pendiente"] and r["clips"] and all(x["miniatura"] for x in r["clips"])
    assert {x["seccion"] for x in r["clips"]} >= {"gancho", "cierre"}
    # la voz lleva pausas naturales (sobre el audio ya pagado)
    voz = json.loads((c.ruta / "audio" / "humano.json").read_text(encoding="utf-8"))
    assert voz["pausas"] > 0
    original = json.loads((c.ruta / "audio" / "oraciones_original.json").read_text(encoding="utf-8"))["duracion"]
    nueva = json.loads((c.ruta / "audio" / "oraciones.json").read_text(encoding="utf-8"))["duracion"]
    assert nueva > original

    # retoques: texto grande, más larga, otro clip
    primero = r["clips"][0]["id"]
    r = revision.cambiar(c, primero, "texto", "EMPIEZA HOY", ffmpeg=ff)
    assert r["clips"][0]["grande"] == "EMPIEZA HOY"
    antes = r["clips"][0]["fin"]
    try:
        r = revision.cambiar(c, primero, "alargar", ffmpeg=ff)
        assert r["clips"][0]["fin"] > antes and r["clips"][0]["fin"] == r["clips"][1]["inicio"]
    except ValueError:
        pass                                             # si la siguiente quedaría muy corta, lo dice y no rompe nada
    stock = next(x for x in r["clips"] if x["tipo"] == "stock")
    ids_antes = {x.get("pexels_id") for x in json.loads((c.ruta / "clips.json").read_text("utf-8"))["clips"]}
    revision.cambiar(c, stock["id"], "otro_stock", ffmpeg=ff, sesion=pex)
    nuevo = next(x for x in json.loads((c.ruta / "clips.json").read_text("utf-8"))["clips"] if x["id"] == stock["id"])
    assert nuevo["pexels_id"] not in ids_antes

    t = Trabajo("tracy")
    destino = exportar_y_entregar(c, t)
    final = c.ruta / "render" / "final.mp4"
    assert final.exists() and destino.exists()
    assert duracion_video(final, ff) == pytest.approx(nueva, abs=0.2)          # imagen y voz del mismo largo
    info = subprocess.run([ff, "-hide_banner", "-i", str(final)], capture_output=True, text=True).stderr
    assert "1920x1080" in info and info.count("Audio:") == 1
    rep = json.loads((c.ruta / "reporte_edicion.json").read_text(encoding="utf-8"))
    assert rep["clips"] > 3 and rep["fenix_pct"] <= 35 + 1 and rep["stock_unicos"] >= 1
    assert sum(rep["efectos"]["movimientos"].values()) == rep["clips"]
    assert not revision.ver(c, ff)["pendiente"]
    assert (c.ruta / "huella_video.json").exists()
