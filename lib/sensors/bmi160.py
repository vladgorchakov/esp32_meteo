"""BMI160 I2C 6-axis Inertial Measurement Unit (Accelerometer & Gyroscope) driver."""

import struct
import time
from lib.sensor_presets import validate_metric_values

try:
    import machine
    HAVE_HARDWARE = True
except ImportError:
    HAVE_HARDWARE = False


class BMI160Driver:
    """Bosch BMI160 16-bit 6-axis IMU driver."""

    BMI160_CHIP_ID = 0xD1
    REG_CHIP_ID = 0x00
    REG_DATA_START = 0x0C  # 12 consecutive bytes for Gyro (6B) and Accel (6B)
    REG_CMD = 0x7E
    REG_ACC_CONF = 0x40
    REG_ACC_RANGE = 0x41
    REG_GYR_CONF = 0x42
    REG_GYR_RANGE = 0x43

    # Command codes
    CMD_SOFT_RESET = 0xB6
    CMD_ACCEL_NORMAL = 0x11
    CMD_GYRO_NORMAL = 0x15
    CMD_SUSPEND = 0x00

    def __init__(self):
        self.i2c = None
        self.addr = 0x68
        self._sim_step = 0

    def init(self, params, i2c_bus=None):
        """Initialize BMI160 registers and power modes."""
        addr = params.get("address", 0x68)
        if isinstance(addr, str):
            self.addr = int(addr, 16) if addr.startswith("0x") else int(addr)
        else:
            self.addr = addr

        if not HAVE_HARDWARE or i2c_bus is None:
            return True

        self.i2c = i2c_bus

        # Check Chip ID
        try:
            chip_id = self.i2c.readfrom_mem(self.addr, self.REG_CHIP_ID, 1)[0]
            if chip_id != self.BMI160_CHIP_ID:
                raise RuntimeError(
                    "BMI160: invalid chip ID 0x{:02X} at 0x{:02X} (expected 0x{:02X})".format(
                        chip_id, self.addr, self.BMI160_CHIP_ID
                    )
                )
        except Exception as exc:
            raise RuntimeError("BMI160 not responding at 0x{:02X}: {}".format(self.addr, exc))

        # Soft reset
        self.i2c.writeto_mem(self.addr, self.REG_CMD, bytes([self.CMD_SOFT_RESET]))
        time.sleep_ms(20)

        # Power on Accelerometer and Gyroscope (Normal Mode)
        self.i2c.writeto_mem(self.addr, self.REG_CMD, bytes([self.CMD_ACCEL_NORMAL]))
        time.sleep_ms(10)
        self.i2c.writeto_mem(self.addr, self.REG_CMD, bytes([self.CMD_GYRO_NORMAL]))
        time.sleep_ms(60)

        # Configure Accelerometer: 100Hz ODR (0x28), Range ±2g (0x03 -> 16384 LSB/g)
        self.i2c.writeto_mem(self.addr, self.REG_ACC_CONF, b"\x28")
        self.i2c.writeto_mem(self.addr, self.REG_ACC_RANGE, b"\x03")

        # Configure Gyroscope: 100Hz ODR (0x28), Range ±250 deg/s (0x03 -> 131.2 LSB/deg/s)
        self.i2c.writeto_mem(self.addr, self.REG_GYR_CONF, b"\x28")
        self.i2c.writeto_mem(self.addr, self.REG_GYR_RANGE, b"\x03")

        return True

    def read(self):
        """Perform burst read of 12 bytes: Gyro X,Y,Z and Accel X,Y,Z."""
        if not HAVE_HARDWARE or self.i2c is None:
            self._sim_step = (self._sim_step + 1) % 360
            values = {
                "ax": 0.05,
                "ay": -0.02,
                "az": 9.81,
                "gx": 0.01,
                "gy": -0.01,
                "gz": 0.00,
            }
            return values, "OK", ""

        # Burst read 12 data bytes: GYR_X..Z (6B) then ACC_X..Z (6B)
        data = self.i2c.readfrom_mem(self.addr, self.REG_DATA_START, 12)
        gx_raw, gy_raw, gz_raw, ax_raw, ay_raw, az_raw = struct.unpack("<hhhhhh", data)

        # Scale Accel (±2g -> 16384 LSB/g) and Gyro (±250 deg/s -> 131.2 LSB/deg/s)
        ax = ax_raw / 16384.0
        ay = ay_raw / 16384.0
        az = az_raw / 16384.0

        gx = gx_raw / 131.2
        gy = gy_raw / 131.2
        gz = gz_raw / 131.2

        values = {
            "ax": round(ax, 2),
            "ay": round(ay, 2),
            "az": round(az, 2),
            "gx": round(gx, 2),
            "gy": round(gy, 2),
            "gz": round(gz, 2),
        }

        valid, warning = validate_metric_values("BMI160", values)
        status = "OK" if valid else "WARNING"
        return values, status, warning

    def deinit(self):
        """Suspend sensor to low power mode."""
        if HAVE_HARDWARE and self.i2c is not None:
            try:
                self.i2c.writeto_mem(self.addr, self.REG_CMD, bytes([self.CMD_SUSPEND]))
            except Exception:
                pass
        self.i2c = None
