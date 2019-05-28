import serial

conn = serial.Serial(port="/dev/ttyACM0",baudrate=115200)
rxPacket = [0]*16

def generateChecksum(packet):
	_sum = 0
	for i in range(15):
		_sum+=packet[i]
	return (255-(_sum%256))

def isValid(packet):
	_sum = 0
	for i in range(16):
		_sum+=packet[i]
	return _sum%256

def unpack(packet):
	deviceID = (packet[14] & 0xF0) >> 4
	packetNum = packet[14] & 0x0F
	if(deviceID == 0x00):
		print("DEVICE_ALLTRAX: packet "+str(packetNum))
		txPacket = [0]*16
		txPacket[0] = 0x50
		throt = 125
		txPacket[1] = throt & 0xFF
		txPacket[2] = (throt & 0xFF) >> 8
		txPacket[15] = encodeChecksum(txPacket)
		conn.write(bytearray(txPacket))

	elif(deviceID == 0x01):
		print("DEVICE_VESC: packet "+str(packetNum))
		#send data
	elif(deviceID == 0x02):
		print("DEVICE_MOTOR_BOARD: packet "+str(packetNum))
		#send data
	elif(deviceID == 0x03):
		print("DEVICE_BATTERY_BOARD: packet "+str(packetNum))
		#send data
	elif(deviceID == 0x04):
		print("DEVICE_GPS_IMU: packet "+str(packetNum))
		#send data
	elif(deviceID == 0x05):
		print("DEVICE_THROTTLE: packet "+str(packetNum))
		#send data
	elif(deviceID ==0x06):
		print("DEVICE_SOLAR: packet "+str(packetNum))
		#send data

while True:
	#wait for data and respond
	if(conn.inWaiting() > 15):
		header = ord(conn.read())
		if(header == 0xF0):
			rxPacket[0] = header
			for i in range(1,16):
				rxPacket[i] = ord(conn.read())
			#print(rxPacket)
			if(decodeChecksum(rxPacket) == 255):
				unpack(rxPacket)
			else:
				print("Dropped Packet")
