from flask import Flask, jsonify
import smtplib
import time
import server.config as config
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
	#app.run(host='0.0.0.0',threaded=True, use_reloader=False)
    http_server = WSGIServer(listener=('0.0.0.0', 3000), application=app, log=None,error_log=None)
    http_server.serve_forever()

class HTTPServerManager:
	def __init__(self, cache):
		print("[API] Starting server instance...")
		global dataInstance
		dataInstance = cache
		threading.Thread(target=flaskThread,daemon=True).start()
