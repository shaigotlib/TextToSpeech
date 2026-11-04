import unittest
import time
from src.hotkey_manager import HotkeyManager, MOD_CONTROL, MOD_ALT, MOD_SHIFT

class TestHotkeyManager(unittest.TestCase):
    def test_hotkey_constants(self):
        self.assertEqual(MOD_CONTROL, 0x0002)
        self.assertEqual(MOD_ALT, 0x0001)
        self.assertEqual(MOD_SHIFT, 0x0004)

    def test_registration_and_callback_storage(self):
        manager = HotkeyManager()
        called = []
        def dummy_cb():
            called.append(True)

        # Register Ctrl+Shift+R (ord('R') == 0x52)
        success = manager.add_hotkey(hotkey_id=1, modifiers=MOD_CONTROL | MOD_SHIFT, vk_code=ord('R'), callback=dummy_cb)
        self.assertTrue(success)
        self.assertIn(1, manager._hotkeys)
        self.assertEqual(manager._hotkeys[1]['callback'], dummy_cb)

        # Trigger callback directly via internal dispatcher
        manager._dispatch(1)
        self.assertEqual(len(called), 1)

    def test_remove_hotkey(self):
        manager = HotkeyManager()
        manager.add_hotkey(1, MOD_CONTROL, ord('R'), lambda: None)
        self.assertIn(1, manager._hotkeys)
        manager.remove_hotkey(1)
        self.assertNotIn(1, manager._hotkeys)

    def test_lifecycle_start_stop(self):
        manager = HotkeyManager()
        manager.add_hotkey(1, MOD_CONTROL, ord('R'), lambda: None)
        manager.start()
        self.assertTrue(manager.is_running())
        time.sleep(0.1)
        manager.stop()
        self.assertFalse(manager.is_running())

if __name__ == '__main__':
    unittest.main()
