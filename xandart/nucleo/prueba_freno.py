"""
Prueba del freno duro en pesos (nucleo/freno.py) enganchado al medidor.

Una imagen y una toma de voz de mentira pasan por los mismos envoltorios que
las de verdad; se comprueba que se paran ANTES de pasar del maximo, que el
permiso explicito las deja seguir y que lo de la suscripcion no frena.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TMP = tempfile.mkdtemp(prefix="freno_")
RUTA_COSTOS = os.path.join(TMP, "costos.json")
with open(RUTA_COSTOS, "w", encoding="utf-8") as fh:
    json.dump({"presupuesto_maximo_cop": 1000, "trm_cop_por_usd": 4000}, fh)
os.environ["ESTUDIO_COSTOS"] = RUTA_COSTOS
os.environ["ESTUDIO_COSTE_GLOBAL"] = os.path.join(TMP, "global.jsonl")

from nucleo import Proyecto, coste, freno  # noqa: E402

FALLOS = []


def comprobar(condicion, texto):
    print(f"  {'ok  ' if condicion else 'FALLO'} {texto}")
    if not condicion:
        FALLOS.append(texto)


try:
    proyecto = Proyecto.crear(TMP, "Video de prueba")
    llamadas = {"imagen": 0, "voz": 0}

    def imagen_falsa(prompt, referencias, **_):
        llamadas["imagen"] += 1
        # 0,06 $ de tokens: a 4000 COP/USD son 240 COP por imagen
        return b"png", {"usage": {"input_tokens": 0, "output_tokens": 2000}, "quality": "low"}

    def toma_falsa(texto, cfg):
        llamadas["voz"] += 1
        return b"wav"

    medir_imagen = coste._medir_imagen(imagen_falsa)
    medir_voz = coste._medir_toma_real(toma_falsa)

    print("\nFRENO DE IMAGEN")
    frenado = None
    with coste.contexto(proyecto, "assets"):
        for _ in range(20):
            try:
                medir_imagen("un alacran", [])
            except freno.FrenoPresupuesto as ex:
                frenado = str(ex)
                break
    gastado = freno.gastado_usd(coste.Medidor(proyecto)) * 4000
    comprobar(frenado is not None, "la tanda se para sola")
    comprobar(gastado <= 1000, f"nunca pasa del maximo (gastado {gastado:.0f} COP)")
    comprobar(llamadas["imagen"] < 20, f"no se hicieron las 20 llamadas ({llamadas['imagen']})")
    comprobar("COP" in (frenado or ""), "el mensaje habla en pesos")

    print("\nPERMISO EXPLICITO")
    proyecto.config["permiso_superar_maximo"] = True
    antes = llamadas["imagen"]
    with coste.contexto(proyecto, "assets"):
        medir_imagen("un alacran", [])
    comprobar(llamadas["imagen"] == antes + 1, "con permiso la llamada se hace")
    proyecto.config["permiso_superar_maximo"] = False

    print("\nFRENO DE VOZ")
    with coste.contexto(proyecto, "voz"):
        try:
            medir_voz("hola " * 10, {})
            voz_frenada = False
        except freno.FrenoPresupuesto:
            voz_frenada = True
    comprobar(voz_frenada, "con el maximo ya pasado, la voz tampoco se genera")

    print("\nSIN CONTEXTO NO SE ATRIBUYE NI SE FRENA")
    antes = llamadas["imagen"]
    medir_imagen("sin proyecto", [])
    comprobar(llamadas["imagen"] == antes + 1, "una llamada huerfana no se bloquea")

    print("\nMAXIMO PROPIO DEL VIDEO")
    otro = Proyecto.crear(TMP, "Otro video")
    otro.config["presupuesto_maximo_cop"] = 200
    with coste.contexto(otro, "assets"):
        try:
            medir_imagen("x", [])
            primera = "pasa"
        except freno.FrenoPresupuesto:
            primera = "frena"
    comprobar(primera == "frena", "un maximo de 200 COP no deja pasar una imagen estimada en 240")
finally:
    shutil.rmtree(TMP, ignore_errors=True)

if FALLOS:
    print(f"\nPRUEBA FRENO: {len(FALLOS)} FALLOS")
    sys.exit(1)
print("\nPRUEBA FRENO OK: todas las comprobaciones pasan")
