<#
.SYNOPSIS
    Installs, validates prerequisites, and registers the Read Aloud utility for automatic background startup on Windows.
    Handles brand-new (empty) computers, checks for Python and upgrades older Python versions if needed,
    and asks user permission before installing or upgrading any software or package.
.PARAMETER TestOnly
    Runs validation and shortcut verification without starting the background service.
.PARAMETER NonInteractive
    Runs without interactive user prompts, assuming Yes for required installations.
.PARAMETER DeclineAll
    Simulates user declining all permission prompts (useful for validation tests).
.PARAMETER UpdateDependencies
    Checks for and offers updates to existing Python packages.
.PARAMETER SimulateOldPython
    Test simulation flag to verify detection and permission prompts for older Python versions (<3.10).
.PARAMETER SimulateNoPython
    Test simulation flag to verify detection and installation flow when Python is absent.
.PARAMETER SkipActualWebInstall
    Used in test validation to simulate user approval without actually invoking external web installers.
#>
param(
    [switch]$TestOnly,
    [switch]$NonInteractive,
    [switch]$DeclineAll,
    [switch]$UpdateDependencies,
    [switch]$SimulateOldPython,
    [switch]$SimulateNoPython,
    [switch]$SkipActualWebInstall,
    [switch]$InstallInPlace
)

$ErrorActionPreference = "Stop"

function Ask-UserPermission {
    param(
        [string]$PromptMessage,
        [bool]$DefaultYes = $true
    )

    if ($DeclineAll) {
        Write-Host "$PromptMessage [Declined: DeclineAll flag]" -ForegroundColor DarkGray
        return $false
    }

    if ($NonInteractive) {
        Write-Host "$PromptMessage [Auto-Approved: NonInteractive mode]" -ForegroundColor DarkGray
        return $true
    }

    $defaultChoice = if ($DefaultYes) { "Y/n" } else { "y/N" }
    Write-Host "$PromptMessage [$defaultChoice]: " -NoNewline -ForegroundColor Yellow
    $response = [System.Console]::ReadLine()
    if ([string]::IsNullOrWhiteSpace($response)) {
        return $DefaultYes
    }
    $trimmed = $response.Trim().ToLower()
    return ($trimmed -eq "y" -or $trimmed -eq "yes")
}

function Install-PythonFromWeb {
    if ($SkipActualWebInstall) {
        Write-Host "[OK] Simulated web installer execution (SkipActualWebInstall)." -ForegroundColor Green
        return $true
    }

    Write-Host "[*] Looking for Windows Package Manager (winget)..." -ForegroundColor Cyan
    $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetCmd) {
        Write-Host "[*] Installing Python 3.10 via winget..." -ForegroundColor Yellow
        & winget install Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Python 3.10 installed successfully via winget." -ForegroundColor Green
            return $true
        }
    }

    Write-Host "[*] Downloading official Python 3.10.11 64-bit installer from python.org..." -ForegroundColor Yellow
    $downloadUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
    $installerPath = Join-Path $env:TEMP "python-3.10.11-amd64.exe"

    try {
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
        $webClient = New-Object System.Net.WebClient
        $webClient.DownloadFile($downloadUrl, $installerPath)
        Write-Host "[OK] Downloaded Python installer to $installerPath" -ForegroundColor Green

        Write-Host "[*] Running Python installer with standard options (PrependPath=1, InstallLauncherAllUsers=1)..." -ForegroundColor Yellow
        $proc = Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1" -Wait -PassThru
        if ($proc.ExitCode -eq 0) {
            Write-Host "[OK] Python 3.10 installed successfully from official installer." -ForegroundColor Green
            return $true
        } else {
            Write-Warning "Python installer exited with code $($proc.ExitCode)."
            return $false
        }
    } catch {
        Write-Warning "Direct download failed: $_"
        return $false
    } finally {
        if (Test-Path $installerPath) {
            Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Read Aloud Utility - Installation Setup " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. Resolve Project Root and Main Script
# -----------------------------------------------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MainScriptPath = Join-Path $ScriptDir "main.pyw"

if (-not (Test-Path $MainScriptPath)) {
    Write-Error "Could not find main.pyw at: $MainScriptPath"
    exit 1
}
Write-Host "[OK] Project directory resolved: $ScriptDir" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 2. Check Python 3.10+ Prerequisite & Handle Missing or Older Versions
# -----------------------------------------------------------------------------
Write-Host "`n[*] Checking Python 3.10+ prerequisite..." -ForegroundColor Cyan

$PythonExe = $null

if (-not $SimulateNoPython) {
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pyCmd) {
        $PythonExe = $pyCmd.Source
    }

    if (-not $PythonExe) {
        $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pyLauncher) {
            $detectedPath = & py -3 -c "import sys; print(sys.executable)" 2>$null
            if ($detectedPath -and (Test-Path $detectedPath)) {
                $PythonExe = $detectedPath.Trim()
            }
        }
    }

    if (-not $PythonExe) {
        $CommonPaths = @(
            "C:\Python312\python.exe",
            "C:\Python311\python.exe",
            "C:\Python310\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
        )
        foreach ($cand in $CommonPaths) {
            if (Test-Path $cand) {
                $PythonExe = $cand
                break
            }
        }
    }
}

# If Python is not installed at all (e.g. brand new / empty computer)
if (-not $PythonExe) {
    Write-Warning "Python was NOT found on this computer."
    Write-Host "Python 3.10+ is required for the Read Aloud utility." -ForegroundColor Yellow
    $allowInstallPy = Ask-UserPermission -PromptMessage "Would you like to install Python 3.10 now?" -DefaultYes $true
    if ($allowInstallPy) {
        $installSuccess = Install-PythonFromWeb
        if ($installSuccess) {
            # Refresh PATH
            $sysPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Machine)
            $usrPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
            $env:Path = "$sysPath;$usrPath"
            $pyCmdAfter = Get-Command python -ErrorAction SilentlyContinue
            if ($pyCmdAfter) { $PythonExe = $pyCmdAfter.Source }
        }
    } else {
        Write-Host "Installation cancelled: Python installation was declined by user." -ForegroundColor Yellow
        exit 1
    }

    if (-not $PythonExe) {
        Write-Error "Python 3.10+ is required. Please download and install Python from https://www.python.org/downloads/ and re-run install.bat."
        exit 1
    }
}

# Detect installed Python version
$pyVerOutput = & "$PythonExe" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>$null

if ($SimulateOldPython) {
    $pyVerOutput = "3.8.10"
}

$parsedVer = $null
try {
    $parsedVer = [version]$pyVerOutput
} catch {
    Write-Warning "Could not parse version '$pyVerOutput'."
}

# Handle older installed Python (<3.10)
if ($parsedVer -and ($parsedVer -lt [version]"3.10")) {
    Write-Warning "Detected Python version ($pyVerOutput) is below minimum required version (3.10)."
    Write-Host "This utility requires Python 3.10 or higher for async speech features and typing." -ForegroundColor Yellow

    $allowUpgrade = Ask-UserPermission -PromptMessage "Would you like to install/upgrade to Python 3.10+ alongside your existing Python?" -DefaultYes $true
    if ($allowUpgrade) {
        $installedNewPy = Install-PythonFromWeb
        if ($installedNewPy) {
            $sysPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::Machine)
            $usrPath = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
            $env:Path = "$sysPath;$usrPath"
            $pyCmdAfter = Get-Command python -ErrorAction SilentlyContinue
            if ($pyCmdAfter) { $PythonExe = $pyCmdAfter.Source }
        }
    } else {
        Write-Host "Upgrade declined by user: Python 3.10+ upgrade was not authorized. Cannot proceed with older Python $pyVerOutput." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "[OK] Python interpreter found: $PythonExe (v$pyVerOutput)" -ForegroundColor Green

# Locate pythonw.exe (for quiet background execution without a console window)
$PythonDir = Split-Path -Parent $PythonExe
$PythonWPath = Join-Path $PythonDir "pythonw.exe"

if (-not (Test-Path $PythonWPath)) {
    $altW = Get-Command pythonw -ErrorAction SilentlyContinue
    if ($altW -and (Test-Path $altW.Source)) {
        $PythonWPath = $altW.Source
    } else {
        Write-Warning "pythonw.exe not found; falling back to python.exe."
        $PythonWPath = $PythonExe
    }
}
Write-Host "[OK] Background runner found: $PythonWPath" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 3. Check pip Prerequisite
# -----------------------------------------------------------------------------
Write-Host "`n[*] Checking pip (Python Package Installer)..." -ForegroundColor Cyan
$pipCheck = & "$PythonExe" -m pip --version 2>$null
if (-not $pipCheck) {
    Write-Warning "pip is not installed in Python environment."
    $installPip = Ask-UserPermission -PromptMessage "Would you like to install pip using ensurepip?" -DefaultYes $true
    if ($installPip) {
        Write-Host "[*] Bootstrapping pip..." -ForegroundColor Yellow
        & "$PythonExe" -m ensurepip --default-pip
        & "$PythonExe" -m pip install --upgrade pip
    } else {
        Write-Host "Installation cancelled: pip installation was declined by user." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[OK] pip detected: $pipCheck" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# 4. Check & Install/Upgrade Required Python Libraries
# -----------------------------------------------------------------------------
Write-Host "`n[*] Checking required Python dependencies..." -ForegroundColor Cyan

$RequiredPackages = @(
    @{ Name = "pywin32"; Module = "win32gui"; Description = "Windows API, Clipboard, System Tray and SAPI5 Speech" },
    @{ Name = "edge-tts"; Module = "edge_tts"; Description = "Microsoft Natural Neural Voice for Hebrew and English" }
)

$MissingPackages = @()
$ExistingPackages = @()

foreach ($pkg in $RequiredPackages) {
    $pName = $pkg.Name
    $pDesc = $pkg.Description
    $modName = $pkg.Module
    $isInstalled = & "$PythonExe" -c "import importlib.util; exit(0 if importlib.util.find_spec('$modName') else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Package '$pName' is already installed ($pDesc)." -ForegroundColor Green
        $ExistingPackages += $pName
    } else {
        Write-Host "[!] Package '$pName' is NOT installed ($pDesc)." -ForegroundColor Yellow
        $MissingPackages += $pName
    }
}

# Ask user permission before installing missing packages
if ($MissingPackages.Count -gt 0) {
    $pkgList = $MissingPackages -join ", "
    Write-Host "`nThe following required packages need to be installed: $pkgList" -ForegroundColor Yellow
    $allowInstall = Ask-UserPermission -PromptMessage "Do you authorize downloading and installing these prerequisites via pip?" -DefaultYes $true
    if (-not $allowInstall) {
        Write-Host "Installation cancelled: Package installation was declined by user." -ForegroundColor Yellow
        exit 1
    }

    foreach ($pkgName in $MissingPackages) {
        Write-Host "[*] Installing '$pkgName' via pip..." -ForegroundColor Yellow
        & "$PythonExe" -m pip install --user $pkgName
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install package '$pkgName' via pip. Error code: $LASTEXITCODE"
            exit $LASTEXITCODE
        }
    }
    Write-Host "[OK] All missing packages installed successfully." -ForegroundColor Green
}

# Ask user permission before upgrading existing packages (if -UpdateDependencies or requested)
if ($UpdateDependencies -and ($ExistingPackages.Count -gt 0)) {
    $allowUpdate = Ask-UserPermission -PromptMessage "Would you like to check for and apply updates to existing packages ($($ExistingPackages -join ', '))?" -DefaultYes $false
    if ($allowUpdate) {
        foreach ($pkgName in $ExistingPackages) {
            Write-Host "[*] Updating '$pkgName' to latest version..." -ForegroundColor Yellow
            & "$PythonExe" -m pip install --upgrade --user $pkgName
        }
        Write-Host "[OK] Package updates completed." -ForegroundColor Green
    }
}

# Verify full imports
$fullVerification = & "$PythonExe" -c "import win32gui, win32clipboard, win32com.client, edge_tts; print('ALL_OK')" 2>$null
if ($fullVerification -ne "ALL_OK") {
    Write-Error "Dependency verification failed. Please verify pywin32 and edge-tts are properly installed."
    exit 1
}
Write-Host "[OK] Dependencies verified (all required modules imported cleanly)." -ForegroundColor Green

# -----------------------------------------------------------------------------
# 5. Check Windows Audio / SAPI 5 Voices
# -----------------------------------------------------------------------------
Write-Host "`n[*] Verifying Windows Speech Synthesis Engine (SAPI5)..." -ForegroundColor Cyan
$sapiCount = & "$PythonExe" -c "import win32com.client, pythoncom; pythoncom.CoInitialize(); v = win32com.client.Dispatch('SAPI.SpVoice'); print(v.GetVoices().Count)" 2>$null
if ($sapiCount -and [int]$sapiCount -gt 0) {
    Write-Host "[OK] Windows SAPI 5 speech engine verified ($sapiCount voices available)." -ForegroundColor Green
} else {
    Write-Warning "Could not detect Windows SAPI 5 voices. Speech audio playback may use fallback."
}

# -----------------------------------------------------------------------------
# 6. Deploy to Standard Windows Application Directory & Configure Auto-Start
# -----------------------------------------------------------------------------
Write-Host "`n[*] Configuring Standard Windows Installation Path & Auto-Start..." -ForegroundColor Cyan

# Standard Windows user application path (%LOCALAPPDATA%\ReadAloudTTS)
$StandardAppDir = Join-Path ([System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::LocalApplicationData)) "ReadAloudTTS"

if (-not $InstallInPlace -and ($ScriptDir.TrimEnd('\') -ne $StandardAppDir.TrimEnd('\'))) {
    Write-Host "[*] Deploying tool to standard Windows location: $StandardAppDir" -ForegroundColor Yellow
    if (-not (Test-Path $StandardAppDir)) {
        New-Item -ItemType Directory -Path $StandardAppDir -Force | Out-Null
    }

    # Copy files and src folder to standard destination
    $ItemsToDeploy = @("main.pyw", "stop.ps1", "stop.bat", "start.bat", "uninstall.ps1", "uninstall.bat", "LICENSE", "src")
    foreach ($item in $ItemsToDeploy) {
        $srcPath = Join-Path $ScriptDir $item
        if (Test-Path $srcPath) {
            Copy-Item -Path $srcPath -Destination $StandardAppDir -Recurse -Force
        }
    }

    $TargetWorkingDir = $StandardAppDir
    $TargetScriptPath = Join-Path $StandardAppDir "main.pyw"
    Write-Host "[OK] Deployed to standard application directory: $StandardAppDir" -ForegroundColor Green
} else {
    $TargetWorkingDir = $ScriptDir
    $TargetScriptPath = $MainScriptPath
    Write-Host "[OK] Using installation directory: $TargetWorkingDir" -ForegroundColor Green
}

$StartupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$ShortcutPath = Join-Path $StartupFolder "ReadAloudTTS.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PythonWPath
$Shortcut.Arguments = "`"$TargetScriptPath`""
$Shortcut.WorkingDirectory = $TargetWorkingDir
$Shortcut.Description = 'Read Aloud Selected Text Background Utility (Ctrl+Alt+R, Toggle: Ctrl+Alt+\)'
$Shortcut.Save()

Write-Host "[OK] Startup shortcut created: $ShortcutPath" -ForegroundColor Green
Write-Host "     Target: $PythonWPath `"$TargetScriptPath`"" -ForegroundColor Gray

try {
    $RunKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
    $RunCmd = "`"$PythonWPath`" `"$TargetScriptPath`""
    Set-ItemProperty -Path $RunKeyPath -Name "ReadAloudTTS" -Value $RunCmd -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Registry autostart key configured in HKCU Run." -ForegroundColor Green
} catch {
    Write-Warning "Could not register in HKCU Run key: $_"
}

# -----------------------------------------------------------------------------
# 7. Stop Previous Instance & Launch Background Service
# -----------------------------------------------------------------------------
Write-Host "`n[*] Managing running instances..." -ForegroundColor Cyan

$stopScript = Join-Path $TargetWorkingDir "stop.ps1"
if (Test-Path $stopScript) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
} elseif (Test-Path (Join-Path $ScriptDir "stop.ps1")) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "stop.ps1")
}

if (-not $TestOnly) {
    Write-Host "[*] Launching Read Aloud utility in background..." -ForegroundColor Yellow
    Start-Process -FilePath $PythonWPath -ArgumentList "`"$TargetScriptPath`"" -WorkingDirectory $TargetWorkingDir
    Start-Sleep -Seconds 1
    Write-Host "[OK] Read Aloud utility is now active and running in the background!" -ForegroundColor Green
} else {
    Write-Host "[OK] Test-only mode complete. Shortcut and prerequisites verified." -ForegroundColor Cyan
}

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "Installation Complete! Press Ctrl+Alt+R on highlighted text." -ForegroundColor Green
Write-Host "Press Ctrl+Alt+\ to toggle shortcut passthrough mode." -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
