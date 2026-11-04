import time
import ctypes
from typing import Dict, Any, Optional, Tuple
import win32clipboard
import win32con
import win32gui
import keyboard

# Unique sentinel string used to detect fresh clipboard copy events
CLIPBOARD_SENTINEL = "__READ_ALOUD_CLIPBOARD_SENTINEL_TOKEN_V1__"

# Known console and terminal window class names
TERMINAL_WINDOW_CLASSES = {
    "cascadia_hosting_window_class",  # Windows Terminal
    "consolewindowclass",             # Legacy cmd / powershell console
    "pseudoconsolewindow",            # ConPTY pseudoconsole
}


class TextCapturer:
    """Safely captures highlighted text across standard GUI apps and terminal windows
    while preserving and restoring the user's prior clipboard content.
    """

    def __init__(self):
        self._user32 = ctypes.windll.user32

    def is_terminal_class(self, class_name: str) -> bool:
        """Check if window class belongs to a Windows Terminal or Console host."""
        if not class_name:
            return False
        return class_name.lower().strip() in TERMINAL_WINDOW_CLASSES

    def get_foreground_window_info(self) -> Tuple[int, str, str]:
        """Return (hwnd, class_name, title) of currently focused foreground window."""
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return 0, "", ""
        try:
            class_name = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
            return hwnd, class_name, title
        except Exception:
            return hwnd, "", ""

    def get_clipboard_text(self, retries: int = 5, delay: float = 0.02) -> Optional[str]:
        """Read current unicode text from the Windows clipboard safely."""
        for _ in range(retries):
            try:
                win32clipboard.OpenClipboard()
                try:
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                        return data
                    return None
                finally:
                    win32clipboard.CloseClipboard()
            except Exception:
                time.sleep(delay)
        return None

    def set_clipboard_text(self, text: Optional[str], retries: int = 5, delay: float = 0.02) -> bool:
        """Set unicode text into the Windows clipboard safely."""
        for _ in range(retries):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    if text is not None:
                        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            except Exception:
                time.sleep(delay)
        return False

    def backup_clipboard(self) -> Dict[str, Any]:
        """Save current text clipboard content."""
        return {"text": self.get_clipboard_text()}

    def restore_clipboard(self, backup: Dict[str, Any]) -> bool:
        """Restore previously saved clipboard text content."""
        saved_text = backup.get("text")
        return self.set_clipboard_text(saved_text)

    def clean_text(self, text: Optional[str]) -> str:
        """Strip trailing and leading whitespace, normalizing string."""
        if not text:
            return ""
        return text.strip()

    def simulate_copy(self, is_terminal: bool = False) -> None:
        """Release physically held hotkeys and trigger application copy sequence."""
        try:
            # First release any keys that might be held physically by the user
            keyboard.release("r")
            time.sleep(0.01)
            keyboard.release("ctrl")
            time.sleep(0.02)

            if is_terminal:
                # In Windows Terminal, Ctrl+Shift+C and Ctrl+C copy highlighted text
                keyboard.send("ctrl+shift+c")
                time.sleep(0.03)
                keyboard.send("ctrl+c")
            else:
                # Standard Windows copy shortcut across Notepad, Chrome, Word, Outlook, etc.
                keyboard.send("ctrl+c")
        except Exception:
            pass

    def get_selected_text(self, timeout_ms: int = 400) -> str:
        """Capture highlighted text across the active application window:
        1. Backs up current clipboard.
        2. Detects active window type (Terminal vs GUI app).
        3. Sets a sentinel marker in the clipboard.
        4. Triggers copy sequence.
        5. Polls clipboard for newly copied content.
        6. Restores original clipboard.
        7. Returns the captured text.
        """
        backup = self.backup_clipboard()
        hwnd, class_name, _ = self.get_foreground_window_info()
        is_terminal = self.is_terminal_class(class_name)

        # Set sentinel marker so we can distinguish freshly copied text from pre-existing
        self.set_clipboard_text(CLIPBOARD_SENTINEL)
        time.sleep(0.02)

        # Trigger application copy
        self.simulate_copy(is_terminal=is_terminal)

        # Poll for new content arriving in clipboard
        start = time.time()
        timeout_sec = timeout_ms / 1000.0
        selected = ""

        while (time.time() - start) < timeout_sec:
            time.sleep(0.03)
            copied = self.get_clipboard_text()
            if copied and copied != CLIPBOARD_SENTINEL:
                selected = copied
                break

        # Always restore the original clipboard
        self.restore_clipboard(backup)

        # Fallback for Windows Terminal with "Copy on select":
        # If simulated copy yielded nothing (because selection was already copied upon mouse select)
        # and the previous clipboard content had text, use that!
        if not selected and is_terminal and backup.get("text"):
            prev = backup["text"]
            if prev and prev != CLIPBOARD_SENTINEL and prev.strip():
                selected = prev

        return self.clean_text(selected)
