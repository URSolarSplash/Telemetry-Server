import regex
import serial
import ast
from .. import statistics
import time
from .. import pynmea2
import traceback

class GenericSerialDevice(object):
	def __init__(self, cache, portName, baudRate):
		self.open = False
		self.portName = portName
		self.baudRate = baudRate
		self.lastTime = time.time()
		self.buffer = []
		self.cache = cache
		print("[Serial Device] Opened serial connection on port "+portName+", with baud rate "+str(baudRate)+".")
		try:
			self.port = serial.Serial(port=portName,baudrate=baudRate,timeout=0,write_timeout=0)
			self.open = True
		except:
			print("[Serial Device] Failed to open device!")
			self.open = False
	def isOpen(self):
		return self.open and self.port.is_open
	def close(self):
		print("[Serial Device] Closed serial connection on port "+self.portName+".")
		if self.open:
			self.port.close()
			self.open = False
	def update(self):
		# Gets new serial data if it is incoming
		pass
