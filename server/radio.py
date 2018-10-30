import serial

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
            print("[Radio Manager] Detected serial telemetry device.")
        except (serial.SerialException):
            self.mode = 0
            print("[Radio Manager] No detected serial telemetry device.")
    def write(self):
        # Writes a data point update to the radio stream
        # For now, does nothing
        return
    def shutdown(self):
        try:
            self.serialPortWrite.close()
        except:
            pass
        print("[Radio Manager] shutdown complete.")
