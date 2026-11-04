import threading
from typing import List, Optional
import win32com.client
import pythoncom

# SAPI 5 Flags
# SVSFlagsAsync = 1 (Speaks asynchronously)
# SVSFPurgeBeforeSpeak = 2 (Purges previous speech before speaking)
SVS_FLAGS_ASYNC = 1
SVS_PURGE_BEFORE_SPEAK = 2


class SpeechEngine:
    """Wrapper around Windows SAPI5 SpVoice for local, offline text-to-speech."""

    def __init__(self):
        pythoncom.CoInitialize()
        self._voice = win32com.client.Dispatch("SAPI.SpVoice")
        self._lock = threading.Lock()

    def get_voices(self) -> List[str]:
        """Return the names/descriptions of all installed Windows SAPI voices."""
        with self._lock:
            voices = self._voice.GetVoices()
            return [voices.Item(i).GetDescription() for i in range(voices.Count)]

    def set_voice_by_name(self, name: str) -> bool:
        """Select a voice matching the given name or description."""
        with self._lock:
            voices = self._voice.GetVoices()
            for i in range(voices.Count):
                voice_token = voices.Item(i)
                if name.lower() in voice_token.GetDescription().lower():
                    self._voice.Voice = voice_token
                    return True
            return False

    def set_rate(self, rate: int) -> None:
        """Set speech speed. Valid range is -10 (slowest) to 10 (fastest)."""
        clamped = max(-10, min(10, rate))
        with self._lock:
            self._voice.Rate = clamped

    def get_rate(self) -> int:
        """Return current rate setting (-10 to 10)."""
        with self._lock:
            return self._voice.Rate

    def set_volume(self, volume: int) -> None:
        """Set speech volume. Valid range is 0 to 100."""
        clamped = max(0, min(100, volume))
        with self._lock:
            self._voice.Volume = clamped

    def get_volume(self) -> int:
        """Return current volume setting (0 to 100)."""
        with self._lock:
            return self._voice.Volume

    def is_speaking(self) -> bool:
        """Return True if speech is actively rendering."""
        with self._lock:
            try:
                # Status.RunningState == 2 means currently speaking (SRSEIsSpeaking = 2)
                return self._voice.Status.RunningState == 2
            except Exception:
                return False

    def speak(self, text: str, async_mode: bool = True) -> bool:
        """Speak given text aloud.

        If async_mode is True, speaks without blocking.
        Purges any currently speaking speech queue prior to speaking new text.
        Returns True if speech was queued/rendered, False if text was empty.
        """
        if not text or not text.strip():
            return False

        flags = SVS_PURGE_BEFORE_SPEAK
        if async_mode:
            flags |= SVS_FLAGS_ASYNC

        with self._lock:
            pythoncom.CoInitialize()
            self._voice.Speak(text.strip(), flags)
            return True

    def stop(self) -> None:
        """Immediately cancel and stop any currently active speech."""
        with self._lock:
            pythoncom.CoInitialize()
            # Speaking empty string with purge flag stops any running audio
            self._voice.Speak("", SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)
