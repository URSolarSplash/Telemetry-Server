from server.alarms import *

# Keys in the SQLite table
dataKeys = [
    "controllerTemp",
    "controllerOutCurrent",
    "controllerInCurrent",
    "controllerDutyCycle",
    "controllerRpm",
    "controllerInVoltage",
    "vescFault",
    "alltraxFault",
    "batteryVoltage",
    "batteryCurrent",
    "batteryPower",
    "batteryTimeRemaining",
    "batteryConsumedAh",
    "batteryStateOfCharge",
    "motorRpm",
    "propRpm",
    "motorTemp",
    "gyroTrimAngle",
    "gyroRollAngle",
    "gyroYawAngle",
    "gpsSpeed",
    "gpsHeading",
    "gpsTimestamp",
    "gpsLatitude",
    "gpsLongitude",
    "gpsNumSatellites",
    "throttle",
    "throttleInput",
    "throttleCurrentTarget",
    "throttleMode",
    "solarChargerCurrent1",
    "solarChargerCurrent2",
    "solarChargerCurrentTotal",
]

# Defines a list of alarms
# Each item in the dict is an alarm id, mapped to an alarm object
# Each alarm is constructed with a data point, description, a minimum value, and a maximum value.
alarmThresholds = {
    'alarmVoltageRange' : Alarm("batteryVoltage","Battery Over/Under Voltage",32,40),
    'alarmCurrentRange' : Alarm("batteryCurrent","Battery Over/Under Current",-20,100),
    'alarmStateOfCharge' : Alarm("batteryStateOfCharge","Battery Drain",50,100),
    'alarmMotorTemp' : Alarm("motorTemp","Motor Over/Under Temperature",50,150),
    'alarmMotorOverspeed' : Alarm("motorRpm","Motor Over Speed",0,3600)
}

# Blacklist for serial ports
portBlacklist = [
    "/dev/cu.Bluetooth-Incoming-Port",
    "/dev/ttyAMA0",
    "/dev/cu.JBLCharge3-SPPDev-1",
    "/dev/cu.BIGJAMBOXbyJawbone-SPPD",
    "/dev/cu.Bluetooth-Incoming-Port",
    "/dev/cu.BoseSoundSport-SPPDev"
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
scanRate = 1

# Interval at which data is saved to database
saveRate = 1

# Number of seconds until a data point is invalidated
dataTimeOut = 5

# Port for the HTTP interface
httpPort = 5000

# Whether to log http requests
httpLogging = False


#--- Control Algorithms Configuration ---
# Control algorithms can set telemetry data points based on other data points.
# For example, this can be used to drive the autopilot system in endurance.
# Will be automatically disabled if the server is "slave",eg, receiving radio telemetry.
isSlave = False

# Interval at which control algorithms are updated, if relevant
controlAlgorithmUpdateRate = 0.05

# Control algorithm which saves some mock data for testing
controlAlgorithmMockData = False
