# Read Aloud Desktop Utility - Installation & User Guide

A lightweight background Windows utility that reads aloud any selected text across your applications whenever you press **`Ctrl + Alt + R`**.

---

## 🚀 Key Features

- **Global Shortcuts (Consistent `Ctrl + Alt` Family):**
  - **`Ctrl + Alt + R`**: Read selected text aloud / Stop speech.
  - **`Ctrl + Alt + Space`**: Pause / Resume ongoing speech.
  - **`Ctrl + Alt + Up`**: Increase speech speed (+1).
  - **`Ctrl + Alt + Down`**: Decrease speech speed (-1).
  - **`Ctrl + Alt + Right`**: Skip one word forward (active while reading; accumulates multi-clicks).
  - **`Ctrl + Alt + Left`**: Move back one word and re-read it (active while reading; accumulates multi-clicks).
  - **`Ctrl + Alt + \`**: **Toggle Shortcut Passthrough Mode** — When toggled, all tool shortcuts (such as `Ctrl+Alt+R`, `Ctrl+Alt+Space`, etc.) are released and passed directly to your focused application so they can be handled by it. Pressing `Ctrl + Alt + \` again restores capturing so `Ctrl+Alt+R` reads text aloud again.
  - **Zero App Interference:** Arrow navigation shortcuts (`Ctrl+Alt+Left/Right`) are dynamically hooked **only while reading text** and automatically released back to VS Code and other applications when reading is not active, or via "Release Navigation Keys" in the tray menu.
- **Laptop Lid / Sleep & Wake Robustness:** Uses the native Windows kernel `RegisterHotKey` subsystem together with automatic `WM_POWERBROADCAST` (sleep/wake/resume) and `WM_WTSSESSION_CHANGE` (screen lock/unlock/logon) listeners. Closing your laptop lid, sleeping, or locking will never break the hotkeys — they are verified and re-registered upon opening and unlocking.
- **Bilingual Hebrew & English Support:** Automatically detects the language of the selected text:
  - **Hebrew text:** Reads with natural Hebrew neural voice (`Hila`).
  - **English text:** Reads with fast Windows voice (`David`).
- **Universal Application Support:**
  - **PowerShell / Windows Terminal / CMD**
  - **Notepad & Notepad++**
  - **Microsoft Outlook** (both Classic and New Outlook emails)
  - **Web Browsers:** Google Chrome, Microsoft Edge
  - **Microsoft Office:** Word, Excel, PowerPoint
  - **Collaboration:** Microsoft Teams, Slack
  - Any standard Windows window or text field.
- **Toggle to Stop:** Pressing **`Ctrl + Alt + R`** again while speech is playing immediately cancels and stops speech.
- **Audible Feedback:**
  - If you press read without any text selected, a subtle chime sounds.
  - Pressing Speed Up/Down gives an immediate confirmation click/tone.
- **Clipboard Safe:** Captures highlighted text without overwriting or losing your previous clipboard contents.
- **100% Local & Offline:** Uses built-in Windows speech synthesis (SAPI5) — no cloud keys, no fees, no internet needed.
- **Zero-Distraction Background Execution:** Runs silently via `pythonw.exe` without an open terminal window.
- **Automatic Startup:** Starts automatically every time your laptop restarts or you log in.

---

## 🛠️ Quick Installation (1-Click)

### Option A: Double-Click (Easiest)
Simply double-click **`install.bat`** in this folder. It automatically bypasses PowerShell execution policies and configures everything.

### Option B: PowerShell
1. Open **PowerShell** in this project directory:
   ```powershell
   cd "C:\Users\shai.gotlib\AI Prompts Projects\TextToSpeach"
   ```

2. Run the automated installer:
   ```powershell
   .\install.ps1
   ```
   *(If prompted about script execution, run: `powershell -ExecutionPolicy Bypass -File .\install.ps1`)*

The script will:
- **Empty Computer Support (Zero-Dependency Initial Setup)**: If Python is not installed at all, the installer detects this, clearly explains that Python 3.10+ is required, and asks your permission: `"Would you like to install Python 3.10 now? [Y/n]"`. Upon approval, it installs Python automatically via `winget` or downloads the official installer directly from python.org. If declined, it exits cleanly without making any system changes.
- **Older Python Detection & Upgrade Prompt**: If an older Python version (such as Python 3.8 or 3.9) is installed, the installer detects that it is below the minimum required version (3.10), explains why (for async neural speech and typing support), and asks your permission: `"Would you like to install/upgrade to Python 3.10+ alongside your existing Python? [Y/n]"`. It will never upgrade or replace your Python environment without explicit user approval.
- **Dependency Verification & Permission**: Checks for required Python packages (`pywin32`, `edge-tts`). If any are missing, it asks permission before installing them via pip.
- **Windows Speech Engine Check**: Verifies that Windows Speech Synthesis (SAPI5) voices are available.
- **Dual-Layer Auto-Start**: Configures auto-start via both the Windows Startup folder (`shell:startup`) and User Registry Run key (`HKCU\...\Run`).
- **Running Instance Management**: Terminates any previous instances cleanly before starting the updated service.
- **Optional Updates**: Supports `.\install.ps1 -UpdateDependencies` to check and prompt for updating existing packages.

---

## 🏃 Manual Launch & Management Scripts

- **Start Utility (One-Click Launch)**:
  - Double-click **`start.bat`** (or run `pythonw main.pyw` in PowerShell).
  - Starts the background service immediately without an open console window.
- **Stop Specific Running Instance (Without Uninstalling)**:
  - Double-click **`stop.bat`** (or run `.\stop.ps1` in PowerShell).
  - Stops any currently active Read Aloud processes immediately.
  - Leaves auto-start and shortcuts intact so it still runs automatically after reboot.
- **Uninstall / Clean Removal (Stop & Remove from Startup)**:
  - Double-click **`uninstall.bat`** (or run `.\uninstall.ps1` in PowerShell).
  - Terminates all running instances, removes the Startup folder shortcut (`ReadAloudTTS.lnk`), and deletes the `HKCU\...\Run` registry key so it will no longer launch automatically on reboot.

---

## 🔄 How Automatic Launch on Laptop Restart Works

When you install, the utility configures dual-layer startup protection:
1. **Startup Folder Shortcut**: `ReadAloudTTS.lnk` in:
   ```
   %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ReadAloudTTS.lnk
   ```
2. **Registry Autostart Key**:
   ```
   HKCU\Software\Microsoft\Windows\CurrentVersion\Run -> ReadAloudTTS
   ```

Every time you log into Windows or reboot your laptop, Windows automatically starts the utility silently using `pythonw.exe` without popping up any black console windows. A single-instance mutex prevents duplicate background instances from running simultaneously.

To verify or view your Startup folder at any time:
1. Press `Win + R` on your keyboard.
2. Type `shell:startup` and press Enter.
3. You will see `ReadAloudTTS.lnk` present and enabled.

---

## 🎧 How to Use

1. **Highlight / Select Text** in any application:
   - In **PowerShell / Terminal**: Select text with your mouse.
   - In **Outlook**: Highlight text in any received email or draft.
   - In **Notepad / Notepad++**: Select lines or words.
   - In **Chrome / Edge / Teams / Slack**: Highlight any chat message or webpage text.
2. **Press `Ctrl + Alt + R`**: The computer reads the selected text aloud immediately.
3. **Pause / Resume**: Press **`Ctrl + Alt + Space`** to pause speech at any moment, and press it again to resume right where it left off.
4. **Adjust Speed**:
   - Press **`Ctrl + Alt + Up`** to speed up speech on the fly.
   - Press **`Ctrl + Alt + Down`** to slow down speech on the fly.
5. **Navigate Words (Forward & Backward)**:
   - Press **`Ctrl + Alt + Right`** to skip one word forward.
   - Press **`Ctrl + Alt + Left`** to move back one word and re-read it.
   - **Sequence of Clicks**: Rapid successive clicks accumulate automatically (e.g. 3 rapid clicks = jump 3 words forward or backward) without stuttering or restarting audio repeatedly.
   - **Persistent Re-reading**: Even after speech completes or is stopped, you can press **`Ctrl + Alt + Left`** to move back word-by-word into the previously read text up until a new text selection is captured.
   - **Bilingual Parity**: Word navigation works identically in Hebrew and English.
6. **Stop Speech**: If you want to interrupt or stop speech completely, press **`Ctrl + Alt + R`** again.
7. **Toggle Passthrough to Focused Application (`Ctrl + Alt + \`)**:
   - If your active application (IDE, terminal, text editor) uses `Ctrl + Alt + R` or any other tool shortcut, press **`Ctrl + Alt + \`**.
   - A descending dual-tone chime confirms that **Passthrough Mode is ON**. All shortcuts (except `Ctrl + Alt + \`) are released immediately and handled directly by your focused application.
   - Press **`Ctrl + Alt + \`** again whenever you want to return to text-to-speech reading mode. An ascending dual-tone chime confirms that capturing is active again.

---

## ⚙️ System Tray Controls

Look at your Windows taskbar system tray (bottom-right corner, near the clock):
- You will see the **Read Aloud** tray icon.
- **Right-click** the icon to open the menu:
  - **Disable / Enable Hotkeys (Passthrough Mode)**: Toggle between passing hotkeys to applications vs reading aloud (equivalent to `Ctrl + Alt + \`).
  - **Test Speech**: Plays a quick test greeting.
  - **Speech Speed**: Switch between Slower (-3), Normal (0), and Faster (+3).
  - **Release Navigation Keys**: Instantly unhooks the arrow keys and clears reading state, giving full control back to VS Code.
  - **Exit**: Cleanly shuts down the utility.

---

## 🗑️ How to Uninstall

To remove the utility from auto-startup and stop any running instances:
```powershell
.\uninstall.ps1
```
