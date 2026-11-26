@echo off
rem Read Aloud Background Launcher
echo ========================================================
echo  Starting Read Aloud Desktop Utility in the background
echo  Hotkeys:
echo    Read / Stop:          Ctrl + Alt + R
echo    Pause / Resume:       Ctrl + Alt + Space
echo    Speed Up / Down:      Ctrl + Alt + Up / Down
echo    Skip Word Next:       Ctrl + Alt + Right
echo    Move Back Word:       Ctrl + Alt + Left
echo    Toggle Passthrough:   Ctrl + Alt + \
echo ========================================================

rem Terminate any previous main.pyw instances cleanly
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.pyw*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

rem Launch main.pyw silently using pythonw
start "" pythonw "%~dp0main.pyw"

echo [OK] Read Aloud is now running in your system tray!
echo Select any text in PowerShell, Notepad, Outlook, etc.
echo and press Ctrl + Alt + R to read it aloud.
echo Press Ctrl + Alt + \ to toggle shortcut passthrough.
echo ========================================================
ping -n 3 127.0.0.1 >nul

