'''
dataKeys = [
    "motorTemp",
    "motorRpm",
    "propRpm",
    "batteryPackVoltage",
    "batteryCellVoltage0",
    "batteryCellVoltage1",
    "batteryCellVoltage2",
    "batteryCellVoltage3",
    "batteryCellVoltage4",
    "batteryCellVoltage5",
    "batteryCellVoltage6",
    "batteryCellVoltage7",
    "batteryCellVoltage8",
    "batteryCellVoltage9",
    "batteryBusTemp1",
    "batteryBusTemp2",
    "batteryBusTemp3",
    "batteryBusTemp4",
    "gyroTrimAngle",
    "gyroRollAngle",
    "gyroYawAngle",
    "gpsSpeed",
    "gpsHeading",
    "gpsTimestamp",
    "gpsLatitude",
    "gpsLongitude",
    "gpsNumSatellites",
    "bmvTimeRemaining",
    "bmvConsumedAh",
    "bmvShuntVoltage",
    "bmvShuntCurrent",
    "bmvStateOfCharge"
]
'''

# Keys in the SQLite table
dataKeys = [
    "bmvTimeRemaining",
    "bmvConsumedAh",
    "bmvShuntVoltage",
    "bmvShuntCurrent",
    "bmvStateOfCharge"
]

# Blacklist for serial ports
portBlacklist = [
    "/dev/cu.Bluetooth-Incoming-Port",
    "/dev/ttyAMA0"
]

# Database path
# Folder must
dbFolder = "~/SOLAR_SPLASH/telemetry/"
dbFile = "test1.db"

# Interval at which devices are polled
pollRate = 0.1

# Interval at which devices are scanned
scanRate = 1

# Interval at which data is saved to database
saveRate = 1

# Number of seconds until a data point is invalidated
dataTimeOut = 5
