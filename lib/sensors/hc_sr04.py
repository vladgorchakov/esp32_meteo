"""HC-SR04 ultrasonic distance sensor driver."""

import time
from lib.sensor_presets import validate_metric_values

try:
    import machine
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class HCSR04Driver:
    """Ultrasonic distance driver using time_pulse_us."""

    def __init__(self):
        self.trig = None
        self.echo = None
        self._sim_dist = 45.0

    def init(self, params):
        """Initialize Trig and Echo GPIO pins."""
        pins = params.get("pins", {})
        trig_pin = pins.get("trig")
        echo_pin = pins.get("echo")
        if trig_pin is None or echo_pin is None:
            raise ValueError("HC-SR04: requires both 'trig' and 'echo' pins")

        if not HAVE_HARDWARE:
            return True

        self.trig = machine.Pin(trig_pin, machine.Pin.OUT)
        self.echo = machine.Pin(echo_pin, machine.Pin.IN)
        self.trig.value(0)
        return True

    def read(self):
        """Send ultrasonic trigger pulse and measure echo pulse duration."""
        if not HAVE_HARDWARE:
            self._sim_dist += 1.0
            if self._sim_dist > 150.0:
                self._sim_dist = 20.0
            values = {"distance": round(self._sim_dist, 1)}
            return values, "OK", ""

        if self.trig is None or self.echo is None:
            raise RuntimeError("HC-SR04: not initialized")

        # Send 10us HIGH pulse on Trig pin
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        # Measure duration of HIGH pulse on Echo pin (max timeout 30000us ~ 5 meters)
        duration_us = machine.time_pulse_us(self.echo, 1, 30000)
        if duration_us < 0:
            return {"distance": None}, "WARNING", "Echo pulse timeout (no obstacle)"

        # Sound speed in air: ~343 m/s = 0.0343 cm/us -> divide by 2 for round-trip
        dist_cm = (duration_us * 0.0343) / 2.0
        values = {"distance": round(dist_cm, 1)}

        valid, warning = validate_metric_values("HC-SR04", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Release GPIO resources."""
        self.trig = None
        self.echo = None
