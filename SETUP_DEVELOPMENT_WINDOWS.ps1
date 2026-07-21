try { Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force } catch {}

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-SupportedPython {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$Prefix = @()
    )

    & $Command @Prefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    $PythonCommand = $null
    $PythonPrefix = @()

    if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-SupportedPython -Command "py" -Prefix @("-3"))) {
        $PythonCommand = "py"
        $PythonPrefix = @("-3")
    }
    elseif ((Get-Command python -ErrorAction SilentlyContinue) -and (Test-SupportedPython -Command "python")) {
        $PythonCommand = "python"
    }
    else {
        throw "Python 3.11 o superior no está instalado o no está disponible en PATH. Instálelo y vuelva a ejecutar este asistente."
    }

    & $PythonCommand @PythonPrefix -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear .venv con $PythonCommand." }
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
