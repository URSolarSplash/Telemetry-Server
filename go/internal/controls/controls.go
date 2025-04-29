// Package controls ports server/controls.py: control algorithms which set
// data points based on other data points (e.g. throttle regulation).
// Disabled when the server is in "slave" mode.
package controls

import (
	"math"

	"telemetryserver/internal/config"
	"telemetryserver/internal/data"
)

// ControlAlgorithms handles all control algorithms which set values.
type ControlAlgorithms struct {
	cache             *data.DataCache
	lastUpdate        float64
	prevBoatConfig    float64
	prevThrottleMode  float64
	throttleOutEnable bool
	startTime         float64
}

// NewControlAlgorithms binds the control algorithms to a cache.
func NewControlAlgorithms(cache *data.DataCache) *ControlAlgorithms {
	return &ControlAlgorithms{
		cache:      cache,
		lastUpdate: data.Now(),
		startTime:  data.Now(),
	}
}

func millis() float64 {
	return data.Now() * 1000
}

// interp linearly maps val from [a,b] onto [x,y].
func interp(val, a, b, x, y float64) float64 {
	q := (val - a) / (b - a)
	return y + (1-q)*(x-y)
}

// GetEffective maps an average current draw to the battery's effective
// amp-hour capacity (discharge-rate curve).
func (c *ControlAlgorithms) GetEffective(avgCurrent float64) float64 {
	switch {
	case avgCurrent <= 7.9:
		return 39.5
	case avgCurrent <= 23.5:
		return interp(avgCurrent, 7.9, 23.5, 39.5, 35.25)
	case avgCurrent <= 33.8:
		return interp(avgCurrent, 23.5, 33.8, 35.25, 33.8)
	case avgCurrent <= 60.8:
		return interp(avgCurrent, 33.8, 60.8, 33.8, 30.4)
	case avgCurrent <= 104.1:
		return interp(avgCurrent, 60.8, 104.1, 30.4, 26.03)
	case avgCurrent <= 138.4:
		return interp(avgCurrent, 104.1, 138.4, 26.03, 23.07)
	case avgCurrent <= 212.0:
		return interp(avgCurrent, 138.4, 212.0, 23.07, 17.67)
	default:
		return 17.667
	}
}

// Update runs the control algorithms, rate limited to
// config.ControlAlgorithmUpdateRate.
func (c *ControlAlgorithms) Update() {
	if data.Now()-c.lastUpdate < config.ControlAlgorithmUpdateRate {
		return
	}
	c.lastUpdate = data.Now()

	if config.ControlAlgorithmMockData {
		// Save mock data into the cache for a bunch of data points.
		c.cache.Set("throttleMode", 0)
		c.cache.Set("throttleEnabled", 1)
		c.cache.Set("throttleInput", math.Abs(math.Sin((data.Now()-c.startTime)/100.0)*254))
	}

	// ------ AUTO THROTTLE REGULATION ALGORITHM -------
	// Mode 0 - Manual throttle
	// Mode 1 - Current limiting throttle
	//          Maximizes throttle, aiming to hit a certain current target.
	// Inputs: Throttle cutoff - Value of user throttle potentiometer
	//         Limiter setting - Target amperage from user limiter potentiometer
	//         Throttle mode - Manual / auto based on user input

	// If we switch boat config or mode, require a throttle reset
	newBoatConfig := c.cache.GetNumerical("boatConfig", 0)
	if c.prevBoatConfig != newBoatConfig {
		c.prevBoatConfig = newBoatConfig
		c.throttleOutEnable = false
	}
	newThrottleMode := c.cache.GetNumerical("throttleMode", 0)
	if c.prevThrottleMode != newThrottleMode {
		c.prevThrottleMode = newThrottleMode
		c.throttleOutEnable = false
	}

	// If dead man's switch is pulled, require a throttle reset
	if c.cache.GetNumerical("throttleEnabled", 0) == 0 {
		c.cache.Set("throttle", 0)
		c.throttleOutEnable = false
	} else {
		if c.cache.GetNumerical("throttleMode", 0) == 0 {
			// Mode 0 - Manual Throttle
			// Just set output throttle to the throttle cutoff value.
			c.cache.Set("throttle", c.cache.GetNumerical("throttleInput", 0))
		} else {
			// Mode 1 - Current limiting throttle
			throttleInput := c.cache.GetNumerical("throttleInput", 0)

			// This goal current is read by the VESC.
			// Note: Alltrax right now does not support current-based mode!
			// Map throttle input to a current value
			goalCurrent := (throttleInput / 255.0) * -60.0
			c.cache.Set("throttleCurrentTarget", goalCurrent)
			c.cache.Set("throttle", throttleInput)
		}

		// Handle any case where it's been deemed the throttle must be reset
		if !c.throttleOutEnable {
			if c.cache.GetNumerical("throttle", 0) <= 5 {
				c.throttleOutEnable = true
			}
			c.cache.Set("throttle", 0)
			c.cache.Set("throttleCurrentTarget", 0)
		}
	}

	// current recommendation
	if c.cache.GetNumerical("startTime", 0) == 0 {
		c.cache.Set("startTime", millis())
	}
	elapsedTime := millis() - c.cache.GetNumerical("startTime", 0)
	avgCurrent := c.cache.GetNumerical("batteryConsumedAh", 0) / elapsedTime
	// Consumed Ah is a neg. number
	ahrRemaining := c.GetEffective(avgCurrent) + c.cache.GetNumerical("batteryConsumedAh", 0)
	suggestedCurrent := (ahrRemaining - c.cache.GetNumerical("targetAh", 0)) /
		((c.cache.GetNumerical("targetDuration", 3*1000*3600) - elapsedTime) / 3.6e6)
	suggestedCurrent += c.cache.GetNumerical("solarChargerCurrentTotal", 0)
	c.cache.Set("throttleRecommendation", suggestedCurrent)
}
