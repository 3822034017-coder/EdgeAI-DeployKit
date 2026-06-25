@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-runtime-windows.ps1" %*
if errorlevel 1 (
  echo.
  echo EdgeAI-DeployKit runtime bootstrap failed.
  pause
)
