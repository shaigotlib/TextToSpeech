@echo off
rem Read Aloud Desktop Utility - Quick Uninstaller
echo ========================================================
echo  Read Aloud Desktop Utility - Uninstaller
echo ========================================================
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1"

echo.
pause
