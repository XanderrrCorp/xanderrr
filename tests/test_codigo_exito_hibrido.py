"""Código del Éxito híbrido: guion etiquetado, tramos de stock (≤30 s, sin repetir clip en el video), respiros del aura
(≤2,5 min seguidos), subtítulos en trozos cortos y la mezcla de audio (-14 LUFS)."""
import json

import numpy as np
import pytest

GUION = """[PROFESOR]
Hola. Hoy vemos la primera regla.

[STOCK: sunrise city, man running]
Piensa en la mañana. Todo empieza temprano.
Y este párrafo sigue en el mismo bloque.

[AURA]
Respira profundo. Repite conmigo.

[PROFESOR]
Regla número dos: empieza pequeño.
"""


def test_guion_etiquetado_en_bloques_y_partes():
    from estudio.codigo_exito import guion

    b = guion.leer(GUION)
    assert [x["tipo"] for x in b] == ["profesor", "stock", "aura", "profesor"]
    assert b[1]["claves"] == ["sunrise city", "man running"]
    assert "mismo bloque" in b[1]["texto"]
    assert [x["parte"] for x in b] == [0, 0, 0, 1]                 # cada [PROFESOR] abre una parte
    with pytest.raises(ValueError):
        guion.leer("[STOCK]\nsin palabras clave")


def test_tramos_de_stock_y_respiros_del_aura():
    from estudio.codigo_exito import armar, stock

    assert stock.tramos(7) == [7.0]
    t = stock.tramos(75)
    assert max(t) <= stock.TOMA <= stock.MAX_CLIP and abs(sum(t) - 75) < 0.01   # tomas cortas, ninguna de más de 30 s
    assert armar.respiros(100) == []
    r = armar.respiros(420)
    cortes = [0.0] + [x for t in r for x in (t, t + armar.RESPIRO)] + [420.0]
    assert r and all(b - a <= 150 for a, b in zip(cortes[::2], cortes[1::2]))   # ningún tramo de aura pasa de 2,5 min


def test_stock_no_repite_clips_en_el_video(tmp_path, monkeypatch):
    from estudio.codigo_exito import stock
    from estudio.tracy import clips

    vistos = iter(range(1000, 2000))
    def buscar(q, minimo, excluir, sesion=None):
        return [{"pexels_id": str(i), "duracion": 40.0, "url_origen": "u", "autor": "a", "descarga": "d", "ancho": 1920,
                 "alto": 1080, "consulta": q} for i in [next(vistos) for _ in range(2)] + ["7"] if str(i) not in excluir]
    def descargar(clip, sesion=None):
        p = tmp_path / f"c{clip['pexels_id']}.mp4"; p.write_bytes(b"0"); return p
    monkeypatch.setattr(clips, "buscar", buscar)
    monkeypatch.setattr(clips, "descargar", descargar)
    out = stock.elegir(tmp_path / "v", [{"clave": "a", "claves": ["x"], "dur": 70}, {"clave": "b", "claves": ["x"], "dur": 20}], avisar=lambda *_: None)
    ids = [c["pexels_id"] for v in out.values() for c in v]
    assert len(ids) == len(set(ids)) == len(stock.tramos(70)) + len(stock.tramos(20))
    reg = json.loads((tmp_path / "v" / "stock" / "usados.json").read_text())
    assert len(reg["clips"]) == len(ids) and {c["pedido"] for c in reg["clips"]} == {"a", "b"}
    again = stock.elegir(tmp_path / "v", [{"clave": "a", "claves": ["x"], "dur": 70}], avisar=lambda *_: None)
    assert [c["pexels_id"] for c in again["a"]] == [c["pexels_id"] for c in out["a"]]   # se reusa, no se vuelve a buscar


def test_subtitulos_en_trozos_cortos():
    from estudio.codigo_exito import voz

    z = voz.trozos([{"texto": "Hoy empiezo pequeño, y empezar pequeño también es avanzar.", "ini": 0.0, "fin": 4.0}])
    assert all(1 <= len(x["texto"].split()) <= 4 for x in z)
    assert z[0]["ini"] == 0 and abs(z[-1]["fin"] - 4.0) < 0.01


def test_mezcla_a_menos_14_lufs():
    from estudio.codigo_exito.mezcla import mezclar
    from estudio.pt_animado.audio.dsp import SR, integrated, true_peak

    t = np.arange(int(12 * SR)) / SR
    v = (0.2 * np.sin(2 * np.pi * 170 * t) * (np.sin(2 * np.pi * 0.5 * t) > 0)).astype(np.float32)
    m, info = mezclar(v, "ffmpeg")
    assert m.shape == (2, len(v))
    assert abs(integrated(m) + 14) < 0.5 and true_peak(m) <= -0.9
    assert info["musica"] == "por código"


def _bloque_profesor():
    texto = "Regla número uno: si algo toma menos de dos minutos, hazlo ahora. No vas a escribir un libro hoy. Vas a escribir una frase."
    from estudio.codigo_exito import voz

    frases = voz.trozos([{"texto": texto, "ini": 10.0, "fin": 20.0}])
    return {"id": 4, "tipo": "profesor", "texto": texto, "inicio": 10.0, "fin": 20.0, "ranura": 10.6, "trozos": frases}


def test_plan_de_claude_validado_y_en_su_segundo():
    from estudio.codigo_exito import plan_escenas as PE

    b = _bloque_profesor()
    datos = {"tabla_video": None, "bloques": {"4": [
        {"tipo": "numero", "desde": "", "profesor": "lado", "n_punto": 1, "etiqueta": "REGLA", "titulo": ["MENOS DE 2 MINUTOS", "HAZLO AHORA"]},
        {"tipo": "fondo_frase", "desde": "No vas a escribir", "profesor": "esquina", "frase": "No es un *libro*, es una frase"},
        {"tipo": "inventado", "desde": "Vas a escribir una frase", "profesor": "lado"},
        {"tipo": "tabla", "desde": "una frase.", "modo": "fila", "fila": 1}]}}
    plan = PE.validar(datos, [b])["4"]
    assert plan[0]["tipo"] == "numero" and plan[0]["inicio"] == 0.0 and plan[0]["profesor"] == "lado"
    assert plan[1]["tipo"] == "fondo_frase" and plan[1]["profesor"] is None and 3.0 < plan[1]["inicio"] < 8.0
    assert all(e["tipo"] in PE.TIPOS for e in plan)                 # lo inventado se cambia por una escena segura
    assert "tabla" not in [e["tipo"] for e in plan]                 # sin tabla del video no hay escenas de tabla
    assert all(b2["inicio"] - a["inicio"] >= PE.MIN_ESCENA for a, b2 in zip(plan, plan[1:]))


def test_sin_claude_plan_por_reglas(tmp_path):
    from estudio.codigo_exito import plan_escenas as PE

    b = _bloque_profesor()
    def falla(*a, **k):
        raise RuntimeError("sin sesión")
    plan = PE.planear(tmp_path, [b], avisar=lambda *_: None, ejecutar=falla)["4"]
    assert plan and plan[0]["inicio"] == 0.0 and all(e["tipo"] in PE.TIPOS for e in plan)
    assert (tmp_path / "plan_escenas.json").exists()


def test_pagina_crea_el_video_con_su_costo(tmp_path):
    from fastapi.testclient import TestClient

    from estudio.app import app

    c = TestClient(app)
    r = c.get("/api/codigo-exito")
    assert r.status_code == 200 and "faltan" in r.json()
    r = c.post("/api/codigo-exito/videos", json={"titulo": "La regla de los dos minutos", "guion": GUION})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["costo"]["por_tipo"] == {"profesor": 2, "stock": 1, "aura": 1} and d["estado"] == "nuevo"
    v = c.get(f"/api/codigo-exito/videos/{d['slug']}").json()
    assert v["titulo"] == "La regla de los dos minutos" and not v["final"]
    assert c.post("/api/codigo-exito/videos", json={"titulo": "Malo", "guion": "[STOCK]\\n" + "x " * 30}).status_code == 422
    assert any(m["clave"] == "codigo_exito" for m in c.get("/api/v2/estudio").json()["modulos"])


# ---------------------------------------------------------------- guion sin etiquetas (07-11: MiniMax «text too long»)

def _guion_largo():
    frase = "Esta es una oración larga sobre cómo tomar decisiones con calma y sin miedo al qué dirán. "
    partes = ["Hoy vas a descubrir por qué tu vida no se siente tuya."]
    for n in range(1, 4):
        partes.append(f"Decisión número {n}. " + frase * 12)
        partes.append(frase * 30)
    partes.append("Suscríbete y comenta qué decisión tomas hoy.")
    return "\n\n".join(partes)


def test_guion_sin_etiquetas_se_etiqueta_y_ningun_bloque_es_muy_largo():
    from estudio.codigo_exito import guion as G

    texto = _guion_largo()
    assert not G.tiene_etiquetas(texto)
    salida = G.etiquetar(texto, ejecutar=lambda p: ("no es json", None), avisar=lambda *_: None)
    assert G.tiene_etiquetas(salida)
    bloques = G.leer(salida)
    assert bloques[0]["tipo"] == "profesor"
    assert max(len(b["texto"]) for b in bloques) <= G.MAX_LETRAS
    assert any(b["tipo"] == "stock" for b in bloques)
    assert all(len(b["texto"]) <= G.PROFESOR_MAX for b in bloques if b["tipo"] == "profesor")
    # no se pierde ni cambia ninguna palabra
    assert G._palabras(" ".join(b["texto"] for b in bloques)) == G._palabras(texto)


def test_etiquetas_de_claude_validas_se_usan():
    import json

    from estudio.codigo_exito import guion as G

    texto = "Gancho corto del video.\n\nUna mujer camina por la playa al amanecer.\n\nRespira profundo tres veces."
    resp = json.dumps([{"desde": 0, "hasta": 0, "tipo": "profesor"},
                       {"desde": 1, "hasta": 1, "tipo": "stock", "claves": ["woman walking beach"]},
                       {"desde": 2, "hasta": 2, "tipo": "aura"}])
    bloques = G.leer(G.etiquetar(texto, ejecutar=lambda p: (resp, None), avisar=lambda *_: None))
    assert [b["tipo"] for b in bloques] == ["profesor", "stock", "aura"]


def test_bloque_etiquetado_largo_se_parte():
    from estudio.codigo_exito import guion as G

    texto = "[STOCK: nature]\n" + "Una oración de prueba que se repite bastante. " * 120
    bloques = G.leer(texto)
    assert len(bloques) > 1 and max(len(b["texto"]) for b in bloques) <= G.MAX_LETRAS


def test_costo_de_guion_sin_etiquetas_cuenta_varios_bloques():
    from estudio.codigo_exito.api import _costo

    c = _costo(_guion_largo())
    assert c["bloques"] > 3 and c["por_tipo"]["stock"] > 0


def test_guion_con_la_forma_del_dueno_emoji_comillas_y_notas():
    from estudio.codigo_exito import guion as G

    texto = ('[ 🎬 AURA: fondo oscuro, onda dorada | TEXTO grande: "¿CUÁNTAS VECES DIJISTE ESTO HOY?"] Hay frases.\n\n'
             '[ 🎬 STOCK: "woman apologizing office" / "woman talking phone worried"] "Perdón por molestar." Si alguna.\n\n'
             '[ 🎬 PROFESOR: aparece de frente, dedo en la sien] Vamos a hacer un test.\n\n'
             '[ 🎬 STOCK: "woman looking in mirror morning" | TEXTO: "7 FRASES + 1 SECRETA"] Brian Tracy enseña.\n\n'
             '[STOCK: nature, sea] Como antes.')
    assert G.tiene_etiquetas(texto)
    b = G.leer(texto)
    assert [x["tipo"] for x in b] == ["aura", "stock", "profesor", "stock", "stock"]
    assert b[0]["texto"] == "Hay frases." and b[0]["texto_pantalla"] == "¿CUÁNTAS VECES DIJISTE ESTO HOY?"
    assert b[1]["claves"] == ["woman apologizing office", "woman talking phone worried"]
    assert b[1]["texto"].startswith('"Perdón por molestar."')
    assert b[2]["nota"] == "aparece de frente, dedo en la sien" and b[2]["texto"] == "Vamos a hacer un test."
    assert b[3]["claves"] == ["woman looking in mirror morning"] and b[3]["texto_pantalla"] == "7 FRASES + 1 SECRETA"
    assert b[4]["claves"] == ["nature", "sea"]
    assert not any("🎬" in x["texto"] or "TEXTO" in x["texto"] for x in b)


def test_qr_de_compra_en_la_venta(tmp_path, monkeypatch):
    from estudio.codigo_exito import venta as V

    monkeypatch.setattr(V, "archivo", lambda: tmp_path / "venta.json")
    bloques = [{"id": 1, "inicio": 0.0, "ranura": 20.0, "texto": "Hay frases que una mujer dice veinte veces al día."},
               {"id": 2, "inicio": 20.0, "ranura": 15.0, "texto": "Eso es lo que trabajamos en MI VALOR, el programa de veintiún días."},
               {"id": 3, "inicio": 35.0, "ranura": 3.0, "texto": "Te dejo el link en la descripción."},
               {"id": 4, "inicio": 60.0, "ranura": 12.0, "texto": "Ahora sí, la frase número uno.", "nota": "dedo en la sien"},
               {"id": 5, "inicio": 80.0, "ranura": 5.0, "texto": "Una cosa más.", "nota": "VENTA, mostrar QR"}]
    assert V.tramos(bloques) == []                                     # sin link guardado: no hay QR
    try:
        V.guardar("mi-valor.com")
        raise AssertionError("debía pedir https://")
    except ValueError:
        pass
    V.guardar("https://ejemplo.com/mi-valor", "Mi Valor")
    assert V.tramos(bloques) == [(20.0, 38.0), (80.0, 88.0)]           # producto + link juntos; la nota VENTA (mín. 8 s)
    png = V.imagen(V.leer()["link"], tmp_path / "qr.png")
    import cv2

    assert cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(png)))[0] == "https://ejemplo.com/mi-valor"


def test_el_qr_va_en_las_partes_que_toca(tmp_path, monkeypatch):
    import wave

    import numpy as np

    from estudio.codigo_exito import armar as A, venta as V
    from estudio.pipeline import ffmpeg

    monkeypatch.setattr(V, "archivo", lambda: tmp_path / "venta.json")
    V.guardar("https://ejemplo.com/mi-valor", "MI VALOR")
    (tmp_path / "voz").mkdir()
    with wave.open(str(tmp_path / "voz" / "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(np.zeros(48000 * 40, "<i2").tobytes())
    tl = {"bloques": [{"id": 1, "parte": 0, "tipo": "aura", "inicio": 0.0, "ranura": 10.0, "texto": "Hola.", "trozos": []},
                      {"id": 2, "parte": 1, "tipo": "aura", "inicio": 10.0, "ranura": 12.0, "trozos": [],
                       "texto": "En MI VALOR te enseño a dejar de ponerte en rebaja."}]}
    datos = {1: {"tipo": "aura", "aura": {"respiros": []}}, 2: {"tipo": "aura", "aura": {"respiros": []}}}
    (tmp_path / "partes").mkdir()
    lista = A.partes(tmp_path, tl, datos, ffmpeg(), A.qr_de_venta(tmp_path, tl, avisar=lambda *_: None))
    assert "qr" not in lista[0]["props"]
    q = lista[1]["props"]["qr"]
    assert q[0]["ini"] == 0.0 and q[0]["fin"] == 12.0 and q[0]["url"].startswith("@/partes/qr_")
