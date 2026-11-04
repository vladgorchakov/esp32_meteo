"""BMP280 I2C barometric pressure and temperature sensor driver."""

import struct
import time
from lib.sensor_presets import validate_metric_values

try:
    import machine
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class BMP280Driver:
    """Bosch BMP280 I2C sensor driver."""

    BMP280_CHIP_ID = 0x58
    REG_CHIP_ID = 0xD0
    REG_RESET = 0xE0
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_DATA = 0xF7

    def __init__(self):
        self.i2c = None
        self.addr = 0x76
        self.calib = None
        self._sim_temp = 22.8
        self._sim_press = 1012.8

    def init(self, params, i2c_bus=None):
        """Initialize BMP280 registers and read calibration parameters."""
        addr = params.get("address", 0x76)
        if isinstance(addr, str):
            self.addr = int(addr, 16) if addr.startswith("0x") else int(addr)
        else:
            self.addr = addr

        if not HAVE_HARDWARE or i2c_bus is None:
            self.calib = True
            return True

        self.i2c = i2c_bus

        # Check I2C address and chip ID
        try:
            chip_id = self.i2c.readfrom_mem(self.addr, self.REG_CHIP_ID, 1)[0]
            if chip_id != self.BMP280_CHIP_ID:
                raise RuntimeError(
                    "BMP280: invalid chip ID 0x{:02X} at 0x{:02X} (expected 0x{:02X})".format(
                        chip_id, self.addr, self.BMP280_CHIP_ID
                    )
                )
        except Exception as exc:
            raise RuntimeError("BMP280 not responding at 0x{:02X}: {}".format(self.addr, exc))

        # Soft-reset chip
        self.i2c.writeto_mem(self.addr, self.REG_RESET, b"\xB6")
        time.sleep_ms(10)

        # Read calibration data (24 bytes from 0x88)
        b = self.i2c.readfrom_mem(self.addr, 0x88, 24)
        t_p = struct.unpack("<HhhHhhhhhhhh", b)
        dig_T1 = t_p[0]
        dig_T2 = t_p[1]
        dig_T3 = t_p[2]
        dig_P = t_p[3:12]

        self.calib = {
            "T": (dig_T1, dig_T2, dig_T3),
            "P": dig_P,
        }

        # Configure sensor:
        # Standby 1000ms, filter coeff 4
        self.i2c.writeto_mem(self.addr, self.REG_CONFIG, b"\xA0")
        # Temp oversampling x1, Pressure oversampling x1, Normal mode (0x27)
        self.i2c.writeto_mem(self.addr, self.REG_CTRL_MEAS, b"\x27")

        return True

    def read(self):
        """Read and compensate temperature and pressure."""
        if not HAVE_HARDWARE or self.i2c is None:
            self._sim_temp += 0.04
            if self._sim_temp > 27.0:
                self._sim_temp = 20.0
            values = {
                "temperature": round(self._sim_temp, 1),
                "pressure": round(self._sim_press, 1),
            }
            return values, "OK", ""

        if not self.calib:
            raise RuntimeError("BMP280: calibration not loaded")

        # Read 6 data bytes: press (3B), temp (3B)
        data = self.i2c.readfrom_mem(self.addr, self.REG_DATA, 6)
        raw_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)

        # 1. Temperature calculation
        t1, t2, t3 = self.calib["T"]
        var1 = (raw_t / 16384.0 - t1 / 1024.0) * t2
        var2 = ((raw_t / 131072.0 - t1 / 8192.0) ** 2) * t3
        t_fine = var1 + var2
        temp_c = t_fine / 5120.0

        # 2. Pressure calculation
        p1, p2, p3, p4, p5, p6, p7, p8, p9 = self.calib["P"]
        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * p6 / 32768.0
        var2 = var2 + var1 * p5 * 2.0
        var2 = (var2 / 4.0) + (p4 * 65536.0)
        var1 = (p3 * var1 * var1 / 524288.0 + p2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * p1

        if var1 != 0:
            p = 1048576.0 - raw_p
            p = ((p - var2 / 4096.0) * 6250.0) / var1
            var1 = p9 * p * p / 2147483648.0
            var2 = p * p8 / 32768.0
            press_hpa = (p + (var1 + var2 + p7) / 16.0) / 100.0
        else:
            press_hpa = 0.0

        values = {
            "temperature": round(temp_c, 1),
            "pressure": round(press_hpa, 1),
        }

        valid, warning = validate_metric_values("BMP280", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Put sensor into sleep mode."""
        if HAVE_HARDWARE and self.i2c is not None:
            try:
                self.i2c.writeto_mem(self.addr, self.REG_CTRL_MEAS, b"\x00")
            except Exception:
                pass
        self.calib = None
        self.i2c = None
