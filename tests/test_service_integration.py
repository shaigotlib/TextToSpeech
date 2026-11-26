import unittest
import time
from unittest.mock import MagicMock, patch
from src.read_aloud_service import (
    ReadAloudService,
    HOTKEY_ID_READ,
    HOTKEY_ID_PAUSE,
    HOTKEY_ID_SPEED_UP,
    HOTKEY_ID_SPEED_DOWN,
    HOTKEY_ID_SKIP_FORWARD,
    HOTKEY_ID_SKIP_BACKWARD,
)

class TestReadAloudServiceIntegration(unittest.TestCase):
    def setUp(self):
        self.mock_engine = MagicMock()
        self.mock_capturer = MagicMock()
        self.mock_hotkey = MagicMock()
        self.service = ReadAloudService(
            engine=self.mock_engine,
            capturer=self.mock_capturer,
            hotkey_mgr=self.mock_hotkey,
            feedback_beeps=False,
            debounce_delay=0.05,
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
        # Pressing Ctrl+Alt+R while speech is active cancels speech
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

    def test_pause_and_resume_hotkey(self):
        # Case 1: Currently speaking -> should pause
        self.mock_engine.is_paused.return_value = False
        self.mock_engine.is_speaking.return_value = True
        self.service.on_pause_pressed()
        self.mock_engine.pause.assert_called_once()

        # Case 2: Currently paused -> should resume
        self.mock_engine.is_paused.return_value = True
        self.service.on_pause_pressed()
        self.mock_engine.resume.assert_called_once()

    def test_speed_up_and_down_hotkeys(self):
        self.mock_engine.get_rate.return_value = 0
        self.service.on_speed_up_pressed()
        self.mock_engine.set_rate.assert_called_with(1)

        self.mock_engine.get_rate.return_value = 2
        self.service.on_speed_down_pressed()
        self.mock_engine.set_rate.assert_called_with(1)

    def test_service_start_registers_base_four_hotkeys_and_navigation_when_reading(self):
        # On start, base hotkeys (Read, Pause, Speed Up, Speed Down, Passthrough Toggle x2 for ANSI & ISO) are registered
        self.service.start()
        self.assertTrue(self.service.is_active())
        self.assertEqual(self.mock_hotkey.add_hotkey.call_count, 6)
        self.assertFalse(self.service.is_navigation_hooked())

        # When reading text, navigation hotkeys are dynamically hooked
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "Word one word two"
        self.service.on_hotkey_pressed()
        self.assertTrue(self.service.is_navigation_hooked())
        # Total hotkey additions now 8 (6 base + 2 navigation)
        self.assertEqual(self.mock_hotkey.add_hotkey.call_count, 8)

        # When speech stops, navigation hotkeys remain hooked while document is active
        self.mock_engine.is_speaking.return_value = True
        self.service.on_hotkey_pressed()
        self.assertTrue(self.service.is_navigation_hooked())

        # When service stops, everything unhooks
        self.service.stop()
        self.assertFalse(self.service.is_active())
        self.assertFalse(self.service.is_navigation_hooked())

    def test_release_navigation_unhooks_arrows_and_clears_doc(self):
        self.service.start()
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "Test word navigation release"
        self.service.on_hotkey_pressed()
        self.assertTrue(self.service.is_navigation_hooked())

        # Calling release_navigation unhooks the arrows and clears document
        self.service.release_navigation()
        self.assertFalse(self.service.is_navigation_hooked())
        self.assertIsNone(self.service.get_current_doc())
        self.service.stop()

    def test_skip_forward_and_backward_navigation(self):
        # First capture text
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "One two three four five six"
        self.service.on_hotkey_pressed()

        # Simulate currently at word index 1 ("two")
        self.mock_engine.get_current_word_index.return_value = 1

        # Press skip forward (+1)
        self.service.on_skip_forward_pressed()
        time.sleep(0.08)

        # Should have sought to word index 2 ("three")
        self.mock_engine.seek_and_play.assert_called_with(self.service.get_current_doc(), 2)

        # Press skip backward (-1)
        self.mock_engine.get_current_word_index.return_value = 2
        self.service.on_skip_backward_pressed()
        time.sleep(0.08)

        # Should have sought back to word index 1 ("two")
        self.mock_engine.seek_and_play.assert_called_with(self.service.get_current_doc(), 1)

    def test_sequence_of_clicks_accumulates(self):
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "One two three four five six"
        self.service.on_hotkey_pressed()

        # Currently at word 1
        self.mock_engine.get_current_word_index.return_value = 1

        # Rapid sequence of 3 forward clicks
        self.service.on_skip_forward_pressed()
        time.sleep(0.01)
        self.service.on_skip_forward_pressed()
        time.sleep(0.01)
        self.service.on_skip_forward_pressed()

        # Wait for debounce to flush
        time.sleep(0.08)

        # 1 + 3 = 4 ("five")
        self.mock_engine.seek_and_play.assert_called_once_with(self.service.get_current_doc(), 4)

    def test_moving_back_up_until_new_text_is_selected(self):
        # 1. Capture and read first text
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "Alpha beta gamma delta epsilon"
        self.service.on_hotkey_pressed()
        doc1 = self.service.get_current_doc()
        self.assertIsNotNone(doc1)

        # 2. Speech finishes, engine is stopped or idle at the last word
        self.mock_engine.is_speaking.return_value = False
        self.mock_engine.get_current_word_index.return_value = 4  # "epsilon"

        # 3. User navigates back without selecting new text
        self.service.on_skip_backward_pressed()
        time.sleep(0.08)

        # It should seek backward in doc1 (4 - 1 = 3 -> "delta")
        self.mock_engine.seek_and_play.assert_called_with(doc1, 3)

        # 4. User selects NEW text
        self.mock_capturer.get_selected_text.return_value = "New text selected"
        self.service.on_hotkey_pressed()
        doc2 = self.service.get_current_doc()
        self.assertIsNotNone(doc2)
        self.assertNotEqual(doc1, doc2)
        self.assertEqual(doc2.spans[0].text, "New")

    def test_passthrough_toggle_releases_and_restores_shortcuts(self):
        # On start, 5 base shortcuts are registered (Read, Pause, SpeedUp, SpeedDown, and TogglePassthrough)
        self.service.start()
        self.assertFalse(self.service.is_passthrough_active())

        # When passthrough toggle is pressed (Ctrl+Alt+\):
        # All hotkeys except Ctrl+Alt+\ are removed from hotkey_mgr so focused app gets them
        self.service.on_toggle_passthrough_pressed()
        self.assertTrue(self.service.is_passthrough_active())

        # Verify that hotkey_mgr was instructed to remove the functional hotkeys
        self.mock_hotkey.remove_hotkey.assert_any_call(HOTKEY_ID_READ)
        self.mock_hotkey.remove_hotkey.assert_any_call(HOTKEY_ID_PAUSE)
        self.mock_hotkey.remove_hotkey.assert_any_call(HOTKEY_ID_SPEED_UP)
        self.mock_hotkey.remove_hotkey.assert_any_call(HOTKEY_ID_SPEED_DOWN)

        # Pressing Ctrl+Alt+\ again re-enables all hotkeys
        self.service.on_toggle_passthrough_pressed()
        self.assertFalse(self.service.is_passthrough_active())
        # The base hotkeys should have been re-added
        self.assertTrue(self.mock_hotkey.add_hotkey.call_count >= 5)
        self.service.stop()

    def test_hebrew_navigation_behavior_parity(self):
        # Hebrew text is treated identically (Right = forward, Left = backward in reading order)
        self.mock_engine.is_speaking.return_value = False
        self.mock_capturer.get_selected_text.return_value = "שלום עולם זהו מבחן"
        self.service.on_hotkey_pressed()

        self.mock_engine.get_current_word_index.return_value = 0
        self.service.on_skip_forward_pressed()
        time.sleep(0.08)

        # Word 1 ("עולם")
        self.mock_engine.seek_and_play.assert_called_with(self.service.get_current_doc(), 1)


if __name__ == '__main__':
    unittest.main()

