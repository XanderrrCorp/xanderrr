"""Capítulos (formato YouTube), descripción final y coordenadas de la pantalla final (reutilizable)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import escenas as E  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
PLAN = json.loads((AQUI / "escenas.json").read_text(encoding="utf-8"))
TL = json.loads((AQUI / "timeline.json").read_text(encoding="utf-8"))
LEYENDA = "Contenido inspirado en las ideas de Brian Tracy. Voz generada con IA. Este canal no está afiliado a Brian Tracy."


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def capitulos():
    caps = sorted(PLAN["capitulos"])
    caps[0][0] = 0.0
    limpio = []
    for k, (t, titulo) in enumerate(caps):
        fin = caps[k + 1][0] if k + 1 < len(caps) else TL["duracion"]
        if fin - t >= 10 or k == len(caps) - 1:
            limpio.append((t, titulo))
    assert limpio[0][0] == 0 and len(limpio) >= 3
    return "\n".join(f"{mmss(t)} {titulo}" for t, titulo in limpio)


DESCRIPCION = """Lo que una mujer tolera es exactamente lo que recibe. En este video no vas a escuchar otra charla sobre estándares altos: vas a hacer tu propia tabla, con papel y lápiz, en las cinco áreas de tu vida donde más se nota lo que aceptas.

Lo que descubrirás en este video:
✔️ Las dos trampas que te hacen bajar tu precio sin darte cuenta
✔️ Cómo escribir tu "nuevo mínimo" en pareja, familia, trabajo, dinero y amistades
✔️ Por qué la quinta fila (tú misma) decide si todo lo demás funciona
✔️ Las cuatro palabras exactas para el día en que alguien cruce tu línea

{capitulos}

✍️ Ten a mano una hoja y un lápiz. Pausa el video en cada fila.

💎 MI VALOR – programa de amor propio de 21 días (PDF, 7 días de garantía): [TU ENLACE DE HOTMART]
🤝 Únete al círculo (audio semanal, reto de límites y lección de dinero): botón «Unirme» debajo del video.

💬 Cuéntanos en los comentarios: ¿cuál fila te costó más escribir? Solo el número, del 1 al 5.
{creditos}
{leyenda}

#amorpropio #estándaresaltos #mujeres
"""


def creditos_musica():
    ruta = AQUI / "musica" / "creditos.txt"            # si alguna pista pide atribución, se pone ahí
    return ("\n🎵 Música:\n" + ruta.read_text(encoding="utf-8").strip() + "\n") if ruta.exists() else ""


if __name__ == "__main__":
    caps = capitulos()
    (AQUI / "capitulos.txt").write_text(caps + "\n", encoding="utf-8")
    try:
        from contenido import DESCRIPCION as _D  # la descripción propia de ESTE video
    except ImportError:
        _D = DESCRIPCION
    (AQUI / "descripcion_final.txt").write_text(_D.format(capitulos=caps, creditos=creditos_musica(), leyenda=LEYENDA),
                                                encoding="utf-8")
    x0, y0, x1, y1 = E.FINAL_VIDEO
    cx, cy, r = E.FINAL_SUSCRIBIR
    W, H = E.W, E.H
    ini = [e for e in PLAN["escenas"] if e["tipo"] == "pantalla_final"][0]["inicio"]
    (AQUI / "pantalla_final.txt").write_text(
        f"Pantalla final: desde {mmss(ini)} hasta {mmss(TL['duracion'])} (últimos {TL['duracion'] - ini:.0f} s).\n"
        f"En YouTube Studio > Pantalla final, coloca:\n"
        f"- VIDEO (mejor para la espectadora): caja de {x0},{y0} a {x1},{y1} px "
        f"(izquierda {x0 / W:.0%}, arriba {y0 / H:.0%}, ancho {(x1 - x0) / W:.0%}).\n"
        f"- SUSCRIBIRSE: círculo con centro en {cx},{cy} px y radio {r} px (centro en {cx / W:.0%} del ancho y {cy / H:.0%} del alto).\n"
        f"El botón «UNIRME · El círculo de las dueñas» ya va dibujado en el video (no es un elemento de YouTube).\n",
        encoding="utf-8")
    print(caps)
