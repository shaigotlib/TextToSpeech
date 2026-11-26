import unittest
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SCRIPT = os.path.join(BASE_DIR, "install.ps1")

class TestInstaller(unittest.TestCase):
    def test_installer_script_exists(self):
        self.assertTrue(os.path.exists(INSTALL_SCRIPT))

    def test_installer_syntax_valid(self):
        # Validate PowerShell script syntax
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"& {{ $errs = @(); [System.Management.Automation.Language.Parser]::ParseFile('{INSTALL_SCRIPT}', [ref]$null, [ref]$errs) | Out-Null; if ($errs.Count -gt 0) {{ $errs | ForEach-Object {{ Write-Error $_ }}; exit 1 }} else {{ Write-Output 'OK' }} }}"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"PowerShell syntax error: {proc.stderr}")
        self.assertIn("OK", proc.stdout)

    def test_installer_test_only_mode(self):
        # Run install.ps1 with -TestOnly and -NonInteractive
        cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", INSTALL_SCRIPT,
            "-TestOnly",
            "-NonInteractive"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Install test-only failed: {proc.stderr}\nOutput: {proc.stdout}")
        self.assertIn("Python interpreter found", proc.stdout)
        self.assertIn("Dependencies verified", proc.stdout)
        self.assertIn("Startup shortcut created", proc.stdout)

    def test_installer_declines_upgrade_when_user_refuses(self):
        # When simulate declining python upgrade, script respects user permission
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"& '{INSTALL_SCRIPT}' -TestOnly -SimulateOldPython -DeclineAll"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        # Should not proceed or upgrade without permission
        self.assertIn("Upgrade declined by user", proc.stdout + proc.stderr)

    def test_installer_detects_and_prompts_for_old_python(self):
        # Test that old Python is detected and user is prompted
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"& '{INSTALL_SCRIPT}' -TestOnly -SimulateOldPython -NonInteractive -SkipActualWebInstall"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn("below minimum required version", proc.stdout)

    def test_installer_detects_missing_python_and_prompts_permission(self):
        # Test that on an empty machine (no Python), install prompts for permission
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"& '{INSTALL_SCRIPT}' -TestOnly -SimulateNoPython -DeclineAll"
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertIn("Python installation was declined by user", proc.stdout + proc.stderr)

if __name__ == '__main__':
    unittest.main()
