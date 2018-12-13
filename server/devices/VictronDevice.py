from GenericSerialDevice import *

# Decodes the Victron VE.Direct text-based protocol
# For more information on the protocol, view the Whitepaper in the URSS drive.
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
