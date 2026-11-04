import time
import ctypes
from typing import Dict, Any, Optional
import win32clipboard
import win32con

# Win32 SendInput constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_C = 0x43


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


class TextCapturer:
    """Safely captures highlighted text from any Windows application via simulated Ctrl+C
    while preserving and restoring the user's prior clipboard content.
    """

    def __init__(self):
        self._user32 = ctypes.windll.user32

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

    def simulate_copy(self) -> None:
        """Simulate physical Ctrl+C key sequence using SendInput API."""
        extra = ctypes.c_ulong(0)
        p_extra = ctypes.pointer(extra)

        # 4 events: Ctrl down, C down, C up, Ctrl up
        inputs = (INPUT * 4)(
            INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=0, time=0, dwExtraInfo=p_extra))),
            INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(wVk=VK_C, wScan=0, dwFlags=0, time=0, dwExtraInfo=p_extra))),
            INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(wVk=VK_C, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=p_extra))),
            INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(wVk=VK_CONTROL, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=p_extra))),
        )
        self._user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))

    def clean_text(self, text: Optional[str]) -> str:
        """Strip trailing and leading whitespace, normalizing string."""
        if not text:
            return ""
        return text.strip()

    def get_selected_text(self, timeout_ms: int = 350) -> str:
        """Capture highlighted text across the active application window:
        1. Backs up current clipboard.
        2. Clears clipboard so we can detect newly copied content.
        3. Simulates Ctrl+C.
        4. Polls clipboard for copied text within timeout_ms.
        5. Restores original clipboard.
        6. Returns cleaned text.
        """
        backup = self.backup_clipboard()

        # Clear clipboard temporarily to detect if new selection was copied
        self.set_clipboard_text("")

        # Small delay to ensure any key modifiers settle, then simulate copy
        time.sleep(0.04)
        self.simulate_copy()

        # Poll for new content arriving in clipboard
        start = time.time()
        timeout_sec = timeout_ms / 1000.0
        selected = ""

        while (time.time() - start) < timeout_sec:
            time.sleep(0.02)
            copied = self.get_clipboard_text()
            if copied and copied.strip():
                selected = copied
                break

        # Always restore the original clipboard
        self.restore_clipboard(backup)
        return self.clean_text(selected)
