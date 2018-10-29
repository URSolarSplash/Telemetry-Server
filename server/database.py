import sqlite3
from data import *

class Database:
    def __init__(self,cache, filename, overwrite):
        self.cache = cache
        self.filename = filename
        self.overwriteOnStart = overwrite
        self.timestampOffset = 0
        # Create the database object. Will create file if not exists
        self.db = sqlite3.connect(self.filename)
        self.setSchema()

    def resetTimestamp(self):
        self.timestampOffset = time()

    def shutdown(self):
        self.db.close()

    def saveData(self):
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
