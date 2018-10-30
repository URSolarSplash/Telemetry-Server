#!/usr/bin/env python
import traceback
import time
import serial
import serial.tools.list_ports
import sys
import atexit
import platform
import re

serialPorts = []
serialPortBuffers = []
serialPortModes = []

#Status indicator variables
serialPortsWantsStatus = []
statusVoltage = 0
statusCurrent = 0
statusRPM = 0
statusStateOfCharge = 0
statusTargetCurrent = 10
hasStatusData = False

#Parses a data message for data we are interested in.
def parseForData(inString):
	global hasStatusData, statusRe, statusVoltage, statusCurrent, statusStateOfCharge, statusRPM
	

def updateSerialPorts():
	#Scan for new serial ports that haven't been added already
	#print("Available ports:")
	portList = list(serial.tools.list_ports.comports())
	for port in portList:
		portAlreadyOpen = False
		#Check if we are already connected to this serial port
		for serialPort in serialPorts:
			if (serialPort.port == port[0]):
				#Port already exists
				portAlreadyOpen = True
		if portAlreadyOpen:
			continue

		#Blacklist some system ports
		if port[0]=="/dev/ttyAMA0":
			continue

		baudRate = 9600
		mode = 0
		#See if this port is the VE.Direct, which uses USB
		if port[0]=="/dev/ttyUSB0":
			#Use different baud rate and mode for this one
			mode = 1
			baudRate = 19200

		serialPort = serial.Serial(port[0],baudRate)
		if serialPort.is_open:
			print("Opened connection on port "+port[0]+", with mode flag "+str(mode)+".")
			serialPorts.append(serialPort)
			serialPortBuffers.append(b'')
			serialPortsWantsStatus.append(0)
			serialPortModes.append(mode)
		else:
			print("Failed attempted connection on port "+port[0]+".")
			serialPort.close()

	#Remove serial ports that have been closed
	for serialPort in serialPorts:
		if serialPort.is_open == False:
			print("Closed stale connection on port "+serialPort.port+".")
			del serialPortBuffers[serialPorts.index(serialPort)]
			del serialPortModes[serialPorts.index(serialPort)]
			del serialPortsWantsStatus[serialPorts.index(serialPort)]
			serialPorts.remove(serialPort)


while 1:
	updateSerialPorts()
	#Check for new input on any of the serial port lines
	for serialPort in serialPorts:
		serialIndex = serialPorts.index(serialPort)
		try:
			waitingBytes = serialPort.in_waiting
			#print (str(waitingBytes) +" bytes on port "+serialPort.port)
			if waitingBytes == 0:
				continue
			for c in serialPort.read(waitingBytes):
				if c == b'\n':
					if serialPortModes[serialIndex] == 0:
						handleLine(serialPort,serialPortBuffers[serialIndex],serialIndex)
						serialPortBuffers[serialIndex]=b''
					else:
						# Send victron buffer if we reached a line containing checksum
						# Otherwise add this line to the buffer
						rawLine = str(serialPortBuffers[serialIndex]).lstrip().rstrip().replace('\t',' ')
						rawLine = re.sub('/\p{C}+/u','',rawLine)
						serialPortBuffers[serialIndex]=b''
						#print "VICTRON BUFFER: "+rawLine+"\n"
						if rawLine.lower().startswith("checksum"):
							if len(victronBuffer) > 0:
								handleLine(serialPort,"URSSBATTERY"+victronBuffer,serialIndex)
								victronBuffer = ""
						else:
							for e in victronCommands:
								if rawLine.startswith(e):
									victronBuffer += ("," + rawLine)
									break
				else:
					serialPortBuffers[serialIndex] += c
		except Exception as e:
			#traceback.print_exc()
			serialPort.close()
			print("Connection error during port read on port "+serialPort.port+". port closed.")
	time.sleep(0.1)
