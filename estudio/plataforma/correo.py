"""Correos de Xandart por SMTP de Gmail con contraseña de aplicación.

Se configuran en `.env` (⚙ Ajustes), nunca en el código:
    XANDART_SMTP_USUARIO=tu_correo@gmail.com
    XANDART_SMTP_CLAVE=contraseña de aplicación de 16 letras (myaccount.google.com/apppasswords)
Sin eso, los avisos solo se ven en la administración.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ..config import clave_api

SERVIDOR, PUERTO = "smtp.gmail.com", 465


def configurado() -> bool:
    return bool(clave_api("XANDART_SMTP_USUARIO") and clave_api("XANDART_SMTP_CLAVE"))


def para_avisos(email_dueno: str | None) -> str | None:
    """A dónde van los avisos: el correo del dueño si es real; si no (modo local sin correo
    configurado, «…@xandart.local»), el mismo Gmail que los manda."""
    if email_dueno and not email_dueno.endswith(".local"):
        return email_dueno
    return clave_api("XANDART_SMTP_USUARIO")


def enviar(para: str, asunto: str, texto: str) -> bool:
    """True si salió. Si no está configurado, False (no es un error: el aviso queda en la administración)."""
    usuario, clave = clave_api("XANDART_SMTP_USUARIO"), clave_api("XANDART_SMTP_CLAVE")
    if not (usuario and clave):
        return False
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = f"Xandart <{usuario}>", para, asunto
    m.set_content(texto)
    with smtplib.SMTP_SSL(SERVIDOR, PUERTO, timeout=30) as smtp:
        smtp.login(usuario, clave)
        smtp.send_message(m)
    return True
