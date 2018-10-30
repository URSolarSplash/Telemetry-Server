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
