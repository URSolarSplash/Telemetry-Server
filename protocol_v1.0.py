import serial
import time
import sys
import struct

def millis():
    return time.time()*1000

lastResponse = millis()
lastPulse = 0
nodeSerial = serial.Serial(port='/dev/cu.usbmodem14201',baudrate=115200)
connected = False
dropped = 0

def connect():
    global connected, nodeSerial,lastResponse
    if(nodeSerial.in_waiting!=0):
        byte =ord(nodeSerial.read(1))
        print(hex(byte))
        if(byte==0x69):
            nodeSerial.write(chr(0x68))
            time.sleep(.100)
            if(nodeSerial.in_waiting!=0):
                print(hex(ord(nodeSerial.read(1))))
                nodeSerial.write(chr(0x67))
                connected=True
                lastResponse = millis()

def sendHeartbeat():
    global nodeSerial,lastPulse, dropped
    if(millis()-lastPulse >= 250):
        #print('sent')
        nodeSerial.write(chr(0x50))
        lastPulse = millis()

def unpack(packet):
    global dropped
    sum =0;
    for i in range(16):
        sum+=packet[i]
    if(sum%256==255):
        unpackAlltrax(packet)
    else:
        dropped+=1
        print('Fropped'+str(dropped))

def unpackAlltrax(packet):
    temp = (packet[2]<<8) | packet[1]
    voltage = (packet[4]<<8)|packet[3]
    outCurrent = (packet[6]<<8)|packet[5]
    inCurrrent = (packet[8]<<8)|packet[7]
    dutyCycle = (packet[9]/255.0)*100
    error = packet[10]
    packetNum = packet[14]
    print('Temp: '+str(temp)+'deg C')
    print('Voltage: '+str(voltage)+'V')
    print('Output Current: '+str(outCurrent)+'A')
    print('Input Current: '+str(inCurrrent)+'A')
    print('Duty Cycle: '+str(dutyCycle)+'%')
    print('Error Code: '+str(error))
    print('Packet number: '+str(packetNum+1)+'/1')

def unpackGPS(packet):
    if(packet[14]==0):
        latStr = chr(packet[4])+chr(packet[3])+chr(packet[2])+chr(packet[1])
        lat = struct.unpack('>f',latStr)
        print(lat)

def checkResponse():
    global nodeSerial, lastResponse, connected, dropped
    if(nodeSerial.in_waiting!=0):
        byte =ord(nodeSerial.read(1))
        if(byte==0xF0):
            lastResponse = millis()
            time.sleep(.001)
            if(nodeSerial.in_waiting>=15):
                packet = [0] * 16
                packet[0] =byte
                for i in range(15):
                    packet[i+1]=ord(nodeSerial.read(1))
                unpack(packet)
            else:
                dropped+=1
                print('dropped'+str(dropped))
    elif(millis()-lastResponse>1000):
        connected = False
        print('disconnected')

def main():
    global connected, nodeSerial
    nodeSerial.reset_input_buffer()
    while True:
        try:
            if(connected):
                sendHeartbeat();
                checkResponse();
                pass
            else:
                connect()
        except KeyboardInterrupt:
            nodeSerial.close()
            sys.exit()

if __name__ == '__main__':
	main()
