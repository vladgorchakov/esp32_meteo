"""Display manager with double buffering, dirty region tracking, and font scaling."""

try:
    import framebuf
except ImportError:
    from lib.ssd1306 import framebuf
import board_config
from lib import state
from lib.ssd1306 import SSD1306_I2C

try:
    import machine
    HAVE_MACHINE = True
except ImportError:
    HAVE_MACHINE = False

WIDTH = 128
HEIGHT = 64
PAGES = HEIGHT // 8
BUFFER_SIZE = WIDTH * PAGES


class DisplayManager:
    """Manages OLED hardware lifecycle, double-buffering, and drawing primitives."""

    def __init__(self):
        self.width = WIDTH
        self.height = height = HEIGHT
        self.pages = PAGES
        self._is_on = True
        self._driver = None
        self._i2c = None

        # Double buffers: back buffer for drawing, front buffer for display sync
        self.back_buf = bytearray(BUFFER_SIZE)
        self.front_buf = bytearray(BUFFER_SIZE)

        # Drawing framebuffer attached to back_buf
        self.fb = framebuf.FrameBuffer(self.back_buf, self.width, self.height, framebuf.MONO_VLSB)

        # Temporary 8x8 buffer for scaling size=2 fonts
        self._char_buf = bytearray(8)
        self._char_fb = framebuf.FrameBuffer(self._char_buf, 8, 8, framebuf.MONO_VLSB)

    def init(self):
        """Initialize I2C bus and SSD1306 OLED panel."""
        if not HAVE_MACHINE:
            print("[DISPLAY] Running in simulation mode (no hardware I2C).")
            return True

        try:
            # Initialize hardware I2C
            self._i2c = machine.I2C(
                0,
                scl=machine.Pin(board_config.PIN_I2C_SCL),
                sda=machine.Pin(board_config.PIN_I2C_SDA),
                freq=board_config.I2C_FREQ_HZ,
            )

            # Check I2C bus presence
            devices = self._i2c.scan()
            if board_config.I2C_ADDR_SSD1306 not in devices:
                print(
                    "[DISPLAY] Warning: SSD1306 address 0x{:02X} not found on I2C bus. Found: {}".format(
                        board_config.I2C_ADDR_SSD1306, [hex(d) for d in devices]
                    )
                )

            # Create SSD1306 driver
            self._driver = SSD1306_I2C(
                self.width,
                self.height,
                self._i2c,
                addr=board_config.I2C_ADDR_SSD1306,
                external_vcc=False,
            )
            self._is_on = True
            state.set("display_on", True)
            self.clear()
            self.flush()
            print("[DISPLAY] SSD1306 128x64 initialized on I2C (addr=0x{:02X})".format(
                board_config.I2C_ADDR_SSD1306
            ))
            return True
        except Exception as exc:
            print("[DISPLAY] Error initializing SSD1306: {}".format(exc))
            self._driver = None
            return False

    def is_on(self):
        """Return True if display is powered on."""
        return self._is_on

    def on(self):
        """Power on OLED display."""
        if not self._is_on:
            self._is_on = True
            state.set("display_on", True)
            if self._driver:
                try:
                    self._driver.poweron()
                except Exception as exc:
                    print("[DISPLAY] Error powering on: {}".format(exc))
            self.flush(force=True)

    def off(self):
        """Power off OLED display (low-power sleep)."""
        if self._is_on:
            self._is_on = False
            state.set("display_on", False)
            if self._driver:
                try:
                    self._driver.poweroff()
                except Exception as exc:
                    print("[DISPLAY] Error powering off: {}".format(exc))

    def contrast(self, val):
        """Set display contrast level (0-255)."""
        if self._driver:
            try:
                self._driver.contrast(val)
            except Exception as exc:
                print("[DISPLAY] Error setting contrast: {}".format(exc))

    def clear(self, col=0):
        """Clear back buffer with given color (0 = black, 1 = white)."""
        self.fb.fill(col)

    def text(self, string, x, y, col=1, size=1):
        """Draw text string at (x, y). Supports size=1 (8x8) and size=2 (16x16 scaled)."""
        if size == 1:
            self.fb.text(string, x, y, col)
        elif size == 2:
            self._text_scaled(string, x, y, col)
        else:
            self.fb.text(string, x, y, col)

    def _text_scaled(self, string, start_x, start_y, col):
        """Render 2x scaled characters using pixel replication."""
        curr_x = start_x
        for ch in string:
            self._char_fb.fill(0)
            self._char_fb.text(ch, 0, 0, 1)

            # Replicate each active pixel into a 2x2 block
            for py in range(8):
                dest_y = start_y + py * 2
                if dest_y >= self.height:
                    break
                for px in range(8):
                    dest_x = curr_x + px * 2
                    if dest_x >= self.width:
                        break
                    if self._char_fb.pixel(px, py):
                        self.fb.fill_rect(dest_x, dest_y, 2, 2, col)
            curr_x += 16

    def pixel(self, x, y, col=1):
        """Set pixel color at (x, y)."""
        self.fb.pixel(x, y, col)

    def hline(self, x, y, w, col=1):
        """Draw horizontal line."""
        self.fb.hline(x, y, w, col)

    def vline(self, x, y, h, col=1):
        """Draw vertical line."""
        self.fb.vline(x, y, h, col)

    def line(self, x1, y1, x2, y2, col=1):
        """Draw arbitrary line from (x1, y1) to (x2, y2)."""
        self.fb.line(x1, y1, x2, y2, col)

    def rect(self, x, y, w, h, col=1):
        """Draw unfilled rectangle outline."""
        self.fb.rect(x, y, w, h, col)

    def fill_rect(self, x, y, w, h, col=1):
        """Draw filled rectangle."""
        self.fb.fill_rect(x, y, w, h, col)

    def flush(self, force=False):
        """Synchronize back buffer changes to front buffer and hardware display."""
        if not self._is_on:
            return

        if not force and self.back_buf == self.front_buf:
            return  # No changes detected, skip bus transmission

        if self._driver is not None:
            try:
                # Update driver's internal buffer and transmit
                self._driver.buffer[:] = self.back_buf
                self._driver.show()
            except Exception as exc:
                print("[DISPLAY] Flush I2C error: {}".format(exc))

        # Copy back buffer into front buffer
        self.front_buf[:] = self.back_buf


# Global singleton instance
display = DisplayManager()
