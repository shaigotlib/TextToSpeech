#!/usr/bin/env pythonw
"""
Read Aloud Desktop Utility (main.pyw)
Runs quietly in the background without a console window.
Listens for Ctrl+R and reads selected text across any active Windows application.
"""

import sys
import time
import os

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.read_aloud_service import ReadAloudService
from src.tray_icon import TrayIcon


def main():
    service = ReadAloudService()
    service.start()

    def on_exit():
        service.stop()
        sys.exit(0)

    def on_test():
        service.engine.speak("Read aloud is active. Select any text and press Control R.", async_mode=True)

    def on_speed_change(rate_offset):
        service.engine.set_rate(rate_offset)
        service.engine.speak(f"Speed set to {rate_offset}", async_mode=True)

    tray = TrayIcon(
        tooltip="Read Aloud Utility (Ctrl+R Active)",
        on_exit=on_exit,
        on_test_speak=on_test,
        on_speed_change=on_speed_change,
    )
    tray.start()

    # Keep the main thread alive waiting for shutdown
    try:
        while service.is_active():
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        tray.stop()
        service.stop()


if __name__ == "__main__":
    main()
