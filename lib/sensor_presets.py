"""Sensor presets, units, ranges, and configuration validation rules."""

# =============================================================================
# Sensor Presets Catalog
# =============================================================================

SENSOR_PRESETS = {
    "BME280": {
        "interface": "I2C",
        "description": "Temperature, Humidity and Pressure Sensor",
        "required_pins": ["sda", "scl"],
        "default_address": 0x76,
        "valid_addresses": [0x76, 0x77],
        "default_interval_ms": 3000,
        "min_interval_ms": 1000,
        "max_interval_ms": 60000,
        "metrics": {
            "temperature": {"unit": "C", "range": (-40.0, 85.0), "precision": 1},
            "humidity": {"unit": "%", "range": (0.0, 100.0), "precision": 1},
            "pressure": {"unit": "hPa", "range": (300.0, 1100.0), "precision": 1},
        },
    },
    "BMP280": {
        "interface": "I2C",
        "description": "Temperature and Pressure Sensor",
        "required_pins": ["sda", "scl"],
        "default_address": 0x76,
        "valid_addresses": [0x76, 0x77],
        "default_interval_ms": 3000,
        "min_interval_ms": 1000,
        "max_interval_ms": 60000,
        "metrics": {
            "temperature": {"unit": "C", "range": (-40.0, 85.0), "precision": 1},
            "pressure": {"unit": "hPa", "range": (300.0, 1100.0), "precision": 1},
        },
    },
    "BMI160": {
        "interface": "I2C",
        "description": "6-Axis Accelerometer and Gyroscope IMU",
        "required_pins": ["sda", "scl"],
        "default_address": 0x68,
        "valid_addresses": [0x68, 0x69],
        "default_interval_ms": 200,
        "min_interval_ms": 50,
        "max_interval_ms": 5000,
        "metrics": {
            "ax": {"unit": "g", "range": (-16.0, 16.0), "precision": 2},
            "ay": {"unit": "g", "range": (-16.0, 16.0), "precision": 2},
            "az": {"unit": "g", "range": (-16.0, 16.0), "precision": 2},
            "gx": {"unit": "deg/s", "range": (-2000.0, 2000.0), "precision": 2},
            "gy": {"unit": "deg/s", "range": (-2000.0, 2000.0), "precision": 2},
            "gz": {"unit": "deg/s", "range": (-2000.0, 2000.0), "precision": 2},
        },
    },
    "DS18B20": {
        "interface": "1-Wire",
        "description": "High-Precision 1-Wire Temperature Sensor",
        "required_pins": ["data"],
        "default_interval_ms": 5000,
        "min_interval_ms": 1000,
        "max_interval_ms": 60000,
        "metrics": {
            "temperature": {"unit": "C", "range": (-55.0, 125.0), "precision": 1},
        },
    },
    "DHT11": {
        "interface": "GPIO",
        "description": "Temperature and Humidity Sensor",
        "required_pins": ["data"],
        "default_interval_ms": 10000,
        "min_interval_ms": 2000,
        "max_interval_ms": 60000,
        "metrics": {
            "temperature": {"unit": "C", "range": (0.0, 50.0), "precision": 1},
            "humidity": {"unit": "%", "range": (20.0, 90.0), "precision": 1},
        },
    },
    "HC-SR04": {
        "interface": "GPIO",
        "description": "Ultrasonic Distance Sensor",
        "required_pins": ["trig", "echo"],
        "default_interval_ms": 1000,
        "min_interval_ms": 200,
        "max_interval_ms": 10000,
        "metrics": {
            "distance": {"unit": "cm", "range": (2.0, 400.0), "precision": 1},
        },
    },
    "PIR": {
        "interface": "GPIO",
        "description": "Passive Infrared Motion Sensor",
        "required_pins": ["data"],
        "default_interval_ms": 500,
        "min_interval_ms": 100,
        "max_interval_ms": 5000,
        "metrics": {
            "motion": {"unit": "", "range": (0, 1), "precision": 0},
        },
    },
}

# Forbidden / Reserved ESP32 GPIOs (Flash, UART0 console, strapping pins)
RESERVED_PINS = {
    1: "UART0 TX (Serial console)",
    3: "UART0 RX (Serial console)",
    6: "SPI Flash CLK",
    7: "SPI Flash SDO",
    8: "SPI Flash SDI",
    9: "SPI Flash SHD",
    10: "SPI Flash SWP",
    11: "SPI Flash CS",
}


# =============================================================================
# Configuration Validation
# =============================================================================

def validate_metric_values(sensor_type, values):
    """Validate measured values against physical preset range. Returns (is_valid, warning_msg)."""
    preset = SENSOR_PRESETS.get(sensor_type)
    if not preset:
        return True, ""

    metrics = preset.get("metrics", {})
    for key, val in values.items():
        if val is None:
            continue
        spec = metrics.get(key)
        if spec:
            min_val, max_val = spec["range"]
            if val < min_val or val > max_val:
                return False, "{}: {} out of range [{}, {}]".format(key, val, min_val, max_val)

    return True, ""


def validate_sensor_config(cfg, existing_sensors=None):
    """Validate sensor configuration dictionary against presets and pin collisions.

    Returns:
        (is_valid: bool, error_msg: str)
    """
    if not isinstance(cfg, dict):
        return False, "Config must be a dictionary"

    sensor_id = cfg.get("id")
    if not sensor_id or not isinstance(sensor_id, str):
        return False, "Missing or invalid sensor 'id'"

    sensor_type = cfg.get("type")
    if sensor_type not in SENSOR_PRESETS:
        return False, "Unsupported sensor type: {}".format(sensor_type)

    preset = SENSOR_PRESETS[sensor_type]

    # Validate interface
    interface = cfg.get("interface", preset["interface"])
    if interface != preset["interface"]:
        return False, "Invalid interface '{}' for {}. Expected '{}'".format(
            interface, sensor_type, preset["interface"]
        )

    # Validate required pins
    pins = cfg.get("pins", {})
    if not isinstance(pins, dict):
        return False, "Field 'pins' must be a dictionary"

    for req_pin in preset["required_pins"]:
        if req_pin not in pins:
            return False, "Missing required pin '{}' for {}".format(req_pin, sensor_type)
        pin_num = pins[req_pin]
        if not isinstance(pin_num, int) or pin_num < 0 or pin_num > 39:
            return False, "Pin '{}' must be integer between 0 and 39".format(req_pin)
        if pin_num in RESERVED_PINS:
            return False, "Pin {} is reserved: {}".format(pin_num, RESERVED_PINS[pin_num])

    # Validate I2C address
    if interface == "I2C":
        addr = cfg.get("address", preset.get("default_address"))
        if isinstance(addr, str):
            try:
                addr = int(addr, 16) if addr.startswith("0x") else int(addr)
            except ValueError:
                return False, "Invalid I2C address format: {}".format(addr)
        if addr not in preset["valid_addresses"]:
            return False, "I2C address 0x{:02X} invalid for {}. Allowed: {}".format(
                addr, sensor_type, [hex(a) for a in preset["valid_addresses"]]
            )

    # Validate polling interval
    poll_int = cfg.get("poll_interval_ms", preset["default_interval_ms"])
    if not isinstance(poll_int, int) or poll_int < preset["min_interval_ms"] or poll_int > preset["max_interval_ms"]:
        return False, "poll_interval_ms must be between {} and {}".format(
            preset["min_interval_ms"], preset["max_interval_ms"]
        )

    # Check conflicts with existing sensors
    if existing_sensors:
        for other in existing_sensors:
            if other.get("id") == sensor_id:
                continue  # Skip checking against self (e.g. on update)

            other_pins = other.get("pins", {})

            # Check I2C bus and address conflict
            if interface == "I2C" and other.get("interface") == "I2C":
                same_sda = pins.get("sda") == other_pins.get("sda")
                same_scl = pins.get("scl") == other_pins.get("scl")
                if same_sda and same_scl:
                    other_addr = other.get("address")
                    if isinstance(other_addr, str):
                        other_addr = int(other_addr, 16) if other_addr.startswith("0x") else int(other_addr)
                    this_addr = cfg.get("address", preset.get("default_address"))
                    if isinstance(this_addr, str):
                        this_addr = int(this_addr, 16) if this_addr.startswith("0x") else int(this_addr)

                    if this_addr == other_addr:
                        return False, "I2C address collision: address 0x{:02X} on pins (SDA:{}, SCL:{}) already used by {}".format(
                            this_addr, pins["sda"], pins["scl"], other.get("id")
                        )
                elif same_sda or same_scl:
                    return False, "Partial I2C pin conflict with sensor {}".format(other.get("id"))

            # Check GPIO conflicts for non-I2C or cross-interface collisions
            else:
                for p_name, p_val in pins.items():
                    for op_name, op_val in other_pins.items():
                        if p_val == op_val:
                            # 1-Wire allows multiple devices on same bus, others do not
                            if interface == "1-Wire" and other.get("interface") == "1-Wire":
                                continue
                            return False, "Pin {} is already in use by sensor {} ({})".format(
                                p_val, other.get("id"), op_name
                            )

    return True, ""
