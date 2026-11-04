@echo off
rem Read Aloud Background Launcher
echo ========================================================
echo  Starting Read Aloud Desktop Utility in the background
echo  Hotkey: Ctrl + Shift + R
echo ========================================================

rem Terminate any previous instance
taskkill /F /FI "IMAGENAME eq pythonw.exe" /FI "WINDOWTITLE eq ReadAloud*" >nul 2>&1

rem Launch main.pyw silently using pythonw
start "" pythonw "%~dp0main.pyw"

echo [OK] Read Aloud is now running in your system tray!
echo Select any text in PowerShell, Notepad, Outlook, etc.
echo and press Ctrl + Shift + R to read it aloud.
echo ========================================================
timeout /t 3 >nul
