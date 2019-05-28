//////////////////////////////////////////////////////////
// Telemetry-Server.js
// Library which handles connection to a telemetry Server
// Featuring:
// - Live data streaming
// - Polling of data points
// - Getting and setting data points
// - Callbacks and handlers for data
//////////////////////////////////////////////////////////
// Usage
// Telemetry.get("name")       - Gets a data point's last value (NULL if expired)
// Telemetry.set("name",value) - Sets a data point's value and sends this to server
// Telemetry.getMin("name")    - Gets a data point's minimum value (NULL if none)
// Telemetry.getMax("name")    - Gets a data point's maximum value (NULL if none)
// Telemetry.pause()           - Pauses the streaming of new telemetry data
// Telemetry.unpause()         - Unpauses the streaming of new telemetry data
// Telemetry.addDataCallback(func)    - Adds a callback for any data update
// Telemetry.removeDataCallback(func) - Removes a callback for any data update
// Telemetry.addStatsCallback(func)    - Adds a callback for any stats update
// Telemetry.removeStatsCallback(func) - Removes a callback for any stats update
// Telemetry.addDataPointCallback(data, func)    - Adds a callback for a data point
// Telemetry.removeDataPointCallback(data, func) - Removes a callback for a data point
// Telemetry.addAlarmCallback(func)    - Adds a callback for an alarm
// Telemetry.removeAlarmCallback(func) - Removes a callback for an alarm
// Telemetry.getAll()          - Returns all data points
// Telemetry.getAllAlarms()    - Returns all alarms
//////////////////////////////////////////////////////////

// add functionality to delete an item from an array by value
Array.prototype.remove = function() {
    var what, a = arguments, L = a.length, ax;
    while (L && this.length) {
        what = a[--L];
        while ((ax = this.indexOf(what)) !== -1) {
            this.splice(ax, 1);
        }
    }
    return this;
};

class TelemetryServer {
    constructor(ip,port){
        this.ip = ip;
        this.port = port;
        this.address = "http://" + this.ip + ":" + this.port;
        this.isPaused = false;

        // Used to store callback functions for data points
        this.dataCallbacks = [];
        this.statsCallbacks = [];
        this.dataPointCallbacks = {};
        //this.alarmCallbacks = {};
        this.alarmCallbacks = [];

        // Stores the last data points
        this.lastDataPoints = {};

        // Stores statistics about data
        this.numDataPoints = 0;
        this.numDataPackets = 0;
        this.alarms = null;
        this.shownModal = false;

        // On startup, setup a websockets client which will receive updates from the server

        // Temporarily use the old JSON method to get data
        // Repeatedly calls a web request which fills in data
        // Call web requests for live data and statistics
        var telemetryInstance = this;
        setInterval(function() {
            $.getJSON(telemetryInstance.address+"/live", function(data){
                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        telemetryInstance._receiveDataPoint("telemetry",key,data[key]);
                    }
                }

                // Call the data callbacks
                for (var i = 0; i < telemetryInstance.dataCallbacks.length; i++){
                    telemetryInstance.dataCallbacks[i].call();
                }
                if (telemetryInstance.shownModal){
                    hideModal();
                    telemetryInstance.shownModal = false;
                    location.reload();
                }
            }).fail(function(){
                // Show an error modal to indicate we need to wait until we are connected to the server.
                showModal("Telemetry Offline","Connecting to the Telemetry Server. Please wait...<br><br> Please ensure that the telemetry server is running.");
                telemetryInstance.shownModal = true;
            });
            $.getJSON(telemetryInstance.address+"/stats", function(data){
                for (var key in data) {
                    if (data.hasOwnProperty(key)) {
                        var dataPacket = {}
                        dataPacket.current = data[key]
                        telemetryInstance._receiveDataPoint("stats",key,dataPacket);
                    }
                }
                // Call the stats callbacks
                for (var i = 0; i < telemetryInstance.statsCallbacks.length; i++){
                    telemetryInstance.statsCallbacks[i].call();
                }
            }).fail(function(){});
            $.getJSON(telemetryInstance.address+"/alarms", function(data){
                telemetryInstance.alarms = data;
                // Call all of the alarm callbacks
                // For now, alarm callbacks are global and don't correspond to individual alarms
                // TODO: Implement callback calling based on state switch of individual alarms
                for (var i = 0; i < telemetryInstance.alarmCallbacks.length; i++){
                    telemetryInstance.alarmCallbacks[i].call();
                }
                /*
                for (var key in telemetryInstance.alarms){
                    if (key in telemetryInstance.alarmCallbacks){
                        for (var i = 0; i < telemetryInstance.alarmCallbacks[key].length; i++){
                            telemetryInstance.alarmCallbacks[key][i].call();
                        }
                    }
                }
                */
            }).fail(function(){});
      }, 250);
    }

    // Rounds a data point if it's a number
    round(inputNumber, decimals){
        if (isNaN(inputNumber) | inputNumber == null){
            return inputNumber;
        } else {
            return Number(Math.round(inputNumber+'e'+decimals)+'e-'+decimals);
        }
    }

    // Gets the latest value for a data point. Returns NULL if the data point is expired.
    get(dataPointName){
        if (dataPointName in this.lastDataPoints.telemetry){
            return this.lastDataPoints.telemetry[dataPointName].current;
        }
        return null;
    }

    // gets the latest of a statistic
    getStat(statName){
        if (statName in this.lastDataPoints.stats){
            return this.lastDataPoints.stats[statName].current;
        }
        return null;
    }

    // Sets the latest value for a data point. This gets relayed back to the server.
    // TODO send over socket back to telemetry server
    set(dataPointName,dataPointValue){
        this._receiveDataPoint("telemetry",dataPointName,dataPointValue);
        console.log("[Telemetry] Telemetry data point change not saved upstream.")
    }

    getMin(dataPointName){
        if (dataPointName in this.lastDataPoints.telemetry){
            return this.lastDataPoints.telemetry.dataPointName.min;
        }
        return null;
    }

    getMax(dataPointName){
        if (dataPointName in this.lastDataPoints.source){
            return this.lastDataPoints.source.dataPointName.max;
        }
        return null;
    }

    // Pauses / unpauses the live data stream.
    // when stream is resumed, the data will jump to the latest values.
    // This just prevents input data from being saved (cutting it off at the socket).
    pause(){
        console.log("[Telemetry] paused data stream.")
        this.isPaused = true;
    }
    unpause(){
        console.log("[Telemetry] resumed data stream.")
        this.isPaused = false;
    }

    // Returns a list of all data points and states
    getAll(){
        return this.lastDataPoints;
    }

    // Returns a list of all alarms and states
    getAllAlarms(){
        return this.alarms;
    }

    // Returns the number of active alarms
    getNumAlarms(){
        var numAlarms = 0;
        for (var alarmKey in this.alarms) {
            if (this.alarms.hasOwnProperty(alarmKey)) {
                if (alarms[alarmKey].state == true){
                    numAlarms++;
                }
            }
        }
        return numAlarms;
    }

    // Gets the number of valid data points
    getNumValidDataPoints(){
        var numDataPoints = 0;
        for (var dataPointKey in this.lastDataPoints.telemetry) {
            if (this.lastDataPoints.telemetry.hasOwnProperty(dataPointKey)) {
                if (this.lastDataPoints.telemetry[dataPointKey].current != null){
                    numDataPoints++;
                }
            }
        }
        return numDataPoints;
    }

    // Gets the number of data points
    getNumDataPoints(){
        var numDataPoints = 0;
        for (var dataPointKey in this.lastDataPoints.telemetry) {
            if (this.lastDataPoints.telemetry.hasOwnProperty(dataPointKey)) {
                numDataPoints++;
            }
        }
        return numDataPoints;
    }

    addStatsCallback(func){
        this.statsCallbacks.push(func);
    }

    removeStatsCallback(func){
        this.statsCallbacks.remove(func);
    }

    addDataCallback(func){
        this.dataCallbacks.push(func);
    }

    removeDataCallback(func){
        this.dataCallbacks.remove(func);
    }

    addDataPointCallback(dataPoint,func){
        if (!(dataPoint in this.dataPointCallbacks)){
            this.dataPointCallbacks[dataPoint] = [];
        }
        this.dataPointCallbacks[dataPoint].push(func);
    }

    removeDataPointCallback(dataPoint, func){
        if (dataPoint in this.dataPointCallbacks){
            this.dataPointCallbacks[dataPoint].remove(func);
        }
    }

    addAlarmCallback(func){
        /*
        if (!(dataPoint in this.alarmCallbacks)){
            this.alarmCallbacks[dataPoint] = [];
        }
        this.alarmCallbacks[dataPoint].push(func);
        */
        this.alarmCallbacks.push(func);
    }
    removeAlarmCallback(func){
        /*
        if (dataPoint in this.alarmCallbacks){
            this.alarmCallbacks[dataPoint].remove(func);
        }
        */
        this.alarmCallbacks.remove(func);
    }

    // -- pseudo-private methods, don't use outside library --
    _receiveDataPoint(source,key,value){
        // If we are paused just skip over the data points
        if (!this.isPaused){
            if (!(source in this.lastDataPoints)){
                this.lastDataPoints[source] = {};
            }
            if (value.current == "None"){ value.current = null; }
            if (value.min == "None"){ value.min = null; }
            if (value.max == "None"){ value.max = null; }
            this.lastDataPoints[source][key] = {};
            this.lastDataPoints[source][key].current = value.current;
            this.lastDataPoints[source][key].min = value.min;
            this.lastDataPoints[source][key].max = value.max;
            // Call the callbacks for this data point, if they exist
            if (source == "telemetry"){
                if (key in this.dataPointCallbacks){
                    for (var i = 0; i < this.dataPointCallbacks[key].length; i++){
                        this.dataPointCallbacks[key][i].call();
                    }
                }
            }
        }
    }
}

//////////////////////////////////////////////////////////
// End of File
//////////////////////////////////////////////////////////
