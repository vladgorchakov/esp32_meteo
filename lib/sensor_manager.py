"""Sensor manager orchestrating discovery, lifecycle, polling, validation, and events."""

import time
import config
import board_config
from lib import config_store
from lib import time_service
from lib import state
from lib.sensor_presets import SENSOR_PRESETS, validate_sensor_config

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

# Compatibility helpers for host environment simulation
if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.time() * 1000)
if not hasattr(time, "ticks_diff"):
    time.ticks_diff = lambda a, b: a - b
if not hasattr(time, "ticks_add"):
    time.ticks_add = lambda a, b: a + b
if not hasattr(asyncio, "sleep_ms"):
    asyncio.sleep_ms = lambda ms: asyncio.sleep(ms / 1000.0)

try:
    import machine
    HAVE_MACHINE = True
except ImportError:
    HAVE_MACHINE = False

# Import driver classes
from lib.sensors.bme280 import BME280Driver
from lib.sensors.bmp280 import BMP280Driver
from lib.sensors.bmi160 import BMI160Driver
from lib.sensors.ds18b20 import DS18B20Driver
from lib.sensors.dht11 import DHT11Driver
from lib.sensors.hc_sr04 import HCSR04Driver
from lib.sensors.pir import PIRDriver

DRIVER_REGISTRY = {
    "BME280": BME280Driver,
    "BMP280": BMP280Driver,
    "BMI160": BMI160Driver,
    "DS18B20": DS18B20Driver,
    "DHT11": DHT11Driver,
    "HC-SR04": HCSR04Driver,
    "PIR": PIRDriver,
}


class Sensor:
    """Represents a configured physical or virtual sensor instance."""

    def __init__(self, cfg):
        self.id = cfg["id"]
        self.name = cfg.get("name", self.id)
        self.type = cfg["type"]
        self.interface = cfg.get("interface", "GPIO")
        self.pins = cfg.get("pins", {})
        self.address = cfg.get("address")
        self.description = cfg.get("description", "")
        self.poll_interval_ms = cfg.get("poll_interval_ms", 5000)
        self.enabled = cfg.get("enabled", True)

        # Operational state
        self.state = "NOT_CONFIGURED" if not self.enabled else "INITIALIZING"
        self.last_ok_ts = 0
        self.last_values = {}
        self.last_error = ""
        self.error_count = 0
        self.consecutive_errors = 0
        self.error_logged = False
        self.backoff_ms = 0
        self.next_run_ms = time.ticks_ms()

        self.driver = None
        self.is_dirty = True

    def to_dict(self):
        """Serialize sensor configuration for JSON persistence."""
        res = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "interface": self.interface,
            "pins": self.pins,
            "poll_interval_ms": self.poll_interval_ms,
            "enabled": self.enabled,
            "description": self.description,
        }
        if self.address is not None:
            res["address"] = "0x{:02X}".format(self.address) if isinstance(self.address, int) else self.address
        return res


class SensorManager:
    """Manages sensor instances, shared I2C buses, polling schedules, and event queues."""

    def __init__(self):
        self.sensors = {}
        self.event_queue = asyncio.Queue(maxsize=32)
        self._i2c_buses = {}
        self._running = False
        self._on_update_callback = None

    def set_update_callback(self, cb):
        """Register callback invoked whenever sensor data is refreshed."""
        self._on_update_callback = cb

    def get_i2c_bus(self, sda_pin, scl_pin):
        """Retrieve or create shared I2C bus instance for given SDA/SCL pin pair."""
        key = (sda_pin, scl_pin)
        if key in self._i2c_buses:
            return self._i2c_buses[key]

        if not HAVE_MACHINE:
            self._i2c_buses[key] = None
            return None

        bus = None
        try:
            # Check if matching BME280 / BMI160 bus pins
            if key == (getattr(board_config, "PIN_BME280_SDA", 16), getattr(board_config, "PIN_BME280_SCL", 17)):
                try:
                    bus = machine.I2C(1, scl=machine.Pin(scl_pin), sda=machine.Pin(sda_pin), freq=board_config.I2C_FREQ_HZ)
                except Exception:
                    bus = machine.SoftI2C(scl=machine.Pin(scl_pin), sda=machine.Pin(sda_pin), freq=board_config.I2C_FREQ_HZ)
            else:
                # SoftI2C for dedicated buses (e.g. BMP280 on 18/23)
                bus = machine.SoftI2C(scl=machine.Pin(scl_pin), sda=machine.Pin(sda_pin), freq=board_config.I2C_FREQ_HZ)

            print("[SENSOR] Configured I2C bus for SDA:{} SCL:{}".format(sda_pin, scl_pin))
        except Exception as exc:
            print("[SENSOR] Error initializing I2C bus (SDA:{} SCL:{}): {}".format(sda_pin, scl_pin, exc))

        self._i2c_buses[key] = bus
        return bus

    def init(self):
        """Load sensor configurations from filesystem or generate board defaults."""
        raw_cfg = config_store.load_json(config.PATH_SENSORS_CONFIG, default={})

        # If configuration file is empty, generate default presets based on board wiring
        if not raw_cfg:
            print("[SENSOR] sensors.json is empty. Generating board default presets...")
            raw_cfg = self._generate_board_defaults()
            config_store.save_json(config.PATH_SENSORS_CONFIG, raw_cfg)

        # Instantiate validated sensors
        existing_list = []
        for s_id, s_data in raw_cfg.items():
            if not isinstance(s_data, dict):
                continue
            s_data["id"] = s_id
            is_valid, err = validate_sensor_config(s_data, existing_list)
            if not is_valid:
                print("[SENSOR] Skipping invalid sensor config '{}': {}".format(s_id, err))
                continue

            existing_list.append(s_data)
            sensor = Sensor(s_data)
            self.sensors[sensor.id] = sensor

        # Initialize hardware drivers for all enabled sensors
        for sensor in self.sensors.values():
            if sensor.enabled:
                self._init_sensor_driver(sensor)

        self._sync_state()
        print("[SENSOR] Initialized {} configured sensors ({} active)".format(
            len(self.sensors), sum(1 for s in self.sensors.values() if s.state == "OK")
        ))

    def _generate_board_defaults(self):
        """Build initial sensor dictionary based on board_config.py pin assignments."""
        return {
            "bme280_1": {
                "name": "Room Climate",
                "type": "BME280",
                "interface": "I2C",
                "address": "0x76",
                "pins": {
                    "sda": getattr(board_config, "PIN_BME280_SDA", 16),
                    "scl": getattr(board_config, "PIN_BME280_SCL", 17),
                },
                "poll_interval_ms": 3000,
                "enabled": True,
                "description": "Indoor temperature, humidity, and atmospheric pressure",
            },
            "bmp280_1": {
                "name": "Barometer",
                "type": "BMP280",
                "interface": "I2C",
                "address": "0x76",
                "pins": {
                    "sda": getattr(board_config, "PIN_BMP280_SDA", 18),
                    "scl": getattr(board_config, "PIN_BMP280_SCL", 23),
                },
                "poll_interval_ms": 3000,
                "enabled": True,
                "description": "Secondary atmospheric pressure and temperature sensor",
            },
            "bmi160_1": {
                "name": "Motion IMU",
                "type": "BMI160",
                "interface": "I2C",
                "address": "0x68",
                "pins": {
                    "sda": getattr(board_config, "PIN_BMI160_SDA", 16),
                    "scl": getattr(board_config, "PIN_BMI160_SCL", 17),
                },
                "poll_interval_ms": 200,
                "enabled": True,
                "description": "6-axis accelerometer and gyroscope IMU",
            },
            "ds18b20_1": {
                "name": "Precision Temp",
                "type": "DS18B20",
                "interface": "1-Wire",
                "pins": {
                    "data": getattr(board_config, "PIN_DS18B20", 5),
                },
                "poll_interval_ms": 5000,
                "enabled": True,
                "description": "1-Wire digital temperature probe",
            },
            "dht11_1": {
                "name": "DHT Ambience",
                "type": "DHT11",
                "interface": "GPIO",
                "pins": {
                    "data": getattr(board_config, "PIN_DHT11", 19),
                },
                "poll_interval_ms": 10000,
                "enabled": True,
                "description": "Ambient temperature and humidity sensor",
            },
        }

    def _init_sensor_driver(self, sensor):
        """Instantiate and configure hardware driver for individual sensor."""
        driver_cls = DRIVER_REGISTRY.get(sensor.type)
        if not driver_cls:
            sensor.state = "ERROR"
            sensor.last_error = "Driver not implemented for {}".format(sensor.type)
            return False

        try:
            sensor.driver = driver_cls()
            if sensor.interface == "I2C":
                sda = sensor.pins.get("sda")
                scl = sensor.pins.get("scl")
                i2c_bus = self.get_i2c_bus(sda, scl)
                sensor.driver.init(sensor.to_dict(), i2c_bus=i2c_bus)
            else:
                sensor.driver.init(sensor.to_dict())

            sensor.state = "INITIALIZING"
            sensor.last_error = ""
            return True
        except Exception as exc:
            sensor.state = "ERROR"
            sensor.last_error = str(exc)
            if not sensor.error_logged:
                print("[SENSOR_{}] ERROR initializing: {}".format(sensor.id, exc))
                sensor.error_logged = True
            return False

    async def _poll_sensor(self, sensor, now_ms):
        """Execute acquisition cycle for single sensor instance."""
        # 1. Ensure driver is initialized
        if sensor.driver is None or sensor.state == "ERROR":
            if not self._init_sensor_driver(sensor):
                # Backoff retry
                sensor.backoff_ms = min(sensor.backoff_ms * 2 if sensor.backoff_ms > 0 else 2000, 30000)
                sensor.next_run_ms = time.ticks_add(now_ms, sensor.backoff_ms)
                return

        # 2. Acquire measurement (supporting both async and sync driver contracts)
        try:
            read_fn = getattr(sensor.driver, "read")
            if asyncio.iscoroutinefunction(read_fn):
                values, status, warning = await read_fn()
            else:
                values, status, warning = read_fn()

            # Successful acquisition
            if sensor.error_logged:
                print("[SENSOR_{}] recovered".format(sensor.id))
                sensor.error_logged = False

            sensor.state = status
            sensor.last_values = values
            sensor.last_error = warning
            sensor.last_ok_ts = time_service.now_unix()
            sensor.consecutive_errors = 0
            sensor.backoff_ms = 0
            sensor.is_dirty = True
            sensor.next_run_ms = time.ticks_add(now_ms, sensor.poll_interval_ms)

            # Publish event to bounded sliding event queue
            event_payload = (sensor.id, values, status, sensor.last_ok_ts)
            try:
                if self.event_queue.full():
                    try:
                        self.event_queue.get_nowait()
                    except Exception:
                        pass
                self.event_queue.put_nowait(event_payload)
            except Exception:
                pass

        except Exception as exc:
            # Handle hardware failure
            sensor.state = "ERROR"
            sensor.error_count += 1
            sensor.consecutive_errors += 1
            sensor.last_error = str(exc)
            sensor.is_dirty = True

            if not sensor.error_logged:
                print("[SENSOR_{}] ERROR: {}".format(sensor.id, exc))
                sensor.error_logged = True

            # Exponential backoff on communication error
            sensor.backoff_ms = min(sensor.backoff_ms * 2 if sensor.backoff_ms > 0 else 2000, 30000)
            sensor.next_run_ms = time.ticks_add(now_ms, sensor.backoff_ms)

    def _sync_state(self):
        """Synchronize active sensor snapshots into global state repository."""
        data_snapshot = {}
        active_count = 0

        for s in self.sensors.values():
            if s.state in ("OK", "WARNING"):
                active_count += 1
            data_snapshot[s.id] = {
                "name": s.name,
                "type": s.type,
                "state": s.state,
                "values": s.last_values,
                "last_ok_ts": s.last_ok_ts,
                "error": s.last_error,
            }

        state.set("sensors_total", len(self.sensors))
        state.set("sensors_active", active_count)
        state.set("sensors_data", data_snapshot)

        if self._on_update_callback:
            try:
                self._on_update_callback()
            except Exception:
                pass

    async def poll_task(self):
        """Asynchronous scheduler polling due sensors with isolated timing intervals."""
        self._running = True
        print("[SENSOR] Sensor polling task started")

        while self._running:
            now_ms = time.ticks_ms()
            due_sensors = []
            min_remaining_ms = 1000

            for sensor in self.sensors.values():
                if not sensor.enabled:
                    continue

                diff = time.ticks_diff(sensor.next_run_ms, now_ms)
                if diff <= 0:
                    due_sensors.append(sensor)
                elif diff < min_remaining_ms:
                    min_remaining_ms = diff

            # Poll due sensors sequentially
            for sensor in due_sensors:
                await self._poll_sensor(sensor, now_ms)

            self._sync_state()

            # Sleep until next scheduled sensor run (or at least 25ms, at most 100ms)
            sleep_time = max(25, min(min_remaining_ms, 100))
            await asyncio.sleep_ms(sleep_time)

    def get_sensor(self, sensor_id):
        """Retrieve sensor instance by ID."""
        return self.sensors.get(sensor_id)

    def get_all_sensors(self):
        """Return list of all configured sensors."""
        return list(self.sensors.values())


# Global singleton instance
sensor_mgr = SensorManager()
