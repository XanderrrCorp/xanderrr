"""Fase 4 preparada: dónde va cada plantilla animada de Peligro Tropical."""
from estudio.pt_animado.plan import planear, minutos_animados


def _video():
    fr, t = [], 0.0
    def add(sec, intn, txt, d):
        nonlocal t
        fr.append({"seccion": sec, "intencion": intn, "texto": txt, "ini": t, "fin": t + d}); t += d + 0.3
    add("gancho", "gancho", "En Colombia hay una serpiente que causa la mayoría de mordeduras.", 4)
    add("gancho", "gancho", "Imagina que vas caminando con tus botas por el potrero al amanecer.", 8)
    add("gancho", "gancho", "Y ahí, junto a tu pie, la mapaná levanta la cabeza y muerde.", 20)
    for k, animal in enumerate(["avispa", "alacrán", "rana", "araña"]):
        add(f"nivel_{k}", "dato_impactante", f"La {animal} tiene un dato absurdo.", 6)
        add(f"nivel_{k}", "explicacion", f"Imagina que estás en la casa y una {animal} te pica en la mano.", 9)
        add(f"nivel_{k}", "explicacion", "Verás que el veneno hace que todo duela mucho.", 20)
    add("cierre", "cierre", "Cuéntame en los comentarios cuál te dio más miedo.", 12)
    return fr


def test_intro_encuentros_transiciones_y_cierre():
    clips = planear(_video())
    tipos = [c["plantilla"] for c in clips]
    assert tipos[0] == "intro" and tipos[-1] == "cierre"
    assert tipos.count("encuentro") == 4 and tipos.count("transicion") == 3
    intro = clips[0]
    assert 30 <= intro["fin"] <= 60 and intro["luz"] == "amanecer" and intro["escenario"] == "finca"
    k = intro["claves"]
    assert k["gancho_fin"] < k["botas"] < k["revela"] < k["susto"] < k["fin"]
    for c in clips:
        if c["plantilla"] == "encuentro":
            assert 5 <= c["fin"] - c["inicio"] <= 10 and c["escenario"] == "casa"
            assert 0 <= c["claves"]["aparece"] < c["claves"]["reaccion"] < c["claves"]["fin"]
        if c["plantilla"] == "transicion":
            assert 3 <= c["fin"] - c["inicio"] <= 5
    inicios = [c["inicio"] for c in clips]
    assert inicios == sorted(inicios)
    assert all(a["fin"] <= b["inicio"] + 1e-6 for a, b in zip(clips, clips[1:]))   # no se pisan
    assert 0.5 < minutos_animados(clips) < 4
