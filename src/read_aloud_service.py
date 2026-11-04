import logging
from typing import Optional
from src.speech_engine import SpeechEngine
from src.text_capturer import TextCapturer
from src.hotkey_manager import HotkeyManager, MOD_CONTROL

HOTKEY_ID_READ = 1001


class ReadAloudService:
    """Coordinates hotkey triggering, text capture, and speech synthesis."""

    def __init__(
        self,
        engine: Optional[SpeechEngine] = None,
        capturer: Optional[TextCapturer] = None,
        hotkey_mgr: Optional[HotkeyManager] = None,
    ):
        self.engine = engine or SpeechEngine()
        self.capturer = capturer or TextCapturer()
        self.hotkey_mgr = hotkey_mgr or HotkeyManager()
        self._active = False

    def on_hotkey_pressed(self) -> None:
        """Triggered whenever the user presses Ctrl+R globally."""
        # 1. If actively speaking, pressing Ctrl+R stops speech immediately (toggle behavior)
        if self.engine.is_speaking():
            self.engine.stop()
            return

        # 2. Otherwise, capture highlighted text across active window
        text = self.capturer.get_selected_text()
        if text:
            self.engine.speak(text, async_mode=True)

    def stop_speech(self) -> None:
        """Immediately stop ongoing speech."""
        self.engine.stop()

    def start(self) -> None:
        """Register Ctrl+R global hotkey and start listening."""
        if self._active:
            return
        # Register Ctrl+R (0x52 is virtual key code for 'R')
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_READ,
            modifiers=MOD_CONTROL,
            vk_code=ord("R"),
            callback=self.on_hotkey_pressed,
        )
        self.hotkey_mgr.start()
        self._active = True

    def stop(self) -> None:
        """Stop listening and cleanly shutdown."""
        if not self._active:
            return
        self._active = False
        self.hotkey_mgr.stop()
        self.engine.stop()

    def is_active(self) -> bool:
        return self._active
