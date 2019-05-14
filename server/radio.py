import serial
from server import statistics

# Handles radio communication of telemetry data
# This handles output from the Pi to the shore computer
# The receiving of this data is handled via the standard serial system;
# the usb radio telemetry device shows up as a serial device.
class RadioManager():
    def __init__(self):
        self.mode = 0
        try:
            self.serialPortWrite = serial.Serial(
            	port='/dev/serial0',
            	baudrate=57600,
            	parity=serial.PARITY_NONE,
            	stopbits=serial.STOPBITS_ONE,
            	bytesize=serial.EIGHTBITS
            )
            self.mode = 1
            statistics.stats["hasRadio"] =  True
            print("[Radio] Detected serial telemetry device.")
        except (serial.SerialException):
            self.mode = 0
            statistics.stats["hasRadio"] =  False
            print("[Radio] No detected serial telemetry device.")
    def write(self,dataName, dataValue):
        # Writes a data point update to the radio stream if radio is active
        if self.mode == 1:
            #print("[Radio] writing data update string "+dataString)
            dataString= "{0}:{1}\n".format(dataName,dataValue)
            self.serialPortWrite.write(bytes(dataString,"utf-8"))
    def shutdown(self):
        try:
            self.serialPortWrite.close()
        except:
            pass
        print("[Radio] shutdown complete.")
