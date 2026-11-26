import threading
import logging
import time
import ctypes
from typing import Callable, Optional, Dict, Any
import win32gui
import win32api
import win32con

# Hotkey Modifier Constants for Win32 RegisterHotKey API
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual Key Codes
VK_SPACE = 0x20
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_OEM_5 = 0xDC    # Backslash '\' on US ANSI layout
VK_OEM_102 = 0xE2  # Backslash '\' on International ISO / laptop layout

# Win32 Windows Messages & System Event Constants
WM_HOTKEY = 0x0312
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WTS_SESSION_LOGON = 0x5
WTS_SESSION_LOGOFF = 0x6
PBT_APMRESUMEAUTOMATIC = 0x12
PBT_APMRESUMESUSPEND = 0x7

# Internal thread message codes
WM_USER_REGISTER = win32con.WM_USER + 101
WM_USER_UNREGISTER = win32con.WM_USER + 102
WM_USER_REREGISTER_ALL = win32con.WM_USER + 103


def vk_to_key_str(vk_code: int) -> str:
    """Map common VK codes to key names."""
    if vk_code == VK_SPACE:
        return "space"
    elif vk_code == VK_LEFT:
        return "left"
    elif vk_code == VK_UP:
        return "up"
    elif vk_code == VK_RIGHT:
        return "right"
    elif vk_code == VK_DOWN:
        return "down"
    elif vk_code in (VK_OEM_5, VK_OEM_102) or vk_code == ord("\\"):
        return "\\"
    elif ord("A") <= vk_code <= ord("Z"):
        return chr(vk_code).lower()
    elif ord("0") <= vk_code <= ord("9"):
        return chr(vk_code)
    else:
        try:
            return chr(vk_code).lower()
        except Exception:
            return str(vk_code)


class HotkeyManager:
    """Robust Win32 RegisterHotKey manager.
    - Uses native Windows kernel hotkey subsystem (immune to low-level hook timeouts).
    - Automatically listens for WM_POWERBROADCAST (sleep, standby, resume).
    - Automatically listens for WM_WTSSESSION_CHANGE (laptop lid close, lock, unlock, logon).
    - Automatically re-registers hotkeys on wake and unlock.
    - Includes a background watchdog ensuring hotkeys never drop across power transitions.
    """

    def __init__(self):
        self._running = False
        self._lock = threading.Lock()
        self._hotkeys: Dict[int, Dict[str, Any]] = {}
        self._hwnd = None
        self._thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._ready_event = threading.Event()
        self._user32 = ctypes.windll.user32
        self._wtsapi32 = ctypes.windll.wtsapi32
        self._wts_registered = False

    def add_hotkey(self, hotkey_id: int, modifiers: int, vk_code: int, callback: Callable) -> bool:
        """Register a hotkey specification with a callback."""
        with self._lock:
            parts = []
            if modifiers & MOD_CONTROL:
                parts.append("ctrl")
            if modifiers & MOD_ALT:
                parts.append("alt")
            if modifiers & MOD_SHIFT:
                parts.append("shift")

            key_name = vk_to_key_str(vk_code)
            parts.append(key_name)
            hotkey_str = "+".join(parts)

            self._hotkeys[hotkey_id] = {
                "modifiers": modifiers,
                "vk_code": vk_code,
                "callback": callback,
                "hotkey_str": hotkey_str,
                "registered": False,
            }

            if self._running and self._hwnd and win32gui.IsWindow(self._hwnd):
                win32api.PostMessage(self._hwnd, WM_USER_REGISTER, hotkey_id, 0)
            return True

    def remove_hotkey(self, hotkey_id: int) -> None:
        """Remove registered hotkey."""
        with self._lock:
            if hotkey_id in self._hotkeys:
                if self._running and self._hwnd and win32gui.IsWindow(self._hwnd):
                    win32api.PostMessage(self._hwnd, WM_USER_UNREGISTER, hotkey_id, 0)
                del self._hotkeys[hotkey_id]

    def _dispatch(self, hotkey_id: int) -> None:
        """Dispatch the callback for the triggered hotkey on a background thread."""
        callback = None
        with self._lock:
            if hotkey_id in self._hotkeys:
                callback = self._hotkeys[hotkey_id].get("callback")

        if callback:
            try:
                threading.Thread(
                    target=callback,
                    daemon=True,
                    name=f"HotkeyCallback_{hotkey_id}",
                ).start()
            except Exception as e:
                logging.error(f"Error dispatching hotkey {hotkey_id} callback: {e}")

    def _register_api(self, hwnd: int, hk_id: int, item: Dict[str, Any], verbose: bool = True) -> bool:
        """Register single hotkey via RegisterHotKey API on the window thread."""
        mods = item["modifiers"] | MOD_NOREPEAT
        vk = item["vk_code"]
        self._user32.UnregisterHotKey(hwnd, hk_id)
        res = self._user32.RegisterHotKey(hwnd, hk_id, mods, vk)
        was_registered = item.get("registered", False)
        item["registered"] = bool(res)
        if res:
            if verbose or not was_registered:
                logging.info(f"Global hotkey registered: {item['hotkey_str']} (id={hk_id}, suppress=True)")
        else:
            err = ctypes.GetLastError()
            logging.error(f"Failed to register global hotkey {item['hotkey_str']} (id={hk_id}): error {err}")
        return bool(res)

    def _reregister_all_internal(self, hwnd: int, verbose: bool = True) -> int:
        """Re-register all currently configured hotkeys on window thread."""
        with self._lock:
            items = list(self._hotkeys.items())
        count = 0
        for hk_id, item in items:
            if self._register_api(hwnd, hk_id, item, verbose=verbose):
                count += 1
        return count

    def reregister_all(self) -> None:
        """External trigger to force re-registration across all hotkeys."""
        hwnd = self._hwnd
        if hwnd and win32gui.IsWindow(hwnd):
            win32api.PostMessage(hwnd, WM_USER_REREGISTER_ALL, 1, 0)

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_HOTKEY:
            hk_id = wparam
            self._dispatch(hk_id)
            return 0
        elif msg == WM_USER_REGISTER:
            hk_id = wparam
            with self._lock:
                item = self._hotkeys.get(hk_id)
            if item:
                self._register_api(hwnd, hk_id, item, verbose=True)
            return 0
        elif msg == WM_USER_UNREGISTER:
            hk_id = wparam
            self._user32.UnregisterHotKey(hwnd, hk_id)
            return 0
        elif msg == WM_USER_REREGISTER_ALL:
            verbose = bool(wparam)
            self._reregister_all_internal(hwnd, verbose=verbose)
            return 0
        elif msg == win32con.WM_POWERBROADCAST:
            # Laptop resumed from sleep or standby
            if wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                logging.info(f"System resumed from sleep/standby (PBT={wparam}). Re-registering hotkeys...")
                self._reregister_all_internal(hwnd, verbose=True)
            return 1
        elif msg == WM_WTSSESSION_CHANGE:
            # User unlocked the laptop or logged back in
            if wparam in (WTS_SESSION_UNLOCK, WTS_SESSION_LOGON):
                logging.info(f"Windows session unlock/logon detected (WTS={wparam}). Re-registering hotkeys...")
                self._reregister_all_internal(hwnd, verbose=True)
            return 0
        elif msg == win32con.WM_DESTROY:
            if self._wts_registered:
                try:
                    self._wtsapi32.WTSUnRegisterSessionNotification(hwnd)
                except Exception:
                    pass
                self._wts_registered = False
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _watchdog_loop(self) -> None:
        """Lightweight background watchdog ensuring hotkeys remain registered across laptop lid events."""
        while self._running:
            time.sleep(30.0)
            if not self._running:
                break
            try:
                hwnd = self._hwnd
                if hwnd and win32gui.IsWindow(hwnd):
                    win32api.PostMessage(hwnd, WM_USER_REREGISTER_ALL, 0, 0)
            except Exception:
                pass

    def _run(self) -> None:
        """Message pump thread procedure."""
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = f"ReadAloudHotkeyClass_{id(self)}_{int(time.time() * 1000)}"
        wc.lpfnWndProc = self._wnd_proc
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        self._hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "ReadAloudHotkeys",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            wc.hInstance,
            None,
        )

        try:
            self._wtsapi32.WTSRegisterSessionNotification(self._hwnd, 0)
            self._wts_registered = True
        except Exception as e:
            logging.warning(f"Could not register session notification: {e}")

        # Register initial hotkeys
        self._reregister_all_internal(self._hwnd)
        self._ready_event.set()

        try:
            win32gui.PumpMessages()
        finally:
            self._hwnd = None

    def start(self) -> None:
        """Start listening for all registered global hotkeys in dedicated message pump thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._ready_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="HotkeyWndThread",
            )
            self._thread.start()

            self._watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                daemon=True,
                name="HotkeyWatchdogThread",
            )
            self._watchdog_thread.start()

        self._ready_event.wait(timeout=2.0)

    def stop(self) -> None:
        """Stop listening and remove all hotkey registrations."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            hwnd = self._hwnd
            if hwnd and win32gui.IsWindow(hwnd):
                for hk_id in list(self._hotkeys.keys()):
                    try:
                        self._user32.UnregisterHotKey(hwnd, hk_id)
                    except Exception:
                        pass
                try:
                    win32api.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                except Exception:
                    pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._watchdog_thread = None

    def is_running(self) -> bool:
        """Return True if the hotkey listener is active."""
        return self._running
