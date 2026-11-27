# Where and How to Get and Install Read Aloud Desktop Utility

A lightweight Windows background utility that reads aloud any selected text across your applications whenever you press **`Ctrl + Alt + R`**.

---

## 🔗 Repository Download Link

- **Public GitHub Repository**: [https://github.com/shaigotlib/TextToSpeech](https://github.com/shaigotlib/TextToSpeech)
- **Direct ZIP Download**: [https://github.com/shaigotlib/TextToSpeech/archive/refs/heads/master.zip](https://github.com/shaigotlib/TextToSpeech/archive/refs/heads/master.zip)

---

## ⚡ Super Fast Installation (1-Line PowerShell Command)

Open **PowerShell** (press `Win + X` then choose **Terminal** or **PowerShell**) and paste this single command:

```powershell
git clone https://github.com/shaigotlib/TextToSpeech.git "$HOME\TextToSpeech"; & "$HOME\TextToSpeech\install.bat"
```

The script will automatically:
1. Verify whether Python 3.10+ is installed (and ask your permission to install it if missing).
2. Verify required dependencies (`pywin32`, `edge-tts`) and ask your permission before downloading them.
3. Automatically deploy the tool to standard Windows application directory (`%LOCALAPPDATA%\ReadAloudTTS`).
4. Configure Windows auto-start upon reboot/login (via Startup shortcut and user registry).
5. Launch the tool silently in the background (visible in your system tray).

---

## 🛠️ Step-by-Step Manual Installation

### Option A: Using Git
1. Open PowerShell and clone the project:
   ```powershell
   git clone https://github.com/shaigotlib/TextToSpeech.git
   cd TextToSpeech
   ```
2. Double-click **`install.bat`** (or run `.\install.ps1` in PowerShell).

### Option B: Download ZIP without Git
1. Go to [https://github.com/shaigotlib/TextToSpeech](https://github.com/shaigotlib/TextToSpeech).
2. Click the green **Code** button and select **Download ZIP**.
3. Extract the downloaded ZIP folder to your computer.
4. Open the extracted folder and double-click **`install.bat`**.

---

## 🎧 Shortcuts Cheat Sheet

| Shortcut | Action |
| :--- | :--- |
| **`Ctrl + Alt + R`** | **Read Aloud** selected text / **Stop** ongoing speech |
| **`Ctrl + Alt + Space`** | **Pause / Resume** speech |
| **`Ctrl + Alt + Up`** | **Speed Up** speech rate (+1) |
| **`Ctrl + Alt + Down`** | **Slow Down** speech rate (-1) |
| **`Ctrl + Alt + Right`** | Skip forward one word (active while reading) |
| **`Ctrl + Alt + Left`** | Move back one word and re-read it (active while reading) |
| **`Ctrl + Alt + \`** | **Toggle Passthrough Mode** (passes shortcuts to focused app) |

---

## 🏃 Running and Stopping

- **Launch manually**: Double-click `start.bat` (or run `pythonw main.pyw`).
- **Stop running instance**: Double-click `stop.bat` (leaves auto-start intact for next reboot).
- **Clean uninstall**: Double-click `uninstall.bat` (stops process, removes autostart shortcut, and cleans `%LOCALAPPDATA%\ReadAloudTTS`).

---

## ⚖️ License & Disclaimer

This software is provided **100% free of charge for non-commercial use only**. Charging money, selling, or monetizing this code or derivative works is strictly prohibited. The software is provided **"AS IS" WITHOUT WARRANTY OF ANY KIND**; the author assumes no responsibility or liability for any consequences or results of using this software. See `LICENSE` for details.
