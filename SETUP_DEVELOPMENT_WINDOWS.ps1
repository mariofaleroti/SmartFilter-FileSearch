try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force } catch {}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear .venv." }
}

$PythonExecutable = ".\.venv\Scripts\python.exe"
& $PythonExecutable -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $PythonExecutable -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
& $PythonExecutable -c "from smart_filter.bootstrap import ensure_sharedcode_on_path, get_installed_sharedcode_version; ensure_sharedcode_on_path(); print('SharedCode Cores', get_installed_sharedcode_version())"
if ($LASTEXITCODE -ne 0) { throw "SharedCode Cores no quedó disponible." }
& $PythonExecutable -m tools.run_release_validation
if ($LASTEXITCODE -ne 0) { throw "La validación del entorno falló." }

Write-Host ""
Write-Host "OK: usar .\.venv\Scripts\python.exe app.py" -ForegroundColor Green
