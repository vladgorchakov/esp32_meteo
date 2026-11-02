"""Wi-Fi network status screen."""

from lib.screens.base import BaseScreen
from lib import state


class WifiScreen(BaseScreen):
    """Network connection status screen corresponding to §5.4 of the technical specification."""

    def __init__(self):
        super().__init__("wifi")

    def render(self, disp):
        disp.clear(0)

        # 1. Header
        mode = state.get("wifi_mode", "STA")
        status = state.get("wifi_state", "DISCONNECTED")
        disp.text("WI-FI: {} ({})".format(mode, status[:3]), 0, 0, 1)
        disp.hline(0, 9, 128, 1)

        # 2. SSID
        ssid = state.get("wifi_ssid", "None")
        disp.text("SSID: {}".format(ssid[:10] if ssid else "None"), 0, 12, 1)

        # 3. IP Address
        ip = state.get("wifi_ip", "0.0.0.0")
        disp.text("IP: {}".format(ip[:12]), 0, 23, 1)

        # 4. Gateway
        gw = state.get("wifi_gw", "0.0.0.0")
        disp.text("GW: {}".format(gw[:12]), 0, 34, 1)

        # 5. RSSI signal strength
        rssi = state.get("wifi_rssi", 0)
        disp.text("RSSI: {} dBm".format(rssi), 0, 45, 1)

        # 6. Connected clients (AP mode) or MAC
        if mode == "AP":
            clients = state.get("wifi_clients", 0)
            disp.text("Clients: {}".format(clients), 0, 56, 1)
        else:
            mac = state.get("wifi_mac", "00:00:00:00:00:00")
            disp.text("MAC: {}".format(mac[-8:]), 0, 56, 1)
