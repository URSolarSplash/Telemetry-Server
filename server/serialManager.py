import traceback
import time
import serial.tools.list_ports
import sys
import atexit
import platform
import re
import server.config as config
from server.devices.TelemetryNodeDevice import *
from server.devices.RadioDevice import *
from server.devices.TelemetryNodeDevice import *
from server.devices.TelemetryTextDevice import *
from server.devices.UsbGpsDevice import *
from server.devices.UsbWindSensorDevice import *
from server.devices.VictronDevice import *
from server.devices.VescDevice import *
import server.statistics as statistics

class SerialDevice:
	def __init__(self, id, baud):
		self.portName = None
		self.portInstance = None
		self.baudRate = None
		self.buffer = None
		self.mode = None
		self.lastPolled = time.time()
	def needsPoll(self):
		return time.time() - self.lastPolled > config.pollRate

class SerialManager:
	def __init__(self, cache):
		self.cache = cache
		self.devices = []
		self.deviceBlacklist = config.portBlacklist
		self.lastScan = time.time()
		self.lastPoll = time.time()

	def shutdown(self):
		for device in self.devices:
			device.close()
		print("[Serial Manager] shutdown complete.")

	def updateDevices(self):
		if time.time() - self.lastScan < config.scanRate:
			return
		else:
			self.lastScan = time.time()

		# Update number of live devices
		statistics.stats["numActiveDevices"] = len(self.devices)

		#print("[Serial Manager] Scanning devices...")
		try:
			portList = list(serial.tools.list_ports.comports())
		except:
			print("[Serial Manager] Race condition during port scan. Skipping scan...")
			return
		# Scan through the entire list of serial ports looking for devices
		portNames = []

		# Debug: Ignore devices
		if config.ignoreDevices:
			portList = []
		for port in portList:
			portNames.append(port[0])
			portAlreadyOpen = False
			portId = port[0]
			portDescription = port[1]
			for device in self.devices:
				if (device.portName == port[0]):
					#Port already exists
					portAlreadyOpen = True
			if portAlreadyOpen:
				continue

			# We have found a new device
			# Exit early if the device ID is blacklisted
			if port[0] in self.deviceBlacklist:
				continue

			print("[Serial Manager] detected new device id={0}, desc={1}".format(str(portId),str(portDescription)))

			# This device is one of the following:
			# - Victron BMV device
			# - USB GPS
			# - Telemetry Protocol device
			# - Radio serial
			# We will use the USB-Serial description field to determine this.
			# If the description matches a known hardware device, we use the custom
			# protocol, otherwise we use the standard telemetry protocol.
			deviceInstance = None
			if portDescription.startswith("FT231X"):
				# USB Radio Telemetry
				print("[Serial Manager] Detected Device Type: USB Radio Telemetry")
				# Attempt to open a connection
				deviceInstance = RadioDevice(self.cache,portId)
				# Turn on radio flag in statistics
				statistics.stats["hasRadio"] = True
				# Disable control algorithms for this session (slave mode).
				print("[Serial Manager] Setting config to slave mode for duration of this session! Control algorithms disabled.")
				config.isSlave = True
			elif portDescription.startswith("u_blox 7") or portDescription.startswith("u-blox 7"):
				print("[Serial Manager] Detected Device Type: U-Blox GPS")
				deviceInstance = UsbGpsDevice(self.cache,portId)
			elif portDescription.startswith("VE Direct"):
				print("[Serial Manager] Detected Device Type: VE Direct")
				deviceInstance = VictronDevice(self.cache,portId)
			elif portDescription.startswith("CP2102 USB to UART"):
				print("[Serial Manager] Detected Device Type: Wind Sensor")
				deviceInstance = UsbWindSensorDevice(self.cache,portId)
			elif portDescription.startswith("ChibiOS"):
				print("[Serial Manager] Detected Device Type: Vesc Motor Controller")
				deviceInstance = VescDevice(self.cache,portId)
			else:
				print("[Serial Manager] Detected Device Type: Default Telemetry")
				deviceInstance = TelemetryNodeDevice(self.cache,portId)

			# Add newly opened device to the list
			self.devices.append(deviceInstance)

		# Remove serial devices that have been closed
		# This is identified based on if the serial device is closed
		# or if the device did not show up on the serial scan
		for device in self.devices:
			if not (device.isOpen() and (device.portName in portNames)):
				device.close()
				self.devices.remove(device)
				if type(device) is RadioDevice:
					statistics.stats["hasRadio"] = False

	def pollDevices(self):
		if time.time() - self.lastPoll < config.pollRate:
			return
		else:
			self.lastPoll = time.time()

		#print("[Serial Manager] Polling devices...")
		# Get data from our active device list
		for device in self.devices:
			#print("[Serial Manager] - polling "+device.portName)
			if (device.isOpen()):
				 device.update()
