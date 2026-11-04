import threading
import logging
from typing import Callable, Optional
import keyboard

# Hotkey Modifier Constants for Win32 API compatibility
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000


class HotkeyManager:
    """Manages global hotkeys using the low-level Windows keyboard hook (`keyboard` library),
    providing seamless support across PowerShell, Windows Terminal, Notepad, Outlook, and all Windows apps.
    """

    def __init__(self):
        self._hotkey_str = "ctrl+shift+r"
        self._callback: Optional[Callable[[], None]] = None
        self._running = False
        self._hook_handle = None
        self._lock = threading.Lock()
        # Storage for backward compatibility with hotkey_id registration
        self._hotkeys = {}

    def add_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, callback: Callable) -> bool:
        """Register a hotkey specification with a callback."""
        with self._lock:
            # Build string from modifiers and vk_code
            parts = []
            if modifiers & MOD_CONTROL:
                parts.append("ctrl")
            if modifiers & MOD_SHIFT:
                parts.append("shift")
            if modifiers & MOD_ALT:
                parts.append("alt")
            if vk_code == ord("R"):
                parts.append("r")
            else:
                parts.append(chr(vk_code).lower())

            hotkey_str = "+".join(parts)
            self._hotkey_str = hotkey_str
            self._callback = callback
            self._hotkeys[hotkey_id] = {
                "modifiers": modifiers,
                "vk_code": vk_code,
                "callback": callback,
                "hotkey_str": hotkey_str,
            }

            if self._running:
                self._register_hook()
            return True

    def remove_hotkey(self, hotkey_id: int) -> None:
        """Remove registered hotkey."""
        with self._lock:
            if hotkey_id in self._hotkeys:
                del self._hotkeys[hotkey_id]
            if self._hook_handle:
                try:
                    keyboard.remove_hotkey(self._hook_handle)
                except Exception:
                    pass
                self._hook_handle = None

    def _dispatch(self, hotkey_id: int) -> None:
        """Dispatch the callback for the triggered hotkey."""
        callback = None
        with self._lock:
            if hotkey_id in self._hotkeys:
                callback = self._hotkeys[hotkey_id].get("callback")
            elif self._callback:
                callback = self._callback

        if callback:
            try:
                threading.Thread(target=callback, daemon=True, name="HotkeyCallback").start()
            except Exception as e:
                logging.error(f"Error dispatching hotkey callback: {e}")

    def _on_hotkey_triggered(self) -> None:
        """Internal callback when keyboard hook detects combination."""
        if self._callback:
            try:
                threading.Thread(target=self._callback, daemon=True, name="HotkeyCallback").start()
            except Exception as e:
                logging.error(f"Error starting callback thread: {e}")

    def _register_hook(self) -> None:
        if self._hook_handle:
            try:
                keyboard.remove_hotkey(self._hook_handle)
            except Exception:
                pass
            self._hook_handle = None

        try:
            self._hook_handle = keyboard.add_hotkey(
                self._hotkey_str,
                self._on_hotkey_triggered,
                suppress=True,
                trigger_on_release=False,
            )
            logging.info(f"Global hotkey registered: {self._hotkey_str} (suppress=True)")
        except Exception as e:
            logging.error(f"Failed to register global hotkey {self._hotkey_str}: {e}")

    def start(self) -> None:
        """Start listening for the global hotkey."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._register_hook()

    def stop(self) -> None:
        """Stop listening and remove hook."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._hook_handle:
                try:
                    keyboard.remove_hotkey(self._hook_handle)
                except Exception:
                    pass
                self._hook_handle = None

    def is_running(self) -> bool:
        return self._running
