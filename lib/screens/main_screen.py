"""Main dashboard screen displaying time, network, sensors, power, and uptime."""

import time
from lib.screens.base import BaseScreen
from lib import state
from lib import time_service
from lib import diagnostics


class MainScreen(BaseScreen):
    """Primary system dashboard corresponding to §5.2 of the technical specification."""

    def __init__(self):
        super().__init__("main")

    def render(self, disp):
        disp.clear(0)

        # 1. Header with Title and Current Time (or --:--)
        if time_service.is_synced():
            t = time.gmtime()
            time_str = "{:02d}:{:02d}".format(t[3], t[4])
        else:
            time_str = "--:--"
        disp.text("ESP32 Stn  {}".format(time_str), 0, 0, 1)
        disp.hline(0, 9, 128, 1)

        # 2. Wi-Fi and MQTT connectivity indicators
        wifi_st = "OK" if state.get("wifi_state") == "CONNECTED" else "--"
        mqtt_st = "OK" if state.get("mqtt_state") == "CONNECTED" else "--"
        disp.text("WiFi:{} MQTT:{}".format(wifi_st, mqtt_st), 0, 12, 1)

        # 3. Active and configured sensors count
        active_s = state.get("sensors_active", 0)
        total_s = state.get("sensors_total", 0)
        disp.text("Sensors: {}/{}".format(active_s, total_s), 0, 23, 1)

        # 4. IP address or Access Point mode notification
        ip_addr = state.get("wifi_ip", "0.0.0.0")
        if state.get("wifi_mode") == "AP":
            disp.text("AP: 192.168.4.1", 0, 34, 1)
        elif ip_addr != "0.0.0.0":
            disp.text("IP: {}".format(ip_addr[:12]), 0, 34, 1)
        else:
            disp.text("IP: Disconnected", 0, 34, 1)

        # 5. Power source and battery voltage
        v_bat = state.get("battery_voltage")
        if v_bat is not None:
            disp.text("Battery: {:.1f}V".format(v_bat), 0, 45, 1)
        else:
            disp.text("Power: USB (5V)", 0, 45, 1)

        # 6. Device uptime
        uptime = diagnostics.get_uptime_sec()
        hours = (uptime // 3600) % 100
        mins = (uptime % 3600) // 60
        secs = uptime % 60
        disp.text("Uptime: {:02d}:{:02d}:{:02d}".format(hours, mins, secs), 0, 56, 1)
