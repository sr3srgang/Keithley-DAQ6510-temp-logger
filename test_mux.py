import vxi11
import time
import traceback


# Connection setup
DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
TIMEOUT_DURATION = 2  # Timeout in seconds
# CHANNELS = ["101", "102", "103", "104", "105"]  # Multiplexer channels
CHANNELS = ["101", "102", "103", "104"]  # Multiplexer channels

try:
    # Connect to DAQ6510
    print(f"Connecting to DAQ6510 at {DAQ6510_IP}...")
    daq = vxi11.Instrument(DAQ6510_IP)
    print("A vxi11 session established.")
    daq.timeout = TIMEOUT_DURATION

    # Test connection
    idn = daq.ask("*IDN?")
    if not idn:
        raise ConnectionError("No response from DAQ6510. Check IP or network.")
    print(f"Connected! *IDN? = {idn}")
    
    # configure the measurement
    BUFFERSIZE = len(CHANNELS)
    CHSSTR = ",".join(CHANNELS)
    daq.write("*RST") # Reset and configure instrument
    daq.write(f"TRAC:POIN {BUFFERSIZE}, 'defbuffer1'")
    daq.write("ROUT:SCAN:BUFF 'defbuffer1'")
    daq.write(f"FUNC 'RES', (@{CHSSTR})")
    daq.write(f"ROUT:SCAN (@{CHSSTR})")
    daq.write("ROUT:SCAN:COUN:SCAN 1")
    
    # start the measurement
    daq.write("INIT")
    daq.write("*WAI")
    
    # query the measurement result
    # im_last = daq.ask("TRAC:ACT?")
    # measstr = daq.ask("TRAC:DATA?")
    measstr = daq.ask(f"TRAC:DATA? 1, {BUFFERSIZE}")
    # print(measstr)
    resistances = [float(s) for s in measstr.split(",")]
    
    print(resistances)

except:
    print(traceback.format_exc())
finally:
    try:
        daq.close()
        print("The vxi11 session closed.")
    except:
        print(traceback.format_exc())

# Set function to resistance
# daq.write("SENS:RES:RANG 100000")  # Set resistance range to 100kΩ
# daq.write("SENS:RES:NPLC 1")  # Set integration time to 1 power line cycle


# Loop through channels
# for ch in CHANNELS:
#     print(f"Measuring resistance on CH{ch}...")
#     daq.write(f"ROUT:SCAN (@{ch})")  # Select channel
#     daq.write("INIT")  # Start measurement
#     daq.write("*WAI")  # Wait for completion
#     resistance = daq.ask("FETC?")  # Fetch result

#     print(f"CH{ch}: Resistance = {resistance} Ω")

daq.close()

print("Measurement complete.")
