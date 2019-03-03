import time
import server.config as config
import math
import random

# Control Algorithms class
# Handles all control algorithms which set values.
# Will be disabled if the server is in "slave" mode.
class ControlAlgorithms:
    def __init__(self, cache):
        self.cache = cache
        self.lastUpdate = time.time()
    def update(self):
        if time.time() - self.lastUpdate < config.controlAlgorithmUpdateRate:
            return
        else:
            self.lastUpdate = time.time()
        if config.controlAlgorithmMockData:
            # Save mock data into the cache for a bunch of data points.
            self.cache.set("bmvVoltage",35.0+math.sin(time.time()/1000.0)*1.0+random.random())
            self.cache.set("bmvCurrent",-(1.1*(self.cache.getNumerical("throttle",0))+random.random()))
            motorRpm = (3000.0+math.sin(time.time()/5.0)*1500.0)*((time.time() % 100)/100)
            self.cache.set("motorRpm",motorRpm)
            self.cache.set("propRpm",motorRpm*0.58)
            self.cache.set("gpsSpeed",motorRpm*0.01+random.random())
            self.cache.set("throttleCutoff",50+math.sin(time.time()/5.0)*50)
            self.cache.set("throttleCurrentTarget",-60)
            if (self.cache.getNumerical("throttleCutoff",0) > 90):
                self.cache.set("throttleCurrentTarget",-100)
            self.cache.set("throttleMode",1)
        ## ------ AUTO THROTTLE REGULATION ALGORITHM -------
        # Mode 0 - Manual throttle
        # Mode 1 - Current limiting throttle
        #          Maximizes throttle, aiming to hit a certain current target.
        # Inputs: Throttle cutoff - Value of user throttle potentiometer
        #         Limiter setting - Target amperage from user limiter potentiometer
        #         Throttle mode - Manual / auto based on user input
        if self.cache.getNumerical("throttleMode",0) == 0:
            # Mode 0 - Manual Throttle
            # Just set output throttle to the throttle cutoff value.
            self.cache.set("throttle",self.cache.getNumerical("throttleCutoff",0))
        else:
            # Mode 1 - Current limiting throttle
            throttleCutoff = self.cache.getNumerical("throttleCutoff",0)
            current = self.cache.getNumerical("bmvCurrent",0)
            targetCurrent = self.cache.getNumerical("throttleCurrentTarget",0)
            throttle = self.cache.getNumerical("throttle",0)
            if (current < targetCurrent):
                throttle -= 1;
            elif (current > targetCurrent):
                throttle += 1;
            throttle = min(throttleCutoff, throttle)
            self.cache.set("throttle",throttle)
