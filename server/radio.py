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
# IN ORDER FOR RADIO TELEMETRY TO WORK CORRECTLY, BOTH DEVICES MUST HAVE SAME VERSION
class RadioManager():
    def __init__(self, dataCache):
        self.mode = 0
        self.dataCache = dataCache
        self.lastUpdate = time.time()
        self.buffer = []
        try:
            self.serialPort = serial.Serial(
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

        # Check for input packets
        # These are used for control signals from the shore
        try:
            while (self.port.in_waiting > 0):
                self.buffer.append(ord(self.port.read(1)))

            while (len(self.buffer) > 0 and self.buffer[0] != 0xF0):
                self.buffer.pop(0)

            if (len(self.buffer) >= 6):
                packet = self.buffer[0:6]
                self.buffer = self.buffer[6:]
                self.read(packet)
        except Exception as e:
            pass

        # Sends packets at a fixed rate
        if time.time() - self.lastUpdate < config.radioPacketRate:
            return
        else:
            self.lastUpdate = time.time()
        for i, key in enumerate(self.dataCache.getKeys()):
            self.write(key, self.dataCache.get(key))
    def write(self,dataName, dataValue):
        # Writes a data point update to the radio stream if radio is active
        if self.mode == 1:
            # Each packet consists of six bytes:
            # byte 1: packet header (0xF0)
            # byte 2: data point ID
            # byte 3 - 6: data
            packet = bytearray(6)
            packet[0] = 0xF0
            packet[1] = self.dataCache.keyToIndex(dataName)
            if not dataValue is None:
                packet[2:6] = bytearray(struct.pack(">f", dataValue))
            else:
                # Use NaN to represent None for the data point.
                packet[2:6] = bytearray(struct.pack(">f", float('NaN')))
            self.serialPort.write(packet)
    def read(self,packet):
        # Reads a packet
        if len(packet) != 6:
            return
        packetHeader = packet[0]
        dataId = packet[1]
        data = packet[2:6]
        dataValue = struct.unpack(">f", bytearray(data))[0]
        dataKey = self.cache.indexToKey(dataId)
        if dataValue != dataValue:
            dataValue = None
        print("From Slave: {0} = {1}".format(dataKey,dataValue))
        if not dataValue == None:
            self.cache.set(dataKey,dataValue)
    def shutdown(self):
        try:
            self.serialPort.close()
        except:
            pass
        print("[Radio] shutdown complete.")
