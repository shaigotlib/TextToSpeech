<#
.SYNOPSIS
    Uninstalls the Read Aloud utility and removes its Windows Startup shortcut.
#>

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Yellow
Write-Host " Read Aloud Utility - Uninstallation     " -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

# 1. Stop any running instances
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.pyw*" } | ForEach-Object {
    Write-Host "[*] Terminating process (PID: $($_.ProcessId))..." -ForegroundColor Yellow
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# 2. Remove Startup Shortcut & Registry Run entry
$StartupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$ShortcutPath = Join-Path $StartupFolder "ReadAloudTTS.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item -Path $ShortcutPath -Force
    Write-Host "[✓] Removed Windows Startup shortcut from: $ShortcutPath" -ForegroundColor Green
} else {
    Write-Host "[*] Startup shortcut was not present." -ForegroundColor Gray
}

try {
    $RunKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    if (Get-ItemProperty -Path $RunKeyPath -Name "ReadAloudTTS" -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $RunKeyPath -Name "ReadAloudTTS" -Force -ErrorAction SilentlyContinue
        Write-Host "[✓] Removed autostart entry from HKCU Run key." -ForegroundColor Green
    }
} catch {
    Write-Warning "Could not remove HKCU Run key: $_"
}

Write-Host "=========================================" -ForegroundColor Yellow
Write-Host "Uninstallation Complete." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Yellow
