package devices

import (
	"encoding/binary"
	"math"
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

// putFloatLE writes a float in the node wire format (reversed big-endian,
// i.e. little-endian float32).
func putFloatLE(packet []byte, offset int, v float32) {
	binary.LittleEndian.PutUint32(packet[offset:], math.Float32bits(v))
}

// buildNodePacket assembles a valid 16-byte stateless node packet.
func buildNodePacket(deviceID, packetNum byte, fill func(p []byte)) []byte {
	p := make([]byte, 16)
	p[0] = 0xF0
	if fill != nil {
		fill(p)
	}
	p[14] = deviceID<<4 | packetNum&0x0F
	p[15] = EncodeChecksum(p)
	return p
}

func newNodeUnderTest(t *testing.T) (*StatelessTelemetryNodeDevice, *serialio.FakePort, *data.DataCache) {
	t.Helper()
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug("/dev/ttyUSB9", "Arduino Micro")
	cache := data.NewDataCache(config.DataKeys)
	dev := NewStatelessTelemetryNodeDevice(provider, cache, "/dev/ttyUSB9")
	if !dev.IsOpen() {
		t.Fatal("device should open against fake port")
	}
	return dev, port, cache
}

func TestChecksumRoundtrip(t *testing.T) {
	p := buildNodePacket(DeviceThrottle, 0, func(p []byte) {
		p[1] = 0xAB
		p[2] = 0x01
	})
	if DecodeChecksum(p) != 255 {
		t.Fatal("checksum of a valid packet must decode to 255")
	}
	p[5] ^= 0x10
	if DecodeChecksum(p) == 255 {
		t.Fatal("corrupted packet must fail checksum")
	}
}

func TestThrottlePacket(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	port.FeedToServer(buildNodePacket(DeviceThrottle, 0, func(p []byte) {
		p[1] = 0x2A // throttle low byte -> 42
		p[2] = 0x00
		p[3] = 1 // enabled
		p[4] = 1 // mode
	}))
	dev.Update()

	if v := cache.GetNumerical("throttleInput", -1); v != 42 {
		t.Fatalf("throttleInput = %v", v)
	}
	if v := cache.GetNumerical("throttleEnabled", -1); v != 1 {
		t.Fatalf("throttleEnabled = %v", v)
	}
	if v := cache.GetNumerical("throttleMode", -1); v != 1 {
		t.Fatalf("throttleMode = %v", v)
	}
}

func TestMotorBoardPacket(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	// motorTemp is only stored in sprint mode (boatConfig 1)
	cache.Set("boatConfig", 1)
	port.FeedToServer(buildNodePacket(DeviceMotorBoard, 0, func(p []byte) {
		putFloatLE(p, 1, 48.5)                     // motorTemp
		binary.LittleEndian.PutUint32(p[5:], 3000) // motorRpm
		binary.LittleEndian.PutUint32(p[9:], 1740) // propRpm
	}))
	dev.Update()

	if v := cache.GetNumerical("motorTemp", -1); v != 48.5 {
		t.Fatalf("motorTemp = %v", v)
	}
	if v := cache.GetNumerical("motorRpm", -1); v != 3000 {
		t.Fatalf("motorRpm = %v", v)
	}
	if v := cache.GetNumerical("propRpm", -1); v != 1740 {
		t.Fatalf("propRpm = %v", v)
	}
}

func TestGpsPackets(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)

	// Packet 0: IMU + fix/satellites/heading
	port.FeedToServer(buildNodePacket(DeviceGpsImu, 0, func(p []byte) {
		putFloatLE(p, 1, 2.5)  // pitch
		putFloatLE(p, 5, -1.5) // roll
		p[9] = 1               // fix
		p[10] = 7              // satellites
		p[11] = 127            // heading -> ~179.29 deg
	}))
	dev.Update()

	if v := cache.GetNumerical("imuPitch", -99); v != 2.5 {
		t.Fatalf("imuPitch = %v", v)
	}
	if v := cache.GetNumerical("imuRoll", -99); v != -1.5 {
		t.Fatalf("imuRoll = %v", v)
	}
	if v := cache.GetNumerical("gpsNumSatellites", -1); v != 7 {
		t.Fatalf("gpsNumSatellites = %v", v)
	}
	heading := cache.GetNumerical("gpsHeading", -1)
	if diff := heading - (127.0/255.0)*360.0; diff > 1e-9 || diff < -1e-9 {
		t.Fatalf("gpsHeading = %v", heading)
	}

	// Packet 1: position + speed
	port.FeedToServer(buildNodePacket(DeviceGpsImu, 1, func(p []byte) {
		putFloatLE(p, 1, 43.13)  // latitude
		putFloatLE(p, 5, -77.63) // longitude
		putFloatLE(p, 9, 10.0)   // speed knots
		p[13] = 1                // fix
	}))
	dev.Update()

	if v := cache.GetNumerical("gpsSpeedKnots", -1); v != 10 {
		t.Fatalf("gpsSpeedKnots = %v", v)
	}
	mph := cache.GetNumerical("gpsSpeedMph", -1)
	if diff := mph - 11.5078; diff > 1e-4 || diff < -1e-4 {
		t.Fatalf("gpsSpeedMph = %v", mph)
	}

	// Without a fix, position data must not be stored.
	port.FeedToServer(buildNodePacket(DeviceGpsImu, 1, func(p []byte) {
		putFloatLE(p, 1, 99.0)
		p[13] = 0 // no fix
	}))
	dev.Update()
	if v := cache.GetNumerical("gpsLatitude", -1); v != float64(float32(43.13)) {
		t.Fatalf("gpsLatitude overwritten without fix: %v", v)
	}
	if v := cache.GetNumerical("gpsFix", -1); v != 0 {
		t.Fatalf("gpsFix = %v", v)
	}
}

func TestSolarPacket(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	port.FeedToServer(buildNodePacket(DeviceSolar, 0, func(p []byte) {
		putFloatLE(p, 1, 4.25)
		putFloatLE(p, 5, 3.75)
		putFloatLE(p, 9, 8.0)
	}))
	dev.Update()

	if v := cache.GetNumerical("solarChargerCurrent1", -1); v != 4.25 {
		t.Fatalf("solarChargerCurrent1 = %v", v)
	}
	if v := cache.GetNumerical("solarChargerCurrent2", -1); v != 3.75 {
		t.Fatalf("solarChargerCurrent2 = %v", v)
	}
	if v := cache.GetNumerical("solarChargerCurrentTotal", -1); v != 8 {
		t.Fatalf("solarChargerCurrentTotal = %v", v)
	}
}

func TestAlltraxPacketGetsThrottleResponse(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	cache.Set("boatConfig", 1) // sprint mode
	cache.Set("throttle", 300) // 0x012C: exercises both bytes
	cache.Set("throttleEnabled", 1)

	port.FeedToServer(buildNodePacket(DeviceAlltrax, 0, nil))
	dev.Update()

	response := port.TakeWritten()
	if len(response) != 16 {
		t.Fatalf("response length = %d, want 16", len(response))
	}
	if response[0] != 0xF0 {
		t.Fatal("response missing header")
	}
	if response[1] != 0x2C || response[2] != 0x01 {
		t.Fatalf("throttle bytes = %#x %#x, want 0x2c 0x01", response[1], response[2])
	}
	if response[3] != 1 {
		t.Fatal("throttleEnabled byte not set")
	}
	if DecodeChecksum(response) != 255 {
		t.Fatal("response checksum invalid")
	}
	if v := cache.GetNumerical("boatConfig", -1); v != 1 {
		t.Fatalf("boatConfig = %v", v)
	}
}

func TestNonAlltraxGetsNoResponse(t *testing.T) {
	dev, port, _ := newNodeUnderTest(t)
	port.FeedToServer(buildNodePacket(DeviceSolar, 0, nil))
	dev.Update()
	if written := port.TakeWritten(); len(written) != 0 {
		t.Fatalf("unexpected response written: %v", written)
	}
}

func TestCorruptPacketDropped(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	packet := buildNodePacket(DeviceThrottle, 0, func(p []byte) { p[1] = 42 })
	packet[15] ^= 0xFF // break checksum
	port.FeedToServer(packet)
	dev.Update()

	if _, ok := cache.Get("throttleInput"); ok {
		t.Fatal("corrupt packet must not update the cache")
	}
	if stats.NumDroppedNodePackets() != 1 {
		t.Fatalf("dropped packets = %d, want 1", stats.NumDroppedNodePackets())
	}
}

func TestLeadingGarbageIsSkipped(t *testing.T) {
	dev, port, cache := newNodeUnderTest(t)
	garbage := []byte{0x01, 0x02, 0x99}
	packet := buildNodePacket(DeviceThrottle, 0, func(p []byte) { p[1] = 42 })
	port.FeedToServer(append(garbage, packet...))
	dev.Update()

	if v := cache.GetNumerical("throttleInput", -1); v != 42 {
		t.Fatalf("throttleInput = %v; garbage before header not skipped", v)
	}
}

func TestUpdateAfterUnplugClosesDevice(t *testing.T) {
	stats.Reset()
	provider := serialio.NewFakeProvider()
	provider.Plug("/dev/ttyUSB9", "Arduino Micro")
	cache := data.NewDataCache(config.DataKeys)
	dev := NewStatelessTelemetryNodeDevice(provider, cache, "/dev/ttyUSB9")

	provider.Unplug("/dev/ttyUSB9") // cable pulled: port operations now error
	dev.Update()
	if dev.IsOpen() {
		t.Fatal("device should close itself after a read error")
	}
}
