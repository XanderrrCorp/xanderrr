"""En Windows, los programas que lanza Xandart no abren ventanas negras."""
import subprocess

from estudio import sin_ventanas


def test_en_windows_se_lanzan_sin_ventana_salvo_que_se_pida(monkeypatch):
    vistos = []
    monkeypatch.setattr(subprocess.Popen, "__init__", lambda self, *a, **kw: vistos.append(kw.get("creationflags")))
    monkeypatch.setattr(sin_ventanas.os, "name", "nt")
    monkeypatch.setattr(sin_ventanas, "_activo", False)
    sin_ventanas.activar()
    subprocess.Popen(["ffmpeg", "-version"])
    subprocess.Popen(["cmd"], creationflags=0x10)             # quien pide su ventana, la tiene
    assert vistos == [sin_ventanas.SIN_VENTANA, 0x10]


def test_fuera_de_windows_no_cambia_nada(monkeypatch):
    original = subprocess.Popen.__init__
    monkeypatch.setattr(sin_ventanas, "_activo", False)
    monkeypatch.setattr(sin_ventanas.os, "name", "posix")
    sin_ventanas.activar()
    assert subprocess.Popen.__init__ is original
