import threading
import asyncio
import os
import tempfile
import ctypes
import logging
import bisect
from typing import List, Optional, Any
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
        self._is_paused = False
        self._stop_event = threading.Event()
        self._mci_alias = "read_aloud_tts_mci"
        self._winmm = ctypes.windll.winmm
        self._sapi_base_char_offset: int = 0
        self._last_word_index: int = 0
        self._current_audio_file: Optional[str] = None
        self._current_text: str = ""
        self._audio_duration_ms: int = 0
        self._word_timestamps: List[int] = []

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

    def is_paused(self) -> bool:
        """Return True if speech is currently paused."""
        return self._is_paused

    def pause(self) -> bool:
        """Pause speech playback if currently speaking."""
        if self._is_paused:
            return False

        if self._is_external_speaking:
            try:
                self._winmm.mciSendStringW(f"pause {self._mci_alias}", None, 0, 0)
                self._is_paused = True
                return True
            except Exception as e:
                logging.error(f"Error pausing MCI playback: {e}")
                return False
        else:
            with self._lock:
                try:
                    pythoncom.CoInitialize()
                    self._voice.Pause()
                    self._is_paused = True
                    return True
                except Exception as e:
                    logging.error(f"Error pausing SAPI voice: {e}")
                    return False

    def resume(self) -> bool:
        """Resume speech playback if currently paused."""
        if not self._is_paused:
            return False

        if self._is_external_speaking:
            try:
                self._winmm.mciSendStringW(f"resume {self._mci_alias}", None, 0, 0)
                self._is_paused = False
                return True
            except Exception as e:
                logging.error(f"Error resuming MCI playback: {e}")
                return False
        else:
            with self._lock:
                try:
                    pythoncom.CoInitialize()
                    self._voice.Resume()
                    self._is_paused = False
                    return True
                except Exception as e:
                    logging.error(f"Error resuming SAPI voice: {e}")
                    return False

    def toggle_pause(self) -> bool:
        """Toggle between paused and resumed states. Return True if paused, False if resumed/inactive."""
        if self._is_paused:
            self.resume()
            return False
        elif self.is_speaking():
            self.pause()
            return True
        return False

    def get_last_word_index(self) -> int:
        """Return the last known word index."""
        return self._last_word_index

    def get_current_word_index(self, doc: Any = None) -> int:
        """Return the current word index being spoken or last reached."""
        if doc is None or getattr(doc, "total_words", 0) == 0:
            return self._last_word_index

        if self._is_external_speaking:
            buf = ctypes.create_unicode_buffer(128)
            self._winmm.mciSendStringW(f"status {self._mci_alias} position", buf, 128, 0)
            try:
                pos_ms = int(buf.value)
                if not self._word_timestamps and self._audio_duration_ms > 0:
                    self._word_timestamps = doc.get_word_timestamps(self._audio_duration_ms)
                if self._word_timestamps:
                    idx = bisect.bisect_right(self._word_timestamps, pos_ms) - 1
                    idx = max(0, min(idx, doc.total_words - 1))
                    self._last_word_index = idx
            except Exception:
                pass
            return self._last_word_index

        with self._lock:
            try:
                if self._voice.Status.RunningState == 2:
                    char_offset = self._sapi_base_char_offset + self._voice.Status.InputWordPosition
                    self._last_word_index = doc.get_word_index_by_char_offset(char_offset)
            except Exception:
                pass
        return self._last_word_index

    def seek_and_play(self, doc: Any, word_index: int) -> bool:
        """Seek speech to target word index and resume playback."""
        if doc is None or getattr(doc, "total_words", 0) == 0:
            return False

        clamped_idx = doc.clamp_word_index(word_index)
        self._last_word_index = clamped_idx

        # Hebrew (MCI audio)
        if self.is_hebrew(doc.raw_text):
            if self._current_audio_file and os.path.exists(self._current_audio_file):
                if not self._word_timestamps and self._audio_duration_ms > 0:
                    self._word_timestamps = doc.get_word_timestamps(self._audio_duration_ms)
                target_ms = 0
                if self._word_timestamps and clamped_idx < len(self._word_timestamps):
                    target_ms = self._word_timestamps[clamped_idx]
                self._stop_event.clear()
                self._winmm.mciSendStringW(f"play {self._mci_alias} from {target_ms}", None, 0, 0)
                self._is_external_speaking = True
                self._is_paused = False
                return True
            else:
                char_offset = doc.get_char_offset_for_word_index(clamped_idx)
                return self.speak(doc.raw_text[char_offset:], async_mode=True)

        # English (SAPI)
        char_offset = doc.get_char_offset_for_word_index(clamped_idx)
        self._sapi_base_char_offset = char_offset
        slice_text = doc.raw_text[char_offset:]
        with self._lock:
            pythoncom.CoInitialize()
            try:
                self._voice.Resume()
            except Exception:
                pass
            self._voice.Speak(slice_text, SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)
        self._is_paused = False
        return True

    def _cleanup_audio_file(self) -> None:
        """Close MCI device and remove temporary MP3 file."""
        if self._current_audio_file:
            try:
                self._winmm.mciSendStringW(f"close {self._mci_alias}", None, 0, 0)
            except Exception:
                pass
            try:
                if os.path.exists(self._current_audio_file):
                    os.remove(self._current_audio_file)
            except Exception:
                pass
            self._current_audio_file = None
            self._audio_duration_ms = 0
            self._word_timestamps = []

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

            self._current_audio_file = file_path

            # Query total length in milliseconds
            len_buf = ctypes.create_unicode_buffer(128)
            mci(f"status {self._mci_alias} length", len_buf, 128, 0)
            try:
                self._audio_duration_ms = int(len_buf.value)
            except Exception:
                self._audio_duration_ms = 0

            # Start playback
            mci(f"play {self._mci_alias}", None, 0, 0)
            self._is_external_speaking = True

            # Poll status until finished or stopped
            status_buf = ctypes.create_unicode_buffer(128)
            while not self._stop_event.is_set():
                mci(f"status {self._mci_alias} mode", status_buf, 128, 0)
                mode = status_buf.value.lower()
                if mode != "playing" and mode != "paused":
                    break
                self._stop_event.wait(0.08)

        except Exception as e:
            logging.error(f"Error in MCI audio playback: {e}")
        finally:
            self._is_external_speaking = False

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
        if clean_text != self._current_text:
            self._cleanup_audio_file()
            self._current_text = clean_text
            self._sapi_base_char_offset = 0
            self._last_word_index = 0

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
        self._is_paused = False
        if self._is_external_speaking:
            try:
                self._winmm.mciSendStringW(f"stop {self._mci_alias}", None, 0, 0)
            except Exception:
                pass
            self._is_external_speaking = False

        with self._lock:
            pythoncom.CoInitialize()
            try:
                self._voice.Resume()
            except Exception:
                pass
            self._voice.Speak("", SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)

    def cleanup(self) -> None:
        """Clean up audio devices and temporary files."""
        self.stop()
        self._cleanup_audio_file()
