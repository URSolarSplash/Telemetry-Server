// Package integration runs the whole telemetry server against simulated
// hardware: fake serial devices feed real protocol bytes through the serial
// manager into the cache, database, and HTTP API — no sensors or Raspberry Pi
// required.
package integration

import (
	"database/sql"
	"encoding/json"
	"io"
	"net/http/httptest"
	"path/filepath"
	"testing"
	"time"

	"telemetryserver/internal/api"
	"telemetryserver/internal/config"
	"telemetryserver/internal/controls"
	"telemetryserver/internal/data"
	"telemetryserver/internal/devices"
	"telemetryserver/internal/manager"
	"telemetryserver/internal/radio"
	"telemetryserver/internal/radioproto"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
	"telemetryserver/internal/vesc"
)

func fastConfig(t *testing.T) {
	t.Helper()
	origScan, origPoll, origSave := config.ScanRate, config.PollRate, config.SaveRate
	origMock, origSlave, origRadioRate := config.ControlAlgorithmMockData, config.IsSlave, config.RadioPacketRate
	origCtrlRate := config.ControlAlgorithmUpdateRate
	config.ScanRate = 0
	config.PollRate = 0
	config.SaveRate = 0
	config.RadioPacketRate = 0
	config.ControlAlgorithmUpdateRate = 0
	config.ControlAlgorithmMockData = false
	config.IsSlave = false
	t.Cleanup(func() {
		config.ScanRate, config.PollRate, config.SaveRate = origScan, origPoll, origSave
		config.ControlAlgorithmMockData, config.IsSlave, config.RadioPacketRate = origMock, origSlave, origRadioRate
		config.ControlAlgorithmUpdateRate = origCtrlRate
	})
	stats.Reset()
}

// buildNodePacket assembles a valid stateless-node packet like a real Arduino
// telemetry node would.
func buildNodePacket(deviceID, packetNum byte, fill func(p []byte)) []byte {
	p := make([]byte, 16)
	p[0] = 0xF0
	if fill != nil {
		fill(p)
	}
	p[14] = deviceID<<4 | packetNum&0x0F
	p[15] = devices.EncodeChecksum(p)
	return p
}

func getJSON(t *testing.T, server *httptest.Server, path string, out any) {
	t.Helper()
	resp, err := server.Client().Get(server.URL + path)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(body, out); err != nil {
		t.Fatalf("invalid JSON from %s: %v\n%s", path, err, body)
	}
}

// TestFullServerAgainstSimulatedBoat wires every ported subsystem together
// and drives it with realistic device traffic.
func TestFullServerAgainstSimulatedBoat(t *testing.T) {
	fastConfig(t)

	// --- Boot the server (mirrors main.go, with a fake serial bus) ---
	provider := serialio.NewFakeProvider()
	cache := data.NewDataCache(config.DataKeys)
	dbFile := filepath.Join(t.TempDir(), "integration.db")
	database, err := data.NewDatabase(cache, dbFile, true)
	if err != nil {
		t.Fatal(err)
	}
	defer database.Shutdown()
	database.ResetTimestamp()

	serialMgr := manager.NewSerialManager(cache, provider)
	defer serialMgr.Shutdown()
	controlAlgorithms := controls.NewControlAlgorithms(cache)
	apiServer := httptest.NewServer(api.Handler(cache))
	defer apiServer.Close()

	// --- Plug in the simulated boat hardware ---
	throttleNode := provider.Plug("/dev/ttyACM1", "Arduino Micro (throttle)")
	victronPort := provider.Plug("/dev/ttyUSB3", "VE Direct cable")
	vescPort := provider.Plug("/dev/ttyACM0", "ChibiOS/RT Virtual COM Port")

	loop := func() {
		serialMgr.UpdateDevices()
		serialMgr.PollDevices()
		if cache.HasValidData() {
			if err := database.SaveData(); err != nil {
				t.Fatal(err)
			}
		}
		if !config.IsSlave {
			controlAlgorithms.Update()
		}
	}

	loop() // first loop connects the devices

	if got := len(serialMgr.Devices()); got != 3 {
		t.Fatalf("connected devices = %d, want 3", got)
	}

	// --- Feed real protocol bytes from each simulated device ---

	// Throttle node: dead man's switch on, manual mode, throttle 3 (arms output).
	throttleNode.FeedToServer(buildNodePacket(devices.DeviceThrottle, 0, func(p []byte) {
		p[1] = 3 // throttle input
		p[3] = 1 // enabled
		p[4] = 0 // manual mode
	}))

	// Victron battery monitor block.
	block := []byte("\r\nV\t36500\r\nI\t-15000\r\nSOC\t855\r\nChecksum\t")
	sum := 0
	for _, b := range block {
		sum += int(b)
	}
	sum += '\r' + '\n'
	block = append(block, byte((256-sum%256)%256), '\r', '\n')
	victronPort.FeedToServer(block)

	// VESC values frame (padded: the driver waits for >= 71 bytes).
	frame := vesc.EncodeValues(vesc.Values{
		TempMotorFiltered: 52.5,
		TempFetFiltered:   40.0,
		AvgInputCurrent:   -18.5,
		AvgMotorCurrent:   -30.25,
		DutyCycle:         0.75,
		Rpm:               2800,
		VIn:               36.4,
	})
	vescPort.FeedToServer(append(frame, make([]byte, 72-len(frame))...))

	loop() // parses all three devices, arms throttle
	// Let the VESC driver pass its 10 Hz write rate so it sends the
	// throttle + poll frames on the next loop.
	time.Sleep(120 * time.Millisecond)
	// Throttle node now raises the throttle; controls should pass it through.
	throttleNode.FeedToServer(buildNodePacket(devices.DeviceThrottle, 0, func(p []byte) {
		p[1] = 180
		p[3] = 1
		p[4] = 0
	}))
	loop()

	// --- Verify the cache through the live API ---
	var live map[string]map[string]any
	getJSON(t, apiServer, "/live", &live)
	if v := live["batteryVoltage"]["current"]; v != 36.5 {
		t.Fatalf("batteryVoltage over API = %v", v)
	}
	if v := live["controllerRpm"]["current"]; v != 2800.0 {
		t.Fatalf("controllerRpm over API = %v", v)
	}
	if v := live["motorTemp"]["current"]; v != 52.5 {
		t.Fatalf("motorTemp over API = %v", v)
	}
	if v := live["throttle"]["current"]; v != 180.0 {
		t.Fatalf("throttle over API = %v (controls did not pass through)", v)
	}

	// batteryStateOfCharge 85.5% is below the 50..100 alarm's minimum? No:
	// 85.5 is in range; verify alarms report healthy.
	var alarms map[string]struct {
		State bool     `json:"state"`
		Value *float64 `json:"value"`
	}
	getJSON(t, apiServer, "/alarms", &alarms)
	if alarms["alarmStateOfCharge"].State {
		t.Fatal("SOC 85.5% must not trip the drain alarm")
	}
	if alarms["alarmVoltageRange"].Value == nil || *alarms["alarmVoltageRange"].Value != 36.5 {
		t.Fatal("voltage alarm should carry the live value")
	}

	// --- Verify device writes back to the boat ---
	// The VESC receives duty-cycle commands derived from the throttle.
	written := vescPort.TakeWritten()
	if len(written) == 0 {
		t.Fatal("VESC should have received throttle + poll frames")
	}

	// --- Verify stats ---
	var statsResp map[string]string
	getJSON(t, apiServer, "/stats", &statsResp)
	if statsResp["numActiveDevices"] != "3" {
		t.Fatalf("numActiveDevices = %q", statsResp["numActiveDevices"])
	}
	if statsResp["activeSession"] != "dataSession0" {
		t.Fatalf("activeSession = %q", statsResp["activeSession"])
	}

	// --- Verify rows landed in SQLite ---
	db, err := sql.Open("sqlite", dbFile)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	var count int
	if err := db.QueryRow("select count(*) from dataSession0").Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count == 0 {
		t.Fatal("no rows saved to the database")
	}
	var voltage float64
	if err := db.QueryRow("select batteryVoltage from dataSession0 where batteryVoltage is not null limit 1").Scan(&voltage); err != nil {
		t.Fatal(err)
	}
	if voltage != 36.5 {
		t.Fatalf("saved batteryVoltage = %v", voltage)
	}

	// --- Unplug everything; the server must keep running ---
	provider.Unplug("/dev/ttyACM1")
	provider.Unplug("/dev/ttyUSB3")
	provider.Unplug("/dev/ttyACM0")
	loop()
	if got := len(serialMgr.Devices()); got != 0 {
		t.Fatalf("devices after unplug = %d", got)
	}
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v; must be zeroed when the node disappears", v)
	}
}

// TestRadioLinkBoatToShore couples a boat-side RadioManager to a shore-side
// server whose RadioDevice arrives over USB, verifying the radio protocol
// end to end including the write-back path.
func TestRadioLinkBoatToShore(t *testing.T) {
	fastConfig(t)

	// Boat side: cache + RadioManager on /dev/serial0.
	boatProvider := serialio.NewFakeProvider()
	boatRadioPort := boatProvider.Plug(config.RadioSerialPort, "on-board radio")
	boatCache := data.NewDataCache(config.DataKeys)
	boatRadio := radio.NewRadioManager(boatCache, boatProvider)
	defer boatRadio.Shutdown()

	// Shore side: cache + serial manager that discovers the USB radio.
	shoreProvider := serialio.NewFakeProvider()
	shoreRadioPort := shoreProvider.Plug("/dev/ttyUSB0", "FT231X USB UART")
	shoreCache := data.NewDataCache(config.DataKeys)
	shoreMgr := manager.NewSerialManager(shoreCache, shoreProvider)
	defer shoreMgr.Shutdown()
	shoreMgr.UpdateDevices()
	if !config.IsSlave {
		t.Fatal("shore server should enter slave mode")
	}

	// Boat measures a battery voltage and broadcasts it.
	boatCache.Set("batteryVoltage", 36.5)
	boatRadio.Update()
	airBytes := boatRadioPort.TakeWritten()
	if len(airBytes) == 0 {
		t.Fatal("boat radio wrote nothing")
	}

	// ...the bytes travel over the air to the shore USB radio...
	shoreRadioPort.FeedToServer(airBytes)
	// The shore device consumes one packet per poll (Python parity), so poll
	// once per key.
	for range config.DataKeys {
		shoreMgr.PollDevices()
	}

	if v := shoreCache.GetNumerical("batteryVoltage", -1); v != 36.5 {
		t.Fatalf("shore batteryVoltage = %v", v)
	}

	// Shore writes a throttle command (e.g. via /set); it must be mirrored
	// back to the boat through the radio write cache.
	shoreCache.Set("throttleInput", 200)
	shoreMgr.PollDevices() // flush write cache (RadioPacketRate = 0)
	replyBytes := shoreRadioPort.TakeWritten()
	if len(replyBytes) != radioproto.PacketSize {
		t.Fatalf("shore->boat bytes = %d, want one packet", len(replyBytes))
	}
	boatRadioPort.FeedToServer(replyBytes)
	boatRadio.Update()
	if v := boatCache.GetNumerical("throttleInput", -1); v != 200 {
		t.Fatalf("boat throttleInput = %v; write-back failed", v)
	}
}
