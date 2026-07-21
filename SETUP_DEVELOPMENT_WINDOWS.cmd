@echo off
setlocal
cd /d "%~dp0"

echo Smart Filter - Preparacion del entorno de desarrollo
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_DEVELOPMENT_WINDOWS.ps1"
if errorlevel 1 (
  echo.
  echo ERROR: no se pudo preparar el entorno.
  pause
  exit /b 1
)

echo.
echo Entorno preparado correctamente.
pause
