from GenericSerialDevice import *
import time
import serial
import time
import sys
import struct
from .. import statistics

# State Constants
STATE_UNCONNECTED = 0 # Waiting for a initial message (0x69) from the node
STATE_CONNECTED_INIT = 1 # Got 0x69 packet, sent 0x68 response, waiting for device ID
STATE_CONNECTED_CONFIRMED = 2 # Connection active, waiting for data
STATE_CONNECTED_RECEIVING = 3 # Connection active, receiving a packet.

# Device ID Constants
DEVICE_ALLTRAX = 0x00
DEVICE_VESC = 0x01
DEVICE_MOTOR_BOARD = 0x02
DEVICE_BATTERY_BOARD = 0x03
DEVICE_GPS_IMU = 0x04
DEVICE_THROTTLE = 0x05

#TelemetryNode implementing URSS telemetry protocol
class TelemetryNodeDevice(GenericSerialDevice):
	def __init__(self,cache,portName):
		super(TelemetryNodeDevice,self).__init__(cache,portName,115200)
		self.lastResponse = self.millis()
		self.lastPulse = 0
		self.dropped = 0
		self.state = STATE_UNCONNECTED
		self.connectionTimeout = 0
		self.deviceId = None

	def millis(self):
		return time.time()*1000

	def generateChecksum(self,packet):
		sum = 0
		for i in range(15):
			sum += packet[i]
		return (255 - (sum % 256))

	def getChecksum(self,packet):
		sum = 0
		for i in range(16):
			sum += packet[i]
		return (sum % 256)

	def unpack(self,packet):
		if (self.deviceId == DEVICE_ALLTRAX):
			self.cache.set("controllerTemp",(packet[2] << 8 | packet[1]))
			self.cache.set("controllerInVoltage",(packet[4] << 8 | packet[3]))
			self.cache.set("controllerOutCurrent",(packet[6] << 8 | packet[5]))
			self.cache.set("controllerInCurrent",(packet[8] << 8 | packet[7]))
			self.cache.set("controllerDutyCycle",(packet[9]/255.0)*100.0)
			self.cache.set("alltraxFault",packet[10])
		elif (self.deviceId == DEVICE_VESC):
			self.cache.set("controllerTemp",(packet[2] << 8 | packet[1]))
			self.cache.set("controllerInVoltage",(packet[4] << 8 | packet[3]))
			self.cache.set("controllerOutCurrent",(packet[6] << 8 | packet[5]))
			self.cache.set("controllerInCurrent",(packet[8] << 8 | packet[7]))
			self.cache.set("controllerDutyCycle",(packet[9]/255.0)*100.0)
			self.cache.set("vescFault",packet[10])
		elif (self.deviceId == DEVICE_MOTOR_BOARD):
			motorTemp = struct.unpack(">f",chr(packet[4])+chr(packet[3])+chr(packet[2])+chr(packet[1]))[0]
			motorRpm = struct.unpack(">f",chr(packet[8])+chr(packet[7])+chr(packet[6])+chr(packet[5]))[0]
			propRpm = struct.unpack(">f",chr(packet[12])+chr(packet[11])+chr(packet[10])+chr(packet[9]))[0]
			self.cache.set("motorTemp",motorTemp)
			self.cache.set("motorRpm",motorRpm)
			self.cache.set("propRpm",propRpm)
		elif (self.deviceId == DEVICE_BATTERY_BOARD):
			pass
		elif (self.deviceId == DEVICE_GPS_IMU):
			if (packet[14] == 0):
				latitude = struct.unpack(">f",chr(packet[4])+chr(packet[3])+chr(packet[2])+chr(packet[1]))[0]
				longitude = struct.unpack(">f",chr(packet[8])+chr(packet[7])+chr(packet[6])+chr(packet[5]))[0]
				self.cache.set("gpsLatitude",latitude)
				self.cache.set("gpsLongitude",longitude)
				self.cache.set("gpsTimestamp",(packet[12] << 24 | packet[11] << 16 | packet[10] << 8 | packet[9]))
				self.cache.set("gpsNumSatellites",(packet[13]))
			elif (packet[14] == 1):
				speed = struct.unpack(">f",chr(packet[4])+chr(packet[3])+chr(packet[2])+chr(packet[1]))[0]
				heading = (packet[5]/255.0)*360.0
				self.cache.set("gpsHeading",heading)
				self.cache.set("gpsSpeed",speed)
			else:
				print("[Telemetry Node] GPS IMU board invalid packet state!")
				statistics.stats["numDroppedNodePackets"] += 1
		elif (self.deviceId == DEVICE_THROTTLE):
			self.cache.set("throttle",packet[2] << 8 | packet[1])

	def sendHeartbeat(self):
		packet = [0] * 16
		packet[0] = 0x50
		packet[15] = self.generateChecksum(packet)
		#print("[Telemetry Node] Sending heartbeat packet: "+str(packet))
		self.port.write(bytearray(packet))

	def update(self):
		#print(self.state)
		try:
			# Connecting sequence
			if (self.state == STATE_UNCONNECTED):
				if (self.port.in_waiting != 0):
					byte=ord(self.port.read(1))
					if(byte==0x69):
						self.port.write(chr(0x68))
						self.state = STATE_CONNECTED_INIT
						self.connectionTimeout = self.millis()
			# Connecting sequence
			elif (self.state == STATE_CONNECTED_INIT):
				if (self.millis() - self.connectionTimeout > 100):
					self.state = STATE_UNCONNECTED
				else:
					if(self.port.in_waiting!=0):
						self.deviceId = ord(self.port.read(1))
						if self.deviceId == 0x69:
							self.state = STATE_UNCONNECTED
						else:
							print("[Telemetry Node] Connected to device id "+hex(self.deviceId))
							self.port.write(chr(0x67))
							self.lastResponse = self.millis()
							self.lastPulse = self.millis()
							self.state = STATE_CONNECTED_CONFIRMED
			# Device is connected and receiving data
			elif (self.state == STATE_CONNECTED_CONFIRMED):
				# Every 250 ms, send a heartbeat pulse.
				if (self.millis() - self.lastPulse >= 250):
					self.sendHeartbeat()
					self.lastPulse = self.millis()

				# If data is received, read and handle the packet.
				if (self.port.in_waiting != 0):
					byte = ord(self.port.read(1))
					if (byte == 0xF0):
						self.lastResponse = self.millis()
						if(self.port.in_waiting >= 15):
							self.readPacket()
						else:
							# We haven't received the entire packet. Switch states and wait for packet to come.
							self.state = STATE_CONNECTED_RECEIVING
				elif (self.millis() - self.lastResponse > 1000):
					self.state = STATE_UNCONNECTED
					print('[Telemetry Node] Node timed out, reset to STATE_UNCONNECTED')
			elif (self.state == STATE_CONNECTED_RECEIVING):
				# Waiting for 15 packets so we can read.
				if (self.port.in_waiting >= 15):
					self.readPacket()
					self.state = STATE_CONNECTED_CONFIRMED
				# If it's been more than 10ms, give up on the packet.
				if (self.millis() - self.lastResponse > 10):
					statistics.stats["numDroppedNodePackets"] += 1
					print('[Telemetry Node] dropped packet!')
					self.state = STATE_CONNECTED_CONFIRMED
		except Exception as e:
			print(e)
			self.close()
	def readPacket(self):
		packet = [0] * 16
		packet[0] = 0xF0
		for i in range(15):
			packet[i+1]=ord(self.port.read(1))
		checksumValue = self.getChecksum(packet)
		#print(checksumValue)
		if (checksumValue == 255):
			self.unpack(packet)
		else:
			print("[Telemetry Node] Packet failed checksum. Packet fropped! checksum value = "+str(checksumValue))
			statistics.stats["numDroppedNodePackets"] += 1
		#print("[Telemetry Node] recv'd packet:"+str(packet))
