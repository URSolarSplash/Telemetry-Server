from server.alarms import *

# Keys in the SQLite table
# Please keep sorted alphabetically!
# Each entry is a key, number of decimals for rounding purposes, and a unit for display
dataKeys = [
    ["alltraxFault",0,""],
    ["batteryConsumedAh",2," Ah"],
    ["batteryCurrent",2," A"],
    ["batteryPower",0," W"],
    ["batteryStateOfCharge",1,"%"],
    ["batteryTimeRemaining",0," min"],
    ["batteryVoltage",2," V"],
    ["controllerDutyCycle",2,"%"],
    ["controllerInCurrent",0," A"],
    ["controllerInVoltage",2," V"],
    ["controllerOutCurrent",2," A"],
    ["controllerRpm",0," rpm"],
    ["controllerTemp",2," C"],
    ["gpsFix",0,""],
    ["gpsHeading",0," deg"],
    ["gpsLatitude",4,""],
    ["gpsLongitude",4,""],
    ["gpsNumSatellites",0,""],
    ["gpsSpeedKnots",2," kt"],
    ["gpsSpeedMph",2," mph"],
    ["imuPitch",2," deg"],
    ["imuRoll",2," deg"],
    ["motorRpm",0," rpm"],
    ["motorTemp",2," C"],
    ["propRpm",0," rpm"],
    ["solarChargerCurrent1",2," A"],
    ["solarChargerCurrent2",2," A"],
    ["solarChargerCurrentTotal",2," A"],
    ["throttle",0,"b"],
    ["throttleCurrentTarget",1," A"],
    ["throttleInput",0,"b"],
    ["throttleMode",0,""],
    ["throttleRecommendation",1," A"],
    ["vescFault",0,""]
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
