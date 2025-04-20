from .GenericSerialDevice import GenericSerialDevice
from server import statistics
from server import config
import traceback
import struct
import time

class RadioDevice(GenericSerialDevice):
    def __init__(self, cache, portName):
        super(RadioDevice, self).__init__(cache, portName, 57600)
        self.lastUpdate = time.time()
        self.writeCache = {}
    def update(self):
        if self.open:
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
                traceback.print_exc()
                self.close()

        # Sends packets at a fixed rate
        # Each time it checks the write cache and if there are new packets, writes them
        if time.time() - self.lastUpdate < config.radioPacketRate:
            return
        else:
            self.lastUpdate = time.time()
        #print("Writing cache packets")
        for i, key in enumerate(self.writeCache.keys()):
            self.write(key, self.writeCache.get(key))
        self.writeCache = {}
    def addToWriteCache(self,name,value):
        self.writeCache[name] = value
    def read(self,packet):
        # Reads a packet
        if len(packet) != 6:
            return
        packetHeader = packet[0]
        dataId = packet[1]
        data = packet[2:6]
        dataValue = struct.unpack(">f", bytearray(data))[0]
        dataKey = self.cache.indexToKey(dataId)
        #print("From Master: {0} = {1}".format(dataKey,dataValue))
        if dataValue is not None:
            self.cache.setNoRadio(dataKey,dataValue)
    def write(self,dataName, dataValue):
        try:
            #print("To Master: {0} = {1}".format(dataName,dataValue))
            # Writes a data point update to the radio stream if radio is active
            # Each packet consists of six bytes:
            # byte 1: packet header (0xF0)
            # byte 2: data point ID
            # byte 3 - 6: data
            packet = bytearray(6)
            packet[0] = 0xF0
            packet[1] = self.cache.keyToIndex(dataName)
            if dataValue is not None:
                packet[2:6] = bytearray(struct.pack(">f", dataValue))
            else:
                # Use NaN to represent None for the data point.
                packet[2:6] = bytearray(struct.pack(">f", float('NaN')))
            self.port.write(packet)
        except Exception as e:
            print("Failed to write radio packet from Slave.")
            traceback.print_exc()
            pass
