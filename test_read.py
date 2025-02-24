import vxi11
import time
import math
import logging
from datetime import datetime
from pathlib import Path

# Logging setup
LOG_DIR = "./logs/"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
TEMP_LOG_FILE = LOG_DIR + "temp.log"
ERROR_LOG_FILE = LOG_DIR + "error.log"

# Configure loggers
temp_logger = logging.getLogger("temperature_logger")
error_logger = logging.getLogger("error_logger")

temp_handler = logging.FileHandler(TEMP_LOG_FILE)
temp_handler.setLevel(logging.INFO)
temp_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))  # Include timestamp in temp log

temp_logger.addHandler(temp_handler)
temp_logger.setLevel(logging.INFO)

error_handler = logging.FileHandler(ERROR_LOG_FILE)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))

error_logger.addHandler(error_handler)

# Connection setup
DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
TIMEOUT_DURATION = 2  # Timeout in seconds

# Thermistor setup
THERMISTORS = [
    {"name": "Front_Panel", "B": 3775.6, "R0": 29939, "T0": 273.15 + 25, "channel": "1"}, 
    # {"name": "Multiplexer_CH1", "B": 3950, "R0": 10000, "T0": 298.15, "channel": "101"},  # 7710 CH1 (Commented out, multiplexer not installed)
]

# Measurement settings
MEASUREMENT_INTERVAL = 2  # Seconds between measurements
TOTAL_MEASUREMENTS = 5  # Number of iterations before stopping (set to None for infinite loop)

# Resistance-to-temperature conversion function
def resistance_to_temperature(resistance, B, R0, T0):
    temp_K = 1 / ((1 / B) * (math.log(resistance / R0)) + (1 / T0))
    return temp_K - 273.15  # Convert to Celsius

# Connect to DAQ6510
try:
    print(f"Connecting to {DAQ6510_IP}...")
    daq = vxi11.Instrument(DAQ6510_IP)
    daq.timeout = TIMEOUT_DURATION  # Set timeout
    
    # Connection test
    idn = daq.ask("*IDN?")
    if not idn:
        raise ConnectionError("No response from DAQ6510. Check IP or network.")
    print(f"Connected to: {idn.strip()} ✅")
except Exception as e:
    error_logger.error(f"Connection failed: {e}")
    raise ConnectionError(f"Connection failed: {e}")

print("Starting thermistor measurements...")
iteration = 0

try:
    while True:
        try:
            # Apply measurement settings at the start of each cycle
            daq.write(":SYSTem:REMote")  # Set instrument to remote mode
            daq.write(":ROUTe:TERMinals FRONt")  # Use front panel globally to avoid redundant commands
            daq.write(":SENSe:FUNCtion 'RESistance'")
            daq.write(":SENSe:RESistance:RANGe 100000")  # 100 kΩ range for 33kΩ thermistor
            daq.write(":SENSe:RESistance:NPLCycles 5")  # Higher accuracy
            daq.write(":SENSe:RESistance:OCOMp ON")  # Offset compensation
            daq.write(":SENSe:RESistance:AZERo ON")  # Auto-zero
            
            for thermistor in THERMISTORS:
                # Select measurement channel only
                daq.write(f":ROUTe:SCAN (@{thermistor['channel']})")
                
                # Initiate and fetch resistance measurement
                daq.write(":INITiate")
                daq.write("*WAI")  # Wait for measurement completion
                resistance = float(daq.ask(":FETCH?"))

                # Convert to temperature
                temperature = resistance_to_temperature(resistance, thermistor["B"], thermistor["R0"], thermistor["T0"])
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                meas_str = f"{timestamp} {thermistor['name']} - Resistance: {resistance:.2f} Ω, Temperature: {temperature:.2f} °C"
                print(f"[{timestamp}] {thermistor['name']} - Resistance: {resistance:.2f} Ω, Temperature: {temperature:.2f} °C")
                temp_logger.info(meas_str)
            
            daq.write(":SYSTem:LOCal")  # Return instrument to local mode

        except Exception as ex:
            err_str = f"⚠️ Error reading thermistor data; see error.log"
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {err_str}")
            error_logger.error(f"{ex}")

        time.sleep(MEASUREMENT_INTERVAL)  # Wait before next measurement cycle

except KeyboardInterrupt:
    print("Measurement stopped manually.")
finally:
    daq.write(":SYSTem:LOCal")  # Return instrument to local mode
    print("Measurement complete.")
