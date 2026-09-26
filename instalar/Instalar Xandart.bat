@echo off
chcp 65001 >nul
title Instalando Xandart
REM Doble clic y listo. Si este archivo esta junto a instalar.ps1 usa ese; si no, lo baja de GitHub.
if exist "%~dp0instalar.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; $s = Invoke-RestMethod 'https://raw.githubusercontent.com/XanderrrCorp/xanderrr/claude/new-session-uq98jd/instalar/instalar.ps1'; & ([scriptblock]::Create($s))"
)
if errorlevel 1 (
  echo.
  echo Algo fallo. Toma una foto de esta ventana y mandasela a Claude.
)
echo.
pause
