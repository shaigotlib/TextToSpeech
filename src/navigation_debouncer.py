import threading
from typing import Callable, Optional


class NavigationDebouncer:
    """Accumulates rapid clicks (sequence of clicks) and flushes the net delta."""

    def __init__(self, on_flush: Callable[[int], None], debounce_delay: float = 0.22):
        self.on_flush = on_flush
        self.debounce_delay = debounce_delay
        self.accumulated_delta = 0
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def add_step(self, step: int, on_first_click: Optional[Callable[[], None]] = None) -> None:
        """Register a click step (+1 forward, -1 backward).

        Calls on_first_click only on the first step of an active click sequence.
        """
        with self._lock:
            # If this is the start of a sequence, call on_first_click
            if self._timer is None and on_first_click:
                try:
                    on_first_click()
                except Exception:
                    pass

            self.accumulated_delta += step

            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_delay, self._dispatch)
            self._timer.daemon = True
            self._timer.start()

    def _dispatch(self) -> None:
        with self._lock:
            delta = self.accumulated_delta
            self.accumulated_delta = 0
            self._timer = None

        if delta != 0:
            try:
                self.on_flush(delta)
            except Exception:
                pass

    def cancel(self) -> None:
        """Cancel any pending debounce timer and clear accumulated delta."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self.accumulated_delta = 0
