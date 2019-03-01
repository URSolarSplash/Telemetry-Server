from .GenericSerialDevice import GenericSerialDevice

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
					if c == b'\n':
						rawLine = str(self.buffer).lstrip().rstrip().replace('\t',' ') # Replace tabs with spaces and strip whitespace
						rawLine = re.sub('/\p{C}+/u','',rawLine) # Replace invisible characters
						self.buffer=b'' # Reset the buffer
						# Extract variable name and value
						dataArray = rawLine.split(':',1)
						dataName = dataArray[0]
						dataValues = float(dataArray[1])
						self.cache.set(dataName,dataValues)
						statistics.stats["numRadioPackets"] += 1
						#print("[Radio] Received remote telemetry data {0}={1}".format(dataName,dataValues))
					else:
						self.buffer += c
			except Exception as e:
				traceback.print_exc()
				self.close()
