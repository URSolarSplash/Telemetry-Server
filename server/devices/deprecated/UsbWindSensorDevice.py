from .GenericSerialDevice import GenericSerialDevice

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
