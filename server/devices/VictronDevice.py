from .GenericSerialDevice import GenericSerialDevice
import time
from textwrap import wrap

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
		self.pollRate = 1
		self.lastPoll = time.time()
	def update(self):
		if self.open:
			#try:
				# Handle sending of poll serial commands
				if time.time() - self.lastPoll > self.pollRate:
					self.lastPoll = time.time()
					self.port.write(self.encodeGetCommand(0xED8D))

				# Read serial data in.
				waitingBytes = self.port.in_waiting
				if waitingBytes == 0:
					return
				for c in self.port.read(waitingBytes):
					if c == ord(b'\n'):
						bytesToString = "".join(map(chr, self.buffer));
						rawLine = bytesToString.lstrip().rstrip()
						self.decodeGetCommand(rawLine)
						self.buffer = []
					else:
						self.buffer.append(c)
			#except Exception as e:
			#	print(e)
			#	self.close()
	def saveData(self):
		# Commit the cached data to the database
		# print("Battery Data: {0}V, {1}A, SOC:{2}".format(self.statusVoltage,self.statusCurrent,self.statusStateOfCharge))
		self.cache.set("batteryVoltage",self.statusVoltage)
		#self.cache.set("bmvAuxVoltage",self.statusAuxVoltage)
		self.cache.set("batteryCurrent",self.statusCurrent)
		self.cache.set("batteryPower",self.statusPower)
		self.cache.set("batteryTimeRemaining",self.statusTimeRemaining)
		self.cache.set("batteryConsumedAh",self.statusConsumedAh)
		self.cache.set("batteryStateOfCharge",self.statusStateOfCharge)
	def encodeGetCommand(self,id_hex):
		# Encodes a VE.Direct hex command to read data
		commandArray = []
		idBytes = id_hex.to_bytes(2, 'little')
		commandId = 7
		commandArray.append(idBytes[0])
		commandArray.append(idBytes[1])
		commandArray.append(0)
		#print(commandArray)
		commandString = ":" + str(commandId)
		checksum = 0x55 - commandId
		for byte in commandArray:
			checksum -= byte
			commandString += "{0:02X}".format(byte)
		# Wrap checksum
		checksum = checksum % 0xFF

		#print(checksum)
		#print((checksum +sum(idBytes)) % 0xFF)
		commandString += "{0:02X}".format(checksum)
		commandString += "\n"
		print("Sending request for data ID: 0x{0:X}".format(id_hex))
		print(commandString)
		return bytes(commandString,"utf-8")
	def decodeGetCommand(self,rawLine):
		print(rawLine)
		if len(rawLine) == 0 or rawLine[0] != ":":
			return
		if rawLine[1] != "7":
			return
		dataBytes = wrap(rawLine[2:], 2)
		print(dataBytes)
		dataId = int("0x"+dataBytes[1]+dataBytes[0],16)
		print("Received response for data ID: 0x{0:X}".format(dataId))
		# 8 bit: dataValue = int("0x"+dataBytes[3],16)
		# 16 bit: dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
		# 32 bit: dataValue = int("0x"+dataBytes[6]+dataBytes[5]+dataBytes[4]+dataBytes[3],16)
		if dataId == 0xED8D:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
			self.statusVoltage=dataValue*100
		elif dataId == 0xED8C:
			dataValue = int("0x"+dataBytes[6]+dataBytes[5]+dataBytes[4]+dataBytes[3],16)
			self.statusCurrent = dataValue * 1000
		elif dataId == 0xED8E:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
			self.statusPower=dataValue
		elif dataId == 0xEEFF:
			dataValue = int("0x"+dataBytes[6]+dataBytes[5]+dataBytes[4]+dataBytes[3],16)
			self.statusConsumedAh=dataValue
		elif dataId == 0x0FFF:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
			self.statusStateOfCharge=dataValue
		elif dataId == 0x0FFE:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
			self.statusTimeRemaining=dataValue
