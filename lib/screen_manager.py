"""Screen coordinator and asynchronous UI task scheduler."""

import time
from lib.display_manager import display
from lib.input_manager import input_mgr
from lib import state
from lib.screens.splash_screen import SplashScreen
from lib.screens.main_screen import MainScreen
from lib.screens.wifi_screen import WifiScreen
from lib.screens.system_screen import SystemScreen
from lib.screens.menu_screen import MenuScreen

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

# Compatibility helpers for host environment simulation
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.time() * 1000)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
if not hasattr(asyncio, "sleep_ms"):
    asyncio.sleep_ms = lambda ms: asyncio.sleep(ms / 1000.0)

UI_LOOP_INTERVAL_MS = 40


class ScreenManager:
    """Manages active view, screen transitions, display sleep, and UI loop execution."""

    def __init__(self):
        self.splash = SplashScreen()
        self.main_scr = MainScreen()
        self.wifi_scr = WifiScreen()
        self.system_scr = SystemScreen()
        self.menu_scr = MenuScreen(self)

        # Standard carousel screens for sequential navigation (§6.1)
        self.carousel = [
            self.main_scr,
            self.wifi_scr,
            self.system_scr,
        ]
        self.carousel_idx = 0

        # Currently visible screen
        self.current_screen = self.splash
        self.previous_screen = self.main_scr
        self.in_menu = False
        self._running = False

    def init(self):
        """Initialize display and input manager, show splash screen."""
        display.init()
        input_mgr.init()
        self.current_screen = self.splash
        self.current_screen.on_enter()

    def open_menu(self):
        """Open settings menu overlay."""
        if not self.in_menu:
            self.previous_screen = self.current_screen
            self.in_menu = True
            self.current_screen = self.menu_scr
            self.current_screen.on_enter()

    def close_menu(self):
        """Close settings menu and return to previous screen."""
        if self.in_menu:
            self.in_menu = False
            self.current_screen = self.previous_screen
            self.current_screen.on_enter()

    def toggle_menu(self):
        """Toggle menu open/closed state."""
        if self.in_menu:
            self.close_menu()
        else:
            self.open_menu()

    def switch_to_screen(self, name):
        """Switch to a specific screen by identifier."""
        for idx, scr in enumerate(self.carousel):
            if scr.name == name:
                self.carousel_idx = idx
                self.current_screen = scr
                self.current_screen.on_enter()
                return

    def next_screen(self):
        """Advance to next screen in carousel (§6.1: wrap around to first)."""
        self.carousel_idx = (self.carousel_idx + 1) % len(self.carousel)
        self.current_screen = self.carousel[self.carousel_idx]
        self.current_screen.on_enter()

    def prev_screen(self):
        """Step back to previous screen in carousel (§6.1: wrap around to last)."""
        self.carousel_idx = (self.carousel_idx - 1) % len(self.carousel)
        self.current_screen = self.carousel[self.carousel_idx]
        self.current_screen.on_enter()

    def first_screen(self):
        """Jump directly to the first screen (Main Screen) (§6.1)."""
        self.carousel_idx = 0
        self.current_screen = self.carousel[0]
        self.current_screen.on_enter()

    def last_screen(self):
        """Jump directly to the last screen (System Screen) (§6.1)."""
        self.carousel_idx = len(self.carousel) - 1
        self.current_screen = self.carousel[self.carousel_idx]
        self.current_screen.on_enter()

    def toggle_display_power(self):
        """Toggle display ON/OFF (§6.1)."""
        if display.is_on():
            display.off()
            print("[UI] Display turned OFF (sleep mode)")
        else:
            display.on()
            print("[UI] Display turned ON")

    def handle_input_event(self, button_name, event_type):
        """Route user input events according to system state and navigation rules."""
        # 1. If display is OFF, wake up on BUTTON_5, ROTARY_SW, or encoder turn (§6.1)
        if not display.is_on():
            if button_name in ("BUTTON_5", "ROTARY_SW") and event_type == "SHORT":
                self.toggle_display_power()
            elif button_name == "ROTARY":
                self.toggle_display_power()
            return

        # 2. Let active screen handle event first (e.g. MenuScreen)
        if self.current_screen.on_event(button_name, event_type):
            return

        # 3. Global navigation bindings (when not consumed by active screen)
        if button_name == "ROTARY":
            if not self.in_menu:
                if event_type == "CW":
                    self.next_screen()
                elif event_type == "CCW":
                    self.prev_screen()

        elif event_type == "SHORT":
            if button_name == "BUTTON_5":
                self.toggle_display_power()

            elif button_name in ("TOUCH_BUTTON", "ROTARY_SW"):
                self.toggle_menu()

            elif not self.in_menu:
                if button_name == "BUTTON_3":
                    self.next_screen()
                elif button_name == "BUTTON_1":
                    self.prev_screen()
                elif button_name == "BUTTON_2":
                    self.first_screen()
                elif button_name == "BUTTON_4":
                    self.last_screen()

        elif event_type == "LONG":
            if button_name == "ROTARY_SW":
                self.toggle_display_power()

    async def ui_task(self):
        """Main UI task loop: process input events, update view, and render display."""
        self._running = True
        while self._running:
            now_ms = time.ticks_ms()

            # Automatic display wake-up on critical system alert
            if state.get("critical_alert") and not display.is_on():
                display.on()

            # 1. Drain input event queue without blocking
            while not input_mgr.event_queue.empty():
                try:
                    button_name, event_type = input_mgr.event_queue.get_nowait()
                    self.handle_input_event(button_name, event_type)
                except Exception as exc:
                    print("[UI] Error handling event: {}".format(exc))

            # 2. Check if splash screen duration has finished
            if self.current_screen is self.splash and self.splash.is_finished():
                self.carousel_idx = 0
                self.current_screen = self.carousel[0]
                self.current_screen.on_enter()

            # 3. Update active view state
            self.current_screen.update(now_ms)

            # 4. Render and flush to display
            if display.is_on():
                self.current_screen.render(display)
                display.flush()

            await asyncio.sleep_ms(UI_LOOP_INTERVAL_MS)


# Global singleton instance
screen_mgr = ScreenManager()
