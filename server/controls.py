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
        self.prevBoatConfig = 0
        self.prevThrottleMode = 0
        self.throttleOutEnable = 0

    
    def millis(self):
        return time.time() * 1000

    def getEffective(self, avgCurrent):
        def interp(val, a, b, x, y):
            q = (val - a) / (b - a)
            return y + (1 - q) * (x - y)

        effective = 0.0
        if avgCurrent <= 7.9:
            effective = 39.5
        elif avgCurrent <= 23.5:
            # math
            # x = (avgCurrent-7.9)/(23.5-7.9)
            # effective = 35.25 + (1-x)*(39.5-35.25)
            return interp(avgCurrent, 7.9, 23.5, 39.5, 35.25)
        elif avgCurrent <= 33.8:
            return interp(avgCurrent, 23.5, 33.8, 35.25, 33.8)
        elif avgCurrent <= 60.8:
            return interp(avgCurrent, 33.8, 60.8, 33.8, 30.4)
        elif avgCurrent <= 104.1:
            return interp(avgCurrent, 60.8, 104.1, 30.4, 26.03)
        elif avgCurrent <= 138.4:
            return interp(avgCurrent, 104.1, 138.4, 26.03, 23.07)
        elif avgCurrent <= 212.0:
            return interp(avgCurrent, 138.4, 212.0, 23.07, 17.67)
        else:
            effective = 17.667
        return effective

    def update(self):
        if time.time() - self.lastUpdate < config.controlAlgorithmUpdateRate:
            return
        else:
            self.lastUpdate = time.time()
        if config.controlAlgorithmMockData:
            # Save mock data into the cache for a bunch of data points.

            self.cache.set(
                "batteryVoltage",
                35.0 + math.sin(time.time() / 1000.0) * 1.0 + random.random(),
            )
            self.cache.set("batteryCurrent", math.sin(time.time() / 5.0) * 100.0)
            self.cache.set(
                "batteryPower",
                self.cache.getNumerical("batteryVoltage", 0)
                * self.cache.getNumerical("batteryCurrent", 0),
            )
            motorRpm = (1640.0 + math.sin(time.time() / 5.0) * 1500.0) * (
                (time.time() % 100) / 100
            )
            self.cache.set("motorRpm", motorRpm)
            self.cache.set("propRpm", motorRpm * 0.58)
            self.cache.set("gpsSpeedMph", motorRpm * 0.008 + random.random())
            self.cache.set("throttleInput", 127.5 + math.sin(time.time() / 2.0) * 127.5)
            self.cache.set("imuPitch", random.random() * 10)
            solarCurrent1 = 4.0 + (random.random() * 0.05)
            solarCurrent2 = 4.0 + (random.random() * 0.05)
            self.cache.set("solarChargerCurrent1", solarCurrent1)
            self.cache.set("solarChargerCurrent2", solarCurrent2)
            self.cache.set("solarChargerCurrentTotal", solarCurrent1 + solarCurrent2)
            self.cache.set(
                "batteryStateOfCharge", 80 + math.sin(time.time() / 50.0) * 20
            )
            # self.cache.set("throttleCutoff",50+math.sin(time.time()/5.0)*50)
            # self.cache.set("throttleCurrentTarget",-60)
            # if (self.cache.getNumerical("throttleCutoff",0) > 90):
            #    self.cache.set("throttleCurrentTarget",-100)
            # self.cache.set("throttleMode",1)
        ## ------ AUTO THROTTLE REGULATION ALGORITHM -------
        # Mode 0 - Manual throttle
        # Mode 1 - Current limiting throttle
        #          Maximizes throttle, aiming to hit a certain current target.
        # Inputs: Throttle cutoff - Value of user throttle potentiometer
        #         Limiter setting - Target amperage from user limiter potentiometer
        #         Throttle mode - Manual / auto based on user input

        # If we switch boat config or mode, require a throttle reset
        newBoatConfig = self.cache.getNumerical("boatConfig", 0)
        if self.prevBoatConfig != newBoatConfig:
            self.prevBoatConfig = newBoatConfig
            self.throttleOutEnable = False
        newThrottleMode = self.cache.getNumerical("throttleMode", 0)
        if self.prevThrottleMode != newThrottleMode:
            self.prevThrottleMode = newThrottleMode
            self.throttleOutEnable = False

        # If dead man's switch is pulled, require a throttle reset
        if self.cache.getNumerical("throttleEnabled", 0) == 0:
            self.cache.set("throttle", 0)
            self.throttleOutEnable = False
        else:
            if self.cache.getNumerical("throttleMode", 0) == 0:
                # Mode 0 - Manual Throttle
                # Just set output throttle to the throttle cutoff value.
                self.cache.set("throttle", self.cache.getNumerical("throttleInput", 0))
            else:
                # Mode 1 - Current limiting throttle
                throttleInput = self.cache.getNumerical("throttleInput", 0)
                throttleOutput = self.cache.getNumerical("throttle", 0)
                currentInput = self.cache.getNumerical("batteryCurrent", 0)

                # This goal current is read by the VESC.
                # Note: Alltrax right now does not support current-based mode!
                # Map throttle input to a current value
                goalCurrent = (throttleInput / 255.0) * -60.0
                self.cache.set("throttleCurrentTarget", goalCurrent)
                self.cache.set("throttle", throttleInput)

            # Handle any case where it's been deemed the throttle must be reset
            if not self.throttleOutEnable:
                if self.cache.getNumerical("throttle", 0) <= 5:
                    self.throttleOutEnable = True
                self.cache.set("throttle", 0)
                self.cache.set("throttleCurrentTarget", 0)

        # current recommendation
        if self.cache.getNumerical("startTime", 0) == 0:
            self.cache.set("startTime", self.millis())
        elapsedTime = self.millis() - self.cache.getNumerical("startTime", 0)
        # print("Elapsed time: "+str(elapsedTime))
        avgCurrent = self.cache.getNumerical("batteryConsumedAh", 0) / elapsedTime
        # print("Avg current: "+str(avgCurrent))
        ahrRemaining = self.getEffective(avgCurrent) + self.cache.getNumerical(
            "batteryConsumedAh", 0
        )  # Consumed Ah is a neg. number
        # print("Ahr remaining: "+str(ahrRemaining))
        suggestedCurrent = (ahrRemaining - self.cache.getNumerical("targetAh", 0)) / (
            (self.cache.getNumerical("targetDuration", 3 * 1000 * 3600) - elapsedTime)
            / 3.6e6
        )
        # print("Suggested current: "+str(suggestedCurrent))
        if suggestedCurrent < 0:
            suggestedCurrent = 0
        suggestedCurrent += self.cache.getNumerical("solarChargerCurrentTotal", 0)
        self.cache.set("throttleRecommendation", suggestedCurrent);
