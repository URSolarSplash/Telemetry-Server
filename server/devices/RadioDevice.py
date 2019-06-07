from .GenericSerialDevice import GenericSerialDevice
from server import statistics
import traceback

class RadioDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(RadioDevice, self).__init__(cache, portName, 57600)
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
				pass
				#traceback.print_exc()
				#self.close()
	def read(self,packet):
		# Reads a packet
		if len(packet) != 6:
			return
		packetHeader = packet[0]
		dataId = packet[1]
		data = packet[2:6]
		dataValue = struct.unpack(">f", data)
	def write(self,dataName, dataValue):
		# Writes a data point update to the radio stream if radio is active
		# Each packet consists of six bytes:
		# byte 1: packet header (0xF0)
		# byte 2: data point ID
		# byte 3 - 6: data
		packet = bytearray(6)
		packet[0] = 0xF0
		packet[1] = self.dataCache.keyToIndex(dataName)
		packet[2:6] = bytearray(struct.pack(">f", dataValue))
		self.port.write(bytes(dataString,"utf-8"))
