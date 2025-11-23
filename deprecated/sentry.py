# Monitors the telemetry server status
# Blinks GPIO led for status on the telemetry server box
# Runs as a separate service on the pi
import RPi.GPIO as GPIO
from time import sleep
import requests

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(32,GPIO.OUT,initial=GPIO.LOW)

GPIO.output(32,GPIO.HIGH)
GPIO.output(32,GPIO.LOW)

status = 0
numDevices = 0
while True:
    try:
        r = requests.get('http://localhost:5000/stats')
        if r.status_code == 200:
            # Server is up
            status = 1
            jsonPacket = r.json()
            numDevices = int(jsonPacket["numActiveDevices"])
    except:
        # Server isn't up
        status = 0
    if status == 0:
        # Blink slowly since the telemetry is off
        for i in range(5):
            GPIO.output(32,GPIO.HIGH)
            sleep(1)
            GPIO.output(32,GPIO.LOW)
            sleep(1)
    elif status == 1:
        # blink a number of times representing the number of devices connected
        for i in range(numDevices):
            GPIO.output(32,GPIO.HIGH)
            sleep(0.1)
            GPIO.output(32,GPIO.LOW)
            sleep(0.1)
        sleep(1)
