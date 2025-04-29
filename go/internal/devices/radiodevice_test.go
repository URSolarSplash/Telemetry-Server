package devices

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/radioproto"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

func newRadioUnderTest(t *testing.T) (*RadioDevice, *serialio.FakePort, *data.DataCache) {
	t.Helper()
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug("/dev/ttyUSB0", "FT231X USB UART")
	cache := data.NewDataCache(config.DataKeys)
	dev := NewRadioDevice(provider, cache, "/dev/ttyUSB0")
	return dev, port, cache
}

func TestRadioDeviceReceivesDataPoint(t *testing.T) {
	dev, port, cache := newRadioUnderTest(t)
	idx, _ := cache.KeyToIndex("batteryVoltage")
	port.FeedToServer(radioproto.Encode(idx, 36.5, true))
	dev.Update()

	if v := cache.GetNumerical("batteryVoltage", -1); v != 36.5 {
		t.Fatalf("batteryVoltage = %v", v)
	}
}

func TestRadioDeviceIgnoresNaNPackets(t *testing.T) {
	dev, port, cache := newRadioUnderTest(t)
	idx, _ := cache.KeyToIndex("batteryVoltage")
	port.FeedToServer(radioproto.Encode(idx, 0, false))
	dev.Update()

	if _, ok := cache.Get("batteryVoltage"); ok {
		t.Fatal("NaN packet must not set a value")
	}
}

func TestRadioDeviceFlushesWriteCache(t *testing.T) {
	dev, port, cache := newRadioUnderTest(t)
	cache.SetRadioDevice(dev)

	// Writes to the cache land in the radio write cache...
	cache.Set("throttle", 100)
	// ...and are transmitted on the next update past the packet rate.
	dev.lastUpdate = data.Now() - config.RadioPacketRate - 1
	dev.Update()

	written := port.TakeWritten()
	if len(written) != radioproto.PacketSize {
		t.Fatalf("wrote %d bytes, want one packet", len(written))
	}
	id, value, ok := radioproto.Decode(written)
	wantIdx, _ := cache.KeyToIndex("throttle")
	if !ok || id != wantIdx || value != 100 {
		t.Fatalf("transmitted packet = (%d, %v, %v)", id, value, ok)
	}

	// The write cache drains, so nothing further is sent.
	dev.lastUpdate = data.Now() - config.RadioPacketRate - 1
	dev.Update()
	if len(port.TakeWritten()) != 0 {
		t.Fatal("write cache should be empty after flush")
	}
}

func TestRadioDeviceReceiveDoesNotEcho(t *testing.T) {
	dev, port, cache := newRadioUnderTest(t)
	cache.SetRadioDevice(dev)

	idx, _ := cache.KeyToIndex("batteryVoltage")
	port.FeedToServer(radioproto.Encode(idx, 36.5, true))
	dev.Update()

	dev.lastUpdate = data.Now() - config.RadioPacketRate - 1
	dev.Update()
	if len(port.TakeWritten()) != 0 {
		t.Fatal("received packets must not be echoed back (SetNoRadio)")
	}
}
