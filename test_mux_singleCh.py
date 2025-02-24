import vxi11

# Connection setup
DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
TIMEOUT_DURATION = 2  # Timeout in seconds
CHANNELS = ["101", "102", "103", "104", "105"]  # Multiplexer channels

# Connect to DAQ6510
print(f"Connecting to DAQ6510 at {DAQ6510_IP}...")
daq = vxi11.Instrument(DAQ6510_IP)
daq.timeout = TIMEOUT_DURATION

# Test connection
idn = daq.ask("*IDN?")
if not idn:
    raise ConnectionError("No response from DAQ6510. Check IP or network.")
print(f"Connected to: {idn.strip()} ✅")

# Reset and configure instrument
daq.write("*RST")
daq.write("SENS:FUNC 'RES'")  # Set function to resistance
daq.write("SENS:RES:RANG 100000")  # Set resistance range to 100kΩ
daq.write("SENS:RES:NPLC 1")  # Set integration time to 1 power line cycle

# Loop through channels
for ch in CHANNELS:
    print(f"Measuring resistance on CH{ch}...")
    daq.write(f"ROUT:SCAN (@{ch})")  # Select channel
    daq.write("INIT")  # Start measurement
    daq.write("*WAI")  # Wait for completion
    resistance = daq.ask("FETC?")  # Fetch result

    print(f"CH{ch}: Resistance = {resistance} Ω")

print("Measurement complete.")
