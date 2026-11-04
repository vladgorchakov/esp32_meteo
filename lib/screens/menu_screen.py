"""Interactive menu screen with scrollable list and modal confirmation dialogs."""

import os
import config
from lib.screens.base import BaseScreen
from lib import state
from lib import config_store

try:
    import machine
    HAVE_MACHINE = True
except ImportError:
    HAVE_MACHINE = False

MENU_ITEMS = [
    "Connect Wi-Fi",
    "Disconnect Wi-Fi",
    "Wi-Fi Status",
    "Connect MQTT",
    "Disconnect MQTT",
    "Open Web UI",
    "Restart",
    "Factory Reset",
    "Exit",
]


class MenuScreen(BaseScreen):
    """Interactive system settings menu corresponding to §6.2 and §6.3 of the specification."""

    def __init__(self, screen_manager):
        super().__init__("menu")
        self.sm = screen_manager
        self.selected_idx = 0
        self.scroll_offset = 0

        # Modal dialog state: None, "RESTART", "FACTORY_RESET", "WEB_UI", "NOTICE"
        self.modal_state = None
        self.modal_text = ""

    def on_enter(self):
        self.modal_state = None
        self.modal_text = ""

    def render(self, disp):
        disp.clear(0)

        # Render active modal dialog if open
        if self.modal_state is not None:
            self._render_modal(disp)
            return

        # Header
        disp.text("--- MENU ---", 16, 0, 1)
        disp.hline(0, 9, 128, 1)

        # Keep selected item visible within 4 visible rows
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + 4:
            self.scroll_offset = self.selected_idx - 3

        # Render 4 visible menu items
        for i in range(4):
            item_idx = self.scroll_offset + i
            if item_idx >= len(MENU_ITEMS):
                break

            y = 12 + i * 13
            item_name = MENU_ITEMS[item_idx]

            if item_idx == self.selected_idx:
                # Highlight selected row with white background and inverted text
                disp.fill_rect(0, y, 128, 12, 1)
                disp.text("> " + item_name, 2, y + 2, 0)
            else:
                disp.text("  " + item_name, 2, y + 2, 1)

    def _render_modal(self, disp):
        """Render modal overlay on screen."""
        disp.rect(4, 4, 120, 56, 1)
        disp.fill_rect(5, 5, 118, 54, 0)

        if self.modal_state == "RESTART":
            disp.text("Restart ESP32?", 10, 12, 1)
            disp.text("B3: Confirm", 10, 30, 1)
            disp.text("B1: Cancel", 10, 44, 1)

        elif self.modal_state == "FACTORY_RESET":
            disp.text("Factory Reset?", 10, 10, 1)
            disp.text("Erase /data/?", 10, 22, 1)
            disp.text("B3: Confirm", 10, 36, 1)
            disp.text("B1: Cancel", 10, 48, 1)

        elif self.modal_state == "WEB_UI":
            disp.text("Web UI Address:", 8, 10, 1)
            ip = state.get("wifi_ip", "0.0.0.0")
            disp.text("http://" + (ip if ip != "0.0.0.0" else "192.168.4.1"), 8, 26, 1)
            disp.text("B1: Back", 8, 44, 1)

        elif self.modal_state == "NOTICE":
            lines = self.modal_text.split("\n")
            y = 14
            for line in lines:
                disp.text(line, 10, y, 1)
                y += 12
            disp.text("B1: Back", 10, 44, 1)

    def on_event(self, button_name, event_type):
        """Process menu navigation and selection buttons."""
        if event_type not in ("SHORT", "LONG", "CW", "CCW"):
            return False

        # -----------------------------------------------------------------
        # Modal Dialog Handling
        # -----------------------------------------------------------------
        if self.modal_state is not None:
            if self.modal_state == "RESTART":
                if button_name in ("BUTTON_3", "ROTARY_SW") and event_type == "SHORT":
                    print("[SYS] Reboot confirmed by user. Resetting...")
                    if HAVE_MACHINE:
                        machine.reset()
                    return True
                elif button_name == "BUTTON_1" or (button_name == "ROTARY_SW" and event_type == "LONG"):
                    self.modal_state = None
                    return True

            elif self.modal_state == "FACTORY_RESET":
                if button_name in ("BUTTON_3", "ROTARY_SW") and event_type == "SHORT":
                    print("[SYS] Factory reset confirmed. Erasing /data directory...")
                    self._perform_factory_reset()
                    if HAVE_MACHINE:
                        machine.reset()
                    return True
                elif button_name == "BUTTON_1" or (button_name == "ROTARY_SW" and event_type == "LONG"):
                    self.modal_state = None
                    return True

            elif self.modal_state in ("WEB_UI", "NOTICE"):
                if button_name in ("BUTTON_1", "BUTTON_5", "TOUCH_BUTTON", "ROTARY_SW"):
                    self.modal_state = None
                    return True
            return True

        # -----------------------------------------------------------------
        # Standard Menu Navigation
        # -----------------------------------------------------------------
        if button_name == "BUTTON_4" or (button_name == "ROTARY" and event_type == "CW"):  # Down
            self.selected_idx = (self.selected_idx + 1) % len(MENU_ITEMS)
            return True

        elif button_name == "BUTTON_2" or (button_name == "ROTARY" and event_type == "CCW"):  # Up
            self.selected_idx = (self.selected_idx - 1) % len(MENU_ITEMS)
            return True

        elif (button_name in ("BUTTON_5", "BUTTON_3") and event_type == "SHORT") or (button_name == "ROTARY_SW" and event_type == "SHORT"):  # Select / Confirm
            self._execute_action(MENU_ITEMS[self.selected_idx])
            return True

        elif (button_name in ("BUTTON_1", "TOUCH_BUTTON") and event_type == "SHORT") or (button_name == "ROTARY_SW" and event_type == "LONG"):  # Back / Exit Menu
            self.sm.close_menu()
            return True

        return False

    def _execute_action(self, item_name):
        """Execute selected menu option."""
        if item_name == "Exit":
            self.sm.close_menu()

        elif item_name == "Wi-Fi Status":
            self.sm.close_menu()
            self.sm.switch_to_screen("wifi")

        elif item_name == "Open Web UI":
            self.modal_state = "WEB_UI"

        elif item_name == "Restart":
            self.modal_state = "RESTART"

        elif item_name == "Factory Reset":
            self.modal_state = "FACTORY_RESET"

        elif item_name in ("Connect Wi-Fi", "Disconnect Wi-Fi"):
            print("[MENU] {}: not implemented (Phase 4/5)".format(item_name))
            self.modal_state = "NOTICE"
            self.modal_text = "{}\nNot implemented\n(Phase 4/5)".format(item_name)

        elif item_name in ("Connect MQTT", "Disconnect MQTT"):
            print("[MENU] {}: not implemented (Phase 4/5)".format(item_name))
            self.modal_state = "NOTICE"
            self.modal_text = "{}\nNot implemented\n(Phase 4/5)".format(item_name)

    def _perform_factory_reset(self):
        """Erase all configuration files in /data directory."""
        for path in (
            config.PATH_SENSORS_CONFIG,
            config.PATH_BROKERS_CONFIG,
            config.PATH_ROUTING_CONFIG,
            config.PATH_POWER_CONFIG,
        ):
            config_store.delete_file(path)
