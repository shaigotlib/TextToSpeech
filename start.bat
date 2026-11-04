@echo off
rem Read Aloud Background Launcher
echo ========================================================
echo  Starting Read Aloud Desktop Utility in the background
echo  Hotkey: Ctrl + Shift + R
echo ========================================================

rem Terminate any previous main.pyw instances cleanly
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.pyw*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

rem Launch main.pyw silently using pythonw
start "" pythonw "%~dp0main.pyw"

echo [OK] Read Aloud is now running in your system tray!
echo Select any text in PowerShell, Notepad, Outlook, etc.
echo and press Ctrl + Shift + R to read it aloud.
echo ========================================================
timeout /t 3 >nul
