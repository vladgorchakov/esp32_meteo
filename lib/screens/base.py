"""Base class for all local OLED screen views."""


class BaseScreen:
    """Abstract screen view defining lifecycle and rendering hooks."""

    def __init__(self, name):
        self.name = name

    def on_enter(self):
        """Called when this screen becomes the active view."""
        pass

    def on_exit(self):
        """Called when switching away from this screen."""
        pass

    def update(self, now_ms):
        """Periodic background update (e.g. data polling or animation timers)."""
        pass

    def render(self, display):
        """Render screen contents onto the display manager's back buffer."""
        pass

    def on_event(self, button_name, event_type):
        """Handle user input event. Return True if event was consumed, False to allow fallback."""
        return False
