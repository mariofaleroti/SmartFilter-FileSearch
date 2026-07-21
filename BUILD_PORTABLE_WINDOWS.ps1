try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force } catch {}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$PythonExecutable = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory = $true)][string]$Description,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "== $Description ==" -ForegroundColor DarkCyan
    & $script:PythonExecutable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description falló con código de salida $LASTEXITCODE."
    }
}

function Require-Path {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Description
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Falta $Description $Path"
    }
}

& $PythonExecutable --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Python no está disponible. Ejecutar SETUP_DEVELOPMENT_WINDOWS.cmd."
}

foreach ($required in @(
    ".\requirements.txt",
    ".\requirements-dev.txt",
    ".\SmartFilter.spec",
    ".\SmartFilterCLI.spec",
    ".\tools\build_release.py",
    ".\tools\validate_portable_build_integrity.py",
    ".\smart_filter\app_info.py",
    ".\resources\defaults\settings.json",
    ".\resources\defaults\categories.json",
    ".\assets\app_icon.ico"
)) {
    Require-Path -Path $required -Description "archivo de build"
}

Invoke-PythonChecked -Description "Instalación de dependencias de build" -Arguments @("-m", "pip", "install", "-r", "requirements-dev.txt")

$sharedCodeVersion = (& $PythonExecutable -c "from smart_filter.bootstrap import REQUIRED_SHAREDCODE_VERSION, ensure_sharedcode_on_path, get_installed_sharedcode_version; ensure_sharedcode_on_path(); print(get_installed_sharedcode_version() or REQUIRED_SHAREDCODE_VERSION)").Trim()
if ($LASTEXITCODE -ne 0 -or $sharedCodeVersion -ne "1.0.0") {
    throw "SharedCode Cores 1.0.0 no está instalado correctamente."
}

Invoke-PythonChecked -Description "Validación de templates instalados de RenderCore" -Arguments @("-c", "from importlib.util import find_spec; from pathlib import Path; s=find_spec('render_core'); p=Path(next(iter(s.submodule_search_locations))) / 'templates'; assert p.is_dir(), p; print(p)")

$appVersion = (& $PythonExecutable -c "from smart_filter.app_info import APP_VERSION; print(APP_VERSION)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $appVersion) {
    throw "No se pudo resolver la versión actual de Smart Filter."
}

$releaseDir = ".\release\SmartFilter"
$cliExecutable = Join-Path $releaseDir "SmartFilterCLI.exe"
$guiExecutable = Join-Path $releaseDir "SmartFilter.exe"
$portableZip = ".\SmartFilter_Portable_v$($appVersion).zip"

Write-Host "== Smart Filter $appVersion · build portable ==" -ForegroundColor Cyan
Write-Host "Proyecto: $PSScriptRoot" -ForegroundColor DarkCyan
Write-Host "SharedCode Cores: $sharedCodeVersion (paquete instalado)" -ForegroundColor DarkCyan

Invoke-PythonChecked -Description "Validación de defaults de fábrica" -Arguments @("-m", "tools.validate_factory_defaults")
Invoke-PythonChecked -Description "Validación previa del creador de release" -Arguments @("-m", "tools.validate_portable_build_integrity")
Invoke-PythonChecked -Description "Suite de estabilización" -Arguments @("-m", "tools.run_release_validation")

Remove-Item ".\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item ".\release" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $portableZip -Force -ErrorAction SilentlyContinue

Invoke-PythonChecked -Description "Generación y autoprueba del release" -Arguments @("tools\build_release.py", "--build-exe")

Require-Path -Path $guiExecutable -Description "SmartFilter.exe"
Require-Path -Path $cliExecutable -Description "SmartFilterCLI.exe"
Require-Path -Path (Join-Path $releaseDir "tool_manifest.json") -Description "tool_manifest.json"

Write-Host "== Autoprueba final del ejecutable portable ==" -ForegroundColor DarkCyan
& $cliExecutable --portable-self-check
if ($LASTEXITCODE -ne 0) {
    throw "SmartFilterCLI.exe no superó --portable-self-check."
}

Compress-Archive -Path $releaseDir -DestinationPath $portableZip -Force
Require-Path -Path $portableZip -Description "ZIP portable"

Invoke-PythonChecked -Description "Validación del ZIP portable" -Arguments @("-m", "tools.validate_portable_archive", $portableZip)

Write-Host ""
Write-Host "OK: $releaseDir" -ForegroundColor Green
Write-Host "OK: $portableZip" -ForegroundColor Green
Write-Host "Versión validada: $appVersion" -ForegroundColor Green
