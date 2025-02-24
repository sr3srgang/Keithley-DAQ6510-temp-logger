import vxi11

# Connection setup
DAQ6510_IP = "192.168.1.25"  # Update with actual DAQ6510 IP
daq = vxi11.Instrument(DAQ6510_IP)

# Send SCPI commands
daq.write("*RST")
daq.write(":ROUT:TERM REAR")
daq.write(":TRAC:MAKE \"res_buf\", 100")  # Create a buffer
daq.write(":SENS:FUNC 'RES'")
daq.write(":SENS:RES:RANG 100000, (@101:105)")  # Set range
daq.write(":ROUT:SCAN (@101:105)")  # Select channels
daq.write(":TRAC:CLE")  # Clear previous readings
daq.write(":INIT")
daq.write("*WAI")

# Retrieve and print results
resistances = daq.ask(":TRAC:DATA? 1, 5, \"res_buf\"").split(",")
for i, res in enumerate(resistances):
    print(f"CH{101 + i}: {res} Ω")

daq.close()
