import traceback
import time
import serial.tools.list_ports
import sys
import atexit
import platform
import re
import config

class SerialDevice:
    def __init__(self, id, baud):
        self.portName = None
        self.portInstance = None
        self.baudRate = None
        self.buffer = None
        self.mode = None
        self.lastPolled = time()
    def needsPoll(self):
        return time() - self.lastPolled > config.pollRate

class SerialManager:
    def __init__(self, cache):
        self.cache = cache
        self.devices = []
        self.deviceBlacklist = config.portBlacklist

    def shutdown(self):
        for device in self.devices:
            print("[Serial Manager] disconnecting from device "+device.portName+"...")
            device.portInstance.close()
        print("[Serial Manager] shutdown complete.")

    def updateDevices(self):
        portList = list(serial.tools.list_ports.comports())
        # Scan through the entire list of serial ports looking for devices
        for port in portList:
            portAlreadyOpen = False
            portId = port[0]
            portDescription = port[1]
            for device in self.devices:
    			if (device.portName.port == port[0]):
    				#Port already exists
    				portAlreadyOpen = True
            if portAlreadyOpen:
            	continue

            # We have found a new device
            # Exit early if the device ID is blacklisted
            if port[0] in self.deviceBlacklist:
                continue

            print("[Serial Manager] detected new device id={0}, desc={1}".format(str(portId),str(portDescription)))

            # This device is one of the following:
            # - Victron BMV device
            # - USB GPS
            # - Telemetry Protocol device
            # We will use the USB-Serial description field to determine this.
            # If the description matches a known hardware device, we use the custom
            # protocol, otherwise we use the standard telemetry protocol.
            if portDescription.startswith("FT231X"):
                # USB Radio Telemetry
                print("USB Radio Telemetry")
            elif portDescription.startswith("u_blox 7") or portDescription.startswith("u-blox 7"):
                print("U-Blox GPS")
            elif portDescription.startswith("VE Direct"):
                print("VE Direct")
            else:
                print("Default Telemetry")


    def pollDevices(self):
        return
