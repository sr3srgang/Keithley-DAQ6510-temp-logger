# Keithly DAQ6510 temp logger
- Created by Joonseok Hur

## Functions
1. The App periodically reads the resistances of thermistors connected to a Keithley DAQ6510 or the multiplexers inserted to the DAQ, 
2. converts the measured resistances to the corresponding temperature from the input B, R0, and T0 parameters that can be set by the user, and
3. uploads the measured values to a InfluxDB. 

Intended to be run in Ubuntu (tested in Ubuntu 20.04.6 LTS)


## Initial setup
TBD (you don't need to know hopefully...)


## Starting app
Click "Keitley Temp Logger" icon in the sidebar or *Show Applications* dashboard. If it doesn't work, try run `./Startup_ubuntu` in a terminal.

## Autostart setting at OS startup
Using *Startup Applications Properties* GUI application.
Refer to https://help.ubuntu.com/stable/ubuntu-help/startup-applications.html.en.


1. Open gnome-session-properties GUI by one of the following ways:
    - Open *Activity* dashboard and search for *Startup Applications Properties*
    - Press Alt+F2 and run `gnome-session-properties`
2. Click *Add* button and populate the blanks as follows:
    - Name: Keithley Temp Logger
    - Command: ##type the absolute path to the (renamed) copy of `Startup_ubuntu` script file## (e.g.,/home/srgang/Startup_ubuntu)
    - Comment: 
3. Click *Save* button.

Tested for Ubuntu 20.04 LTS.

## Use
In `main.py`, edit the block between `>>>>> User parameters >>>>>` and `# <<<<< User parameters <<<<<` comments to setup thermistor connections, parameters, and measurement names.

As soon as starting the app up, it will start reading temps, print in stdout, and uploading to Grafana's DB periodically.

## Developer's notes
TBD