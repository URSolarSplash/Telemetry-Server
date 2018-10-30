import re
import serial

class GenericDevice:
    def __init__(self):
        return
    def _


class TelemetryDevice(GenericDevice):
    def readByte():
        # Reads in a single byte

class UsbGpsDevice(GenericDevice):

class VictronDevice(GenericDecoder):
    def __init__(self):
        self.serialBuffer = []
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
