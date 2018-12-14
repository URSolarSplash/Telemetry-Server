from GenericSerialDevice import *
import time

class TelemetryTextDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(TelemetryTextDevice, self).__init__(cache, portName, 115200)
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting
				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == b'\n':
						rawLine = str(self.buffer).lstrip().rstrip().replace('\t',' ') # Replace tabs with spaces and strip whitespace
						rawLine = re.sub('/\p{C}+/u','',rawLine) # Replace invisible characters
						self.buffer=b'' # Reset the buffer
						# Extract variable name and value
						dataArray = rawLine.split(':',1)
						dataName = dataArray[0]
						dataValues = float(dataArray[1])
						self.cache.set(dataName,dataValues)
						delay = time.time() - self.lastTime
						#print("[Telemetry Device] time since last packet: {0}".format(delay*1000))
						self.lastTime = time.time()
					else:
						self.buffer += c
			except Exception as e:
				print(e)
				self.close()