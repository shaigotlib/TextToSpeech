import unittest
from unittest.mock import MagicMock, patch
from src.read_aloud_service import ReadAloudService

class TestReadAloudServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_hotkey = MagicMock()
        self.service = ReadAloudService(
            engine=self.mock_engine,
            capturer=self.mock_capturer,
            hotkey_mgr=self.mock_hotkey
        )

    def test_hotkey_when_idle_and_text_selected(self):
        # When engine is not speaking and text is highlighted
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "Important text in email"

        self.service.on_hotkey_pressed()

        self.mock_engine.is_speaking.assert_called()
        self.mock_capturer.get_selected_text.assert_called_once()
        self.mock_engine.speak.assert_called_once_with("Important text in email", async_mode=True)

    def test_hotkey_when_already_speaking_stops_speech(self):
        # Pressing Ctrl+R while speech is active cancels speech
        self.mock_engine.is_speaking.return_value = True

        self.service.on_hotkey_pressed()

        self.mock_engine.stop.assert_called_once()
        self.mock_capturer.get_selected_text.assert_not_called()
        self.mock_engine.speak.assert_not_called()

    def test_hotkey_when_no_text_selected(self):
        # When nothing is highlighted, does not call speak
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = ""

        self.service.on_hotkey_pressed()

        self.mock_engine.speak.assert_not_called()

    def test_service_start_and_stop(self):
        self.service.start()
        self.assertTrue(self.service.is_active())
        self.mock_hotkey.add_hotkey.assert_called()
        self.mock_hotkey.start.assert_called_once()

        self.service.stop()
        self.assertFalse(self.service.is_active())
        self.mock_hotkey.stop.assert_called_once()
        self.mock_engine.stop.assert_called()

if __name__ == '__main__':
    unittest.main()
