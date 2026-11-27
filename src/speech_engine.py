import threading
import asyncio
import os
import re
import tempfile
import ctypes
import logging
import bisect
import queue
from typing import List, Optional, Any, Tuple
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

# Default natural neural voices
DEFAULT_HEBREW_VOICE = "he-IL-HilaNeural"
DEFAULT_ENGLISH_NEURAL_VOICE = "en-US-JennyNeural"


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
        self._pipeline_phrases: List[Tuple[str, str]] = []
        self._pipeline_phrase_word_indices: List[int] = []
        self._pipeline_active_index: int = 0

    def is_hebrew(self, text: Optional[str]) -> bool:
        """Return True if text contains any Hebrew characters (Unicode ֐-׿)."""
        if not text:
            return False
        return any("֐" <= c <= "׿" for c in text)

    def segment_bilingual_text(self, text: str) -> List[Tuple[str, str]]:
        """Segments text into language blocks ('he' or 'en') for authentic native pronunciation.
        Returns a list of (lang, text) tuples.
        """
        if not text or not text.strip():
            return []

        tokens = re.findall(r"\w+|[^\w\s]+|\s+", text, re.UNICODE)
        segments: List[Tuple[str, str]] = []

        current_lang = None
        current_text = []

        for token in tokens:
            has_heb = any("֐" <= c <= "׿" for c in token)
            has_lat = any(("a" <= c <= "z") or ("A" <= c <= "Z") for c in token)

            if has_heb:
                token_lang = "he"
            elif has_lat:
                token_lang = "en"
            else:
                token_lang = None  # Neutral (punctuation, numbers, spaces)

            if current_lang is None:
                if token_lang is not None:
                    current_lang = token_lang
                current_text.append(token)
            else:
                if token_lang is None or token_lang == current_lang:
                    current_text.append(token)
                else:
                    # Switch language boundary
                    segments.append((current_lang, "".join(current_text)))
                    current_lang = token_lang
                    current_text = [token]

        if current_text:
            segments.append((current_lang or "he", "".join(current_text)))

        return segments

    def segment_phrased_bilingual(self, text: str, max_words: int = 5) -> List[Tuple[str, str]]:
        """Splits text into short bite-sized phrases (typically 3-5 words) broken along natural
        clause boundaries (. , ! ? ; : \n), retaining native language attribution ('he' or 'en').
        Small adjacent clauses are merged up to max_words to maintain natural rhythm.
        This enables rapid-start pipelined playback and high responsiveness to stop/speed controls.
        """
        if not text or not text.strip():
            return []

        raw_clauses = re.split(r"([.!?:;\n]+|,\s*)", text)
        clauses = []
        i = 0
        while i < len(raw_clauses):
            part = raw_clauses[i]
            delim = raw_clauses[i + 1] if i + 1 < len(raw_clauses) else ""
            c = (part + delim).strip()
            if c:
                clauses.append(c)
            i += 2

        bounded_clauses = []
        for c in clauses:
            words = c.split()
            if len(words) <= max_words:
                bounded_clauses.append(c)
            else:
                for k in range(0, len(words), max_words):
                    sub = " ".join(words[k : k + max_words])
                    if sub:
                        bounded_clauses.append(sub)

        # Merge small adjacent fragments up to max_words to avoid single-word network roundtrips
        merged = []
        cur_chunks = []
        for bc in bounded_clauses:
            w_count = len(bc.split())
            cur_count = sum(len(x.split()) for x in cur_chunks)
            if not cur_chunks:
                cur_chunks.append(bc)
            elif cur_count + w_count <= max_words:
                cur_chunks.append(bc)
            else:
                merged.append(" ".join(cur_chunks))
                cur_chunks = [bc]
        if cur_chunks:
            merged.append(" ".join(cur_chunks))

        segments: List[Tuple[str, str]] = []
        for ch in merged:
            has_heb = any("֐" <= c <= "׿" for c in ch)
            has_lat = any(("a" <= c <= "z") or ("A" <= c <= "Z") for c in ch)

            if has_heb and not has_lat:
                segments.append(("he", ch))
            elif has_lat and not has_heb:
                segments.append(("en", ch))
            else:
                sub_segs = self.segment_bilingual_text(ch)
                for lang, txt in sub_segs:
                    clean = txt.strip()
                    if clean:
                        segments.append((lang, clean))

        return [(lang, txt.strip()) for lang, txt in segments if txt.strip()]

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
            base_idx = 0
            if (
                self._pipeline_phrase_word_indices
                and 0 <= self._pipeline_active_index < len(self._pipeline_phrase_word_indices)
            ):
                base_idx = self._pipeline_phrase_word_indices[self._pipeline_active_index]

            buf = ctypes.create_unicode_buffer(128)
            self._winmm.mciSendStringW(f"status {self._mci_alias} position", buf, 128, 0)
            try:
                pos_ms = int(buf.value)
                if not self._word_timestamps and self._audio_duration_ms > 0:
                    self._word_timestamps = doc.get_word_timestamps(self._audio_duration_ms)
                if self._word_timestamps:
                    idx = bisect.bisect_right(self._word_timestamps, pos_ms) - 1
                    idx = max(0, min(idx, doc.total_words - 1))
                    self._last_word_index = max(base_idx, idx)
                else:
                    self._last_word_index = base_idx
            except Exception:
                self._last_word_index = base_idx
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
                self._stop_event.wait(0.05)

        except Exception as e:
            logging.error(f"Error in MCI audio playback: {e}")
        finally:
            try:
                self._winmm.mciSendStringW(f"close {self._mci_alias}", None, 0, 0)
            except Exception:
                pass

    async def _download_segment_audio(self, text_chunk: str, voice_name: str, rate_str: str) -> bytes:
        """Download raw MP3 audio bytes for a single speech segment."""
        communicate = edge_tts.Communicate(text_chunk, voice_name, rate=rate_str)
        audio_chunks = []
        async for chunk in communicate.stream():
            if self._stop_event.is_set():
                return b""
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)

    async def _download_phrase_pipeline_worker(
        self,
        phrases: List[Tuple[str, str]],
        audio_queue: "queue.Queue",
        created_files: List[str],
    ) -> None:
        """Background coroutine that synthesizes phrases ahead of playback.
        Dynamically applies speed adjustments (rate_str) to upcoming phrases.
        """
        for idx, (lang, text_chunk) in enumerate(phrases):
            if self._stop_event.is_set():
                break

            rate_val = self.get_rate()
            rate_str = f"{rate_val * 5:+d}%" if rate_val != 0 else "+0%"
            voice = DEFAULT_HEBREW_VOICE if lang == "he" else DEFAULT_ENGLISH_NEURAL_VOICE

            data = await self._download_segment_audio(text_chunk, voice, rate_str)
            if self._stop_event.is_set():
                break

            if data:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    file_path = f.name
                    f.write(data)
                created_files.append(file_path)
                audio_queue.put((idx, file_path))

        audio_queue.put(None)

    def _speak_hebrew_worker(self, text: str) -> None:
        """Pipelined neural speech playback:
        1. Breaks text into natural 3-5 word phrases.
        2. Starts playing the 1st phrase immediately (~0.8s) while fetching future phrases in background.
        3. Remains instantly responsive to Stop (Ctrl+Alt+R), Pause (Ctrl+Alt+Space), and Speed (Ctrl+Alt+Up/Down).
        """
        created_files: List[str] = []
        audio_queue: queue.Queue = queue.Queue(maxsize=3)

        try:
            self._stop_event.clear()
            self._is_external_speaking = True

            phrases = self.segment_phrased_bilingual(text, max_words=5)
            if not phrases:
                return

            self._pipeline_phrases = phrases
            # Map word indices for navigation tracking
            self._pipeline_phrase_word_indices = []
            accumulated_words = 0
            for _, p_text in phrases:
                self._pipeline_phrase_word_indices.append(accumulated_words)
                accumulated_words += len(p_text.split())

            def download_thread_target():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self._download_phrase_pipeline_worker(phrases, audio_queue, created_files)
                    )
                finally:
                    try:
                        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
                        for t in tasks:
                            t.cancel()
                        if tasks:
                            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                        loop.run_until_complete(asyncio.sleep(0.05))
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    loop.close()

            dl_thread = threading.Thread(
                target=download_thread_target,
                daemon=True,
                name="HebrewPipelineDownloader",
            )
            dl_thread.start()

            # Play phrases sequentially as they arrive from the download pipeline
            while not self._stop_event.is_set():
                try:
                    item = audio_queue.get(timeout=0.2)
                except queue.Empty:
                    if not dl_thread.is_alive():
                        break
                    continue

                if item is None:
                    # Pipeline completed
                    break

                phrase_idx, file_path = item
                if self._stop_event.is_set():
                    break

                self._pipeline_active_index = phrase_idx
                self._play_audio_file(file_path)

        except Exception as e:
            logging.error(f"Pipelined neural TTS failed: {e}. Falling back to SAPI.")
            self._is_external_speaking = False
            with self._lock:
                pythoncom.CoInitialize()
                self._voice.Speak(text, SVS_PURGE_BEFORE_SPEAK | SVS_FLAGS_ASYNC)
        finally:
            self._is_external_speaking = False
            # Clean up temporary phrase files
            for fp in created_files:
                try:
                    if os.path.exists(fp):
                        os.remove(fp)
                except Exception:
                    pass

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
