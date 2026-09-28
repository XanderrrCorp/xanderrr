@echo off
chcp 65001 >nul
title Instalando Xandart Nueva (al lado de la de siempre)
REM Doble clic y listo. Si este archivo esta junto a instalar.ps1 usa ese; si no, lo baja de GitHub.
if exist "%~dp0instalar-nueva.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-nueva.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; $s = (Invoke-RestMethod 'https://raw.githubusercontent.com/XanderrrCorp/xanderrr/claude/xandart-saas/instalar/instalar-nueva.ps1').TrimStart([char]0xFEFF); & ([scriptblock]::Create($s))"
)
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo Algo fallo. Toma una foto de esta ventana y mandasela a Claude.
) else (
  echo Listo. Ya puedes cerrar esta ventana.
)
pause
exit /b %ERR%
