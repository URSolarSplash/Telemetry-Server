import time
import config
import math

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
			self.cache.set("bmvVoltage",35.0+math.sin(time.time()/10000.0)*1.0)
			self.cache.set("bmvCurrent",15.0+math.sin(time.time()/10.0)*5.0)
			motorRpm = (3000.0+math.sin(time.time()/5.0)*1500.0)*((time.time() % 100)/100)
			self.cache.set("motorRpm",motorRpm)
			self.cache.set("propRpm",motorRpm*0.58)
			self.cache.set("gpsSpeed",motorRpm*0.01)
		if config.controlAlgorithmEnduranceThrottle:
			self.cache.set("throttle",0)
