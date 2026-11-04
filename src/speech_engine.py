import threading
import asyncio
import os
import tempfile
import ctypes
import logging
from typing import List, Optional
import win32com.client
import pythoncom

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# SAPI 5 Flags
SVS_FLAGS_ASYNC = 1
SVS_PURGE_BEFORE_SPEAK = 2

# Default natural Hebrew voice
DEFAULT_HEBREW_VOICE = "he-IL-HilaNeural"


class SpeechEngine:
    """Bilingual Windows speech engine supporting Hebrew and English.
    - English: Fast, offline Windows SAPI5 voice engine.
    - Hebrew: High-quality natural neural voice (edge-tts) with instant Windows MCI audio playback.
    """

    def __init__(self):
        pythoncom.CoInitialize()
        self._voice = win32com.client.Dispatch("SAPI.SpVoice")
        self._lock = threading.Lock()
        self._is_external_speaking = False
        self._stop_event = threading.Event()
        self._mci_alias = "read_aloud_tts_mci"
        self._winmm = ctypes.windll.winmm

    def is_hebrew(self, text: Optional[str]) -> bool:
        """Return True if text contains any Hebrew characters (Unicode ֐-׿)."""
        if not text:
            return False
        return any("֐" <= c <= "׿" for c in text)

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
        """Set speech speed. Valid range is -10 to 10."""
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
        """Return True if speech is actively rendering (either SAPI or external stream)."""
        if self._is_external_speaking:
            return True
        with self._lock:
            try:
                return self._voice.Status.RunningState == 2
            except Exception:
                return False

    def _play_audio_file(self, file_path: str) -> None:
        """Play generated audio via Windows MCI and support instant cancellation."""
        try:
            mci = self._winmm.mciSendStringW
            # Close any previous audio device instance
            mci(f"close {self._mci_alias}", None, 0, 0)

            # Open file
            ret = mci(f'open "{file_path}" type mpegvideo alias {self._mci_alias}', None, 0, 0)
            if ret != 0:
                logging.error(f"MCI open failed with code: {ret}")
                return

            # Start playback
            mci(f"play {self._mci_alias}", None, 0, 0)
            self._is_external_speaking = True

            # Poll status until finished or stopped
            status_buf = ctypes.create_unicode_buffer(128)
            while not self._stop_event.is_set():
                mci(f"status {self._mci_alias} mode", status_buf, 128, 0)
                if status_buf.value.lower() != "playing":
                    break
                self._stop_event.wait(0.08)

            mci(f"stop {self._mci_alias}", None, 0, 0)
            mci(f"close {self._mci_alias}", None, 0, 0)
        except Exception as e:
            logging.error(f"Error in MCI audio playback: {e}")
        finally:
            self._is_external_speaking = False
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass

    def _speak_hebrew_worker(self, text: str) -> None:
        """Generate and play Hebrew speech asynchronously."""
        tmp_path = ""
        try:
            self._stop_event.clear()
            self._is_external_speaking = True

            # Calculate rate string for edge-tts (e.g. "+10%", "-10%")
            rate_val = self.get_rate()
            rate_str = f"{rate_val * 5:+d}%" if rate_val != 0 else "+0%"

            communicate = edge_tts.Communicate(text, DEFAULT_HEBREW_VOICE, rate=rate_str)

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name

            # Run async edge_tts download
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(tmp_path))
            loop.close()

            if self._stop_event.is_set():
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return

            self._play_audio_file(tmp_path)
        except Exception as e:
            logging.error(f"Hebrew TTS generation failed: {e}. Falling back to SAPI.")
            self._is_external_speaking = False
            # Fallback to SAPI
            with self._lock:
                pythoncom.CoInitialize()
                self._voice.Speak(text, SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)

    def speak(self, text: str, async_mode: bool = True) -> bool:
        """Speak given text aloud in Hebrew or English automatically."""
        if not text or not text.strip():
            return False

        # First stop any currently playing audio
        self.stop()

        clean_text = text.strip()

        # Check if text contains Hebrew
        if self.is_hebrew(clean_text) and EDGE_TTS_AVAILABLE:
            if async_mode:
                threading.Thread(
                    target=self._speak_hebrew_worker,
                    args=(clean_text,),
                    daemon=True,
                    name="HebrewTTSWorker",
                ).start()
            else:
                self._speak_hebrew_worker(clean_text)
            return True

        # Pure English or fallback SAPI
        flags = SVS_PURGE_BEFORE_SPEAK
        if async_mode:
            flags |= SVS_FLAGS_ASYNC

        with self._lock:
            pythoncom.CoInitialize()
            self._voice.Speak(clean_text, flags)
            return True

    def stop(self) -> None:
        """Immediately cancel and stop any currently active speech."""
        self._stop_event.set()
        if self._is_external_speaking:
            try:
                self._winmm.mciSendStringW(f"stop {self._mci_alias}", None, 0, 0)
                self._winmm.mciSendStringW(f"close {self._mci_alias}", None, 0, 0)
            except Exception:
                pass
            self._is_external_speaking = False

        with self._lock:
            pythoncom.CoInitialize()
            self._voice.Speak("", SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)
