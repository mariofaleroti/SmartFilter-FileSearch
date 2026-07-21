@echo off
setlocal
cd /d "%~dp0"

echo Smart Filter - Build release Windows
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0BUILD_PORTABLE_WINDOWS.ps1"

if errorlevel 1 (
  echo.
  echo ERROR: no se pudo generar o validar el release portable.
  pause
  exit /b 1
)

echo.
echo Release portable generado y validado correctamente.
pause
