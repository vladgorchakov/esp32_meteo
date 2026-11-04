"""DHT11 temperature and humidity sensor driver."""

import time
from lib.sensor_presets import validate_metric_values

try:
    import machine
    import dht
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class DHT11Driver:
    """Driver for DHT11 single-wire digital temperature and humidity sensor."""

    def __init__(self):
        self.pin_num = None
        self.sensor = None
        self._sim_temp = 21.0
        self._sim_hum = 45.0

    def init(self, params):
        """Initialize DHT11 on specified GPIO pin."""
        pins = params.get("pins", {})
        self.pin_num = pins.get("data")
        if self.pin_num is None:
            raise ValueError("DHT11: missing required 'data' pin")

        if not HAVE_HARDWARE:
            return True

        self.sensor = dht.DHT11(machine.Pin(self.pin_num))
        return True

    def read(self):
        """Read temperature and humidity values synchronously."""
        if not HAVE_HARDWARE:
            self._sim_temp += 0.2
            if self._sim_temp > 30.0:
                self._sim_temp = 20.0
            self._sim_hum += 0.5
            if self._sim_hum > 70.0:
                self._sim_hum = 40.0
            values = {
                "temperature": round(self._sim_temp, 1),
                "humidity": round(self._sim_hum, 1),
            }
            return values, "OK", ""

        if self.sensor is None:
            raise RuntimeError("DHT11: not initialized")

        try:
            self.sensor.measure()
            temp = float(self.sensor.temperature())
            hum = float(self.sensor.humidity())
        except OSError as exc:
            raise RuntimeError("DHT11 read error: {}".format(exc))

        values = {
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
        }

        valid, warning = validate_metric_values("DHT11", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Release hardware resources."""
        self.sensor = None
