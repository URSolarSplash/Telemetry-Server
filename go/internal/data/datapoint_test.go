package data

import (
	"math"
	"testing"
)

// fakeClock lets tests advance data.Now manually.
func fakeClock(t *testing.T) *float64 {
	t.Helper()
	now := 1000.0
	orig := Now
	Now = func() float64 { return now }
	t.Cleanup(func() { Now = orig })
	return &now
}

func TestDataPointExpiry(t *testing.T) {
	now := fakeClock(t)
	dp := NewDataPoint(5)

	if _, ok := dp.Get(); ok {
		t.Fatal("unset data point should have no value")
	}
	dp.Set(42)
	if v, ok := dp.Get(); !ok || v != 42 {
		t.Fatalf("expected 42, got %v ok=%v", v, ok)
	}

	*now += 4.9
	if _, ok := dp.Get(); !ok {
		t.Fatal("value should still be live before timeout")
	}
	*now += 0.2
	if _, ok := dp.Get(); ok {
		t.Fatal("value should have expired after timeout")
	}
	if dp.GetNumerical(-1) != -1 {
		t.Fatal("GetNumerical should return default when expired")
	}
}

func TestDataPointZeroTimeoutNeverExpires(t *testing.T) {
	now := fakeClock(t)
	dp := NewDataPoint(0)
	dp.Set(7)
	*now += 1e6
	if v, ok := dp.Get(); !ok || v != 7 {
		t.Fatal("zero-timeout data point must never expire")
	}
}

func TestDataPointMinMax(t *testing.T) {
	fakeClock(t)
	dp := NewDataPoint(5)
	if _, ok := dp.GetMin(); ok {
		t.Fatal("min should be unset initially")
	}
	if _, ok := dp.GetMax(); ok {
		t.Fatal("max should be unset initially")
	}
	dp.Set(10)
	dp.Set(3)
	dp.Set(8)
	if v, ok := dp.GetMin(); !ok || v != 3 {
		t.Fatalf("min: got %v ok=%v, want 3", v, ok)
	}
	if v, ok := dp.GetMax(); !ok || v != 10 {
		t.Fatalf("max: got %v ok=%v, want 10", v, ok)
	}
}

func TestDataPointSkipsNaN(t *testing.T) {
	fakeClock(t)
	dp := NewDataPoint(5)
	dp.Set(5)
	dp.Set(math.NaN())
	if v, ok := dp.Get(); !ok || v != 5 {
		t.Fatal("NaN set should be ignored")
	}
}
