from server.alarms import *

# Keys in the SQLite table
# Please keep sorted alphabetically!
dataKeys = [
    "alltraxFault",
    "batteryConsumedAh",
    "batteryCurrent",
    "batteryPower",
    "batteryStateOfCharge",
    "batteryTimeRemaining",
    "batteryVoltage",
    "controllerDutyCycle",
    "controllerInCurrent",
    "controllerInVoltage",
    "controllerOutCurrent",
    "controllerRpm",
    "controllerTemp",
    "gpsFix",
    "gpsHeading",
    "gpsLatitude",
    "gpsLongitude",
    "gpsNumSatellites",
    "gpsSpeedKnots",
    "gpsSpeedMph",
    "imuPitch",
    "imuRoll",
    "motorRpm",
    "motorTemp",
    "propRpm",
    "solarChargerCurrent1",
    "solarChargerCurrent2",
    "solarChargerCurrentTotal",
    "throttle",
    "throttleCurrentTarget",
    "throttleInput",
    "throttleMode",
    "throttleRecommendation",
    "vescFault"
]

# Defines formatting for the dashboard UI
# rounding decimal places, units
dataKeyFormat = [
    [0,""],
    [2,"Ah"],
    [2,"A"],
    [2,"W"],
    [2,"%"],
    [0,"min"],
    [2,"V"],
    [2,"%"],
    [2,"A"],
    [2,"V"],
    [2,"A"],
    [2,"rpm"],
    [2,"C"],
    [0,""],
    [1,"deg"],
    [2,""],
    [2,""],
    [0,""],
    [2,"kt"],
    [2,"mph"],
    [2,"deg"],
    [2,"deg"],
    [2,"rpm"],
    [2,"C"],
    [2,"rpm"],
    [2,"A"],
    [2,"A"],
    [2,"A"],
    [0,""],
    [2,"A"],
    [0,""],
    [0,""],
    [2,"A"],
    [0,""]
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
dbEraseOnStart = False

# Debug: Ignore all devices, don't connect to anything
ignoreDevices = False

# Interval at which devices are polled
pollRate = 0

# Interval at which devices are scanned
scanRate = 1.1 # offset so scan doesn't always happen at same time as database saving

# Interval at which data is saved to database
saveRate = 1

# Number of seconds until a data point is invalidated
dataTimeOut = 5

# Port for the HTTP interface
httpPort = 5000

# Port for the dashboard server
dashboardHttpPort = 5001

# Whether to log http requests
httpLogging = False

#--- Control Algorithms Configuration ---
# Control algorithms can set telemetry data points based on other data points.
# For example, this can be used to drive the autopilot system in endurance.
# Will be automatically disabled if the server is "slave",eg, receiving radio telemetry.
isSlave = False

# Interval at which control algorithms are updated, if relevant
controlAlgorithmUpdateRate = 0.01

# Control algorithm which saves some mock data for testing
controlAlgorithmMockData = False
