from time import time
import config
import sqlite3
import statistics

# Stores a single data point, which is a value that expires if it's too old.
# - get(): gets the value, or None if value is >timeout seconds old.
# - set(value): sets the value.
class DataPoint:
    def __init__(self):
        self.lastUpdated = 0
        self.value = None
        self.hasMin = False
        self.hasMax = False
        self.minValue = float("inf")
        self.maxValue = float("-inf")
    def set(self, newValue):
        self.value = newValue
        self.lastUpdated = time()
        if (self.value < self.minValue):
            self.minValue = self.value
            self.hasMin = True
        if (self.value > self.maxValue):
            self.maxValue = self.value
            self.hasMax = True
    def get(self):
        if (not self.isExpired()):
            return self.value
        else:
            return None
    def getMin(self):
        if self.hasMin:
            return self.minValue
        else:
            return None
    def getMax(self):
        if self.hasMax:
            return self.maxValue
        else:
            return None
    def isExpired(self):
        # Expires if the time since last update has been at least 5 seconds
        return (time() - self.lastUpdated > config.dataTimeOut)
    def __repr__(self):
        return "[Last Value: {0}, Expired: {1}]".format(self.value, self.isExpired())

# Represents a collection of data points for all telemetry items.
class DataCache:
    def __init__(self, keyList):
        # Create a dictionary of all data points with ID as a key
        self.values = {}
        self.keyList = sorted(keyList)
        self.radioMirror = None

        # Create list of keys which have alarms
        self.alarmedKeys = []
        for key in self.keyList:
            if key in config.alarmThresholds.keys():
                self.alarmedKeys.append(key)
        print("Alarmed keys: "+str(self.alarmedKeys))

        # Create blank data points based on key list
        for key in self.keyList:
            self.values[key] = DataPoint()
    def setRadioMirror(self, instance):
        self.radioMirror = instance
    def set(self, name, value):
        # Set a data point if it exists
        # If it doesn't exist, raise an error
        if name in self.values:
            self.values[name].set(value)
            statistics.stats["numDataPoints"] += 1
            if self.radioMirror:
                # If we're hooked up to radio transmitter, send data update packet
                self.radioMirror.write(name, value)
        else:
            print("[Tried to set invalid key [{0}]]".format(name))
    def get(self, name):
        # Get a data point's value if it exists
        # If it doesn't exist, return a null value
        if name in self.values:
            return self.values[name].get()
        else:
            print("[Tried to get invalid key [{0}]]".format(name))
            return None
    def getMin(self, name):
        # Get a data point's min value if it exists
        # If it doesn't exist, return a null value
        if name in self.values:
            return self.values[name].getMin()
        else:
            return None
    def getMax(self, name):
        # Get a data point's max value if it exists
        # If it doesn't exist, return a null value
        if name in self.values:
            return self.values[name].getMax()
        else:
            return None
    def getKeys(self):
        return self.values.keys()
    def hasValidData(self):
        for key in self.values.keys():
            if not self.values[key].isExpired():
                return True
        return False
    # Checks if the key specified is in an alarm state
    # To be in an alarm state, the following conditions must be matched:
    # - Key is in cache
    # - Key has defined alarm thresholds
    # - Key is outside alarm thresholds
    def checkAlarm(self, key):
        if key not in self.alarmedKeys:
            return False
        value = self.get(key)
        if value == None:
            return False
        if value < config.alarmThresholds[key][0]:
            return True
        if value > config.alarmThresholds[key][1]:
            return True
        return False
    # Returns a dict of alarm statuses
    def getAlarms(self):
        alarmDict = {}
        for key in self.alarmedKeys:
            alarmDict[key] = self.checkAlarm(key)
        return alarmDict
    def __repr__(self):
        representation = "[DataCache Instance with {0} values]:\n".format(len(self.values.keys()))
        for key in self.values.keys():
            representation += " -[Key: {0}, DataPoint: {1}]\n".format(key,str(self.values[key]))
        return representation

# Responsible for storage of the data cache to the sqlite database
class Database:
    def __init__(self,cache, filename, overwrite):
        self.cache = cache
        self.filename = filename
        self.overwriteOnStart = overwrite
        self.timestampOffset = 0
        self.lastSave = time()
        # Create the database object. Will create file if not exists
        self.db = sqlite3.connect(self.filename)
        self.sessionList = []
        self.sessionId = 0
        self.tableName = None
        self.getSessions()
        # Auto set the session id to one past the existing session
        while (config.dbTablePrefix + str(self.sessionId)) in self.sessionList:
            self.sessionId += 1
        self.setSchema()

    # Gets all the sessions that exist in the database.
    def getSessions(self):
        cursor = self.db.cursor()
        self.sessionList = []
        for row in cursor.execute("select name from sqlite_master WHERE type='table';"):
            self.sessionList.append(str(row[0]))
        print(self.sessionList)
        self.db.commit()

    def resetTimestamp(self):
        self.timestampOffset = time()

    def shutdown(self):
        self.db.close()

    def getSessionId(self):
        return self.sessionId

    def incrementSessionId(self):
        self.sessionId += 1
        self.createSessionTable()

    def setSessionId(self,id):
        self.sessionId = id
        self.createSessionTable()

    def saveData(self):
        if time() - self.lastSave < config.saveRate:
            return
        else:
            self.lastSave = time()

        # Saves a row of data into the database.
        cursor = self.db.cursor()
        fields = ""
        valuePlaceholders = ""
        valueList = []
        for i, key in enumerate(self.cache.getKeys()):
            fields += "," + key
            valuePlaceholders += ",?"
            valueList.append(self.cache.get(key))
        #print("fields:"+fields)
        #print("value placeholder:"+valuePlaceholders)
        #print("values:"+str(valueList))
        timestamp = time() - self.timestampOffset
        valueList.insert(0, timestamp)
        #print("[Saving database row with timestamp {0}]".format(timestamp))
        cursor.execute("insert into "+self.tableName+"(timestamp"+fields+") values (?"+valuePlaceholders+")",valueList)
        self.db.commit()

    def clearData(self):
        # Removes all data from the current session
        cursor = self.db.cursor()
        cursor.execute("delete from "+self.tableName+";")
        self.db.commit()

    # Creates a session table for the current session id, if it doesn't exist
    def createSessionTable(self):
        cursor = self.db.cursor()
        # Create the session metadata table
        cursor.execute('''create table if not exists sessionMetadata(session TEXT PRIMARY KEY, created TEXT, UNIQUE(session))''')
        self.db.commit()

        createTableCommand = '''create table if not exists '''
        self.tableName = config.dbTablePrefix + str(self.sessionId)
        tableFields = '''id INTEGER PRIMARY KEY, timestamp NUMERIC'''
        for key in sorted(self.cache.getKeys()):
            tableFields += ", {0} NUMERIC".format(key)
        #print("Creating database schema:")
        #print(createTableCommand + "data("+tableFields+")")
        cursor.execute(createTableCommand + self.tableName +"("+tableFields+")")
        self.db.commit()

        # Insert a timestamp into session metadata for when this session was created
        cursor.execute("insert or ignore into sessionMetadata(session, created) values(?,datetime('now'))",[self.tableName])
        self.db.commit()

        # Update the session list
        self.getSessions()
        print("[Database] Updated sessions. Current session name: "+self.tableName)
        print("[Database] Total number of sessions: "+str(len(self.sessionList)))

        # Update statistic with active session
        statistics.stats["activeSession"] = self.tableName

    def setSchema(self):
        cursor = self.db.cursor()
        # If we are set to overwrite all the tables, delete them all.
        if self.overwriteOnStart:
            print("Overwriting database table(s)...")
            for table in self.sessionList:
                cursor.execute("drop table if exists "+table+";")
            self.db.commit()
            # Reset session id
            self.sessionId = 0
        # Create the session table
        self.createSessionTable()
