"""Global application configuration, limits, and system paths."""

import sys

APP_NAME = "ESP32 Sensor Station"
APP_VERSION = "0.1.0"

# Filesystem Directory Paths (absolute on MicroPython root, relative in host simulation)
IS_MICROPYTHON = getattr(sys.implementation, "name", "") == "micropython"
if IS_MICROPYTHON:
    DIR_DATA = "/data"
    DIR_CERTS = "/certs"
    DIR_HISTORY = "/history"
else:
    DIR_DATA = "data"
    DIR_CERTS = "certs"
    DIR_HISTORY = "history"

# Configuration File Paths
PATH_SENSORS_CONFIG = DIR_DATA + "/sensors.json"
PATH_BROKERS_CONFIG = DIR_DATA + "/brokers.json"
PATH_ROUTING_CONFIG = DIR_DATA + "/routing.json"
PATH_POWER_CONFIG = DIR_DATA + "/power.json"

# System Limits & Capacities
MAX_SENSORS = 16
MAX_BROKERS = 4
MAX_NAME_LENGTH = 32
HISTORY_MAX_RECORDS = 1440  # 24 hours at 1 reading per minute

# Task Timing Defaults (Seconds)
DEFAULT_SENSOR_INTERVAL_SEC = 10
DEFAULT_PUBLISH_INTERVAL_SEC = 30
DEFAULT_UI_UPDATE_INTERVAL_SEC = 1
HEARTBEAT_INTERVAL_SEC = 30

# Logging Levels and Active Configuration
LOG_LEVEL_DEBUG = 10
LOG_LEVEL_INFO = 20
LOG_LEVEL_WARN = 30
LOG_LEVEL_ERROR = 40
CURRENT_LOG_LEVEL = LOG_LEVEL_INFO
