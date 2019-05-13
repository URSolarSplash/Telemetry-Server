from .GenericSerialDevice import GenericSerialDevice
import pynmea2

# Reads a USB-based GPS device. Deprecated, replaced with Node-based GPS board.
class UsbGpsDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(UsbGpsDevice, self).__init__(cache, portName, 4800)
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting

				if not waitingBytes == 0:
					for c in self.port.read(waitingBytes):
						self.buffer.append(c)

				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == ord(b'\n'):
						bytesToString = "".join(map(chr, self.buffer));
						rawLine = bytesToString.lstrip().rstrip()
						self.buffer=[] # Reset the buffer
						try:
							msg = pynmea2.parse(rawLine)
							print(msg)
							if isinstance(msg, pynmea2.types.talker.GGA):
								if msg.gps_qual > 0:
									self.cache.set("usbGpsLatitude",msg.lat)
									self.cache.set("usbGpsLongitude",msg.lon)
									self.cache.set("usbGpsNumSatellites",msg.num_sats)
								else:
									self.cache.set("usbGpsNumSatellites",0)
							if isinstance(msg, pynmea2.types.talker.VTG):
								self.cache.set("usbGpsSpeed",msg.spd_over_grnd_kts)
						except:
							pass
					else:
						self.buffer.append(c)
			except Exception as e:
				self.close()
