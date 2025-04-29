package data

import (
	"testing"

	"telemetryserver/internal/config"
)

type fakeRadio struct {
	writes map[string]float64
}

func (f *fakeRadio) AddToWriteCache(name string, value float64) {
	if f.writes == nil {
		f.writes = map[string]float64{}
	}
	f.writes[name] = value
}

func TestCacheSetGet(t *testing.T) {
	fakeClock(t)
	c := NewDataCache(config.DataKeys)

	if _, ok := c.Get("batteryVoltage"); ok {
		t.Fatal("unset key should have no value")
	}
	c.Set("batteryVoltage", 36.5)
	if v, ok := c.Get("batteryVoltage"); !ok || v != 36.5 {
		t.Fatalf("got %v ok=%v", v, ok)
	}
	if c.GetNumerical("motorRpm", 123) != 123 {
		t.Fatal("GetNumerical default not returned")
	}
	// Unknown keys must not panic, matching Python's print-and-continue.
	c.Set("noSuchKey", 1)
	if _, ok := c.Get("noSuchKey"); ok {
		t.Fatal("unknown key should return no value")
	}
}

func TestCacheKeyIndexRoundtrip(t *testing.T) {
	c := NewDataCache(config.DataKeys)
	for i, key := range c.GetKeys() {
		idx, ok := c.KeyToIndex(key)
		if !ok || idx != i {
			t.Fatalf("KeyToIndex(%s) = %d ok=%v, want %d", key, idx, ok, i)
		}
		name, ok := c.IndexToKey(idx)
		if !ok || name != key {
			t.Fatalf("IndexToKey(%d) = %s, want %s", idx, name, key)
		}
	}
	if _, ok := c.IndexToKey(len(config.DataKeys)); ok {
		t.Fatal("out-of-range index should fail")
	}
}

// The Python cache reports valid data whenever any point is unexpired; the
// three timeout=0 keys (targetAh, targetDuration, startTime) never expire, so
// HasValidData is true even on a fresh cache. The port preserves this.
func TestCacheHasValidDataAlwaysTrueWithZeroTimeoutKeys(t *testing.T) {
	fakeClock(t)
	c := NewDataCache(config.DataKeys)
	if !c.HasValidData() {
		t.Fatal("expected HasValidData=true due to timeout=0 keys (Python parity)")
	}
}

func TestCacheCoveragePercentage(t *testing.T) {
	fakeClock(t)
	c := NewDataCache(config.DataKeys)
	base := c.GetCoveragePercentage() // the timeout=0 keys count as covered
	c.Set("batteryVoltage", 36)
	after := c.GetCoveragePercentage()
	want := base + 100.0/float64(len(config.DataKeys))
	if diff := after - want; diff > 1e-9 || diff < -1e-9 {
		t.Fatalf("coverage after one set = %v, want %v", after, want)
	}
}

func TestCacheMirrorsWritesToRadio(t *testing.T) {
	fakeClock(t)
	c := NewDataCache(config.DataKeys)
	radio := &fakeRadio{}
	c.SetRadioDevice(radio)

	c.Set("throttle", 100)
	if radio.writes["throttle"] != 100 {
		t.Fatal("Set should mirror to radio write cache")
	}
	c.SetNoRadio("throttle", 50)
	if radio.writes["throttle"] != 100 {
		t.Fatal("SetNoRadio must not mirror to radio")
	}
	c.SetRadioDevice(nil)
	c.Set("throttle", 25)
	if radio.writes["throttle"] != 100 {
		t.Fatal("unlinked radio must not receive writes")
	}
}

func TestAlarmStates(t *testing.T) {
	fakeClock(t)
	c := NewDataCache(config.DataKeys)
	var voltageAlarm *Alarm
	for _, a := range c.GetAlarms() {
		if a.ID == "alarmVoltageRange" {
			voltageAlarm = a
		}
	}
	if voltageAlarm == nil {
		t.Fatal("alarmVoltageRange not found")
	}

	if voltageAlarm.GetAlarmState() {
		t.Fatal("alarm with no value must be off")
	}
	c.Set("batteryVoltage", 36)
	if voltageAlarm.GetAlarmState() {
		t.Fatal("in-range value must not trip alarm")
	}
	c.Set("batteryVoltage", 31.9)
	if !voltageAlarm.GetAlarmState() {
		t.Fatal("under-voltage must trip alarm")
	}
	c.Set("batteryVoltage", 40.1)
	if !voltageAlarm.GetAlarmState() {
		t.Fatal("over-voltage must trip alarm")
	}
	if voltageAlarm.Value != 40.1 || !voltageAlarm.HasValue {
		t.Fatal("alarm should record last checked value")
	}
}
