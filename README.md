# ESP32 Sensor Station (MicroPython)

Production-grade IoT environmental monitoring station for ESP32 WROOM-32.

---

## 1. Project Requirements & Stack

- **Hardware**: ESP32 WROOM-32 DevKit (4MB Flash).
- **Firmware**: MicroPython v1.24+ (`ESP32_GENERIC-*.bin`).
- **Concurrency**: `asyncio` (`uasyncio` under MicroPython).
- **Filesystem**: LittleFS with atomic JSON configuration persistence.
- **Tools**: `esptool.py`, `mpremote` (or `ampy` / Thonny IDE).

---

## 2. Directory Structure

```text
/
├── boot.py               # Minimal boot-time initialization & GC tuning
├── main.py               # Application orchestrator & asyncio event loop
├── config.py             # System paths, limits, intervals, log constants
├── board_config.py       # Hardware pin definitions & I2C addresses
├── lib/
│   ├── config_store.py   # Atomic JSON storage & integrity fallback
│   ├── time_service.py   # SNTP sync & 1970 POSIX Unix timestamp provider
│   └── diagnostics.py    # Reset cause, chip info, heap & uptime snapshot
├── data/                 # JSON configurations (created on first boot)
│   ├── sensors.json      # {}
│   ├── brokers.json      # []
│   ├── routing.json      # []
│   └── power.json        # Default power configuration
├── certs/                # TLS certificates (populated in MQTT/TLS phases)
├── history/              # 24h rolling local sensor history files
└── README.md
```

---

## 3. Firmware Flashing

1. Install `esptool` and `mpremote`:
   ```bash
   pip install esptool mpremote
   ```

2. Connect your ESP32 board via USB (determine port, e.g. `/dev/ttyUSB0` or `COM3`).

3. Erase existing flash:
   ```bash
   esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
   ```

4. Flash MicroPython v1.24+ firmware (baudrate 460800):
   ```bash
   esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-*.bin
   ```

---

## 4. Uploading Project Files

Use `mpremote` for fast recursive synchronization:

```bash
# Verify connection
mpremote connect /dev/ttyUSB0

# Upload code and data to device root
mpremote connect /dev/ttyUSB0 cp -r . :
```

*Alternatively, using `ampy`:*
```bash
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put main.py
ampy --port /dev/ttyUSB0 put config.py
ampy --port /dev/ttyUSB0 put board_config.py
ampy --port /dev/ttyUSB0 put lib
ampy --port /dev/ttyUSB0 put data
```

---

## 5. First Boot & Verification

Open the REPL console:
```bash
mpremote connect /dev/ttyUSB0 repl
```
Press the **EN / RST** button on the ESP32. You should see output similar to:

```text
==================================================
  ESP32 Sensor Station v0.1.0
==================================================
[BOOT] Verifying filesystem directories and configuration store...
[SYS] Platform: ESP32 module with ESP32
[SYS] MicroPython: 1.24.1
[SYS] Reset Cause: [1] Power-on Reset
[SYS] Initial Free Heap: 111456 bytes (Total: 125952 bytes)
[TIME] Time service initialized. Synced: False (Unix: 0)
[SYS] Launching background asyncio tasks...
[UI] next phase: OLED UI loop
[SENSOR] next phase: Sensor polling loop
[WIFI] next phase: WiFi connection manager
[MQTT] next phase: MQTT publishing loop
[SYS] All background tasks scheduled. Event loop running.
[SYS] Heartbeat: uptime=30s, free_heap=110820B, synced=False
```

### Verification Checklist:
1. **Directories created**: Check via REPL:
   ```python
   import os
   os.listdir('/')
   # Output: ['boot.py', 'main.py', 'config.py', 'board_config.py', 'lib', 'data', 'certs', 'history']
   os.listdir('/data')
   # Output: ['sensors.json', 'brokers.json', 'routing.json', 'power.json']
   ```
2. **Atomic save & reload test**:
   ```python
   from lib import config_store
   config_store.save_json("/data/test.json", {"key": "value"})
   config_store.load_json("/data/test.json")
   # Returns: {'key': 'value'}
   ```
3. **Corrupted file recovery**:
   ```python
   with open("/data/bad.json", "w") as f:
       f.write("{invalid_json:")
   config_store.load_json("/data/bad.json", default={"fallback": True})
   # Returns: {'fallback': True} with logged warning
   ```

---

## 6. Factory Reset Procedure

To restore default configuration, remove the contents of `/data` or delete the directory:

Via `mpremote`:
```bash
mpremote connect /dev/ttyUSB0 rm :data/sensors.json
mpremote connect /dev/ttyUSB0 rm :data/brokers.json
mpremote connect /dev/ttyUSB0 rm :data/routing.json
mpremote connect /dev/ttyUSB0 rm :data/power.json
mpremote connect /dev/ttyUSB0 rmdir :data
```
On next reboot, `main.py` will automatically recreate `/data` and write fresh default configurations.
