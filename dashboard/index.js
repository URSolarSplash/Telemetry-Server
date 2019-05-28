//////////////////////////////////////////////////////////
// Main html page JS
// Handles all page mechanics.
//////////////////////////////////////////////////////////

// Create an instance of the Telemetry system connected to the local machine
var Telemetry = new TelemetryServer("localhost",5000)

var chartThrottle,chartRpm,chartSpeed,chartTrim;

// On page initialization
$(function(){
    // Clear all the data points on page reload
    // After this we request a full data reload
    $(".data-point-raw").each(function(index, element){
        $(this).text("---");
    });
    chartThrottle = $('#gaugeChartThrottle').epoch({
        type: 'time.gauge',
        value: 0.0,
        domain: [0,100],
        ticks: 10,
        tickSize:30,
        tickOffset:10,
        format: function(v) { return (v).toFixed(2) + '%'; }
    });
    chartCurrent = $('#gaugeChartCurrent').epoch({
        type: 'time.gauge',
        value: 0.0,
        domain: [-250,250],
        ticks: 10,
        tickSize:30,
        tickOffset:10,
        format: function(v) { return (v).toFixed(1) + ' A'; }
    });
    chartRpm = $('#gaugeChartRpm').epoch({
        type: 'time.gauge',
        value: 0.0,
        domain: [0,3500],
        ticks: 10,
        tickSize:30,
        tickOffset:10,
        format: function(v) { return (v).toFixed(0) + ' rpm'; }
    });
    chartSpeed = $('#gaugeChartSpeed').epoch({
        type: 'time.gauge',
        value: 0.0,
        domain: [0,30],
        ticks: 10,
        tickSize:30,
        tickOffset:10,
        format: function(v) { return (v).toFixed(2) + ' mph'; }
    });
    chartTrim = $('#gaugeChartTrim').epoch({
        type: 'time.gauge',
        value: 0.0,
        domain: [-15,15],
        ticks: 10,
        tickSize:30,
        tickOffset:10,
        format: function(v) { return (v).toFixed(2) + ' deg'; }
    });
});

// Handle dashboard scaling
$(function(){
    $(window).resize(function(){
        doDashboardResize();
    });
    doDashboardResize();

});

Telemetry.addDataPointCallback("throttle",function(){
    chartThrottle.update(Telemetry.get("throttle"));
})

Telemetry.addDataPointCallback("batteryCurrent",function(){
    chartCurrent.update(Telemetry.get("batteryCurrent"));
})

Telemetry.addDataPointCallback("motorRpm",function(){
    chartRpm.update(Telemetry.get("motorRpm"));
})

Telemetry.addDataPointCallback("gpsSpeedMph",function(){
    chartSpeed.update(Telemetry.get("gpsSpeedMph"));
})

Telemetry.addDataPointCallback("imuPitch",function(){
    chartTrim.update(Telemetry.get("imuPitch"));
})

function doDashboardResize(){
    var scale = Math.min(
      $("#dashboard-scaleable-wrapper").outerWidth() / $("#dashboard-canvas").outerWidth(),
      $("#dashboard-scaleable-wrapper").outerHeight() / $("#dashboard-canvas").outerHeight()
    );

    $("#dashboard-canvas").css({
      transform: "translate(-50%, -50%) " + "scale(" + scale + ")"
    });
}


Telemetry.addStatsCallback(function(){
    $("#status-messages").text("Status: "+Telemetry.getStat("numActiveDevices")+" active device(s)");
    dataCoverageRatio = ((Telemetry.getNumValidDataPoints()/Telemetry.getNumDataPoints())*100.0).toFixed(1)
    $("#status-data").text("("+Telemetry.getStat("numDataPoints")+" data points \/ "+Telemetry.getStat("numRadioPackets")+" packets / "+dataCoverageRatio+"% coverage)")
    if (Telemetry.getStat("hasRadio") == "True") {
        $("#status-radio").text("Radio Link Established");
    } else {
        $("#status-radio").text("No Radio Link");
    }
});

Telemetry.addDataCallback(function(){
    lastDataPoints = Telemetry.getAll();
    for (source in lastDataPoints){
        for (key in lastDataPoints[source]){
            // Update live divs with the data points
            var combinedKey = source+"\\."+key;
            var current = Telemetry.round(lastDataPoints[source][key].current,2);
            var min = Telemetry.round(lastDataPoints[source][key].min,2);
            var max = Telemetry.round(lastDataPoints[source][key].max,2);
            if (current == null){ current = "---"; }
            if (min == null){ min = "---"; }
            if (max == null){ max = "---"; }
            $("#"+combinedKey).text(current);
            $("#"+combinedKey+"\\.min").text(min);
            $("#"+combinedKey+"\\.max").text(max);
        }
    }
});

var alarms = {};
var firstAlarmUpdate = true;

function updateAlarms(){
    alarms = Telemetry.getAllAlarms();
    for (var alarmId in alarms) {
        if (alarms.hasOwnProperty(alarmId)) {
            $("#alarm-"+alarmId).html("<h3>"+alarms[alarmId].desc+"</h3><span>"+alarms[alarmId].state+", ["+Telemetry.round(alarms[alarmId].value,4)+"],["+alarms[alarmId].range_min+","+alarms[alarmId].range_max+"]</span>");
            if (alarms[alarmId].state == true){
                $("#alarm-"+alarmId).removeClass("alarm-inactive").addClass("alarm-active");
            } else {
                $("#alarm-"+alarmId).removeClass("alarm-active").addClass("alarm-inactive");
            }
        }
    }
}

Telemetry.addAlarmCallback(function(){
    updateAlarms();

    // Update alarm header
    $("#alarm-header").text("Alarms ("+Telemetry.getNumAlarms()+" active)");
    $("#numActiveAlarms").text(Telemetry.getNumAlarms());
    if (Telemetry.getNumAlarms() > 0){
        $("#dashboardAlarms").addClass("dashboardAlarmsActive")
    } else {
        $("#dashboardAlarms").removeClass("dashboardAlarmsActive")
    }
});
