import serial
from RepeatedTimer import RepeatedTimer
from DataPoint import DataPoint
from time import sleep
from threading import Event
import serial.tools.list_ports

currentDevices = []

testDataPoint = DataPoint("test")

def checkDeviceName(deviceId):
    if deviceId.startswith("/dev/cu.usb"):
        return True
    return False

def updateDevices():
    print "Updating Device List..."
    for port in serial.tools.list_ports.comports():
        print port

deviceTimer = RepeatedTimer(10,updateDevices)
exit = Event()

def main():
    while not exit.is_set():
        #print currentDevices
        print testDataPoint
        sleep(1)
    print "Shutting down."
    # Clean up everything
    deviceTimer.stop()

#---- Main entry point and interrupt handler ----
def quit(signo, _frame):
    exit.set()

if __name__ == '__main__':
    import signal
    for sig in ('TERM', 'HUP', 'INT'):
        signal.signal(getattr(signal, 'SIG'+sig), quit);
    main()
