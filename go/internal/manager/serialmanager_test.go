package manager

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/devices"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// fastScan removes the scan/poll rate limits for the duration of a test.
func fastScan(t *testing.T) {
	t.Helper()
	origScan, origPoll, origSlave := config.ScanRate, config.PollRate, config.IsSlave
	config.ScanRate = 0
	config.PollRate = 0
	t.Cleanup(func() {
		config.ScanRate, config.PollRate, config.IsSlave = origScan, origPoll, origSlave
	})
}

func newManagerUnderTest(t *testing.T) (*SerialManager, *serialio.FakeProvider, *data.DataCache) {
	t.Helper()
	stats.Reset()
	fastScan(t)
	provider := serialio.NewFakeProvider()
	cache := data.NewDataCache(config.DataKeys)
	return NewSerialManager(cache, provider), provider, cache
}

func TestDeviceTypeDetection(t *testing.T) {
	m, provider, _ := newManagerUnderTest(t)
	provider.Plug("/dev/ttyUSB0", "FT231X USB UART")
	provider.Plug("/dev/ttyUSB1", "VE Direct cable")
	provider.Plug("/dev/ttyACM0", "ChibiOS/RT Virtual COM Port")
	provider.Plug("/dev/ttyACM1", "Arduino Micro")

	m.UpdateDevices()

	if len(m.Devices()) != 4 {
		t.Fatalf("connected %d devices, want 4", len(m.Devices()))
	}
	types := map[string]string{}
	for _, d := range m.Devices() {
		switch d.(type) {
		case *devices.RadioDevice:
			types[d.PortName()] = "radio"
		case *devices.VictronDevice:
			types[d.PortName()] = "victron"
		case *devices.VescDevice:
			types[d.PortName()] = "vesc"
		case *devices.StatelessTelemetryNodeDevice:
			types[d.PortName()] = "node"
		}
	}
	want := map[string]string{
		"/dev/ttyUSB0": "radio",
		"/dev/ttyUSB1": "victron",
		"/dev/ttyACM0": "vesc",
		"/dev/ttyACM1": "node",
	}
	for port, kind := range want {
		if types[port] != kind {
			t.Fatalf("port %s detected as %q, want %q", port, types[port], kind)
		}
	}

	if !stats.HasRadio() {
		t.Fatal("radio device must set hasRadio")
	}
	if !config.IsSlave {
		t.Fatal("radio device must switch the server to slave mode")
	}
}

func TestBlacklistedPortIgnored(t *testing.T) {
	m, provider, _ := newManagerUnderTest(t)
	provider.Plug("/dev/ttyAMA0", "on-board UART") // blacklisted in config
	m.UpdateDevices()
	if len(m.Devices()) != 0 {
		t.Fatal("blacklisted port must not be opened")
	}
}

func TestDuplicateScanDoesNotReopen(t *testing.T) {
	m, provider, _ := newManagerUnderTest(t)
	provider.Plug("/dev/ttyACM1", "Arduino Micro")
	m.UpdateDevices()
	m.UpdateDevices()
	if len(m.Devices()) != 1 {
		t.Fatalf("device list = %d entries after rescan, want 1", len(m.Devices()))
	}
}

func TestUnplugRemovesDeviceAndResetsThrottle(t *testing.T) {
	m, provider, cache := newManagerUnderTest(t)
	provider.Plug("/dev/ttyACM1", "Arduino Micro")
	m.UpdateDevices()

	cache.Set("throttle", 200)
	cache.Set("throttleEnabled", 1)

	provider.Unplug("/dev/ttyACM1")
	m.UpdateDevices()

	if len(m.Devices()) != 0 {
		t.Fatal("unplugged device must be removed")
	}
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v; must be zeroed when telemetry node disappears", v)
	}
	if v := cache.GetNumerical("throttleEnabled", -1); v != 0 {
		t.Fatalf("throttleEnabled = %v; must be zeroed", v)
	}
}

func TestUnplugRadioClearsSlaveState(t *testing.T) {
	m, provider, cache := newManagerUnderTest(t)
	provider.Plug("/dev/ttyUSB0", "FT231X USB UART")
	m.UpdateDevices()
	if !stats.HasRadio() {
		t.Fatal("precondition: radio connected")
	}

	provider.Unplug("/dev/ttyUSB0")
	m.UpdateDevices()

	if stats.HasRadio() {
		t.Fatal("hasRadio must clear when the radio is unplugged")
	}
	// The cache must no longer mirror writes to the removed radio
	// (mirroring would panic or leak; just verify no radio is linked by
	// setting a value and ensuring nothing blows up).
	cache.Set("throttle", 1)
}

func TestUnplugSeveralDevicesAtOnce(t *testing.T) {
	// The Python version removed list items while iterating, skipping every
	// other unplugged device; the port must remove all of them in one scan.
	m, provider, _ := newManagerUnderTest(t)
	provider.Plug("/dev/ttyACM1", "Arduino Micro")
	provider.Plug("/dev/ttyACM2", "Arduino Micro")
	provider.Plug("/dev/ttyACM3", "Arduino Micro")
	m.UpdateDevices()
	if len(m.Devices()) != 3 {
		t.Fatalf("connected %d devices", len(m.Devices()))
	}

	provider.Unplug("/dev/ttyACM1")
	provider.Unplug("/dev/ttyACM2")
	provider.Unplug("/dev/ttyACM3")
	m.UpdateDevices()

	if len(m.Devices()) != 0 {
		t.Fatalf("%d devices left after unplugging all", len(m.Devices()))
	}
}

func TestIgnoreDevicesFlag(t *testing.T) {
	m, provider, _ := newManagerUnderTest(t)
	orig := config.IgnoreDevices
	config.IgnoreDevices = true
	t.Cleanup(func() { config.IgnoreDevices = orig })

	provider.Plug("/dev/ttyACM1", "Arduino Micro")
	m.UpdateDevices()
	if len(m.Devices()) != 0 {
		t.Fatal("IgnoreDevices must prevent connections")
	}
}

func TestPollDevicesDispatchesData(t *testing.T) {
	m, provider, cache := newManagerUnderTest(t)
	port := provider.Plug("/dev/ttyACM1", "Arduino Micro")
	m.UpdateDevices()

	// Feed a throttle packet and let PollDevices drive the device Update.
	packet := make([]byte, 16)
	packet[0] = 0xF0
	packet[1] = 42
	packet[14] = devices.DeviceThrottle << 4
	packet[15] = devices.EncodeChecksum(packet)
	port.FeedToServer(packet)

	m.PollDevices()

	if v := cache.GetNumerical("throttleInput", -1); v != 42 {
		t.Fatalf("throttleInput = %v; PollDevices did not drive the device", v)
	}
}
