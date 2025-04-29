package data

import "telemetryserver/internal/config"

// Alarm represents a range-based alarm (port of server/alarms.py).
type Alarm struct {
	cache *DataCache

	ID          string
	Key         string
	Description string
	Min         float64
	Max         float64

	// Value/HasValue and State mirror the "value" and "state" entries of the
	// Python dict; they are refreshed by GetAlarmState().
	Value    float64
	HasValue bool
	State    bool
}

// NewAlarm builds an alarm bound to a cache from its config spec.
func NewAlarm(cache *DataCache, spec config.AlarmSpec) *Alarm {
	return &Alarm{
		cache:       cache,
		ID:          spec.ID,
		Key:         spec.Key,
		Description: spec.Description,
		Min:         spec.Min,
		Max:         spec.Max,
	}
}

// GetAlarmState refreshes and returns whether the alarm is tripped: true when
// the watched value exists and is outside [Min, Max].
func (a *Alarm) GetAlarmState() bool {
	if a.cache == nil {
		a.State = false
		return a.State
	}
	value, ok := a.cache.Get(a.Key)
	a.Value = value
	a.HasValue = ok
	a.State = false
	if !ok {
		a.State = false
	} else if value < a.Min {
		a.State = true
	} else if value > a.Max {
		a.State = true
	}
	return a.State
}
