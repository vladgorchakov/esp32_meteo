"""Dynamic individual sensor status screen for OLED display."""

import time
from lib.screens.base import BaseScreen
from lib import time_service
from lib.sensor_presets import SENSOR_PRESETS


class SensorScreen(BaseScreen):
    """Dynamic sensor view rendering metrics and status according to §5.3."""

    def __init__(self, sensor):
        super().__init__("sensor_" + sensor.id)
        self.sensor = sensor

    def render(self, disp):
        disp.clear(0)

        # 1. Header: "<TYPE>: <Name>"
        title = "{}: {}".format(self.sensor.type, self.sensor.name)
        disp.text(title[:16], 0, 0, 1)
        disp.hline(0, 9, 128, 1)

        # 2. Render depending on sensor state
        if self.sensor.state == "ERROR":
            disp.text("Status: ERROR", 0, 14, 1)
            err_line = self.sensor.last_error if self.sensor.last_error else "Offline"
            disp.text(err_line[:16], 0, 26, 1)
            if len(err_line) > 16:
                disp.text(err_line[16:32], 0, 37, 1)

            if self.sensor.last_ok_ts > 0:
                t = time.gmtime(self.sensor.last_ok_ts)
                disp.text("Last: {:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5]), 0, 52, 1)
            return

        # 3. Specialized Layout for BMI160 6-Axis IMU (§5.3)
        if self.sensor.type == "BMI160":
            v = self.sensor.last_values
            ax = v.get("ax", 0.0)
            ay = v.get("ay", 0.0)
            az = v.get("az", 0.0)
            gx = v.get("gx", 0.0)
            gy = v.get("gy", 0.0)
            gz = v.get("gz", 0.0)

            disp.text("AX:{:4.1f} AY:{:4.1f}".format(ax, ay), 0, 12, 1)
            disp.text("AZ:{:4.1f}".format(az), 0, 22, 1)
            disp.text("GX:{:4.1f} GY:{:4.1f}".format(gx, gy), 0, 33, 1)
            disp.text("GZ:{:4.1f}".format(gz), 0, 43, 1)

            # Footer status
            disp.text("St:{} {}".format(self.sensor.state, self._format_updated_time()), 0, 55, 1)
            return

        # 4. Standard Metric Layout for Environmental Sensors (BME280, BMP280, DS18B20, DHT11, etc.)
        preset = SENSOR_PRESETS.get(self.sensor.type, {})
        metrics = preset.get("metrics", {})
        values = self.sensor.last_values

        y = 12
        line_count = 0
        for m_key, m_spec in metrics.items():
            if m_key in values:
                val = values[m_key]
                unit = m_spec.get("unit", "")
                if val is not None:
                    # Short key abbreviation: temperature -> T, humidity -> H, pressure -> P, distance -> D
                    abbr = m_key[0].upper()
                    if m_key == "pressure":
                        abbr = "P"
                    elif m_key == "distance":
                        abbr = "Dist"
                    elif m_key == "motion":
                        disp.text("Motion: {}".format("DETECTED" if val else "NONE"), 0, y, 1)
                        y += 11
                        line_count += 1
                        continue

                    val_str = "{:.1f}".format(val) if isinstance(val, float) else str(val)
                    disp.text("{}: {} {}".format(abbr, val_str, unit).strip(), 0, y, 1)
                else:
                    disp.text("{}: -- {}".format(m_key[:4].capitalize(), unit), 0, y, 1)

                y += 11
                line_count += 1
                if line_count >= 3:
                    break

        # 5. Status & Update time footer
        disp.text("Status: {}".format(self.sensor.state), 0, y + 1, 1)
        disp.text("Upd: {}".format(self._format_updated_time()), 0, 55, 1)

    def _format_updated_time(self):
        """Format timestamp into HH:MM:SS or '--:--:--'."""
        if self.sensor.last_ok_ts > 0:
            t = time.gmtime(self.sensor.last_ok_ts)
            return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
        return "--:--:--"
