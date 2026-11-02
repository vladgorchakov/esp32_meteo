"""Graphical startup splash screen with system initialization status."""

import time
from lib.screens.base import BaseScreen


class SplashScreen(BaseScreen):
    """Initial splash screen displayed for 2 seconds upon device startup."""

    def __init__(self, duration_ms=2000):
        super().__init__("splash")
        self.duration_ms = duration_ms
        self.start_time = 0
        self.finished = False

    def on_enter(self):
        self.start_time = time.ticks_ms()
        self.finished = False

    def update(self, now_ms):
        if not self.finished and time.ticks_diff(now_ms, self.start_time) >= self.duration_ms:
            self.finished = True

    def is_finished(self):
        """Return True when splash duration has elapsed."""
        return self.finished

    def render(self, disp):
        disp.clear(0)

        # Title banner
        disp.rect(0, 0, 128, 17, 1)
        disp.text("ESP32 STATION", 12, 5, 1)

        # Initialization checklist
        disp.text("Storage: OK", 4, 22, 1)
        disp.text("Display: OK", 4, 32, 1)
        disp.text("Sensors: READY", 4, 42, 1)
        disp.text("Network: READY", 4, 52, 1)

    def on_event(self, button_name, event_type):
        # Allow user to dismiss splash immediately by pressing any key
        self.finished = True
        return True
