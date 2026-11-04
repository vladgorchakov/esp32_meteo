"""DS18B20 1-Wire temperature sensor driver."""

import time
from lib.sensor_presets import validate_metric_values

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

try:
    import machine
    import onewire
    import ds18x20
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class DS18B20Driver:
    """Non-blocking 1-Wire temperature driver for DS18B20 sensors."""

    def __init__(self):
        self.pin_num = None
        self.ow = None
        self.ds = None
        self.roms = []
        self._sim_temp = 22.5

    def init(self, params):
        """Initialize 1-Wire bus and scan for DS18B20 devices."""
        pins = params.get("pins", {})
        self.pin_num = pins.get("data")
        if self.pin_num is None:
            raise ValueError("DS18B20: missing required 'data' pin")

        if not HAVE_HARDWARE:
            self.roms = [b"SIM_DS18B20_0001"]
            return True

        pin = machine.Pin(self.pin_num)
        self.ow = onewire.OneWire(pin)
        self.ds = ds18x20.DS18X20(self.ow)
        self.roms = self.ds.scan()
        if not self.roms:
            raise RuntimeError("DS18B20: no devices found on 1-Wire bus (pin {})".format(self.pin_num))
        return True

    async def read(self):
        """Perform non-blocking temperature acquisition."""
        if not HAVE_HARDWARE:
            self._sim_temp += 0.1
            if self._sim_temp > 28.0:
                self._sim_temp = 20.0
            values = {"temperature": round(self._sim_temp, 1)}
            return values, "OK", ""

        if self.ds is None or not self.roms:
            raise RuntimeError("DS18B20: not initialized")

        # 1. Trigger temperature conversion
        self.ds.convert_temp()

        # 2. Non-blocking async sleep for conversion time (750ms for 12-bit)
        await asyncio.sleep_ms(750)

        # 3. Read measured temperature
        rom = self.roms[0]
        raw_temp = self.ds.read_temp(rom)
        if raw_temp is None or raw_temp == 85.0:  # 85.0C is power-on default reset value in DS18B20 register
            # Check if 85.0 was power glitch
            if raw_temp == 85.0:
                return {"temperature": 85.0}, "WARNING", "Power-on default 85C read"

        values = {"temperature": round(raw_temp, 1)}
        valid, warning = validate_metric_values("DS18B20", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Release bus resources."""
        self.roms = []
        self.ds = None
        self.ow = None
