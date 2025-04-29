// Package data ports server/data.py: the DataPoint / DataCache structures and
// the SQLite-backed Database.
package data

import (
	"fmt"
	"math"
	"time"
)

// Now returns the current unix time in float seconds. It is a variable so
// tests can substitute a fake clock.
var Now = func() float64 {
	return float64(time.Now().UnixNano()) / 1e9
}

// DataPoint stores a single value that expires if it's too old.
// Methods are not goroutine-safe on their own; DataCache serializes access.
type DataPoint struct {
	lastUpdated float64
	timeout     float64
	hasValue    bool
	value       float64
	hasMin      bool
	hasMax      bool
	minValue    float64
	maxValue    float64
}

// NewDataPoint creates an empty data point with the given timeout in seconds.
// A timeout of zero means the data never expires.
func NewDataPoint(timeout float64) *DataPoint {
	return &DataPoint{
		timeout:  timeout,
		minValue: math.Inf(1),
		maxValue: math.Inf(-1),
	}
}

// Set stores a new value, refreshing the expiration and min/max tracking.
// NaN values are skipped.
func (d *DataPoint) Set(newValue float64) {
	if math.IsNaN(newValue) {
		return
	}
	d.value = newValue
	d.hasValue = true
	d.lastUpdated = Now()
	if d.value < d.minValue {
		d.minValue = d.value
		d.hasMin = true
	}
	if d.value > d.maxValue {
		d.maxValue = d.value
		d.hasMax = true
	}
}

// Get returns the value, or ok=false if the value is more than timeout seconds old.
func (d *DataPoint) Get() (value float64, ok bool) {
	if !d.IsExpired() {
		return d.value, d.hasValue
	}
	return 0, false
}

// GetNumerical returns the value, or the default when expired or never set.
func (d *DataPoint) GetNumerical(def float64) float64 {
	if v, ok := d.Get(); ok {
		return v
	}
	return def
}

// GetMin returns the historical minimum, if one was ever recorded.
func (d *DataPoint) GetMin() (float64, bool) {
	return d.minValue, d.hasMin
}

// GetMax returns the historical maximum, if one was ever recorded.
func (d *DataPoint) GetMax() (float64, bool) {
	return d.maxValue, d.hasMax
}

// IsExpired reports whether the time since last update exceeds the timeout.
// If timeout is zero, data never times out.
func (d *DataPoint) IsExpired() bool {
	if d.timeout == 0 {
		return false
	}
	return Now()-d.lastUpdated > d.timeout
}

func (d *DataPoint) String() string {
	if d.hasValue {
		return fmt.Sprintf("[Last Value: %v, Expired: %v]", d.value, d.IsExpired())
	}
	return fmt.Sprintf("[Last Value: None, Expired: %v]", d.IsExpired())
}
