import serial
from server import statistics
import struct
import time
from server import config
import binascii

# Handles radio communication of telemetry data
# This handles output from the Pi to the shore computer
# The receiving of this data is handled via the standard serial system;
# the usb radio telemetry device shows up as a serial device.
class RadioManager():
    def __init__(self, dataCache):
        self.mode = 0
        self.dataCache = dataCache
        self.lastUpdate = time.time()
        try:
            self.serialPortWrite = serial.Serial(
            	port='/dev/serial0',
            	baudrate=57600,
            	parity=serial.PARITY_NONE,
            	stopbits=serial.STOPBITS_ONE,
            	bytesize=serial.EIGHTBITS
            )
            self.mode = 1
            statistics.stats["hasRadio"] =  True
            print("[Radio] Detected serial telemetry device.")
        except (serial.SerialException):
            self.mode = 0
            statistics.stats["hasRadio"] =  False
            print("[Radio] No detected serial telemetry device.")
    def update(self):
        # Update the radio subsystem
        # Sends packets at a fixed rate
        if time.time() - self.lastUpdate < config.radioPacketRate:
            return
        else:
            self.lastUpdate = time.time()
        for i, key in enumerate(self.dataCache.getKeys()):
            self.write(key, self.dataCache.getNumerical(key,0))

    def write(self,dataName, dataValue):
        # Writes a data point update to the radio stream if radio is active
        if self.mode == 1:
            # Each packet consists of six bytes:
            # byte 1: packet header (0xF0)
            # byte 2: data point ID
            # byte 3 - 6: data
            packet = bytearray(6)
            packet[0] = 0xF0
            packet[1] = 0x55 #self.dataCache.keyToIndex(dataName)
            packet[2:6] = bytearray(struct.pack(">f", 1))
            #self.serialPortWrite.write(bytes(dataString,"utf-8"))
    def shutdown(self):
        try:
            self.serialPortWrite.close()
        except:
            pass
        print("[Radio] shutdown complete.")
