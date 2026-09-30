# Xandart NUEVA (plataforma en pruebas) - se instala AL LADO de la de siempre, sin reemplazarla.
# Queda en %LOCALAPPDATA%\XandartNueva, abre en el puerto 8031 y lee tus videos, estilos, canales
# y sonidos de la Xandart de siempre. La primera vez hace una copia de seguridad completa en
# Documentos\Xandart copias antes de preparar nada. Correrlo otra vez la actualiza.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'   # descargas mucho mas rapidas
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Rama    = 'claude/xandart-saas'
$Zip     = "https://github.com/XanderrrCorp/xanderrr/archive/refs/heads/$Rama.zip"
$Destino = Join-Path $env:LOCALAPPDATA 'XandartNueva'
$Actual  = Join-Path $env:LOCALAPPDATA 'Xandart'        # la de siempre: no se toca
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

Write-Host '  XANDART NUEVA (en pruebas, al lado de la de siempre)' -ForegroundColor Magenta

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
# si Xandart esta abierto, Windows bloquea sus archivos: se cierra antes de actualizar
# (el acceso directo abre un lanzador que a su vez abre otro python: se cierran todos los de Xandart)
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { ($_.Name -like 'python*') -and
        ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($Destino + '\', [StringComparison]::OrdinalIgnoreCase)) } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
if (-not (Test-Path "$Venv\Scripts\pythonw.exe")) {
    if (Test-Path $Venv) { Remove-Item $Venv -Recurse -Force }
    & $Uv venv --python 3.12 $Venv
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo preparar el entorno de Xandart.' }
}
& $Uv pip install --python "$Venv\Scripts\python.exe" -e $Destino
if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de las dependencias (revisa tu internet y corre de nuevo).' }
# quitar fondos de las miniaturas (opcional: si falla, Xandart usa el recorte simple)
& $Uv pip install --python "$Venv\Scripts\python.exe" "rembg[cpu]>=2.0.50"
if ($LASTEXITCODE -ne 0) { Write-Host '   (no se pudo instalar rembg: las miniaturas usan el recorte simple)' }
# Whisper local para el modo Tracy (tiempos reales de la voz; el modelo se baja la primera vez que se usa)
& $Uv pip install --python "$Venv\Scripts\python.exe" "faster-whisper>=1.0"
if ($LASTEXITCODE -ne 0) { Write-Host '   (no se pudo instalar Whisper: el modo Tracy no podra alinear la voz)' }
Remove-Item $env:UV_CACHE_DIR -Recurse -Force -ErrorAction SilentlyContinue
Write-Host '   listo'

# ---------------------------------------------------------------- 3b. ajustes para convivir
# La nueva usa otro puerto y lee los datos de la de siempre. Las claves se copian de la de siempre
# (quedan solo en este computador). Nunca se escribe nada en la carpeta de la de siempre.
$envNueva = Join-Path $Destino '.env'
# lista que se modifica en su lugar: funciona igual corriendo este archivo o bajandolo como bloque
# (el .bat lo baja de GitHub y lo corre como bloque: ahi $script: apuntaba a otra variable y el .env quedaba vacio)
$lineas = New-Object System.Collections.ArrayList
if (Test-Path $envNueva) { foreach ($l in (Get-Content $envNueva -Encoding UTF8)) { if ($l.Trim()) { [void]$lineas.Add($l.TrimStart([char]0xFEFF)) } } }
$quiero = [ordered]@{
    'XANDART_PUERTO'     = '8031'
    'XANDART_ABRIR'      = '/app/'
    'XANDART_ORIGEN'     = $Actual
    'ESTUDIO_PROYECTOS'  = (Join-Path $Actual 'proyectos')
    'XANDART_BIBLIOTECA' = (Join-Path $Actual 'biblioteca')
}
$envActual = Join-Path $Actual '.env'
if (Test-Path $envActual) {
    foreach ($l in (Get-Content $envActual -Encoding UTF8)) {
        $l = $l.TrimStart([char]0xFEFF)
        if ($l -match '^([A-Z_]+_API_KEY|XANDART_SMTP_[A-Z]+)=') { if (-not $quiero.Contains($Matches[1])) { $quiero[$Matches[1]] = $l.Substring($Matches[1].Length + 1) } }
    }
}
foreach ($clave in @($quiero.Keys)) {
    $ya = $false
    foreach ($l in $lineas) { if ($l -like "$clave=*") { $ya = $true } }
    if (-not $ya) { [void]$lineas.Add("$clave=$($quiero[$clave])") }
}
[IO.File]::WriteAllLines($envNueva, [string[]]$lineas)   # UTF-8 sin BOM
if (-not (Select-String -Path $envNueva -Pattern '^ESTUDIO_PROYECTOS=' -Quiet)) { throw 'No se pudo guardar la configuracion de la Xandart nueva (.env)' }
Write-Host "   usa tus videos de: $(Join-Path $Actual 'proyectos')"
Write-Host "   copia de seguridad: $([Environment]::GetFolderPath('MyDocuments'))\Xandart copias"

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
Acceso "$escritorio\Xandart Nueva.lnk" "$Venv\Scripts\pythonw.exe" '-m estudio.app' 'Abre la Xandart nueva (en pruebas)'
Acceso "$menu\Xandart Nueva.lnk" "$Venv\Scripts\pythonw.exe" '-m estudio.app' 'Abre la Xandart nueva (en pruebas)'
Acceso "$menu\Actualizar Xandart Nueva.lnk" 'powershell.exe' "-NoProfile -ExecutionPolicy Bypass -File `"$Destino\instalar\instalar-nueva.ps1`"" 'Baja la ultima version de la Xandart nueva'
Write-Host '   listo: "Xandart Nueva" en el escritorio (la de siempre sigue igual)'

Write-Host "`nXandart Nueva quedo instalada. Se abre en tu navegador..." -ForegroundColor Green
Write-Host 'La primera vez hace la copia de seguridad completa (puede tardar unos minutos): la pagina te avisa cuando termine.'
Start-Process "$Venv\Scripts\pythonw.exe" -ArgumentList '-m', 'estudio.app' -WorkingDirectory $Destino
Start-Sleep -Seconds 3
