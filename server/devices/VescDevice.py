from .GenericSerialDevice import GenericSerialDevice
import pyvesc

class VescDevice(GenericSerialDevice):
	def __init__(self, cache, portName):
		super(VescDevice, self).__init__(cache, portName, 115200)
		self.throttleOutEnable = False
		print("INIT VESC 4")
	def update(self):
		if self.open:
			#try:
			self.writeData()

			waitingBytes = self.port.in_waiting
			if not waitingBytes == 0:
				for c in self.port.read(waitingBytes):
					self.buffer.append(c)

			# Check for new vesc message in the buffer
			vescMessage, consumed = pyvesc.decode(bytes(self.buffer))
			self.buffer = self.buffer[consumed:]
			if vescMessage:
				self.cache.set("controllerTemp",float(vescMessage.temp_pcb))
				self.cache.set("controllerInCurrent",float(vescMessage.current_in))
				self.cache.set("controllerOutCurrent",float(vescMessage.current_motor))
				self.cache.set("controllerDutyCycle",float(vescMessage.duty_now))
				self.cache.set("controllerRpm",float(vescMessage.rpm))
				self.cache.set("controllerInVoltage",float(vescMessage.v_in))
				#self.cache.set("vescFault",int(vescMessage.mc_fault_code))

			#except Exception as e:
			#	print(e)
			#	self.close()
	def writeData(self):
		#Get the throttle value and write it to the vesc.
		# Throttle duty cycle value range for vesc: -100,000 to 100,000
		# Input throttle: 0 to 100
		throttle = (self.cache.getNumerical('throttle',0) * 1000.0)
		# disable throttle until it is turned down so we don't jerk hard
		if not self.throttleOutEnable:
			if throttle <= 5:
				self.throttleOutEnable = True
			throttle = 0
		throttleMessage = pyvesc.SetDutyCycle(int(throttle))
		self.port.write(pyvesc.encode(throttleMessage))
		# Write value request
		self.port.write(pyvesc.encode_request(pyvesc.GetValues()))
