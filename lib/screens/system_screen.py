"""System diagnostics and hardware status screen."""

import config
from lib.screens.base import BaseScreen
from lib import diagnostics
from lib import state


class SystemScreen(BaseScreen):
    """System information view corresponding to §5.5 of the technical specification."""

    def __init__(self):
        super().__init__("system")

    def render(self, disp):
        disp.clear(0)

        # 1. Header
        disp.text("SYSTEM INFO", 20, 0, 1)
        disp.hline(0, 9, 128, 1)

        # 2. Firmware and MicroPython versions
        diag = diagnostics.snapshot()
        disp.text("FW:v{} MPy:{}".format(config.APP_VERSION, diag["mpy_version"][:4]), 0, 12, 1)

        # 3. Heap memory statistics
        free_kb = diag["free_heap"] // 1024
        total_kb = diag["total_heap"] // 1024
        disp.text("Heap: {}K/{}K free".format(free_kb, total_kb), 0, 23, 1)

        # 4. Chip model
        chip_name = diag["machine"][:16]
        disp.text("Chip: {}".format(chip_name[:10]), 0, 34, 1)

        # 5. Last reset reason
        reset_desc = diag["reset_reason"][:16]
        disp.text("Rst: {}".format(reset_desc), 0, 45, 1)

        # 6. Power source profile
        p_src = state.get("power_source", "USB")
        disp.text("Power: {} Mode".format(p_src), 0, 56, 1)
