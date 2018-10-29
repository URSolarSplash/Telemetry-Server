# Main telemetry server file
from server.data import DataCache
from server.database import Database
from server import config
from time import sleep

# Create a data cache
data = DataCache(config.dataKeys)
database = Database(data,"./data/test1.db",True)
database.resetTimestamp()

print(str(data))

data.set("test1",0)
while True:
    data.set("test2",0)

    if data.hasValidData():
        database.saveData()
    sleep(0.01)

database.shutdown()
