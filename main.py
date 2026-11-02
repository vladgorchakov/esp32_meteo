"""ESP32 Sensor Station - Main Application Entrypoint."""

import gc
import config
from lib import config_store
from lib import time_service
from lib import diagnostics

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio


# -----------------------------------------------------------------------------
# Placeholder Coroutines for Future Phases (Next Phases)
# -----------------------------------------------------------------------------

async def task_display_runner():
    """Placeholder task for SSD1306 OLED display UI rendering."""
    print("[UI] next phase: OLED UI loop")
    while True:
        await asyncio.sleep(config.DEFAULT_UI_UPDATE_INTERVAL_SEC)


async def task_sensor_runner():
    """Placeholder task for scheduled sensor acquisition (BME280, DS18B20, etc.)."""
    print("[SENSOR] next phase: Sensor polling loop")
    while True:
        await asyncio.sleep(config.DEFAULT_SENSOR_INTERVAL_SEC)


async def task_network_runner():
    """Placeholder task for Wi-Fi station management and reconnection logic."""
    print("[WIFI] next phase: WiFi connection manager")
    while True:
        await asyncio.sleep(60)


async def task_mqtt_runner():
    """Placeholder task for MQTT client connection and data telemetry publishing."""
    print("[MQTT] next phase: MQTT publishing loop")
    while True:
        await asyncio.sleep(config.DEFAULT_PUBLISH_INTERVAL_SEC)


async def task_heartbeat_runner():
    """Periodic system health heartbeat logger."""
    while True:
        await asyncio.sleep(config.HEARTBEAT_INTERVAL_SEC)
        gc.collect()
        diag = diagnostics.snapshot()
        print(
            "[SYS] Heartbeat: uptime={}s, free_heap={}B, synced={}".format(
                diag["uptime_sec"], diag["free_heap"], time_service.is_synced()
            )
        )


# -----------------------------------------------------------------------------
# Main Application Orchestrator
# -----------------------------------------------------------------------------

async def main_async():
    """Async main routine launching background services."""
    print("[SYS] Launching background asyncio tasks...")

    # Spawn asynchronous service tasks into event loop
    asyncio.create_task(task_display_runner())
    asyncio.create_task(task_sensor_runner())
    asyncio.create_task(task_network_runner())
    asyncio.create_task(task_mqtt_runner())
    asyncio.create_task(task_heartbeat_runner())

    print("[SYS] All background tasks scheduled. Event loop running.")

    # Keep root task active
    while True:
        await asyncio.sleep(3600)


def start():
    """Synchronous initialization and startup sequence."""
    print("\n" + "=" * 50)
    print("  {} v{}".format(config.APP_NAME, config.APP_VERSION))
    print("=" * 50)

    # 1. Ensure required filesystem directories and default JSON configuration files
    print("[BOOT] Verifying filesystem directories and configuration store...")
    config_store.ensure_dirs()

    # 2. Collect and log system diagnostics
    diag = diagnostics.snapshot()
    print("[SYS] Platform: {}".format(diag["machine"]))
    print("[SYS] MicroPython: {}".format(diag["mpy_version"]))
    print("[SYS] Reset Cause: [{}] {}".format(diag["reset_code"], diag["reset_reason"]))
    print("[SYS] Initial Free Heap: {} bytes (Total: {} bytes)".format(diag["free_heap"], diag["total_heap"]))

    # 3. Initialize time service
    print("[TIME] Time service initialized. Synced: {} (Unix: {})".format(
        time_service.is_synced(), time_service.now_unix()
    ))

    # 4. Start asyncio event loop
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[SYS] Execution interrupted by user (KeyboardInterrupt).")
    except Exception as exc:
        print("\n[CRITICAL] Unhandled exception in event loop: {}".format(exc))


if __name__ == "__main__":
    start()
