import unittest
import time
from src.speech_engine import SpeechEngine

class TestSpeechEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SpeechEngine()

    def test_initialization(self):
        self.assertIsNotNone(self.engine)
        self.assertFalse(self.engine.is_speaking())

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
        self.assertFalse(self.engine.is_hebrew("1234567890"))
        self.assertFalse(self.engine.is_hebrew(""))

if __name__ == '__main__':
    unittest.main()
