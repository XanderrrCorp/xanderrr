"""Paso 2: plan de escenas → escenas.json. Cada escena arranca en una frase ancla de su segmento (tiempo estimado por
la proporción de letras dentro del segmento, que ya tiene su duración exacta) y dura hasta la siguiente."""
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
TL = json.loads((AQUI / "timeline.json").read_text(encoding="utf-8"))

from contenido import *  # noqa: F401,F403  (el contenido de ESTE video)

OSCURAS = {"tipografia", "fondo_frase", "test", "puertas", "comentario", "diamante", "preguntas", "membresia", "cuatro_palabras", "trampas",
           "estuche", "cita", "encuesta", "numero", "burbujas", "edades", "sobre", "dato", "medalla", "mochila", "noche_plancha", "mesa_familia"}


def tiempo_de_ancla(seg, ancla):
    if ancla is None:
        return seg["inicio"]
    texto = " ".join(seg["parrafos"])
    k = texto.find(ancla)
    if k < 0:
        raise SystemExit(f"no encuentro «{ancla}» en el segmento {seg['id']}")
    return round(seg["inicio"] + (seg["fin"] - seg["inicio"]) * k / len(texto), 2)


MAX_ESCENA = 9.0
DIVISIONES = [0]
NO_PARTIR = {"pausa", "test", "dos_columnas", "encuesta"}     # se arman paso a paso: partirlas confunde


def _frases(seg):
    """Oraciones del segmento con su tiempo estimado de inicio (proporción de letras)."""
    texto = " ".join(seg["parrafos"])
    out, k = [], 0
    for m in re.finditer(r"[^.!?¿¡]*[.!?]+[»\"]?|\S[^.!?]*$", texto):
        frase = m.group(0).strip()
        if len(frase.split()) >= 4:
            out.append((seg["inicio"] + (seg["fin"] - seg["inicio"]) * m.start() / len(texto), frase))
    return out


def _corta(frase, max_pal=12):
    pal = frase.replace("«", "").replace("»", "").replace('"', "").split()
    if len(pal) > max_pal:
        pal = pal[:max_pal]
        pal[-1] = pal[-1].rstrip(",.;:") + "…"
    clave = min(3, max(1, len(pal) // 4))
    return " ".join(pal[:-clave]) + " *" + " ".join(pal[-clave:]) + "*"


def dividir_largas(escenas, segs):
    """Si una escena dura más de MAX_ESCENA, mete en el medio una frase animada con lo que dice la voz en ese
    momento (así siempre hay un cambio). Se repite hasta que todas queden cortas."""
    for _ in range(6):
        nuevas, cambio = [], False
        for i, e in enumerate(escenas):
            nuevas.append(e)
            fin = escenas[i + 1]["inicio"] if i + 1 < len(escenas) else TL["duracion"]
            if fin - e["inicio"] <= MAX_ESCENA or e["tipo"] in NO_PARTIR:
                continue
            cand = []
            for sg in TL["segmentos"]:
                if sg["fin"] < e["inicio"] or sg["inicio"] > fin:
                    continue
                cand += [(t0, f) for t0, f in _frases(sg) if e["inicio"] + 4.5 <= t0 <= fin - 3.5]
            if not cand:
                continue
            medio = (e["inicio"] + fin) / 2
            t0, f = min(cand, key=lambda x: abs(x[0] - medio))
            fondo = "vino" if e.get("fondo") != "vino" else "noche"
            base = {"n": 0, "segmento": e["segmento"], "desde_frase": f[:30], "inicio": round(t0, 2), "fondo": fondo, "auto": True}
            DIVISIONES[0] += 1
            if DIVISIONES[0] % 2 and len(f.split()) <= 14:            # letras grandes animadas
                pal = f.replace("«", "").replace("»", "").replace('"', "").rstrip(".").upper().split()
                tam = max(2, min(4, (len(pal) + 2) // 3))
                lineas = [" ".join(pal[k:k + tam]) for k in range(0, len(pal), tam)][:4]
                nuevas.append({**base, "tipo": "tipografia",
                               "lineas": [[ln, "dorado" if j == len(lineas) - 1 else "blanco"] for j, ln in enumerate(lineas)]})
            else:
                nuevas.append({**base, "tipo": "fondo_frase", "frase": _corta(f)})
            cambio = True
        escenas = nuevas
        if not cambio:
            break
    for k, e in enumerate(escenas):
        e["n"] = k + 1
    return escenas


def main():
    segs = {s["id"]: s for s in TL["segmentos"]}
    escenas = []
    for i, (sid, ancla, tipo, params) in enumerate(P):
        ini = tiempo_de_ancla(segs[sid], ancla)
        escenas.append({"n": i + 1, "segmento": sid, "desde_frase": ancla or "(inicio del segmento)", "tipo": tipo,
                        "inicio": ini, **params})
    for a, b in zip(escenas, escenas[1:]):              # ninguna escena de menos de 4 s: la siguiente espera
        b["inicio"] = max(b["inicio"], round(a["inicio"] + 4.0, 2))
    escenas = dividir_largas(escenas, segs)             # nada quieto más de ~9 s
    corte = round(TL["duracion"] - FINAL_S, 2)          # pantalla final: los últimos 20 s
    escenas = [e for e in escenas if e["inicio"] < corte - 3]
    escenas.append({"n": len(escenas) + 1, "segmento": TL["segmentos"][-1]["id"], "desde_frase": "(últimos 20 s)",
                    "tipo": "pantalla_final", "inicio": corte, "fondo": "noche", "profesor": "final"})
    for sg in TL["segmentos"]:                          # la frase final se ve escrita mientras El Profesor la dice
        k = sg["texto"].find(FRASE_FUERTE)
        if k >= 0:
            escenas[-1]["frase"] = FRASE_FUERTE
            escenas[-1]["frase_desde"] = round(sg["inicio"] + (sg["fin"] - sg["inicio"]) * k / len(sg["texto"]) - corte, 2)
    for e in escenas:
        if (e["tipo"] in ("tipografia", "fondo_frase") and e["segmento"] in PROFESOR_LADO) or e["tipo"] == "numero":
            e["profesor"], e["lado"] = "lado", True
        elif e["tipo"] in PROFESOR_ESQUINA or (e["tipo"] == "fondo_frase" and e["segmento"] == SEGMENTO_SUSCRIBIR):
            e["profesor"] = "esquina"
        elif e["tipo"] == "tabla" and e.get("modo") == "fila":
            e["profesor"] = "tabla"
    for a, b in zip(escenas, escenas[1:]):
        a["fin"] = b["inicio"]
    escenas[-1]["fin"] = TL["duracion"]
    for e in escenas:
        e["duracion"] = round(e["fin"] - e["inicio"], 2)
        if e["tipo"] == "pausa":                                  # la pausa de 3 s va dentro de esta escena
            e["temporizador_desde"] = segs[e["segmento"]]["fin"]
        if e["tipo"] == "historia":
            e["fondo"] = "noche" if e["escena"] in ("oficina", "celular") else "crema"
        elif "fondo" not in e:
            e["fondo"] = "noche" if e["tipo"] in OSCURAS else ("vino" if e["tipo"] == "mivalor" else "crema")
    # gestos (brazo a la sien): gancho, «Soy joya, no oferta», presentación de cada fila y «Ya no lo acepto»
    gestos = [[0.4, 4.2]]
    for e in escenas:
        if e["tipo"] in ("comentario", "numero") or (e["tipo"] == "tabla" and e.get("modo") == "fila"):
            gestos.append([e["inicio"] + 0.3, e["inicio"] + 3.3])
    for sg in TL["segmentos"]:
        k = sg["texto"].find(FRASE_FUERTE)
        if k >= 0:
            t0 = sg["inicio"] + (sg["fin"] - sg["inicio"]) * k / len(sg["texto"])
            gestos.append([round(t0 - 0.3, 2), round(t0 + 2.2, 2)])
    # barra de progreso: secciones (filas) y cuándo se completa cada una (al terminar su pausa de 3 s)
    secciones = []
    for e in escenas:
        if "seccion" in e:                               # la sección empieza con su segmento (la historia que la abre)
            secciones.append({"n": e["seccion"], "inicio": segs[e["segmento"]]["inicio"], "segmento": e["segmento"]})
        elif e["tipo"] == "tabla" and e.get("modo") == "fila":
            secciones.append({"n": e["fila"], "inicio": e["inicio"], "segmento": e["segmento"]})
        if e["tipo"] == "pausa":
            for sc in secciones:
                if sc["n"] == e["fila"]:
                    sc["completa"] = round(e["temporizador_desde"] + 3.0, 2)
    for a, b in zip(secciones, secciones[1:]):          # sin pausas: se completa al empezar la siguiente
        a.setdefault("completa", round(b["inicio"] - 0.5, 2))
    if secciones:
        secciones[-1].setdefault("completa", segs[secciones[-1]["segmento"]]["fin"])
    ocultar = [[e["inicio"], e["fin"]] for e in escenas if e["tipo"] in OCULTAR_PROGRESO]
    progreso = {"etiqueta": ETIQUETA_PROGRESO, "total": len(secciones), "secciones": secciones, "ocultar": ocultar}
    capitulos = []
    for sid, ancla, titulo in CAPITULOS:
        capitulos.append([0.0 if sid == 1 else tiempo_de_ancla(segs[sid], ancla), titulo])
    (AQUI / "escenas.json").write_text(json.dumps({"tabla": {"filas": FILAS, "celdas": TABLA}, "progreso": progreso,
                                                   "gestos": gestos, "capitulos": capitulos, "escenas": escenas},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    largas = [(e["n"], e["tipo"], e["duracion"]) for e in escenas if e["duracion"] > 30]
    seguidas = [(a["n"], a["tipo"]) for a, b in zip(escenas, escenas[1:]) if a["tipo"] == b["tipo"] and
                {k: v for k, v in a.items() if k not in ("n", "inicio", "fin", "duracion", "desde_frase", "segmento")} ==
                {k: v for k, v in b.items() if k not in ("n", "inicio", "fin", "duracion", "desde_frase", "segmento")}]
    print(len(escenas), "escenas · más larga", max(e["duracion"] for e in escenas), "s · >30 s:", largas, "· idénticas seguidas:", seguidas)
    claras = sum(e["duracion"] for e in escenas if e["fondo"] == "crema")
    print(f"claras {claras:.0f} s · oscuras {TL['duracion'] - claras:.0f} s")
    for e in escenas:
        m, s = divmod(round(e["inicio"], 1), 60)
        print(f"{e['n']:2d} {int(m)}:{s:04.1f} {e['duracion']:5.1f}s {e['fondo']:6s} {e['tipo']}")


if __name__ == "__main__":
    main()
