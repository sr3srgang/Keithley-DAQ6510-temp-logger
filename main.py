# 2025/02/19: created by Joonseok Hur

import vxi11
import time
import math
import traceback
import sys
from datetime import datetime
from pathlib import Path
# InfluxDB client package
# pip (or conda/mamba) install influxdb-client
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# >>>>> User parameters >>>>>
# Keithley DAQ6510 settings
IP = "192.168.1.25"
VXI11_TIMEOUT = 2  # sec

# Measurement settings
MEASUREMENT_INTERVAL = 5  # Seconds between measurements
TOTAL_MEASUREMENTS = None  # Number of iterations before stopping (set to None for infinite loop)

# Thermistor configuration
ASSIGNMENTS = [
    {
        "channel": "101",
        "name": "Laser-side HVAC air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
    {
        "channel": "102",
        "name": "Exp-side top layer air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
    {
        "channel": "103",
        "name": "Exp-side middle layer air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
    {
        "channel": "104",
        "name": "Exp-side bottom layer air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
    {
        "channel": "105",
        "name": "Cavity homodyne section air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
    {
        "channel": "106",
        "name": "Exp-side HVAC air",
        "thermistor_connection": "7710 multiplexer",
        "thermistor_model": "44008RC",
        "thermistor_params": {"B": 3775.6, "R0": 29939, "T0": 273.15 + 25},
    },
]
# <<<<< User parameters <<<<<

# yemonitor database credentials
url = "http://yemonitor.colorado.edu:8086"
token = "yelabtoken"
org = "yelab"
bucket = "sr3"  # If bucket not exists, create it from the database UI.

# Device channels for measurement
Nch = len(ASSIGNMENTS)
BUFFERSIZE = Nch
BUFFERSIZE = max(BUFFERSIZE, 10)  # Ensure buffer size is valid
CHANNELS = [ASSIGNMENT["channel"] for ASSIGNMENT in ASSIGNMENTS]
CHSSTR = ",".join(CHANNELS)

# Function to convert resistance to temperature
def resistance_to_temperature(resistance, B, R0, T0):
    temp_K = 1 / ((1 / B) * (math.log(resistance / R0)) + (1 / T0))
    return temp_K - 273.15  # Convert to Celsius

DAQ_SN = None  # serial number of DAQ

def parse_idn_response(idn_response):
    """Parses the *IDN? response string into manufacturer, model, serial number, and firmware version."""
    try:
        manufacturer, model, serial_number, firmware_version = idn_response.strip().split(",")
        return {
            "Manufacturer": manufacturer,
            "Model": model,
            "Serial Number": serial_number,
            "Firmware Version": firmware_version
        }
    except ValueError:
        err_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Error: Unexpected *IDN? response format."
        print(err_msg, file=sys.stdout)
        print(err_msg, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        return None

# Start measurement loop
iteration = 0

print("Starting thermistor measurements...")

while TOTAL_MEASUREMENTS is None or iteration < TOTAL_MEASUREMENTS:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Iteration {iteration}:")
    
    try:
        # Establish a new VXI-11 session
        daq = vxi11.Instrument(IP)
        daq.timeout = VXI11_TIMEOUT

        # Test connection
        if iteration == 0:
            print("Printing connection status in the first loop run:")
            print(f"\tConnecting to DAQ6510 at {IP}...")
        idn = daq.ask("*IDN?")
        if not idn:
            raise ConnectionError("No response from DAQ6510. Check IP or network.")
        if iteration == 0:
            print(f"\tConnected! *IDN? = {idn}")
            idn_parsed = parse_idn_response(idn)
            DAQ_SN = idn_parsed["Serial Number"] if idn_parsed else "UNKNOWN"
        
        # Configure the measurement
        daq.write("*RST")  # Reset and configure instrument
        daq.write("TRAC:CLE 'defbuffer1'")
        daq.write(f"TRAC:POIN {BUFFERSIZE}, 'defbuffer1'")  # Set buffer size
        daq.write("ROUT:SCAN:BUFF 'defbuffer1'")  # Assign scan buffer
        daq.write(f"FUNC 'RES', (@{CHSSTR})")  # Set function to resistance
        daq.write(f"ROUT:SCAN (@{CHSSTR})")  # Set channels for scanning
        daq.write("ROUT:SCAN:COUN:SCAN 1")  # Set scan count

        # Start the measurement
        daq.write("INIT")
        daq.write("*WAI")

        # Check number of recorded points
        Nact = daq.ask("TRAC:ACT?")  # Query active points
        Nact = int(float(Nact.strip()))  # Convert to int

        # Fetch resistance values
        measstr = daq.ask(f"TRAC:DATA? 1, {Nact}")
        resistances = [float(s) for s in measstr.split(",")]

        # Process and print temperature readings
        temps_C = [None] * Nch
        for ich, channel in enumerate(CHANNELS):
            resistance = resistances[ich]
            name = ASSIGNMENTS[ich]["name"]
            thermistor_params = ASSIGNMENTS[ich]["thermistor_params"]
            temp_C = resistance_to_temperature(resistance, **thermistor_params)
            temps_C[ich] = temp_C

            meas_str = f"{channel} - R={resistance:.2f} Ω, T={temp_C:.4f} °C ({name})"
            print(f"\t{meas_str}")

        # Upload results to yemonitor DB
        records = [None] * Nch
        for ich, assignment in enumerate(ASSIGNMENTS):
            temp_C = temps_C[ich]
            record = {
                "measurement": "Keithley DAQ6510",
                "tags": {
                    "DAQ SN": DAQ_SN,
                    "channel": assignment["channel"],
                    "name": assignment["name"],
                    "thermistor connection": assignment["thermistor_connection"],
                    "thermistor model": assignment["thermistor_model"],
                },
                "fields": {"Temp[degC]": temp_C},
            }
            records[ich] = record
            
        with InfluxDBClient(url=url, token=token, org=org) as client:
            with client.write_api(write_options=SYNCHRONOUS) as writer:
                writer.write(bucket=bucket, record=records)

    except Exception as ex:
        # Construct error message with timestamp.
        err_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Error reading thermistor data."
        print(err_msg, file=sys.stdout)
        # Also print the error message and traceback to stderr for detailed debugging.
        print(err_msg, file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)

    finally:
        try:
            daq.close()
        except Exception as e:
            err_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Error closing session: {e}"
            print(err_msg, file=sys.stdout)
            print(err_msg, file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)

    iteration += 1
    time.sleep(MEASUREMENT_INTERVAL)

print("Measurement complete.")
