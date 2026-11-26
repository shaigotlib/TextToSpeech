@echo off
rem Read Aloud Desktop Utility - Quick 1-Click Installer
echo ========================================================
echo  Read Aloud Desktop Utility - Installer
echo ========================================================
echo.

cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation encountered an error. Please review messages above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
