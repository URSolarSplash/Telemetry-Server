from flask import Flask, jsonify
import smtplib
import time
import config
import thread
import json
import logging
import statistics
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
dataInstance = None
@app.route('/live',methods=['GET'])
def liveData():
    jsonString = ""
    jsonString += "{"
    for i, key in enumerate(dataInstance.getKeys()):
        if (i > 0):
            jsonString += ",\n"
        else:
            jsonString +="\n"
        jsonString += "  \"{0}\" : {{\"current\" : \"{1}\", \"min\" : \"{2}\", \"max\" : \"{3}\"}}".format(key,dataInstance.get(key),dataInstance.getMin(key),dataInstance.getMax(key))
    jsonString += "\n}"
    response = app.response_class(
        response=jsonString,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/alarms',methods=['GET'])
def liveAlarms():
    jsonString = ""
    jsonString += "{"
    alarms = dataInstance.getAlarms()
    for i, alarmKey in enumerate(alarms.keys()):
        if (i > 0):
            jsonString += ",\n"
        else:
            jsonString +="\n"
        jsonString += "  \"{0}\" : {1}".format(alarmKey,"true" if alarms[alarmKey] else "false")
    jsonString += "\n}"
    response = app.response_class(
        response=jsonString,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/stats',methods=['GET'])
def liveStats():
    jsonString = ""
    jsonString += "{"
    for i, key in enumerate(statistics.stats.keys()):
        if (i > 0):
            jsonString += ",\n"
        else:
            jsonString +="\n"
        jsonString += "  \"{0}\" : \"{1}\"".format(key,statistics.stats[key])
    jsonString += "\n}"
    response = app.response_class(
        response=jsonString,
        status=200,
        mimetype='application/json'
    )
    return response

# Returns all sessions
#@app.route('/session',methods=['GET'])
#def getAllSessions():

def flaskThread():
    app.run(host='0.0.0.0',threaded=True, use_reloader=False)

class HTTPServerManager:
    def __init__(self, cache):
        print("[HTTP Server Manager] Starting server instance...")
        global dataInstance
        dataInstance = cache
        thread.start_new_thread(flaskThread,())
