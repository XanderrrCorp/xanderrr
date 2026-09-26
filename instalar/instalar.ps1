# Xandart · instalador y actualizador para Windows.
# Deja todo en %LOCALAPPDATA%\Xandart y un acceso directo "Xandart" en el escritorio.
# Correrlo otra vez actualiza el programa sin tocar tus claves (.env) ni tus videos (proyectos).
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # descargas mucho más rápidas
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Rama    = 'claude/new-session-uq98jd'
$Zip     = "https://github.com/XanderrrCorp/xanderrr/archive/refs/heads/$Rama.zip"
$Destino = Join-Path $env:LOCALAPPDATA 'Xandart'
$Venv    = Join-Path $Destino '.venv'

function Paso($texto) { Write-Host "`n==> $texto" -ForegroundColor Magenta }
function RefrescarPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User') + ';' +
                (Join-Path $env:USERPROFILE '.local\bin')
}

function BuscarPython {
    foreach ($v in '3.12', '3.13', '3.11') {
        try { $r = & py "-$v" -c 'import sys; print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0 -and $r) { return $r.Trim() } } catch {}
    }
    foreach ($c in @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
                     "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
                     "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe")) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

Write-Host '  XANDART' -ForegroundColor Magenta
Write-Host '  Instalando... no cierres esta ventana (tarda unos 5 minutos).'

# ---------------------------------------------------------------- 1. Python
Paso '1/5 Python'
$Python = BuscarPython
if (-not $Python) {
    $hecho = $false
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
        RefrescarPath; $Python = BuscarPython; $hecho = [bool]$Python
    }
    if (-not $hecho) {
        $inst = Join-Path $env:TEMP 'python-3.12-instalador.exe'
        Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile $inst
        Start-Process $inst -Wait -ArgumentList '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1'
        RefrescarPath; $Python = BuscarPython
    }
    if (-not $Python) { throw 'No se pudo instalar Python. Instálalo desde python.org (marca "Add to PATH") y corre de nuevo el instalador.' }
}
Write-Host "   listo: $Python"

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
Paso '3/5 Instalando lo que necesita (imágenes, video, página)'
if (-not (Test-Path "$Venv\Scripts\python.exe")) { & $Python -m venv $Venv }
& "$Venv\Scripts\python.exe" -m pip install --upgrade pip --quiet --disable-pip-version-check
& "$Venv\Scripts\python.exe" -m pip install -e $Destino --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { throw 'Falló la instalación de las dependencias (revisa tu internet y corre de nuevo).' }
Write-Host '   listo'

# ---------------------------------------------------------------- 4. Claude
Paso '4/5 Claude (escribe los guiones con tu suscripción)'
RefrescarPath
if (-not (Get-Command claude -ErrorAction SilentlyContinue) -and -not (Test-Path "$env:USERPROFILE\.local\bin\claude.exe")) {
    try { Invoke-RestMethod https://claude.ai/install.ps1 | Invoke-Expression }
    catch { Write-Host '   No se pudo instalar Claude ahora; la página te avisará y puedes reintentar luego.' -ForegroundColor Yellow }
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
Acceso "$menu\Actualizar Xandart.lnk" 'powershell.exe' "-NoProfile -ExecutionPolicy Bypass -File `"$Destino\instalar\instalar.ps1`"" 'Baja la última versión de Xandart'
Write-Host '   listo: "Xandart" en el escritorio'

Write-Host "`nXandart quedó instalado. Se abre en tu navegador..." -ForegroundColor Green
Write-Host 'La primera vez: entra a Ajustes, pega tus claves y dale "Iniciar sesión" en Claude.'
Start-Process "$Venv\Scripts\pythonw.exe" -ArgumentList '-m', 'estudio.app' -WorkingDirectory $Destino
Start-Sleep -Seconds 3
