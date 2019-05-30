import time
import server.config as config
import math
import random
from simple_pid import PID

# Control Algorithms class
# Handles all control algorithms which set values.
# Will be disabled if the server is in "slave" mode.
class ControlAlgorithms:
    def __init__(self, cache):
        self.cache = cache
        self.lastUpdate = time.time()
        self.throttlePid = PID(1.5,0.1,0.0,setpoint=0)
    def update(self):
        if time.time() - self.lastUpdate < config.controlAlgorithmUpdateRate:
            return
        else:
            self.lastUpdate = time.time()
        if config.controlAlgorithmMockData:
            # Save mock data into the cache for a bunch of data points.


            self.cache.set("batteryVoltage",35.0+math.sin(time.time()/1000.0)*1.0+random.random())
            self.cache.set("batteryCurrent",math.sin(time.time()/5.0) * 100.0)
            self.cache.set("batteryPower",self.cache.getNumerical("batteryVoltage",0)*self.cache.getNumerical("batteryCurrent",0))
            motorRpm = (1640.0+math.sin(time.time()/5.0)*1500.0)*((time.time() % 100)/100)
            self.cache.set("motorRpm",motorRpm)
            self.cache.set("propRpm",motorRpm*0.58)
            self.cache.set("gpsSpeedMph",motorRpm*0.008+random.random())
            self.cache.set("throttleInput",127.5 + math.sin(time.time()/2.0)*127.5)
            self.cache.set("imuPitch",random.random()*10)
            solarCurrent1 = 4.0 + (random.random()*0.05)
            solarCurrent2 = 4.0 + (random.random()*0.05)
            self.cache.set("solarChargerCurrent1",solarCurrent1)
            self.cache.set("solarChargerCurrent2",solarCurrent2)
            self.cache.set("solarChargerCurrentTotal",solarCurrent1 + solarCurrent2)
            self.cache.set("batteryStateOfCharge",80 + math.sin(time.time()/50.0) * 20)
            #self.cache.set("throttleCutoff",50+math.sin(time.time()/5.0)*50)
            #self.cache.set("throttleCurrentTarget",-60)
            #if (self.cache.getNumerical("throttleCutoff",0) > 90):
            #    self.cache.set("throttleCurrentTarget",-100)
            #self.cache.set("throttleMode",1)
        ## ------ AUTO THROTTLE REGULATION ALGORITHM -------
        # Mode 0 - Manual throttle
        # Mode 1 - Current limiting throttle
        #          Maximizes throttle, aiming to hit a certain current target.
        # Inputs: Throttle cutoff - Value of user throttle potentiometer
        #         Limiter setting - Target amperage from user limiter potentiometer
        #         Throttle mode - Manual / auto based on user input
        self.cache.set("throttleMode",0)
        if self.cache.getNumerical("throttleMode",0) == 0:
            # Mode 0 - Manual Throttle
            # Just set output throttle to the throttle cutoff value.
            self.cache.set("throttle",self.cache.getNumerical("throttleInput",0))
        else:
            # Mode 1 - Current limiting throttle
            throttleInput = self.cache.getNumerical("throttleInput",0)
            throttleOutput = self.cache.getNumerical("throttle",0)
            currentInput = self.cache.getNumerical("batteryCurrent",0)

            # Map throttle input to a current value
            self.cache.set("throttleCurrentTarget",throttleInput * -0.6)
            goalCurrent = self.cache.getNumerical("throttleCurrentTarget",0)

            # Scale currents so positive = drawing current
            currentInput = -currentInput;
            goalCurrent = -goalCurrent;

            self.throttlePid.setpoint = goalCurrent
            pidOut = self.throttlePid(currentInput)
            #print("PID delta = "+str(pidOut))
            throttle = throttleOutput +pidOut
            #print("PID output = "+str(throttle))

            throttle = max(min(255,throttle),0)
            self.cache.set("throttle",throttle)
