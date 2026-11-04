# Read-Aloud Desktop Utility Design Specification

## Overview & Intent
A lightweight, background Windows utility that reads aloud any currently selected text upon pressing `Ctrl+R`. It functions across all Windows applications (PowerShell, Notepad, Notepad++, Outlook, Chrome, Edge, Word, Excel, PowerPoint, Teams, Slack, etc.) without requiring per-application plugins. It runs silently in the system tray, preserves clipboard contents, starts automatically on Windows logon, and relies on built-in Windows speech synthesis (SAPI5).

## Goals
1. **Global Hotkey:** Trigger speech on `Ctrl+R` from any focused application window.
2. **Universal Compatibility:** Support all desktop applications:
   - PowerShell (Console & Windows Terminal)
   - Notepad and Notepad++
   - Microsoft Outlook (Classic and New Outlook)
   - Web Browsers (Google Chrome, Microsoft Edge)
   - Office Apps (Word, Excel, PowerPoint)
   - Collaboration Tools (Microsoft Teams, Slack)
   - Any other standard Win32 / UWP desktop application
3. **Safe Clipboard Preservation:** Temporarily fetch selected text using simulated copy (`Ctrl+C` or Win32 clipboard), then restore the user's previous clipboard content immediately so normal clipboard history is not corrupted.
4. **Immediate Speech Control:**
   - Pressing `Ctrl+R` when text is selected speaks the text.
   - Pressing `Ctrl+R` (or a dedicated stop key like `Esc` / `Ctrl+Shift+R`) while speech is active stops/cancels ongoing speech immediately.
5. **Autostart on Boot:** Automatically registers in the current user's Windows Startup (`shell:startup` shortcut or `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry entry) to run silently on restart.
6. **Background Execution & Tray Control:** Runs without an open console window (`pythonw.exe`), with a system tray icon for status, mute, speed adjustments, and exit.
7. **Clean Installation & Setup:** Provided with one-click install and uninstall scripts (`install.bat` / `install.ps1`).

## Non-Goals & Anti-Goals
- **Anti-Goal:** Requiring cloud API keys (e.g., Azure Cognitive Services, ElevenLabs, OpenAI). Must work 100% locally and offline via built-in Windows SAPI5 / Windows.Media.SpeechSynthesis.
- **Anti-Goal:** Overriding standard `Ctrl+R` when no text is selected or blocking standard application shortcuts if unhandled.
- **Non-Goal:** Full screen-reader for visually impaired users (like NVDA or JAWS). This is a fast, on-demand read-aloud utility for highlighted text.

## Architecture & Technology Stack
- **Language & Runtime:** Python 3 (installed on machine: Python 3.10 with `pywin32` and `pyperclip` already available). Can run via `pythonw.exe` for zero-console background execution.
- **Speech Engine:** Windows SAPI5 (`win32com.client.Dispatch("SAPI.SpVoice")`) with asynchronous speech flag (`SVSFlagsAsync = 1`) to allow instant stop/resume and non-blocking operation.
- **Hotkey & Input Simulation:** Windows API `RegisterHotKey` (or low-level keyboard hook) via `ctypes.windll.user32` combined with `SendInput` / Win32 key events for reliable `Ctrl+C` emission.
- **Clipboard Management:** Win32 OpenClipboard/GetClipboardData/SetClipboardData with retry logic and full restoration of previous text/format.
- **Startup Integration:** Windows Startup Shortcut in `shell:startup` pointing to `pythonw.exe read_aloud.pyw`.

## Constraints
- Windows 11 Enterprise 64-bit environment.
- Works offline without third-party external service costs or network calls.
- Python 3.10+ already present with `pywin32`.
