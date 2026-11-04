# Read-Aloud Desktop Utility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight, background Windows desktop utility that reads aloud any selected text in PowerShell, Notepad, Notepad++, Outlook, Chrome, Edge, Word, Excel, Teams, Slack, and any Windows app upon pressing `Ctrl+R`, running automatically at Windows startup.

**Architecture:** A Python 3 background service executing without a console window via `pythonw.exe`. It registers a global hotkey (`Ctrl+R`) using the Win32 `RegisterHotKey` API, captures highlighted text safely via simulated copy with clipboard state preservation, renders speech locally and asynchronously via Windows SAPI5 (`SpVoice`), provides a system tray interface, and auto-starts on login via a Windows Startup shortcut.

**Tech Stack:** Python 3.10+, `pywin32` (SAPI5 COM, Win32 GUI/Messages), `ctypes` (Win32 user32 `RegisterHotKey`, `SendInput`), `pystray` / native win32 tray icon, Windows Startup shortcut.

**Spec:** `docs/superpowers/specs/2026-11-04-read-aloud-utility-design.md`

## Global Constraints
- Target platform: Windows 11 Enterprise (64-bit), Python 3.10+.
- Zero cloud dependencies: must operate 100% offline using native Windows TTS.
- Clipboard preservation: the user's pre-existing clipboard must be restored after text capture.
- Background execution: no terminal/command prompt window visible during normal operation.
- Non-blocking audio: speech must be asynchronous so subsequent hotkeys can pause, stop, or read new text instantly.

## Review Focus
1. **Empty Selection:** Pressing `Ctrl+R` when no text is selected should not trigger speech or wipe clipboard.
2. **Clipboard Content Restoration:** Existing clipboard content (including multiline or formatting) should remain unchanged after speaking.
3. **Rapid Keypress / Cancellation:** Pressing `Ctrl+R` while audio is actively playing should immediately stop speech (toggle behavior).
4. **Elevated Windows / Console Windows:** PowerShell / Windows Terminal must release selection properly on simulated `Ctrl+C`.
5. **Clean Shutdown:** Exiting from tray or script must cleanly unregister hotkeys and release COM resources.

---

### Task 1: Speech Engine Wrapper (`src/speech_engine.py`)

**Files:**
- Create: `src/speech_engine.py`
- Test: `tests/test_speech_engine.py`

**Interfaces:**
- Produces:
  - `class SpeechEngine`:
    - `speak(text: str, async_mode: bool = True) -> bool`
    - `stop() -> None`
    - `is_speaking() -> bool`
    - `set_rate(rate: int) -> None`  # -10 to 10
    - `set_volume(volume: int) -> None`  # 0 to 100
    - `get_voices() -> list[str]`
    - `set_voice_by_name(name: str) -> bool`

- [ ] **Step 1: Write unit tests for `SpeechEngine`**
Create `tests/test_speech_engine.py` verifying initialization, voice enumeration, volume/rate bounds, `speak`, `stop`, and `is_speaking` status using SAPI5.

- [ ] **Step 2: Run tests to verify failure**
Run: `python -m unittest tests/test_speech_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.speech_engine'`

- [ ] **Step 3: Implement `SpeechEngine` in `src/speech_engine.py`**
Implement SAPI5 `SpVoice` wrapper with asynchronous flags (`SVSFlagsAsync = 1`, `SVSFPurgeBeforeSpeak = 2`).

- [ ] **Step 4: Run tests to verify pass**
Run: `python -m unittest tests/test_speech_engine.py -v`
Expected: PASS

- [ ] **Step 5: Verify speech output on system**
Execute a 1-second quick audible utterance to verify sound generation.

---

### Task 2: Selected Text Capturer & Clipboard Restorer (`src/text_capturer.py`)

**Files:**
- Create: `src/text_capturer.py`
- Test: `tests/test_text_capturer.py`

**Interfaces:**
- Produces:
  - `class TextCapturer`:
    - `get_selected_text(timeout_ms: int = 300) -> str`
    - `backup_clipboard() -> dict`
    - `restore_clipboard(backup: dict) -> bool`
    - `simulate_copy() -> None`

- [ ] **Step 1: Write unit tests for clipboard backup and restore**
Create `tests/test_text_capturer.py` testing:
1. `backup_clipboard` and `restore_clipboard` accurately preserves clipboard text.
2. Simulated copy handling and timeout safety when no text is selected.

- [ ] **Step 2: Run tests to verify failure**
Run: `python -m unittest tests/test_text_capturer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.text_capturer'`

- [ ] **Step 3: Implement `TextCapturer` using Win32 API and SendInput**
Use Win32 `SendInput` (`KEYEVENTF_KEYUP`, `VK_CONTROL`, `VK_C`) with retry-friendly clipboard access (`OpenClipboard`, `GetClipboardData`, `CloseClipboard`) to safely capture text and restore the original clipboard contents immediately.

- [ ] **Step 4: Run tests to verify pass**
Run: `python -m unittest tests/test_text_capturer.py -v`
Expected: PASS

---

### Task 3: Global Hotkey Listener (`src/hotkey_manager.py`)

**Files:**
- Create: `src/hotkey_manager.py`
- Test: `tests/test_hotkey_manager.py`

**Interfaces:**
- Consumes:
  - `ctypes.windll.user32.RegisterHotKey`
  - `ctypes.windll.user32.UnregisterHotKey`
  - `ctypes.windll.user32.GetMessageW`
- Produces:
  - `class HotkeyManager`:
    - `register_hotkey(hotkey_id: int, modifiers: int, vk_code: int, callback: Callable) -> bool`
    - `unregister_all() -> None`
    - `start() -> None` (starts message pump thread)
    - `stop() -> None`

- [ ] **Step 1: Write tests for `HotkeyManager` registration and key-code resolution**
Test modifier combinations (`MOD_CONTROL`, `ord('R')`), callback registration, and clean unregistration.

- [ ] **Step 2: Run test to verify failure**
Run: `python -m unittest tests/test_hotkey_manager.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.hotkey_manager'`

- [ ] **Step 3: Implement `HotkeyManager` with dedicated Win32 message pump**
Implement Win32 `RegisterHotKey` pump running in a daemon thread, posting hotkey events to registered callbacks safely.

- [ ] **Step 4: Run tests to verify pass**
Run: `python -m unittest tests/test_hotkey_manager.py -v`
Expected: PASS

---

### Task 4: Core Service Coordinator (`src/read_aloud_service.py` & `main.pyw`)

**Files:**
- Create: `src/read_aloud_service.py`
- Create: `main.pyw`
- Test: `tests/test_service_integration.py`

**Interfaces:**
- Consumes:
  - `SpeechEngine`
  - `TextCapturer`
  - `HotkeyManager`
- Produces:
  - `class ReadAloudService`:
    - `on_hotkey_pressed() -> None`
    - `stop_speech() -> None`
    - `start() -> None`
    - `stop() -> None`
    - `is_active: bool`

- [ ] **Step 1: Write integration tests for service coordination**
Test hotkey trigger flow:
- When speech is idle and text is captured: triggers `speak(text)`.
- When speech is currently speaking: cancels speech immediately.
- When no text is selected: safely ignores without error.

- [ ] **Step 2: Run test to verify failure**
Run: `python -m unittest tests/test_service_integration.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `ReadAloudService` and `main.pyw`**
Implement the coordination logic, including system tray icon (via `pystray` or lightweight native Win32 `Shell_NotifyIcon`) showing "Read Aloud (Active)" with options to Mute, Adjust Speed, Stop, and Exit.

- [ ] **Step 4: Run integration tests to verify pass**
Run: `python -m unittest tests/test_service_integration.py -v`
Expected: PASS

---

### Task 5: Installation, Startup Autostart & Verification Scripts

**Files:**
- Create: `install.ps1` (registers Windows Startup shortcut for automatic boot execution)
- Create: `uninstall.ps1` (removes startup shortcut and cleans up)
- Create: `run_background.vbs` or `start.bat` (one-click manual background launcher)
- Create: `INSTALLATION_GUIDE.md` (clear step-by-step documentation with screenshots/descriptions)

- [ ] **Step 1: Implement `install.ps1`**
Script that:
1. Validates Python environment and dependencies (`pywin32`, `pystray`, `pillow`).
2. Creates a Windows Startup shortcut (`$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\ReadAloudTTS.lnk`) pointing to `pythonw.exe main.pyw`.
3. Optionally starts the background service immediately.

- [ ] **Step 2: Implement `uninstall.ps1`**
Script that terminates any running `main.pyw` instance and removes the Startup shortcut.

- [ ] **Step 3: Test installation and startup shortcut creation**
Run: `powershell -ExecutionPolicy Bypass -File install.ps1 -TestOnly`
Verify that the shortcut target correctly points to `pythonw.exe` and `main.pyw`.

- [ ] **Step 4: Write `INSTALLATION_GUIDE.md`**
Detailed explanation of:
- How to install in 1 click.
- How automatic startup on computer restart works.
- How to use `Ctrl+R` in PowerShell, Notepad, Notepad++, Outlook, Chrome, Edge, Teams, Slack, Word, etc.
- How to stop speech, adjust speed, and exit via the tray.

---

### Task 6: End-to-End Testing & Verification Across Target Apps

- [ ] **Step 1: Run comprehensive automated test suite**
Run: `python -m unittest discover -s tests -v`
Ensure all unit and integration tests pass.

- [ ] **Step 2: Manual interactive verification**
Verify reading aloud with `Ctrl+R` across:
1. PowerShell console / Windows Terminal
2. Notepad
3. Web page / documents / Office apps
Verify speech cancellation on second press, tray icon behavior, and startup shortcut registration.
