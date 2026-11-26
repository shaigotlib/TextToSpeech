import unittest
import time
from src.navigation_debouncer import NavigationDebouncer

class TestNavigationDebouncer(unittest.TestCase):
    def test_single_click_dispatches_after_delay(self):
        dispatched = []
        debouncer = NavigationDebouncer(on_flush=dispatched.append, debounce_delay=0.08)

        debouncer.add_step(1)
        self.assertEqual(len(dispatched), 0)

        time.sleep(0.12)
        self.assertEqual(dispatched, [1])

    def test_sequence_of_clicks_accumulates_into_single_dispatch(self):
        dispatched = []
        debouncer = NavigationDebouncer(on_flush=dispatched.append, debounce_delay=0.1)

        # 3 clicks forward in rapid succession
        debouncer.add_step(1)
        time.sleep(0.03)
        debouncer.add_step(1)
        time.sleep(0.03)
        debouncer.add_step(1)

        # Should not have dispatched yet
        self.assertEqual(len(dispatched), 0)

        time.sleep(0.15)
        # Should have dispatched once with accumulated sum of 3
        self.assertEqual(dispatched, [3])

    def test_forward_and_backward_sequence_cancellation(self):
        dispatched = []
        debouncer = NavigationDebouncer(on_flush=dispatched.append, debounce_delay=0.08)

        # 2 forward (+2), 1 backward (-1) -> net +1
        debouncer.add_step(1)
        time.sleep(0.02)
        debouncer.add_step(1)
        time.sleep(0.02)
        debouncer.add_step(-1)

        time.sleep(0.12)
        self.assertEqual(dispatched, [1])

    def test_net_zero_delta_does_not_dispatch(self):
        dispatched = []
        debouncer = NavigationDebouncer(on_flush=dispatched.append, debounce_delay=0.08)

        debouncer.add_step(1)
        debouncer.add_step(-1)

        time.sleep(0.12)
        self.assertEqual(len(dispatched), 0)

    def test_on_first_click_callback_called_only_once_per_sequence(self):
        first_clicks = []
        debouncer = NavigationDebouncer(on_flush=lambda d: None, debounce_delay=0.08)

        debouncer.add_step(1, on_first_click=lambda: first_clicks.append("first"))
        debouncer.add_step(1, on_first_click=lambda: first_clicks.append("second"))
        debouncer.add_step(1, on_first_click=lambda: first_clicks.append("third"))

        # Only the very first click in the active sequence should trigger the callback
        self.assertEqual(first_clicks, ["first"])
        time.sleep(0.12)

    def test_cancel_aborts_pending_dispatch(self):
        dispatched = []
        debouncer = NavigationDebouncer(on_flush=dispatched.append, debounce_delay=0.08)

        debouncer.add_step(2)
        debouncer.cancel()

        time.sleep(0.12)
        self.assertEqual(len(dispatched), 0)


if __name__ == "__main__":
    unittest.main()
