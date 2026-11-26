import unittest
import time
import win32con
import win32api
from src.hotkey_manager import (
    HotkeyManager,
    MOD_CONTROL,
    MOD_ALT,
    MOD_SHIFT,
    VK_SPACE,
    VK_LEFT,
    VK_UP,
    VK_RIGHT,
    VK_DOWN,
    VK_OEM_5,
    PBT_APMRESUMEAUTOMATIC,
    PBT_APMRESUMESUSPEND,
    WM_WTSSESSION_CHANGE,
    WTS_SESSION_UNLOCK,
    WTS_SESSION_LOGON,
    vk_to_key_str,
)

class TestHotkeyManager(unittest.TestCase):
    def test_hotkey_constants(self):
        self.assertEqual(MOD_CONTROL, 0x0002)
        self.assertEqual(MOD_ALT, 0x0001)
        self.assertEqual(MOD_SHIFT, 0x0004)
        self.assertEqual(VK_SPACE, 0x20)
        self.assertEqual(VK_LEFT, 0x25)
        self.assertEqual(VK_UP, 0x26)
        self.assertEqual(VK_RIGHT, 0x27)
        self.assertEqual(VK_DOWN, 0x28)
        self.assertEqual(VK_OEM_5, 0xDC)

    def test_vk_to_key_str(self):
        self.assertEqual(vk_to_key_str(VK_SPACE), "space")
        self.assertEqual(vk_to_key_str(VK_LEFT), "left")
        self.assertEqual(vk_to_key_str(VK_UP), "up")
        self.assertEqual(vk_to_key_str(VK_RIGHT), "right")
        self.assertEqual(vk_to_key_str(VK_DOWN), "down")
        self.assertEqual(vk_to_key_str(VK_OEM_5), "\\")
        self.assertEqual(vk_to_key_str(ord("R")), "r")

    def test_registration_and_callback_storage(self):
        manager = HotkeyManager()
        called = []
        def dummy_cb():
            called.append(True)

        # Register Ctrl+Alt+R (ord('R') == 0x52)
        success = manager.add_hotkey(hotkey_id=1, modifiers=MOD_CONTROL | MOD_ALT, vk_code=ord('R'), callback=dummy_cb)
        self.assertTrue(success)
        self.assertIn(1, manager._hotkeys)
        self.assertEqual(manager._hotkeys[1]['callback'], dummy_cb)
        self.assertEqual(manager._hotkeys[1]['hotkey_str'], "ctrl+alt+r")

        # Trigger callback directly via internal dispatcher
        manager._dispatch(1)
        time.sleep(0.05)
        self.assertEqual(len(called), 1)

    def test_multiple_hotkeys_registration(self):
        manager = HotkeyManager()
        manager.add_hotkey(1, MOD_CONTROL | MOD_ALT, ord('R'), lambda: None)
        manager.add_hotkey(2, MOD_CONTROL | MOD_ALT, VK_SPACE, lambda: None)
        manager.add_hotkey(3, MOD_CONTROL | MOD_ALT, VK_UP, lambda: None)
        manager.add_hotkey(4, MOD_CONTROL | MOD_ALT, VK_DOWN, lambda: None)
        manager.add_hotkey(5, MOD_CONTROL | MOD_ALT, VK_RIGHT, lambda: None)
        manager.add_hotkey(6, MOD_CONTROL | MOD_ALT, VK_LEFT, lambda: None)

        self.assertEqual(len(manager._hotkeys), 6)
        self.assertEqual(manager._hotkeys[1]['hotkey_str'], "ctrl+alt+r")
        self.assertEqual(manager._hotkeys[2]['hotkey_str'], "ctrl+alt+space")
        self.assertEqual(manager._hotkeys[3]['hotkey_str'], "ctrl+alt+up")
        self.assertEqual(manager._hotkeys[4]['hotkey_str'], "ctrl+alt+down")
        self.assertEqual(manager._hotkeys[5]['hotkey_str'], "ctrl+alt+right")
        self.assertEqual(manager._hotkeys[6]['hotkey_str'], "ctrl+alt+left")

    def test_remove_hotkey(self):
        manager = HotkeyManager()
        manager.add_hotkey(1, MOD_CONTROL | MOD_ALT, ord('R'), lambda: None)
        self.assertIn(1, manager._hotkeys)
        manager.remove_hotkey(1)
        self.assertNotIn(1, manager._hotkeys)

    def test_lifecycle_start_stop(self):
        manager = HotkeyManager()
        VK_F12 = 0x7B
        manager.add_hotkey(1, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_F12, lambda: None)
        manager.start()
        self.assertTrue(manager.is_running())
        self.assertTrue(manager._hotkeys[1].get('registered', False))
        time.sleep(0.1)
        manager.stop()
        self.assertFalse(manager.is_running())

    def test_power_resume_triggers_reregistration(self):
        manager = HotkeyManager()
        VK_F12 = 0x7B
        manager.add_hotkey(1, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_F12, lambda: None)
        manager.start()
        self.assertTrue(manager.is_running())

        # Simulate Windows WM_POWERBROADCAST (PBT_APMRESUMEAUTOMATIC)
        hwnd = manager._hwnd
        self.assertIsNotNone(hwnd)
        win32api.PostMessage(hwnd, win32con.WM_POWERBROADCAST, PBT_APMRESUMEAUTOMATIC, 0)
        time.sleep(0.1)

        self.assertTrue(manager._hotkeys[1].get('registered', False))
        manager.stop()

    def test_session_unlock_triggers_reregistration(self):
        manager = HotkeyManager()
        VK_F12 = 0x7B
        manager.add_hotkey(1, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_F12, lambda: None)
        manager.start()
        self.assertTrue(manager.is_running())

        # Simulate Windows WM_WTSSESSION_CHANGE (WTS_SESSION_UNLOCK)
        hwnd = manager._hwnd
        self.assertIsNotNone(hwnd)
        win32api.PostMessage(hwnd, WM_WTSSESSION_CHANGE, WTS_SESSION_UNLOCK, 0)
        time.sleep(0.1)

        self.assertTrue(manager._hotkeys[1].get('registered', False))
        manager.stop()

if __name__ == '__main__':
    unittest.main()
