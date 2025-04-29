// Package config is the Go port of server/config.py.
package config

// DefaultDataTimeout is the default number of seconds until a data point is invalidated.
const DefaultDataTimeout = 5

// DataKey describes one key in the SQLite table.
// Each entry is a key, number of decimals for rounding purposes, a unit for
// display, and a timeout in seconds (0 = never expires).
type DataKey struct {
	Name     string
	Decimals int
	Units    string
	Timeout  float64
}

// DataKeys lists the telemetry data points. Please keep sorted alphabetically
// (the trailing entries preserve the original Python ordering).
var DataKeys = []DataKey{
	{"alltraxFault", 0, "", DefaultDataTimeout},
	{"batteryConsumedAh", 2, " Ah", DefaultDataTimeout},
	{"batteryCurrent", 2, " A", DefaultDataTimeout},
	{"batteryPower", 0, " W", DefaultDataTimeout},
	{"batteryStateOfCharge", 1, "%", DefaultDataTimeout},
	{"batteryTimeRemaining", 0, " min", DefaultDataTimeout},
	{"batteryVoltage", 2, " V", DefaultDataTimeout},
	{"controllerDutyCycle", 2, "%", DefaultDataTimeout},
	{"controllerInCurrent", 0, " A", DefaultDataTimeout},
	{"controllerInVoltage", 2, " V", DefaultDataTimeout},
	{"controllerOutCurrent", 2, " A", DefaultDataTimeout},
	{"controllerRpm", 0, " rpm", DefaultDataTimeout},
	{"controllerTemp", 2, " C", DefaultDataTimeout},
	{"gpsFix", 0, "", DefaultDataTimeout},
	{"gpsHeading", 0, " deg", DefaultDataTimeout},
	{"gpsLatitude", 4, "", DefaultDataTimeout},
	{"gpsLongitude", 4, "", DefaultDataTimeout},
	{"gpsNumSatellites", 0, "", DefaultDataTimeout},
	{"gpsSpeedKnots", 2, " kt", DefaultDataTimeout},
	{"gpsSpeedMph", 2, " mph", DefaultDataTimeout},
	{"imuPitch", 2, " deg", DefaultDataTimeout},
	{"imuRoll", 2, " deg", DefaultDataTimeout},
	{"motorRpm", 0, " rpm", DefaultDataTimeout},
	{"motorTemp", 2, " C", DefaultDataTimeout},
	{"propRpm", 0, " rpm", DefaultDataTimeout},
	{"solarChargerCurrent1", 2, " A", DefaultDataTimeout},
	{"solarChargerCurrent2", 2, " A", DefaultDataTimeout},
	{"solarChargerCurrentTotal", 2, " A", DefaultDataTimeout},
	{"throttle", 0, "b", DefaultDataTimeout},
	{"throttleCurrentTarget", 1, " A", DefaultDataTimeout},
	{"throttleInput", 0, "b", DefaultDataTimeout},
	{"throttleMode", 0, "", DefaultDataTimeout},
	{"throttleRecommendation", 1, " A", DefaultDataTimeout},
	{"targetAh", 1, " Ah", 0},
	{"targetDuration", 0, "mil", 0},
	{"startTime", 0, "mil", 0},
	{"throttleEnabled", 0, "", DefaultDataTimeout},
	{"boatConfig", 0, "", DefaultDataTimeout},
	{"vescFault", 0, "", DefaultDataTimeout},
}

// AlarmSpec defines a range-based alarm on a data point.
type AlarmSpec struct {
	ID          string
	Key         string
	Description string
	Min         float64
	Max         float64
}

// AlarmThresholds defines the list of alarms. Order matters: it is preserved
// in the /alarms JSON output (Python dict insertion order).
var AlarmThresholds = []AlarmSpec{
	{"alarmVoltageRange", "batteryVoltage", "Battery Over/Under Voltage", 32, 40},
	{"alarmCurrentRange", "batteryCurrent", "Battery Over/Under Current", -20, 100},
	{"alarmStateOfCharge", "batteryStateOfCharge", "Battery Drain", 50, 100},
	{"alarmMotorTemp", "motorTemp", "Motor Over/Under Temperature", 50, 150},
	{"alarmMotorOverspeed", "motorRpm", "Motor Over Speed", 0, 3600},
	{"alarmFullThrottle", "throttle", "FULL THROTTLE", 0, 254},
}

// PortBlacklist lists serial ports that must never be opened.
var PortBlacklist = []string{
	"/dev/cu.Bluetooth-Incoming-Port",
	"/dev/cu.mifoO5Gen2Touch",
	"/dev/cu.OontZAngle3XLIDF53",
	"/dev/ttyAMA0",
	"/dev/cu.JBLCharge3-SPPDev-1",
	"/dev/cu.BIGJAMBOXbyJawbone-SPPD",
	"/dev/cu.Bluetooth-Incoming-Port",
	"/dev/cu.BoseSoundSport-SPPDev",
	"/dev/cu.BoseSoundSport-SPPDev-1",
	"/dev/cu.BoseSoundSport-SPPDev-2",
}

var (
	// DbFolder is the database path. Folder is created on start if missing.
	DbFolder = "~/SOLAR_SPLASH/telemetry/"
	DbFile   = "test1.db"

	// DbTablePrefix prefixes each session of telemetry data.
	DbTablePrefix = "dataSession"

	// DbEraseOnStart controls whether to erase the database on start.
	DbEraseOnStart = true

	// IgnoreDevices - debug: ignore all devices, don't connect to anything.
	IgnoreDevices = false

	// PollRate is the interval (seconds) at which devices are polled.
	PollRate = 0.0

	// ScanRate is the interval at which devices are scanned.
	// Offset so scan doesn't always happen at same time as database saving.
	ScanRate = 1.1

	// SaveRate is the interval at which data is saved to the database.
	SaveRate = 1.0

	// RadioPacketRate is the interval at which data is sent over radio.
	RadioPacketRate = 0.25

	// HTTPPort is the port for the HTTP interface.
	HTTPPort = 5000

	// DashboardHTTPPort is the port for the dashboard server.
	DashboardHTTPPort = 5001

	// HTTPLogging controls whether to log http requests.
	HTTPLogging = false

	// RadioSerialPort is the device the RadioManager transmits on.
	RadioSerialPort = "/dev/serial0"

	// --- Control Algorithms Configuration ---
	// Control algorithms can set telemetry data points based on other data points.
	// Automatically disabled if the server is "slave", eg receiving radio telemetry.
	IsSlave = false

	// WriteFromSlave allows the slave to write back values to the parent server.
	WriteFromSlave = true

	// ControlAlgorithmUpdateRate is the interval at which control algorithms update.
	ControlAlgorithmUpdateRate = 0.01

	// ControlAlgorithmMockData saves some mock data for testing.
	ControlAlgorithmMockData = true
)
