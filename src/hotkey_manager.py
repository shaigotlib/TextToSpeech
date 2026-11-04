import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Dict, Any

# Windows Hotkey Modifier Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012


class HotkeyManager:
    """Manages system-wide global hotkeys via Windows RegisterHotKey API
    in a dedicated background message pump thread.
    """

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self._hotkeys: Dict[int, Dict[str, Any]] = {}
        self._thread: threading.Thread = None
        self._thread_id: int = 0
        self._running = False
        self._ready_event = threading.Event()
        self._lock = threading.Lock()

    def add_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, callback: Callable) -> bool:
        """Register a hotkey specification with a callback."""
        with self._lock:
            self._hotkeys[hotkey_id] = {
                "modifiers": modifiers,
                "vk_code": vk_code,
                "callback": callback,
                "registered": False,
            }
            # If thread is already running, register immediately on that thread
            if self._running and self._thread_id:
                # Hotkeys must be registered by the thread that processes the message loop
                pass
            return True

    def remove_hotkey(self, hotkey_id: int) -> None:
        """Remove and unregister a hotkey."""
        with self._lock:
            if hotkey_id in self._hotkeys:
                if self._hotkeys[hotkey_id].get("registered"):
                    self._user32.UnregisterHotKey(None, hotkey_id)
                del self._hotkeys[hotkey_id]

    def _dispatch(self, hotkey_id: int) -> None:
        """Dispatch the callback for the triggered hotkey."""
        callback = None
        with self._lock:
            if hotkey_id in self._hotkeys:
                callback = self._hotkeys[hotkey_id].get("callback")
        if callback:
            try:
                # Run callback in a separate thread so message pump is never delayed or blocked
                threading.Thread(target=callback, daemon=True).start()
            except Exception:
                pass

    def _message_loop(self) -> None:
        """Dedicated Windows message pump thread."""
        self._thread_id = self._kernel32.GetCurrentThreadId()

        # Register all hotkeys on this message-loop thread
        with self._lock:
            for hid, item in self._hotkeys.items():
                # Add MOD_NOREPEAT if supported to prevent auto-repeat spamming
                mods = item["modifiers"] | MOD_NOREPEAT
                success = self._user32.RegisterHotKey(None, hid, mods, item["vk_code"])
                if not success:
                    # Retry without MOD_NOREPEAT in case of legacy compatibility
                    success = self._user32.RegisterHotKey(None, hid, item["modifiers"], item["vk_code"])
                item["registered"] = bool(success)

        self._running = True
        self._ready_event.set()

        msg = wintypes.MSG()
        # GetMessageW blocks until a message arrives
        while self._running:
            b_ret = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if b_ret == 0 or b_ret == -1:  # WM_QUIT or Error
                break
            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                self._dispatch(hotkey_id)
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup hotkeys when exiting message loop
        with self._lock:
            for hid, item in self._hotkeys.items():
                if item.get("registered"):
                    self._user32.UnregisterHotKey(None, hid)
                    item["registered"] = False
        self._running = False

    def start(self) -> None:
        """Start the background hotkey listener thread."""
        if self._running:
            return
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="HotkeyMessageLoop")
        self._thread.start()
        self._ready_event.wait(timeout=2.0)

    def stop(self) -> None:
        """Stop the listener thread and unregister all hotkeys."""
        if not self._running:
            return
        self._running = False
        if self._thread_id:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread_id = 0

    def is_running(self) -> bool:
        return self._running
