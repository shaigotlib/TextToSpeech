import logging
import winsound
from typing import Optional
from src.speech_engine import SpeechEngine
from src.text_capturer import TextCapturer
from src.text_model import TextDocument
from src.navigation_debouncer import NavigationDebouncer
from src.hotkey_manager import (
    HotkeyManager,
    MOD_CONTROL,
    MOD_ALT,
    VK_SPACE,
    VK_UP,
    VK_DOWN,
    VK_LEFT,
    VK_RIGHT,
    VK_OEM_5,
    VK_OEM_102,
)

HOTKEY_ID_READ = 1001
HOTKEY_ID_PAUSE = 1002
HOTKEY_ID_SPEED_UP = 1003
HOTKEY_ID_SPEED_DOWN = 1004
HOTKEY_ID_SKIP_FORWARD = 1005
HOTKEY_ID_SKIP_BACKWARD = 1006
HOTKEY_ID_TOGGLE_PASSTHROUGH_1 = 1007
HOTKEY_ID_TOGGLE_PASSTHROUGH_2 = 1008
HOTKEY_ID_TOGGLE_PASSTHROUGH = 1007  # Backward compatibility alias



class ReadAloudService:
    """Coordinates hotkey triggering, text capture, and speech synthesis.
    Shortcuts:
    - Ctrl + Alt + R     : Read highlighted text aloud / Stop speech
    - Ctrl + Alt + Space : Pause / Resume ongoing speech
    - Ctrl + Alt + Up    : Increase speech speed (+1, max 10)
    - Ctrl + Alt + Down  : Decrease speech speed (-1, min -10)
    - Ctrl + Alt + Right : Skip one word forward (accumulates on sequence of clicks)
    - Ctrl + Alt + Left  : Move back one word and re-read it (accumulates on sequence of clicks)
    - Ctrl + Alt + \     : Toggle shortcut passthrough mode (release all hotkeys to focused app)
    """

    def __init__(
        self,
        engine: Optional[SpeechEngine] = None,
        capturer: Optional[TextCapturer] = None,
        hotkey_mgr: Optional[HotkeyManager] = None,
        feedback_beeps: bool = True,
        debounce_delay: float = 0.22,
    ):
        self.engine = engine or SpeechEngine()
        self.capturer = capturer or TextCapturer()
        self.hotkey_mgr = hotkey_mgr or HotkeyManager()
        self.feedback_beeps = feedback_beeps
        self._active = False
        self._passthrough_active = False
        self._current_doc: Optional[TextDocument] = None
        self._nav_hooked: bool = False
        self._debouncer = NavigationDebouncer(
            on_flush=self._apply_word_navigation,
            debounce_delay=debounce_delay,
        )

    def is_navigation_hooked(self) -> bool:
        """Return True if word navigation arrow hotkeys are currently hooked."""
        return self._nav_hooked

    def is_passthrough_active(self) -> bool:
        """Return True if shortcuts are currently passed through to the focused application."""
        return self._passthrough_active

    def on_toggle_passthrough_pressed(self) -> None:
        """Toggle passthrough mode: releases or restores all tool hotkeys beside Ctrl+Alt+\\."""
        logging.info("Hotkey Ctrl+Alt+\\ triggered (Toggle Passthrough).")
        if not self._passthrough_active:
            # Activate passthrough: release all shortcuts to the focused application
            self._passthrough_active = True
            self.stop_speech()
            self._disable_navigation_hotkeys()
            self._unregister_functional_hotkeys()
            logging.info(
                "Passthrough mode ACTIVATED (Ctrl+Alt+\\): All tool shortcuts released to focused application."
            )
            if self.feedback_beeps:
                try:
                    winsound.Beep(500, 100)
                    time.sleep(0.04)
                    winsound.Beep(400, 100)
                except Exception:
                    try:
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    except Exception:
                        pass
        else:
            # Deactivate passthrough: restore all tool hotkeys
            self._passthrough_active = False
            self._register_base_hotkeys()
            logging.info(
                "Passthrough mode DEACTIVATED (Ctrl+Alt+\\): Tool shortcuts restored and active."
            )
            if self.feedback_beeps:
                try:
                    winsound.Beep(600, 100)
                    time.sleep(0.04)
                    winsound.Beep(900, 100)
                except Exception:
                    try:
                        winsound.MessageBeep(winsound.MB_OK)
                    except Exception:
                        pass

    def _register_base_hotkeys(self) -> None:
        """Register the functional read aloud shortcuts."""
        # 1. Ctrl + Alt + R : Read / Stop
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_READ,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=ord("R"),
            callback=self.on_hotkey_pressed,
        )

        # 2. Ctrl + Alt + Space : Pause / Resume
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_PAUSE,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_SPACE,
            callback=self.on_pause_pressed,
        )

        # 3. Ctrl + Alt + Up : Speed Up
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_SPEED_UP,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_UP,
            callback=self.on_speed_up_pressed,
        )

        # 4. Ctrl + Alt + Down : Speed Down
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_SPEED_DOWN,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_DOWN,
            callback=self.on_speed_down_pressed,
        )

    def _unregister_functional_hotkeys(self) -> None:
        """Unregister functional shortcuts so the active app receives them."""
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_READ)
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_PAUSE)
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_SPEED_UP)
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_SPEED_DOWN)

    def _enable_navigation_hotkeys(self) -> None:
        """Dynamically register Ctrl+Alt+Left and Ctrl+Alt+Right arrow hotkeys while reading."""
        if self._nav_hooked:
            return
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_SKIP_FORWARD,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_RIGHT,
            callback=self.on_skip_forward_pressed,
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_SKIP_BACKWARD,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_LEFT,
            callback=self.on_skip_backward_pressed,
        )
        self._nav_hooked = True
        logging.info("Word navigation hotkeys (Ctrl+Alt+Left/Right) activated.")

    def _disable_navigation_hotkeys(self) -> None:
        """Release Ctrl+Alt+Left and Ctrl+Alt+Right arrow hotkeys back to VS Code and other apps."""
        if not self._nav_hooked:
            return
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_SKIP_FORWARD)
        self.hotkey_mgr.remove_hotkey(HOTKEY_ID_SKIP_BACKWARD)
        self._nav_hooked = False
        logging.info("Word navigation hotkeys (Ctrl+Alt+Left/Right) released to applications.")

    def release_navigation(self) -> None:
        """Explicitly release navigation arrow shortcuts and clear active document."""
        self._debouncer.cancel()
        self._disable_navigation_hotkeys()
        self._current_doc = None
        logging.info("Navigation released and document cleared by user.")

    def get_current_doc(self) -> Optional[TextDocument]:
        """Return the currently captured TextDocument if any."""
        return self._current_doc

    def on_hotkey_pressed(self) -> None:
        """Triggered whenever the user presses Ctrl+Alt+R globally."""
        logging.info("Hotkey Ctrl+Alt+R triggered.")

        # 1. If actively speaking, pressing hotkey toggles and cancels speech immediately
        if self.engine.is_speaking():
            logging.info("Currently speaking - stopping speech.")
            self.engine.stop()
            return

        # 2. Capture highlighted text across active window
        text = self.capturer.get_selected_text()
        if text and self.capturer.has_speakable_content(text):
            logging.info(f"Speaking captured text ({len(text)} chars): {text[:60]!r}")
            self._current_doc = TextDocument(text)
            self._enable_navigation_hotkeys()
            self.engine.speak(text, async_mode=True)
        else:
            logging.info(f"No valid speakable text captured (raw: {text!r}).")
            if self._current_doc and self._current_doc.total_words > 0:
                logging.info("Re-reading existing captured document from current position.")
                self._enable_navigation_hotkeys()
                current_idx = self.engine.get_current_word_index(self._current_doc)
                self.engine.seek_and_play(self._current_doc, current_idx)
            elif self.feedback_beeps:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

    def on_pause_pressed(self) -> None:
        """Triggered whenever user presses Ctrl+Alt+Space (pause / resume)."""
        logging.info("Hotkey Ctrl+Alt+Space triggered (Pause/Resume).")
        if self.engine.is_paused():
            logging.info("Resuming paused speech.")
            self.engine.resume()
        elif self.engine.is_speaking():
            logging.info("Pausing ongoing speech.")
            self.engine.pause()
        else:
            logging.info("No active speech to pause or resume.")

    def on_speed_up_pressed(self) -> None:
        """Triggered whenever user presses Ctrl+Alt+Up (increase speech speed)."""
        current_rate = self.engine.get_rate()
        new_rate = min(10, current_rate + 1)
        self.engine.set_rate(new_rate)
        logging.info(f"Speech speed increased: {current_rate} -> {new_rate}")
        if self.feedback_beeps:
            try:
                winsound.Beep(1200, 70)
            except Exception:
                pass

    def on_speed_down_pressed(self) -> None:
        """Triggered whenever user presses Ctrl+Alt+Down (decrease speech speed)."""
        current_rate = self.engine.get_rate()
        new_rate = max(-10, current_rate - 1)
        self.engine.set_rate(new_rate)
        logging.info(f"Speech speed decreased: {current_rate} -> {new_rate}")
        if self.feedback_beeps:
            try:
                winsound.Beep(700, 70)
            except Exception:
                pass

    def on_skip_forward_pressed(self) -> None:
        """Triggered whenever user presses Ctrl+Alt+Right (skip forward 1 word)."""
        if not self._current_doc or self._current_doc.total_words == 0:
            logging.info("Ctrl+Alt+Right pressed but no active document to navigate.")
            if self.feedback_beeps:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
            return

        logging.info("Hotkey Ctrl+Alt+Right triggered (Skip Forward).")
        self._debouncer.add_step(1, on_first_click=self.engine.pause)

    def on_skip_backward_pressed(self) -> None:
        """Triggered whenever user presses Ctrl+Alt+Left (move back 1 word and re-read)."""
        if not self._current_doc or self._current_doc.total_words == 0:
            logging.info("Ctrl+Alt+Left pressed but no active document to navigate.")
            if self.feedback_beeps:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
            return

        logging.info("Hotkey Ctrl+Alt+Left triggered (Skip Backward).")
        self._debouncer.add_step(-1, on_first_click=self.engine.pause)

    def _apply_word_navigation(self, delta: int) -> None:
        """Callback invoked after a sequence of navigation clicks settles."""
        if not self._current_doc or self._current_doc.total_words == 0:
            return

        current_idx = self.engine.get_current_word_index(self._current_doc)
        target_idx = self._current_doc.clamp_word_index(current_idx + delta)
        logging.info(
            f"Word navigation applied: delta={delta:+d}, from word {current_idx} -> {target_idx} ('{self._current_doc.spans[target_idx].text}')"
        )

        if self.feedback_beeps:
            try:
                freq = 1100 if delta > 0 else 850
                winsound.Beep(freq, 60)
            except Exception:
                pass

        self.engine.seek_and_play(self._current_doc, target_idx)

    def stop_speech(self) -> None:
        """Immediately stop ongoing speech."""
        self._debouncer.cancel()
        self.engine.stop()

    def start(self) -> None:
        """Register all Ctrl+Alt global hotkeys and start listening."""
        if self._active:
            return

        # Register functional shortcuts (Read, Pause, SpeedUp, SpeedDown)
        self._register_base_hotkeys()

        # 5. Ctrl + Alt + \ : Toggle Passthrough (Register both US ANSI VK_OEM_5 and ISO VK_OEM_102)
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_TOGGLE_PASSTHROUGH_1,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_OEM_5,
            callback=self.on_toggle_passthrough_pressed,
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=HOTKEY_ID_TOGGLE_PASSTHROUGH_2,
            modifiers=MOD_CONTROL | MOD_ALT,
            vk_code=VK_OEM_102,
            callback=self.on_toggle_passthrough_pressed,
        )

        self.hotkey_mgr.start()
        self._active = True
        self._passthrough_active = False
        logging.info(
            "ReadAloudService started with hotkeys: Ctrl+Alt+R, Ctrl+Alt+Space, Ctrl+Alt+Up, Ctrl+Alt+Down, and Ctrl+Alt+\\ (Passthrough Toggle)."
        )

    def stop(self) -> None:
        """Stop listening and cleanly shutdown."""
        if not self._active:
            return
        self._active = False
        self._passthrough_active = False
        self._debouncer.cancel()
        self._disable_navigation_hotkeys()
        self.hotkey_mgr.stop()
        self.engine.stop()
        logging.info("ReadAloudService stopped.")

    def is_active(self) -> bool:
        return self._active
