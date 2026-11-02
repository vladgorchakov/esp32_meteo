# boot.py - ESP32 Sensor Station boot initialization
# This file is executed on board power-up before main.py.

import gc
import esp

# Disable noisy vendor OS debug messages on UART0
esp.osdebug(None)

# Activate garbage collector and set allocation threshold
gc.enable()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
