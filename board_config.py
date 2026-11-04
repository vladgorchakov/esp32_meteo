"""Hardware pinout and board-specific definitions for ESP32 WROOM-32 DevKit."""

# =============================================================================
# I2C Bus Architecture
# =============================================================================
# Bus 0: SSD1306 128x64 OLED Display (Hardware I2C0)
PIN_SSD1306_SDA = 21
PIN_SSD1306_SCL = 22
PIN_I2C_SDA = PIN_SSD1306_SDA  # Default / backward compatibility alias
PIN_I2C_SCL = PIN_SSD1306_SCL  # Default / backward compatibility alias
I2C_FREQ_HZ = 400000

# Bus 1: BME280 Environmental Sensor & BMI160 6-Axis IMU (Hardware I2C1 / SoftI2C)
PIN_BME280_SDA = 16
PIN_BME280_SCL = 17
PIN_BMI160_SDA = 16
PIN_BMI160_SCL = 17

# Bus 2: BMP280 Pressure/Temp Sensor (SoftI2C / Dedicated Bus to avoid 0x76 address clash)
PIN_BMP280_SDA = 18
PIN_BMP280_SCL = 23

# Default I2C Device Addresses
I2C_ADDR_SSD1306 = 0x3C  # SSD1306 128x64 OLED display (0x3C or 0x3D)
I2C_ADDR_BME280  = 0x76  # BME280 environmental sensor (0x76 or 0x77)
I2C_ADDR_BMP280  = 0x76  # BMP280 pressure/temp sensor (0x76 or 0x77)
I2C_ADDR_BMI160  = 0x68  # BMI160 6-axis IMU (0x68 or 0x69)

# =============================================================================
# Environmental & 1-Wire Sensors
# =============================================================================
# 1-Wire Bus: DS18B20 High-Precision Temperature Sensor (Requires 4.7k pull-up to 3.3V)
PIN_DS18B20 = 5
PIN_ONEWIRE = PIN_DS18B20  # Compatibility alias

# DHT11 Temperature & Humidity Sensor (Single-wire protocol, 10k pull-up recommended)
PIN_DHT11 = 19
PIN_DHT = PIN_DHT11        # Compatibility alias

# Optional / Expansion Sensors (reassigned placeholders)
PIN_HCSR04_TRIG = 12       # Ultrasonic trigger (optional)
PIN_HCSR04_ECHO = 14       # Ultrasonic echo (optional, requires voltage divider 5V->3.3V)
PIN_PIR = 15               # PIR motion sensor (optional)

# =============================================================================
# Power & Battery Voltage Monitoring
# =============================================================================
# Battery Voltage Monitoring (ADC1 only - GPIO 36 / SENSOR_VP, input only)
# Note: GPIO 34 was previously reserved for ADC, now assigned to BUTTON_2.
# GPIO 36 (ADC1_CH0) is input-only and ADC1 remains functional during Wi-Fi operation.
PIN_BATTERY_ADC = 36
BATTERY_DIVIDER_RATIO = 2.0  # R1=100k, R2=100k -> 2.0x factor
BATTERY_VREF_MV = 3300       # ADC reference voltage in mV

# =============================================================================
# User Interface: Buttons & Touch
# =============================================================================
PIN_STATUS_LED = 2         # Built-in LED on ESP32 DevKit board
PIN_BUTTON_BOOT = 0        # On-board BOOT button (active LOW)

# Navigation Buttons (Active LOW)
# IMPORTANT: GPIO 34 and GPIO 35 are GPI (input only) with NO internal pull-up!
# External pull-up resistors (10k to 3.3V) are required on hardware for buttons 2 & 5.
PIN_BUTTON_1 = 33          # BUTTON_1: Prev screen / Back in menu
PIN_BUTTON_2 = 34          # BUTTON_2: First screen / Up in menu (INPUT-ONLY, external pull-up required)
PIN_BUTTON_3 = 25          # BUTTON_3: Next screen / Forward/Confirm in menu
PIN_BUTTON_4 = 32          # BUTTON_4: Last screen / Down in menu
PIN_BUTTON_5 = 35          # BUTTON_5: Display toggle / Select in menu (INPUT-ONLY, external pull-up required)

# Touch Button (GPIO 4 is TouchPad 0 / T0)
PIN_TOUCH_BUTTON = 4       # TOUCH_BUTTON: Open/Close menu
TOUCH_USE_HARDWARE_TOUCHPAD = False  # Set to True for machine.TouchPad, False for digital Pin
BUTTON_ACTIVE_LEVEL = 0    # 0 = active LOW (pull-up to GND)

# =============================================================================
# User Interface: Rotary Encoder (EC11)
# =============================================================================
PIN_ROTARY_ENCODER_CLK = 27  # Rotary Encoder Clock / Channel A
PIN_ROTARY_ENCODER_DT  = 26  # Rotary Encoder Data / Channel B (DI)
PIN_ROTARY_ENCODER_SW  = 13  # Rotary Encoder Push Switch (active LOW, internal pull-up)

