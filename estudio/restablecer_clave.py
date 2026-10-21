"""(Paso B) «Restablecer mi contraseña»: el dueño pone una contraseña nueva desde su PC, sin correo.

Se abre con el acceso directo del menú Inicio o con «Restablecer mi contraseña.bat» junto al instalador. Pide la
contraseña nueva dos veces en la ventana negra (no se ve lo que se escribe), cierra las sesiones abiertas y muestra el
correo con el que se entra. No toca nada más: canales, videos y ajustes quedan igual.
"""
from __future__ import annotations

import getpass
import sys


def restablecer(clave: str) -> str:
    """Pone la contraseña nueva al dueño y devuelve su correo. Lanza ValueError si la contraseña no sirve."""
    from .plataforma import acceso, db
    from .plataforma.cuentas import cuenta_local

    problema = acceso.problema_clave(clave)
    if problema:
        raise ValueError(problema)
    db.preparar()
    with db.sesion() as s:
        u, _ = cuenta_local(s)
        u.clave_hash = acceso.hash_clave(clave)
        u.bloqueado, u.activo = False, True
        email = u.email
    acceso.olvidar_sesiones()
    acceso.olvidar_fallos(email)
    return email


def main() -> int:
    from .config import aplicar_ajustes_de_instalacion
    from .plataforma.acceso import LARGO_MINIMO

    aplicar_ajustes_de_instalacion()
    print("\n  RESTABLECER LA CONTRASEÑA DE XANDART (cuenta del dueño)\n")
    print("  Escribe tu contraseña nueva y presiona Enter. Mientras escribes no se ve nada: es normal.")
    print(f"  Mínimo {LARGO_MINIMO} caracteres.\n")
    for _ in range(3):
        clave = getpass.getpass("  Contraseña nueva: ")
        otra = getpass.getpass("  Escríbela otra vez: ")
        if clave != otra:
            print("\n  No coinciden. Inténtalo de nuevo.\n")
            continue
        try:
            email = restablecer(clave)
        except ValueError as ex:
            print(f"\n  {ex} Inténtalo de nuevo.\n")
            continue
        print("\n  Listo. Tu contraseña quedó cambiada.")
        print(f"  Entra a Xandart con el correo: {email}")
        print("  Si Xandart estaba abierto en el navegador, te pedirá entrar de nuevo.\n")
        return 0
    print("\n  No se cambió la contraseña. Vuelve a abrir este archivo cuando quieras.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
