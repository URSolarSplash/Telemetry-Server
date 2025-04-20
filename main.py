# Main telemetry server file
from server.data import *
from server.controls import *
from server.dashboard import DashboardManager
from server.serialManager import SerialManager
from server.radio import RadioManager
from server.api import HTTPServerManager
from server import config
from time import sleep
from threading import Event
import signal
import os
import time
from os.path import expanduser

print("[Main] Initializing Telemetry Server...")

# Create base database folder if it doesnt exists
config.dbFolder = expanduser(config.dbFolder)
if not os.path.exists(config.dbFolder):
    print("[Database] Creating base database folder...")
    os.makedirs(config.dbFolder)

# Create a data cache and Database
# Data cache handles storage of values and their expirations
# Database connects the data cache to a sqlite file
data = DataCache(config.dataKeys)
database = Database(data,config.dbFolder + config.dbFile,config.dbEraseOnStart)

# Set timestamp to start at 0 at program start
# If you don't call this, the timestamp is since epoch
database.resetTimestamp()

# Create manager classes for several functions:
# - Serial manager is responsible for managing serial devices
# - Radio manager is responsible for radio-based data transmission to shore
# - HTTPServerManager creates a lightweight interface to get the latest data via GET request.
serial = SerialManager(data)
radio = RadioManager(data)
server = HTTPServerManager(data)
dashboard = DashboardManager()

# Set up control algorithms manager
controlAlgorithms = ControlAlgorithms(data)

print("[Main] Telemetry Server Initialized.")

try:
    while True:
        # Update the device list and connect to new devices
        # Also disconnect from devices which have timed out
        serial.updateDevices()

        # Polls active devices that want new data
        # Sends a packet which requests more data
        serial.pollDevices()

        # Update radio communication
        # Sends radio packets at a fixed rate
        radio.update()

        # If the data cache has valid data, save into the database
        if data.hasValidData():
            database.saveData()

        # Update control algorithms
        if (not config.isSlave):
            controlAlgorithms.update()

except (KeyboardInterrupt, SystemExit):
    print("\n[Main] Shutting down...")

serial.shutdown()
radio.shutdown()
database.shutdown()
dashboard.shutdown()
