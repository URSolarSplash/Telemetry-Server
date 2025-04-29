package controls

import (
	"testing"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
	"telemetryserver/internal/stats"
)

func newControlsUnderTest(t *testing.T) (*ControlAlgorithms, *data.DataCache) {
	t.Helper()
	stats.Reset()
	origRate := config.ControlAlgorithmUpdateRate
	origMock := config.ControlAlgorithmMockData
	config.ControlAlgorithmUpdateRate = 0
	config.ControlAlgorithmMockData = false
	t.Cleanup(func() {
		config.ControlAlgorithmUpdateRate = origRate
		config.ControlAlgorithmMockData = origMock
	})
	cache := data.NewDataCache(config.DataKeys)
	return NewControlAlgorithms(cache), cache
}

func TestGetEffectiveCurve(t *testing.T) {
	c, _ := newControlsUnderTest(t)
	cases := []struct{ in, want float64 }{
		{0, 39.5},
		{7.9, 39.5},
		{23.5, 35.25},
		{(7.9 + 23.5) / 2, (39.5 + 35.25) / 2}, // linear midpoint
		{33.8, 33.8},
		{60.8, 30.4},
		{104.1, 26.03},
		{138.4, 23.07},
		{212.0, 17.67},
		{500, 17.667},
	}
	for _, tc := range cases {
		got := c.GetEffective(tc.in)
		if diff := got - tc.want; diff > 1e-9 || diff < -1e-9 {
			t.Fatalf("GetEffective(%v) = %v, want %v", tc.in, got, tc.want)
		}
	}
}

func TestDeadMansSwitchZeroesThrottle(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	cache.Set("throttle", 150)
	cache.Set("throttleEnabled", 0)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v with dead man's switch off", v)
	}
}

func TestManualThrottleRequiresResetBeforeEnabling(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	cache.Set("throttleEnabled", 1)
	cache.Set("throttleMode", 0)

	// High throttle before a reset: output must stay clamped to zero.
	cache.Set("throttleInput", 100)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v before throttle reset", v)
	}

	// Bring the throttle down to <= 5: this arms the output...
	cache.Set("throttleInput", 3)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v during arming iteration", v)
	}

	// ...and from now on the input passes straight through.
	cache.Set("throttleInput", 100)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 100 {
		t.Fatalf("throttle = %v after reset, want 100", v)
	}
}

func TestCurrentLimitingModeSetsTarget(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	cache.Set("throttleEnabled", 1)
	cache.Set("throttleMode", 1)

	// Arm the throttle first (mode change also forces a reset).
	cache.Set("throttleInput", 0)
	c.Update()

	cache.Set("throttleInput", 255)
	c.Update()

	if v := cache.GetNumerical("throttle", -1); v != 255 {
		t.Fatalf("throttle = %v", v)
	}
	if v := cache.GetNumerical("throttleCurrentTarget", 1); v != -60 {
		t.Fatalf("throttleCurrentTarget = %v, want -60 (full throttle)", v)
	}
}

func TestModeSwitchForcesThrottleReset(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	cache.Set("throttleEnabled", 1)
	cache.Set("throttleMode", 0)

	// Arm and drive at full throttle.
	cache.Set("throttleInput", 0)
	c.Update()
	cache.Set("throttleInput", 200)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 200 {
		t.Fatalf("precondition failed: throttle = %v", v)
	}

	// Switching modes must clamp the output until re-armed.
	cache.Set("throttleMode", 1)
	c.Update()
	if v := cache.GetNumerical("throttle", -1); v != 0 {
		t.Fatalf("throttle = %v after mode switch, want 0", v)
	}
}

func TestThrottleRecommendationIsProduced(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	cache.Set("throttleEnabled", 0)
	c.Update()
	if _, ok := cache.Get("throttleRecommendation"); !ok {
		t.Fatal("throttleRecommendation should be set")
	}
	if v := cache.GetNumerical("startTime", 0); v == 0 {
		t.Fatal("startTime should be initialized")
	}
}

func TestMockDataPopulatesThrottleInputs(t *testing.T) {
	c, cache := newControlsUnderTest(t)
	config.ControlAlgorithmMockData = true
	c.Update()
	if _, ok := cache.Get("throttleInput"); !ok {
		t.Fatal("mock data should set throttleInput")
	}
	if v := cache.GetNumerical("throttleEnabled", -1); v != 1 {
		t.Fatalf("throttleEnabled = %v", v)
	}
}
