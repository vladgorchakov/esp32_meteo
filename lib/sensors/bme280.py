"""BME280 I2C environmental sensor driver (temperature, humidity, pressure)."""

import struct
import time
from lib.sensor_presets import validate_metric_values

try:
    import machine
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class BME280Driver:
    """Bosch BME280 I2C sensor driver."""

    BME280_CHIP_ID = 0x60
    REG_CHIP_ID = 0xD0
    REG_RESET = 0xE0
    REG_CTRL_HUM = 0xF2
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_DATA = 0xF7

    def __init__(self):
        self.i2c = None
        self.addr = 0x76
        self.calib = None
        self._sim_temp = 23.4
        self._sim_hum = 48.2
        self._sim_press = 1013.2

    def init(self, params, i2c_bus=None):
        """Initialize BME280 registers and read calibration parameters."""
        addr = params.get("address", 0x76)
        if isinstance(addr, str):
            self.addr = int(addr, 16) if addr.startswith("0x") else int(addr)
        else:
            self.addr = addr

        if not HAVE_HARDWARE or i2c_bus is None:
            self.calib = True
            return True

        self.i2c = i2c_bus

        # Check I2C address presence
        try:
            chip_id = self.i2c.readfrom_mem(self.addr, self.REG_CHIP_ID, 1)[0]
            if chip_id != self.BME280_CHIP_ID:
                raise RuntimeError(
                    "BME280: invalid chip ID 0x{:02X} at 0x{:02X} (expected 0x{:02X})".format(
                        chip_id, self.addr, self.BME280_CHIP_ID
                    )
                )
        except Exception as exc:
            raise RuntimeError("BME280 not responding at 0x{:02X}: {}".format(self.addr, exc))

        # Soft-reset chip
        self.i2c.writeto_mem(self.addr, self.REG_RESET, b"\xB6")
        time.sleep_ms(10)

        # Read calibration data
        self._read_calibration()

        # Configure sensor:
        # 1. Humidity oversampling x1
        self.i2c.writeto_mem(self.addr, self.REG_CTRL_HUM, b"\x01")
        # 2. Standby 1000ms, filter coeff 4
        self.i2c.writeto_mem(self.addr, self.REG_CONFIG, b"\xA0")
        # 3. Temp oversampling x1, Pressure oversampling x1, Normal mode (0x27)
        self.i2c.writeto_mem(self.addr, self.REG_CTRL_MEAS, b"\x27")

        return True

    def _read_calibration(self):
        """Load factory calibration coefficients from OTP ROM."""
        # 1. Read temperature and pressure calibration (24 bytes from 0x88)
        b1 = self.i2c.readfrom_mem(self.addr, 0x88, 24)
        t_p = struct.unpack("<HhhHhhhhhhhh", b1)
        dig_T1 = t_p[0]
        dig_T2 = t_p[1]
        dig_T3 = t_p[2]
        dig_P = t_p[3:12]

        # 2. Read humidity calibration (0xA1 and 0xE1..0xE7)
        dig_H1 = self.i2c.readfrom_mem(self.addr, 0xA1, 1)[0]
        b2 = self.i2c.readfrom_mem(self.addr, 0xE1, 7)
        dig_H2 = struct.unpack("<h", b2[0:2])[0]
        dig_H3 = b2[2]
        dig_H4 = (b2[3] << 4) | (b2[4] & 0x0F)
        if dig_H4 > 2047:
            dig_H4 -= 4096
        dig_H5 = (b2[5] << 4) | (b2[4] >> 4)
        if dig_H5 > 2047:
            dig_H5 -= 4096
        dig_H6 = struct.unpack("b", bytes([b2[6]]))[0]

        self.calib = {
            "T": (dig_T1, dig_T2, dig_T3),
            "P": dig_P,
            "H": (dig_H1, dig_H2, dig_H3, dig_H4, dig_H5, dig_H6),
        }

    def read(self):
        """Read and compensate temperature, humidity, and pressure."""
        if not HAVE_HARDWARE or self.i2c is None:
            self._sim_temp += 0.05
            if self._sim_temp > 28.0:
                self._sim_temp = 20.0
            values = {
                "temperature": round(self._sim_temp, 1),
                "humidity": round(self._sim_hum, 1),
                "pressure": round(self._sim_press, 1),
            }
            return values, "OK", ""

        if not self.calib:
            raise RuntimeError("BME280: calibration not loaded")

        # Read 8 data bytes at once: press (3B), temp (3B), hum (2B)
        data = self.i2c.readfrom_mem(self.addr, self.REG_DATA, 8)
        raw_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        raw_h = (data[6] << 8) | data[7]

        # 1. Temperature calculation (Bosch reference)
        t1, t2, t3 = self.calib["T"]
        var1 = (raw_t / 16384.0 - t1 / 1024.0) * t2
        var2 = ((raw_t / 131072.0 - t1 / 8192.0) ** 2) * t3
        t_fine = var1 + var2
        temp_c = t_fine / 5120.0

        # 2. Pressure calculation (Bosch reference)
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

        # 3. Humidity calculation (Bosch reference)
        h1, h2, h3, h4, h5, h6 = self.calib["H"]
        h = t_fine - 76800.0
        h = (raw_h - (h4 * 64.0 + h5 / 16384.0 * h)) * (
            h2 / 65536.0 * (1.0 + h6 / 67108864.0 * h * (1.0 + h3 / 67108864.0 * h))
        )
        hum_pct = h * (1.0 - h1 * h / 524288.0)
        if hum_pct > 100.0:
            hum_pct = 100.0
        elif hum_pct < 0.0:
            hum_pct = 0.0

        values = {
            "temperature": round(temp_c, 1),
            "humidity": round(hum_pct, 1),
            "pressure": round(press_hpa, 1),
        }

        valid, warning = validate_metric_values("BME280", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Put sensor into low-power sleep mode."""
        if HAVE_HARDWARE and self.i2c is not None:
            try:
                # Set mode to Sleep (0x00)
                self.i2c.writeto_mem(self.addr, self.REG_CTRL_MEAS, b"\x00")
            except Exception:
                pass
        self.calib = None
        self.i2c = None
