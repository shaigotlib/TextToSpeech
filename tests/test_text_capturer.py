import unittest
import time
from src.text_capturer import TextCapturer

class TestTextCapturer(unittest.TestCase):
    def setUp(self):
        self.capturer = TextCapturer()

    def test_backup_and_restore_clipboard_text(self):
        # Set known initial clipboard content
        initial_content = "Precious clipboard text that must not be lost 12345! @#$"
        self.capturer.set_clipboard_text(initial_content)

        # Backup
        backup = self.capturer.backup_clipboard()
        self.assertEqual(backup.get('text'), initial_content)

        # Modify clipboard to simulate simulated copy
        self.capturer.set_clipboard_text("Temporary selected text")
        self.assertEqual(self.capturer.get_clipboard_text(), "Temporary selected text")

        # Restore
        success = self.capturer.restore_clipboard(backup)
        self.assertTrue(success)
        self.assertEqual(self.capturer.get_clipboard_text(), initial_content)

    def test_backup_empty_clipboard(self):
        # Even if clipboard has empty or non-text content, backup should not fail
        backup = self.capturer.backup_clipboard()
        self.assertIsInstance(backup, dict)
        self.assertIn('text', backup)

    def test_clean_text(self):
        raw = "   \r\nHello \t world!   \n\r"
        cleaned = self.capturer.clean_text(raw)
        self.assertEqual(cleaned, "Hello \t world!")

    def test_clean_empty_text(self):
        self.assertEqual(self.capturer.clean_text(""), "")
        self.assertEqual(self.capturer.clean_text("   \r\n   "), "")

    def test_has_speakable_content(self):
        self.assertTrue(self.capturer.has_speakable_content("Hello PowerShell"))
        self.assertTrue(self.capturer.has_speakable_content("123"))
        self.assertFalse(self.capturer.has_speakable_content(""))
        self.assertFalse(self.capturer.has_speakable_content("   \r\n\t  "))
        self.assertFalse(self.capturer.has_speakable_content("\x03"))
        self.assertFalse(self.capturer.has_speakable_content("\x12"))

    def test_is_terminal_window(self):
        self.assertTrue(self.capturer.is_terminal_class("CASCADIA_HOSTING_WINDOW_CLASS"))
        self.assertTrue(self.capturer.is_terminal_class("ConsoleWindowClass"))
        self.assertTrue(self.capturer.is_terminal_class("PseudoConsoleWindow"))
        self.assertFalse(self.capturer.is_terminal_class("Notepad"))
        self.assertFalse(self.capturer.is_terminal_class("Chrome_WidgetWin_1"))
        self.assertFalse(self.capturer.is_terminal_class("rctrl_renwnd32"))  # Outlook

if __name__ == '__main__':
    unittest.main()
