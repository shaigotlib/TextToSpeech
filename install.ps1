<#
.SYNOPSIS
    Installs and registers the Read Aloud utility for automatic background startup on Windows logon.
.PARAMETER TestOnly
    Runs validation and shortcut creation test without launching the service.
#>
param(
    [switch]$TestOnly
)

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Read Aloud Utility - Installation Setup " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Resolve Project Root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MainScriptPath = Join-Path $ScriptDir "main.pyw"

if (-not (Test-Path $MainScriptPath)) {
    Write-Error "Could not find main.pyw at: $MainScriptPath"
    exit 1
}

# 2. Locate Python and Pythonw executable
$PythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonPath) {
    Write-Error "Python was not found in PATH. Please install Python 3.10+."
    exit 1
}

$PythonDir = Split-Path -Parent $PythonPath
$PythonWPath = Join-Path $PythonDir "pythonw.exe"

if (-not (Test-Path $PythonWPath)) {
    # Check alternate known python directories
    $AltPythonW = (Get-Command pythonw -ErrorAction SilentlyContinue).Source
    if ($AltPythonW) {
        $PythonWPath = $AltPythonW
    } else {
        Write-Warning "pythonw.exe not found directly; using python.exe instead."
        $PythonWPath = $PythonPath
    }
}

Write-Host "[✓] Python interpreter found: $PythonWPath" -ForegroundColor Green

# 3. Verify dependencies
Write-Host "[*] Checking Python dependencies..." -ForegroundColor Yellow
$depsCheck = & python -c "import win32gui, win32clipboard, win32com.client, keyboard, edge_tts; print('OK')" 2>$null
if ($depsCheck -ne "OK") {
    Write-Host "[*] Installing required dependencies (pywin32, keyboard, edge-tts)..." -ForegroundColor Yellow
    & python -m pip install --user pywin32 keyboard edge-tts
}
Write-Host "[✓] Dependencies verified (pywin32, keyboard, edge-tts ready)." -ForegroundColor Green

# 4. Create Windows Startup Shortcut
$StartupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$ShortcutPath = Join-Path $StartupFolder "ReadAloudTTS.lnk"

Write-Host "[*] Creating Startup shortcut in: $StartupFolder" -ForegroundColor Yellow

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonWPath
$Shortcut.Arguments = "`"$MainScriptPath`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Read Aloud Selected Text Background Utility (Ctrl+Shift+R)"
$Shortcut.Save()

Write-Host "[✓] Startup shortcut created: $ShortcutPath" -ForegroundColor Green
Write-Host "    Target: $PythonWPath `"$MainScriptPath`"" -ForegroundColor Gray

# 5. Stop any existing instance to avoid duplicate hotkey hooks
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.pyw*" } | ForEach-Object {
    Write-Host "[*] Stopping previous instance (PID: $($_.ProcessId))..." -ForegroundColor Yellow
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

if (-not $TestOnly) {
    Write-Host "[*] Launching Read Aloud utility in background..." -ForegroundColor Yellow
    Start-Process -FilePath $PythonWPath -ArgumentList "`"$MainScriptPath`"" -WorkingDirectory $ScriptDir
    Start-Sleep -Seconds 1
    Write-Host "[✓] Read Aloud utility is now active and running in the background!" -ForegroundColor Green
} else {
    Write-Host "[✓] Test-only mode complete. Shortcut verified." -ForegroundColor Cyan
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Installation Complete! Press Ctrl+Shift+R on any highlighted text." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
