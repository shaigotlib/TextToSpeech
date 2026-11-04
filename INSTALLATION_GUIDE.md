# Read Aloud Desktop Utility - Installation & User Guide

A lightweight background Windows utility that reads aloud any selected text across your applications whenever you press **`Ctrl+R`**.

---

## 🚀 Key Features

- **Global Hotkey:** Press `Ctrl+R` from anywhere to read selected text aloud.
- **Universal Application Support:**
  - **PowerShell / Windows Terminal / CMD**
  - **Notepad & Notepad++**
  - **Microsoft Outlook** (both Classic and New Outlook emails)
  - **Web Browsers:** Google Chrome, Microsoft Edge
  - **Microsoft Office:** Word, Excel, PowerPoint
  - **Collaboration:** Microsoft Teams, Slack
  - Any standard Windows window or text field.
- **Toggle to Stop:** Pressing `Ctrl+R` again while speech is playing immediately cancels and stops speech.
- **Clipboard Safe:** Captures highlighted text without overwriting or losing your previous clipboard contents.
- **100% Local & Offline:** Uses built-in Windows speech synthesis (SAPI5) — no cloud keys, no fees, no internet needed.
- **Zero-Distraction Background Execution:** Runs silently via `pythonw.exe` without an open terminal window.
- **Automatic Startup:** Starts automatically every time your laptop restarts or you log in.

---

## 🛠️ Quick Installation (1-Click)

1. Open **PowerShell** in this project directory:
   ```powershell
   cd "C:\Users\shai.gotlib\AI Prompts Projects\TextToSpeach"
   ```

2. Run the automated installer:
   ```powershell
   .\install.ps1
   ```

The script will:
- Check your Python environment and verify required libraries (`pywin32`).
- Create an auto-start shortcut in your Windows Startup folder (`shell:startup`).
- Launch the utility in the background immediately.

---

## 🔄 How Automatic Launch on Laptop Restart Works

When you run `.\install.ps1`, a shortcut named `ReadAloudTTS.lnk` is automatically placed into your Windows User Startup folder:
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ReadAloudTTS.lnk
```

Every time you log into Windows or reboot your laptop, Windows executes this shortcut automatically. It runs `pythonw.exe main.pyw` silently, which leaves no command prompt window on your screen.

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
2. **Press `Ctrl + R`**: The computer reads the selected text aloud immediately.
3. **Stop Speech**: If you want to interrupt or stop speech before it finishes, press **`Ctrl + R`** again.

---

## ⚙️ System Tray Controls

Look at your Windows taskbar system tray (bottom-right corner, near the clock):
- You will see the **Read Aloud** tray icon.
- **Right-click** the icon to open the menu:
  - **Test Speech**: Plays a quick test greeting.
  - **Speech Speed**: Switch between Slower (-3), Normal (0), and Faster (+3).
  - **Exit**: Cleanly shuts down the utility.

---

## 🗑️ How to Uninstall

To remove the utility from auto-startup and stop any running instances:
```powershell
.\uninstall.ps1
```
