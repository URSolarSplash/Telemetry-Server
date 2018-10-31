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


# Decodes the Victron VE.Direct text-based protocol
# Consists of lines with keys and values:
# H1 - Depth of deepest discharge (mAh)
# H2 - Depth of last discharge (mAh)
# H3 - Depth of average discharge (mAh)
# H4 - Number of charge cycles
# H5 - Number of full discharges
# H6 - Cumulative amp hours drawn (mAh)
# H7 - Minimum main battery voltage (mV)
# H8 - Maximum main battery voltage (mV)
# H9 - Num seconds since last full charge
# H10 - Number of automatic synchronizations
# H11 - Number of low main voltage alarms
# H12 - Number of high main voltage alarms
# H15 - Number of low auxiliary voltage alarms
# H16 - Number of high auxiliary voltage alarms
# H17 - Amount of discharged energy (0.01 kWh)
# H18 - Amount of charged energy (0.01 kWh)
# CHECKSUM - Modulo sum of all bytes since last checksum, should equal 0
# PID - Id of the device
# V - Main battery voltage (mV)
# VS - Auxiliary voltage (mv)
# I - Battery shunt current (mA)
# P - Instantaneous Power (W)
# CE - Consumed Amp Hours (mAh)
# SOC - State of charge (percentage)
# TTG - Time-to-go (minutes)
# ALARM - Alarm active
# RELAY - Relay state
# AR - Alarm reason
# BMV - String label of the BMV (ignore)
# FW -  Firmware version
class VictronDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(VictronDevice, self).__init__(cache, portName, 19200)
		self.statusVoltage = 0
		self.statusAuxVoltage = 0
		self.statusCurrent = 0
		self.statusPower = 0
		self.statusStateOfCharge = 0
		self.statusTimeRemaining = 0
		self.statusConsumedAh = 0
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting
				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == b'\n':
						rawLine = str(self.buffer).lstrip().rstrip()
						dataArray = rawLine.split('\t',1)
						if len(dataArray) == 2:
							victronCommand = dataArray[0]
							victronData = dataArray[1]
							#print("[{0}]=[{1}]".format(victronCommand,victronData))
							if victronCommand == "V":
								self.statusVoltage = int(victronData)/1000.0
								self.saveData()
							elif victronCommand == "VS":
								self.statusAuxVoltage = int(victronData)/1000.0
								self.saveData()
							elif victronCommand == "I":
								self.statusCurrent = int(victronData)/1000.0
								self.saveData()
							elif victronCommand == "P":
								self.statusPower = float(victronData)
								self.saveData()
							elif victronCommand == "CE":
								self.statusConsumedAh = float(victronData)/1000.0
								self.saveData()
							elif victronCommand == "SOC":
								self.statusStateOfCharge = float(victronData)/1000.0
								self.saveData()
							elif victronCommand == "TTG":
								self.statusTimeRemaining = float(victronData)
								self.saveData()

						self.buffer=b''
						#self.statusVoltage = int(m.group(1))/1000.0
						#self.statusCurrent = int(m.group(3))/1000.0
						#self.statusStateOfCharge = int(m.group(5))/1000.0
						#self.saveData()
					else:
						self.buffer += c
			except Exception as e:
				print(e)
				self.close()
	def saveData(self):
		# Commit the cached data to the database
		#print("Battery Data: {0}V, {1}A, SOC:{2}".format(self.statusVoltage,self.statusCurrent,self.statusStateOfCharge))
		self.cache.set("bmvVoltage",self.statusVoltage)
		self.cache.set("bmvAuxVoltage",self.statusAuxVoltage)
		self.cache.set("bmvCurrent",self.statusCurrent)
		self.cache.set("bmvPower",self.statusPower)
		self.cache.set("bmvStateOfCharge",self.statusStateOfCharge)
		self.cache.set("bmvTimeRemaining",self.statusTimeRemaining)
		self.cache.set("bmvConsumedAh",self.statusConsumedAh)
