from GenericSerialDevice import *
import time
import serial
import time
import sys
import struct
from .. import statistics

STATE_UNCONNECTED = 0 # Waiting for a initial message (0x69) from the node
STATE_CONNECTED_INIT = 1 # Got 0x69 packet, sent 0x68 response, waiting for device ID
STATE_CONNECTED_CONFIRMED = 2 # Connection active, waiting for data
STATE_CONNECTED_RECEIVING = 3 # Connection active, receiving a packet.

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
						print("[Telemetry Node] Connecting to device id "+hex(self.deviceId))
						self.port.write(chr(0x67))
						self.lastResponse = self.millis()
						self.state = STATE_CONNECTED_CONFIRMED
			# Device is connected and receiving data
			elif (self.state == STATE_CONNECTED_CONFIRMED):
				# Every 250 ms, send a heartbeat pulse.
				if (self.millis() - self.lastPulse >= 250):
					self.port.write(chr(0x50))
					self.lastPulse = self.millis()

				# If data is received, read and handle the packer.
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
		#unpack(packet)
		print("[Telemetry Node] recv'd packet:"+str(packet))
