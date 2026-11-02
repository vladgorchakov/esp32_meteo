"""System time and SNTP network synchronization service for ESP32."""

import time

# Number of seconds between Unix epoch (1970-01-01) and MicroPython epoch (2000-01-01)
UNIX_EPOCH_OFFSET = 946684800

_time_synced = False
_last_sync_time = 0


def is_synced():
    """Return True if system time has been synchronized with SNTP or manual source."""
    return _time_synced


def now_unix():
    """Return current Unix timestamp in seconds (epoch 1970). Returns 0 if time is not synced."""
    if not _time_synced:
        return 0
    return time.time() + UNIX_EPOCH_OFFSET


def now_iso():
    """Return current UTC time in ISO-8601 format (YYYY-MM-DDTHH:MM:SSZ) or epoch default if unsynced."""
    if not _time_synced:
        return "1970-01-01T00:00:00Z"
    t = time.gmtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def sync_sntp(host="pool.ntp.org"):
    """Attempt SNTP time synchronization. Catches network failures gracefully."""
    global _time_synced, _last_sync_time
    try:
        import ntptime
        ntptime.host = host
        ntptime.settime()
        _time_synced = True
        _last_sync_time = time.time()
        print("[TIME] SNTP synchronized successfully with {}. Current UTC: {}".format(host, now_iso()))
        return True
    except Exception as exc:
        _time_synced = False
        print("[TIME] SNTP synchronization failed: {}. Continuing in unsynced mode.".format(exc))
        return False


def set_time_manual(unix_timestamp):
    """Set system RTC manually using a standard Unix timestamp (seconds since 1970)."""
    global _time_synced, _last_sync_time
    try:
        import machine
        mpy_sec = unix_timestamp - UNIX_EPOCH_OFFSET
        t = time.gmtime(mpy_sec)
        # machine.RTC().datetime tuple: (year, month, day, weekday, hour, minute, second, subsecond)
        rtc = machine.RTC()
        rtc.datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
        _time_synced = True
        _last_sync_time = time.time()
        print("[TIME] RTC set manually to Unix timestamp {}".format(unix_timestamp))
        return True
    except Exception as exc:
        print("[TIME] Failed to set RTC manually: {}".format(exc))
        return False
