import sqlite3

class DataPoint:
    def __init(self):
        this.test = 1

class Database:
    def __init__(self,filename):
        self.filename = filename
        # Create the database object. Will create file if not exists
        self.db = sqlite3.connect(self.filename)
        self.setSchema()

    def setSchema(self):
        cursor = self.db.cursor()
        # Tables:
        # -vesc
        # -alltrax
        # -motor
        # -battery
        # -gyro
        # -gps
        # -victron
        # -throttle
        createTableCommand = '''create table if not exists '''
        commonFields = '''id INTEGER PRIMARY KEY, timestamp INTEGER, '''
        cursor.execute(createTableCommand + 'vesc('+commonFields+' testdata INTEGER)')
        cursor.execute(createTableCommand + 'alltrax('+commonFields+' diodeTemp REAL, inVoltage REAL, inCurrent REAL, outCurrent REAL, dutyCycle REAL, errorCode INTEGER)')
        cursor.execute(createTableCommand + 'motor('+commonFields+' motorTemp REAL, motorRpm REAL, propRpm REAL)')
        cursor.execute(createTableCommand + 'battery('+commonFields+' packVoltage REAL, cellVoltage0 REAL, cellVoltage1 REAL, cellVoltage2 REAL,cellVoltage3 REAL,cellVoltage4 REAL,cellVoltage5 REAL,cellVoltage6 REAL,cellVoltage7 REAL,cellVoltage8 REAL, busTemp1 REAL, busTemp2 REAL, busTemp3 REAL, busTemp4 REAL)')
        cursor.execute(createTableCommand + 'gyro('+commonFields+' trim REAL, roll REAL, yaw REAL)')
        cursor.execute(createTableCommand + 'gps('+commonFields+' speed REAL, heading REAL, lat REAL, lon REAL, numSatellites INTEGER)')
        cursor.execute(createTableCommand + 'victron('+commonFields+' timeRemaining REAL, consumedAh REAL, shuntVoltage REAL, shuntCurrent REAL, stateOfCharge REAL)')
        cursor.execute(createTableCommand + 'throttle('+commonFields+' throttlePosition REAL)')
        self.db.commit()

    def shutdown(self):
        self.db.close()

    # Takes in a data point and saves it to the Database
    # Also triggers the IPC to send it to the electron process for live streaming
    #def setDataPoint():



def main():
    # Test program for the database object
    testDb = Database("test.db")
    testDb.shutdown()

if __name__ == "__main__":
    main()
