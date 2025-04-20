from flask import Flask, jsonify, request
import smtplib
import time
import server.config as config
import server.statistics as statistics
import threading
import json
import logging
import server.statistics as statistics
from gevent.pywsgi import WSGIServer
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
		currentValue = dataInstance.get(key)
		minValue = dataInstance.getMin(key)
		maxValue = dataInstance.getMax(key)
		if (currentValue is None):
			currentValue = "\"None\""
		if (minValue is None):
			minValue = "\"None\""
		if (maxValue is None):
			maxValue = "\"None\""
		jsonString += "  \"{0}\" : {{\"current\" : {1}, \"min\" : {2}, \"max\" : {3}}}".format(key,currentValue,minValue,maxValue)
	jsonString += "\n}"
	response = app.response_class(
		response=jsonString,
		status=200,
		mimetype='application/json'
	)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

@app.route('/set')
def setData():
	key = request.args.get('key')
	value = request.args.get('value')
	if (not key is None) and (not value is None):
		dataInstance.set(key,float(value))
	return value

@app.route('/stats_raw',methods=['GET'])
def statsRaw():
	return "test"

@app.route('/live_formatted',methods=['GET'])
def liveFormattedData():
	jsonString = ""
	jsonString += "{"
	for i, keyData in enumerate(config.dataKeys):
		key = keyData[0]
		keyDecimalPlaces = keyData[1]
		keyUnits = keyData[2]
		if (i > 0):
			jsonString += ",\n"
		else:
			jsonString +="\n"
		currentValue = dataInstance.get(key)
		currentValueNumerical = dataInstance.get(key)
		minValue = dataInstance.getMin(key)
		maxValue = dataInstance.getMax(key)
		if (currentValueNumerical is None):
			currentValueNumerical = 0
		if (currentValue is None):
			currentValue = "---"
		else:
			currentValue = round(currentValue,keyDecimalPlaces)
			if (keyDecimalPlaces == 0):
				currentValue = int(currentValue)
			currentValue = "{0}{1}".format(currentValue,keyUnits)
		if (minValue is None):
			minValue = "---"
		else:
			minValue = round(minValue,keyDecimalPlaces)
			if (keyDecimalPlaces == 0):
				minValue = int(minValue)
			minValue = "{0}{1}".format(minValue,keyUnits)
		if (maxValue is None):
			maxValue = "---"
		else:
			maxValue = round(maxValue,keyDecimalPlaces)
			if (keyDecimalPlaces == 0):
				maxValue = int(maxValue)
			maxValue = "{0}{1}".format(maxValue,keyUnits)
		minMaxValue = "min: {0} / max: {1}".format(minValue,maxValue)
		jsonString += "  \"{0}\" : {{\"current\" : \"{1}\", \"min_max\" : \"{2}\", \"currentNum\" : {3}}}".format(key,currentValue,minMaxValue,currentValueNumerical)
	jsonString += ",\n"
	statusString = ""
	if (statistics.stats["hasRadio"]):
		statusString += "Radio Link Established "
	else:
		statusString += "No Radio Link "
	percentCoverage = 0
	statusString += "({0} data points / {1} packets / {2:.1f}% coverage) Status: {3} active devices".format(statistics.stats["numDataPoints"],statistics.stats["numRadioPackets"],dataInstance.getCoveragePercentage(),statistics.stats["numActiveDevices"])
	jsonString += "  \"status\" : \""+statusString+"\"\n"
	jsonString += "}"
	response = app.response_class(
		response=jsonString,
		status=200,
		mimetype='application/json'
	)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

@app.route('/alarms',methods=['GET'])
def liveAlarms():
	alarms = dataInstance.getAlarms()
	# Update alarms before encoding
	for alarm in alarms:
		alarms[alarm].getAlarmState()

	jsonString = json.dumps(alarms)
	response = app.response_class(
		response=jsonString,
		status=200,
		mimetype='application/json'
	)
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

@app.route('/stats',methods=['GET'])
def liveStats():
	statistics.stats["numDataKeys"] = len(config.dataKeys)
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
	response.headers.add('Access-Control-Allow-Origin', '*')
	return response

# Returns all sessions
#@app.route('/session',methods=['GET'])
#def getAllSessions():

def flaskThread():
	#app.run(host='0.0.0.0',threaded=True, use_reloader=False)
	if config.httpLogging:
		http_server = WSGIServer(listener=('127.0.0.1', config.httpPort), application=app)
		http_server.serve_forever()
	else:
		http_server = WSGIServer(listener=('127.0.0.1', config.httpPort), application=app, log=None,error_log=None)
		http_server.serve_forever()

class HTTPServerManager:
	def __init__(self, cache):
		print("[API] Starting server instance...")
		global dataInstance
		dataInstance = cache
		threading.Thread(target=flaskThread,daemon=True).start()
