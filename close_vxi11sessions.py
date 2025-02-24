import vxi11

DAQ6510_IP = "192.168.1.25"

# Attempt to close an existing session before creating a new one
try:
    daq = vxi11.Instrument(DAQ6510_IP)
    daq.close()  # Close any lingering connections
    print("Closed existing VXI-11 session.")
except Exception as e:
    print(f"Could not close previous session: {e}")

# Now try opening a fresh connection
try:
    daq = vxi11.Instrument(DAQ6510_IP)
    daq.timeout = 2
    print(daq.ask("*IDN?"))  # Query identification
except Exception as e:
    print(f"Error: {e}")
