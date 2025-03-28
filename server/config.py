from server.alarms import *

# Default number of seconds until a data point is invalidated
defaultDataTimeout = 5

# Keys in the SQLite table
# Please keep sorted alphabetically!
# Each entry is a key, number of decimals for rounding purposes, and a unit for display
# [name, decimals rounding, units, timeout seconds]
dataKeys = [
    ["alltraxFault",0,"",defaultDataTimeout],
    ["batteryConsumedAh",2," Ah",defaultDataTimeout],
    ["batteryCurrent",2," A",defaultDataTimeout],
    ["batteryPower",0," W",defaultDataTimeout],
    ["batteryStateOfCharge",1,"%",defaultDataTimeout],
    ["batteryTimeRemaining",0," min",defaultDataTimeout],
    ["batteryVoltage",2," V",defaultDataTimeout],
    ["controllerDutyCycle",2,"%",defaultDataTimeout],
    ["controllerInCurrent",0," A",defaultDataTimeout],
    ["controllerInVoltage",2," V",defaultDataTimeout],
    ["controllerOutCurrent",2," A",defaultDataTimeout],
    ["controllerRpm",0," rpm",defaultDataTimeout],
    ["controllerTemp",2," C",defaultDataTimeout],
    ["gpsFix",0,"",defaultDataTimeout],
    ["gpsHeading",0," deg",defaultDataTimeout],
    ["gpsLatitude",4,"",defaultDataTimeout],
    ["gpsLongitude",4,"",defaultDataTimeout],
    ["gpsNumSatellites",0,"",defaultDataTimeout],
    ["gpsSpeedKnots",2," kt",defaultDataTimeout],
    ["gpsSpeedMph",2," mph",defaultDataTimeout],
    ["imuPitch",2," deg",defaultDataTimeout],
    ["imuRoll",2," deg",defaultDataTimeout],
    ["motorRpm",0," rpm",defaultDataTimeout],
    ["motorTemp",2," C",defaultDataTimeout],
    ["propRpm",0," rpm",defaultDataTimeout],
    ["solarChargerCurrent1",2," A",defaultDataTimeout],
    ["solarChargerCurrent2",2," A",defaultDataTimeout],
    ["solarChargerCurrentTotal",2," A",defaultDataTimeout],
    ["throttle",0,"b",defaultDataTimeout],
    ["throttleCurrentTarget",1," A",defaultDataTimeout],
    ["throttleInput",0,"b",defaultDataTimeout],
    ["throttleMode",0,"",defaultDataTimeout],
    ["throttleRecommendation",1," A",defaultDataTimeout],
    ["targetAh",1," Ah",0],
    ["targetDuration",0,"mil",0],
    ["startTime",0,"mil",0],
    ["throttleEnabled",0,"",defaultDataTimeout],
    ["boatConfig",0,"",defaultDataTimeout],
    ["vescFault",0,"",defaultDataTimeout]
]

# Defines a list of alarms
# Each item in the dict is an alarm id, mapped to an alarm object
# Each alarm is constructed with a data point, description, a minimum value, and a maximum value.
alarmThresholds = {
    'alarmVoltageRange' : Alarm("batteryVoltage","Battery Over/Under Voltage",32,40),
    'alarmCurrentRange' : Alarm("batteryCurrent","Battery Over/Under Current",-20,100),
    'alarmStateOfCharge' : Alarm("batteryStateOfCharge","Battery Drain",50,100),
    'alarmMotorTemp' : Alarm("motorTemp","Motor Over/Under Temperature",50,150),
    'alarmMotorOverspeed' : Alarm("motorRpm","Motor Over Speed",0,3600),
    'alarmFullThrottle' : Alarm("throttle","FULL THROTTLE",0,254)
}

# Blacklist for serial ports
portBlacklist = [
    "/dev/cu.Bluetooth-Incoming-Port",
    "/dev/cu.mifoO5Gen2Touch",
	"/dev/cu.OontZAngle3XLIDF53",
    "/dev/ttyAMA0",
    "/dev/cu.JBLCharge3-SPPDev-1",
    "/dev/cu.BIGJAMBOXbyJawbone-SPPD",
    "/dev/cu.Bluetooth-Incoming-Port",
    "/dev/cu.BoseSoundSport-SPPDev",
    "/dev/cu.BoseSoundSport-SPPDev-1",
    "/dev/cu.BoseSoundSport-SPPDev-2",
]

# Database path
# Folder must exist
dbFolder = "~/SOLAR_SPLASH/telemetry/"
dbFile = "test1.db"

# Prefix for each session of telemetry data
dbTablePrefix = "dataSession"

# Whether to erase the database on start
dbEraseOnStart = True

# Debug: Ignore all devices, don't connect to anything
ignoreDevices = False

# Interval at which devices are polled
pollRate = 0

# Interval at which devices are scanned
scanRate = 1.1  # offset so scan doesn't always happen at same time as database saving

# Interval at which data is saved to database
saveRate = 1

# Interval at which data is sent over radio
radioPacketRate = 0.25

# Port for the HTTP interface
httpPort = 5000

# Port for the dashboard server
dashboardHttpPort = 5001

# Whether to log http requests
httpLogging = False

# --- Control Algorithms Configuration ---
# Control algorithms can set telemetry data points based on other data points.
# For example, this can be used to drive the autopilot system in endurance.
# Will be automatically disabled if the server is "slave",eg, receiving radio telemetry.
isSlave = False

# Whether the slave can write back values to the parent server
# Allows for control of data points (eg throttle) from a remote computer
writeFromSlave = True

# Interval at which control algorithms are updated, if relevant
controlAlgorithmUpdateRate = 0.01

# Control algorithm which saves some mock data for testing
controlAlgorithmMockData = False
