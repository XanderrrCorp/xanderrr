"""Liberar espacio (16-10): borra solo lo que se puede rehacer; con permiso, copias y videos viejos."""
import json
import os
import time


def _proyecto(base, nombre, terminado=True, viejo=False, videos=None):
    d = base / nombre
    (d / "render" / "tracy").mkdir(parents=True)
    (d / "imagenes").mkdir()
    (d / "imagenes" / "a.png").write_bytes(b"x" * 1000)
    (d / "render" / "tracy" / "tramo_0001.mp4").write_bytes(b"t" * 5000)
    salida = []
    if terminado:
        (d / "render" / "final.mp4").write_bytes(b"v" * 8000)
        if videos is not None:
            videos.mkdir(parents=True, exist_ok=True)
            copia = videos / f"{nombre}.mp4"
            copia.write_bytes(b"v" * 8000)
            salida = [str(copia)]
    (d / "proyecto.json").write_text(json.dumps({"pasos": {"export_final": {
        "estado": "completo" if terminado else "pendiente", "salida": salida}}}), "utf-8")
    if viejo:
        t = time.time() - 40 * 86400
        os.utime(d / "proyecto.json", (t, t))
    return d


def test_liberar_no_toca_lo_que_no_se_puede_rehacer(tmp_path, monkeypatch):
    from estudio import limpieza

    base, videos = tmp_path / "proyectos", tmp_path / "videos"
    monkeypatch.setenv("ESTUDIO_PROYECTOS", str(base))
    listo = _proyecto(base, "listo", videos=videos)
    pendiente = _proyecto(base, "pendiente", terminado=False)
    inv = limpieza.inventario()
    assert inv["archivos"] == 2                                   # el tramo del terminado + su video doble
    r = limpieza.liberar()
    assert r["liberado"] == 5000 + 8000
    assert not (listo / "render" / "tracy" / "tramo_0001.mp4").exists()
    assert (pendiente / "render" / "tracy" / "tramo_0001.mp4").exists()          # sin terminar: intacto
    assert (listo / "render" / "final.mp4").samefile(videos / "listo.mp4")      # un solo archivo, dos nombres
    assert (videos / "listo.mp4").read_bytes() == b"v" * 8000
    assert (listo / "imagenes" / "a.png").exists()


def test_videos_viejos_y_copias_solo_con_permiso(tmp_path, monkeypatch):
    from estudio import limpieza

    base, videos, copias = tmp_path / "proyectos", tmp_path / "videos", tmp_path / "copias"
    monkeypatch.setenv("ESTUDIO_PROYECTOS", str(base))
    monkeypatch.setenv("XANDART_COPIAS", str(copias))
    viejo = _proyecto(base, "viejo", viejo=True, videos=videos)
    nuevo = _proyecto(base, "nuevo", videos=videos)
    sin_copia = _proyecto(base, "sin-copia", viejo=True)                 # su video no está a salvo afuera
    for nombre in ("2026-10-01_a", "2026-10-05_b", "2026-10-09_c"):
        (copias / nombre).mkdir(parents=True)
        (copias / nombre / "copia.json").write_text("{}", "utf-8")
        (copias / nombre / "datos.bin").write_bytes(b"c" * 3000)
    inv = limpieza.inventario()
    assert inv["copias_viejas"] == 2 and inv["videos_viejos"] == 1 and inv["videos_viejos_lista"] == ["viejo"]
    limpieza.borrar_copias_viejas()
    assert sorted(p.name for p in copias.iterdir()) == ["2026-10-09_c"]
    r = limpieza.archivar_viejos()
    assert r["videos"] == 1 and not (viejo / "imagenes").exists() and (videos / "viejo.mp4").exists()
    assert (nuevo / "imagenes").exists() and (sin_copia / "imagenes").exists()
    assert limpieza.inventario()["videos_viejos"] == 0                   # no se vuelve a contar


def test_copiar_o_enlazar_ocupa_una_vez(tmp_path):
    from estudio.limpieza import copiar_o_enlazar

    a = tmp_path / "a.mp4"
    a.write_bytes(b"123")
    b = tmp_path / "b.mp4"
    copiar_o_enlazar(a, b)
    copiar_o_enlazar(a, b)                                                # repetir no falla
    assert b.read_bytes() == b"123" and a.samefile(b)
