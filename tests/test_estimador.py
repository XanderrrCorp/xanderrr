from estudio.config import ConfigCostos
from estudio.estimador import Plan, calcular, estimar


def test_escenas_salen_de_duracion_y_perfil(estilo, perfil, config):
    c = calcular(600, estilo, perfil, config, Plan(0.5, 2))
    assert c.escenas == 188  # 600 / 3.2
    c2 = calcular(1080, estilo, perfil, config, Plan(0.5, 2))
    assert c2.escenas == 338 and c2.imagenes_nuevas > c.imagenes_nuevas


def test_sin_animacion_y_local_gratis(estilo, perfil, config):
    c = calcular(600, estilo, perfil, config, Plan(0.5, 2))
    assert c.desglose_usd["local"] == 0
    assert "animacion" not in c.desglose_usd


def test_degradacion_en_orden(estilo, perfil, config):
    est = estimar(1080, estilo, perfil, config)
    reglas = [a.regla for a in est.ajustes]
    assert reglas == sorted(reglas) and reglas[0] == "2.4-1"
    assert est.calculo.total_usd < est.inicial.total_usd


def test_freno_si_supera_maximo(estilo, perfil, config):
    assert "FRENO" in estimar(3600, estilo, perfil, config).estado


def test_mejora_no_pasa_del_objetivo(estilo, perfil):
    datos = dict(ConfigCostos.cargar().datos)
    datos["presupuesto_objetivo_cop"] = 40000
    datos["presupuesto_maximo_cop"] = 50000
    cfg = ConfigCostos(datos)
    est = estimar(480, estilo, perfil, cfg)
    assert est.ajustes and est.ajustes[0].regla == "2.5"
    assert est.total_cop <= cfg.objetivo_cop
    assert est.calculo.plan.proporcion_unicas > estilo.proporcion_imagenes_unicas


def test_precios_faltantes_marcan_incompleta(estilo, perfil):
    datos = dict(ConfigCostos.cargar().datos)
    datos["precios_usd"] = {**datos["precios_usd"], "imagen_por_unidad": None}
    est = estimar(600, estilo, perfil, ConfigCostos(datos))
    assert "imagen_por_unidad" in est.calculo.faltantes
    assert "incompleta" in est.estado
