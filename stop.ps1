<#
.SYNOPSIS
    Stops any currently running instances of the Read Aloud utility without uninstalling or removing startup shortcuts.
#>

$ErrorActionPreference = "SilentlyContinue"

Write-Host "=========================================" -ForegroundColor Yellow
Write-Host " Stopping Read Aloud Utility             " -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

$stopped = 0
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*main.pyw*" } | ForEach-Object {
    Write-Host "[*] Stopping Read Aloud process (PID: $($_.ProcessId))..." -ForegroundColor Yellow
    Stop-Process -Id $_.ProcessId -Force
    $stopped++
}

if ($stopped -gt 0) {
    Write-Host "[OK] Read Aloud utility stopped successfully ($($stopped) instances terminated)." -ForegroundColor Green
    Write-Host "     Note: Auto-start and shortcuts remain configured. Run .\start.bat to start again." -ForegroundColor Gray
} else {
    Write-Host "[*] No active Read Aloud instances were currently running." -ForegroundColor Cyan
}

Write-Host "=========================================" -ForegroundColor Yellow
