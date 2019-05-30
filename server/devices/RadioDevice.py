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
					packetHeader = packet[0]
					dataId = packet[1]
					data = packet[2:6]
					dataValue = struct.unpack(">f", data)

					key = self.cache.indexToKey(dataId)
					if not key is None:
						self.cache.set(dataName,dataValue)
						statistics.stats["numRadioPackets"] += 1
			except Exception as e:
				pass
				#traceback.print_exc()
				#self.close()
