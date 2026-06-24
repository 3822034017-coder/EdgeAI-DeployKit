@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-windows.ps1" %*
if errorlevel 1 (
  echo.
  echo EdgeAI-DeployKit failed to start. Check outputs\logs for details.
  pause
)

