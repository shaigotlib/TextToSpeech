#!/usr/bin/env pythonw
"""
Read Aloud Desktop Utility (main.pyw)
Runs quietly in the background without a console window.
Listens for Ctrl+Alt+R, Ctrl+Alt+Space, Ctrl+Alt+Up, Ctrl+Alt+Down, Ctrl+Alt+Right, and Ctrl+Alt+Left across any active Windows application.
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

MUTEX_NAME = "Local\\ReadAloudTTS_SingleInstance_Mutex_v3"


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
    logging.info("Starting Read Aloud Desktop Utility (Ctrl+Alt+R)...")

    service = ReadAloudService()
    service.start()

    def on_exit():
        logging.info("Exit requested from tray menu.")
        service.stop()
        sys.exit(0)

    def on_test():
        logging.info("Test speech requested from tray menu.")
        service.engine.speak(
            "Read aloud is active. Select any text and press Control Alt R.",
            async_mode=True,
        )

    def on_speed_change(rate_offset):
        service.engine.set_rate(rate_offset)
        service.engine.speak(f"Speed set to {rate_offset}", async_mode=True)

    def on_clear_reading():
        logging.info("Releasing navigation arrow keys from tray menu.")
        service.release_navigation()
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    def on_toggle_passthrough():
        service.on_toggle_passthrough_pressed()

    tray = TrayIcon(
        tooltip="Read Aloud Utility (Ctrl+Alt+R Active)",
        on_exit=on_exit,
        on_test_speak=on_test,
        on_speed_change=on_speed_change,
        on_clear_reading=on_clear_reading,
        on_toggle_passthrough=on_toggle_passthrough,
        is_passthrough_active=service.is_passthrough_active,
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
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        try:
            tray.stop()
        except Exception:
            pass
        try:
            service.stop()
        except Exception:
            pass
        if mutex_handle:
            ctypes.windll.kernel32.CloseHandle(mutex_handle)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical(f"Fatal error running main: {e}", exc_info=True)
