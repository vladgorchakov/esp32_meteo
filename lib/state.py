"""Shared application state repository for decoupled cross-module communication."""

_state = {
    # Network status
    "wifi_state": "DISCONNECTED",
    "wifi_ssid": "",
    "wifi_ip": "0.0.0.0",
    "wifi_gw": "0.0.0.0",
    "wifi_mac": "00:00:00:00:00:00",
    "wifi_rssi": 0,
    "wifi_clients": 0,
    "wifi_mode": "STA",  # STA or AP

    # MQTT status
    "mqtt_state": "DISCONNECTED",
    "mqtt_connected_brokers": 0,
    "mqtt_total_brokers": 0,

    # Sensor status
    "sensors_total": 0,
    "sensors_active": 0,

    # Power & Battery
    "power_source": "USB",
    "battery_voltage": None,
    "battery_percent": None,

    # Display & Alerts
    "display_on": True,
    "critical_alert": None,
}


def get(key, default=None):
    """Retrieve state value by key."""
    return _state.get(key, default)


def set(key, value):
    """Update state value by key."""
    _state[key] = value


def update(mapping):
    """Update multiple state values simultaneously."""
    _state.update(mapping)


def get_all():
    """Return a shallow copy of the full state dictionary."""
    return dict(_state)
