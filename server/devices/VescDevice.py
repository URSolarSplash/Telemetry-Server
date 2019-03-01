from GenericSerialDevice import *

class VescDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(VescDevice, self).__init__(cache, portName, 4800)
	def update(self):
		if self.open:
			try:
				//Get the throttle value and write it to the vesc.
                throttle = self.cache.
			except Exception as e:
				traceback.print_exc()
				self.close()
