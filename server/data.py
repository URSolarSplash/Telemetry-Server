from time import time
import config

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

        # Create blank data points based on key list
        for key in self.keyList:
            self.values[key] = DataPoint()
    def set(self, name, value):
        # Set a data point if it exists
        # If it doesn't exist, raise an error
        if name in self.values:
            self.values[name].set(value)
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
        return false
    def __repr__(self):
        representation = "[DataCache Instance with {0} values]:\n".format(len(self.values.keys()))
        for key in self.values.keys():
            representation += " -[Key: {0}, DataPoint: {1}]\n".format(key,str(self.values[key]))
        return representation
