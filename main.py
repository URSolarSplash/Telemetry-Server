# Main telemetry server file
from server.data import *
from server.serialManager import SerialManager
from server.radio import RadioManager
from server import config
from time import sleep
from threading import Event
import signal
import os
from os.path import expanduser

# Create base database folder if it doesnt exists
config.dbFolder = expanduser(config.dbFolder)
if not os.path.exists(config.dbFolder):
    os.makedirs(config.dbFolder)

# Create a data cache and Database
# Data cache handles storage of values and their expirations
# Database connects the data cache to a sqlite file
data = DataCache(config.dataKeys)
database = Database(data,config.dbFolder + config.dbFile,True)

# Set timestamp to start at 0 at program start
# If you don't call this, the timestamp is since epoch
database.resetTimestamp()

# Create manager classes for several functions:
# - Serial manager is responsible for managing serial devices
# - Radio manager is responsible for radio-based data transmission to shore
serial = SerialManager(data)
radio = RadioManager()

# Set up the radio mirroring
# This uses the radio system to emit events when data is updated
# Used for remote data collection etc...
data.setRadioMirror(radio)

try:
    while True:
        # Update the device list and connect to new devices
        # Also disconnect from devices which have timed out
        serial.updateDevices()

        # Polls active devices that want new data
        # Sends a packet which requests more data
        serial.pollDevices()

        # If the data cache has valid data, save into the database
        if data.hasValidData():
            database.saveData()

except (KeyboardInterrupt, SystemExit):
    print("\nShutting down...")

serial.shutdown()
radio.shutdown()
database.shutdown()
