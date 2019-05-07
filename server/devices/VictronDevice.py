from .GenericSerialDevice import GenericSerialDevice
import time
from textwrap import wrap
import struct
import math

def twos_complement(hexstr,bits):
	value = int(hexstr,16)
	if value & (1 << (bits-1)):
		value -= 1 << bits
	return value

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
		self.pollRate = 0.1
		self.lastPoll = time.time()
	def update(self):
		if self.open:
			try:
				# Handle sending of poll serial commands
				if time.time() - self.lastPoll > self.pollRate:
					self.lastPoll = time.time()
					self.port.write(self.encodeGetCommand(0xED8D))
					self.port.write(self.encodeGetCommand(0xED8F))
					self.port.write(self.encodeGetCommand(0xED8E))
					self.port.write(self.encodeGetCommand(0xEEFF))
					self.port.write(self.encodeGetCommand(0x0FFF))
					self.port.write(self.encodeGetCommand(0x0FFE))

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
			except Exception as e:
				print(e)
				self.close()
	def encodeGetCommand(self,id_hex):
		# Encodes a VE.Direct hex command to read data
		commandArray = []
		checksumArray = []
		idBytes = id_hex.to_bytes(2, 'little')

		checksumArray.append(0x7)
		checksumArray.append(idBytes[0])
		checksumArray.append(idBytes[1])
		checksumArray.append(0x0)

		checksum = 0x55
		for byte in checksumArray:
			checksum = (checksum - byte) % 256

		commandString = ":7{0:02X}{1:02X}00{2:02X}\n".format(idBytes[0],idBytes[1],checksum)
		return bytes(commandString,"utf-8")
	def decodeGetCommand(self,rawLine):
		#print(rawLine)
		if len(rawLine) == 0 or rawLine[0] != ":":
			return
		if rawLine[1] != "7":
			return
		dataBytes = wrap(rawLine[2:], 2)
		dataId = int("0x"+dataBytes[1]+dataBytes[0],16)
		#print("0x{0:04X}".format(dataId))
		# 8 bit: dataValue = int("0x"+dataBytes[3],16)
		# 16 bit: dataValue = int("0x"+dataBytes[4]+dataBytes[3],16)
		# 32 bit: dataValue = int("0x"+dataBytes[6]+dataBytes[5]+dataBytes[4]+dataBytes[3],16)
		if dataId == 0xED8D:
			dataValue = twos_complement(dataBytes[4]+dataBytes[3],16)
			self.statusVoltage=dataValue / 100
			self.cache.set("batteryVoltage",self.statusVoltage)
		elif dataId == 0xED8F:
			dataValue = twos_complement(dataBytes[4]+dataBytes[3],16)
			self.statusCurrent = dataValue / 1000
			self.cache.set("batteryCurrent",self.statusCurrent)
		elif dataId == 0xED8E:
			dataValue = twos_complement(dataBytes[4]+dataBytes[3],16)
			self.statusPower=dataValue
			self.cache.set("batteryPower",self.statusPower)
		elif dataId == 0xEEFF:
			dataValue = twos_complement(dataBytes[6]+dataBytes[5]+dataBytes[4]+dataBytes[3],32)
			self.statusConsumedAh=dataValue / 10
			self.cache.set("batteryConsumedAh",self.statusConsumedAh)
		elif dataId == 0x0FFF:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16) #unsigned
			self.statusStateOfCharge=dataValue / 100
			self.cache.set("batteryStateOfCharge",self.statusStateOfCharge)
		elif dataId == 0x0FFE:
			dataValue = int("0x"+dataBytes[4]+dataBytes[3],16) #unsigned
			self.statusTimeRemaining=dataValue
			self.cache.set("batteryTimeRemaining",self.statusTimeRemaining)
