from time import time

class DataPoint:
    def __init__(self,name):
        self.lastUpdated = time()
        self.value = 0
        self.name = name
    def setValue(self,newValue):
        self.value = newValue
        self.lastUpdated = time()
    def getValue(self):
        if (time() - self.lastUpdated < 5):
            return self.value
        else:
            return None
    def __repr__(self):
        return "[Name: {0}, Value: {1}]".format(self.name, self.getValue())
