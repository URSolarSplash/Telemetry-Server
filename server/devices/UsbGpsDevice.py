from GenericSerialDevice import *

class UsbGpsDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(UsbGpsDevice, self).__init__(cache, portName, 4800)
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

						msg = pynmea2.parse(rawLine)
						if isinstance(msg, pynmea2.types.talker.GGA):
							if msg.gps_qual > 0:
								self.cache.set("gpsLatitude",msg.lat)
								self.cache.set("gpsLongitude",msg.lon)
								self.cache.set("gpsNumSatellites",msg.num_sats)
							else:
								self.cache.set("gpsNumSatellites",0)
					else:
						self.buffer += c
			except Exception as e:
				traceback.print_exc()
				self.close()
