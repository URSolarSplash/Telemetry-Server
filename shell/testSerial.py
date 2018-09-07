#!/usr/bin/env python
import traceback
import time
import serial
import serial.tools.list_ports
import sys
import atexit
import platform
import re

serialPortWrite = serial.Serial(
	port='/dev/serial0',
	baudrate=57600,
	parity=serial.PARITY_NONE,
	stopbits=serial.STOPBITS_ONE,
	bytesize=serial.EIGHTBITS
)

print "Starting serial port scanner..."

serialPorts = []
serialPortBuffers = []
serialPortModes = []
victronBuffer = ""
victronCommands = ["PID","V","VS","I","P","SOC","TTG","Alarm","Relay"]

#Status indicator variables
serialPortsWantsStatus = []
statusVoltage = 0
statusCurrent = 0
statusRPM = 0
statusStateOfCharge = 0
statusTargetCurrent = 10
hasStatusData = False
statusRe = re.compile("BATTERY,PID \S*,V (-?\d*),VS (-?\d*),I (-?\d*),P (-?\d*),SOC (-?\d*),TTG (-?\d*),.*")

#Parses a data message for data we are interested in.
def parseForData(inString):
	global hasStatusData, statusRe, statusVoltage, statusCurrent, statusStateOfCharge, statusRPM
	m = statusRe.match(inString)
	if (m):
		statusVoltage = int(m.group(1))/1000.0
		statusCurrent = int(m.group(3))/1000.0
		statusStateOfCharge = int(m.group(5))/1000.0
		hasStatusData = True
	if inString.startswith("RPM="):
		statusRPM = int(inString[4:])
		hasStatusData = True

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

def doAtExit():
	#Close any open serial ports
	for serialPort in serialPorts:
		print("Closed connection on port "+serialPort.port+".")
		serialPort.close()
	print("Program shutdown.")

atexit.register(doAtExit);

def handleLine(port,line,index):
	rawString = str(line).rstrip()
	if rawString.startswith("URSS"):
		rawString = rawString[4:]
		parseForData(rawString)
		serialString = "{ \"port\": \""+port.port+"\", \"message\": \""+rawString+"\" }"
		print(serialString)
		serialPortWrite.write(serialString+"\n")
		serialPortWrite.flush()
		if (rawString == "REQUEST_STATUS"):
			print("Flagged serial port \""+port.port+"\" as data monitoring device!\n")
			serialPortsWantsStatus[index] = 1
			serialPorts[serialIndex].write("Connected!      Waiting for data.\n")

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
	#Send status data if we have anything new
	if hasStatusData == True:
		#print("Sending new status data...\n")
		for serialPort in serialPorts:
			#print("Sending new status to port "+serialPort.port+"\n")
			serialIndex = serialPorts.index(serialPort)
			if (serialPortsWantsStatus[serialIndex] == 1):
				statusStringLine1 = "{:<16}".format("{:.2f}v / {:.2f}A".format(statusVoltage,statusCurrent))
				statusStringLine2 = "{:<16}".format("{:.0%} RPM: {:}".format(statusStateOfCharge,statusRPM))
				serialPort.write(statusStringLine1+statusStringLine2+"\n")
		hasStatusData = False
