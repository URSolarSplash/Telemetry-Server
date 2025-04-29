package devices

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/serialio"
	"telemetryserver/internal/stats"
	"telemetryserver/internal/vesc"
)

func newVescUnderTest(t *testing.T) (*VescDevice, *serialio.FakePort, *data.DataCache) {
	t.Helper()
	stats.Reset()
	provider := serialio.NewFakeProvider()
	port := provider.Plug("/dev/ttyACM1", "ChibiOS/RT Virtual COM Port")
	cache := data.NewDataCache(config.DataKeys)
	dev := NewVescDevice(provider, cache, "/dev/ttyACM1")
	return dev, port, cache
}

func TestVescParsesGetValues(t *testing.T) {
	dev, port, cache := newVescUnderTest(t)
	frame := vesc.EncodeValues(vesc.Values{
		TempFetFiltered:   40.5,
		TempMotorFiltered: 55.1,
		AvgMotorCurrent:   -42.25,
		AvgInputCurrent:   -20.5,
		DutyCycle:         0.85,
		Rpm:               3120,
		VIn:               36.4,
	})
	// The device reads only when >= 71 bytes are waiting (Python parity),
	// so pad the frame like the byte stream of a chatty VESC would.
	padded := append(frame, make([]byte, 71-len(frame)+1)...)
	port.FeedToServer(padded)
	dev.Update()

	approx := func(key string, want float64) {
		t.Helper()
		got := cache.GetNumerical(key, -999)
		if diff := got - want; diff > 1e-6 || diff < -1e-6 {
			t.Fatalf("%s = %v, want %v", key, got, want)
		}
	}
	approx("boatConfig", 0)
	approx("motorTemp", 55.1)
	approx("controllerTemp", 40.5)
	approx("controllerInCurrent", -20.5)
	approx("controllerOutCurrent", -42.25)
	approx("controllerDutyCycle", 0.85)
	approx("controllerRpm", 3120)
	approx("controllerInVoltage", 36.4)
}

func TestVescWritesThrottleAndPollsValues(t *testing.T) {
	dev, port, cache := newVescUnderTest(t)
	cache.Set("boatConfig", 0)   // endurance mode
	cache.Set("throttleMode", 0) // manual
	cache.Set("throttle", 127.5) // half throttle -> duty 50000

	// The device writes at 10 Hz; wait past the write rate.
	dev.lastWrite = data.Now() - 1
	dev.Update()

	written := port.TakeWritten()
	wantDuty := vesc.EncodeSetDutyCycle(50000)
	wantPoll := vesc.EncodeGetValuesRequest()
	if len(written) != len(wantDuty)+len(wantPoll) {
		t.Fatalf("written %d bytes, want %d", len(written), len(wantDuty)+len(wantPoll))
	}
	for i, b := range wantDuty {
		if written[i] != b {
			t.Fatalf("duty frame mismatch at %d: %#x != %#x", i, written[i], b)
		}
	}
	for i, b := range wantPoll {
		if written[len(wantDuty)+i] != b {
			t.Fatalf("poll frame mismatch at %d", i)
		}
	}
}

func TestVescCurrentModeWrite(t *testing.T) {
	dev, port, cache := newVescUnderTest(t)
	cache.Set("boatConfig", 0)
	cache.Set("throttleMode", 1) // current limiting
	cache.Set("throttleCurrentTarget", -30)
	cache.Set("controllerDutyCycle", 5) // /10 -> 0.5 duty

	dev.lastWrite = data.Now() - 1
	dev.Update()

	// motorCurrent = (-30 / 0.5) * -1 * 1000 = 60000 mA
	written := port.TakeWritten()
	want := vesc.EncodeSetCurrent(60000)
	for i, b := range want {
		if written[i] != b {
			t.Fatalf("current frame mismatch at byte %d", i)
		}
	}
}

func TestVescSprintModeWritesZeroDuty(t *testing.T) {
	dev, port, cache := newVescUnderTest(t)
	cache.Set("boatConfig", 1) // sprint mode: alltrax owns the throttle
	cache.Set("throttle", 200)

	dev.lastWrite = data.Now() - 1
	dev.Update()

	written := port.TakeWritten()
	want := vesc.EncodeSetDutyCycle(0)
	for i, b := range want {
		if written[i] != b {
			t.Fatalf("expected zero-duty frame, mismatch at byte %d", i)
		}
	}
}
