from .GenericSerialDevice import GenericSerialDevice
from server import statistics
import traceback

class RadioDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(RadioDevice, self).__init__(cache, portName, 57600)
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting
				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == ord(b'\n'):
						bytesToString = "".join(map(chr, self.buffer));
						rawLine = bytesToString.lstrip().rstrip()

						# DECODE:
						# Todo replace protocol
						# Extract variable name and value
						dataArray = rawLine.split(':',1)
						if (len(dataArray) == 2):
							dataName = dataArray[0]
							dataValues = float(dataArray[1])
							self.cache.set(dataName,dataValues)
							statistics.stats["numRadioPackets"] += 1
							#print("[Radio] Received remote telemetry data {0}={1}".format(dataName,dataValues))

						# Clear buffer
						self.buffer = []
					else:
						self.buffer.append(c)
			except Exception as e:
				traceback.print_exc()
				self.close()
