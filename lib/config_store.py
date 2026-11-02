"""Filesystem and JSON configuration persistence service with atomic write and integrity checks."""

import os
import json
import config

SENSITIVE_KEYS = {
    "password",
    "private_key",
    "ca_certificate",
    "client_certificate",
    "token",
    "secret",
    "api_key",
}


def sanitize_for_log(data):
    """Recursively redact sensitive credential keys from dict or list structures for safe logging."""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in str(key).lower() for sensitive in SENSITIVE_KEYS):
                sanitized[key] = "******"
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_for_log(value)
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, list):
        return [sanitize_for_log(item) for item in data]
    return data


def file_exists(path):
    """Check if a file or directory exists on the filesystem."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _ensure_dir(path):
    """Create directory if it does not already exist."""
    try:
        os.stat(path)
    except OSError:
        try:
            os.mkdir(path)
            print("[CONFIG] Created directory: {}".format(path))
        except OSError as exc:
            print("[CONFIG] Failed to create directory {}: {}".format(path, exc))


def ensure_dirs():
    """Ensure all required system directories and default config files exist."""
    for directory in (config.DIR_DATA, config.DIR_CERTS, config.DIR_HISTORY):
        _ensure_dir(directory)

    # Initialize default configuration files if they are missing
    defaults = (
        (config.PATH_SENSORS_CONFIG, {}),
        (config.PATH_BROKERS_CONFIG, []),
        (config.PATH_ROUTING_CONFIG, []),
        (
            config.PATH_POWER_CONFIG,
            {
                "power_mode": "always_on",
                "sleep_duration_sec": 60,
                "battery_adc_enabled": False,
                "battery_min_voltage": 3.3,
            },
        ),
    )

    for file_path, default_content in defaults:
        if not file_exists(file_path):
            print("[CONFIG] Initializing missing default config: {}".format(file_path))
            save_json(file_path, default_content, atomic=True)


def load_json(path, default=None):
    """Load and parse JSON from file path. Returns default value on error or corrupted file."""
    if not file_exists(path):
        return default

    try:
        with open(path, "r") as f:
            content = f.read()
        if not content.strip():
            print("[CONFIG] Empty file encountered at {}, returning default".format(path))
            return default
        return json.loads(content)
    except Exception as exc:
        print("[CONFIG] JSON load/parse error at {}: {}. Falling back to default.".format(path, exc))
        return default


def save_json(path, data, atomic=True):
    """Save serializable data to JSON file. Supports atomic write via temporary file."""
    try:
        json_str = json.dumps(data)
    except Exception as exc:
        print("[CONFIG] Failed to serialize data for {}: {}".format(path, exc))
        return False

    if not atomic:
        try:
            with open(path, "w") as f:
                f.write(json_str)
            return True
        except OSError as exc:
            print("[CONFIG] Error writing directly to {}: {}".format(path, exc))
            return False

    temp_path = "{}.tmp".format(path)
    try:
        with open(temp_path, "w") as f:
            f.write(json_str)

        # Atomic rename handling cross-platform MicroPython quirks
        try:
            os.rename(temp_path, path)
        except OSError:
            try:
                os.remove(path)
            except OSError:
                pass
            os.rename(temp_path, path)
        return True
    except OSError as exc:
        print("[CONFIG] Atomic save error for {}: {}".format(path, exc))
        try:
            if file_exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        return False


def delete_file(path):
    """Safely delete a file if it exists."""
    if file_exists(path):
        try:
            os.remove(path)
            print("[CONFIG] Deleted file: {}".format(path))
            return True
        except OSError as exc:
            print("[CONFIG] Error deleting file {}: {}".format(path, exc))
            return False
    return False
