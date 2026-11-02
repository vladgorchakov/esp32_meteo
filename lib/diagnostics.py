"""Hardware and system diagnostics service for ESP32 platform."""

import gc
import sys
import os
import time

try:
    import machine
    HAVE_MACHINE = True
except ImportError:
    HAVE_MACHINE = False

RESET_REASONS = {
    1: "Power-on Reset",        # machine.PWRON_RESET
    2: "Hard Reset",            # machine.HARD_RESET
    3: "Watchdog Reset",        # machine.WDT_RESET
    4: "Deep-Sleep Wakeup",     # machine.DEEPSLEEP_RESET
    5: "Soft Reset",            # machine.SOFT_RESET
}


def get_reset_reason():
    """Retrieve the platform reset cause code and human-readable description."""
    if not HAVE_MACHINE:
        return (0, "Simulated Environment")
    try:
        cause = machine.reset_cause()
        desc = RESET_REASONS.get(cause, "Unknown Reset ({})".format(cause))
        return (cause, desc)
    except Exception as exc:
        return (-1, "Error detecting reset cause: {}".format(exc))


def get_heap_stats():
    """Return dictionary of free, allocated, and total heap bytes."""
    if hasattr(gc, "mem_free"):
        free_b = gc.mem_free()
        alloc_b = gc.mem_alloc()
    else:
        # Fallback for host environment simulation
        free_b = 0
        alloc_b = 0
    return {
        "free": free_b,
        "allocated": alloc_b,
        "total": free_b + alloc_b,
    }


def get_uptime_sec():
    """Return device uptime in seconds calculated from monotonic tick counter."""
    try:
        return time.ticks_ms() // 1000
    except (AttributeError, TypeError):
        return int(time.time())


def get_platform_info():
    """Return system platform, chip, and MicroPython runtime details."""
    uname = os.uname()
    mpy_ver = ".".join(str(x) for x in sys.implementation.version)
    return {
        "platform": sys.platform,
        "machine": uname.machine if hasattr(uname, "machine") else str(uname[4]),
        "mpy_version": mpy_ver,
        "sys_version": sys.version,
    }


def snapshot():
    """Capture a comprehensive dictionary snapshot of current device diagnostics."""
    reset_code, reset_desc = get_reset_reason()
    heap = get_heap_stats()
    platform_info = get_platform_info()

    return {
        "uptime_sec": get_uptime_sec(),
        "free_heap": heap["free"],
        "alloc_heap": heap["allocated"],
        "total_heap": heap["total"],
        "reset_code": reset_code,
        "reset_reason": reset_desc,
        "platform": platform_info["platform"],
        "machine": platform_info["machine"],
        "mpy_version": platform_info["mpy_version"],
    }
