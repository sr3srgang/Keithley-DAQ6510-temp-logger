import vxi11
import traceback

# Connection setup
DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
TIMEOUT_DURATION = 2  # Timeout in seconds


try:
    daq = vxi11.Instrument(DAQ6510_IP)
    print("vxi11 session established.")
    daq.timeout = TIMEOUT_DURATION
    
    idn = daq.ask("*IDN?")
    print(f"*IDN? \t\t\t= {idn}")
    slot1_idn = daq.ask("SYST:CARD1:IDN?")
    print(f"SYST:CARD1:IDN? \t= {slot1_idn}")
except:
    print(traceback.format_exc())
finally:
    try:
        daq.close()
        print("vxi11 session closed.")
    except:
        print(traceback.format_exc())
        
        


# import vxi11

# # Connection setup
# DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
# TIMEOUT_DURATION = 2  # Timeout in seconds
# CHANNELS = ["101", "102", "103", "104", "105"]  # Multiplexer channels

# # Connect to DAQ6510
# print(f"Connecting to DAQ6510 at {DAQ6510_IP}...")
# daq = vxi11.Instrument(DAQ6510_IP)
# daq.timeout = TIMEOUT_DURATION

# # Test connection
# idn = daq.ask("*IDN?")