@echo off
chcp 65001 >nul
title Xandart en el celular
REM Doble clic: abre Xandart Nueva para usarla tambien desde el celular (misma Wi-Fi). Pide tu contrasena.
set "XN=%LOCALAPPDATA%\XandartNueva"
if not exist "%XN%\.venv\Scripts\python.exe" (
  echo No encuentro Xandart Nueva en este computador. Instalala primero con "Instalar Xandart Nueva".
  pause
  exit /b 1
)
cd /d "%XN%"
"%XN%\.venv\Scripts\python.exe" -m estudio.app --celular
pause
