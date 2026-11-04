"""Asynchronous button input manager with software debouncing and event queue."""

import time
import board_config

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

try:
    import machine
    HAVE_MACHINE = True
except ImportError:
    HAVE_MACHINE = False

# Debounce and timing parameters
POLL_INTERVAL_MS = 25
STABLE_TICKS_REQUIRED = 2
LONG_PRESS_MS = 800

# ESP32 GPI pins: input only, silicon does not have internal pull-ups or pull-downs
INPUT_ONLY_PINS = (34, 35, 36, 39)

# Quadrature encoder 2-bit state transition table
QUAD_TRANSITIONS = {
    (0b11, 0b01): 1, (0b01, 0b00): 1, (0b00, 0b10): 1, (0b10, 0b11): 1,
    (0b11, 0b10): -1, (0b10, 0b00): -1, (0b00, 0b01): -1, (0b01, 0b11): -1,
}


class Button:
    """State tracker for an individual physical button or touch pad."""

    def __init__(self, name, pin_num, is_touch=False):
        self.name = name
        self.pin_num = pin_num
        self.is_touch = is_touch
        self.pin = None
        self.touch_pad = None

        self.last_raw = 0
        self.stable_state = 0
        self.stable_count = 0
        self.press_start_time = 0
        self.long_reported = False

        if HAVE_MACHINE:
            try:
                if self.is_touch and getattr(board_config, "TOUCH_USE_HARDWARE_TOUCHPAD", False):
                    self.touch_pad = machine.TouchPad(machine.Pin(pin_num))
                elif pin_num in INPUT_ONLY_PINS:
                    # ESP32 input-only pins (34, 35, 36, 39) cannot enable internal pull-up
                    self.pin = machine.Pin(pin_num, machine.Pin.IN)
                else:
                    self.pin = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
            except Exception as exc:
                print("[INPUT] Error initializing pin {} for {}: {}".format(pin_num, name, exc))

    def read_is_pressed(self):
        """Read raw button state. Returns True if button is currently pressed."""
        if not HAVE_MACHINE or (self.pin is None and self.touch_pad is None):
            return False

        if self.touch_pad is not None:
            try:
                val = self.touch_pad.read()
                # TouchPad values drop significantly when touched (typically < 400)
                return val < 400
            except Exception:
                return False

        if self.pin is not None:
            try:
                # Active LOW: 0 = pressed, 1 = released
                active_level = getattr(board_config, "BUTTON_ACTIVE_LEVEL", 0)
                return self.pin.value() == active_level
            except Exception:
                return False

        return False


class RotaryEncoder:
    """Quadrature rotary encoder reader with debouncing and step accumulation."""

    def __init__(self, pin_clk, pin_dt, steps_per_click=2):
        self.pin_clk_num = pin_clk
        self.pin_dt_num = pin_dt
        self.steps_per_click = steps_per_click
        self.pin_clk = None
        self.pin_dt = None
        self.last_state = 0b11
        self.accum = 0

        if HAVE_MACHINE:
            try:
                self.pin_clk = machine.Pin(pin_clk, machine.Pin.IN, machine.Pin.PULL_UP)
                self.pin_dt = machine.Pin(pin_dt, machine.Pin.IN, machine.Pin.PULL_UP)
                clk_v = self.pin_clk.value()
                dt_v = self.pin_dt.value()
                self.last_state = (clk_v << 1) | dt_v
            except Exception as exc:
                print("[INPUT] Error initializing rotary encoder (pins {}, {}): {}".format(pin_clk, pin_dt, exc))

    def poll(self):
        """Read encoder pins and return 'CW', 'CCW', or None."""
        if not HAVE_MACHINE or self.pin_clk is None or self.pin_dt is None:
            return None

        try:
            clk_v = self.pin_clk.value()
            dt_v = self.pin_dt.value()
            curr = (clk_v << 1) | dt_v
            if curr == self.last_state:
                return None

            step = QUAD_TRANSITIONS.get((self.last_state, curr), 0)
            self.last_state = curr
            self.accum += step

            if self.accum >= self.steps_per_click:
                self.accum = 0
                return "CW"
            elif self.accum <= -self.steps_per_click:
                self.accum = 0
                return "CCW"

            return None
        except Exception:
            return None


class InputManager:
    """Manages button polling coroutine, rotary encoder, and event queue dispatch."""

    def __init__(self):
        self.event_queue = asyncio.Queue()
        self.buttons = []
        self.encoder = None
        self._running = False

    def init(self):
        """Configure button hardware, rotary encoder, and registers."""
        self.buttons = [
            Button("BUTTON_1", board_config.PIN_BUTTON_1),
            Button("BUTTON_2", board_config.PIN_BUTTON_2),
            Button("BUTTON_3", board_config.PIN_BUTTON_3),
            Button("BUTTON_4", board_config.PIN_BUTTON_4),
            Button("BUTTON_5", board_config.PIN_BUTTON_5),
            Button("TOUCH_BUTTON", board_config.PIN_TOUCH_BUTTON, is_touch=True),
        ]

        # Rotary encoder push switch
        if hasattr(board_config, "PIN_ROTARY_ENCODER_SW"):
            self.buttons.append(Button("ROTARY_SW", board_config.PIN_ROTARY_ENCODER_SW))

        # Quadrature encoder (CLK/DT)
        if hasattr(board_config, "PIN_ROTARY_ENCODER_CLK") and hasattr(board_config, "PIN_ROTARY_ENCODER_DT"):
            self.encoder = RotaryEncoder(board_config.PIN_ROTARY_ENCODER_CLK, board_config.PIN_ROTARY_ENCODER_DT)
        else:
            self.encoder = None

        print("[INPUT] Configured {} button channels + Rotary Encoder".format(len(self.buttons)))

    async def poll_task(self):
        """Async polling loop for debouncing, press duration, and rotary encoder."""
        self._running = True
        while self._running:
            now = time.ticks_ms()

            # Poll rotary encoder rotation
            if self.encoder is not None:
                enc_direction = self.encoder.poll()
                if enc_direction == "CW":
                    await self.event_queue.put(("ROTARY", "CW"))
                elif enc_direction == "CCW":
                    await self.event_queue.put(("ROTARY", "CCW"))

            # Poll buttons
            for btn in self.buttons:
                raw = 1 if btn.read_is_pressed() else 0

                # Check if state is stable
                if raw == btn.last_raw:
                    btn.stable_count += 1
                else:
                    btn.last_raw = raw
                    btn.stable_count = 0

                if btn.stable_count >= STABLE_TICKS_REQUIRED:
                    # State transition detected
                    if raw != btn.stable_state:
                        btn.stable_state = raw

                        if raw == 1:
                            # Button PRESSED
                            btn.press_start_time = now
                            btn.long_reported = False
                        else:
                            # Button RELEASED
                            if not btn.long_reported:
                                # Short press
                                duration = time.ticks_diff(now, btn.press_start_time)
                                if duration >= (POLL_INTERVAL_MS * STABLE_TICKS_REQUIRED):
                                    await self.event_queue.put((btn.name, "SHORT"))
                    else:
                        # Button held down
                        if raw == 1 and not btn.long_reported:
                            duration = time.ticks_diff(now, btn.press_start_time)
                            if duration >= LONG_PRESS_MS:
                                btn.long_reported = True
                                await self.event_queue.put((btn.name, "LONG"))

            await asyncio.sleep_ms(POLL_INTERVAL_MS)

    async def post_event(self, button_name, event_type):
        """Manually inject an event into queue (for testing or simulation)."""
        await self.event_queue.put((button_name, event_type))


# Global singleton instance
input_mgr = InputManager()
