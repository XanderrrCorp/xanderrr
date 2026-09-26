# Xandart - instalador y actualizador para Windows.
# Deja todo en %LOCALAPPDATA%\Xandart y un acceso directo "Xandart" en el escritorio.
# Correrlo otra vez actualiza el programa sin tocar tus claves (.env) ni tus videos (proyectos).
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # descargas mucho mas rapidas
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Rama    = 'claude/new-session-uq98jd'
$Zip     = "https://github.com/XanderrrCorp/xanderrr/archive/refs/heads/$Rama.zip"
$Destino = Join-Path $env:LOCALAPPDATA 'Xandart'
$Venv    = Join-Path $Destino '.venv'
$Uv      = Join-Path $Destino 'herramientas\uv.exe'
# Python propio y portatil dentro de la carpeta de Xandart: no usa el instalador
# de Windows (que falla con el error 1603 si hay otro Python) ni pide administrador.
$env:UV_PYTHON_INSTALL_DIR = Join-Path $Destino 'python'
$env:UV_PYTHON_PREFERENCE  = 'only-managed'
$env:UV_CACHE_DIR          = Join-Path $Destino 'cache'   # se borra al final: ahorra espacio
$env:UV_LINK_MODE          = 'copy'

function Paso($texto) { Write-Host "`n==> $texto" -ForegroundColor Magenta }
function RefrescarPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User') + ';' +
                (Join-Path $env:USERPROFILE '.local\bin')
}

Write-Host '  XANDART' -ForegroundColor Magenta

# ---------------------------------------------------------------- 0. espacio
$unidad = Get-PSDrive ($env:LOCALAPPDATA.Substring(0, 1))
$libreGb = [math]::Round($unidad.Free / 1GB, 1)
if ($libreGb -lt 3) {
    Write-Host ''
    Write-Host "  Tu disco $($unidad.Name): tiene solo $libreGb GB libres y Xandart necesita al menos 3 GB" -ForegroundColor Yellow
    Write-Host '  (el programa ocupa ~1 GB y cada video terminado ~200 MB).' -ForegroundColor Yellow
    Write-Host '  Libera espacio y vuelve a correr el instalador:' -ForegroundColor Yellow
    Write-Host '   - Inicio > escribe "Liberador de espacio en disco" > marca todo > Aceptar' -ForegroundColor Yellow
    Write-Host '   - Vacia la Papelera y borra lo que no uses de Descargas' -ForegroundColor Yellow
    Write-Host '   - Configuracion > Sistema > Almacenamiento > Archivos temporales > Quitar' -ForegroundColor Yellow
    throw "Falta espacio en el disco ($libreGb GB libres)."
}
Write-Host "  Espacio libre: $libreGb GB"
Write-Host '  Instalando... no cierres esta ventana (tarda unos 5 minutos).'

# ---------------------------------------------------------------- 1. Python
Paso '1/5 Python (portatil, solo para Xandart)'
New-Item -ItemType Directory -Force (Split-Path $Uv) | Out-Null
if (-not (Test-Path $Uv)) {
    $tmpUv = Join-Path $env:TEMP ('uv-' + [guid]::NewGuid())
    New-Item -ItemType Directory -Force $tmpUv | Out-Null
    Invoke-WebRequest 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' -OutFile "$tmpUv\uv.zip"
    Expand-Archive "$tmpUv\uv.zip" -DestinationPath $tmpUv -Force
    Copy-Item (Get-ChildItem $tmpUv -Recurse -Filter uv.exe | Select-Object -First 1).FullName $Uv
    Remove-Item $tmpUv -Recurse -Force -ErrorAction SilentlyContinue
}
& $Uv python install 3.12
if ($LASTEXITCODE -ne 0) { throw 'No se pudo bajar Python (revisa tu internet y corre de nuevo).' }
Write-Host '   listo'

# ---------------------------------------------------------------- 2. Xandart
Paso '2/5 Descargando Xandart'
$tmp = Join-Path $env:TEMP ('xandart-' + [guid]::NewGuid())
New-Item -ItemType Directory -Force $tmp | Out-Null
Invoke-WebRequest $Zip -OutFile "$tmp\xandart.zip"
Expand-Archive "$tmp\xandart.zip" -DestinationPath $tmp -Force
$fuente = Get-ChildItem $tmp -Directory | Select-Object -First 1
New-Item -ItemType Directory -Force $Destino | Out-Null
# copia encima sin borrar: .env (claves), proyectos y logs se conservan
robocopy $fuente.FullName $Destino /E /NFL /NDL /NJH /NJS /NP /XD .venv proyectos logs | Out-Null
if ($LASTEXITCODE -ge 8) { throw "No se pudo copiar Xandart a $Destino" }
Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   listo: $Destino"

# ---------------------------------------------------------------- 3. dependencias
Paso '3/5 Instalando lo que necesita (imagenes, video, pagina)'
if (-not (Test-Path "$Venv\Scripts\pythonw.exe")) {
    if (Test-Path $Venv) { Remove-Item $Venv -Recurse -Force }
    & $Uv venv --python 3.12 $Venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el entorno de Xandart.' }
}
& $Uv pip install --python "$Venv\Scripts\python.exe" -e $Destino
if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de las dependencias (revisa tu internet y corre de nuevo).' }
Remove-Item $env:UV_CACHE_DIR -Recurse -Force -ErrorAction SilentlyContinue
Write-Host '   listo'

# ---------------------------------------------------------------- 4. Claude
Paso '4/5 Claude (escribe los guiones con tu suscripcion)'
RefrescarPath
if (-not (Get-Command claude -ErrorAction SilentlyContinue) -and -not (Test-Path "$env:USERPROFILE\.local\bin\claude.exe")) {
    # en otro proceso: si su instalador termina con 'exit' no corta este
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex"
    if ($LASTEXITCODE -ne 0) { Write-Host '   No se pudo instalar Claude ahora; la pagina te avisara y puedes reintentar luego.' -ForegroundColor Yellow }
    RefrescarPath
} else { Write-Host '   ya estaba instalado' }

# ---------------------------------------------------------------- 5. accesos directos
Paso '5/5 Accesos directos'
$shell = New-Object -ComObject WScript.Shell
$icono = Join-Path $Destino 'instalar\xandart.ico'
function Acceso($ruta, $destino, $argumentos, $descripcion) {
    $a = $shell.CreateShortcut($ruta)
    $a.TargetPath = $destino; $a.Arguments = $argumentos
    $a.WorkingDirectory = $Destino; $a.Description = $descripcion
    if (Test-Path $icono) { $a.IconLocation = $icono }
    $a.Save()
}
$escritorio = [Environment]::GetFolderPath('Desktop')
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'Xandart'
New-Item -ItemType Directory -Force $menu | Out-Null
Acceso "$escritorio\Xandart.lnk" "$Venv\Scripts\pythonw.exe" '-m estudio.app' 'Abre Xandart en el navegador'
Acceso "$menu\Xandart.lnk" "$Venv\Scripts\pythonw.exe" '-m estudio.app' 'Abre Xandart en el navegador'
Acceso "$menu\Actualizar Xandart.lnk" 'powershell.exe' "-NoProfile -ExecutionPolicy Bypass -File `"$Destino\instalar\instalar.ps1`"" 'Baja la ultima version de Xandart'
Write-Host '   listo: "Xandart" en el escritorio'

Write-Host "`nXandart quedo instalado. Se abre en tu navegador..." -ForegroundColor Green
Write-Host 'La primera vez: entra a Ajustes, pega tus claves y dale "Iniciar sesion" en Claude.'
Start-Process "$Venv\Scripts\pythonw.exe" -ArgumentList '-m', 'estudio.app' -WorkingDirectory $Destino
Start-Sleep -Seconds 3
