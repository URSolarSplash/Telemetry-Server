from time import time
import config
import sqlite3

# Stores a single data point, which is a value that expires if it's too old.
# - get(): gets the value, or None if value is >timeout seconds old.
# - set(value): sets the value.
class DataPoint:
    def __init__(self):
        self.lastUpdated = 0
        self.value = None
    def set(self, newValue):
        self.value = newValue
        self.lastUpdated = time()
    def get(self):
        if (not self.isExpired()):
            return self.value
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
    def getKeys(self):
        return self.values.keys()
    def hasValidData(self):
        for key in self.values.keys():
            if not self.values[key].isExpired():
                return True
        return False
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
        self.setSchema()

    def resetTimestamp(self):
        self.timestampOffset = time()

    def shutdown(self):
        self.db.close()

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
        print("[Saving database row with timestamp {0}]".format(timestamp))
        cursor.execute("insert into data(timestamp"+fields+") values (?"+valuePlaceholders+")",valueList)
        self.db.commit()

    def clearData(self):
        # Removes all data
        cursor = self.db.cursor()
        cursor.execute("delete from data;")
        self.db.commit()

    def setSchema(self):
        cursor = self.db.cursor()
        if self.overwriteOnStart:
            print("Overwriting database table...")
            cursor.execute("drop table if exists data;")
            self.db.commit()
        createTableCommand = '''create table if not exists '''
        tableFields = '''id INTEGER PRIMARY KEY, timestamp NUMERIC'''
        for key in sorted(self.cache.getKeys()):
            tableFields += ", {0} NUMERIC".format(key)
        print("Creating database schema:")
        print(createTableCommand + "data("+tableFields+")")
        cursor.execute(createTableCommand + "data("+tableFields+")")
        self.db.commit()
