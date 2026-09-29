import pytest

from estudio.config import ConfigCostos, PrecioFaltante, formato_cop
from estudio.costos import FrenoPresupuesto, LibroCostos


def test_registra_en_jsonl(tmp_path, config):
    libro = LibroCostos(tmp_path, config)
    e = libro.registrar(modulo="guionista", proveedor="anthropic", modelo="claude-opus-5",
                        unidades={"input": 1000, "output": 500}, costo_usd=0.1)
    assert e["costo_cop"] == pytest.approx(310)
    assert (tmp_path / "logs" / "costos.jsonl").read_text(encoding="utf-8").count("\n") == 1
    assert libro.total_cop() == pytest.approx(310)


def test_animacion_no_cuenta_en_base(tmp_path, config):
    libro = LibroCostos(tmp_path, config)
    libro.registrar(modulo="animar", proveedor="x", modelo="y", unidades={"seg": 5},
                    costo_usd=3.0, categoria="animacion")
    assert libro.total_cop() == 0
    assert libro.total_cop("animacion") == pytest.approx(9300)


def test_freno_duro_al_maximo(tmp_path, config):
    libro = LibroCostos(tmp_path, config)
    casi = config.datos["presupuesto_maximo_cop"] / config.datos["trm_cop_por_usd"] - 0.2
    libro.registrar(modulo="imagenes", proveedor="gemini", modelo="m", unidades={"n": 1}, costo_usd=casi)
    with pytest.raises(FrenoPresupuesto):
        libro.autorizar(0.5)  # a 0,2 USD del máximo, 0,5 más lo pasa
    libro.autorizar(0.5, permiso=True)
    libro.autorizar(0.1)


def test_precio_null_avisa(config):
    with pytest.raises(PrecioFaltante):
        config.precio("animacion_por_segundo")
    datos = dict(config.datos)
    datos["precios_usd"] = {**config.precios, "claude_por_millon_tokens": {}}
    with pytest.raises(PrecioFaltante):
        ConfigCostos(datos).costo_claude("claude-opus-5", 1, 1)


def test_formato_cop():
    assert formato_cop(15000) == "15.000 COP"


def test_escribir_json_reintenta_si_windows_niega_el_acceso(tmp_path, monkeypatch):
    import os

    from estudio import config

    reales, fallos = os.replace, [2]

    def replace(a, b):
        if fallos[0]:
            fallos[0] -= 1
            raise PermissionError(5, "Acceso denegado")
        reales(a, b)

    monkeypatch.setattr(config.os, "replace", replace)
    config.escribir_json(tmp_path / "m.json", {"a": 1})
    assert config.leer_json(tmp_path / "m.json") == {"a": 1}


def test_manifiesto_pendiente_no_se_pierde(tmp_path):
    from estudio import config

    (tmp_path / "m.json").write_text('{"a": 1}', encoding="utf-8")
    (tmp_path / "m.json.tmp").write_text('{"a": 1, "b": 2}', encoding="utf-8")   # escritura que no terminó
    assert config.leer_json_con_pendiente(tmp_path / "m.json") == {"a": 1, "b": 2}
    assert not (tmp_path / "m.json.tmp").exists() and config.leer_json(tmp_path / "m.json")["b"] == 2
    (tmp_path / "m.json.tmp").write_text('{"roto', encoding="utf-8")               # a medias: se ignora
    assert config.leer_json_con_pendiente(tmp_path / "m.json") == {"a": 1, "b": 2}
