from .GenericSerialDevice import GenericSerialDevice
import time
import serial
import time
import sys
import struct
from .. import statistics
import traceback

# StatelessTelemetryNodeDevice
# A version of the telemetry node protocol that does not use state
# With this system, the node sends encoded packets periodically
# Each time the node sends an encoded packet, the server can respond with some data.
# This all occurs at 10hz

# Device ID Constants
DEVICE_ALLTRAX = 0x01
DEVICE_MOTOR_BOARD = 0x02
DEVICE_BATTERY_BOARD = 0x03
DEVICE_GPS_IMU = 0x04
DEVICE_THROTTLE = 0x05
DEVICE_SOLAR = 0x06

# Packet Breakdown:
#- Byte 0: Header (0xF0)
#- Byte 1-4:  Data (1)
#- Byte 5-8:  Data (2)
#- Byte 9-12: Data (3)
#- Byte 13:   Data (misc)
#- Byte 14: Packet metadata (Device ID and Packet Number)
#- Byte 15: 8-bit Checksum

class StatelessTelemetryNodeDevice(GenericSerialDevice):
	def __init__(self,cache,portName):
		super(StatelessTelemetryNodeDevice,self).__init__(cache,portName,115200)
		self.lastValidResponse = self.millis()
		self.dropped = 0
		self.connectionTimeout = 0

	def handlePacket(self,packet):
		packetHeader = packet[0]
		deviceId = (packet[14] & 0xF0) >> 4
		packetNum = (packet[14] & 0x0F)
		packetChecksum = packet[15]

		if deviceId == DEVICE_ALLTRAX:
			self.cache.set("controllerTemp",(((packet[2] << 8 | packet[1])-559)*(1/2.048)))
			self.cache.set("controllerInVoltage",((packet[4] << 8 | packet[3])*0.1025))
			self.cache.set("controllerOutCurrent",(packet[6] << 8 | packet[5]))
			self.cache.set("controllerInCurrent",(packet[8] << 8 | packet[7]))
			self.cache.set("controllerDutyCycle",(packet[9]/255.0)*100.0)
			self.cache.set("alltraxFault",packet[10])
		elif deviceId == DEVICE_BATTERY_BOARD:
			pass
		elif deviceId == DEVICE_MOTOR_BOARD:
			motorTemp = struct.unpack(">f",bytes([packet[4],packet[3],packet[2],packet[1]]))[0]
			motorRpm = (packet[8] << 24 | packet[7] << 16 | packet[6] << 8 | packet[5])
			propRpm = (packet[12] << 24 | packet[11] << 16 | packet[10] << 8 | packet[9])
			if(motorTemp == motorTemp):
				self.cache.set("motorTemp",motorTemp)
			self.cache.set("motorRpm",motorRpm)
			self.cache.set("propRpm",propRpm)
		elif deviceId == DEVICE_GPS_IMU:
			if packetNum == 0:
				imuPitch = struct.unpack(">f",bytes([packet[4],packet[3],packet[2],packet[1]]))[0]
				imuRoll = struct.unpack(">f",bytes([packet[8],packet[7],packet[6],packet[5]]))[0]
				gpsFix = packet[9]
				gpsNumSatellites = packet[10]
				gpsHeading = (packet[11]/255.0)*360.0
				self.cache.set("imuPitch",imuPitch)
				self.cache.set("imuRoll",imuRoll)
				self.cache.set("gpsFix",gpsFix)
				# Only save GPS data points if we have a GPS fix.
				if (gpsFix):
					self.cache.set("gpsNumSatellites",gpsNumSatellites)
					self.cache.set("gpsHeading",gpsHeading)
			elif packetNum == 1:
				latitude = struct.unpack(">f",bytes([packet[4],packet[3],packet[2],packet[1]]))[0]
				longitude = struct.unpack(">f",bytes([packet[8],packet[7],packet[6],packet[5]]))[0]
				speedKnots = struct.unpack(">f",bytes([packet[12],packet[11],packet[10],packet[9]]))[0]
				gpsFix = packet[13]
				self.cache.set("gpsFix",gpsFix)
				# Only save GPS data points if we have a GPS fix.
				if (gpsFix):
					self.cache.set("gpsLatitude",latitude)
					self.cache.set("gpsLongitude",longitude)
					self.cache.set("gpsSpeedKnots",speedKnots)
					KNOTS_TO_MPH = 1.15078
					self.cache.set("gpsSpeedMph",speedKnots * KNOTS_TO_MPH)
		elif deviceId == DEVICE_THROTTLE:
			throttleValue = packet[2] << 8 | packet[1]
			self.cache.set("throttleInput",throttleValue)
		elif deviceId == DEVICE_SOLAR:
			pass

	# Handles sending a response packet to a device
	# This provides the opportunity to feed back data to the nodes
	def sendResponse(self, deviceId):
		# Build packet header
		packet = [0] * 16
		packet[0] = 0x50

		if deviceId == DEVICE_ALLTRAX:
			# Write back the value of the throttle for the motor controller output
			throttle = int(self.cache.getNumerical('throttle',0))
			packet[1] = (throt & 0xFF)
			packet[2] = (throt & 0xFF) >> 8
		elif deviceId == DEVICE_BATTERY_BOARD:
			pass
		elif deviceId == DEVICE_MOTOR_BOARD:
			pass
		elif deviceId == DEVICE_GPS_IMU:
			pass
		elif deviceId == DEVICE_THROTTLE:
			pass
		elif deviceId == DEVICE_SOLAR:
			pass

		# Generate checksum at the end of the packet, and write the packet to the serial stream.
		packet[15] = self.encodeChecksum(packet)
		self.port.write(bytearray(packet))

	# Update function - Handles reading data, parsing, response packets
	def update(self):
		try:
			# As soon as we receive any serial data, append it into the buffer.
			while (self.port.in_waiting > 0):
				self.buffer.append(ord(self.port.read(1)))

			# Delete from the buffer until we reach a header byte or the buffer is empty.
			# This will remove invalid packets, old data, etc.
			# After this operation, the first byte is GUARANTEED to be a 0xF0 header, or the buffer is empty.
			while (len(self.buffer) > 0 and self.buffer[0] != 0xF0):
				self.buffer.pop(0)

			# If the buffer still has data, then it must be a packet!
			# Consume it and read it
			if (len(self.buffer) >= 16):
				packet = self.buffer[0:16]
				deviceId = (packet[14] & 0xF0) >> 4
				packetNum = (packet[14] & 0x0F)
				self.buffer = self.buffer[16:]

				# Validate the checksum
				checksumValue = self.decodeChecksum(packet)
				if (checksumValue == 255):
					self.handlePacket(packet)
					self.sendResponse(deviceId) # Send a response after reading a valid packet.
				else:
					print("[Telemetry Node] Packet dropped!")
					statistics.stats["numDroppedNodePackets"] += 1

		except Exception as e:
			print("[Stateless Telemetry Node] Error: "+str(e))
			traceback.print_tb(e.__traceback__)
			self.close()

	def millis(self):
		return time.time()*1000

	def encodeChecksum(self,packet):
		sum = 0
		for i in range(15):
			sum += packet[i]
		return (255 - (sum % 256))

	def decodeChecksum(self,packet):
		sum = 0
		for i in range(16):
			sum += packet[i]
		return (sum % 256)

# Hex char to byte string
def byteChar(char):
	return bytes(bytearray((char,)))