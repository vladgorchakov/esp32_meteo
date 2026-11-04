"""PIR passive infrared motion sensor driver."""

from lib.sensor_presets import validate_metric_values

try:
    import machine
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class PIRDriver:
    """PIR motion sensor driver with GPIO edge detection interrupt."""

    def __init__(self):
        self.pin = None
        self._motion_latched = False

    def init(self, params):
        """Initialize PIR GPIO pin and attach interrupt."""
        pins = params.get("pins", {})
        pin_num = pins.get("data")
        if pin_num is None:
            raise ValueError("PIR: missing required 'data' pin")

        if not HAVE_HARDWARE:
            return True

        self.pin = machine.Pin(pin_num, machine.Pin.IN)
        try:
            self.pin.irq(trigger=machine.Pin.IRQ_RISING, handler=self._on_motion_irq)
        except Exception as exc:
            print("[PIR] Notice: could not attach IRQ ({}), using polling only".format(exc))
        return True

    def _on_motion_irq(self, pin):
        """Hardware interrupt handler for detected motion edge."""
        self._motion_latched = True

    def read(self):
        """Read motion state and clear latch."""
        if not HAVE_HARDWARE:
            return {"motion": 0}, "OK", ""

        if self.pin is None:
            raise RuntimeError("PIR: not initialized")

        current_val = self.pin.value()
        is_motion = 1 if (current_val == 1 or self._motion_latched) else 0
        self._motion_latched = False

        values = {"motion": is_motion}
        valid, warning = validate_metric_values("PIR", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Disable interrupt and release pin."""
        if self.pin is not None:
            try:
                self.pin.irq(handler=None)
            except Exception:
                pass
        self.pin = None
