import threading
import win32api
import win32con
import win32gui
from typing import Callable, Optional

# Custom window message for tray events
WM_TRAY_CALLBACK = win32con.WM_USER + 20


class TrayIcon:
    """Lightweight native Windows system tray icon with context menu.
    Allows adjusting speed, testing speech, and cleanly exiting without external packages.
    """

    def __init__(
        self,
        tooltip: str = "Read Aloud (Ctrl+Shift+R)",
        on_exit: Optional[Callable[[], None]] = None,
        on_test_speak: Optional[Callable[[], None]] = None,
        on_speed_change: Optional[Callable[[int], None]] = None,
    ):
        self.tooltip = tooltip
        self.on_exit = on_exit
        self.on_test_speak = on_test_speak
        self.on_speed_change = on_speed_change

        self.hwnd = None
        self._thread = None
        self._running = False
        self._hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    def _create_window(self):
        wc = win32gui.WNDCLASS()
        wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "ReadAloudTrayWindowClass"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = self._wnd_proc

        try:
            win32gui.RegisterClass(wc)
        except win32gui.error:
            pass  # Already registered

        self.hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "ReadAloudTray",
            0,
            0,
            0,
            win32con.CW_USEDEFAULT,
            win32con.CW_USEDEFAULT,
            0,
            0,
            wc.hInstance,
            None,
        )

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, WM_TRAY_CALLBACK, self._hicon, self.tooltip)
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    def _show_menu(self):
        menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(menu, win32con.MF_STRING | win32con.MF_GRAYED, 1000, "Read Aloud (Ctrl+Shift+R Active)")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 1001, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1002, "Test Speech")

        # Submenu for Speed
        speed_menu = win32gui.CreatePopupMenu()
        win32gui.AppendMenu(speed_menu, win32con.MF_STRING, 1010, "Slower (-3)")
        win32gui.AppendMenu(speed_menu, win32con.MF_STRING, 1011, "Normal (0)")
        win32gui.AppendMenu(speed_menu, win32con.MF_STRING, 1012, "Faster (+3)")
        win32gui.AppendMenu(menu, win32con.MF_POPUP, speed_menu, "Speech Speed")

        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 1003, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, 1004, "Exit")

        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None,
        )
        win32gui.DestroyMenu(menu)

        if cmd == 1002 and self.on_test_speak:
            self.on_test_speak()
        elif cmd == 1010 and self.on_speed_change:
            self.on_speed_change(-3)
        elif cmd == 1011 and self.on_speed_change:
            self.on_speed_change(0)
        elif cmd == 1012 and self.on_speed_change:
            self.on_speed_change(3)
        elif cmd == 1004:
            self.stop()
            if self.on_exit:
                self.on_exit()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAY_CALLBACK:
            if lparam in (win32con.WM_RBUTTONUP, win32con.WM_LBUTTONUP):
                self._show_menu()
                return 0
        elif msg == win32con.WM_DESTROY:
            nid = (self.hwnd, 0)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def _run(self):
        self._create_window()
        self._running = True
        win32gui.PumpMessages()
        self._running = False

    def start(self):
        """Start the system tray icon in a dedicated message thread."""
        self._thread = threading.Thread(target=self._run, daemon=True, name="TrayThread")
        self._thread.start()

    def stop(self):
        """Remove tray icon and destroy window."""
        if self.hwnd:
            win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            self.hwnd = None
        self._running = False
