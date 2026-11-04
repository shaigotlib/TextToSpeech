import logging
import winsound
from typing import Optional
from src.speech_engine import SpeechEngine
from src.text_capturer import TextCapturer
from src.hotkey_manager import HotkeyManager, MOD_CONTROL, MOD_SHIFT

HOTKEY_ID_READ = 1001


class ReadAloudService:
    """Coordinates hotkey triggering, text capture, and speech synthesis."""

    def __init__(
        self,
        engine: Optional[SpeechEngine] = None,
        capturer: Optional[TextCapturer] = None,
        hotkey_mgr: Optional[HotkeyManager] = None,
        feedback_beeps: bool = True,
    ):
        self.engine = engine or SpeechEngine()
        self.capturer = capturer or TextCapturer()
        self.hotkey_mgr = hotkey_mgr or HotkeyManager()
        self.feedback_beeps = feedback_beeps
        self._active = False

    def on_hotkey_pressed(self) -> None:
        """Triggered whenever the user presses Ctrl+Shift+R globally."""
        logging.info("Hotkey Ctrl+Shift+R triggered.")

        # 1. If actively speaking, pressing hotkey toggles and cancels speech immediately
        if self.engine.is_speaking():
            logging.info("Currently speaking - stopping speech.")
            self.engine.stop()
            return

        # 2. Capture highlighted text across active window
        text = self.capturer.get_selected_text()
        if text and self.capturer.has_speakable_content(text):
            logging.info(f"Speaking captured text ({len(text)} chars): {text[:60]!r}")
            self.engine.speak(text, async_mode=True)
        else:
            logging.info(f"No valid speakable text captured (raw: {text!r}).")
            if self.feedback_beeps:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

    def stop_speech(self) -> None:
        """Immediately stop ongoing speech."""
        self.engine.stop()

    def start(self) -> None:
        """Register Ctrl+Shift+R global hotkey and start listening."""
        if self._active:
            return
        # Register Ctrl+Shift+R
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_READ,
            modifiers=MOD_CONTROL | MOD_SHIFT,
            vk_code=ord("R"),
            callback=self.on_hotkey_pressed,
        )
        self.hotkey_mgr.start()
        self._active = True
        logging.info("ReadAloudService started with hotkey Ctrl+Shift+R.")

    def stop(self) -> None:
        """Stop listening and cleanly shutdown."""
        if not self._active:
            return
        self._active = False
        self.hotkey_mgr.stop()
        self.engine.stop()
        logging.info("ReadAloudService stopped.")

    def is_active(self) -> bool:
        return self._active
