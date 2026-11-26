import unittest
import time
from src.speech_engine import SpeechEngine

class TestSpeechEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SpeechEngine()

    def test_initialization(self):
        self.assertIsNotNone(self.engine)
        self.assertFalse(self.engine.is_speaking())
        self.assertFalse(self.engine.is_paused())

    def test_voice_enumeration(self):
        voices = self.engine.get_voices()
        self.assertIsInstance(voices, list)
        self.assertGreater(len(voices), 0, "Windows SAPI should have at least one installed voice")

    def test_rate_bounds(self):
        self.engine.set_rate(0)
        self.assertEqual(self.engine.get_rate(), 0)
        self.engine.set_rate(10)
        self.assertEqual(self.engine.get_rate(), 10)
        self.engine.set_rate(-10)
        self.assertEqual(self.engine.get_rate(), -10)
        # Clamping
        self.engine.set_rate(15)
        self.assertEqual(self.engine.get_rate(), 10)
        self.engine.set_rate(-15)
        self.assertEqual(self.engine.get_rate(), -10)

    def test_volume_bounds(self):
        self.engine.set_volume(50)
        self.assertEqual(self.engine.get_volume(), 50)
        self.engine.set_volume(100)
        self.assertEqual(self.engine.get_volume(), 100)
        # Clamping
        self.engine.set_volume(150)
        self.assertEqual(self.engine.get_volume(), 100)
        self.engine.set_volume(-10)
        self.assertEqual(self.engine.get_volume(), 0)

    def test_speak_and_stop(self):
        # Async speak should not block
        result = self.engine.speak("Testing speech engine functionality", async_mode=True)
        self.assertTrue(result)
        # Stop speech immediately
        self.engine.stop()
        self.assertFalse(self.engine.is_speaking())
        self.assertFalse(self.engine.is_paused())

    def test_pause_and_resume_state(self):
        self.engine.speak("Testing pause and resume state tracking in speech engine", async_mode=True)
        time.sleep(0.05)
        # When speaking, pause can be called
        self.engine.pause()
        self.assertTrue(self.engine.is_paused())
        # Resume
        self.engine.resume()
        self.assertFalse(self.engine.is_paused())
        # Stop cleans up pause state
        self.engine.stop()
        self.assertFalse(self.engine.is_paused())

    def test_speak_empty_string(self):
        # Speaking whitespace or empty string returns False without speaking
        result = self.engine.speak("   ")
        self.assertFalse(result)
        self.assertFalse(self.engine.is_speaking())

    def test_voice_selection(self):
        voices = self.engine.get_voices()
        first_voice = voices[0]
        res = self.engine.set_voice_by_name(first_voice)
        self.assertTrue(res)

    def test_hebrew_detection(self):
        self.assertTrue(self.engine.is_hebrew("שלום עולם"))
        self.assertTrue(self.engine.is_hebrew("Status: השרת פעיל"))
        self.assertFalse(self.engine.is_hebrew("Hello world!"))

    def test_bilingual_text_segmentation(self):
        mixed = "שלום לכולם, welcome to our test! הנה עוד משפט."
        segments = self.engine.segment_bilingual_text(mixed)
        # Should produce segmented blocks with appropriate language tags
        self.assertGreaterEqual(len(segments), 3)
        self.assertEqual(segments[0][0], "he")
        self.assertIn("שלום", segments[0][1])
        self.assertEqual(segments[1][0], "en")
        self.assertIn("welcome", segments[1][1])
        self.assertEqual(segments[2][0], "he")
        self.assertIn("הנה", segments[2][1])

    def test_word_index_and_seek_english(self):
        from src.text_model import TextDocument
        doc = TextDocument("First second third fourth fifth sixth")
        self.engine.speak(doc.raw_text, async_mode=True)
        time.sleep(0.05)

        # Current word index should be an integer within [0, doc.total_words - 1]
        idx = self.engine.get_current_word_index(doc)
        self.assertIsInstance(idx, int)
        self.assertTrue(0 <= idx < doc.total_words)

        # Seek to word 2 ("third")
        seek_res = self.engine.seek_and_play(doc, 2)
        self.assertTrue(seek_res)
        self.assertEqual(self.engine.get_last_word_index(), 2)

        self.engine.stop()
        self.assertFalse(self.engine.is_speaking())

    def test_seek_clamps_out_of_bounds(self):
        from src.text_model import TextDocument
        doc = TextDocument("One two three")
        # Seeking beyond bounds clamps
        self.engine.seek_and_play(doc, 100)
        self.assertEqual(self.engine.get_last_word_index(), 2)

        self.engine.seek_and_play(doc, -10)
        self.assertEqual(self.engine.get_last_word_index(), 0)
        self.engine.stop()
        self.assertFalse(self.engine.is_hebrew("1234567890"))
        self.assertFalse(self.engine.is_hebrew(""))

if __name__ == '__main__':
    unittest.main()
