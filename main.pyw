#!/usr/bin/env pythonw
"""
Read Aloud Desktop Utility (main.pyw)
Runs quietly in the background without a console window.
Listens for Ctrl+Shift+R and reads selected text across any active Windows application.
"""

import sys
import time
import os
import logging
import ctypes

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Configure logging
LOG_PATH = os.path.join(BASE_DIR, "read_aloud.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

from src.read_aloud_service import ReadAloudService
from src.tray_icon import TrayIcon

MUTEX_NAME = "Global\\ReadAloudTTS_SingleInstance_Mutex_v2"


def acquire_single_instance_mutex():
    """Ensure only one instance runs at a time using a named Win32 mutex."""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    last_error = kernel32.GetLastError()
    # 183 = ERROR_ALREADY_EXISTS
    if last_error == 183:
        logging.warning("Another instance of Read Aloud is already running. Exiting duplicate.")
        sys.exit(0)
    return handle


def main():
    mutex_handle = acquire_single_instance_mutex()
    logging.info("Starting Read Aloud Desktop Utility (Ctrl+Shift+R)...")

    service = ReadAloudService()
    service.start()

    def on_exit():
        logging.info("Exit requested from tray menu.")
        service.stop()
        sys.exit(0)

    def on_test():
        logging.info("Test speech requested from tray menu.")
        service.engine.speak(
            "Read aloud is active. Select any text and press Control Shift R.",
            async_mode=True,
        )

    def on_speed_change(rate_offset):
        service.engine.set_rate(rate_offset)
        service.engine.speak(f"Speed set to {rate_offset}", async_mode=True)

    tray = TrayIcon(
        tooltip="Read Aloud Utility (Ctrl+Shift+R Active)",
        on_exit=on_exit,
        on_test_speak=on_test,
        on_speed_change=on_speed_change,
    )
    tray.start()

    # Announce readiness with a short pleasant sound
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass

    # Main loop waiting for shutdown
    try:
        while service.is_active():
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        tray.stop()
        service.stop()
        if mutex_handle:
            ctypes.windll.kernel32.CloseHandle(mutex_handle)


if __name__ == "__main__":
    main()
