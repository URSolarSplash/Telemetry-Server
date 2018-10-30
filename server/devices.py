import re
import serial

class GenericSerialDevice(object):
    def __init__(self, portName, baudRate):
        self.open = False
        self.portName = portName
        self.baudRate = baudRate
        print("[Serial Device] Opened serial connection on port "+portName+", with baud rate "+str(baudRate)+".")
        try:
            self.port = serial.Serial(portName,baudRate)
            self.open = True
        except:
            print("[Serial Device] Failed to open device!")
            self.open = False
    def isOpen(self):
        return self.open and self.port.is_open
    def close(self):
        print("[Serial Device] Closed serial connection on port "+self.portName+".")
        if self.open:
            self.port.close()
            self.open = False
    def update(self):
        # Gets new serial data if it is incoming
        pass

class TelemetryDevice(GenericSerialDevice):
    def __init__(self, portName):
        super(TelemetryDevice, self).__init__(portName, 115200)

class RadioDevice(GenericSerialDevice):
    def __init__(self, portName):
        super(RadioDevice, self).__init__(portName, 57600)

class UsbGpsDevice(GenericSerialDevice):
    def __init__(self, portName):
        super(UsbGpsDevice, self).__init__(portName, 19200)

class VictronDevice(GenericSerialDevice):
    def __init__(self, portName):
        super(VictronDevice, self).__init__(portName, 19200)

        '''
        self.victronBuffer = ""
        self.victronCommands = ["PID","V","VS","I","P","SOC","TTG","Alarm","Relay"]
        self.statusRe = re.compile("BATTERY,PID \S*,V (-?\d*),VS (-?\d*),I (-?\d*),P (-?\d*),SOC (-?\d*),TTG (-?\d*),.*")
    def readByte(self, input):
        # Reads in a single byte
        victronBuffer = victronBuffer + input

    def parseBuffer(self, string):
        # Test to check that the serial input matches the buffer regex
        m = statusRe.match(inString)
    	if (m):
    		statusVoltage = int(m.group(1))/1000.0
    		statusCurrent = int(m.group(3))/1000.0
    		statusStateOfCharge = int(m.group(5))/1000.0
    		hasStatusData = True
    	if inString.startswith("RPM="):
    		statusRPM = int(inString[4:])
    		hasStatusData = True
            '''
