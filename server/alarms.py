
# Class representing an alarm
class Alarm(dict):
	def __init__(self,key,desc,min,max):
		dict.__init__(self,key=key,desc=desc,value=0,range_min=min,range_max=max,state=False)
		self.cache = None
		self.min = min
		self.max = max
		self.key = key
	def setCache(self, cache):
		self.cache = cache
	def getAlarmState(self):
		if self.cache:
			value = self.cache.get(self.key)
			self["value"] = value
			self["state"] = False
			if value == None:
				self["state"] = False
			elif value < self.min:
				self["state"] = True
			elif value > self.max:
				self["state"] = True
		else:
			self["state"] = False
		return self["state"]
