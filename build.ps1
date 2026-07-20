param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

python tools/build_icon.py
if ($LASTEXITCODE -ne 0) { throw "No se pudo generar el icono." }
python -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name monitor_dim_overlay `
    --icon build/monitor-dim-overlay.ico `
    --version-file packaging/windows_version_info.txt `
    monitor_dim_overlay.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo generar el ejecutable." }

$AppVersion = python -c "from monitor_dim import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0 -or -not $AppVersion) { throw "No se pudo determinar la versión del ejecutable." }
$PortableExe = "dist/MonitorDimOverlay-$AppVersion.exe"
Copy-Item -LiteralPath "dist/monitor_dim_overlay.exe" -Destination $PortableExe -Force

if ($Installer) {
    $Iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if (-not $Iscc) {
        $Candidates = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
        )
        $IsccPath = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $IsccPath) {
            throw "Inno Setup (iscc) no está instalado o no está disponible en PATH."
        }
    } else {
        $IsccPath = $Iscc.Source
    }
    & $IsccPath packaging/MonitorDimOverlay.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup no pudo generar el instalador." }
}

Write-Host "Build terminado: dist/monitor_dim_overlay.exe"
Write-Host "Portable versionado: $PortableExe"
