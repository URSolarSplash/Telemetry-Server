import re
import serial
import ast
import statistics
import time
import pynmea2
import traceback

class GenericSerialDevice(object):
	def __init__(self, cache, portName, baudRate):
		self.open = False
		self.portName = portName
		self.baudRate = baudRate
		self.lastTime = time.time()
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
						delay = time.time() - self.lastTime
						#print("[Telemetry Device] time since last packet: {0}".format(delay*1000))
						self.lastTime = time.time()
					else:
						self.buffer += c
			except Exception as e:
				print(e)
				self.close()

#TelemetryNode implementing URSS telemetry protocol
class TelemetryNode(GenericSerialDevice):
	def __init__(self,cache,portName):
		super(TelemetryNode,self).__init__(cache,portName,115200)
	'''
	def update(self):
		if self.open:
			try:
	'''


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

class UsbWindSensorDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(UsbWindSensorDevice, self).__init__(cache, portName, 9600)
		self.var1=0
		self.var2=0
		self.var3=0
		self.var4=0
		self.var5=0
		self.var6=0
		self.var7=0
		self.var8=0
		self.i=0
		self.BITMASK_MINMAX=0b11
		self.BITMASK_SPEED_UNITS=0b11100
		self.MAX_FLAG=0
		self.MIN_FLAG=0
		self.windAverageList = [0,0,0,0,0,0,0,0,0,0]
		self.currentIndex = 0
		self.percentageHumidity = 0
		self.temperatureCelcius = 0
		self.windSpeed = 0
		self.windAverageSpeed = 0
		self.windWarningState = 0
	def update(self):
		if self.open:
			try:
				waitingBytes = self.port.in_waiting
				if waitingBytes < 2:
					return
				mostSignificant = ord(self.port.read())
				leastSignificant = ord(self.port.read())
				lastInt = (mostSignificant << 8) | (leastSignificant)
				if (self.i == 1):
					self.var1 = lastInt
				elif (self.i == 2):
					self.var2 = lastInt
				elif (self.i == 3):
					self.var3 = lastInt
				elif (self.i == 4):
					self.var4 = lastInt
				elif (self.i == 5):
					self.var5 = lastInt
				elif (self.i == 6):
					self.var6 = lastInt
				elif (self.i == 7):
					self.var7 = lastInt
				self.i = self.i + 1
				if (self.i >= 8):
					self.MINMAX_STATE = (self.var1 & self.BITMASK_MINMAX)
					self.MAX_FLAG = self.MINMAX_STATE & 0b01
					self.MIN_FLAG = self.MINMAX_STATE & 0b10
					self.percentageHumidity = self.var2/10.0
					self.temperatureCelcius = (self.var3 / 10.0) - 30
					self.windSpeed = self.var5/100.0
					self.windAverageList[self.currentIndex] = self.windSpeed
					self.currentIndex = (self.currentIndex + 1) % 10
					self.windAverageSpeed = sum(self.windAverageList) / len(self.windAverageList)
					self.windWarningState = 1 if (self.windAverageSpeed > 2) else 0
					self.i=0
					# Save data
					self.cache.set("windPercentHumidity",self.percentageHumidity)
					self.cache.set("windTemperature",self.temperatureCelcius)
					self.cache.set("windSpeed",self.windSpeed)
					self.cache.set("windAverageSpeed",self.windAverageSpeed)
					self.cache.set("windWarningState",self.windWarningState)
			except Exception as e:
				print(e)
				self.close()

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
