@echo off
chcp 65001 >nul
title Restablecer mi contrasena de Xandart Nueva
REM Doble clic: pide tu contrasena nueva aqui mismo, sin correo. No toca tus canales ni tus videos.
set "XN=%LOCALAPPDATA%\XandartNueva"
if not exist "%XN%\.venv\Scripts\python.exe" (
  echo No encuentro Xandart Nueva en este computador. Instalala primero con "Instalar Xandart Nueva".
  pause
  exit /b 1
)
cd /d "%XN%"
"%XN%\.venv\Scripts\python.exe" -m estudio.restablecer_clave
set ERR=%ERRORLEVEL%
pause
exit /b %ERR%
