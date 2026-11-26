@echo off
rem Read Aloud Desktop Utility - Quick Stop (Without Uninstalling)
echo ========================================================
echo  Read Aloud Desktop Utility - Stop
echo ========================================================
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"

echo.
ping -n 3 127.0.0.1 >nul
