"""Revisión del video terminado (17-10) y poses nuevas del Calvo."""
import json
from types import SimpleNamespace

import cv2
import numpy as np


def _video(ruta, segundos=4, fps=10):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(str(ruta), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 180))
    for i in range(segundos * fps):
        w.write(np.full((180, 320, 3), (i * 6) % 255, np.uint8))
    w.release()


def test_revisar_video_arma_hoja_y_guarda_lo_que_ve_claude(tmp_path):
    from estudio import revision_video as R

    _video(tmp_path / "render" / "final.mp4")
    escena = SimpleNamespace(narracion="Este es el escorpión.", tiempo=SimpleNamespace(real_inicio=0.0, real_fin=10.0))
    carpeta = SimpleNamespace(ruta=tmp_path, cargar_escenas=lambda: SimpleNamespace(escenas=[escena], video="Prueba"))
    pedidos = []

    def claude(prompt, **k):
        pedidos.append((prompt, k))
        return json.dumps({"problemas": [{"cuadro": 3, "minuto": "0:01", "que": "Texto cortado", "gravedad": "media"}],
                           "resumen": "Un detalle"}), {}

    r = R.revisar(carpeta, ejecutar=claude, avisar=lambda *_: None)
    assert r["problemas"][0]["que"] == "Texto cortado" and R.leer(carpeta)["resumen"] == "Un detalle"
    assert (tmp_path / "render" / "revision_cuadros.jpg").exists()
    prompt, k = pedidos[0]
    assert k["herramientas"] == ["Read"] and "Este es el escorpión." in prompt and "primera persona" in prompt
    assert len(R.momentos(100)) == R.CUADROS and R.momentos(100)[0] > 0.5


def test_poses_nuevas_del_calvo():
    from estudio.calma.personaje import POSES
    from estudio.calma.raster import sprite
    from estudio.explica.canal import GESTO_POR_POSE

    nuevas = ["brazos_cruzados", "saludando", "celebrando", "saltando", "manos_cabeza", "tapandose", "mano_boca",
              "caminando", "cansado", "empujando", "cayendo"]
    for p in nuevas:
        assert p in POSES and p in GESTO_POR_POSE
        img, _ = sprite("personaje", {"pose": p, "gesto": GESTO_POR_POSE[p]}, 0.5)
        borde = np.concatenate([img[0, :, 3], img[-1, :, 3], img[:, 0, 3], img[:, -1, 3]])
        assert img[:, :, 3].any() and borde.max() < 40, f"la pose {p} se sale de su caja"
