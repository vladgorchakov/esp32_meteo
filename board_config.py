"""Hardware pinout and board-specific definitions for ESP32 WROOM-32 DevKit."""

# I2C Bus Configuration (Default ESP32 hardware I2C)
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22
I2C_FREQ_HZ = 400000

# Default I2C Device Addresses
I2C_ADDR_SSD1306 = 0x3C  # SSD1306 128x64 OLED display
I2C_ADDR_BME280 = 0x76   # BME280 / BMP280 environmental sensor (0x76 or 0x77)
I2C_ADDR_BMI160 = 0x68   # BMI160 6-axis IMU (0x68 or 0x69)

# 1-Wire Bus (DS18B20 Temperature Sensors)
PIN_ONEWIRE = 4          # PLACEHOLDER — adjust to actual wiring (requires 4.7k pull-up)

# DHT Sensor (DHT11 / DHT22)
PIN_DHT = 14             # PLACEHOLDER — adjust to actual wiring

# HC-SR04 Ultrasonic Distance Sensor
PIN_HCSR04_TRIG = 12     # PLACEHOLDER — adjust to actual wiring
PIN_HCSR04_ECHO = 13     # PLACEHOLDER — adjust to actual wiring (use voltage divider 5V->3.3V)

# PIR Motion Sensor
PIN_PIR = 19             # PLACEHOLDER — adjust to actual wiring

# Battery Voltage Monitoring (ADC1 only, input-only pins)
PIN_BATTERY_ADC = 34     # PLACEHOLDER — adjust to actual wiring (ADC1_CH6, input only)
BATTERY_DIVIDER_RATIO = 2.0  # R1=100k, R2=100k -> 2.0x factor
BATTERY_VREF_MV = 3300       # ADC reference voltage in mV

# User Interface Hardware
PIN_STATUS_LED = 2       # Built-in LED on ESP32 DevKit board
PIN_BUTTON_BOOT = 0      # On-board BOOT button (active LOW)

# Navigation Buttons (Active LOW with internal pull-up)
# TODO: assign on target board (placeholder pins for DevKit)
PIN_BUTTON_1 = 32        # BUTTON_1: Prev screen / Back in menu
PIN_BUTTON_2 = 33        # BUTTON_2: First screen / Up in menu
PIN_BUTTON_3 = 25        # BUTTON_3: Next screen / Forward/Confirm in menu
PIN_BUTTON_4 = 26        # BUTTON_4: Last screen / Down in menu
PIN_BUTTON_5 = 15        # BUTTON_5: Display toggle / Select item in menu
PIN_TOUCH_BUTTON = 27    # TOUCH_BUTTON: Open/Close menu (Touch pad or digital button)
