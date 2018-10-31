import re
import serial
import ast
import statistics

class GenericSerialDevice(object):
	def __init__(self, cache, portName, baudRate):
		self.open = False
		self.portName = portName
		self.baudRate = baudRate
		self.buffer = b''
		self.cache = cache
		print("[Serial Device] Opened serial connection on port "+portName+", with baud rate "+str(baudRate)+".")
		try:
			self.port = serial.Serial(portName,baudRate)
			self.open = True
		except:
			print("[Serial Device] Failed to open device!")
			self.open = False
	def isOpen(self):
		return self.open and self.port.is_open
	def close(self):
		print("[Serial Device] Closed serial connection on port "+self.portName+".")
		if self.open:
			self.port.close()
			self.open = False
	def update(self):
		# Gets new serial data if it is incoming
		pass

# For now uses protocol of key:value, will be replaced by Gut's telemetry protocol
class TelemetryDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(TelemetryDevice, self).__init__(cache, portName, 115200)
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
					else:
						self.buffer += c
			except Exception as e:
				print(e)
				self.close()

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
				print(e)
				self.close()

class UsbGpsDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(UsbGpsDevice, self).__init__(cache, portName, 19200)

class VictronDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(VictronDevice, self).__init__(cache, portName, 19200)
		self.victronBuffer = ""
		self.victronCommands = ["PID","V","VS","I","P","SOC","TTG","Alarm","Relay"]
		self.statusRe = re.compile("BATTERY,PID \S*,V (-?\d*),VS (-?\d*),I (-?\d*),P (-?\d*),SOC (-?\d*),TTG (-?\d*),.*")
		self.statusVoltage = 0
		self.statusCurrent = 0
		self.statusStateOfCharge = 0
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting
				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == b'\n':
						# Send victron buffer if we reached a line containing checksum
						# Otherwise add this line to the buffer
						rawLine = str(self.buffer).lstrip().rstrip().replace('\t',' ')
						rawLine = re.sub('/\p{C}+/u','',rawLine)
						self.buffer=b''
						if rawLine.lower().startswith("checksum"):
							if len(self.victronBuffer) > 0:
								# Decode and save as telemetry data
								m = self.statusRe.match("BATTERY"+self.victronBuffer)
								if (m):
									self.statusVoltage = int(m.group(1))/1000.0
									self.statusCurrent = int(m.group(3))/1000.0
									self.statusStateOfCharge = int(m.group(5))/1000.0
									self.saveData()
								self.victronBuffer = ""
						else:
							for e in self.victronCommands:
								if rawLine.startswith(e):
									self.victronBuffer += ("," + rawLine)
									break
					else:
						self.buffer += c
			except Exception as e:
				print(e)
				self.close()
	def saveData(self):
		# Commit the cached data to the database
		#print("Battery Data: {0}V, {1}A, SOC:{2}".format(self.statusVoltage,self.statusCurrent,self.statusStateOfCharge))
		self.cache.set("bmvShuntVoltage",self.statusVoltage)
		self.cache.set("bmvShuntCurrent",self.statusCurrent)
		self.cache.set("bmvStateOfCharge",self.statusStateOfCharge)
