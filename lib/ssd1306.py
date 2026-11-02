"""MicroPython SSD1306 OLED display driver for I2C and SPI interfaces."""

try:
    import framebuf
except ImportError:
    class FrameBufferMock:
        def __init__(self, buf, w, h, fmt):
            self.buf = buf
            self.w = w
            self.h = h
        def fill(self, col): pass
        def pixel(self, x, y, col=1): return 0
        def text(self, s, x, y, col=1): pass
        def hline(self, x, y, w, col=1): pass
        def vline(self, x, y, h, col=1): pass
        def line(self, x1, y1, x2, y2, col=1): pass
        def rect(self, x, y, w, h, col=1): pass
        def fill_rect(self, x, y, w, h, col=1): pass
    class FramebufModuleMock:
        FrameBuffer = FrameBufferMock
        MONO_VLSB = 1
        MONO_HLSB = 2
    framebuf = FramebufModuleMock()

# SSD1306 Command Registers
SET_CONTRAST = 0x81
SET_ENTIRE_ON = 0xA4
SET_NORM_INV = 0xA6
SET_DISP = 0xAE
SET_MEM_ADDR = 0x20
SET_COL_ADDR = 0x21
SET_PAGE_ADDR = 0x22
SET_DISP_START_LINE = 0x40
SET_SEG_REMAP = 0xA0
SET_MUX_RATIO = 0xA8
SET_COM_OUT_DIR = 0xC0
SET_DISP_OFFSET = 0xD3
SET_COM_PIN_CFG = 0xDA
SET_DISP_CLK_DIV = 0xD5
SET_PRECHARGE = 0xD9
SET_VCOM_DESEL = 0xDB
SET_CHARGE_PUMP = 0x8D


class SSD1306(framebuf.FrameBuffer):
    """Base framebuf-backed controller for SSD1306 OLED displays."""

    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def init_display(self):
        """Initialize OLED panel with standard SSD1306 configuration sequence."""
        for cmd in (
            SET_DISP,  # Display OFF
            SET_MEM_ADDR, 0x00,  # Horizontal addressing mode
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01,  # Column 127 mapped to SEG0
            SET_MUX_RATIO, self.height - 1,
            SET_COM_OUT_DIR | 0x08,  # Scan from COM[N] to COM0
            SET_DISP_OFFSET, 0x00,
            SET_COM_PIN_CFG, 0x02 if self.width > 2 * self.height else 0x12,
            SET_DISP_CLK_DIV, 0x80,
            SET_PRECHARGE, 0x22 if self.external_vcc else 0xF1,
            SET_VCOM_DESEL, 0x30,
            SET_CONTRAST, 0xFF,
            SET_ENTIRE_ON,
            SET_NORM_INV,
            SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01,  # Display ON
        ):
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        """Put display panel into low-power sleep mode."""
        self.write_cmd(SET_DISP)

    def poweron(self):
        """Turn display panel on from sleep mode."""
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        """Set screen contrast level (0-255)."""
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast & 0xFF)

    def invert(self, invert):
        """Invert display colors (1 = inverted, 0 = normal)."""
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        """Send internal framebuf buffer to the display RAM."""
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            x0 += 32
            x1 += 32
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)


class SSD1306_I2C(SSD1306):
    """SSD1306 controller using hardware or software I2C interface."""

    def __init__(self, width, height, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.cmd_buf = bytearray(2)
        self.write_list = [b"\x40", None]
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        """Write single command byte to I2C slave."""
        self.cmd_buf[0] = 0x80  # Co=1, D/C#=0
        self.cmd_buf[1] = cmd
        self.i2c.writeto(self.addr, self.cmd_buf)

    def write_data(self, buf):
        """Write frame buffer data bytes to I2C slave."""
        try:
            self.write_list[1] = buf
            self.i2c.writevto(self.addr, self.write_list)
        except (AttributeError, OSError):
            # Fallback for I2C implementations lacking writevto
            self.i2c.writeto_mem(self.addr, 0x40, buf)
