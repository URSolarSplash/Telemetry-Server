package radio

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/radioproto"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
)

func TestRadioManagerNoDevice(t *testing.T) {
	stats.Reset()
	cache := data.NewDataCache(config.DataKeys)
	m := NewRadioManager(cache, serialio.NewFakeProvider())
	if stats.HasRadio() {
		t.Fatal("hasRadio must be false without a radio port")
	}
	m.Update() // must be a no-op, not a panic
	m.Shutdown()
}

func TestRadioManagerBroadcastsAllKeys(t *testing.T) {
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug(config.RadioSerialPort, "on-board radio")
	cache := data.NewDataCache(config.DataKeys)
	m := NewRadioManager(cache, provider)
	if !stats.HasRadio() {
		t.Fatal("hasRadio must be true when the radio port opens")
	}

	cache.Set("batteryVoltage", 36.5)
	m.lastUpdate = data.Now() - config.RadioPacketRate - 1
	m.Update()

	written := port.TakeWritten()
	wantLen := len(config.DataKeys) * radioproto.PacketSize
	if len(written) != wantLen {
		t.Fatalf("broadcast %d bytes, want %d (one packet per key)", len(written), wantLen)
	}

	// Verify the batteryVoltage packet carries the value and unset keys carry NaN.
	seen := map[int]struct {
		value float64
		ok    bool
	}{}
	for i := 0; i < len(written); i += radioproto.PacketSize {
		id, value, ok := radioproto.Decode(written[i : i+radioproto.PacketSize])
		seen[id] = struct {
			value float64
			ok    bool
		}{value, ok}
	}
	voltIdx, _ := cache.KeyToIndex("batteryVoltage")
	if got := seen[voltIdx]; !got.ok || got.value != 36.5 {
		t.Fatalf("batteryVoltage packet = %+v", got)
	}
	rpmIdx, _ := cache.KeyToIndex("motorRpm")
	if got := seen[rpmIdx]; got.ok {
		t.Fatal("unset key must broadcast as NaN (no value)")
	}
}

func TestRadioManagerAppliesControlPackets(t *testing.T) {
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug(config.RadioSerialPort, "on-board radio")
	cache := data.NewDataCache(config.DataKeys)
	m := NewRadioManager(cache, provider)

	idx, _ := cache.KeyToIndex("throttleInput")
	port.FeedToServer(radioproto.Encode(idx, 200, true))
	m.Update()

	if v := cache.GetNumerical("throttleInput", -1); v != 200 {
		t.Fatalf("throttleInput = %v; control packet not applied", v)
	}
}
